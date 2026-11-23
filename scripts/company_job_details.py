"""Preserve public job details and recover them from individual posting pages.

No AI credentials are needed. Missing fields remain missing. The description
budget bounds extra requests per company, not the number of jobs saved.
"""
import html
import inspect
import os
import re
from functools import lru_cache
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

DETAIL_KEYS = ("description", "experience", "salary", "job_type", "work_mode",
               "employment_type", "date_posted", "description_source")


def text(value):
    if value is None or isinstance(value, (dict, list)):
        return ""
    value = str(value)
    if value.lower().strip() in ("nan", "none", "null", "nat"):
        return ""
    return re.sub(r"[ \t]+", " ", BeautifulSoup(html.unescape(value), "html.parser").get_text(" ", strip=True)).strip()


def details_from_record(record):
    result = {key: text(record.get(key)) for key in DETAIL_KEYS if text(record.get(key))}
    for key in ("jobDescription", "job_description", "descriptionHtml", "descriptionPlain", "content"):
        if not result.get("description") and text(record.get(key)):
            result["description"] = text(record[key])
    salary = record.get("baseSalary") or record.get("salaryRange")
    if not result.get("salary") and isinstance(salary, dict):
        value = salary.get("value", salary)
        if isinstance(value, dict):
            low, high = value.get("minValue"), value.get("maxValue")
            if low is not None or high is not None:
                result["salary"] = " ".join(str(v) for v in (salary.get("currency"), low, "–" if high is not None else None, high, value.get("unitText")) if v is not None)
    if not result.get("date_posted") and record.get("datePosted"):
        result["date_posted"] = text(record["datePosted"])
    if not result.get("job_type") and record.get("employmentType"):
        result["job_type"] = text(record["employmentType"])
    desc = result.get("description", "")
    if not result.get("experience"):
        match = re.search(r"\b(?:minimum\s+(?:of\s+)?)?\d{1,2}\s*(?:[-–—]|to)\s*\d{1,2}\s*years?\s*(?:of\s+)?(?:relevant\s+|professional\s+|work\s+)?experience\b", desc, re.I)
        if not match:
            match = re.search(r"\b(?:at least\s+|minimum\s+(?:of\s+)?)\d{1,2}\+?\s*years?\s*(?:of\s+)?(?:relevant\s+|professional\s+|work\s+)?experience\b", desc, re.I)
        if match:
            result["experience"] = match.group(0)
    return result


def jobspy_options(scrape_function, proxies=None):
    """Support the installed JobSpy release without passing unknown keywords."""
    params = inspect.signature(scrape_function).parameters
    result = {}
    if "fetch_description" in params:
        result["fetch_description"] = True
    elif "linkedin_fetch_description" in params:
        result["linkedin_fetch_description"] = True
    if proxies and "proxies" in params:
        result["proxies"] = proxies
    return result


def _jobpostings(value):
    if isinstance(value, list):
        for item in value:
            yield from _jobpostings(item)
    elif isinstance(value, dict):
        kind = value.get("@type", [])
        if kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind):
            yield value
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from _jobpostings(child)


@lru_cache(maxsize=2048)
def fetch_details(url):
    """Only accept job-specific structured data or known description containers."""
    import json
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return {}
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/html"}
    candidates = [url]
    if parsed.hostname.endswith("myworkdayjobs.com"):
        parts = [p for p in parsed.path.split("/") if p]
        if "job" in parts and len(parts) > 2:
            idx = parts.index("job")
            site = parts[idx - 1]
            tenant = parsed.hostname.split(".")[0]
            candidates.insert(0, f"https://{parsed.netloc}/wday/cxs/{tenant}/{site}/" + "/".join(parts[idx:]))
    for candidate in candidates:
        try:
            response = requests.get(candidate, headers=headers, timeout=(5, 15))
            if response.status_code != 200:
                continue
            if "json" in response.headers.get("Content-Type", ""):
                raw = response.json()
                record = raw.get("jobPostingInfo", raw) if isinstance(raw, dict) else {}
                details = details_from_record(record)
                if details.get("description"):
                    return {**details, "description_source": candidate}
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup.select('script[type="application/ld+json"]'):
                try:
                    for job in _jobpostings(json.loads(script.string or script.get_text())):
                        # Avoid borrowing a different job's description from list pages.
                        if job.get("url") and str(job["url"]).split("?")[0].rstrip("/") != url.split("?")[0].rstrip("/"):
                            continue
                        details = details_from_record(job)
                        if details.get("description"):
                            return {**details, "description_source": candidate}
                except (ValueError, TypeError):
                    continue
            for selector in ('[itemprop="description"]', '[data-automation-id="jobPostingDescription"]', '.job-description', '#job-description', '.jobsearch-jobDescriptionText', '.jobs-description__content', '.show-more-less-html__markup', '.jobdetail-description'):
                node = soup.select_one(selector)
                description = text(node.get_text(" ", strip=True)) if node else ""
                if len(description) >= 100:
                    return {**details_from_record({"description": description}), "description_source": candidate}
        except (requests.RequestException, ValueError, TypeError):
            continue
    return {}


def enrich_jobs(jobs, limit=None):
    remaining = int(os.environ.get("COMPANY_DETAIL_LIMIT", "3")) if limit is None else limit
    for job in jobs:
        job.update(details_from_record(job))
        if not job.get("description") and remaining > 0:
            url = job.get("apply_url") or job.get("url") or ""
            if url:
                remaining -= 1
                recovered = fetch_details(url)
                for key, value in recovered.items():
                    if not job.get(key):
                        job[key] = value
    return jobs
