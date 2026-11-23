"""Public career-page, observed API and browser recovery shared by company scrapers."""
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup

from scripts.company_job_details import details_from_record, fetch_details, is_india_location, normalize_job_links, text

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/html,*/*"}
NAVIGATION = re.compile(r"^(?:search|view|browse|all|find|explore|join|sign|learn|skip|career|job alert|privacy|cookie|apply now|read more|current openings|open positions)(?:\b|$)", re.I)


def safe_url(url):
    parts = urlsplit(url)
    if parts.username or parts.password:
        return "[credentialed endpoint]"
    query = [(key, value) for key, value in parse_qsl(parts.query) if not re.search(r"token|api.?key|secret|auth|password|signature", key, re.I)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def scalar(value):
    if isinstance(value, list):
        return ", ".join(filter(None, [scalar(item) for item in value]))
    if isinstance(value, dict):
        return scalar(value.get("name") or value.get("label") or value.get("city") or value.get("addressLocality"))
    return text(value)


def first(record, keys):
    for key in keys:
        value = scalar(record.get(key))
        if value:
            return value
    return ""


def posting_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or parsed.fragment in ("main", "content"):
        return False
    path = parsed.path.lower().strip("/")
    if not path or path in ("careers", "jobs", "careers/search", "job-search", "search-results"):
        return False
    return bool(re.search(r"job(?:s|detail)?[/_-].+|/posting|/position|/requisition|/roles/|/vacan|/opening|careers/.+|/\d{4,}|[a-f0-9]{8}-[a-f0-9-]{20,}", "/" + path))


def records_from_json(payload, source_url):
    jobs = []
    seen = set()
    parsed = urlsplit(source_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    def visit(value):
        if isinstance(value, list):
            for child in value:
                visit(child)
            return
        if not isinstance(value, dict):
            return
        row = value.get("response") if isinstance(value.get("response"), dict) else value
        title = first(row, ("title", "jobTitle", "Title", "postingTitle", "unifiedStandardTitle", "JobTitle", "name", "text"))
        link = first(row, ("jobUrl", "jobURL", "postingUrl", "absolute_url", "absoluteUrl", "positionUrl", "canonicalPositionUrl", "careerSiteUrl", "hostedUrl", "apply_url", "url", "URL", "applyUrl", "jcrURL", "externalPath", "DetailUrl", "JobUrl", "ref"))
        identifier = first(row, ("id", "Id", "jobId", "job_id", "jobReqId", "Key"))
        if not link and identifier and "/api/pcsx/" in parsed.path:
            link = f"/careers/job/{identifier}"
        if not link and identifier and parsed.hostname == "careers.wipro.com":
            link = f"/jobs/{identifier}"
        if not link and identifier and "recruitingCEJobRequisition" in parsed.path:
            match = re.search(r"siteNumber=([^,&]+)", source_url)
            if match:
                link = f"/hcmUI/CandidateExperience/en/sites/{match.group(1)}/job/{identifier}"
        if link.startswith("/job/") and "/wday/cxs/" in parsed.path:
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 4:
                link = f"/en-US/{parts[3]}{link}"
        if title and link and not NAVIGATION.search(title):
            absolute = urljoin(origin + "/", link)
            if posting_url(absolute) and absolute not in seen:
                location = first(row, ("location", "locationsText", "locations", "PrimaryLocation", "City", "city", "jobLocationShort", "sfstd_jobLocation_obj", "address"))
                if not location and isinstance(row.get("categories"), dict):
                    location = scalar(row["categories"].get("location"))
                job = {"title": title, "apply_url": absolute, "location": location, **details_from_record(row)}
                posted = first(row, ("datePosted", "publishedAt", "postedDate", "PostedDate", "postedOn"))
                if posted:
                    job.setdefault("date_posted", posted)
                jobs.append(job)
                seen.add(absolute)
        for child in value.values():
            if isinstance(child, (dict, list)):
                visit(child)

    visit(payload)
    return jobs


def jobs_from_html(content, page_url):
    soup = BeautifulSoup(content, "html.parser")
    jobs = []
    for script in soup.select('script[type="application/ld+json"],script[type="application/json"],script#__NEXT_DATA__'):
        try:
            jobs.extend(records_from_json(json.loads(script.string or script.get_text()), page_url))
        except (ValueError, TypeError):
            continue
    # Some SSR sites publish their initial job data as a JavaScript assignment.
    for script in soup.find_all("script", src=False):
        raw = script.string or ""
        for match in re.finditer(r"(?:phApp\.ddo|window\.__INITIAL_STATE__|window\.__PRELOADED_STATE__)\s*=\s*", raw):
            try:
                payload, _ = json.JSONDecoder().raw_decode(raw[match.end():])
                jobs.extend(records_from_json(payload, page_url))
            except ValueError:
                continue
    for anchor in soup.select("a[href]"):
        url = urljoin(page_url, anchor.get("href", ""))
        title = anchor.get("aria-label") or anchor.get_text(" ", strip=True)
        title = re.sub(r"^(?:Learn more about|View details for)\s*", "", title, flags=re.I)
        if not 4 <= len(title) <= 220 or NAVIGATION.search(title) or not posting_url(url):
            continue
        heading = anchor.select_one("h2,h3,h4,.job-title")
        if heading:
            title = heading.get_text(" ", strip=True)
        card = anchor.find_parent(["li", "article"]) or anchor.parent
        loc = card.select_one('[class*="location"],[itemprop="jobLocation"]') if card else None
        jobs.append({"title": title, "apply_url": url, "location": loc.get_text(" ", strip=True) if loc else ""})
    return unique_jobs(jobs)


def unique_jobs(jobs):
    result = {}
    for job in jobs:
        url = job.get("apply_url")
        if url and (url not in result or len(job.get("description", "")) > len(result[url].get("description", ""))):
            result[url] = job
    return list(result.values())


def public_feeds(url, html=""):
    """Derive documented board feeds from URLs actually published on the page."""
    links = [url]
    if html:
        soup = BeautifulSoup(html, "html.parser")
        links.extend(urljoin(url, tag["href"]) for tag in soup.select('a[href]'))
        links.extend(tag.get("src", "") for tag in soup.select('iframe[src],script[src]'))
    feeds = []
    for link in links:
        parts = urlsplit(link)
        path = [p for p in parts.path.split("/") if p]
        host = parts.hostname or ""
        if host in ("boards.greenhouse.io", "job-boards.greenhouse.io") and path:
            feeds.append({"url": f"https://boards-api.greenhouse.io/v1/boards/{path[0]}/jobs?content=true", "method": "GET"})
        if host in ("jobs.lever.co", "jobs.eu.lever.co") and path:
            feeds.append({"url": f"https://api.lever.co/v0/postings/{path[0]}?mode=json", "method": "GET"})
        if host == "jobs.ashbyhq.com" and path:
            feeds.append({"url": f"https://api.ashbyhq.com/posting-api/job-board/{path[0]}?includeCompensation=true", "method": "GET"})
        if host in ("careers.smartrecruiters.com", "jobs.smartrecruiters.com") and path:
            feeds.append({"url": f"https://api.smartrecruiters.com/v1/companies/{path[0]}/postings?limit=100", "method": "GET"})
        if host.endswith("myworkdayjobs.com"):
            site_parts = [p for p in path if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", p)]
            if site_parts and site_parts[0] != "wday":
                feeds.append({"url": f"https://{host}/wday/cxs/{host.split('.')[0]}/{site_parts[0]}/jobs", "method": "POST", "payload": {"limit": 20, "offset": 0, "searchText": "India", "appliedFacets": {}}})
    return list({json.dumps(feed, sort_keys=True): feed for feed in feeds}.values())


def request_feed(feed, transport=None):
    if transport:
        response, evidence = transport.fetch(feed["url"])
        if response is None:
            return [], evidence
    else:
        response = requests.request(feed.get("method", "GET"), feed["url"], json=feed.get("payload"), headers=HEADERS, timeout=(6, 20))
        evidence = {"method": "public-api", "url": safe_url(feed["url"]), "http_status": response.status_code}
    if response.status_code != 200:
        return [], evidence
    try:
        jobs = records_from_json(response.json(), feed["url"])
    except ValueError:
        jobs = jobs_from_html(response.text, feed["url"])
    evidence["jobs"] = len(jobs)
    return jobs, evidence


def description_from_html(content, page_url, expected_title):
    soup = BeautifulSoup(content, "html.parser")
    jobs = jobs_from_html(content, page_url)
    for job in jobs:
        if job["apply_url"].split("?")[0].rstrip("/") == page_url.split("?")[0].rstrip("/") and job.get("description"):
            return details_from_record(job)
    containers = ('[itemprop="description"]', '[data-automation-id="jobPostingDescription"]', '.job-description', '.jobdescription', '#jobDescription', '.posting-page', '.job-detail-description', '.article__content__view')
    for selector in containers:
        nodes = soup.select(selector)
        node = max(nodes, key=lambda n: len(n.get_text()), default=None)
        if node and len(node.get_text()) >= 150:
            return details_from_record({"description": node.get_text(" ", strip=True)})
    header = soup.select_one("h1")
    if header and expected_title:
        words = set(re.findall(r"[a-z]{4,}", expected_title.lower()))
        if words.intersection(re.findall(r"[a-z]{4,}", header.get_text().lower())):
            main = soup.select_one("main,article,[role=main]")
            if main:
                for node in main.select("nav,footer,script,style"):
                    node.decompose()
                value = main.get_text(" ", strip=True)
                if re.search(r"responsibilit|qualifications|requirements|what you|experience", value, re.I):
                    return details_from_record({"description": value})
    return {}


def browser_observe(url, evidence_directory, proxy=None, expected_title=None):
    from playwright.sync_api import sync_playwright
    evidence_directory = Path(evidence_directory)
    evidence_directory.mkdir(parents=True, exist_ok=True)
    jobs, network, feeds = [], [], []
    result = {"method": "playwright-proxy" if proxy else "playwright", "url": safe_url(url)}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, proxy=proxy)
        context = browser.new_context(viewport={"width": 1365, "height": 900}, service_workers="block")
        page = context.new_page()

        def observe(response):
            request = response.request
            if request.resource_type not in ("fetch", "xhr") or not re.search(r"job|career|position|posting|recruit|search|vacanc|eightfold|phenom", response.url, re.I):
                return
            if len(network) >= 30:
                return
            entry = {"url": safe_url(response.url), "http_status": response.status, "method": request.method}
            network.append(entry)
            if response.status != 200 or "json" not in response.headers.get("content-type", ""):
                return
            try:
                data = response.json()
                found = records_from_json(data, response.url)
                entry["jobs"] = len(found)
                jobs.extend(found)
                if found and request.method in ("GET", "POST"):
                    if any(re.search(r"token|key|auth|secret|password", key, re.I) for key, _ in parse_qsl(urlsplit(response.url).query)):
                        return
                    feed = {"url": response.url, "method": request.method}
                    if request.post_data:
                        try:
                            payload = json.loads(request.post_data)
                            if re.search(r'"[A-Za-z_]*(?:token|password|authorization|secret|apiKey)[A-Za-z_]*"', request.post_data, re.I):
                                return
                            feed["payload"] = payload
                        except ValueError:
                            return
                    feeds.append(feed)
            except Exception:
                pass

        page.on("response", observe)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=35000)
            result["http_status"] = response.status if response else None
            page.wait_for_timeout(4500)
            if not jobs:
                search = page.get_by_role("button", name=re.compile(r"^(Search jobs|Search)$", re.I))
                if search.count() == 1 and search.is_visible():
                    search.click(timeout=3000)
                    page.wait_for_timeout(2500)
            content = page.content()
            jobs.extend(jobs_from_html(content, page.url))
            result["page_title"] = page.title()
            result["final_url"] = safe_url(page.url)
            result["challenge"] = bool(re.search(r"verify (?:you are|that you)|access denied|unusual traffic|captcha|just a moment", page.locator("body").inner_text(timeout=2000)[:12000], re.I))
            result["discovered_feeds"] = public_feeds(page.url, content)
            if expected_title:
                result["details"] = description_from_html(content, page.url, expected_title)
            page.screenshot(path=str(evidence_directory / "page.png"), full_page=False, timeout=5000)
        except Exception as error:
            result["outcome"] = type(error).__name__
            try:
                page.screenshot(path=str(evidence_directory / "error.png"), timeout=3000)
            except Exception:
                pass
        finally:
            context.close()
            browser.close()
    (evidence_directory / "network.json").write_text(json.dumps(network, indent=2), encoding="utf-8")
    result["network"] = network
    result["observed_feeds"] = feeds
    result["jobs"] = len(unique_jobs(jobs))
    return unique_jobs(jobs), result


def add_descriptions(jobs, count=2):
    chosen = sorted(jobs, key=lambda job: (bool(job.get("location")) and is_india_location(job.get("location")), bool(job.get("description"))), reverse=True)
    for job in chosen[:count]:
        if len(job.get("description", "")) < 80:
            recovered = fetch_details(job["apply_url"])
            for key, value in recovered.items():
                if not job.get(key):
                    job[key] = value
    return chosen
