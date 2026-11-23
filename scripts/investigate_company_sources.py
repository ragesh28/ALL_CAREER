"""Resume public browser/API/proxy investigations and checkpoint each company."""
import argparse
import json
import os
import subprocess
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests
from scripts.company_proxy_transport import ProxyPool
from scripts.company_recovery import HEADERS, add_descriptions, browser_observe, description_from_html, jobs_from_html, public_feeds, request_feed, safe_url, unique_jobs
from scripts.company_job_details import confirmed_india_location
from scripts.company_sources import configuration


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    temporary.replace(path)


def investigate(company, output, pool):
    started = time.monotonic()
    class AttemptLog(list):
        def append(self, entry):
            super().append(entry)
            write_json(output / f"{company['id']}.json", {**company, "state": "in_progress", "attempts": list(self)})
    attempts = AttemptLog()
    config = configuration(company["company"]) or {}
    jobs, feeds, validated_feeds = [], list(config.get("feeds", [])), []
    evidence = output / company["id"]
    url = company["career_url"]
    try:
        response = requests.get(url, headers=HEADERS, timeout=(6, 20))
        entry = {"method": "direct-html", "url": safe_url(url), "http_status": response.status_code}
        if response.status_code == 200:
            jobs.extend(jobs_from_html(response.text, response.url))
            feeds.extend(public_feeds(response.url, response.text))
        entry["jobs"] = len(jobs)
        attempts.append(entry)
    except requests.RequestException as error:
        attempts.append({"method": "direct-html", "outcome": type(error).__name__})
    for source in company["sources"]:
        source_url = source["source_url"]
        if "/api/pcsx/search" in source_url or "boards-api.greenhouse.io" in source_url:
            feeds.append({"url": source_url, "method": "GET"})
    for feed in list({json.dumps(f, sort_keys=True): f for f in feeds}.values())[:4]:
        try:
            found, entry = request_feed(feed)
            attempts.append(entry)
            jobs.extend(found)
            if found:
                validated_feeds.append(feed)
        except (requests.RequestException, ValueError) as error:
            attempts.append({"method": "public-api", "url": safe_url(feed["url"]), "outcome": type(error).__name__})
    try:
        found, entry = browser_observe(url, evidence / "browser")
        jobs.extend(found)
        observed = entry.pop("observed_feeds", []) + entry.pop("discovered_feeds", [])
        attempts.append(entry)
        for feed in list({json.dumps(f, sort_keys=True): f for f in observed}.values())[:5]:
            try:
                found, entry = request_feed(feed)
                entry["method"] = "observed-api-replay"
                attempts.append(entry)
                jobs.extend(found)
                if found:
                    validated_feeds.append(feed)
            except (requests.RequestException, ValueError) as error:
                attempts.append({"method": "observed-api-replay", "url": safe_url(feed["url"]), "outcome": type(error).__name__})
    except Exception as error:
        attempts.append({"method": "playwright", "outcome": type(error).__name__})
    jobs = add_descriptions(unique_jobs(jobs))
    attempts.append({"method": "posting-detail-api-or-html", "samples_checked": min(2, len(jobs)), "description_chars": [len(job.get("description", "")) for job in jobs[:2]]})
    india = [job for job in jobs if confirmed_india_location(job.get("location"))]
    selected = india or jobs
    if not selected:
        label, proxy = pool.browser_proxy()
        if proxy:
            try:
                found, entry = browser_observe(url, evidence / "proxy-browser", proxy=proxy)
                entry["provider"] = label
                entry.pop("observed_feeds", None)
                entry.pop("discovered_feeds", None)
                attempts.append(entry)
                jobs.extend(found)
            except Exception as error:
                attempts.append({"method": "proxy-browser", "provider": label, "outcome": type(error).__name__})
        for render in (False, True):
            for response, entry in pool.attempts(url, render=render):
                if response is not None and response.status_code == 200:
                    found = jobs_from_html(response.text, url)
                    entry["jobs"] = len(found)
                    jobs.extend(found)
                attempts.append(entry)
                if jobs:
                    break
            if jobs:
                break
        jobs = add_descriptions(unique_jobs(jobs))
        india = [job for job in jobs if confirmed_india_location(job.get("location"))]
        selected = india or jobs
    description_attempted = False
    if selected:
        sample = selected[0]
        if len(sample.get("description", "")) < 500:
            description_attempted = True
            try:
                _, entry = browser_observe(sample["apply_url"], evidence / "description", expected_title=sample["title"])
                details = entry.pop("details", {})
                entry.pop("observed_feeds", None)
                entry.pop("discovered_feeds", None)
                entry["method"] = "browser-description"
                for key, value in details.items():
                    if not sample.get(key) or key != "description" or len(value) > len(sample.get(key, "")):
                        sample[key] = value
                entry["description_chars"] = len(sample.get("description", ""))
                attempts.append(entry)
            except Exception as error:
                attempts.append({"method": "browser-description", "outcome": type(error).__name__})
        if len(sample.get("description", "")) < 500:
            for render in (False, True):
                for response, entry in pool.attempts(sample["apply_url"], render=render):
                    if response is not None and response.status_code == 200:
                        sample.update(description_from_html(response.text, sample["apply_url"], sample["title"]))
                    entry["purpose"] = "description"
                    entry["description_chars"] = len(sample.get("description", ""))
                    attempts.append(entry)
                    if len(sample.get("description", "")) >= 500:
                        break
                if len(sample.get("description", "")) >= 500:
                    break
    else:
        sample = None
    has_description = bool(sample and len(sample.get("description", "")) >= 150 and not sample.get("description", "").rstrip().endswith(("...", "…")))
    state = "india_job_description" if india and has_description else "india_job_missing_description" if india else "job_location_unconfirmed" if sample else "unresolved"
    result = {**company, "state": state, "checked_at": datetime.now(timezone.utc).isoformat(), "seconds": round(time.monotonic() - started, 2), "attempts": attempts, "jobs_found": len(jobs), "india_jobs_found": len(india), "description_found": has_description, "description_browser_attempted": description_attempted, "sample": sample, "validated_feeds": validated_feeds}
    write_json(output / f"{company['id']}.json", result)
    return result


