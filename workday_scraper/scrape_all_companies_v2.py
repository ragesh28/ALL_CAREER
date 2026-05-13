"""
Final Master Job Scraper
Integrates all discovered direct APIs and Playwright fallbacks.
"""

import json
import csv
import sys
import uuid
import time
import re
import os
import requests
from datetime import datetime
from urllib.parse import urlparse, urljoin, urlsplit, urlunsplit
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from jobspy import scrape_jobs
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

# ---- LOCAL JSON CONFIG ----
DB_FILE = "big_company_jobs.json"

def load_existing_jobs():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_jobs(jobs):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4)

def is_india(location):
    if not location: return True
    loc = location.lower()
    indian_keywords = [
        "india", "ind", "bangalore", "bengaluru", "hyderabad", "chennai", 
        "pune", "mumbai", "gurgaon", "noida", "delhi", "remote", 
        "karnataka", "maharashtra", "telangana", "tamil nadu", "haryana"
    ]
    return any(k in loc for k in indian_keywords)

def store_jobs_local(jobs, existing_jobs, company_name):
    if not jobs:
        return 0
    
    india_jobs = [j for j in jobs if is_india(j.get("location", ""))]
    if not india_jobs:
        return 0
        
    fetched_at = datetime.now().strftime("%Y-%m-%d")
    total_inserted = 0
    
    existing_urls = {j.get("apply_url") for j in existing_jobs if j.get("apply_url")}
    
    for job in india_jobs:
        url = job.get("apply_url", "")
        if url and url not in existing_urls:
            job["company"] = company_name
            job["fetched_at"] = fetched_at
            existing_jobs.append(job)
            existing_urls.add(url)
            total_inserted += 1
            
    return total_inserted

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*",
}

def clean(text):
    if not text:
        return ""
    return re.sub(r'[^\x00-\x7F]+', ' ', str(text)).strip()


# ============================================================================
#  NEW DISCOVERED APIs (Direct HTTP)
# ============================================================================

def scrape_atlassian(url, limit=2):
    try:
        resp = requests.get("https://www.atlassian.com/endpoint/careers/listings?location=India", headers=HEADERS, timeout=10)
        data = resp.json()
        jobs = []
        if isinstance(data, list):
            for j in data[:limit]:
                post = j.get("portalJobPost", {})
                locs = post.get("locations", [])
                loc = locs[0].get("name", "") if locs else ""
                jobs.append({
                    "title": clean(post.get("title", "")),
                    "location": clean(loc),
                    "posted": "",
                    "apply_url": post.get("portalUrl", url),
                    "total_jobs": len(data)
                })
        return jobs
    except Exception as e:
        print(f"    Atlassian API error: {e}")
    return []

def scrape_rocketlane(url, limit=2):
    try:
        resp = requests.get("https://careers.kula.ai/api/internal/ats_job_posts?accountName=rocketlane&page=1&type=ats_job_post.index", headers=HEADERS, timeout=10)
        data = resp.json()
        items = data.get("data", []) if isinstance(data, dict) else data
        jobs = []
        if isinstance(items, list):
            for j in items[:limit]:
                jobs.append({
                    "title": clean(j.get("title", j.get("name", ""))),
                    "location": clean(j.get("location", "")),
                    "posted": "",
                    "apply_url": url,
                    "total_jobs": len(items)
                })
        return jobs
    except Exception as e:
        print(f"    Rocketlane API error: {e}")
    return []

