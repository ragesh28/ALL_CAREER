"""Preserve public job details and recover them from individual posting pages.

No AI credentials are needed. Missing fields remain missing. The description
budget bounds extra requests per company, not the number of jobs saved.
"""
import html
import inspect
import json
import os
import re
import time
from functools import lru_cache
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

DETAIL_KEYS = ("description", "experience", "salary", "job_type", "work_mode",
               "employment_type", "date_posted", "description_source")
_detail_seconds_used = 0.0


def is_india_location(location):
    value = text(location).lower()
    if not value:
        return True  # Keep unknown locations available, as the existing store does.
    if re.search(r"\b(?:india|bangalore|bengaluru|chennai|hyderabad|mumbai|pune|noida|gurgaon|gurugram|delhi|kolkata|coimbatore|ahmedabad|karnataka|maharashtra|telangana|tamil nadu|haryana)\b", value):
        return True
    # A foreign location containing 'Remote' is not an India opening.
    return value.strip(" ,-") in ("remote", "ind", "in")


def confirmed_india_location(location):
    """Unlike the storage policy, an unknown/remote-only location is not proof."""
    value = text(location)
    return bool(value and value.lower().strip(" ,-") != "remote" and is_india_location(value))


def location_text(value):
    """Keep explicit city/country values from ATS objects and multi-site lists."""
    if isinstance(value, list):
        return "; ".join(dict.fromkeys(filter(None, (location_text(v) for v in value))))
    if not isinstance(value, dict):
        return text(value)
    if isinstance(value.get("address"), dict):
        return location_text(value["address"])
    parts = []
    for names in (("addressLocality", "city"), ("addressRegion", "region", "state"), ("addressCountry", "country", "countryName")):
        part = next((value[k] for k in names if value.get(k)), "")
        if isinstance(part, dict):
            part = part.get("name") or part.get("code") or ""
        if names[0] == "addressCountry" and text(part).casefold() in ("in", "ind"):
            part = "India"
        if text(part):
            parts.append(text(part))
    return ", ".join(dict.fromkeys(parts)) or text(value.get("location") or value.get("name") or value.get("label"))


def upgrade_details(existing, incoming):
    changed = False
    for key, value in details_from_record(incoming).items():
        if not existing.get(key) or (key == "description" and len(value) > len(existing[key])):
            existing[key] = value
            changed = True
    return changed


def text(value):
    if value is None or isinstance(value, (dict, list)):
        return ""
    value = str(value)
    if value.lower().strip() in ("nan", "none", "null", "nat"):
        return ""
    value = html.unescape(value)
    if "<" in value and ">" in value:
        value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return re.sub(r"[ \t]+", " ", value).strip()


def inline_job_data(soup):
    """Decode public JSON.parse string literals without executing JavaScript."""
    decoder = re.compile(r"\\(?:x([0-9a-fA-F]{2})|u([0-9a-fA-F]{4})|([\s\S]))")
    def unescape(match):
        if match[1] or match[2]:
            return chr(int(match[1] or match[2], 16))
        return {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}.get(match[3], match[3])
    for script in soup.find_all("script", src=False):
        for match in re.finditer(r"\b(?:var\s+)?jobs\s*=\s*JSON\.parse\('((?:\\.|[^'\\])*)'\)", script.string or ""):
            try:
                yield json.loads(decoder.sub(unescape, match[1]))
            except (ValueError, TypeError):
                continue


def public_request(method, url, **kwargs):
    """Use the normal client first; Workday also needs a browser TLS client on CI.

    One alternate client is attempted only for public Workday URLs, and never
    when the server supplies Retry-After. This does not use a login or disable TLS.
    """
    response = requests.request(method, url, **kwargs)
    host = urlparse(url).hostname or ""
    if host.endswith(".myworkdayjobs.com") and response.status_code in (403, 429) and not response.headers.get("Retry-After"):
        try:
            from curl_cffi import requests as browser_http
            alternate = browser_http.request(method, url, impersonate="chrome", **kwargs)
            if alternate.status_code == 200:
                alternate.career_http_client = "curl_cffi-chrome"
                return alternate
        except Exception:
            pass
    return response


