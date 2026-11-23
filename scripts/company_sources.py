"""Verified public career sources, bounded pagination and recovery for all engines.

Configuration contains public endpoints only. Audits never invoke storage. A
failed fallback returns no rows, leaving the original engine and saved jobs intact.
"""
import json
import os
import re
import time
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from scripts.company_job_details import confirmed_india_location, enrich_jobs, public_request
from scripts.company_recovery import HEADERS, browser_observe, jobs_from_html, public_feeds, records_from_json, safe_url, unique_jobs

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {
    "tcs (prime/digital)": "TCS", "infosys (sp/dse)": "Infosys",
    "walmart global tech": "Walmart", "sap labs": "SAP", "citibank": "Citi",
    "amazon ai": "Amazon", "juniper networks / hpe": "Juniper Networks",
}


@lru_cache(maxsize=1)
def registry():
    return json.loads((ROOT / "scripts/company_sources.json").read_text(encoding="utf-8"))


def configuration(name):
    name = re.sub(r"^\d+\.\s*", "", name).strip()
    canonical = ALIASES.get(name.casefold(), name)
    return next((row for row in registry() if row["company"].casefold() == canonical.casefold()), None)


def next_page(feed, payload, count):
    """Only paginate documented/observed listing shapes, never detail endpoints."""
    result = deepcopy(feed)
    parts = urlsplit(feed["url"])
    query = dict(parse_qsl(parts.query))
    body = result.get("payload", {})
    if "/wday/cxs/" in parts.path and parts.path.endswith("/jobs"):
        offset = int(body.get("offset", 0)) + count
        if offset >= payload.get("total", 0):
            return None
        body["offset"] = offset
    elif parts.hostname == "api.smartrecruiters.com":
        offset = int(query.get("offset", 0)) + count
        if offset >= payload.get("totalFound", 0):
            return None
        query["offset"] = str(offset)
    elif "/api/pcsx/search" in parts.path:
        if count < int(query.get("num", 10)):
            return None
        query["start"] = str(int(query.get("start", 0)) + int(query.get("num", 10)))
    elif parts.hostname == "careers.kula.ai":
        meta = payload.get("meta", {})
        if meta.get("page", 1) >= meta.get("pages", 1):
            return None
        query["page"] = str(int(query.get("page", 1)) + 1)
    elif parts.hostname == "careers.wipro.com":
        if payload.get("hasNextPage") is False or not count:
            return None
        body["pageNumber"] = int(body.get("pageNumber", 0)) + 1
    elif parts.hostname == "ibegin.tcsapps.com":
        page = payload.get("payload", {})
        if page.get("last", True):
            return None
        body["page"] = int(body.get("page", 1)) + 1
    elif "recruitingCEJobRequisitions" in parts.path:
        total = (payload.get("items") or [{}])[0].get("TotalJobsCount", 0)
        finder = query.get("finder", "")
        previous = re.search(r"(?:^|,)offset=(\d+)", finder)
        offset = (int(previous[1]) if previous else 0) + count
        if offset >= total:
            return None
        query["finder"] = re.sub(r",offset=\d+", "", finder) + f",offset={offset}"
    elif parts.hostname == "cg-jobstream-api.azurewebsites.net" and parts.path == "/api/job-search":
        page = int(query.get("page", 1))
        size = int(query.get("size", 11))
        if page * size >= payload.get("total", 0):
            return None
        query["page"] = str(page + 1)
    else:
        return None
    result["url"] = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    return result


def fetch_feed_pages(feed, limit=1000, budget=90, session=None):
    jobs, attempts = [], []
    deadline = time.monotonic() + budget
    current = deepcopy(feed)
    seen = set()
    requester = session
    while current and time.monotonic() < deadline and len(jobs) < limit:
        try:
            request = requester.request if requester else public_request
            response = request(current.get("method", "GET"), current["url"], json=current.get("payload"), headers=HEADERS, timeout=(6, min(20, max(1, deadline - time.monotonic()))))
            entry = {"method": "verified-public-api", "url": safe_url(current["url"]), "http_status": response.status_code}
            attempts.append(entry)
            if response.status_code != 200:
                break
            payload = response.json()
            found = records_from_json(payload, current["url"])
            entry["jobs"] = len(found)
            fresh = [job for job in found if job["apply_url"] not in seen]
            if not fresh:
                break
            jobs.extend(fresh)
            seen.update(job["apply_url"] for job in fresh)
            current = next_page(current, payload, len(found))
        except (requests.RequestException, ValueError, TypeError) as error:
            attempts.append({"method": "verified-public-api", "url": safe_url(current["url"]), "outcome": type(error).__name__})
            break
    ordered = sorted(unique_jobs(jobs), key=lambda job: confirmed_india_location(job.get("location")), reverse=True)
    return ordered[:limit], attempts


