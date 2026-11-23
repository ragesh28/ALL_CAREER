"""Live, bounded per-company probes using the production scraper functions.

Writes reports and samples only; never calls production storage/checkpoint code.
Each company runs in its own process so a broken endpoint cannot hang the audit.
"""
import argparse
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.company_job_details import details_from_record, enrich_jobs, normalize_job_links


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def companies(engine):
    if engine == "direct":
        return json.loads((ROOT / "workday_scraper/companies_links.json").read_text(encoding="utf-8"))
    if engine == "indeed":
        return [{"company": name} for name in load("step3_big_company_scrape.py", "step3").TOP_COMPANIES]
    module = load("scrape_from_md.py", "md")
    api, browser = module.parse_md_file(str(ROOT / "job_api_calls.md"))
    return [{**info, "company": info["name"], "browser": info in browser} for info in api + browser]


def probe(engine, index, output):
    started = time.monotonic()
    os.environ["COMPANY_SAMPLE_LIMIT"] = "5"
    # Do not emit secret Markdown configuration, HTTP headers or raw logs.
    with open(os.devnull, "w", encoding="utf-8") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        config = companies(engine)[index]
        name = config["company"]
        error = ""
        http_results = []
        import requests
        real_request = requests.sessions.Session.request
        def observed_request(session, method, url, **kwargs):
            from urllib.parse import urlparse
            try:
                response = real_request(session, method, url, **kwargs)
                http_results.append(f"{urlparse(url).hostname}: HTTP {response.status_code}")
                return response
            except requests.RequestException as exc:
                http_results.append(f"{urlparse(url).hostname}: {type(exc).__name__}")
                raise
        requests.sessions.Session.request = observed_request

        def bound_jobspy(module):
            if not hasattr(module, "scrape_jobs"):
                return
            original = module.scrape_jobs
            @wraps(original)
            def small_search(*args, **kwargs):
                kwargs["results_wanted"] = min(5, kwargs.get("results_wanted", 5))
                return original(*args, **kwargs)
            module.scrape_jobs = small_search
        try:
            if engine == "direct":
                module = load("workday_scraper/scrape_all_companies_v2.py", "direct")
                bound_jobspy(module)
                jobs = module.detect_and_scrape(name, config.get("ats", ""), (config.get("urls") or [""])[0], limit=20)
                in_india = [j for j in jobs if module.is_india(j.get("location", ""))]
            elif engine == "indeed":
                module = load("step3_big_company_scrape.py", "step3")
                jobs, blocked = module.scrape_company(name, ["India"], results_wanted=5)
                error = "blocked" if blocked else ""
                in_india = jobs
            else:
                module = load("scrape_from_md.py", "md")
                bound_jobspy(module)
                result = module.scrape_with_browser(config) if config.get("browser") else module.dispatch_api(config)
                jobs = result.get("all_jobs") or result.get("sample_jobs") or []
                error = result.get("error") or result.get("reason") or ""
                in_india = [j for j in jobs if module.is_india(j.get("location", ""))]
            base_url = config.get("url") or (config.get("urls") or [""])[0]
            normalize_job_links(in_india, base_url)
            valid = [j for j in in_india if (j.get("title") or "").strip() and (j.get("apply_url") or j.get("url"))]
            sample = dict(valid[0]) if valid else None
            had_description = bool(sample and details_from_record(sample).get("description"))
            if sample:
                enrich_jobs([sample], limit=1)
            row = {"engine": engine, "company": name, "index": index,
                   "status": "sample_found" if sample else "invalid_job_links" if in_india else "no_india_sample" if jobs else "no_jobs_returned",
                   "returned": len(jobs), "india_returned": len(in_india),
                   "description_before": had_description,
                   "description_after": bool(sample and sample.get("description")),
                   "sample": sample, "error": re.sub(r"https?://\S+", "[endpoint]", str(error))[:300]}
        except Exception as exc:
            row = {"engine": engine, "company": name, "index": index, "status": "error", "sample": None,
                   "error": re.sub(r"https?://\S+", "[endpoint]", str(exc))[:300]}
        row["seconds"] = round(time.monotonic() - started, 2)
        row["http_results"] = list(dict.fromkeys(http_results))[-10:]
        Path(output).write_text(json.dumps(row, ensure_ascii=False, default=str), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["direct", "md", "indeed"], required=True)
    parser.add_argument("--worker", type=int)
    parser.add_argument("--output", default=".git/company-audit")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.worker is not None:
        probe(args.engine, args.worker, args.output)
        return
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    configs = companies(args.engine)
    if args.limit:
        configs = configs[:args.limit]

    def run(index, config):
        path = output / f"{args.engine}-{index:03}.json"
        command = [sys.executable, str(Path(__file__).resolve()), "--engine", args.engine, "--worker", str(index), "--output", str(path)]
        try:
            process = subprocess.run(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=args.timeout)
            if process.returncode != 0 or not path.exists():
                raise RuntimeError("worker failed before producing a sample")
            row = json.loads(path.read_text(encoding="utf-8"))
        except (subprocess.TimeoutExpired, RuntimeError) as exc:
            row = {"engine": args.engine, "company": config["company"], "index": index, "status": "timeout" if isinstance(exc, subprocess.TimeoutExpired) else "error", "sample": None, "error": str(exc)[:150]}
            path.write_text(json.dumps(row), encoding="utf-8")
        print(f'{index + 1}/{len(configs)} {config["company"]}: {row["status"]}; description={bool(row.get("description_after"))}', flush=True)
        return row

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        names = {n.strip().lower() for n in os.environ.get("COMPANY_AUDIT_ONLY", "").split(",") if n.strip()}
        futures = [executor.submit(run, i, config) for i, config in enumerate(configs) if not names or config["company"].lower() in names]
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: row["index"])
    (output / f"{args.engine}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    found = sum(row.get("status") == "sample_found" for row in rows)
    descriptions = sum(bool(row.get("description_after")) for row in rows)
    print(f"FINAL {args.engine}: {len(rows)} companies, {found} samples, {descriptions} descriptions", flush=True)


if __name__ == "__main__":
    main()