def wipro_details(soup):
    nodes = [node for node in soup.select(".joblayouttoken") if re.search(r"\bJob Description\b", node.get_text(" ", strip=True), re.I)]
    if not nodes:
        return {}
    result = details_from_record({"description": max(nodes, key=lambda n: len(n.get_text())).get_text(" ", strip=True)})
    posted = re.search(r"Posting Start Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", soup.get_text(" ", strip=True))
    if posted:
        from datetime import datetime
        for fmt in ("%m/%d/%y", "%m/%d/%Y"):
            try:
                result["date_posted"] = datetime.strptime(posted[1], fmt).date().isoformat()
                break
            except ValueError:
                continue
    return result


def normalize_job_links(jobs, page_url):
    for job in jobs:
        if not isinstance(job, dict):
            continue
        link = text(job.get("apply_url") or job.get("url"))
        navigation = text(job.get("title")).lower() in ("skip to main content", "skip to content", "view all jobs", "search jobs", "careers", "job search")
        if navigation or not link or link.startswith("#") or urlparse(link).fragment in ("main", "main-content", "content", "top") or urlparse(link).scheme not in ("", "http", "https"):
            job["apply_url"] = ""
            job["url"] = ""
        else:
            job["apply_url"] = urljoin(page_url, link)
    return jobs


def details_from_record(record):
    result = {key: text(record.get(key)) for key in DETAIL_KEYS if text(record.get(key))}
    for key in ("jobDescription", "job_description", "descriptionHtml", "descriptionPlain", "Job_Description", "content", "ExternalDescriptionStr"):
        if not result.get("description") and text(record.get(key)):
            result["description"] = text(record[key])
    salary = record.get("baseSalary") or record.get("salaryRange")
    if not result.get("salary") and isinstance(salary, dict):
        value = salary.get("value", salary)
        if isinstance(value, dict):
            low, high = value.get("minValue"), value.get("maxValue")
            if low is not None or high is not None:
                result["salary"] = " ".join(str(v) for v in (salary.get("currency"), low, "–" if high is not None else None, high, value.get("unitText")) if v is not None)
    if not result.get("salary") and (text(record.get("min_amount")) or text(record.get("max_amount"))):
        result["salary"] = " ".join(filter(None, [text(record.get("currency")), text(record.get("min_amount")), "to" if text(record.get("max_amount")) else "", text(record.get("max_amount")), text(record.get("interval"))]))
    if not result.get("date_posted") and (record.get("datePosted") or record.get("publishedAt")):
        result["date_posted"] = text(record.get("datePosted") or record["publishedAt"])
    if not result.get("job_type") and record.get("employmentType"):
        result["job_type"] = text(record["employmentType"])
    if not result.get("job_type") and text(record.get("timeType")):
        result["job_type"] = text(record["timeType"])
    if not result.get("date_posted") and (record.get("jobPostingId") or record.get("jobReqId")) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text(record.get("startDate"))):
        result["date_posted"] = text(record["startDate"])
    location = location_text(record.get("jobLocation") or record.get("location") or record.get("locations"))
    if location:
        result["location"] = location
    if record.get("minimumExperienceInYears") is not None:
        low, high = record["minimumExperienceInYears"], record.get("maximumExperienceInYears")
        result.setdefault("experience", f"{low}-{high} years" if high is not None else f"Minimum {low} years")
    if not result.get("date_posted") and record.get("postedTs"):
        from datetime import datetime, timezone
        try:
            result["date_posted"] = datetime.fromtimestamp(float(record["postedTs"]), timezone.utc).date().isoformat()
        except (ValueError, TypeError, OverflowError, OSError):
            pass
    desc = result.get("description", "")
    if not result.get("experience"):
        match = re.search(r"\b(?:minimum\s+(?:of\s+)?)?\d{1,2}\s*(?:[-–—]|to)\s*\d{1,2}\s*years?\s*(?:of\s+)?(?:relevant\s+|professional\s+|work\s+)?experience\b", desc, re.I)
        if not match:
            match = re.search(r"\b(?:at least\s+|minimum\s+(?:of\s+)?)\d{1,2}\+?\s*years?\s*(?:of\s+)?(?:relevant\s+|professional\s+|work\s+)?experience\b", desc, re.I)
        if match:
            result["experience"] = match.group(0)
    return result


