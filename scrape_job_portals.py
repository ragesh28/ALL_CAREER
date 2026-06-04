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
OXYLABS_HOST = os.environ.get("OXYLABS_ENTRYPOINT", "dc.oxylabs.io")
OXYLABS_PORTS_STR = os.environ.get("OXYLABS_PORTS", "8001,8002,8003,8004,8005")

oxylabs_proxies = []
if OXYLABS_USER and OXYLABS_PASS:
    ports = [p.strip() for p in OXYLABS_PORTS_STR.split(",") if p.strip()]
    for port in ports:
        oxylabs_proxies.append(f"http://{OXYLABS_USER}:{OXYLABS_PASS}@{OXYLABS_HOST}:{port}")

# Global Playwright Browser Instances
playwright_instance = None
browser_instance = None

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
    "Frontend Developer", "Backend Developer", "Full Stack Developer",
    "Mobile App Developer", "Software Architect", "Software Engineer",
    "AI Engineer", "Machine Learning Engineer", "Data Scientist",
    "Data Engineer", "Data Analyst",
    "DevOps Engineer", "Cloud Architect", "Systems Administrator",
    "Database Administrator",
    "Security Analyst", "Penetration Tester", "Network Engineer",
    "QA Analyst", "SDET",
    "Product Manager", "Project Manager", "Scrum Master",
    "UI UX Designer", "UX Researcher", "Technical Writer",
    "Sales Executive", "Pre-Sales Consultant", "Digital Marketer",
    "Product Marketing Manager",
    "Technical Recruiter", "HR Business Partner",
    "Customer Success Manager", "IT Support Specialist",
    "Operations Manager", "Financial Analyst", "Legal Counsel",
]

LOCATIONS = [
    "Bangalore",
    "Chennai",
    "Hyderabad",
    "Mumbai",
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
    q_term = role.replace(" ", "-").lower() + "-jobs"
    url = f"https://www.shine.com/api/v2/search/simple/?q={q_term}&loc={city.lower()}&page=1"
    proxy = get_oxylabs_proxy()
    try:
        r = requests.get(url, headers=HEADERS, proxies=proxy, timeout=20, verify=False)
        if r.status_code == 200:
            data = r.json()
            jobs = []
            for item in data.get("results", []):
                title = item.get("title", "").strip()
                company = item.get("company_name", "").strip()
                loc = item.get("location", "").strip()
                date_posted = item.get("created_date") or item.get("published_date")
                date_str = parse_date_posted(date_posted)
                job_url = "https://www.shine.com" + item.get("share_url", "") if item.get("share_url") else ""
                if title and job_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc or city,
                        "date_posted": date_str,
                        "url": job_url,
                        "source": "shine",
                        "role_search": role
                    })
            return jobs
    except Exception as e:
        print(f"    Shine error: {e}")
    return []

