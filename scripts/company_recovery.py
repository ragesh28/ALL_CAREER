"""Public career-page, observed API and browser recovery shared by company scrapers."""
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup

from scripts.company_job_details import details_from_record, fetch_details, confirmed_india_location, inline_job_data, location_text, normalize_job_links, public_request, text, wipro_details

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/html,*/*"}
NAVIGATION = re.compile(r"^(?:search|guided search|view|browse|all|find|explore|join|sign|learn|skip|career|job alert|privacy|cookie|apply now|read more|current openings|open positions|my saved jobs|saved jobs|\d+ saved jobs)(?:\b|$)", re.I)


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
    if re.search(r"\.(?:svg|png|jpe?g|webp|gif|css|js|woff2?|pdf)$", path):
        return False
    if re.search(r"(?:^|/)(?:saved-jobs|saved|job-alerts|sign-in|register)(?:/|$)", path):
        return False
    if not path or path in ("careers", "jobs", "careers/search", "job-search", "search-results", "jobs/india"):
        return False
    if re.search(r"(?:^|/)(?:job-search|search-jobs|search-results|life-at[^/]*|culture|benefits|teams|saved-jobs)(?:/|$)", path):
        return False
    if parsed.hostname == "careers.kula.ai" and re.fullmatch(r"[^/]+/\d+-[^/]+", path):
        return True
    if parsed.hostname == "jobs.smartrecruiters.com" and re.fullmatch(r"[^/]+/\d+(?:-[^/]+)?", path):
        return True
    if any(key.lower() in ("jobid", "job_id", "jk", "gh_jid", "requisitionid") and value for key, value in parse_qsl(parsed.query)):
        return True
    return bool(re.search(r"/jobs/results/\d+|/jobs?/(?!results(?:/|$)|search(?:/|$)|all(?:/|$))[^/]+|jobdetail/[^/]+|/postings?/[^/]+|/positions?/[^/]+|/requisitions?/[^/]+|/roles/[^/]+|/vacancies/[^/]+|/openings/[^/]+|/j/\d+|[a-f0-9]{8}-[a-f0-9-]{20,}", "/" + path))


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
        title = first(row, ("title", "jobTitle", "Title", "postingTitle", "unifiedStandardTitle", "JobTitle", "Posting_Title", "Job_Opening_Name", "post_title", "name", "text"))
        link = first(row, ("jobUrl", "jobURL", "postingUrl", "absolute_url", "absoluteUrl", "positionUrl", "canonicalPositionUrl", "careerSiteUrl", "hostedUrl", "apply_url", "apply_job_url", "url", "URL", "$url", "applyUrl", "jcrURL", "externalPath", "DetailUrl", "JobUrl", "ref"))
        identifier = first(row, ("id", "Id", "jobId", "job_id", "jobReqId", "Key", "post_id"))
        if row.get("isListed") is False or row.get("Publish") is False or row.get("is_confidential") is True or row.get("on_career_page") is False:
            title = ""
        if parsed.hostname == "cg-jobstream-api.azurewebsites.net" and (row.get("deleted_at") or str(row.get("status", "1")) != "1"):
            title = ""
        if parsed.hostname == "www.phonepe.com" and parsed.path.endswith("/latest.json") and row.get("status") != "PUBLIC":
            title = ""
        if parsed.hostname == "careers.swiggy.in" and parsed.path == "/api/jobs.json" and row.get("t") and row.get("u"):
            title, link = text(row["t"]), text(row["u"])
            details_record = {**row, "location": row.get("l"), "employment_type": row.get("e")}
        else:
            details_record = row
        if parsed.hostname == "careers.kula.ai" and row.get("id") and isinstance(row.get("ats_job"), dict):
            board = dict(parse_qsl(parsed.query)).get("accountName")
            if board:
                slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
                link = f"/{board}/{row['id']}-{slug}"
                details_record = {**row, **row["ats_job"]}
                details_record["location"] = row["ats_job"].get("offices", [])
        if not link and identifier and parsed.hostname == "careers.turing.com":
            link = f"/job/{identifier}"
        if not link and identifier and parsed.hostname == "careers.zohocorp.com" and identifier in parsed.path.split("/"):
            link = source_url
        if not link and identifier and parsed.hostname == "ibegin.tcsapps.com" and "/api/en-IN/" in parsed.path:
            link = f"/candidate/next/en-IN/jobs/{str(identifier).rstrip('J')}J"
        if not link and identifier and "/api/pcsx/" in parsed.path:
            link = f"/careers/job/{identifier}"
        if not link and identifier and parsed.hostname == "careers.wipro.com":
            link = f"/job/{row['unifiedUrlTitle']}/{identifier}-en_US" if row.get("unifiedUrlTitle") else f"/jobs/{identifier}"
        smart = re.match(r"/v1/companies/([^/]+)/postings", parsed.path)
        if identifier and parsed.hostname == "api.smartrecruiters.com" and smart:
            link = f"https://jobs.smartrecruiters.com/{smart.group(1)}/{identifier}"
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
                location = next((location_text(details_record.get(key)) for key in ("location", "locationsText", "locations", "jobLocation", "PrimaryLocation", "City", "city", "post_location_name", "jobLocationShort", "sfstd_jobLocation_obj", "address") if location_text(details_record.get(key))), "")
                country = row.get("Country") or row.get("Country1") or row.get("country")
                if country and not isinstance(country, (list, dict)) and text(country) not in location:
                    location = ", ".join(filter(None, [location, text(row.get("State")), text(country)]))
                if not location and isinstance(row.get("categories"), dict):
                    location = scalar(row["categories"].get("location"))
                job = {"title": title, "apply_url": absolute, "location": location, **details_from_record(details_record)}
                if row.get("Job_Description"):
                    job.update(details_from_record({"description": row["Job_Description"]}))
                posted = first(row, ("datePosted", "publishedAt", "postedDate", "PostedDate", "postedOn", "Date_Opened", "launch_at"))
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
    base = soup.select_one("base[href]")
    if base:
        page_url = urljoin(page_url, base["href"])
    jobs = []
    for payload in inline_job_data(soup):
        jobs.extend(records_from_json(payload, page_url))
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
        if host == "careers.wipro.com":
            feeds.append({"url": "https://careers.wipro.com/services/recruiting/v1/jobs", "method": "POST", "payload": {"pageNumber": 0, "locale": "en_US"}})
        if host.endswith("oraclecloud.com") and "/sites/" in parts.path:
            site = re.search(r"/sites/([^/]+)", parts.path)
            if site:
                feeds.append({"url": f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber={site[1]},limit=25,sortBy=POSTING_DATES_DESC", "method": "GET"})
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
        response = public_request(feed.get("method", "GET"), feed["url"], json=feed.get("payload"), headers=HEADERS, timeout=(6, 20))
        evidence = {"method": "public-api", "url": safe_url(feed["url"]), "http_status": response.status_code, "http_client": getattr(response, "career_http_client", "requests")}
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
    if urlsplit(page_url).hostname == "careers.wipro.com":
        return wipro_details(soup)
    jobs = jobs_from_html(content, page_url)
    for job in jobs:
        if job["apply_url"].split("?")[0].rstrip("/") == page_url.split("?")[0].rstrip("/") and job.get("description"):
            return details_from_record(job)
    containers = ('[itemprop="description"]', '[data-automation-id="jobPostingDescription"]', '.cw-jobdescription', '.job-description', '.jobdescription', '#jobDescription', '.posting-page', '.job-detail-description', '.article__content__view')
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
            target = urlsplit(response.url)
            if request.resource_type not in ("fetch", "xhr") or not re.search(r"job|career|position|posting|recruit|search|vacanc|eightfold|phenom", target.netloc + target.path, re.I):
                return
            if len(network) >= 30:
                return
            entry = {"url": safe_url(response.url), "http_status": response.status, "method": request.method}
            network.append(entry)
            if response.status != 200 or "json" not in response.headers.get("content-type", ""):
                return
            try:
                data = response.json()
                if request.post_data:
                    try:
                        public_payload = json.loads(request.post_data)
                        if not re.search(r'"[A-Za-z_]*(?:token|password|authorization|secret|apiKey)[A-Za-z_]*"', request.post_data, re.I):
                            entry["payload"] = public_payload
                    except ValueError:
                        pass
                body = json.dumps(data, ensure_ascii=False)
                if len(body) < 2_000_000:
                    (evidence_directory / f"response-{len(network):02}.json").write_text(body, encoding="utf-8")
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

        context.on("response", observe)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=35000)
            result["http_status"] = response.status if response else None
            page.wait_for_timeout(4500)
            if not jobs:
                search = page.get_by_role("button", name=re.compile(r"^(Search jobs|Search)$", re.I))
                if search.count() == 1 and search.is_visible():
                    search.click(timeout=3000)
                    page.wait_for_timeout(2500)
            if not jobs:
                openings = page.get_by_text(re.compile(r"^(See Open Roles|View Open Roles|View open positions|View current openings|Explore jobs)$", re.I))
                if openings.count() == 1 and openings.is_visible():
                    openings.click(timeout=5000)
                    page.wait_for_timeout(3000)
                    page = context.pages[-1]
            content = page.content()
            jobs.extend(jobs_from_html(content, page.url))
            result["page_title"] = page.title()
            result["final_url"] = safe_url(page.url)
            result["challenge"] = bool(re.search(r"verify (?:you are|that you)|access denied|unusual traffic|captcha|just a moment", page.locator("body").inner_text(timeout=2000)[:12000], re.I))
            result["discovered_feeds"] = public_feeds(page.url, content)
            if expected_title:
                result["details"] = description_from_html(content, page.url, expected_title)
                matching = [job for job in jobs if job["apply_url"].split("?")[0].rstrip("/") == page.url.split("?")[0].rstrip("/") and job["title"].casefold() == expected_title.casefold() and job.get("description")]
                if matching:
                    details = details_from_record(max(matching, key=lambda j: len(j["description"])))
                    if len(details.get("description", "")) > len(result["details"].get("description", "")):
                        result["details"] = details
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
    chosen = sorted(jobs, key=lambda job: (confirmed_india_location(job.get("location")), bool(job.get("description"))), reverse=True)
    for job in chosen[:count]:
        if len(job.get("description", "")) < 500:
            recovered = fetch_details(job["apply_url"])
            for key, value in recovered.items():
                if not job.get(key) or (key == "description" and len(value) > len(job.get(key, ""))):
                    job[key] = value
    return chosen