def jobs_from_payload(payload, base_url):
    """Extract actual linked postings, rather than treating a total as jobs."""
    jobs, seen = [], set()
    def visit(value):
        if isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, dict):
            title = next((text(value.get(k)) for k in ("title", "jobTitle", "Title", "postingTitle", "JobTitle", "name") if text(value.get(k))), "")
            link = next((text(value.get(k)) for k in ("apply_url", "url", "jobUrl", "absolute_url", "absoluteUrl", "positionUrl", "job_url", "hostedUrl", "applyUrl") if text(value.get(k))), "")
            if title == text(value.get("name")) and not any(value.get(k) for k in ("title", "jobTitle", "Title", "postingTitle", "JobTitle", "positionUrl", "jobUrl", "hostedUrl", "jobDescription", "jobAd")):
                title = ""
            if title and link:
                url = urljoin(base_url, link)
                if url not in seen:
                    seen.add(url)
                    location = next((value.get(k) for k in ("location", "locationsText", "locations", "PrimaryLocation", "jobLocation") if value.get(k)), "")
                    if isinstance(location, list):
                        location = ", ".join(text(x.get("name")) if isinstance(x, dict) else text(x) for x in location)
                    if isinstance(location, dict):
                        location = location.get("name", "")
                    jobs.append({"title": title, "apply_url": url, "location": text(location), "posted": text(value.get("datePosted") or value.get("postedDate") or value.get("publishedDate")), **details_from_record(value)})
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child)
    visit(payload)
    return jobs


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
    if parsed.hostname == "higher.gs.com":
        identifier = re.search(r"/roles/(\d+)", parsed.path)
        if identifier:
            try:
                # This query and external-source ID were observed on the public
                # career site. Its internal roleId suffix is not a browser URL.
                query = "query GetRoleById($externalSourceId: String!, $externalSourceFetch: Boolean) { role(externalSourceId: $externalSourceId, externalSourceFetch: $externalSourceFetch) { jobTitle descriptionHtml locations { city state country } compensation { minSalary maxSalary currency } } }"
                import uuid
                response = requests.post("https://api-higher.gs.com/gateway/api/v1/graphql", headers={"User-Agent": "Mozilla/5.0", "Origin": "https://higher.gs.com", "Referer": "https://higher.gs.com/", "x-higher-session-id": str(uuid.uuid4())}, json={"operationName": "GetRoleById", "variables": {"externalSourceId": identifier[1], "externalSourceFetch": True}, "query": query}, timeout=(5, 15))
                role = response.json().get("data", {}).get("role") if response.status_code == 200 else None
                if isinstance(role, dict):
                    details = details_from_record(role)
                    compensation = role.get("compensation") or {}
                    if compensation.get("minSalary") is not None or compensation.get("maxSalary") is not None:
                        details.update(details_from_record({"baseSalary": {"currency": compensation.get("currency"), "value": {"minValue": compensation.get("minSalary"), "maxValue": compensation.get("maxSalary")}}}))
                    if details.get("description"):
                        return {**details, "description_source": f"https://higher.gs.com/roles/{identifier[1]}"}
            except (requests.RequestException, ValueError, TypeError):
                pass
    if parsed.hostname == "careers.turing.com":
        identifier = re.search(r"/job/(\d+)", parsed.path)
        if identifier:
            candidates.insert(0, f"https://careers.turing.com/api/v3/job-posts/{identifier.group(1)}")
    microsoft = parsed.hostname == "apply.careers.microsoft.com" and re.search(r"/careers/job/(\d+)", parsed.path)
    if microsoft:
        candidates.insert(0, f"https://{parsed.netloc}/api/pcsx/position_details?position_id={microsoft.group(1)}&domain=microsoft.com")
    domains = {"careers.qualcomm.com": "qualcomm.com", "jobs.ericsson.com": "ericsson.com"}
    eightfold = re.search(r"/careers/job/(\d+)", parsed.path)
    if eightfold and parsed.hostname in domains:
        candidates.insert(0, f"https://{parsed.netloc}/api/pcsx/position_details?position_id={eightfold.group(1)}&domain={domains[parsed.hostname]}")
    greenhouse = parsed.hostname in ("job-boards.greenhouse.io", "boards.greenhouse.io") and re.match(r"/([^/]+)/jobs/(\d+)", parsed.path)
    if greenhouse:
        candidates.insert(0, f"https://boards-api.greenhouse.io/v1/boards/{greenhouse.group(1)}/jobs/{greenhouse.group(2)}?content=true")
    oracle = parsed.hostname.endswith("oraclecloud.com") and re.search(r"/job/(\d+)", parsed.path)
    if oracle:
        candidates.insert(0, f"https://{parsed.netloc}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?finder=ById;Id={oracle.group(1)}")
    smart = parsed.hostname == "jobs.smartrecruiters.com" and re.match(r"/([^/]+)/(\d+)", parsed.path)
    if smart:
        candidates.insert(0, f"https://api.smartrecruiters.com/v1/companies/{smart.group(1)}/postings/{smart.group(2)}")
    if parsed.hostname.endswith("myworkdayjobs.com"):
        parts = [p for p in parsed.path.split("/") if p]
        if parts and parts[-1] == "apply":
            parts.pop()
        if "job" in parts and len(parts) > 2:
            idx = parts.index("job")
            site = parts[idx - 1]
            tenant = parsed.hostname.split(".")[0]
            candidates.insert(0, f"https://{parsed.netloc}/wday/cxs/{tenant}/{site}/" + "/".join(parts[idx:]))
    for candidate in candidates:
        try:
            if (urlparse(candidate).hostname or "").endswith(".myworkdayjobs.com"):
                response = public_request("GET", candidate, headers=headers, timeout=(5, 15))
            else:
                response = requests.get(candidate, headers=headers, timeout=(5, 15))
            if response.status_code != 200:
                continue
            if "json" in response.headers.get("Content-Type", ""):
                raw = response.json()
                record = raw.get("jobPostingInfo", raw.get("data", raw)) if isinstance(raw, dict) else {}
                if isinstance(record, dict) and isinstance(record.get("items"), list) and record["items"]:
                    record = record["items"][0]
                if not isinstance(record, dict):
                    continue
                sections = record.get("jobAd", {}).get("sections", {})
                if isinstance(sections, dict):
                    blocks = [text(sections.get(key, {}).get("text")) for key in ("jobDescription", "qualifications", "additionalInformation") if isinstance(sections.get(key), dict)]
                    if any(blocks):
                        record = {**record, "description": "\n".join(filter(None, blocks))}
                details = details_from_record(record)
                if record.get("ExternalQualificationsStr"):
                    details["description"] = " ".join(filter(None, [details.get("description"), text(record["ExternalQualificationsStr"])]))
                if details.get("description"):
                    return {**details, "description_source": candidate}
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            if parsed.hostname == "careers.zohocorp.com":
                for records in inline_job_data(soup):
                    for row in records if isinstance(records, list) else []:
                        if str(row.get("id", "")) in parsed.path.split("/"):
                            details = details_from_record(row)
                            if details.get("description"):
                                return {**details, "description_source": candidate}
            if parsed.hostname == "careers.wipro.com" and re.search(r"/jobs?/", parsed.path):
                details = wipro_details(soup)
                if details:
                    return {**details, "description_source": candidate}
                continue  # The generic company introduction is not a role description.
            if parsed.hostname == "jobs.siemens.com" and "/JobDetail/" in parsed.path:
                nodes = soup.select("article.article--details .article__content__view")
                node = max(nodes, key=lambda n: len(n.get_text()), default=None)
                if node:
                    details = details_from_record({"description": node.get_text(" ", strip=True)})
                    posted = re.search(r"Posted since\s+(\d{1,2}-[A-Za-z]{3}-\d{4})", soup.get_text(" ", strip=True))
                    if posted:
                        details["date_posted"] = posted.group(1)
                    return {**details, "description_source": candidate}
            if parsed.hostname in ("www.google.com", "google.com") and "/careers/applications/jobs/results/" in parsed.path:
                sections = []
                for heading in soup.find_all(["h2", "h3"]):
                    label = heading.get_text(" ", strip=True).lower().rstrip(":")
                    if label in ("minimum qualifications", "preferred qualifications", "about the job", "responsibilities"):
                        sections.append(heading.parent.get_text(" ", strip=True))
                description = "\n".join(sections)
                if len(description) >= 100:
                    return {**details_from_record({"description": description}), "description_source": candidate}
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
    global _detail_seconds_used
    remaining = int(os.environ.get("COMPANY_DETAIL_LIMIT", "3")) if limit is None else limit
    budget = float(os.environ.get("COMPANY_DETAIL_BUDGET_SECONDS", "180"))
    for job in jobs:
        job.update(details_from_record(job))
        if (not job.get("description") or job["description"].rstrip().endswith(("...", "…"))) and remaining > 0 and _detail_seconds_used < budget:
            url = job.get("apply_url") or job.get("url") or ""
            if url:
                remaining -= 1
                started = time.monotonic()
                try:
                    recovered = fetch_details(url)
                finally:
                    _detail_seconds_used += time.monotonic() - started
                for key, value in recovered.items():
                    if not job.get(key) or (key == "description" and len(value) > len(job.get(key, ""))):
                        job[key] = value
    return jobs