def scrape_timesjobs(role, city):
    print("  - Scraping TimesJobs...")
    url = "https://tjapi.timesjobs.com/search/api/v1/search/jobs/list"
    payload = {
        "keywords": [role],
        "locations": [city],
        "page": 1
    }
    proxy = get_oxylabs_proxy()
    headers_api = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    jobs = []
    try:
        r = requests.post(url, headers=headers_api, json=payload, proxies=proxy, timeout=20, verify=False)
        if r.status_code == 200:
            data = r.json()
            jobs_list = data.get("jobs", []) or data.get("results", []) or data.get("data", {}).get("jobs", [])
            for item in jobs_list:
                title = (item.get("title") or item.get("jobTitle", "")).strip()
                company = (item.get("company") or item.get("companyName", "")).strip()
                loc = item.get("location") or item.get("locations") or city
                if isinstance(loc, list):
                    loc = ", ".join(loc)
                date_posted = item.get("postedDate") or item.get("createdDate")
                date_str = parse_date_posted(date_posted)
                job_url = item.get("jobUrl") or item.get("applyUrl") or item.get("url")
                if title and job_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "date_posted": date_str,
                        "url": job_url,
                        "source": "timesjobs",
                        "role_search": role
                    })
    except Exception as e:
        print(f"    TimesJobs API error: {e}")

    # Fallback to HTML scraping
    if not jobs:
        role_enc = urllib.parse.quote(role)
        city_enc = urllib.parse.quote(city)
        fallback_url = f"https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords={role_enc}&txtLocation={city_enc}"
        try:
            r = requests.get(fallback_url, headers=HEADERS, proxies=proxy, timeout=20, verify=False)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select("li.job-bx")
                for card in cards:
                    title_el = card.select_one("header h2 a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    job_url = title_el["href"]
                    company = ""
                    comp_el = card.select_one("h3.joblist-comp-name")
                    if comp_el:
                        # Sometimes contains rating link
                        company = comp_el.get_text(strip=True)
                        if comp_el.find("span"):
                            company = company.replace(comp_el.find("span").get_text(strip=True), "").strip()
                    loc = city
                    loc_el = card.select_one("span[title]")
                    if loc_el:
                        loc = loc_el.get_text(strip=True)
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    date_el = card.select_one("span.sim-posted span")
                    if date_el:
                        date_str = parse_date_posted(date_el.get_text(strip=True))
                    if title and job_url:
                        jobs.append({
                            "title": title,
                            "company": company,
                            "location": loc,
                            "date_posted": date_str,
                            "url": job_url,
                            "source": "timesjobs",
                            "role_search": role
                        })
        except Exception as e:
            print(f"    TimesJobs HTML fallback error: {e}")
    return jobs

def scrape_hirist(role, city):
    print("  - Scraping Hirist...")
    role_enc = urllib.parse.quote(role)
    city_enc = urllib.parse.quote(city)
    url = f"https://www.hirist.tech/search.html?keyword={role_enc}&location={city_enc}"
    proxy = get_oxylabs_proxy()
    try:
        r = requests.get(url, headers=HEADERS, proxies=proxy, timeout=20, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            
            next_data = soup.find("script", id="__NEXT_DATA__")
            if next_data:
                try:
                    js_data = json.loads(next_data.string)
                    page_props = js_data.get("props", {}).get("pageProps", {})
                    results = page_props.get("jobs", []) or page_props.get("searchResults", []) or page_props.get("initialState", {}).get("search", {}).get("jobs", [])
                    for item in results:
                        title = (item.get("title") or item.get("jobTitle", "")).strip()
                        company = (item.get("companyName") or item.get("recruiterName", "")).strip()
                        loc = item.get("location") or item.get("locationName") or city
                        date_posted = item.get("date") or item.get("postedDate") or item.get("created")
                        date_str = parse_date_posted(date_posted)
                        job_id = item.get("id") or item.get("jobId")
                        job_url = f"https://www.hirist.tech/j/{job_id}.html" if job_id else item.get("url")
                        if title and job_url:
                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": loc,
                                "date_posted": date_str,
                                "url": job_url,
                                "source": "hirist",
                                "role_search": role
                            })
                except Exception:
                    pass
            
            if not jobs:
                # Class scraper fallback
                for a in soup.find_all("a", href=re.compile(r"/j/\d+\.html")):
                    title = a.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue
                    job_url = a["href"]
                    if job_url.startswith("/"):
                        job_url = "https://www.hirist.tech" + job_url
                    company = ""
                    loc = city
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    
                    parent = a.find_parent("div", class_=re.compile(r"job|card|box")) or a.parent.parent
                    if parent:
                        comp_el = parent.find(class_=re.compile(r"comp|recruiter|company"))
                        if comp_el:
                            company = comp_el.get_text(strip=True)
                        loc_el = parent.find(class_=re.compile(r"loc|location"))
                        if loc_el:
                            loc = loc_el.get_text(strip=True)
                        date_el = parent.find(class_=re.compile(r"date|posted|time"))
                        if date_el:
                            date_str = parse_date_posted(date_el.get_text(strip=True))
                            
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "date_posted": date_str,
                        "url": job_url,
                        "source": "hirist",
                        "role_search": role
                    })
            return jobs
    except Exception as e:
        print(f"    Hirist error: {e}")
    return []

