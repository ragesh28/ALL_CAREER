"""
Master Job Scraper - Reads all company API configs from job_api_calls.md
Phase 1: Run all native API companies (requests)
Phase 2: Run all browser-required companies (Playwright)
"""

import json, re, os, sys, time, requests
try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

MD_FILE = "job_api_calls.md"
OUTPUT_FILE = "scraped_jobs_output.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept": "application/json, text/html, */*"}

# ---------------------------------------------------------------------------
# 1. PARSER: Read job_api_calls.md and extract all company configs
# ---------------------------------------------------------------------------

def parse_md_file(filepath):
    """Parse the markdown file and return two lists: api_companies, browser_companies."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r'\n## ', content)
    api_companies = []
    browser_companies = []

    for block in blocks:
        if not block.strip():
            continue

        # Extract company number and name
        header_match = re.match(r'(\d+)\.\s+(.+?)(?:\s*\(|$)', block)
        if not header_match:
            continue

        num = int(header_match.group(1))
        name = header_match.group(2).strip()
        header_line = block.split('\n')[0]

        is_browser = "Playwright" in block and "Browser" in block
        is_blocked_only = "Blocked" in header_line and "Working" not in header_line

        # Extract endpoint URLs
        endpoints = re.findall(r'`((?:GET|POST)\s+https?://[^`]+)`', block)
        # Also find bare endpoint URLs
        bare_endpoints = re.findall(r'\*\*Endpoint\*\*:\s*`(https?://[^`]+)`', block)

        # Extract payload
        payload_match = re.findall(r'\*\*Payload[^*]*\*\*[^`]*`([^`]+)`', block)
        payload = payload_match[0] if payload_match else None

        # Detect method
        method = "GET"
        if any("POST" in e for e in endpoints):
            method = "POST"
        elif payload:
            method = "POST"

        # Get primary URL
        url = None
        if endpoints:
            url = endpoints[0].replace("GET ", "").replace("POST ", "").strip()
        elif bare_endpoints:
            url = bare_endpoints[0].strip()

        # Detect special types
        is_handshake = "Step 1" in block and "Step 2" in block
        is_ssr = "SSR" in block or "HTML Parsing" in block or "BeautifulSoup" in block
        is_workday = "myworkdayjobs.com" in (url or "")
        is_greenhouse = "greenhouse.io" in (url or "")
        is_oracle = "oraclecloud.com" in (url or "")

        # Extract handshake URL if present
        handshake_url = None
        if is_handshake:
            step1_match = re.findall(r'Step 1[^`]*`(?:GET\s+)?(https?://[^`]+)`', block)
            step2_match = re.findall(r'Step 2[^`]*`(?:POST\s+|GET\s+)?(https?://[^`]+)`', block)
            if step1_match:
                handshake_url = step1_match[0]
            if step2_match:
                url = step2_match[0]

        # Extract mandatory headers
        mandatory_headers = {}
        header_matches = re.findall(r'`(Origin|Referer|x-csrf-token|Content-Type|authorization-api):\s*([^`]+)`', block)
        for hk, hv in header_matches:
            mandatory_headers[hk] = hv.strip()

        company_info = {
            "num": num,
            "name": name,
            "url": url,
            "method": method,
            "payload": payload,
            "is_ssr": is_ssr,
            "is_workday": is_workday,
            "is_greenhouse": is_greenhouse,
            "is_oracle": is_oracle,
            "is_handshake": is_handshake,
            "handshake_url": handshake_url,
            "mandatory_headers": mandatory_headers,
            "raw_block": block,
        }

        if is_browser or is_blocked_only:
            browser_companies.append(company_info)
        else:
            api_companies.append(company_info)

    return api_companies, browser_companies


# ---------------------------------------------------------------------------
# 2. SCRAPER ENGINES
# ---------------------------------------------------------------------------

def clean(text):
    if not text:
        return ""
    return re.sub(r'[^\x00-\x7F]+', ' ', str(text)).strip()


def scrape_workday(info):
    """Handle all Workday POST APIs - full pagination."""
    try:
        base_payload = json.loads(info["payload"]) if info["payload"] else {"limit": 20, "offset": 0}
        
        # Override searchText to "India" to target only India jobs and avoid global paging timeouts
        base_payload["searchText"] = "India"
        
        limit = base_payload.get("limit", 20)
        h = {**HEADERS, "Content-Type": "application/json"}
        all_jobs = []
        offset = 0
        total = 0
        while True:
            payload = {**base_payload, "limit": limit, "offset": offset}
            r = requests.post(info["url"], headers=h, json=payload, timeout=20)
            if r.status_code != 200:
                break
            data = r.json()
            if offset == 0:
                total = data.get("total", 0)
            postings = data.get("jobPostings", [])
            if not postings:
                break
            for j in postings:
                all_jobs.append({
                    "title": clean(j.get("title", "")),
                    "location": clean(j.get("locationsText", "")),
                    "apply_url": f"https://{urlparse(info['url']).netloc}{j.get('externalPath', '')}",
                })
            offset += limit
            if total and offset >= total:
                break
            time.sleep(0.2)
        return {"status": "OK", "total": total or len(all_jobs), "sample_jobs": all_jobs[:5], "all_jobs": all_jobs}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def scrape_greenhouse(info):
    """Handle all Greenhouse APIs."""
    try:
        url = info["url"]
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # Handle departments endpoint
            if "departments" in url:
                deps = data.get("departments", [])
                total = sum(len(d.get("jobs", [])) for d in deps)
                jobs = []
                for d in deps:
                    for j in d.get("jobs", []):
                        jobs.append({
                            "title": clean(j.get("title", "")), 
                            "location": clean(j.get("location", {}).get("name", "")),
                            "apply_url": clean(j.get("absolute_url", ""))
                        })
                        if len(jobs) >= 5:
                            break
                    if len(jobs) >= 5:
                        break
                return {"status": "OK", "total": total, "sample_jobs": jobs}
            else:
                all_jobs = data.get("jobs", [])
                total = data.get("meta", {}).get("total", len(all_jobs))
                jobs = [{
                    "title": clean(j.get("title", "")), 
                    "location": clean(j.get("location", {}).get("name", "") if isinstance(j.get("location"), dict) else ""),
                    "apply_url": clean(j.get("absolute_url", ""))
                } for j in all_jobs[:5]]
                return {"status": "OK", "total": total, "sample_jobs": jobs}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
    return {"status": "FAILED", "total": 0}


def scrape_oracle(info):
    """Handle all Oracle HCM APIs - full pagination."""
    try:
        all_jobs = []
        total = 0
        offset = 0
        limit = 25
        base_url = info["url"]
        # Strip existing offset param
        base_url = re.sub(r'&?offset=\d+', '', base_url)
        while True:
            url = f"{base_url}&offset={offset}" if offset > 0 else base_url
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                break
            data = r.json()
            items = data.get("items", [])
            if not items:
                break
            if offset == 0:
                total = items[0].get("TotalJobsCount", 0)
            reqs = items[0].get("requisitionList", [])
            if not reqs:
                break
            for j in reqs:
                all_jobs.append({
                    "title": clean(j.get("Title", "")), 
                    "location": clean(j.get("PrimaryLocation", "")),
                    "job_id": str(j.get("Id", j.get("RequisitionNumber", "")))
                })
            offset += limit
            if total and offset >= total:
                break
            time.sleep(0.3)
        return {"status": "OK", "total": total or len(all_jobs), "sample_jobs": all_jobs[:5], "all_jobs": all_jobs}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
    return {"status": "FAILED", "total": 0}


def scrape_ssr_html(info):
    """Handle SSR/HTML sites with BeautifulSoup - full pagination."""
    SELECTORS = [
        "li.jobs-list-item", "article.article--result", "div.job-info",
        "div.job-item", ".job-card", ".card-job", "tr.data-row",
        ".job-listing", ".job-title", "a.job-result",
    ]
    def parse_page(html):
        soup = BeautifulSoup(html, "html.parser")
        for sel in SELECTORS:
            items = soup.select(sel)
            if items:
                return items
        # Fallback: job-related links
        links = soup.find_all("a", href=True)
        return [a for a in links if any(k in (a.get("href","")+a.get_text()).lower() for k in ["job","career","position","opening"])]

    try:
        all_jobs = []
        page = 1
        base_url = info["url"]
        while True:
            url = base_url if page == 1 else f"{base_url}{'&' if '?' in base_url else '?'}p={page}"
            r = requests.get(url, headers={**HEADERS, "Accept": "text/html"}, timeout=15)
            if r.status_code != 200:
                break
            items = parse_page(r.text)
            if not items:
                break
            prev_count = len(all_jobs)
            for item in items:
                t = item.select_one("h2, h3, .job-title, .card-title a, a")
                link = item.find("a", href=True)
                if not link and t and t.name == "a":
                    link = t
                apply_url = link.get("href", "") if link else ""
                
                all_jobs.append({
                    "title": clean(t.get_text(strip=True) if t else item.get_text(strip=True)[:80]),
                    "apply_url": clean(apply_url)
                })
            # If we got same number as previous (duplicate page), stop
            if len(all_jobs) == prev_count or page >= 20:
                break
            page += 1
            time.sleep(0.3)
        return {"status": "OK", "total": len(all_jobs), "sample_jobs": all_jobs[:5], "all_jobs": all_jobs}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
    return {"status": "FAILED", "total": 0}


def scrape_handshake(info):
    """Handle two-step handshake APIs (ZS Associates, Danfoss, etc.)."""
    try:
        s = requests.Session()
        s.headers.update(HEADERS)

        # Step 1: Handshake
        r1 = s.get(info["handshake_url"], timeout=10)
        if r1.status_code != 200:
            return {"status": "HANDSHAKE_FAILED", "error": f"Step 1 returned {r1.status_code}"}

        # Check for CSRF token in HTML
        csrf_match = re.search(r'var CSRFToken\s*=\s*"([^"]+)"', r1.text)
        if csrf_match:
            s.headers["x-csrf-token"] = csrf_match.group(1)

        # Step 2: Data
        if info["method"] == "POST":
            payload = json.loads(info["payload"]) if info["payload"] else {}
            extra_headers = {**info.get("mandatory_headers", {}), "Content-Type": "application/json"}
            s.headers.update(extra_headers)
            r2 = s.post(info["url"], json=payload, timeout=15)
        else:
            r2 = s.get(info["url"], timeout=15)

        if r2.status_code == 200:
            try:
                data = r2.json()
                if isinstance(data, dict):
                    total = data.get("totalJobCount", data.get("total", data.get("jobs", []).__len__() if isinstance(data.get("jobs"), list) else 0))
                    jobs_list = data.get("jobs", data.get("jobPostings", []))
                    sample = [{
                        "title": clean(j.get("title", j.get("name", ""))),
                        "job_id": str(j.get("id", j.get("jobId", "")))
                    } for j in (jobs_list[:5] if isinstance(jobs_list, list) else [])]
                    return {"status": "OK", "total": total, "sample_jobs": sample}
            except Exception:
                pass
            return {"status": "OK", "total": "unknown", "sample_jobs": []}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
    return {"status": "FAILED", "total": 0}


def scrape_generic_api(info):
    """Handle generic GET/POST API calls."""
    try:
        extra_h = {**HEADERS}
        for k, v in info.get("mandatory_headers", {}).items():
            if "{" not in v:  # Skip template headers
                extra_h[k] = v

        if info["method"] == "POST":
            payload = None
            if info["payload"]:
                try:
                    payload = json.loads(info["payload"])
                except Exception:
                    payload = info["payload"]

            if isinstance(payload, dict):
                extra_h["Content-Type"] = "application/json"
                r = requests.post(info["url"], headers=extra_h, json=payload, timeout=15)
            elif isinstance(payload, str):
                # multipart/form-data
                r = requests.post(info["url"], headers=extra_h, data={"data": payload}, timeout=15)
            else:
                r = requests.post(info["url"], headers=extra_h, timeout=15)
        else:
            r = requests.get(info["url"], headers=extra_h, timeout=15)

        if r.status_code == 200:
            try:
                text = r.text.lstrip("\ufeff")  # Strip BOM
                data = json.loads(text)
                # Try to extract job count from common patterns
                total = 0
                if isinstance(data, dict):
                    for key in ["total", "totalHits", "totalMatches", "totalJobCount", "TotalJobsCount", "hits", "count", "ResultCount"]:
                        if key in data:
                            total = data[key]
                            break
                    if total == 0:
                        for key in ["jobs", "jobPostings", "jobsList", "data", "results", "Results", "positions", "items"]:
                            if key in data and isinstance(data[key], list):
                                total = len(data[key])
                                break
                elif isinstance(data, list):
                    total = len(data)

                return {"status": "OK", "total": total, "response_type": "JSON"}
            except Exception:
                # It's HTML or XML
                return {"status": "OK", "total": "html/xml", "response_type": "HTML"}
        else:
            return {"status": "FAILED", "http_code": r.status_code}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


# ---------------------------------------------------------------------------
# COMPANY-SPECIFIC FIXUPS
# ---------------------------------------------------------------------------

def scrape_wipro(info):
    """Wipro SAP SuccessFactors - full pagination."""
    return _scrape_wipro_paginated(info)


def _scrape_wipro_paginated(info):
    """Wipro SAP SuccessFactors - full pagination by pageNumber."""
    try:
        h = {**HEADERS, "Content-Type": "application/json",
             "Origin": "https://careers.wipro.com",
             "Referer": "https://careers.wipro.com/en-US/search"}
        all_jobs = []
        page = 0
        total = 0
        while True:
            r = requests.post("https://careers.wipro.com/services/recruiting/v1/jobs",
                              headers=h, json={"pageNumber": page, "locale": "en_US"}, timeout=20)
            if r.status_code != 200:
                break
            data = json.loads(r.text.lstrip("\ufeff"))
            if page == 0:
                total = data.get("totalJobs", 0)
            batch = data.get("jobSearchResult", [])
            if not batch:
                break
            for j in batch:
                all_jobs.append({
                    "title": clean(j.get("response", {}).get("unifiedStandardTitle", "")),
                    "job_id": str(j.get("response", {}).get("id", j.get("response", {}).get("jobReqId", "")))
                })
            page += 1
            if total and len(all_jobs) >= total:
                break
            time.sleep(0.2)
        return {"status": "OK", "total": total or len(all_jobs), "sample_jobs": all_jobs[:5], "all_jobs": all_jobs}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

def scrape_maersk(info):
    """Maersk - full pagination by offset=24."""
    consumer_key = "ean6qqcQIuGza1IZ1Rg9dgfjZhlGE7Dw"
    try:
        r_html = requests.get("https://www.maersk.com/careers/vacancies",
                              headers={**HEADERS, "Accept": "text/html"}, timeout=10)
        m = re.search(r'consumer[-_]?key["\']?\s*:\s*["\']([a-zA-Z0-9]+)["\']', r_html.text, re.I)
        if m:
            consumer_key = m.group(1)
    except Exception:
        pass
    try:
        h = {**HEADERS, "consumer-key": consumer_key}
        all_jobs = []
        offset = 0
        limit = 24
        total = 0
        while True:
            r = requests.get(f"https://api.maersk.com/careers/vacancies?limit={limit}&offset={offset}&city=india",
                             headers=h, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            if offset == 0:
                total = data.get("ResultCount", 0)
            batch = data.get("Results", [])
            if not batch:
                break
            for j in batch:
                all_jobs.append({
                    "title": clean(j.get("Title", "")), 
                    "location": clean(j.get("City", "")),
                    "job_id": str(j.get("Key", ""))
                })
            offset += limit
            if total and offset >= total:
                break
            time.sleep(0.2)
        return {"status": "OK", "total": total or len(all_jobs), "sample_jobs": all_jobs[:5], "all_jobs": all_jobs}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def scrape_ibm(info):
    """IBM - full pagination by start."""
    try:
        h = {**HEADERS, "Content-Type": "application/json",
             "Origin": "https://www.ibm.com", "Referer": "https://www.ibm.com/careers"}
        all_jobs = []
        start = 0
        rows = 10
        total = 0
        while True:
            payload = {"query": "India", "start": start, "rows": rows,
                       "fields": ["title", "location", "url", "posted"]}
            r = requests.post("https://www-api.ibm.com/search/api/v2",
                              headers=h, json=payload, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            if start == 0:
                total = data.get("total", 0)
            hits = data.get("results", [])
            if not hits:
                break
            for j in hits:
                all_jobs.append({
                    "title": clean(j.get("title", "")),
                    "apply_url": clean(j.get("url", ""))
                })
            start += rows
            if total and start >= total:
                break
            time.sleep(0.2)
        return {"status": "OK", "total": total or len(all_jobs), "sample_jobs": all_jobs[:5], "all_jobs": all_jobs}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def scrape_bosch(info):
    """Bosch: SmartRecruiters API - full pagination."""
    try:
        all_jobs = []
        offset = 0
        limit = 100
        while True:
            url = f"https://api.smartrecruiters.com/v1/companies/BoschGroup/postings?country=in&limit={limit}&offset={offset}"
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            content = data.get("content", [])
            if not content:
                break
            for j in content:
                all_jobs.append({
                    "title": clean(j.get("name", "")),
                    "location": clean(j.get("location", {}).get("city", "India")),
                    "apply_url": f"https://jobs.smartrecruiters.com/BoschGroup/{j.get('id', '')}"
                })
            offset += limit
            if len(content) < limit:
                break
            time.sleep(0.2)
        return {"status": "OK", "total": len(all_jobs), "sample_jobs": all_jobs[:5], "all_jobs": all_jobs}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def jobspy_fallback_result(company_name):
    """Use JobSpy/LinkedIn as final fallback for hard companies."""
    if not JOBSPY_AVAILABLE:
        return {"status": "FAILED", "error": "JobSpy not installed", "total": 0}
    try:
        # Strip trailing Phenom or other tags to query cleanly: "Mastercard (Phenom)" -> "Mastercard"
        clean_company = re.sub(r'\s*\(.*\)', '', company_name)
        clean_company = re.sub(r'^\d+\.\s+', '', clean_company).strip()
        
        print(f"  [JobSpy Fallback] Scraping LinkedIn for '{clean_company}' in India...")
        df = scrape_jobs(
            site_name=["linkedin"],
            search_term=clean_company,
            location="India",
            results_wanted=100,
            country_indeed="India"
        )
        jobs = []
        seen = set()
        for _, row in df.iterrows():
            url = str(row.get("job_url", ""))
            if not url or url in seen:
                continue
            seen.add(url)
            jobs.append({
                "title": clean(str(row.get("title", ""))),
                "location": clean(str(row.get("location", "India"))),
                "apply_url": url
            })
        if jobs:
            print(f"  [JobSpy Fallback] Successfully fetched {len(jobs)} jobs for '{clean_company}'!")
            return {"status": "OK", "total": len(jobs), "sample_jobs": jobs[:5], "all_jobs": jobs, "method": "JobSpy/LinkedIn fallback"}
        return {"status": "FAILED", "total": 0, "error": "JobSpy returned 0 jobs"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "total": 0}


# ---------------------------------------------------------------------------
# 3. BROWSER ENGINE (Playwright)
# ---------------------------------------------------------------------------

def scrape_with_browser(info):
    """Use Playwright headless browser for blocked sites."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"status": "ERROR", "error": "Playwright not installed. Run: pip install playwright && playwright install chromium"}

    url = info["url"]
    if not url:
        return {"status": "ERROR", "error": "No URL found"}

    name = info.get("name", "").lower()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(
                user_agent=UA,
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
            )
            page = context.new_page()

            # ITC Infotech: use HTTP/1.1 fallback URL
            if "itc" in name:
                url = "https://jobs.itcinfotech.com/itcinfotech/"

            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(10000)  # Wait for JS to render

            # For ITC: try navigating to jobslist after home loads
            if "itc" in name:
                try:
                    page.goto("https://jobs.itcinfotech.com/itcinfotech/jobslist",
                              wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(8000)
                except Exception:
                    pass

            # Extract job data from the rendered page
            content = page.content()
            soup = BeautifulSoup(content, "html.parser")

            # Try common job selectors
            selectors = [
                "li.jobs-list-item", ".job-card", ".job-item",
                "tr[data-job-id]", ".card-job", ".job-listing", ".opening-list li",
                "div[class*='JobCard']", "div[class*='job-card']",
                "a[href*='/job/']", "a[href*='jobId']",
                "div[class*='job']", "div[class*='position']",
            ]
            jobs_found = []
            for sel in selectors:
                items = soup.select(sel)
                if len(items) >= 1:
                    jobs_found = items
                    break

            titles = []
            for item in jobs_found[:5]:
                t = item.select_one("h2, h3, h4, .job-title, a")
                text = clean(t.get_text(strip=True) if t else item.get_text(strip=True)[:80])
                link = item.find("a", href=True)
                if not link and t and t.name == "a":
                    link = t
                apply_url = link.get("href", "") if link else ""

                if text and len(text) > 3:
                    titles.append({
                        "title": text,
                        "apply_url": apply_url
                    })

            browser.close()

            # If browser got 0 jobs, try JobSpy fallback
            if not jobs_found and JOBSPY_AVAILABLE:
                orig_name = info.get("name", "")
                fb = jobspy_fallback_result(orig_name)
                if fb.get("status") == "OK":
                    fb["method"] = "Playwright+JobSpy fallback"
                    return fb

            return {"status": "OK", "total": len(jobs_found), "sample_jobs": titles, "method": "Playwright"}
    except Exception as e:
        # Network-level block (ITC HTTP2 error etc) — fallback to JobSpy
        if JOBSPY_AVAILABLE:
            orig_name = info.get("name", "")
            fb = jobspy_fallback_result(orig_name)
            fb["method"] = f"JobSpy fallback (Playwright blocked: {str(e)[:60]})"
            return fb
        return {"status": "ERROR", "error": str(e), "method": "Playwright"}


def scrape_qualcomm_phenom(info):
    """Qualcomm Phenom API - full pagination by start=10."""
    try:
        h = {**HEADERS}
        all_jobs = []
        start = 0
        while True:
            r = requests.get(
                "https://careers.qualcomm.com/api/pcsx/search",
                headers=h,
                params={"domain": "qualcomm.com", "location": "india", "start": start, "num": 10},
                timeout=15
            )
            if r.status_code != 200:
                break
            positions = r.json().get("data", {}).get("positions", [])
            if not positions:
                break
            for p in positions:
                all_jobs.append({
                    "title": clean(p.get("name", "")),
                    "location": clean(p.get("locations", ["India"])[0] if p.get("locations") else "India"),
                    "job_id": str(p.get("jobSeqNo", p.get("id", "")))
                })
            start += 10
            time.sleep(0.2)
        return {"status": "OK", "total": len(all_jobs), "sample_jobs": all_jobs[:5], "all_jobs": all_jobs}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def scrape_ericsson_phenom(info):
    """Ericsson Phenom API - full pagination by start=10."""
    try:
        h = {**HEADERS}
        all_jobs = []
        start = 0
        while True:
            r = requests.get(
                "https://jobs.ericsson.com/api/pcsx/search",
                headers=h,
                params={"domain": "ericsson.com", "location": "India", "start": start, "num": 10},
                timeout=15
            )
            if r.status_code != 200:
                break
            positions = r.json().get("data", {}).get("positions", [])
            if not positions:
                break
            for p in positions:
                all_jobs.append({
                    "title": clean(p.get("name", "")),
                    "location": clean(p.get("locations", ["India"])[0] if p.get("locations") else "India"),
                    "job_id": str(p.get("jobSeqNo", p.get("id", "")))
                })
            start += 10
            time.sleep(0.2)
        return {"status": "OK", "total": len(all_jobs), "sample_jobs": all_jobs[:5], "all_jobs": all_jobs}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def scrape_crossover(info):
    """Crossover API — total is under totalSize key."""
    try:
        r = requests.get("https://profile-api.crossover.com/pipelines?status=Active",
                         headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            total = data.get("totalSize", 0)
            records = data.get("records", [])
            sample = [{
                "title": clean(rec.get("Name", rec.get("name", ""))),
                "job_id": str(rec.get("id", ""))
            } for rec in records[:5]]
            return {"status": "OK", "total": total, "sample_jobs": sample}
        return {"status": "FAILED", "http_code": r.status_code}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def scrape_amazon_ai(info):
    """Amazon AI jobs — use broader search without strict country filter."""
    try:
        url = "https://www.amazon.jobs/en/search.json"
        params = {
            "category[]": "software-development",
            "normalized_country_code[]": "IND",
            "offset": 0,
            "result_limit": 10,
            "sort": "recent"
        }
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            hits = data.get("hits", 0)
            jobs = data.get("jobs", [])
            total = hits if hits else len(jobs)
            sample = [{
                "title": clean(j.get("title", "")),
                "location": clean(j.get("location", "India")),
                "apply_url": clean(j.get("job_path", j.get("id_icims", "")))
            } for j in jobs[:5]]
            return {"status": "OK", "total": total, "sample_jobs": sample}
        return {"status": "FAILED", "http_code": r.status_code}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


# ---------------------------------------------------------------------------
# 4. DISPATCHER: Route each company to the right engine
# ---------------------------------------------------------------------------

def dispatch_api(info):
    """Route a company to the correct scraper engine based on its config."""
    name = info["name"]
    name_lower = name.lower()
    url = info.get("url", "")

    if not url:
        return {"status": "SKIPPED", "reason": "No URL extracted"}

    # ── Company-specific overrides (highest priority) ──
    if "qualcomm" in name_lower:
        return scrape_qualcomm_phenom(info)
    if "ericsson" in name_lower:
        return scrape_ericsson_phenom(info)
    if "wipro" in name_lower:
        return scrape_wipro(info)
    if "maersk" in name_lower:
        return scrape_maersk(info)
    if "ibm" in name_lower and JOBSPY_AVAILABLE:
        return jobspy_fallback_result("IBM")
    if "bosch" in name_lower:
        return scrape_bosch(info)
    if "crossover" in name_lower:
        return scrape_crossover(info)
    if "amazon" in name_lower:
        result = scrape_amazon_ai(info)
        if not result.get("total") and JOBSPY_AVAILABLE:
            return jobspy_fallback_result("Amazon")
        return result

    # HPE/Juniper, Mastercard, ABB — Phenom /widgets needs CSRF, use Playwright/JobSpy
    if "juniper" in name_lower or "hpe" in name_lower:
        if JOBSPY_AVAILABLE:
            return jobspy_fallback_result("HPE")
        return scrape_with_browser({**info, "url": "https://careers.hpe.com/us/en/search-results?location=India"})
    if "mastercard" in name_lower:
        if JOBSPY_AVAILABLE:
            return jobspy_fallback_result("Mastercard")
        return scrape_with_browser({**info, "url": "https://careers.mastercard.com/us/en/search-results?location=India"})
    if "abb" in name_lower:
        if JOBSPY_AVAILABLE:
            return jobspy_fallback_result("ABB")
        return scrape_with_browser({**info, "url": "https://careers.abb/us/en/search-results?location=India"})

    # Companies known to return 0 / few jobs — use JobSpy fallback
    JOBSPY_FALLBACK_COMPANIES = [
        "continental", "grundfos", "cohesity", "tally", 
        "zs associates", "nutanix", "cognizant", "brillio"
    ]
    if any(n in name_lower for n in JOBSPY_FALLBACK_COMPANIES) and JOBSPY_AVAILABLE:
        return jobspy_fallback_result(name)

    # ── Standard routing ──
    # Handshake companies (ZS Associates, Danfoss) — fallback to JobSpy if 0 returned
    if info["is_handshake"] and info["handshake_url"]:
        result = scrape_handshake(info)
        if not result.get("total") and JOBSPY_AVAILABLE:
            return jobspy_fallback_result(name)
        return result

    # Workday
    if info["is_workday"]:
        return scrape_workday(info)

    # Greenhouse
    if info["is_greenhouse"]:
        return scrape_greenhouse(info)

    # Oracle HCM
    if info["is_oracle"]:
        return scrape_oracle(info)

    # SSR HTML
    if info["is_ssr"]:
        return scrape_ssr_html(info)

    # Generic API
    result = scrape_generic_api(info)
    # If generic API fails hard (401/403/400), try JobSpy as last resort
    if result.get("status") in ("FAILED", "ERROR") and JOBSPY_AVAILABLE:
        fb = jobspy_fallback_result(name)
        if fb.get("status") == "OK":
            return fb
    return result


# ---------------------------------------------------------------------------
# 5. CHECKPOINT HELPERS
# ---------------------------------------------------------------------------

CHECKPOINT_FILE = "scrape_checkpoint.json"

def load_checkpoint():
    """Load existing results + next_index from checkpoint file."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"next_index": 0, "completed": False, "results": {}}

def save_checkpoint(next_index, results, completed=False):
    """Save progress checkpoint so the workflow can resume."""
    data = {
        "next_index": next_index,
        "completed": completed,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
    }
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_india(location):
    if not location:
        return True
    loc = location.lower()
    indian_keywords = [
        "india", "ind", "bangalore", "bengaluru", "hyderabad", "chennai", 
        "pune", "mumbai", "gurgaon", "noida", "delhi", "remote", 
        "karnataka", "maharashtra", "telangana", "tamil nadu", "haryana"
    ]
    return any(k in loc for k in indian_keywords)


def clean_company_name(name):
    # Strip leading number and dot: "4. Amadeus" -> "Amadeus"
    # Also strip any parenthetical info: "ZS Associates (Playwright)" -> "ZS Associates"
    cleaned = re.sub(r'^\d+\.\s+', '', name)
    cleaned = re.sub(r'\s*\(.*\)', '', cleaned)
    return cleaned.strip()


def get_company_career_url(info):
    url = info.get("url", "")
    if not url:
        return ""
    if info.get("is_workday"):
        parsed = urlparse(url)
        netloc = parsed.netloc
        parts = parsed.path.split('/')
        company_segment = ""
        for part in parts:
            if part and part not in ("wday", "cxs", "jobs"):
                company_segment = part
                break
        if company_segment:
            return f"https://{netloc}/en-US/{company_segment}/"
        return f"https://{netloc}/"
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/"


def update_big_company_jobs(all_results, company_info_map):
    big_jobs_path = os.path.join("workday_scraper", "big_company_jobs.json")
    seen_ids_path = "seen_job_ids.json"
    
    existing_jobs = []
    if os.path.exists(big_jobs_path):
        try:
            with open(big_jobs_path, "r", encoding="utf-8") as f:
                existing_jobs = json.load(f)
        except Exception as e:
            print(f"Error loading existing big_company_jobs.json: {e}")
            existing_jobs = []
            
    seen_ids_db = {}
    if os.path.exists(seen_ids_path):
        try:
            with open(seen_ids_path, "r", encoding="utf-8") as f:
                seen_ids_db = json.load(f)
        except Exception as e:
            print(f"Error loading {seen_ids_path}: {e}")

    existing_keys = set()
    for job in existing_jobs:
        comp = (job.get("company") or "").strip().lower()
        title = (job.get("title") or "").strip().lower()
        url = (job.get("apply_url") or "").strip().lower()
        clean_url = url.split('?')[0] if url else ""
        existing_keys.add((comp, title, clean_url))
        
    fetched_at = datetime.now().strftime("%Y-%m-%d")
    
    total_scraped = 0
    total_india = 0
    new_jobs_added = 0
    
    for raw_company_name, result in all_results.items():
        if result.get("status") != "OK":
            continue
            
        clean_name = clean_company_name(raw_company_name)
        info = company_info_map.get(raw_company_name, {})
        company_url = get_company_career_url(info)
        
        # Ensure company exists in seen_ids_db
        if clean_name not in seen_ids_db:
            seen_ids_db[clean_name] = []
        
        jobs_list = result.get("all_jobs") or result.get("sample_jobs") or []
        if not isinstance(jobs_list, list):
            continue
            
        for raw_job in jobs_list:
            if not isinstance(raw_job, dict):
                continue
                
            title = clean(raw_job.get("title", ""))
            if not title or len(title) < 2:
                continue
                
            total_scraped += 1
            location = clean(raw_job.get("location", ""))
            
            if not is_india(location):
                continue
                
            total_india += 1
            apply_url = raw_job.get("apply_url") or raw_job.get("url") or company_url or ""
            unique_job_id = str(raw_job.get("job_id", apply_url)).strip()
            
            # Check if we have seen this ID permanently
            if unique_job_id in seen_ids_db[clean_name] and unique_job_id != "":
                continue  # Skip this job as we've already scraped it in the past

            comp_lower = clean_name.lower()
            title_lower = title.strip().lower()
            url_lower = apply_url.strip().lower()
            clean_url = url_lower.split('?')[0] if url_lower else ""
            
            job_key = (comp_lower, title_lower, clean_url)
            
            if job_key not in existing_keys:
                new_job = {
                    "title": title,
                    "location": location or "India",
                    "posted": "",
                    "apply_url": apply_url,
                    "total_jobs": 0,
                    "fetched_at": fetched_at,
                    "company": clean_name
                }
                existing_jobs.append(new_job)
                existing_keys.add(job_key)
                # Permanently store the seen ID
                if unique_job_id:
                    seen_ids_db[clean_name].append(unique_job_id)
                new_jobs_added += 1
                
    if new_jobs_added > 0:
        print(f"Adding {new_jobs_added} new jobs to big_company_jobs.json...")
        os.makedirs(os.path.dirname(big_jobs_path), exist_ok=True)
        try:
            with open(big_jobs_path, "w", encoding="utf-8") as f:
                json.dump(existing_jobs, f, indent=4, ensure_ascii=False)
            print("Successfully updated big_company_jobs.json!")
            
            # Save the updated seen job IDs
            with open(seen_ids_path, "w", encoding="utf-8") as f:
                json.dump(seen_ids_db, f, indent=4, ensure_ascii=False)
            print("Successfully updated seen_job_ids.json!")
        except Exception as e:
            print(f"Error saving updated JSON files: {e}")
    else:
        print("No new unique jobs found to add to big_company_jobs.json.")
        
    return total_scraped, total_india, new_jobs_added


def save_output(all_results, api_count, browser_count):
    """Write the final scraped_jobs_output.json."""
    output = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_companies": len(all_results),
        "api_count": api_count,
        "browser_count": browser_count,
        "results": all_results,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    total_scraped = 0
    total_india = 0
    new_jobs_added = 0

    try:
        if os.path.exists(MD_FILE):
            api_companies, browser_companies = parse_md_file(MD_FILE)
            all_companies = api_companies + browser_companies
            company_info_map = {}
            for info in all_companies:
                name = f"{info['num']}. {info['name']}"
                company_info_map[name] = info
            
            total_scraped, total_india, new_jobs_added = update_big_company_jobs(all_results, company_info_map)
    except Exception as e:
        print(f"Error during big_company_jobs update inside save_output: {e}")

    # Display the user's requested metrics in a beautiful, prominent box
    print("\n" + "=" * 70)
    print("                METRICS & STATS SUMMARY")
    print("=" * 70)
    print(f"  Total Jobs Scraped (Raw Global)     : {total_scraped:,}")
    print(f"  India-Location Jobs (After Filter)  : {total_india:,}")
    print(f"  New Unique Jobs Added to Database  : +{new_jobs_added:,}")
    print("=" * 70 + "\n")


def load_previous_output():
    """Load previous scraped_jobs_output.json to compare totals (detect new jobs)."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Build dict: company_name -> old total (int)
            prev = {}
            for name, r in data.get("results", {}).items():
                try:
                    t = r.get("total", 0)
                    prev[name] = int(t) if str(t).isdigit() else 0
                except Exception:
                    prev[name] = 0
            return prev
        except Exception:
            pass
    return {}


# ---------------------------------------------------------------------------
# 6. MAIN EXECUTION
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Master Job Scraper")
    parser.add_argument("--resume", type=int, default=0,
                        help="Resume from this global company index (0-based)")
    parser.add_argument("--timeout", type=int, default=0,
                        help="Stop scraping after this many seconds (0 = no limit)")
    args = parser.parse_args()

    resume_index = args.resume
    timeout_secs = args.timeout
    start_time   = time.time()

    print("=" * 70)
    print("  MASTER JOB SCRAPER - Reading configs from job_api_calls.md")
    print(f"  Resume index : {resume_index}")
    print(f"  Timeout secs : {timeout_secs if timeout_secs else 'unlimited'}")
    print("=" * 70)

    if not os.path.exists(MD_FILE):
        print(f"ERROR: {MD_FILE} not found!")
        return

    api_companies, browser_companies = parse_md_file(MD_FILE)
    all_companies = api_companies + browser_companies          # flat ordered list
    total = len(all_companies)
    print(f"\nParsed {len(api_companies)} API + {len(browser_companies)} Browser = {total} total")
    print(f"Starting from index {resume_index}\n")

    # Load any previously saved results (so we don't lose already-scraped data)
    checkpoint = load_checkpoint()
    all_results = checkpoint.get("results", {})

    # Load previous output to detect new jobs
    prev_totals = load_previous_output()

    timed_out = False
    total_new_jobs = 0  # accumulator across all companies

    # ===== PHASE 1: Native API Companies =====
    print("=" * 70)
    print("  PHASE 1: Native API Companies (requests)")
    print("=" * 70)

    for global_idx, info in enumerate(api_companies):
        # Skip already-done companies when resuming
        if global_idx < resume_index:
            continue

        # Timeout guard — stop before GitHub kills the runner
        elapsed = time.time() - start_time
        if timeout_secs and elapsed >= timeout_secs:
            print(f"\n  ⏰ Timeout reached at {elapsed:.0f}s — saving checkpoint at index {global_idx}")
            save_checkpoint(global_idx, all_results, completed=False)
            save_output(all_results, len(api_companies), len(browser_companies))
            timed_out = True
            break

        i = global_idx + 1
        name = f"{info['num']}. {info['name']}"
        print(f"\n[{i}/{total}] Scraping {name}...")
        print(f"  URL: {info.get('url', 'N/A')[:80]}")
        print(f"  Method: {info['method']} | Workday: {info['is_workday']} | "
              f"Greenhouse: {info['is_greenhouse']} | Oracle: {info['is_oracle']} | "
              f"SSR: {info['is_ssr']} | Handshake: {info['is_handshake']}")

        result = dispatch_api(info)
        all_results[name] = result

        status_icon = "OK" if result.get("status") == "OK" else "FAIL"
        total_jobs  = result.get("total", "?")
        old_total   = prev_totals.get(name, 0)
        try:
            new_jobs = max(0, int(total_jobs) - old_total) if str(total_jobs).isdigit() else "?"
        except Exception:
            new_jobs = "?"
        if new_jobs != "?":
            total_new_jobs += new_jobs
        print(f"  Result: [{status_icon}] Total: {total_jobs} | New: +{new_jobs}")
        if result.get("sample_jobs"):
            for j in result["sample_jobs"][:2]:
                print(f"    -> {j.get('title', '?')[:60]}")

        time.sleep(0.3)

    # ===== PHASE 2: Browser Companies =====
    if not timed_out:
        print("\n" + "=" * 70)
        print("  PHASE 2: Browser-Required Companies (Playwright)")
        print("=" * 70)

        browser_start = len(api_companies)   # global index offset for browser list

        for local_idx, info in enumerate(browser_companies):
            global_idx = browser_start + local_idx

            if global_idx < resume_index:
                continue

            elapsed = time.time() - start_time
            if timeout_secs and elapsed >= timeout_secs:
                print(f"\n  ⏰ Timeout reached at {elapsed:.0f}s — saving checkpoint at index {global_idx}")
                save_checkpoint(global_idx, all_results, completed=False)
                save_output(all_results, len(api_companies), len(browser_companies))
                timed_out = True
                break

            i = global_idx + 1
            name = f"{info['num']}. {info['name']}"
            print(f"\n[{i}/{total}] Scraping {name} (Browser)...")
            print(f"  URL: {info.get('url', 'N/A')[:80]}")

            result = scrape_with_browser(info)
            all_results[name] = result

            status_icon = "OK" if result.get("status") == "OK" else "FAIL"
            total_jobs  = result.get("total", "?")
            old_total   = prev_totals.get(name, 0)
            try:
                new_jobs = max(0, int(total_jobs) - old_total) if str(total_jobs).isdigit() else "?"
            except Exception:
                new_jobs = "?"
            if new_jobs != "?":
                total_new_jobs += new_jobs
            print(f"  Result: [{status_icon}] Total: {total_jobs} | New: +{new_jobs}")
            if result.get("sample_jobs"):
                for j in result["sample_jobs"][:2]:
                    print(f"    -> {j.get('title', '?')[:60]}")

            time.sleep(1)

    # ===== SAVE RESULTS =====
    save_output(all_results, len(api_companies), len(browser_companies))

    if not timed_out:
        # Mark run as fully complete — clear checkpoint
        save_checkpoint(0, {}, completed=True)

    # ===== SUMMARY =====
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)

    ok      = sum(1 for r in all_results.values() if r.get("status") == "OK")
    failed  = sum(1 for r in all_results.values() if r.get("status") in ("FAILED", "ERROR"))
    skipped = sum(1 for r in all_results.values() if r.get("status") == "SKIPPED")
    grand_total = sum(
        int(r.get("total", 0))
        for r in all_results.values()
        if str(r.get("total", "")).isdigit()
    )

    print(f"  Total Companies   : {len(all_results)}")
    print(f"  Successful        : {ok}")
    print(f"  Failed            : {failed}")
    print(f"  Skipped           : {skipped}")
    print(f"  Total Jobs Scraped: {grand_total:,}")
    print(f"  New Jobs This Run : +{total_new_jobs:,}")
    print(f"  Timed out         : {'YES — will auto-restart' if timed_out else 'No'}")
    print(f"\n  Results saved to: {OUTPUT_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
