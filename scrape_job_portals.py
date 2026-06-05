import os
import sys
import re
import json
import time
import random
import urllib.parse
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Configure stdout to handle UTF-8 printing cleanly on Windows
sys.stdout.reconfigure(encoding='utf-8')
requests.packages.urllib3.disable_warnings()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
ACCOUNT_ID = "62eacb67a7ee0b199f58ccb540a3eff7"
DATABASE_ID = "20b71b5c-c070-45b5-9542-27ed1cad89e5"

# Priority for ScraperAPI Key: SCRAPERAPI_KEY_2 ONLY
SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY_2", "")

# Oxylabs Proxies Config
OXYLABS_USER = os.environ.get("OXYLABS_USERNAME", "")
OXYLABS_PASS = os.environ.get("OXYLABS_PASSWORD", "")
OXYLABS_HOST = os.environ.get("OXYLABS_ENTRYPOINT", "").strip() or "dc.oxylabs.io"
OXYLABS_PORTS_STR = os.environ.get("OXYLABS_PORTS", "").strip() or "8001,8002,8003,8004,8005"

# Toggle this flag to scrape only Naukri or all 10 portals
SCRAPE_ONLY_NAUKRI = True

oxylabs_proxies = []
if OXYLABS_USER and OXYLABS_PASS:
    ports = [p.strip() for p in OXYLABS_PORTS_STR.split(",") if p.strip()]
    for port in ports:
        oxylabs_proxies.append(f"http://{OXYLABS_USER}:{OXYLABS_PASS}@{OXYLABS_HOST}:{port}")

# Global Playwright Browser Instances
playwright_instance = None
browser_instance = None

# Progress Checkpointing Configuration
PROGRESS_FILE = "job_portals_progress.json"
START_TIME = time.time()
MAX_RUN_SECONDS = 5 * 3600 + 40 * 60  # 5 hours 40 minutes (leaves 20 min buffer under 6h limit)

def load_progress():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
        if data.get("date") != today:
            print(f"📅 New day detected (was {data.get('date')}, now {today}). Resetting progress to start.")
            return {"role_idx": 0, "loc_idx": 0, "date": today}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"role_idx": 0, "loc_idx": 0, "date": today}

def save_progress(role_idx, loc_idx, finished_all=False):
    today = datetime.now().strftime("%Y-%m-%d")
    if finished_all:
        data = {"role_idx": 0, "loc_idx": 0, "date": today, "finished": True}
    else:
        data = {"role_idx": role_idx, "loc_idx": loc_idx, "date": today, "finished": False}
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)

def init_playwright():
    global playwright_instance, browser_instance
    try:
        from playwright.sync_api import sync_playwright
        playwright_instance = sync_playwright().start()
        browser_instance = playwright_instance.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        print("🚀 Playwright Chromium browser initialized successfully!")
    except Exception as e:
        print(f"⚠️ Playwright initialization error: {e}")

def close_playwright():
    global playwright_instance, browser_instance
    try:
        if browser_instance:
            browser_instance.close()
        if playwright_instance:
            playwright_instance.stop()
        print("🛑 Playwright Chromium browser closed.")
    except Exception as e:
        print(f"⚠️ Error closing Playwright: {e}")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

# Roles & Cities
SEARCH_ROLES = [
    "Software Developer",
    "Software Engineer",
]

LOCATIONS = [
    "Bangalore",
    "Chennai",
]

TEST_MODE = "--test" in sys.argv
TEST_LIMIT = 1
if TEST_MODE:
    print("🧪 RUNNING IN TEST MODE: Only 1 role and 1 location will be scraped.")
    SEARCH_ROLES = ["Software Engineer"]
    LOCATIONS = ["Bangalore"]

# ---------------------------------------------------------------------------
# DATABASE HELPERS (Cloudflare D1 REST API)
# ---------------------------------------------------------------------------
def d1_execute(sql, params=None):
    if not CLOUDFLARE_API_TOKEN:
        print("⚠️ CLOUDFLARE_API_TOKEN not configured, skipping D1 database execution.")
        return None
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"sql": sql, "params": params or []}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        if resp.status_code == 200:
            return resp.json()
        print(f"❌ D1 Error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ D1 Connection error: {e}")
    return None

def store_jobs_batch(jobs):
    if not jobs:
        return 0
    
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    unique_jobs = []
    seen_urls = set()
    for j in jobs:
        url = j.get("url")
        date_str = j.get("date_posted", "")
        # Filter out jobs that are 30 days or older
        if date_str and date_str < cutoff_date:
            continue
        if url and url not in seen_urls:
            unique_jobs.append(j)
            seen_urls.add(url)
            
    if not unique_jobs:
        return 0
        
    inserted_count = 0
    for i in range(0, len(unique_jobs), 10):
        chunk = unique_jobs[i:i+10]
        placeholders = []
        params = []
        for job in chunk:
            placeholders.append("(?, ?, ?, ?, ?, ?, ?)")
            params.extend([
                str(job.get("company", "")),
                str(job.get("location", "")),
                str(job.get("title", "")),
                str(job.get("date_posted", datetime.now().strftime("%Y-%m-%d"))),
                str(job.get("url", "")),
                str(job.get("source", "")),
                str(job.get("role_search", ""))
            ])
        sql = f"INSERT OR IGNORE INTO all_jobs (company_name, location, role, job_posted_date, apply_link, platform, search_keyword) VALUES {','.join(placeholders)}"
        result = d1_execute(sql, params)
        if result and result.get("success"):
            for res in result.get("result", []):
                inserted_count += res.get("meta", {}).get("changes", 0)
    return inserted_count