def scrape_workindia(role, city):
    print("  - Scraping Workindia...")
    city_clean = city.lower().split(",")[0].strip()
    role_enc = urllib.parse.quote(role)
    url = f"https://www.workindia.in/jobs-in-{city_clean}/?search={role_enc}"
    proxy = get_oxylabs_proxy()
    try:
        r = requests.get(url, headers=HEADERS, proxies=proxy, timeout=20, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            
            # JSON-LD scripts
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    js_data = json.loads(script.string)
                    if isinstance(js_data, dict):
                        if js_data.get("@type") == "ItemList":
                            for item in js_data.get("itemListElement", []):
                                job_data = item.get("item", {})
                                if job_data.get("@type") == "JobPosting":
                                    title = job_data.get("title", "").strip()
                                    company = job_data.get("hiringOrganization", {}).get("name", "").strip()
                                    loc = job_data.get("jobLocation", {}).get("address", {}).get("addressLocality", city)
                                    date_posted = job_data.get("datePosted")
                                    date_str = parse_date_posted(date_posted)
                                    job_url = job_data.get("url")
                                    if title and job_url:
                                        jobs.append({
                                            "title": title,
                                            "company": company,
                                            "location": loc,
                                            "date_posted": date_str,
                                            "url": job_url,
                                            "source": "workindia",
                                            "role_search": role
                                        })
                        elif js_data.get("@type") == "JobPosting":
                            title = js_data.get("title", "").strip()
                            company = js_data.get("hiringOrganization", {}).get("name", "").strip()
                            loc = js_data.get("jobLocation", {}).get("address", {}).get("addressLocality", city)
                            date_posted = js_data.get("datePosted")
                            date_str = parse_date_posted(date_posted)
                            job_url = js_data.get("url")
                            if title and job_url:
                                jobs.append({
                                    "title": title,
                                    "company": company,
                                    "location": loc,
                                    "date_posted": date_str,
                                    "url": job_url,
                                    "source": "workindia",
                                    "role_search": role
                                })
                except Exception:
                    pass
                    
            if not jobs:
                # Class cards fallback
                cards = soup.select(".job-card, .job_card, .job-item")
                for card in cards:
                    title_el = card.select_one(".job-title, .title, a[href*='/jobs/']")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    job_url = title_el["href"] if title_el.name == "a" else (title_el.find("a")["href"] if title_el.find("a") else "")
                    if not job_url:
                        continue
                    if job_url.startswith("/"):
                        job_url = "https://www.workindia.in" + job_url
                    company = ""
                    comp_el = card.select_one(".company-name, .company, .hiring-org")
                    if comp_el:
                        company = comp_el.get_text(strip=True)
                    loc = city
                    loc_el = card.select_one(".location, .locality")
                    if loc_el:
                        loc = loc_el.get_text(strip=True)
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    date_el = card.select_one(".date, .posted-time")
                    if date_el:
                        date_str = parse_date_posted(date_el.get_text(strip=True))
                    if title and job_url:
                        jobs.append({
                            "title": title,
                            "company": company,
                            "location": loc,
                            "date_posted": date_str,
                            "url": job_url,
                            "source": "workindia",
                            "role_search": role
                        })
            return jobs
    except Exception as e:
        print(f"    Workindia error: {e}")
    return []

def scrape_foundit(role, city):
    if not SCRAPERAPI_KEY:
        print("  - Foundit (Skipped: No ScraperAPI Key)")
        return []
    print("  - Scraping Foundit (via ScraperAPI)...")
    role_enc = role.replace(" ", "-").lower()
    city_enc = city.lower().split(",")[0].strip()
    url = f"https://www.foundit.in/search/{role_enc}-jobs-in-{city_enc}"
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
                    jobs_list = js_data.get("props", {}).get("pageProps", {}).get("jobs", []) or js_data.get("props", {}).get("pageProps", {}).get("initialState", {}).get("jobs", [])
                    for item in jobs_list:
                        title = (item.get("jobTitle") or item.get("title", "")).strip()
                        company = (item.get("companyName") or item.get("company", {}).get("name", "")).strip()
                        loc = item.get("location") or item.get("locations") or city
                        if isinstance(loc, list):
                            loc = ", ".join(loc)
                        date_posted = item.get("postedAt") or item.get("created") or item.get("publishedAt")
                        date_str = parse_date_posted(date_posted)
                        job_url = item.get("jobUrl") or item.get("applyUrl") or item.get("url")
                        if not job_url and item.get("jobId"):
                            job_url = f"https://www.foundit.in/job-description/{item.get('jobId')}"
                        if title and job_url:
                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": loc,
                                "date_posted": date_str,
                                "url": job_url,
                                "source": "foundit",
                                "role_search": role
                            })
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
                    
                    parent = a.find_parent("div", class_=re.compile(r"card|job")) or a.parent.parent
                    if parent:
                        comp_el = parent.select_one(".company-name, .company, [class*='company']")
                        if comp_el:
                            company = comp_el.get_text(strip=True)
                        loc_el = parent.select_one(".location, .loc, [class*='location']")
                        if loc_el:
                            loc = loc_el.get_text(strip=True)
                        date_el = parent.select_one(".date, .posted")
                        if date_el:
                            date_str = parse_date_posted(date_el.get_text(strip=True))
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "date_posted": date_str,
                        "url": job_url,
                        "source": "foundit",
                        "role_search": role
                    })
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
    print("  - Scraping Freshersworld (via ScraperAPI)...")
    role_clean = role.replace(" ", "-").lower()
    city_clean = city.lower().split(",")[0].strip()
    url = f"https://www.freshersworld.com/jobs/category/{role_clean}-job-vacancies-{city_clean}"
    encoded_url = urllib.parse.quote(url)
    endpoint = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={encoded_url}"
    try:
        r = requests.get(endpoint, timeout=60, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            jobs = []
            
            cards = soup.select(".job-container, .job-inner, [class*='job-card']")
            for card in cards:
                title_el = card.select_one(".job-title, .title, a[href*='/jobs/']")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                job_url = title_el["href"] if title_el.name == "a" else (title_el.find("a")["href"] if title_el.find("a") else "")
                if not job_url:
                    continue
                if job_url.startswith("/"):
                    job_url = "https://www.freshersworld.com" + job_url
                company = ""
                comp_el = card.select_one(".company-name, .company")
                if comp_el:
                    company = comp_el.get_text(strip=True)
                loc = city
                loc_el = card.select_one(".job-location, .location")
                if loc_el:
                    loc = loc_el.get_text(strip=True)
                date_str = datetime.now().strftime("%Y-%m-%d")
                date_el = card.select_one(".date, .posted-time")
                if date_el:
                    date_str = parse_date_posted(date_el.get_text(strip=True))
                if title and job_url:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc,
                        "date_posted": date_str,
                        "url": job_url,
                        "source": "freshersworld",
                        "role_search": role
                    })
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
        context = browser_instance.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        page.add_init_script("delete navigator.__proto__.webdriver;")
        
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        try:
            page.wait_for_selector(".srp-jobtuple-container, article.jobTuple, a.title", timeout=10000)
        except Exception:
            pass
            
        content = page.content()
        soup = BeautifulSoup(content, "html.parser")
        job_cards = soup.select(".srp-jobtuple-wrapper")
        
        for card in job_cards:
            title_el = card.select_one("a.title")
            company_el = card.select_one("a.comp-name")
            location_el = card.select_one("span.locWdth")
            post_el = card.select_one("span.job-post-day")
            
            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            loc = location_el.get_text(strip=True) if location_el else city
            job_url = title_el.get("href", "") if title_el else ""
            
            date_str = datetime.now().strftime("%Y-%m-%d")
            if post_el:
                date_str = parse_date_posted(post_el.get_text(strip=True))
                
            if title and job_url:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": loc,
                    "date_posted": date_str,
                    "url": job_url,
                    "source": "naukri",
                    "role_search": role
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

    total_inserted = 0
    
    for role in SEARCH_ROLES:
        for city in LOCATIONS:
            print(f"\n🔍 Searching for '{role}' in '{city}'...")
            
            scraped_jobs = []
            
            # Group 1: Shine (Direct API + Oxylabs)
            scraped_jobs.extend(scrape_shine(role, city))
            
            # Group 2: TimesJobs (Direct API / HTML + Oxylabs)
            scraped_jobs.extend(scrape_timesjobs(role, city))
            
            # Group 3: Hirist (HTML + Oxylabs)
            scraped_jobs.extend(scrape_hirist(role, city))
            
            # Group 4: Workindia (HTML + Oxylabs)
            scraped_jobs.extend(scrape_workindia(role, city))
            
            # Group 5: Foundit (ScraperAPI Standard)
            scraped_jobs.extend(scrape_foundit(role, city))
            
            # Group 6: Apna Jobs (ScraperAPI Standard)
            scraped_jobs.extend(scrape_apna(role, city))
            
            # Group 7: Freshersworld (ScraperAPI Standard)
            scraped_jobs.extend(scrape_freshersworld(role, city))
            
            # Group 8: Glassdoor (ScraperAPI Premium)
            scraped_jobs.extend(scrape_glassdoor(role, city))
            
            # Group 9: Internshala (ScraperAPI Premium)
            scraped_jobs.extend(scrape_internshala(role, city))
            
            # Group 10: Naukri (Playwright Stealth)
            scraped_jobs.extend(scrape_naukri(role, city))
            
            print(f"  -> Found {len(scraped_jobs)} raw jobs for combo: '{role}' in '{city}'")
            
            # Insert to D1 database
            inserted = store_jobs_batch(scraped_jobs)
            total_inserted += inserted
            print(f"  -> Successfully stored {inserted} new unique jobs in D1 database.")
            
            # Cool-down to prevent rate-limiting between search combinations
            time.sleep(3)

    # Close Playwright browser resources
    close_playwright()

    print("\n" + "=" * 70)
    print(f"  🏁 SCRAPING COMPLETED")
    print(f"  📅 End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🆕 New Unique Jobs Stored in D1: {total_inserted}")
    print("=" * 70)

if __name__ == "__main__":
    main()