def scrape_citi_html(url, limit=2):
    try:
        resp = requests.get("https://jobs.citi.com/search-jobs/India/287/2/1269750/22/79/50/2", headers={**HEADERS, "Accept":"text/html"}, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("#search-results-list li")
        total_match = re.search(r"(\d[\d,]*)\s*Results", soup.get_text())
        total = int(total_match.group(1).replace(",","")) if total_match else len(items)
        jobs = []
        for item in items[:limit]:
            t = item.select_one("h2")
            l = item.select_one(".job-location, [class*=location]")
            a = item.select_one("a")
            jobs.append({
                "title": clean(t.get_text(strip=True) if t else ""),
                "location": clean(l.get_text(strip=True) if l else ""),
                "posted": "",
                "apply_url": f"https://jobs.citi.com{a['href']}" if a and a.get("href") else url,
                "total_jobs": total
            })
        return jobs
    except Exception as e:
        print(f"    Citi HTML error: {e}")
    return []

def scrape_comcast_html(url, limit=2):
    try:
        resp = requests.get("https://jobs.comcast.com/search-jobs/India/45483/2/1269750/22/79/25/2", headers={**HEADERS, "Accept":"text/html"}, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("#search-results-list li")
        total_match = re.search(r"(\d[\d,]*)\s*Results", soup.get_text())
        total = int(total_match.group(1).replace(",","")) if total_match else len(items)
        jobs = []
        for item in items[:limit]:
            t = item.select_one("h2")
            l = item.select_one(".job-location")
            a = item.select_one("a")
            jobs.append({
                "title": clean(t.get_text(strip=True) if t else ""),
                "location": clean(l.get_text(strip=True) if l else ""),
                "posted": "",
                "apply_url": f"https://jobs.comcast.com{a['href']}" if a and a.get("href") else url,
                "total_jobs": total
            })
        return jobs
    except Exception as e:
        print(f"    Comcast HTML error: {e}")
    return []


def scrape_bofa(url, limit=2):
    try:
        resp = requests.get("https://careers.bankofamerica.com/services/jobssearchservlet?search=jobsByLocation&searchstring=India&start=0&rows=10", headers=HEADERS, timeout=10)
        data = resp.json()
        jobs = []
        for j in data.get("jobsList", [])[:limit]:
            jobs.append({
                "title": clean(j.get("postingTitle", "")),
                "location": clean(j.get("location", "")),
                "posted": clean(j.get("postedDate", "")),
                "apply_url": "https://careers.bankofamerica.com" + str(j.get("jcrURL", "")),
                "total_jobs": data.get("totalMatches", 0)
            })
        return jobs
    except Exception as e:
        print(f"    BofA API error: {e}")
    return []

def scrape_zerodha(url, limit=2):
    try:
        resp = requests.get("https://careers.zerodha.com/api/jobs", headers=HEADERS, timeout=10)
        data = resp.json()
        items = data.get("data", [])
        jobs = []
        for j in items[:limit]:
            jobs.append({
                "title": clean(j.get("title", "")),
                "location": clean(j.get("location", "")),
                "posted": "",
                "apply_url": url,
                "total_jobs": data.get("count", len(items))
            })
        return jobs
    except Exception as e:
        print(f"    Zerodha API error: {e}")
    return []

# ============================================================================
#  GOOGLE (HTML scraping - no browser!) + MICROSOFT (Eightfold API)
# ============================================================================

def scrape_google_html(url, limit=2):
    """Scrape Google jobs via direct HTML parsing - NO browser needed. Fast pagination."""
    try:
        jobs = []
        page = 1
        while len(jobs) < limit:
            params = {"hl": "en_US", "location": "India"}
            if page > 1:
                params["page"] = page
                
            resp = requests.get(
                "https://www.google.com/about/careers/applications/jobs/results",
                headers={"User-Agent": "Mozilla/5.0 (compatible; JobAggregator/1.0)"},
                params=params, timeout=30
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            
            links_found = 0
            for a in soup.find_all("a", attrs={"aria-label": True, "href": True}):
                label = a["aria-label"]
                if label.startswith("Learn more about"):
                    title = label.replace("Learn more about", "").strip()
                    href = urljoin("https://www.google.com/about/careers/applications/", a["href"])
                    # Canonicalize href
                    parts = urlsplit(href)
                    href = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
                    
                    if not any(j["apply_url"] == href for j in jobs):
                        # Attempt to extract location from the parent card
                        location_text = "India"
                        card = a.find_parent("li") or a.find_parent("div", class_=lambda c: c and "card" in c.lower())
                        if card:
                            card_text = card.get_text(separator=" | ", strip=True)
                            if "place | " in card_text:
                                loc_parts = card_text.split("place | ")
                                if len(loc_parts) > 1:
                                    location_text = loc_parts[1].split(" | ")[0]
                                    
                        jobs.append({
                            "title": clean(title),
                            "location": location_text,
                            "posted": "",
                            "apply_url": href,
                            "total_jobs": 0 # Unknown
                        })
                        links_found += 1
                        if len(jobs) >= limit:
                            break
                            
            if links_found == 0:
                break
                
            page += 1
            time.sleep(0.5)
            
        return jobs
    except Exception as e:
        print(f"    Google HTML scraper error: {e}")
    return []


def scrape_microsoft_api(url, limit=2):
    """Scrape Microsoft jobs via Eightfold API - NO browser needed."""
    try:
        BASE = "https://apply.careers.microsoft.com"
        jobs = []
        offset = 0
        batch_size = 50
        
        while len(jobs) < limit:
            fetch_size = min(batch_size, limit - len(jobs))
            params = {
                "domain": "microsoft.com",
                "query": "",
                "location": "India",
                "start": offset,
                "sort_by": "timestamp",
            }
            resp = requests.get(
                f"{BASE}/api/pcsx/search",
                params=params,
                headers={"accept": "application/json", "user-agent": "Mozilla/5.0"},
                timeout=15
            )
            
            if resp.status_code != 200:
                break
                
            data = resp.json()
            positions = data.get("data", {}).get("positions", [])
            total = data.get("data", {}).get("total", 0)
            
            if not positions:
                break
                
            for p in positions:
                locs = p.get("locations", [])
                loc_str = ", ".join(locs) if isinstance(locs, list) else str(locs)
                jobs.append({
                    "title": clean(p.get("name", "")),
                    "location": clean(loc_str),
                    "posted": "",
                    "apply_url": BASE + p.get("positionUrl", ""),
                    "total_jobs": total,
                    "department": clean(p.get("department", "")),
                })
                
            offset += len(positions)
            if len(positions) < fetch_size:
                break
                
        return jobs[:limit]
    except Exception as e:
        print(f"    Microsoft API error: {e}")
    return []


# ============================================================================
#  GREENHOUSE API (PhonePe, Razorpay, Postman, etc.)
# ============================================================================

def scrape_greenhouse(url, limit=2):
    """Scrape Greenhouse jobs via public boards API."""
    parsed = urlparse(url)
    board = None
    if "greenhouse.io" in parsed.netloc:
        path_parts = [p for p in parsed.path.split("/") if p]
        # boards-api.greenhouse.io/v1/boards/{board}/jobs → index 2
        # job-boards.greenhouse.io/{board}/jobs → index 0
        if "boards-api" in parsed.netloc and len(path_parts) >= 3:
            board = path_parts[2]   # /v1/boards/{board}/jobs
        else:
            board = path_parts[0]   # /{board}/jobs
    if not board:
        return []
    try:
        resp = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true",
            headers=HEADERS, timeout=15
        )
        data = resp.json()
        all_jobs = data.get("jobs", [])
        total = data.get("meta", {}).get("total", len(all_jobs))
        jobs = []
        for j in all_jobs[:limit]:
            loc = j.get("location", {}).get("name", "") if isinstance(j.get("location"), dict) else ""
            jobs.append({
                "title": clean(j.get("title", "")),
                "location": clean(loc),
                "posted": clean(str(j.get("updated_at", ""))[:10]),
                "apply_url": j.get("absolute_url", ""),
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    Greenhouse API error: {e}")
    return []


def scrape_lever(url, limit=2):
    """Scrape Lever jobs via public postings API.
    Supports: api.lever.co/v0/postings/{company}?mode=json"""
    parsed = urlparse(url)
    # Extract company slug from URL path: /v0/postings/{slug}
    path_parts = [p for p in parsed.path.split("/") if p]
    slug = path_parts[2] if len(path_parts) >= 3 else (path_parts[-1] if path_parts else None)
    if not slug:
        return []
    try:
        resp = requests.get(
            f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=50",
            headers=HEADERS, timeout=15
        )
        data = resp.json()
        # Lever returns a flat list of postings
        all_jobs = data if isinstance(data, list) else []
        total = len(all_jobs)
        jobs = []
        for j in all_jobs[:limit]:
            cats = j.get("categories", {})
            loc = cats.get("location", cats.get("allLocations", [""])[0] if cats.get("allLocations") else "")
            jobs.append({
                "title": clean(j.get("text", j.get("title", ""))),
                "location": clean(loc),
                "posted": "",
                "apply_url": j.get("hostedUrl", j.get("applyUrl", url)),
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    Lever API error: {e}")
    return []


# ============================================================================
#  ORACLE CLOUD HCM (JPMC, Hexaware)
# ============================================================================

def scrape_oracle_cloud(url, limit=2):
    """Scrape Oracle Cloud HCM career sites (JPMC, Hexaware) via REST API."""
    parsed = urlparse(url)
    
    # Map known career portal URLs to their actual Oracle Cloud API base
    domain = parsed.netloc.lower()
    if "hexaware" in domain or "jobs.hexaware" in domain:
        base = "https://eeho.fa.us2.oraclecloud.com"
        site_number = "CX_1"
    else:
        base = f"{parsed.scheme}://{parsed.netloc}"
        site_match = re.search(r'sites/([^/]+)', url)
        site_number = site_match.group(1) if site_match else "CX_1001"
    
    # Extract location params if present
    loc_id = ""
    loc_match = re.search(r'locationId=(\d+)', url)
    if loc_match:
        loc_id = f",locationId={loc_match.group(1)}"
    
    try:
        api_url = f"{base}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber={site_number},limit={limit}{loc_id},sortBy=POSTING_DATES_DESC"
        resp = requests.get(api_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            return []
        
        reqs = items[0].get("requisitionList", [])
        total = items[0].get("TotalJobsCount", len(reqs))
        
        jobs = []
        for j in reqs[:limit]:
            jobs.append({
                "title": clean(j.get("Title", "")),
                "location": clean(j.get("PrimaryLocation", "")),
                "posted": clean(str(j.get("PostedDate", ""))[:10]),
                "apply_url": f"{base}/hcmUI/CandidateExperience/en/sites/{site_number}/job/{j.get('Id', '')}",
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    Oracle Cloud API error: {e}")
    return []


# ============================================================================
#  PLAYWRIGHT INTERCEPTORS (for cookie-protected APIs)
# ============================================================================

def _playwright_api_intercept(page_url, api_keyword, limit=2, wait_ms=10000):
    """Generic Playwright interceptor that targets a specific API keyword."""
    jobs = []
    raw_data = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            def handle_response(response):
                if api_keyword in response.url:
                    try:
                        raw_data.append(response.json())
                    except:
                        pass

            page.on("response", handle_response)
            page.goto(page_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(wait_ms)
            browser.close()
    except Exception as e:
        print(f"    Playwright intercept error: {e}")
    return raw_data


def scrape_salesforce_careers(url, limit=2):
    """Scrape Salesforce via direct HTML parsing (no Playwright needed)."""
    jobs = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        cards = soup.select('.card-job')
        
        # Try to find total count
        total = len(cards)
        count_elem = soup.select_one('.job-count strong:last-child')
        if count_elem and count_elem.text.isdigit():
            total = int(count_elem.text)
            
        for c in cards[:limit]:
            title_elem = c.select_one('.card-title a')
            loc_elem = c.select_one('.location')
            
            title = title_elem.text.strip() if title_elem else "Unknown"
            apply_url = title_elem['href'] if title_elem and title_elem.has_attr('href') else url
            if apply_url.startswith('/'):
                apply_url = "https://careers.salesforce.com" + apply_url
                
            loc = loc_elem.text.strip() if loc_elem else ""
            
            jobs.append({
                "title": clean(title),
                "location": clean(loc),
                "posted": "",
                "apply_url": apply_url,
                "total_jobs": total,
            })
    except Exception as e:
        print(f"    Salesforce HTML parse error: {e}")
    return jobs


def scrape_latentview(url, limit=2):
    """Scrape LatentView via Darwinbox direct POST API."""
    try:
        resp = requests.post(
            "https://latentview.darwinbox.in/ms/candidateapi/job/alljobs?companyId=main",
            headers={**HEADERS, "Content-Type": "application/json"},
            json={}, timeout=15
        )
        data = resp.json()
        items = data.get("data", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = []
        total = len(items)
        jobs = []
        for j in items[:limit]:
            title = j.get("designation_display_name") or j.get("designation") or j.get("job_title", "")
            loc_list = j.get("location", j.get("city", ""))
            loc = ", ".join(loc_list) if isinstance(loc_list, list) else str(loc_list)
            jobs.append({
                "title": clean(title),
                "location": clean(loc),
                "posted": clean(str(j.get("created_on", ""))[:10]),
                "apply_url": f"https://latentview.darwinbox.in/ms/candidatev2/main/careers/allJobs#{j.get('id','')}",
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    LatentView Darwinbox error: {e}")
    return []


def scrape_capgemini(url, limit=2):
    """Scrape Capgemini via Playwright intercepting wp-json job-search API."""
    raw = _playwright_api_intercept(
        "https://www.capgemini.com/in-en/careers/join-capgemini/job-search/?page=1&size=11&country_code=in-en",
        "job-search", limit
    )
    jobs = []
    for data in raw:
        items = data.get("results", data.get("jobs", data.get("data", []))) if isinstance(data, dict) else data
        if not isinstance(items, list):
            continue
        total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
        for j in items[:limit]:
            title = j.get("title", j.get("name", ""))
            loc = j.get("location", j.get("country", ""))
            if isinstance(loc, list):
                loc = ", ".join(str(l) for l in loc)
            jobs.append({
                "title": clean(str(title)),
                "location": clean(str(loc)),
                "posted": "",
                "apply_url": j.get("url", j.get("link", url)),
                "total_jobs": total,
            })
        if jobs:
            break
    return jobs[:limit]


def scrape_accenture(url, limit=2):
    """Scrape Accenture via multipart/form-data POST to elastic findjobs API.
    Confirmed endpoint: POST https://www.accenture.com/api/accenture/elastic/findjobs
    Uses multipart form data (NOT JSON body).
    """
    try:
        form_data = {
            "startIndex": (None, "0"),
            "maxResultSize": (None, str(max(limit, 12))),
            "jobKeyword": (None, ""),
            "jobCountry": (None, "India"),
            "jobLanguage": (None, "en"),
            "countrySite": (None, "in-en"),
            "sortBy": (None, "2"),
            "searchType": (None, "vectorSearch"),
            "enableQueryBoost": (None, "true"),
            "minScore": (None, "0.6"),
            "score": (None, "true"),
            "totalHits": (None, "true"),
            "debugQuery": (None, "false"),
        }
        headers = {
            "User-Agent": HEADERS["User-Agent"],
            "Referer": "https://www.accenture.com/in-en/careers/jobsearch",
            "Origin": "https://www.accenture.com",
            "Accept": "*/*",
        }
        resp = requests.post(
            "https://www.accenture.com/api/accenture/elastic/findjobs",
            headers=headers,
            files=form_data,
            timeout=20
        )
        data = resp.json()
        items = data.get("data", [])
        total = data.get("totalHits", len(items))
        jobs = []
        for j in items[:limit]:
            loc_list = j.get("location", j.get("feedCity", ""))
            loc = ", ".join(loc_list) if isinstance(loc_list, list) else str(loc_list)
            jobs.append({
                "title": clean(j.get("title", "")),
                "location": clean(loc),
                "posted": clean(j.get("postedDateText", "")[:10]),
                "apply_url": f"https://www.accenture.com/in-en/careers/jobdetails?id={j.get('guid','')}",
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    Accenture findjobs error: {e}")
    return []


def scrape_tiger_analytics(url, limit=2):
    """Scrape Tiger Analytics via SenseHQ Next.js __NEXT_DATA__ JSON.
    Jobs are pre-loaded in the page's __NEXT_DATA__ script tag under props.pageProps.jobsData
    """
    try:
        resp = requests.get(
            "https://tiger-analytics.sensehq.com/careers/jobs/",
            headers=HEADERS, timeout=15
        )
        from bs4 import BeautifulSoup
        import json as _json
        soup = BeautifulSoup(resp.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            return []
        data = _json.loads(script.string)
        jobs_data = data.get("props", {}).get("pageProps", {}).get("jobsData", {})
        items = jobs_data.get("rows", []) if isinstance(jobs_data, dict) else jobs_data
        if not items:
            return []
        total = jobs_data.get("count", len(items)) if isinstance(jobs_data, dict) else len(items)
        jobs = []
        for j in items[:limit]:
            loc = j.get("location", j.get("office", {}).get("city", ""))
            jobs.append({
                "title": clean(j.get("title", "")),
                "location": clean(loc),
                "posted": "",
                "apply_url": f"https://tiger-analytics.sensehq.com/careers/jobs/{j.get('id','')}",
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    Tiger Analytics SenseHQ error: {e}")
    return []


def scrape_virtusa(url, limit=2):
    """Scrape Virtusa via confirmed GraphQL endpoint.
    POST https://prod.agenticweb-marketing.com/careers/graphql
    Query: JobListResultsQuery with isList=true
    """
    gql_query = """
      query JobListResultsQuery($isList: String!) {
        jobListResults(isList: $isList) {
          results {
            title
            careerCtaLink
            country
            city
            state
            postedDate
            contestNumber
            jobField
            employeeStatus
          }
        }
      }
    """
    try:
        headers = {
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://www.virtusa.com",
            "Referer": "https://www.virtusa.com/",
            "x-cache-graphql": "true",
        }
        resp = requests.post(
            "https://prod.agenticweb-marketing.com/careers/graphql",
            headers=headers,
            json={"query": gql_query, "variables": {"isList": "true"}},
            timeout=20
        )
        data = resp.json()
        results = data.get("data", {}).get("jobListResults", {}).get("results", [])
        # Filter India jobs
        india_jobs = [j for j in results if j.get("country", "") == "India"]
        all_jobs = india_jobs if india_jobs else results
        total = len(results)
        jobs = []
        for j in all_jobs[:limit]:
            city = j.get("city", "")
            country = j.get("country", "")
            loc = f"{city}, {country}".strip(", ") if city else country
            link = j.get("careerCtaLink", "")
            apply_url = f"https://www.virtusa.com{link}" if link.startswith("/") else link
            jobs.append({
                "title": clean(j.get("title", "")),
                "location": clean(loc),
                "posted": clean(str(j.get("postedDate", ""))[:10]),
                "apply_url": apply_url,
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    Virtusa GraphQL error: {e}")
    return []


def scrape_turing(url, limit=2):
    """Scrape Turing via direct REST API."""
    try:
        resp = requests.get("https://careers.turing.com/api/v3/job-posts", headers=HEADERS, timeout=15)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("jobs", data.get("data", []))
        total = len(items)
        jobs = []
        for j in items[:limit]:
            jobs.append({
                "title": clean(j.get("post_title", j.get("title", ""))),
                "location": clean(j.get("post_location_name", j.get("location", ""))),
                "posted": "",
                "apply_url": f"https://careers.turing.com/jobs/{j.get('post_id','')}" if j.get("post_id") else url,
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    Turing API error: {e}")
    return []


def scrape_paypal(url, limit=2):
    """Scrape PayPal via Eightfold API."""
    try:
        resp = requests.get(
            "https://paypal.eightfold.ai/api/pcsx/search?domain=paypal.com&location=india&start=0&sort_by=distance",
            headers=HEADERS, timeout=15
        )
        data = resp.json()
        positions = data.get("data", {}).get("positions", [])
        total = data.get("data", {}).get("count", len(positions))
        jobs = []
        for j in positions[:limit]:
            loc_list = j.get("locations", [])
            loc = ", ".join(loc_list) if isinstance(loc_list, list) else str(loc_list)
            jobs.append({
                "title": clean(j.get("name", "")),
                "location": clean(loc),
                "posted": "",
                "apply_url": f"https://paypal.eightfold.ai/careers?pid={j.get('id','')}",
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    PayPal Eightfold error: {e}")
    return []


def scrape_citi(url, limit=2):
    """Scrape Citi via Eightfold API."""
    try:
        resp = requests.get(
            "https://citi.eightfold.ai/api/pcsx/search?domain=citi.com&location=india&start=0&sort_by=distance",
            headers=HEADERS, timeout=15
        )
        data = resp.json()
        positions = data.get("data", {}).get("positions", [])
        total = data.get("data", {}).get("count", len(positions))
        jobs = []
        for j in positions[:limit]:
            loc_list = j.get("locations", [])
            loc = ", ".join(loc_list) if isinstance(loc_list, list) else str(loc_list)
            jobs.append({
                "title": clean(j.get("name", "")),
                "location": clean(loc),
                "posted": "",
                "apply_url": f"https://jobs.citi.com/job/{j.get('id','')}",
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    Citi Eightfold error: {e}")
    return []


def scrape_ltimindtree(url, limit=2):
    """Scrape LTIMindtree via HTML parsing (Workday URL is dead, direct API requires CSRF)."""
    try:
        resp = requests.get(
            "https://careers.ltimindtree.com/search/?q=&locationsearch=India",
            headers=HEADERS, timeout=15
        )
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.find_all("tr", class_="data-row")
        jobs = []
        for row in rows[:limit]:
            title_tag = row.find("span", class_="jobTitle")
            loc_tag = row.find("span", class_="jobLocation")
            date_tag = row.find("span", class_="jobDate")
            
            title = title_tag.get_text(strip=True) if title_tag else ""
            # The title is often duplicated in the HTML, split by uppercase if needed
            if len(title) > 0 and title[:len(title)//2] == title[len(title)//2:]:
                title = title[:len(title)//2]
                
            loc = loc_tag.get_text(strip=True) if loc_tag else "India"
            # Location is also duplicated
            if len(loc) > 0 and loc[:len(loc)//2] == loc[len(loc)//2:]:
                loc = loc[:len(loc)//2]
                
            posted = date_tag.get_text(strip=True) if date_tag else ""
            if len(posted) > 0 and posted[:len(posted)//2] == posted[len(posted)//2:]:
                posted = posted[:len(posted)//2]
                
            link_tag = row.find("a", class_="jobTitle-link")
            link = f"https://careers.ltimindtree.com{link_tag['href']}" if link_tag else url
            
            jobs.append({
                "title": clean(title),
                "location": clean(loc),
                "posted": clean(posted),
                "apply_url": link,
                "total_jobs": len(rows),
            })
        return jobs
    except Exception as e:
        print(f"    LTIMindtree error: {e}")
    return []


def scrape_wipro(url, limit=2):
    """Scrape Wipro via SAP SuccessFactors direct POST API."""
    try:
        resp = requests.post(
            "https://careers.wipro.com/services/recruiting/v1/jobs",
            headers={**HEADERS, "Content-Type": "application/json"},
            json={"locale": "en_US", "limit": limit, "offset": 0},
            timeout=15
        )
        data = resp.json()
        items = data.get("jobSearchResult", [])
        total = data.get("totalJobs", len(items))
        jobs = []
        for j in items[:limit]:
            resp_data = j.get("response", {})
            # Title is under unifiedStandardTitle in Wipro SAP SF
            title = resp_data.get("unifiedStandardTitle", resp_data.get("jobTitle", [""]))
            if isinstance(title, list):
                title = title[0] if title else ""
            loc = resp_data.get("sfstd_jobLocation_obj", resp_data.get("jobLocationShort", [""]))
            loc = loc[0] if isinstance(loc, list) and loc else str(loc)
            jobs.append({
                "title": clean(title),
                "location": clean(loc),
                "posted": "",
                "apply_url": f"https://careers.wipro.com/jobs/{resp_data.get('id','')}",
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    Wipro SAP SF error: {e}")
    return []


def scrape_jobspy_multi_city(company_keyword, limit=2):
    """Scrape jobs via JobSpy (LinkedIn) across multiple Indian cities.
    Used for companies where direct API scraping is impossible (HCLTech, Walmart, Chargebee, TCS, etc).
    """
    jobs = []
    seen_urls = set()
    cities = ["Chennai", "Bangalore", "Hyderabad", "Mumbai", "Pune", "Kolkata", "Delhi"]
    search_terms = [
        f"{company_keyword}",
        f"{company_keyword} engineer",
        f"{company_keyword} developer",
    ]
    
    for city in cities:
        if len(jobs) >= limit:
            break
        for term in search_terms:
            if len(jobs) >= limit:
                break
            try:
                df = scrape_jobs(
                    site_name=["linkedin"],
                    search_term=term,
                    location=f"{city}, India",
                    results_wanted=min(5, limit - len(jobs)),
                    country_indeed="India",
                )
                if df.empty:
                    continue
                for _, row in df.iterrows():
                    if len(jobs) >= limit:
                        break
                    job_url = str(row.get("job_url", ""))
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)
                    loc = str(row.get("location", ""))
                    if not loc or loc == "nan":
                        loc = f"{city}, India"
                    jobs.append({
                        "title": str(row.get("title", "")),
                        "location": loc,
                        "posted": str(row.get("date_posted", "")),
                        "apply_url": job_url,
                        "total_jobs": len(df)
                    })
            except Exception as e:
                print(f"    JobSpy ({city}/{term}) error: {e}")
                continue
    
    return jobs[:limit]


def scrape_ramco(url, limit=2):
    """Scrape Ramco Systems careers page (JS-rendered job cards)."""
    jobs = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.ramco.com/careers/jobs-by-locations", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
            
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("a.job-listing__card")
        for card in cards[:limit]:
            title_el = card.select_one(".job-listing__job-title")
            loc_el = card.select_one(".job-listing__job-description")
            href = card.get("href", "")
            
            title = title_el.get_text(strip=True) if title_el else ""
            loc = loc_el.get_text(strip=True) if loc_el else "India"
            apply_url = href if href.startswith("http") else f"https://www.ramco.com{href}"
            
            # Only include India-based jobs
            india_keywords = ["india", "chennai", "mumbai", "bangalore", "bengaluru", "hyderabad", "pune", "delhi", "noida", "gurgaon", "kolkata"]
            if any(kw in loc.lower() for kw in india_keywords):
                jobs.append({
                    "title": clean(title),
                    "location": clean(loc),
                    "posted": "",
                    "apply_url": apply_url,
                    "total_jobs": len(cards)
                })
        
        # If no India jobs found, include all jobs
        if not jobs:
            for card in cards[:limit]:
                title_el = card.select_one(".job-listing__job-title")
                loc_el = card.select_one(".job-listing__job-description")
                href = card.get("href", "")
                title = title_el.get_text(strip=True) if title_el else ""
                loc = loc_el.get_text(strip=True) if loc_el else "India"
                apply_url = href if href.startswith("http") else f"https://www.ramco.com{href}"
                jobs.append({
                    "title": clean(title),
                    "location": clean(loc),
                    "posted": "",
                    "apply_url": apply_url,
                    "total_jobs": len(cards)
                })
    except Exception as e:
        print(f"    Ramco Systems error: {e}")
    return jobs[:limit]



# ============================================================================
#  INFOSYS (Playwright - intercepts getCareerSearchJobs API)
# ============================================================================

def scrape_infosys_playwright(url, limit=2):
    """Scrape Infosys jobs by intercepting getCareerSearchJobs API via Playwright."""
    jobs = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            def handle_response(response):
                nonlocal jobs
                if "getCareerSearchJobs" in response.url and len(jobs) < limit:
                    content_type = response.headers.get("content-type", "")
                    if "json" not in content_type:
                        return
                    try:
                        data = response.json()
                        # Response is a direct list of job objects
                        items = data if isinstance(data, list) else []

                        total = len(items)
                        for j in items[:limit]:
                            title = j.get("postingTitle", "")
                            loc = j.get("location", "")
                            ref = j.get("referenceCode", "")
                            role = j.get("roleDesignation", "")
                            # Combine title and role for clarity
                            display_title = f"{title} - {role}" if role and role != title else title
                            jobs.append({
                                "title": clean(str(display_title)),
                                "location": clean(str(loc)),
                                "posted": clean(str(j.get("createdOn", ""))[:10]),
                                "apply_url": f"https://career.infosys.com/jobdesc?jobReferenceCode={ref}" if ref else url,
                                "total_jobs": total,
                            })
                    except Exception as e:
                        print(f"    Infosys parse error: {e}")

            page.on("response", handle_response)
            listing_url = "https://career.infosys.com/jobs?companyhiringtype=IL&countrycode=IN"
            page.goto(listing_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(10000)
            browser.close()
    except Exception as e:
        print(f"    Infosys Playwright error: {e}")
    return jobs[:limit]


# ============================================================================
#  PLAYWRIGHT INTERCEPTION
# ============================================================================

def scrape_playwright_interceptor(url, company_name, limit=2):
    jobs = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            def handle_response(response):
                nonlocal jobs
                req = response.request
                if req.resource_type in ["fetch", "xhr"] and "json" in response.headers.get("content-type", ""):
                    try:
                        data = response.json()
                        data_str = json.dumps(data).lower()
                        if "job" in data_str and ("title" in data_str or "location" in data_str):
                            items = []
                            if isinstance(data, list): items = data
                            elif isinstance(data, dict):
                                for k, v in data.items():
                                    if isinstance(v, list) and len(v) > 0:
                                        items = v
                                        break
                                if not items and data.get("data") and isinstance(data["data"], list):
                                    items = data["data"]
                                if not items and data.get("jobs") and isinstance(data["jobs"], list):
                                    items = data["jobs"]
                            
                            if items and len(jobs) < limit:
                                for j in items[:limit]:
                                    title = j.get("title", j.get("name", j.get("jobTitle", str(j)[:50])))
                                    loc = j.get("location", j.get("city", ""))
                                    if isinstance(title, str) and len(title) > 3:
                                        jobs.append({
                                            "title": clean(title),
                                            "location": clean(str(loc)),
                                            "posted": "",
                                            "apply_url": url,
                                            "total_jobs": len(items)
                                        })
                    except:
                        pass

            page.on("response", handle_response)
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(8000)
            browser.close()
    except Exception as e:
        print(f"    Playwright Interceptor error: {e}")
    
    return jobs[:limit]

# ============================================================================
#  EXISTING ATS SCRAPERS
# ============================================================================

def scrape_workday(url, limit=2):
    parsed = urlparse(url)
    host = parsed.netloc
    parts = host.split(".")
    if len(parts) < 2: return []
    tenant = parts[0]
    wd_server = parts[1]
    path_parts = [p for p in parsed.path.split("/") if p]
    site = None
    for i, part in enumerate(path_parts):
        if part == "en-US" and i + 1 < len(path_parts):
            site = path_parts[i + 1]
            break
    if not site:
        skip = {"wday", "cxs", "en-US", "job", "jobs", "apply"}
        for part in path_parts:
            if part not in skip and not part.startswith("?"):
                site = part
                break
    if not site: return []
    
    if "wday/cxs" in url and url.endswith("/jobs"):
        api_url = url
        # fallback site for apply URL if it was direct API
        site = path_parts[-3] if len(path_parts) >= 3 else site
    else:
        api_url = f"https://{tenant}.{wd_server}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    jobs = []
    offset = 0
    batch_size = 20
    
    while len(jobs) < limit:
        fetch_size = min(batch_size, limit - len(jobs))
        payload = {"appliedFacets": {}, "limit": fetch_size, "offset": offset, "searchText": ""}
        try:
            resp = requests.post(api_url, headers={**HEADERS, "Content-Type": "application/json"}, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total", 0)
                postings = data.get("jobPostings", [])
                
                if not postings:
                    break
                    
                for job in postings:
                    ext_path = job.get("externalPath", "")
                    apply_url = f"https://{tenant}.{wd_server}.myworkdayjobs.com/en-US/{site}{ext_path}" if ext_path else ""
                    jobs.append({
                        "title": clean(job.get("title", "")),
                        "location": clean(job.get("locationsText", "")),
                        "posted": clean(job.get("postedOn", "")),
                        "apply_url": apply_url,
                        "total_jobs": total,
                    })
                    
                offset += len(postings)
                if offset >= total:
                    break
            else:
                break
        except Exception as e:
            print(f"    Workday API error: {e}")
            break
            
    return jobs

def scrape_eightfold(url, limit=2):
    parsed = urlparse(url)
    subdomain = parsed.netloc.split(".")[0]
    domain_to_use = "eightfold.ai" if "eightfold.ai" in url else parsed.netloc
    
    api_url = f"https://{domain_to_use}/api/apply/v2/jobs?num={limit}&domain={subdomain}.com&sort_by=relevance"
    actual_domain = f"{subdomain}.com"
    if "pcsx/search" in url:
        parts = parsed.netloc.split(".")
        actual_domain = ".".join(parts[-2:]) if len(parts) >= 2 else parsed.netloc
        api_url = f"https://{domain_to_use}/api/pcsx/search?domain={actual_domain}&location=India&start=0&sort_by=relevance"
        
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=10)
        data = resp.json()
        positions = data.get("positions", data.get("data", {}).get("positions", []))
        total = data.get("count", data.get("data", {}).get("total", len(positions)))
        jobs = []
        for job in positions[:limit]:
            loc_list = job.get("location", job.get("locations", []))
            loc = ", ".join(loc_list) if isinstance(loc_list, list) else str(loc_list)
            
            apply_link = f"https://{domain_to_use}/careers/job?pid={job.get('id', '')}&domain={actual_domain}"
            if job.get("positionUrl"):
                apply_link = f"https://{domain_to_use}{job.get('positionUrl')}"
                
            jobs.append({
                "title": clean(job.get("name", "")),
                "location": clean(loc),
                "posted": "",
                "apply_url": apply_link,
                "total_jobs": total,
            })
        return jobs
    except Exception as e:
        print(f"    Eightfold API error: {e}")
    return []

def scrape_smartrecruiters(url, company_name, limit=2):
    # Try public API
    try:
        resp = requests.get(f"https://api.smartrecruiters.com/v1/companies/{company_name}/postings", headers=HEADERS, timeout=10)
        data = resp.json()
        total = data.get("totalFound", 0)
        jobs = []
        for job in data.get("content", [])[:limit]:
            loc = job.get("location", {})
            location_str = f"{loc.get('city', '')}, {loc.get('region', '')}".strip(", ")
            jobs.append({
                "title": clean(job.get("name", "")),
                "location": clean(location_str),
                "posted": clean(job.get("releasedDate", "")[:10]),
                "apply_url": job.get("ref", ""),
                "total_jobs": total,
            })
        return jobs
    except: pass
    return []

def scrape_turbohire_playwright(url, limit=2):
    jobs = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            def handle_response(response):
                nonlocal jobs
                if "filteredjobs" in response.url and response.request.method in ["POST", "GET"]:
                    try:
                        data = response.json()
                        if isinstance(data, dict) and "Result" in data:
                            total_jobs = data.get("Total", 0)
                            for job in data["Result"][:limit]:
                                loc_list = job.get("Location", [])
                                loc_str = loc_list[0].get("Address", "") if loc_list and isinstance(loc_list, list) else ""
                                jobs.append({
                                    "title": clean(job.get("JobTitle", "")),
                                    "location": clean(loc_str),
                                    "posted": "",
                                    "apply_url": url,
                                    "total_jobs": total_jobs,
                                })
                    except: pass
            page.on("response", handle_response)
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(8000)
            browser.close()
    except: pass
    return jobs

def scrape_phenom(url, limit=2):
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    try:
        resp = requests.post(f"{base}/widgets", headers={**HEADERS, "Content-Type": "application/json"},
            json={"lang": "en_global", "deviceType": "desktop", "country": "global", "pageName": "search-results",
                  "ddoKey": "refineSearch", "from": 0, "jobs": True, "counts": True,
                  "all_fields": ["category", "country", "state", "city", "type", "reqId"],
                  "size": limit, "is498": True, "keywords": ""}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            ref = data.get("refineSearch", {})
            hits = ref.get("data", {}).get("jobs", [])
            total = ref.get("totalHits", 0)
            jobs = []
            for j in hits[:limit]:
                loc = f"{j.get('city', '')}, {j.get('country', '')}".strip(", ")
                jobs.append({
                    "title": clean(j.get("title", "")),
                    "location": clean(loc),
                    "posted": "",
                    "apply_url": f"{base}{j.get('canonicalPositionUrl', '')}",
                    "total_jobs": total,
                })
            return jobs
    except: pass
    return []

def scrape_amazon(url, limit=2):
    jobs = []
    offset = 0
    batch_size = 100
    try:
        while len(jobs) < limit:
            fetch_size = min(batch_size, limit - len(jobs))
            api_url = f"https://www.amazon.jobs/en/search.json?offset={offset}&result_limit={fetch_size}&sort=relevant&country=IND"
            resp = requests.get(api_url, headers={**HEADERS, "Accept": "application/json"}, timeout=15)
            if resp.status_code != 200:
                print(f"    Amazon API bad status: {resp.status_code}")
                break
                
            data = resp.json()
            total = data.get("hits", 0)
            batch_jobs = data.get("jobs")
            
            if not batch_jobs:
                break
                
            for j in batch_jobs:
                jobs.append({
                    "title": clean(j.get("title", "")),
                    "location": clean(j.get("normalized_location", "")),
                    "posted": clean(j.get("posted_date", "")),
                    "apply_url": f"https://www.amazon.jobs{j.get('job_path', '')}",
                    "total_jobs": total,
                })
                
            offset += len(batch_jobs)
            if len(batch_jobs) < fetch_size:
                break
                
        return jobs[:limit]
    except Exception as e:
        print(f"    Amazon API error: {e}")
    return jobs[:limit]

def scrape_uber(url, limit=2):
    try:
        resp = requests.post("https://www.uber.com/api/loadSearchJobsResults?localeCode=en", headers={**HEADERS, "Content-Type": "application/json", "x-csrf-token": "x"}, json={"params": {"location": [{"country": "IND"}], "department": [], "team": []}, "limit": limit, "page": 1}, timeout=10)
        data = resp.json()
        results = data.get("data", {}).get("results", [])
        total_obj = data.get("data", {}).get("totalResults", {})
        total = total_obj.get("low", 0) if isinstance(total_obj, dict) else total_obj
        jobs = []
        for j in results[:limit]:
            locs = j.get("allLocations", [])
            loc_str = ", ".join([f"{l.get('city','')} {l.get('country','')}".strip() for l in locs]) if locs else ""
            jobs.append({
                "title": clean(j.get("title", "")),
                "location": clean(loc_str),
                "posted": "",
                "apply_url": f"https://www.uber.com/global/en/careers/list/{j.get('id', '')}/",
                "total_jobs": total,
            })
        return jobs
    except: pass
    return []

def scrape_radancy(url, limit=2):
    """Scrape Radancy HTML or JSON (Target, Intuit, etc.)"""
    jobs = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        html_text = resp.text
        try:
            data = resp.json()
            if "results" in data:
                html_text = data["results"]
        except:
            pass
            
        soup = BeautifulSoup(html_text, 'html.parser')
        # if it was JSON, items are direct <li>s. If it was main page, they are in #search-results-list ul li
        items = soup.select('section#search-results-list ul li')
        if not items:
            items = [li for li in soup.find_all('li') if li.select_one('.job-location') or li.select_one('a')]
            
        for item in items[:limit]:
            title_elem = item.select_one('h2, h3, a')
            loc_elem = item.select_one('.job-location')
            if not title_elem:
                continue
            title = title_elem.text.strip()
            loc = loc_elem.text.strip() if loc_elem else "India"
            a_tag = item.select_one('a')
            apply_url = a_tag['href'] if a_tag and a_tag.has_attr('href') else url
            if apply_url.startswith('/'):
                parsed = urlparse(url)
                apply_url = f"{parsed.scheme}://{parsed.netloc}{apply_url}"
            jobs.append({
                "title": clean(title),
                "location": clean(loc),
                "posted": "",
                "apply_url": apply_url,
                "total_jobs": len(items)
            })
    except Exception as e:
        print(f"    Radancy API error: {e}")
    return jobs

def scrape_successfactors(url, limit=2):
    """Scrape SuccessFactors HTML (SAP Labs, etc.)"""
    jobs = []
    try:
        # Append locationsearch=India if not present
        if "?" not in url:
            url += "?q=&locationsearch=India"
        elif "locationsearch" not in url:
            url += "&locationsearch=India"
            
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select('tr.data-row')
        for item in items[:limit]:
            title_elem = item.select_one('.jobTitle-link')
            loc_elem = item.select_one('.jobLocation')
            date_elem = item.select_one('.jobDate')
            if not title_elem:
                continue
            title = title_elem.text.strip()
            loc = loc_elem.text.strip() if loc_elem else "India"
            date = date_elem.text.strip() if date_elem else ""
            apply_url = title_elem['href']
            if apply_url.startswith('/'):
                parsed = urlparse(url)
                apply_url = f"{parsed.scheme}://{parsed.netloc}{apply_url}"
            jobs.append({
                "title": clean(title),
                "location": clean(loc),
                "posted": clean(date),
                "apply_url": apply_url,
                "total_jobs": len(items)
            })
    except Exception as e:
        print(f"    SuccessFactors HTML API error: {e}")
    return jobs

def scrape_curefit(url, limit=2):
    """Scrape Cure.fit using Zwayam API with Session Emulation."""
    jobs = []
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': 'https://careers.cult.fit/',
            'Origin': 'https://careers.cult.fit',
        }
        # Step A: Collect cookies
        session.get('https://careers.cult.fit/cult/jobslist', headers=headers, timeout=15)
        
        # Step B: Multipart form-data
        payload = {
            'domain': (None, 'careers.cult.fit'),
            'companyId': (None, 'MTU0NzA='),
            'filterCri': (None, '{"paginationStartNo":0,"selectedCall":"sort","sortCriteria":{"name":"modifiedDate","isAscending":false},"anyOfTheseWords":""}')
        }
        resp = session.post('https://public.zwayam.com/jobs/search', files=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json().get('data', {}).get('data', [])
            for j in data[:limit]:
                src = j.get('_source', {})
                jobs.append({
                    "title": clean(src.get("title", "")),
                    "location": clean(src.get("city", "India")),
                    "posted": "",
                    "apply_url": "https://careers.cult.fit/cult/jobslist",
                    "total_jobs": len(data)
                })
    except Exception as e:
        print(f"    Cure.fit Zwayam error: {e}")
    return jobs

def scrape_goldmansachs(url, limit=2):
    """Scrape Goldman Sachs Custom GraphQL API."""
    jobs = []
    try:
        api_url = "https://api-higher.gs.com/gateway/api/v1/graphql"
        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'origin': 'https://higher.gs.com',
            'referer': 'https://higher.gs.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'x-higher-session-id': str(uuid.uuid4())
        }
        
        offset = 0
        batch_size = 20
        while len(jobs) < limit:
            fetch_size = min(batch_size, limit - len(jobs))
            payload = {
                "operationName": "GetRoles",
                "variables": {
                    "searchQueryInput": {
                        "page": {"pageSize": fetch_size, "pageNumber": offset // batch_size},
                        "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"},
                        "filters": [{
                            "filterCategoryType": "LOCATION",
                            "filters": [{
                                "filter": "India",
                                "subFilters": [
                                    {"filter": "Karnataka", "subFilters": [{"filter": "Bengaluru", "subFilters": []}]},
                                    {"filter": "Maharashtra", "subFilters": [{"filter": "Mumbai", "subFilters": []}]},
                                    {"filter": "Telangana", "subFilters": [{"filter": "Hyderabad", "subFilters": []}]}
                                ]
                            }]
                        }],
                        "experiences": ["EARLY_CAREER", "PROFESSIONAL"],
                        "searchTerm": ""
                    }
                },
                "query": "query GetRoles($searchQueryInput: RoleSearchQueryInput!) {\n  roleSearch(searchQueryInput: $searchQueryInput) {\n    totalCount\n    items {\n      roleId\n      corporateTitle\n      jobTitle\n      jobFunction\n      locations {\n        primary\n        state\n        country\n        city\n        __typename\n      }\n      status\n      division\n      skills\n      jobType {\n        code\n        description\n        __typename\n      }\n      externalSource {\n        sourceId\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}"
            }
            
            resp = requests.post(api_url, headers=headers, json=payload, timeout=15)
            if resp.status_code != 200:
                break
                
            data = resp.json().get('data', {}).get('roleSearch', {})
            items = data.get('items', [])
            total_count = data.get('totalCount', 0)
            
            if not items:
                break
                
            for j in items:
                locs = j.get('locations', [])
                city = locs[0].get('city', 'India') if locs else 'India'
                jobs.append({
                    "title": clean(j.get("jobTitle", "")),
                    "location": clean(city),
                    "posted": "",
                    "apply_url": f"https://higher.gs.com/roles/{j.get('roleId', '')}",
                    "total_jobs": total_count
                })
                
            offset += len(items)
            if offset >= total_count:
                break
                
    except Exception as e:
        print(f"    Goldman Sachs API error: {e}")
    return jobs

# ============================================================================
#  ROUTING
# ============================================================================

def detect_and_scrape(company_name, ats_type, url, limit=2):
    if not url: return []
    url_lower = url.lower()
    name_lower = company_name.lower()
    
    # ── COMPANY-SPECIFIC DEDICATED SCRAPERS (checked FIRST, before ATS type) ──
    # These companies have ats="SuccessFactors" in config but need their OWN scrapers
    if "wipro" in name_lower:
        return scrape_wipro(url, limit)
    if "ltimindtree" in name_lower or "lti" in name_lower:
        return scrape_ltimindtree(url, limit)
    if "hcltech" in name_lower or "hcl tech" in name_lower:
        print(f"    [JobSpy/LinkedIn multi-city]")
        return scrape_jobspy_multi_city("HCL Tech", limit)
    
    # ── NEW CUSTOM API SCRAPERS ──
    if ats_type == "Zwayam" or name_lower == "cure.fit":
        return scrape_curefit(url, limit)
    if name_lower == "goldman sachs":
        return scrape_goldmansachs(url, limit)
    if name_lower == "sap labs" or "jobs.sap.com" in url_lower:
        print(f"    [SAP SuccessFactors HTML]")
        return scrape_successfactors(url, limit)
    if name_lower in ["target", "intuit"]:
        print(f"    [Radancy HTML]")
        return scrape_radancy(url, limit)
    
    # ── FAANG / BIG COMPANY DEDICATED SCRAPERS ──
    if name_lower == "google" or "google.com/about/careers" in url_lower:
        print(f"    [Google HTML Scraper]")
        return scrape_google_html(url, limit)
    if name_lower == "microsoft" or "careers.microsoft.com" in url_lower:
        print(f"    [Microsoft API]")
        return scrape_microsoft_api(url, limit)
    if "infosys" in name_lower or "career.infosys.com" in url_lower:
        print(f"    [Infosys Playwright Interceptor]")
        return scrape_infosys_playwright(url, limit)
    
    # ── NEW APIS ──
    if company_name == "Atlassian": return scrape_atlassian(url, limit)
    if company_name == "Rocketlane": return scrape_rocketlane(url, limit)
    if company_name == "Citi": return scrape_citi_html(url, limit)
    if company_name == "Comcast": return scrape_comcast_html(url, limit)
    if company_name == "Turing" or "careers.turing.com" in url_lower: return scrape_turing(url, limit)
    if "bank of america" in name_lower: return scrape_bofa(url, limit)
    if "ramco" in name_lower:
        print(f"    [Ramco Playwright]")
        return scrape_ramco(url, limit)
    if "zerodha" in name_lower: return scrape_zerodha(url, limit)
    
    # ── COMPANY-SPECIFIC DIRECT API SCRAPERS ──
    if "paypal" in name_lower: return scrape_paypal(url, limit)
    if "citi" in name_lower and "citi" in url_lower: return scrape_citi(url, limit)
    if "tiger analytics" in name_lower: return scrape_tiger_analytics(url, limit)
    if "virtusa" in name_lower: return scrape_virtusa(url, limit)
    if "accenture" in name_lower: return scrape_accenture(url, limit)
    
    # ── JOBSPY MULTI-CITY FALLBACK (LinkedIn for companies without direct API) ──
    jobspy_keyword_map = {
        "walmart": "Walmart",
        "chargebee": "Chargebee",
        "tcs": "TCS",
        "mu sigma": "Mu Sigma",
        "latentview": "LatentView Analytics",
        "sify": "Sify Technologies",
        "tata elxsi": "Tata Elxsi",
        "uber": "Uber",
        "wells fargo": "Wells Fargo",
        "kaleidofin": "Kaleidofin",
    }
    for key, keyword in jobspy_keyword_map.items():
        if key in name_lower:
            print(f"    [JobSpy/LinkedIn multi-city]")
            return scrape_jobspy_multi_city(keyword, limit)
    
    # ── EXISTING APIS ──
    if "wells fargo" in name_lower: return scrape_workday("https://wellsfargo.wd5.myworkdayjobs.com/wday/cxs/wellsfargo/jobs", limit)
    if "myworkdayjobs.com" in url_lower: return scrape_workday(url, limit)
    if "amazon.jobs" in url_lower: return scrape_amazon(url, limit)
    if "uber.com" in url_lower and "career" in url_lower: return scrape_uber(url, limit)
    if any(domain in url_lower for domain in ["careers.cisco.com", "careers.athenahealth.com"]):
        return scrape_phenom(url, limit)
        
    # ── ATS PLATFORM SCRAPERS ──
    if "eightfold.ai" in url_lower or "pcsx/search" in url_lower: return scrape_eightfold(url, limit)
    if "smartrecruiters.com" in url_lower or ats_type.lower() == "smartrecruiters":
        return scrape_smartrecruiters(url, company_name.replace(" ", ""), limit)
    if "turbohire.co" in url_lower: return scrape_turbohire_playwright(url, limit)
    if "greenhouse.io" in url_lower: return scrape_greenhouse(url, limit)
    if "lever.co" in url_lower or "api.lever.co" in url_lower: return scrape_lever(url, limit)
    
    # ── GREENHOUSE COMPANIES (direct board name lookup) ──
    greenhouse_map = {
        "inmobi": "inmobi", "glance": "inmobi",
        "groww": "groww",
    }
    for key, board in greenhouse_map.items():
        if key in name_lower:
            return scrape_greenhouse(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true", limit)
    
    # ── LEVER COMPANIES (direct posting lookup) ──
    lever_map = {
        "zeta": "zeta",
        "meesho": "meesho",
    }
    for key, slug in lever_map.items():
        if key in name_lower:
            return scrape_lever(f"https://api.lever.co/v0/postings/{slug}?mode=json", limit)
    
    # ── ORACLE CLOUD (JPMC, Hexaware, Honeywell) ──
    if "oraclecloud.com" in url_lower or "hexaware.com" in url_lower or "honeywell" in name_lower:
        print(f"    [Oracle Cloud API]")
        return scrape_oracle_cloud(url, limit)
    
    # ── COMPANY-SPECIFIC PLAYWRIGHT INTERCEPTORS ──
    if "salesforce" in name_lower or "careers.salesforce.com" in url_lower:
        print(f"    [Salesforce Playwright]")
        return scrape_salesforce_careers(url, limit)
    if "capgemini" in name_lower:
        print(f"    [Capgemini Playwright]")
        return scrape_capgemini(url, limit)

    # ── PLAYWRIGHT FALLBACK (last resort) ──
    print(f"    [Playwright Interceptor]")
    jobs = scrape_playwright_interceptor(url, company_name, limit)
    
    return jobs

# ============================================================================
#  MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("  FINAL MASTER JOB SCRAPER")
    print("=" * 70)

    try:
        with open("companies_links.json", "r", encoding="utf-8") as f:
            companies = json.load(f)
    except FileNotFoundError:
        print("  Error: companies_links.json not found.")
        return

    existing_jobs = load_existing_jobs()
    print(f"  Loaded {len(existing_jobs)} existing jobs from {DB_FILE}.")

    all_results = []
    working_companies = []
    not_working_companies = []
    total_new_jobs = 0

    for i, company in enumerate(companies):
        name = company["company"]
        ats = company.get("ats", "Unknown")
        urls = company.get("urls", [])

        print(f"\n[{i+1}/{len(companies)}] {name} ({ats})")

        if not urls:
            print(f"    -> NO LINK")
            not_working_companies.append(name)
            continue

        url = urls[0]
        jobs = detect_and_scrape(name, ats, url, limit=1000)

        if jobs:
            newly_inserted = store_jobs_local(jobs, existing_jobs, name)
            total_new_jobs += newly_inserted
            working_companies.append(name)
            all_results.extend(jobs)
            print(f"    -> SUCCESS: Scraped {len(jobs)} jobs | Newly Inserted to DB: {newly_inserted}")
        else:
            not_working_companies.append(name)
            print(f"    -> FAILED (No jobs found or error)")

    if total_new_jobs > 0:
        save_jobs(existing_jobs)
        print(f"\n  Successfully updated {DB_FILE} with new jobs.")

    print("\n" + "=" * 70)
    print("  FINAL SCRAPE REPORT")
    print("=" * 70)
    print(f"  Total Companies Checked : {len(companies)}")
    print(f"  Working Companies       : {len(working_companies)}")
    print(f"  Failed Companies        : {len(not_working_companies)}")
    print(f"  Total Jobs Scraped      : {len(all_results)}")
    print(f"  NEW JOBS ADDED TO DB    : {total_new_jobs}")
    print("\n  [WORKING COMPANIES]")
    print("  " + ", ".join(working_companies))
    print("\n  [NOT WORKING COMPANIES]")
    print("  " + ", ".join(not_working_companies))
    print("=" * 70)

if __name__ == "__main__":
    main()