def summarize(output, companies):
    rows = [load_json(output / f"{c['id']}.json", c) for c in companies]
    write_json(output / "monitor.json", {"companies": rows})
    lines = ["# Live company investigation monitor", "", "| Company | Career URL | Previous source results | Current result | Jobs / India | Description | Methods attempted |", "|---|---|---|---|---|---|---|"]
    for row in rows:
        previous = ", ".join(f"{s['engine']} {s['previous_status']}" for s in row["sources"])
        methods = ", ".join(a["method"] for a in row.get("attempts", [])) or "Pending"
        cells = [row["company"], row["career_url"], previous, row["state"], f"{row.get('jobs_found', 0)} / {row.get('india_jobs_found', 0)}", str(row.get("description_found", False)), methods]
        lines.append("| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |")
    (output / "monitor.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--health")
    parser.add_argument("--worker")
    parser.add_argument("--only", default="")
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    inventory = load_json(ROOT / "docs/audits/company-investigation-monitor.json", {})["companies"]
    if args.worker:
        company = next(item for item in inventory if item["id"] == args.worker)
        pool = ProxyPool(load_json(Path(args.health), {}) if args.health else {})
        investigate(company, output, pool)
        return
    names = {name.strip().lower() for name in args.only.split(",") if name.strip()}
    companies = [company for index, company in enumerate(inventory) if index % args.shards == args.shard and (not names or company["company"].lower() in names)]
    unfinished = {"pending", "in_progress", "worker_error", "time_budget_reached"}
    pending = [company for company in companies if not args.resume or not (output / f"{company['id']}.json").exists() or load_json(output / f"{company['id']}.json", company).get("state") in unfinished]

    def run(company):
        command = [sys.executable, str(Path(__file__).resolve()), "--output", str(output), "--worker", company["id"]]
        if args.health:
            command.extend(["--health", args.health])
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=os.name != "nt")
        failure = None
        try:
            process.wait(timeout=args.timeout)
            if process.returncode != 0:
                failure = "worker_error"
        except subprocess.TimeoutExpired:
            failure = "time_budget_reached"
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        if failure:
            partial = load_json(output / f"{company['id']}.json", company)
            partial["state"] = failure
            partial.setdefault("attempts", []).append({"method": "worker", "outcome": failure})
            write_json(output / f"{company['id']}.json", partial)
        result = load_json(output / f"{company['id']}.json", company)
        print(f"{company['company']}: {result['state']}; description={result.get('description_found', False)}", flush=True)
        return result

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run, company) for company in pending]
        for future in as_completed(futures):
            future.result()
            summarize(output, companies)
    summarize(output, companies)


if __name__ == "__main__":
    main()
