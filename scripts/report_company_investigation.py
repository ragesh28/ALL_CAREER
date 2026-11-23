"""Merge audit artifacts into a durable, credential-free employer monitor."""
import argparse
import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from scripts.company_job_details import confirmed_india_location
from scripts.company_recovery import NAVIGATION, posting_url, safe_url
from scripts.company_sources import configuration

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def clean_sample(sample):
    if not sample:
        return None
    sample = deepcopy(sample)
    description = sample.pop("description", "")
    if description:
        sample["description_chars"] = len(description)
        sample["description_excerpt"] = description[:220]
    for key in ("apply_url", "url", "description_source"):
        if sample.get(key):
            sample[key] = safe_url(sample[key])
    return sample


def clean_attempt(attempt):
    result = {k: v for k, v in attempt.items() if k not in ("network", "details", "observed_feeds", "discovered_feeds")}
    for key in ("url", "final_url"):
        if result.get(key):
            result[key] = safe_url(result[key])
    return result


def usable(sample):
    return bool(sample and sample.get("title") and not NAVIGATION.search(sample["title"]) and posting_url(sample.get("apply_url") or sample.get("url") or ""))


def has_description(sample):
    if not sample:
        return False
    length = sample.get("description_chars", len(sample.get("description", "")))
    return length >= 150 and not sample.get("description", "").rstrip().endswith(("...", "…"))


def method_label(attempt):
    result = str(attempt.get("http_status") or attempt.get("outcome") or "checked")
    if "jobs" in attempt:
        result += f", {attempt['jobs']} linked records"
    if "description_chars" in attempt:
        result += f", description {attempt['description_chars']} characters"
    return f"{attempt['method']}: {result}"


def cell(value):
    return str(value or "—").replace("|", "/").replace("\n", " ")