def cleanup_old_jobs():
    if not CLOUDFLARE_API_TOKEN:
        return
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    print(f"🧹 Cleaning jobs older than {cutoff} (30 days retention)...")
    result = d1_execute("DELETE FROM all_jobs WHERE job_posted_date < ?", [cutoff])
    if result and result.get("success"):
        for res in result.get("result", []):
            deleted = res.get("meta", {}).get("changes", 0)
            print(f"🗑️ Removed {deleted} old jobs from D1 database.")

# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------
def get_oxylabs_proxy():
    if oxylabs_proxies:
        p = random.choice(oxylabs_proxies)
        return {"http": p, "https": p}
    return None

def parse_date_posted(date_val):
    if not date_val:
        return datetime.now().strftime("%Y-%m-%d")
        
    date_str = str(date_val).strip().lower()
    
    if date_str.isdigit():
        try:
            val = int(date_str)
            if val > 10**11: # Milliseconds
                val = val / 1000
            return datetime.fromtimestamp(val).strftime("%Y-%m-%d")
        except Exception:
            pass
            
    match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        
    today = datetime.now()
    if any(k in date_str for k in ["just now", "today", "hour", "minute", "second"]):
        return today.strftime("%Y-%m-%d")
    elif "yesterday" in date_str or "1 day ago" in date_str:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
    match_days = re.search(r'(\d+)\s+day', date_str)
    if match_days:
        days = int(match_days.group(1))
        return (today - timedelta(days=days)).strftime("%Y-%m-%d")
        
    match_weeks = re.search(r'(\d+)\s+week', date_str)
    if match_weeks:
        weeks = int(match_weeks.group(1))
        return (today - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
        
    match_months = re.search(r'(\d+)\s+month', date_str)
    if match_months:
        months = int(match_months.group(1))
        return (today - timedelta(days=months*30)).strftime("%Y-%m-%d")
        
    return today.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# PORTAL SCRAPERS
# ---------------------------------------------------------------------------

def scrape_shine(role, city):
    print("  - Scraping Shine...")
    # Shine uses Next.js — jobs are in __NEXT_DATA__.initialState.jsrp.searchresult.data.results
    role_slug = role.replace(" ", "-").lower()
    city_slug = city.lower().split(",")[0].strip().replace(" ", "-")
    url = f"https://www.shine.com/job-search/{role_slug}-jobs-in-{city_slug}"
    proxy = get_oxylabs_proxy()
    try:
        r = requests.get(url, headers=HEADERS, proxies=proxy, timeout=25, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            next_data = soup.find("script", id="__NEXT_DATA__")
            if next_data:
                try:
                    js_data = json.loads(next_data.string)
                    page_props = js_data.get("props", {}).get("pageProps", {})
                    # Actual path: initialState -> jsrp -> searchresult -> data -> results
                    results = (
                        page_props
                        .get("initialState", {})
                        .get("jsrp", {})
                        .get("searchresult", {})
                        .get("data", {})
                        .get("results", [])
                    )
                    for item in results:
                        # Shine uses abbreviated field names:
                        # jJT=title, jCName=company, jLoc=location, jPDate=posted, jSlug=url slug
                        title = (item.get("jJT") or item.get("title") or "").strip()
                        company = (item.get("jCName") or item.get("companyName") or "").strip()
                        loc = item.get("jLoc") or item.get("location") or city
                        if isinstance(loc, list):
                            loc = ", ".join(loc)
                        date_posted = item.get("jPDate") or item.get("postedDate")
                        date_str = parse_date_posted(date_posted)
                        slug = item.get("jSlug") or item.get("slug") or ""
                        job_id = item.get("id") or ""
                        if slug:
                            job_url = f"https://www.shine.com/jobs/{slug}"
                        elif job_id:
                            job_url = f"https://www.shine.com/jobs/{job_id}"
                        else:
                            job_url = item.get("jRUrl") or item.get("url") or ""
                        if job_url and job_url.startswith("/"):
                            job_url = "https://www.shine.com" + job_url
                        if title and job_url:
                            jobs.append({
                                "title": title, "company": company,
                                "location": loc, "date_posted": date_str,
                                "url": job_url, "source": "shine", "role_search": role
                            })
                except Exception:
                    pass
            return jobs
    except Exception as e:
        print(f"    Shine error: {e}")
    return []

def scrape_timesjobs(role, city):
    print("  - Scraping TimesJobs...")
    # TimesJobs is now a Next.js SPA — server HTML is an empty shell.
    # Must use ScraperAPI with render=true to execute JavaScript.
    if not SCRAPERAPI_KEY:
        print("    TimesJobs (Skipped: No ScraperAPI Key for JS rendering)")
        return []
    role_enc = urllib.parse.quote(role)
    city_enc = urllib.parse.quote(city)
    url = f"https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords={role_enc}&txtLocation={city_enc}"
    encoded_url = urllib.parse.quote(url)
    endpoint = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={encoded_url}&render=true"
    jobs = []
    try:
        r = requests.get(endpoint, timeout=90, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            # After JS rendering, job cards should appear
            cards = soup.select("li.clearfix.job-bx, li.job-bx, .joblist-comp-info, [class*='job-bx']")
            for card in cards:
                title_el = card.select_one("h2.heading-trun a, header h2 a, .job-ttl a, h2 a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                job_url = title_el.get("href", "")
                if not job_url:
                    continue
                company = ""
                comp_el = card.select_one("h3.joblist-comp-name, .joblist-comp-name, .company-name")
                if comp_el:
                    company = comp_el.get_text(separator=" ", strip=True)
                    company = re.sub(r'\s*\d+(\.\d+)?\s*$', '', company).strip()
                loc = city
                loc_el = card.select_one(".srp-skills, ul.top-jd-dtl span, span[title], .location")
                if loc_el:
                    loc = loc_el.get_text(strip=True)
                date_str = datetime.now().strftime("%Y-%m-%d")
                date_el = card.select_one("span.sim-posted, .sim-posted span, [class*='posted']")
                if date_el:
                    date_str = parse_date_posted(date_el.get_text(strip=True))
                if title and job_url:
                    jobs.append({
                        "title": title, "company": company, "location": loc,
                        "date_posted": date_str, "url": job_url,
                        "source": "timesjobs", "role_search": role
                    })
    except Exception as e:
        print(f"    TimesJobs error: {e}")
    return jobs

def scrape_hirist(role, city):
    print("  - Scraping Hirist...")
    # Hirist uses slug URLs /{role}-jobs-in-{city} (search.html?keyword= returns 404).
    # Jobs load client-side (initialState.job.jobfeed=[] isLoading=True),
    # so we need ScraperAPI with render=true to let JS execute.
    if not SCRAPERAPI_KEY:
        print("    Hirist (Skipped: No ScraperAPI Key for JS rendering)")
        return []
    role_slug = role.replace(" ", "-").lower()
    city_slug = city.lower().split(",")[0].strip().replace(" ", "-")
    url = f"https://www.hirist.tech/{role_slug}-jobs-in-{city_slug}"
    encoded_url = urllib.parse.quote(url)
    endpoint = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={encoded_url}&render=true"
    try:
        r = requests.get(endpoint, timeout=90, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            # After JS render, try finding job cards/links
            # Hirist job links match pattern /j/{slug}.html or /j/{id}.html
            job_links = soup.find_all("a", href=re.compile(r"/j/[a-z0-9\-]+\.html|/j/\d+\.html"))
            seen_urls = set()
            for a in job_links:
                title = a.get_text(strip=True)
                if not title or len(title) < 3:
                    continue
                job_url = a.get("href", "")
                if job_url.startswith("/"):
                    job_url = "https://www.hirist.tech" + job_url
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)
                company = ""
                loc = city
                date_str = datetime.now().strftime("%Y-%m-%d")
                parent = a.find_parent("div", class_=re.compile(r"job|card|box|tuple|feed")) or a.parent
                if parent:
                    comp_el = parent.find(class_=re.compile(r"comp|recruiter|company|employer"))
                    if comp_el:
                        company = comp_el.get_text(strip=True)
                    loc_el = parent.find(class_=re.compile(r"loc|location|city"))
                    if loc_el:
                        loc = loc_el.get_text(strip=True)
                    date_el = parent.find(class_=re.compile(r"date|posted|time|ago"))
                    if date_el:
                        date_str = parse_date_posted(date_el.get_text(strip=True))
                jobs.append({
                    "title": title, "company": company, "location": loc,
                    "date_posted": date_str, "url": job_url,
                    "source": "hirist", "role_search": role
                })
            return jobs
    except Exception as e:
        print(f"    Hirist error: {e}")
    return []

def scrape_workindia(role, city):
    print("  - Scraping Workindia...")
    # WorkIndia serves JSON-LD with flat ListItem objects (just name+url, no nested JobPosting).
    # No JS rendering needed — the JSON-LD is in the SSR HTML, we just need to parse it correctly.
    city_clean = city.lower().split(",")[0].strip()
    role_enc = urllib.parse.quote(role)
    url = f"https://www.workindia.in/jobs-in-{city_clean}/?search={role_enc}"
    proxy = get_oxylabs_proxy()
    try:
        r = requests.get(url, headers=HEADERS, proxies=proxy, timeout=25, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            # Parse JSON-LD: WorkIndia uses flat ListItem objects with name+url (NOT nested JobPosting)
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    js_data = json.loads(script.string)
                    if isinstance(js_data, dict):
                        if js_data.get("@type") == "ItemList":
                            for item in js_data.get("itemListElement", []):
                                # Flat ListItem: {"@type":"ListItem","name":"...","url":"..."}
                                title = (item.get("name") or "").strip()
                                job_url = item.get("url") or ""
                                # Also check nested 'item' in case they add it later
                                if not title and isinstance(item.get("item"), dict):
                                    nested = item["item"]
                                    title = (nested.get("title") or nested.get("name") or "").strip()
                                    job_url = nested.get("url") or job_url
                                if title and job_url:
                                    jobs.append({
                                        "title": title, "company": "", "location": city,
                                        "date_posted": datetime.now().strftime("%Y-%m-%d"),
                                        "url": job_url, "source": "workindia", "role_search": role
                                    })
                        elif js_data.get("@type") == "JobPosting":
                            title = js_data.get("title", "").strip()
                            company = js_data.get("hiringOrganization", {}).get("name", "").strip()
                            loc = js_data.get("jobLocation", {}).get("address", {}).get("addressLocality", city)
                            date_str = parse_date_posted(js_data.get("datePosted"))
                            job_url = js_data.get("url")
                            if title and job_url:
                                jobs.append({"title": title, "company": company, "location": loc,
                                             "date_posted": date_str, "url": job_url,
                                             "source": "workindia", "role_search": role})
                except Exception:
                    pass
            # HTML link fallback
            if not jobs:
                for a in soup.find_all("a", href=re.compile(r"/jobs/[a-z0-9_\-]+")):
                    title = a.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue
                    job_url = a.get("href", "")
                    if job_url.startswith("/"):
                        job_url = "https://www.workindia.in" + job_url
                    jobs.append({
                        "title": title, "company": "", "location": city,
                        "date_posted": datetime.now().strftime("%Y-%m-%d"),
                        "url": job_url, "source": "workindia", "role_search": role
                    })
            return jobs
    except Exception as e:
        print(f"    Workindia error: {e}")
    return []

def scrape_foundit(role, city):
    if not SCRAPERAPI_KEY:
        print("  - Foundit (Skipped: No ScraperAPI Key)")
        return []
    print("  - Scraping Foundit (via ScraperAPI Premium)...")
    role_enc = role.replace(" ", "-").lower()
    city_enc = city.lower().split(",")[0].strip()
    url = f"https://www.foundit.in/search/{role_enc}-jobs-in-{city_enc}"
    encoded_url = urllib.parse.quote(url)
    # FIXED: Foundit has Cloudflare protection — use premium=true
    # Foundit uses Akamai WAF — need both render=true AND premium=true to bypass
    endpoint = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={encoded_url}&render=true&premium=true"
    try:
        r = requests.get(endpoint, timeout=90, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            next_data = soup.find("script", id="__NEXT_DATA__")
            if next_data:
                try:
                    js_data = json.loads(next_data.string)
                    page_props = js_data.get("props", {}).get("pageProps", {})
                    # FIXED: correct Foundit key paths
                    jobs_list = (
                        page_props.get("results", {}).get("data", [])
                        or page_props.get("jobPostings", [])
                        or page_props.get("jobs", [])
                        or page_props.get("initialState", {}).get("jobs", [])
                        or []
                    )
                    for item in jobs_list:
                        title = (item.get("jobTitle") or item.get("title") or "").strip()
                        company = (item.get("companyName") or item.get("company", {}).get("name", "") or "").strip()
                        loc = item.get("location") or item.get("locations") or item.get("jobLocation") or city
                        if isinstance(loc, list):
                            loc = ", ".join(loc)
                        date_posted = item.get("postedAt") or item.get("created") or item.get("publishedAt") or item.get("datePosted")
                        date_str = parse_date_posted(date_posted)
                        job_url = item.get("jobUrl") or item.get("applyUrl") or item.get("url")
                        if not job_url and item.get("jobId"):
                            job_url = f"https://www.foundit.in/job-description/{item.get('jobId')}"
                        if title and job_url:
                            jobs.append({"title": title, "company": company, "location": loc,
                                         "date_posted": date_str, "url": job_url,
                                         "source": "foundit", "role_search": role})
                except Exception:
                    pass
            if not jobs:
                job_links = soup.find_all("a", href=re.compile(r"/job-description/|/jobs/"))
                for a in job_links:
                    title = a.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue
                    job_url = a["href"]
                    if job_url.startswith("/"):
                        job_url = "https://www.foundit.in" + job_url
                    company = ""
                    loc = city
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    parent = a.find_parent("div", class_=re.compile(r"card|job|tuple")) or a.parent.parent
                    if parent:
                        comp_el = parent.select_one(".company-name, .company, [class*='company']")
                        if comp_el:
                            company = comp_el.get_text(strip=True)
                        loc_el = parent.select_one(".location, .loc, [class*='location']")
                        if loc_el:
                            loc = loc_el.get_text(strip=True)
                        date_el = parent.select_one(".date, .posted, [class*='date']")
                        if date_el:
                            date_str = parse_date_posted(date_el.get_text(strip=True))
                    jobs.append({"title": title, "company": company, "location": loc,
                                 "date_posted": date_str, "url": job_url,
                                 "source": "foundit", "role_search": role})
            return jobs
    except Exception as e:
        print(f"    Foundit error: {e}")
    return []

def scrape_apna(role, city):
    if not SCRAPERAPI_KEY:
        print("  - Apna (Skipped: No ScraperAPI Key)")
        return []
    print("  - Scraping Apna (via ScraperAPI)...")
    role_enc = role.replace(" ", "-").lower()
    city_enc = city.lower().split(",")[0].strip()
    url = f"https://apna.co/jobs/{role_enc}-jobs-in-{city_enc}"
    encoded_url = urllib.parse.quote(url)
    endpoint = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={encoded_url}"
    try:
        r = requests.get(endpoint, timeout=60, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            
            next_data = soup.find("script", id="__NEXT_DATA__")
            if next_data:
                try:
                    js_data = json.loads(next_data.string)
                    results = js_data.get("props", {}).get("pageProps", {}).get("jobs", []) or js_data.get("props", {}).get("pageProps", {}).get("initialState", {}).get("jobs", [])
                    for item in results:
                        title = (item.get("title") or item.get("jobTitle", "")).strip()
                        company = (item.get("companyName") or item.get("company", {}).get("name", "")).strip()
                        loc = item.get("location") or item.get("locationName") or city
                        date_posted = item.get("postedDate") or item.get("created")
                        date_str = parse_date_posted(date_posted)
                        job_url = item.get("jobUrl") or item.get("url")
                        if not job_url and item.get("id"):
                            job_url = f"https://apna.co/job/{item.get('id')}"
                        if title and job_url:
                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": loc,
                                "date_posted": date_str,
                                "url": job_url,
                                "source": "apna",
                                "role_search": role
                            })
                except Exception:
                    pass
                    
            if not jobs:
                cards = soup.select("[class*='JobCard'], [class*='job-card'], a[href*='/job/']")
                for card in cards:
                    if card.name == "a" and "/job/" in card["href"]:
                        title = card.get_text(strip=True)
                        job_url = card["href"]
                        if job_url.startswith("/"):
                            job_url = "https://apna.co" + job_url
                        company = ""
                        loc = city
                        date_str = datetime.now().strftime("%Y-%m-%d")
                        parent = card.parent.parent
                        if parent:
                            comp_el = parent.select_one("[class*='CompanyName'], [class*='company']")
                            if comp_el:
                                company = comp_el.get_text(strip=True)
                            loc_el = parent.select_one("[class*='Location'], [class*='location']")
                            if loc_el:
                                loc = loc_el.get_text(strip=True)
                            date_el = parent.select_one("[class*='Posted'], [class*='time']")
                            if date_el:
                                date_str = parse_date_posted(date_el.get_text(strip=True))
                        jobs.append({
                            "title": title,
                            "company": company,
                            "location": loc,
                            "date_posted": date_str,
                            "url": job_url,
                            "source": "apna",
                            "role_search": role
                        })
            return jobs
    except Exception as e:
        print(f"    Apna error: {e}")
    return []

def scrape_freshersworld(role, city):
    if not SCRAPERAPI_KEY:
        print("  - Freshersworld (Skipped: No ScraperAPI Key)")
        return []
    print("  - Scraping Freshersworld (via ScraperAPI Premium)...")
    # FIXED: correct search URL pattern + use premium to bypass bot detection
    role_enc = urllib.parse.quote(role)
    city_enc = urllib.parse.quote(city.split(",")[0].strip())
    url = f"https://www.freshersworld.com/jobs/jobsearch?jobsearch={role_enc}&location={city_enc}&vtype=job"
    encoded_url = urllib.parse.quote(url)
    endpoint = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={encoded_url}&premium=true"
    try:
        r = requests.get(endpoint, timeout=90, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            # Freshersworld card selectors (current 2024-2025 HTML)
            cards = soup.select(".job-container, .job-box, .latest-jobs-innr, [class*='job-block'], tr.job-list")
            for card in cards:
                title_el = card.select_one(".job-ttl a, .heading a, h2 a, h3 a, a[href*='/jobs/']")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                job_url = title_el.get("href", "")
                if not job_url:
                    continue
                if job_url.startswith("/"):
                    job_url = "https://www.freshersworld.com" + job_url
                company = ""
                comp_el = card.select_one(".company-name, .comp-name, [class*='company'], [class*='employer']")
                if comp_el:
                    company = comp_el.get_text(strip=True)
                loc = city
                loc_el = card.select_one(".job-location, .loc, [class*='location'], [class*='city']")
                if loc_el:
                    loc = loc_el.get_text(strip=True)
                date_str = datetime.now().strftime("%Y-%m-%d")
                date_el = card.select_one(".date, .posted-time, [class*='date'], [class*='posted']")
                if date_el:
                    date_str = parse_date_posted(date_el.get_text(strip=True))
                if title and job_url:
                    jobs.append({"title": title, "company": company, "location": loc,
                                 "date_posted": date_str, "url": job_url,
                                 "source": "freshersworld", "role_search": role})
            return jobs
    except Exception as e:
        print(f"    Freshersworld error: {e}")
    return []

def scrape_glassdoor(role, city):
    if not SCRAPERAPI_KEY:
        print("  - Glassdoor (Skipped: No ScraperAPI Key)")
        return []
    print("  - Scraping Glassdoor (via ScraperAPI Premium)...")
    role_enc = urllib.parse.quote(role)
    url = f"https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={role_enc}&locT=C&locName={city}"
    encoded_url = urllib.parse.quote(url)
    endpoint = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={encoded_url}&premium=true"
    try:
        r = requests.get(endpoint, timeout=60, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            
            cards = soup.select('li[data-test="jobListItem"], div[class*="jobCard"], a[href*="/partner/job/"]')
            for card in cards:
                title_el = card.select_one('a[id*="job-title"], [class*="job-title"], [class*="JobCard_jobTitle"]')
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                job_url = title_el.get("href", "")
                if job_url.startswith("/"):
                    job_url = "https://www.glassdoor.co.in" + job_url
                company = ""
                comp_el = card.select_one('[class*="EmployerName"], [class*="companyName"], [class*="employerName"]')
                if comp_el:
                    company = comp_el.get_text(strip=True)
                    company = re.sub(r'\d+(\.\d+)?\s*★', '', company).strip()
                loc = city
                loc_el = card.select_one('[class*="location"], [class*="Location"]')
                if loc_el:
                    loc = loc_el.get_text(strip=True)
                date_str = datetime.now().strftime("%Y-%m-%d")
                date_el = card.select_one('[data-test="job-age"], [class*="listing-age"], [class*="jobAge"]')
                if date_el:
                    date_str = parse_date_posted(date_el.get_text(strip=True))
                if title and job_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "date_posted": date_str,
                        "url": job_url,
                        "source": "glassdoor",
                        "role_search": role
                    })
            return jobs
    except Exception as e:
        print(f"    Glassdoor error: {e}")
    return []

def scrape_internshala(role, city):
    if not SCRAPERAPI_KEY:
        print("  - Internshala (Skipped: No ScraperAPI Key)")
        return []
    print("  - Scraping Internshala (via ScraperAPI Premium)...")
    role_enc = role.replace(" ", "-").lower()
    city_enc = city.lower().split(",")[0].strip()
    url = f"https://internshala.com/jobs/{role_enc}-jobs-in-{city_enc}/"
    encoded_url = urllib.parse.quote(url)
    endpoint = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={encoded_url}&premium=true"
    try:
        r = requests.get(endpoint, timeout=60, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            
            cards = soup.select(".individual_internship")
            for card in cards:
                title_el = card.select_one(".heading_designation, .job_heading, a[href*='/job/detail/']")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                job_url = title_el["href"] if title_el.name == "a" else (title_el.find("a")["href"] if title_el.find("a") else "")
                if job_url.startswith("/"):
                    job_url = "https://internshala.com" + job_url
                company = ""
                comp_el = card.select_one(".company_name")
                if comp_el:
                    company = comp_el.get_text(strip=True)
                loc = city
                loc_el = card.select_one(".location_link")
                if loc_el:
                    loc = loc_el.get_text(strip=True)
                date_str = datetime.now().strftime("%Y-%m-%d")
                date_el = card.select_one(".status-container, .posted-by")
                if date_el:
                    date_str = parse_date_posted(date_el.get_text(strip=True))
                if title and job_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "date_posted": date_str,
                        "url": job_url,
                        "source": "internshala",
                        "role_search": role
                    })
            return jobs
    except Exception as e:
        print(f"    Internshala error: {e}")
    return []

def scrape_naukri(role, city):
    global browser_instance
    if not browser_instance:
        return []
    print("  - Scraping Naukri (via Playwright)...")
    role_clean = role.replace(" ", "-").lower()
    city_clean = city.lower().split(",")[0].strip()
    url = f"https://www.naukri.com/{role_clean}-jobs-in-{city_clean}"

    jobs = []
    try:
        proxy_config = None
        if OXYLABS_USER and OXYLABS_PASS:
            proxy_config = {
                "server": f"http://{OXYLABS_HOST}:8001",
                "username": OXYLABS_USER,
                "password": OXYLABS_PASS
            }
            print(f"    Routing Naukri traffic through Oxylabs proxy: {OXYLABS_HOST}:8001")
        
        context = browser_instance.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            proxy=proxy_config
        )
        page = context.new_page()
        # Stealth: hide automation markers
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-IN','en','hi']});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
        """)
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(5000)

        # Scroll down to trigger lazy-loaded job cards
        page.evaluate("window.scrollBy(0, 800)")
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollBy(0, 800)")
        page.wait_for_timeout(2000)

        # Wait for job cards to appear
        card_selector = ".srp-jobtuple-wrapper, .cust-job-tuple, article.jobTuple, [class*='jobTuple'], .job-tuple-container"
        try:
            page.wait_for_selector(card_selector, timeout=15000)
        except Exception:
            pass

        content = page.content()
        soup = BeautifulSoup(content, "html.parser")

        job_cards = soup.select(card_selector)

        for card in job_cards:
            # Title
            title_el = (
                card.select_one("a.title")
                or card.select_one(".row1 a[title]")
                or card.select_one(".jobTupleHeader a")
                or card.select_one("a[class*='title']")
                or card.select_one("a[href*='naukri.com/job-listings']")
            )
            # Company
            company_el = (
                card.select_one("a.comp-name")
                or card.select_one(".comp-name")
                or card.select_one(".subTitle a")
                or card.select_one("a[class*='comp']")
                or card.select_one("[class*='companyInfo'] a")
            )
            # Location
            location_el = (
                card.select_one("span.locWdth")
                or card.select_one(".location-container span")
                or card.select_one(".loc span")
                or card.select_one("[class*='location'] span")
                or card.select_one("[class*='loc']")
            )
            # Date posted
            post_el = (
                card.select_one("span.job-post-day")
                or card.select_one(".job-post-day")
                or card.select_one("[class*='posted']")
                or card.select_one(".fleft.postedDate")
            )

            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            loc = location_el.get_text(strip=True) if location_el else city
            job_url = title_el.get("href", "") if title_el else ""

            date_str = datetime.now().strftime("%Y-%m-%d")
            if post_el:
                date_str = parse_date_posted(post_el.get_text(strip=True))

            if title and job_url:
                jobs.append({
                    "title": title, "company": company, "location": loc,
                    "date_posted": date_str, "url": job_url,
                    "source": "naukri", "role_search": role
                })
        context.close()
    except Exception as e:
        print(f"    Naukri Playwright error: {e}")
    return jobs

# ---------------------------------------------------------------------------
# MAIN SCHEDULER OR LOOP
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  10 JOB PORTALS SCRAPER")
    print("=" * 70)
    print(f"  📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🔍 Roles Count: {len(SEARCH_ROLES)}")
    print(f"  📍 Cities Count: {len(LOCATIONS)}")
    print(f"  ScraperAPI Key: {'Configured' if SCRAPERAPI_KEY else 'NOT Configured'}")
    print(f"  Oxylabs Proxies: {len(oxylabs_proxies)} ports configured")
    print("=" * 70)

    # Run DB cleanup
    cleanup_old_jobs()

    # Initialize Playwright once
    init_playwright()

    # Load progress
    progress = load_progress()
    start_role = progress.get("role_idx", 0)
    start_loc = progress.get("loc_idx", 0)

    total_inserted = 0
    total_combos = len(SEARCH_ROLES) * len(LOCATIONS)
    combo_num = start_role * len(LOCATIONS) + start_loc
    hit_time_limit = False

    # Stats tracking per portal
    scraped_counts = {
        "shine": 0, "timesjobs": 0, "hirist": 0, "workindia": 0,
        "foundit": 0, "apna": 0, "freshersworld": 0, "glassdoor": 0,
        "internshala": 0, "naukri": 0
    }
    stored_counts = {
        "shine": 0, "timesjobs": 0, "hirist": 0, "workindia": 0,
        "foundit": 0, "apna": 0, "freshersworld": 0, "glassdoor": 0,
        "internshala": 0, "naukri": 0
    }

    if start_role > 0 or start_loc > 0:
        print(f"\n🔄 Resuming scraping from Role Index: {start_role}/{len(SEARCH_ROLES)}, Location Index: {start_loc}/{len(LOCATIONS)}")
        print(f"   Resuming at: '{SEARCH_ROLES[start_role]}' in '{LOCATIONS[start_loc]}'")

    for r_idx in range(start_role, len(SEARCH_ROLES)):
        role = SEARCH_ROLES[r_idx]
        curr_start_loc_idx = start_loc if r_idx == start_role else 0
        
        for l_idx in range(curr_start_loc_idx, len(LOCATIONS)):
            city = LOCATIONS[l_idx]
            combo_num += 1

            # Check time limit before running combo
            elapsed = time.time() - START_TIME
            if elapsed >= MAX_RUN_SECONDS:
                print(f"\n⏰ Time limit reached ({elapsed:.0f}s). Saving progress at role={r_idx}, loc={l_idx}...")
                save_progress(r_idx, l_idx, finished_all=False)
                hit_time_limit = True
                break

            # Save progress before starting so if we crash or get killed, we start exactly here next run
            save_progress(r_idx, l_idx, finished_all=False)

            print(f"\n[{combo_num}/{total_combos}] Searching for '{role}' in '{city}'...")

            combo_raw   = 0  # total raw jobs scraped this combo
            combo_stored = 0  # total new jobs stored this combo

            if not SCRAPE_ONLY_NAUKRI:
                # ── Group 1: Shine (HTML + Oxylabs) ─────────────────────────────
                shine_jobs = scrape_shine(role, city)
                n = len(shine_jobs); ins = store_jobs_batch(shine_jobs)
                scraped_counts["shine"] += n; stored_counts["shine"] += ins
                total_inserted += ins; combo_raw += n; combo_stored += ins
                print(f"      Shine         : {n:>4} scraped  |  {ins:>4} new stored")

                # ── Group 2: TimesJobs (HTML + Oxylabs) ──────────────────────────
                tj_jobs = scrape_timesjobs(role, city)
                n = len(tj_jobs); ins = store_jobs_batch(tj_jobs)
                scraped_counts["timesjobs"] += n; stored_counts["timesjobs"] += ins
                total_inserted += ins; combo_raw += n; combo_stored += ins
                print(f"      TimesJobs     : {n:>4} scraped  |  {ins:>4} new stored")

                # ── Group 3: Hirist (HTML + Oxylabs) ─────────────────────────────
                hirist_jobs = scrape_hirist(role, city)
                n = len(hirist_jobs); ins = store_jobs_batch(hirist_jobs)
                scraped_counts["hirist"] += n; stored_counts["hirist"] += ins
                total_inserted += ins; combo_raw += n; combo_stored += ins
                print(f"      Hirist        : {n:>4} scraped  |  {ins:>4} new stored")

                # ── Group 4: WorkIndia (ScraperAPI render=true) ───────────────────
                workindia_jobs = scrape_workindia(role, city)
                n = len(workindia_jobs); ins = store_jobs_batch(workindia_jobs)
                scraped_counts["workindia"] += n; stored_counts["workindia"] += ins
                total_inserted += ins; combo_raw += n; combo_stored += ins
                print(f"      WorkIndia     : {n:>4} scraped  |  {ins:>4} new stored")

                # ── Group 5: Foundit (ScraperAPI Premium) ────────────────────────
                foundit_jobs = scrape_foundit(role, city)
                n = len(foundit_jobs); ins = store_jobs_batch(foundit_jobs)
                scraped_counts["foundit"] += n; stored_counts["foundit"] += ins
                total_inserted += ins; combo_raw += n; combo_stored += ins
                print(f"      Foundit       : {n:>4} scraped  |  {ins:>4} new stored")

                # ── Group 6: Apna (ScraperAPI Standard) ──────────────────────────
                apna_jobs = scrape_apna(role, city)
                n = len(apna_jobs); ins = store_jobs_batch(apna_jobs)
                scraped_counts["apna"] += n; stored_counts["apna"] += ins
                total_inserted += ins; combo_raw += n; combo_stored += ins
                print(f"      Apna          : {n:>4} scraped  |  {ins:>4} new stored")

                # ── Group 7: Freshersworld (ScraperAPI Premium) ───────────────────
                fw_jobs = scrape_freshersworld(role, city)
                n = len(fw_jobs); ins = store_jobs_batch(fw_jobs)
                scraped_counts["freshersworld"] += n; stored_counts["freshersworld"] += ins
                total_inserted += ins; combo_raw += n; combo_stored += ins
                print(f"      FreshersWorld : {n:>4} scraped  |  {ins:>4} new stored")

                # ── Group 8: Glassdoor (ScraperAPI Premium) ───────────────────────
                gd_jobs = scrape_glassdoor(role, city)
                n = len(gd_jobs); ins = store_jobs_batch(gd_jobs)
                scraped_counts["glassdoor"] += n; stored_counts["glassdoor"] += ins
                total_inserted += ins; combo_raw += n; combo_stored += ins
                print(f"      Glassdoor     : {n:>4} scraped  |  {ins:>4} new stored")

                # ── Group 9: Internshala (ScraperAPI Premium) ────────────────────
                ishala_jobs = scrape_internshala(role, city)
                n = len(ishala_jobs); ins = store_jobs_batch(ishala_jobs)
                scraped_counts["internshala"] += n; stored_counts["internshala"] += ins
                total_inserted += ins; combo_raw += n; combo_stored += ins
                print(f"      Internshala   : {n:>4} scraped  |  {ins:>4} new stored")

            # ── Group 10: Naukri (Playwright Stealth) ────────────────────────
            naukri_jobs = scrape_naukri(role, city)
            n = len(naukri_jobs); ins = store_jobs_batch(naukri_jobs)
            scraped_counts["naukri"] += n; stored_counts["naukri"] += ins
            total_inserted += ins; combo_raw += n; combo_stored += ins
            print(f"      Naukri        : {n:>4} scraped  |  {ins:>4} new stored")

            # ── Combo summary ─────────────────────────────────────────────────
            print(f"   -> Found {combo_raw} raw jobs for combo: '{role}' in '{city}'")
            print(f"   -> Successfully stored {combo_stored} new unique jobs in D1 database.")

            # Cool-down to prevent rate-limiting between search combinations
            time.sleep(3)

        if hit_time_limit:
            break

    # Close Playwright browser resources
    close_playwright()

    if not hit_time_limit:
        save_progress(0, 0, finished_all=True)
        print("\n✅ Scraper completed all roles. Progress reset.")
    else:
        print(f"\n💾 Progress saved at role_idx={r_idx}, loc_idx={l_idx}")

    # Display final statistics per job portal
    total_raw_scraped = sum(scraped_counts.values())
    print("\n" + "=" * 70)
    print("                    JOB PORTAL STATISTICS SUMMARY")
    print("=" * 70)
    print(f"{'Job Portal':<22} | {'Scraped (Raw)':<16} | {'Stored (New D1)':<16}")
    print("-" * 70)
    for portal in sorted(scraped_counts.keys()):
        print(f"{portal.upper():<22} | {scraped_counts[portal]:<16} | {stored_counts[portal]:<16}")
    print("=" * 70)
    print(f"{'TOTAL SUM':<22} | {total_raw_scraped:<16} | {total_inserted:<16}")
    print("=" * 70)

    print("\n" + "=" * 70)
    print(f"  🏁 SCRAPING COMPLETED")
    print(f"  📅 End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🆕 Total New Unique Jobs Stored in D1: {total_inserted}")
    print("=" * 70)

if __name__ == "__main__":
    main()