def browser_listing(name, url, limit=1000):
    """Use a new, unauthenticated context; request further pages in that session."""
    from playwright.sync_api import sync_playwright
    jobs, feeds = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(service_workers="block")
        page = context.new_page()
        def observe(response):
            if response.request.resource_type not in ("xhr", "fetch") or response.status != 200:
                return
            if not re.search(r"job|career|posting|position|recruit|pcsx", urlsplit(response.url).netloc + urlsplit(response.url).path, re.I):
                return
            try:
                found = records_from_json(response.json(), response.url)
                jobs.extend(found)
                if found and response.request.method in ("GET", "POST"):
                    feed = {"url": response.url, "method": response.request.method}
                    if response.request.post_data:
                        feed["payload"] = response.request.post_data_json
                    feeds.append(feed)
            except Exception:
                pass
        context.on("response", observe)
        try:
            if name == "TCS":
                with page.expect_response(lambda r: "/api/en-IN/search/jobs" in r.url, timeout=25000):
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
            else:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            jobs.extend(jobs_from_html(page.content(), page.url))
            # TCS rejects bare requests: its public API works in the career session.
            if name == "TCS":
                listings = [f for f in feeds if "/search/jobs" in f["url"]]
                feed = listings[0] if listings else None
                deadline = time.monotonic() + 60
                while feed and len(unique_jobs(jobs)) < limit and time.monotonic() < deadline:
                    response = context.request.post(feed["url"], data=feed.get("payload"), timeout=15000)
                    if response.status != 200:
                        break
                    payload = response.json()
                    found = records_from_json(payload, feed["url"])
                    if not found:
                        break
                    before = len(unique_jobs(jobs))
                    jobs.extend(found)
                    feed = next_page(feed, payload, len(found))
                    if len(unique_jobs(jobs)) == before and feed and feed.get("payload", {}).get("page", 1) != 2:
                        break
                for job in unique_jobs(jobs)[:int(os.environ.get("COMPANY_DETAIL_LIMIT", "3"))]:
                    identifier = job["apply_url"].rstrip("/").split("/")[-1].rstrip("J")
                    detail = context.request.get(f"https://ibegin.tcsapps.com/candidate/next/api/en-IN/job/desc/{identifier}", timeout=15000)
                    if detail.status == 200:
                        from scripts.company_job_details import details_from_record
                        job.update(details_from_record(detail.json().get("payload", {})))
                    else:
                        # Some edge deployments reject the APIRequestContext TLS
                        # client even with cookies. Navigate the public detail page
                        # and read the response made by the actual browser.
                        try:
                            with page.expect_response(lambda r: f"/job/desc/{identifier}" in r.url, timeout=15000) as pending:
                                page.goto(job["apply_url"], wait_until="domcontentloaded", timeout=25000)
                            payload = pending.value.json().get("payload", {})
                            from scripts.company_job_details import details_from_record
                            job.update(details_from_record(payload))
                        except Exception:
                            pass
        finally:
            context.close()
            browser.close()
    return unique_jobs(jobs)[:limit]


def scrape_verified_company(name, limit=1000, allow_browser=True):
    config = configuration(name)
    if not config:
        return []
    sample_limit = int(os.environ.get("COMPANY_SAMPLE_LIMIT", limit))
    limit = max(1, min(limit, sample_limit))
    jobs = []
    for feed in config.get("feeds", []):
        found, _ = fetch_feed_pages(feed, limit=limit, budget=60)
        jobs.extend(found)
        if any(confirmed_india_location(job.get("location")) for job in jobs):
            break
    browser_url = config["career_url"]
    workday = next((feed for feed in config.get("feeds", []) if "/wday/cxs/" in feed["url"]), None)
    if workday:
        parsed = urlsplit(workday["url"])
        site = parsed.path.strip("/").split("/")[3]
        browser_url = f"{parsed.scheme}://{parsed.netloc}/{site}"
    if not jobs and allow_browser and (config.get("browser_verified") or workday):
        try:
            jobs = browser_listing(config["company"], browser_url, limit)
        except Exception as error:
            print(f"    Public career browser: {type(error).__name__}")
    # Never turn a fallback failure or HTTP 200 landing page into a job.
    for job in jobs:
        job.setdefault("company", name)
        job.setdefault("url", job["apply_url"])
        job.setdefault("source", "company_careers")
    jobs = sorted(unique_jobs(jobs), key=lambda job: confirmed_india_location(job.get("location")), reverse=True)
    return enrich_jobs(jobs)[:limit]