def build(args):
    baseline = read(args.baseline)
    companies = {row["id"]: row for row in baseline["companies"]}
    source_checks = {}
    for directory in args.source_audit:
        for engine in ("direct", "md", "indeed"):
            for path in Path(directory).rglob(engine + ".json"):
                records = read(path)
                for row in records if isinstance(records, list) else records.get("companies", []):
                    row = deepcopy(row)
                    row["sample"] = clean_sample(row.get("sample"))
                    row["artifact"] = path.parent.name
                    source_checks[(row["engine"], row["index"])] = row
    for directory in args.browser:
        environment = "GitHub Actions" if "github" in str(directory).lower() else "Windows local"
        for path in sorted(Path(directory).rglob("monitor.json")):
            for incoming in read(path).get("companies", []):
                if incoming["id"] not in companies:
                    continue
                row = companies[incoming["id"]]
                history = row.setdefault("investigation_history", [])
                history.append({"pass": Path(directory).name, "environment": environment, "checked_at": incoming.get("checked_at"), "state": incoming.get("state"), "jobs_found": incoming.get("jobs_found", 0), "india_jobs_found": incoming.get("india_jobs_found", 0), "description_found": incoming.get("description_found", False)})
                for key in ("state", "checked_at", "seconds", "jobs_found", "india_jobs_found", "description_found", "description_browser_attempted"):
                    row[key] = incoming.get(key)
                row["attempts"] = [clean_attempt(attempt) for attempt in incoming.get("attempts", [])]
                row["sample"] = clean_sample(incoming.get("sample"))
                row["validated_feeds"] = [{"url": safe_url(f["url"]), "method": f.get("method", "GET")} for f in incoming.get("validated_feeds", [])]
                row["latest_investigation_environment"] = environment
    for row in companies.values():
        config = configuration(row["company"]) or {}
        row["career_url"] = config.get("career_url") or row["career_url"]
        current = []
        for source in row["sources"]:
            result = source_checks.get((source["engine"], source["index"]))
            if result:
                source["current_status"] = result["status"]
                source["current_description"] = has_description(result.get("sample"))
                current.append(result)
        row["current_source_checks"] = current
        evidence = [s for s in [row.get("sample")] + [r.get("sample") for r in current] if usable(s)]
        india = [s for s in evidence if confirmed_india_location(s.get("location"))]
        row["verified_india_sample"] = bool(india)
        row["verified_india_description"] = any(has_description(s) for s in india)
        row["overall_status"] = "working_with_description" if row["verified_india_description"] else "working_description_missing" if india else "location_unconfirmed_or_foreign" if evidence else "no_sample_recovered"
        if india:
            row["representative_sample"] = max(india, key=lambda s: s.get("description_chars", 0))
            row["remaining_reason"] = "India sample and posting-specific description verified." if row["verified_india_description"] else "India listing retrieved; the checked posting detail did not yield a usable description."
        elif evidence:
            row["representative_sample"] = max(evidence, key=lambda s: s.get("description_chars", 0))
            row["remaining_reason"] = "A linked listing was retrieved, but its sample location is foreign or cannot be confirmed as India."
        else:
            row["representative_sample"] = None
            failed = [method_label(a) for a in row.get("attempts", []) if a.get("http_status", 200) != 200 or a.get("outcome")]
            row["remaining_reason"] = "No usable linked sample recovered in the bounded searches. " + ("; ".join(failed[-5:]) if failed else "Public pages rendered but no supported linked posting was parsed; inspect the captured network evidence for a new adapter.")
        row["configured_public_feeds"] = [{"url": safe_url(f["url"]), "method": f.get("method", "GET")} for f in config.get("feeds", [])]
    rows = sorted(companies.values(), key=lambda r: r["company"].casefold())
    counts = Counter(row["overall_status"] for row in rows)
    summary = {"employers": len(rows), "configured_source_entries": sum(len(r["sources"]) for r in rows), "source_entries_retested": len(source_checks), "company_results": dict(counts), "engines": {}}
    for engine in ("direct", "md", "indeed"):
        checks = [r for r in source_checks.values() if r["engine"] == engine]
        summary["engines"][engine] = {"checked": len(checks), "linked_samples": sum(r["status"] == "sample_found" and usable(r.get("sample")) for r in checks), "descriptions": sum(usable(r.get("sample")) and has_description(r.get("sample")) for r in checks)}
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    health = read(args.health) if getattr(args, "health", None) else {}
    result = {"started": baseline.get("started"), "phase": "investigation_complete_with_documented_gaps", "generated_at": datetime.now(timezone.utc).isoformat(), "summary": summary, "workflow_runs": args.run_url, "provider_health": health, "companies": rows}
    (output / "company-investigation-monitor.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Company investigation results", "", "Checked 23 November 2026. These are bounded live samples, not a claim that every job, application form, or historical listing was verified.", "", f"**{len(rows)} employer names, {summary['configured_source_entries']} overlapping company/source entries.**", "", "| Employer result | Count |", "|---|---:|"]
    lines += [f"| {status.replace('_', ' ')} | {count} |" for status, count in counts.items()]
    lines += ["", "| Production engine | Entries retested | Linked sample returned | Usable sample description |", "|---|---:|---:|---:|"]
    for engine, stat in summary["engines"].items():
        lines.append(f"| {engine} | {stat['checked']} | {stat['linked_samples']} | {stat['descriptions']} |")
    lines += ["", "An empty Indeed search uses an India/72-hour/five-result scope and does not mean the employer has no openings. A first global page can contain no India jobs. Remote-only and missing locations are not counted as confirmed India. Salary, experience and posted date remain 'not extracted' unless explicitly supplied by the source. A title/link sample does not test the application form. Description coverage refers to checked samples; extra detail retrieval is bounded to protect workflow runtime.", "", "## Verification runs", ""]
    lines += [f"- [GitHub Actions run {url.rsplit('/', 1)[-1]}]({url})" for url in args.run_url]
    if health:
        lines += ["", "## Configured provider checks", "", "These are authentication/connectivity/account checks at run time. A healthy provider can still fail to retrieve a particular website. Credential values are excluded.", "", "| Provider label | Available | HTTP / proxy status | Observed reason / credits |", "|---|---|---|---|"]
        for provider, check in health.items():
            reason = check.get("reason", "")
            if "remaining" in check:
                reason += f"; {check['remaining']} credits remaining at this check"
            lines.append(f"| {provider} | {check.get('available', False)} | {cell(check.get('http_status') or check.get('proxy_http_status'))} | {cell(reason)} |")
    lines += ["", "## Every employer", "", "| Company | Current result | Browser records / confirmed India | Description characters | Remaining finding |", "|---|---|---:|---:|---|"]
    for row in rows:
        sample = row["representative_sample"] or {}
        lines.append(f"| [{cell(row['company'])}]({safe_url(row['career_url'])}) | {row['overall_status'].replace('_', ' ')} | {row.get('jobs_found', 0)} / {row.get('india_jobs_found', 0)} | {sample.get('description_chars', 0)} | {cell(row['remaining_reason'])} |")
    lines += ["", "## Methods and evidence by employer", ""]
    for row in rows:
        lines += [f"### {row['company']}", "", f"Career page: [{row['company']}]({safe_url(row['career_url'])}). Result: **{row['overall_status'].replace('_', ' ')}**.", "", row["remaining_reason"], "", "| Configured source | Previous sample state | Current state | Description |", "|---|---|---|---|"]
        for source in row["sources"]:
            lines.append(f"| {source['engine']}: {cell(source['company_label'])} | {source['previous_status']} | {source.get('current_status', 'not retested')} | {source.get('current_description', False)} |")
        lines += ["", "Methods in the latest browser/API investigation:", ""]
        for attempt in row.get("attempts", []):
            label = method_label(attempt)
            lines.append(f"- [x] {label}" + (f" — [endpoint]({safe_url(attempt['url'])})" if attempt.get("url") else ""))
        if not row.get("validated_feeds"):
            lines.append("- No reusable public listing API was verified during this visit; configured alternatives and source-engine checks are shown separately.")
        sample = row["representative_sample"]
        if sample:
            url = sample.get("apply_url") or sample.get("url")
            lines += ["", f"Sample: [{cell(sample['title'])}]({safe_url(url)}). Location: {cell(sample.get('location'))}. Description: {sample.get('description_chars', 0)} characters.", "", f"Experience: {cell(sample.get('experience') or 'not extracted')}. Salary: {cell(sample.get('salary') or 'not extracted')}. Posted date: {cell(sample.get('date_posted') or sample.get('posted') or sample.get('date') or 'not extracted')}."]
        lines.append("")
    (output / "company-investigation-results.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default=str(ROOT / "docs/audits/company-investigation-monitor.json"))
    parser.add_argument("--browser", action="append", default=[])
    parser.add_argument("--source-audit", action="append", default=[])
    parser.add_argument("--run-url", action="append", default=[])
    parser.add_argument("--health")
    parser.add_argument("--output", default=str(ROOT / "docs/audits"))
    build(parser.parse_args())
