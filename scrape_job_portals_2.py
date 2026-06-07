import os
import sys
import re
import json
import time
import urllib.parse
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
try:
    from jobspy import scrape_jobs
except ImportError:
    scrape_jobs = None

# Configure stdout to handle UTF-8 printing cleanly on Windows
sys.stdout.reconfigure(encoding='utf-8')
requests.packages.urllib3.disable_warnings()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
ACCOUNT_ID = "62eacb67a7ee0b199f58ccb540a3eff7"
DATABASE_ID = "20b71b5c-c070-45b5-9542-27ed1cad89e5"

# Global Playwright Browser Instances
playwright_instance = None
browser_instance = None

# Progress Checkpointing Configuration
PROGRESS_FILE = "job_portals_2_progress.json"
START_TIME = time.time()
MAX_RUN_SECONDS = 5 * 3600 + 45 * 60  # 5 hours 45 minutes

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
        pass

# MASSIVE ROLES LIST (50+ Tech and Non-Tech)
SEARCH_ROLES = [
    # General Tech
    "Software Developer", "Software Engineer", "Frontend Developer", "Backend Developer", 
    "Full Stack Developer", "Java Developer", "Python Developer", "Node.js Developer", 
    "React Developer", "Angular Developer",
    # Mobile
    "Mobile App Developer", "iOS Developer", "Android Developer", "Flutter Developer", "React Native Developer",
    # Design
    "UI UX Designer", "Product Designer", "Graphic Designer",
    # Data & AI
    "Data Analyst", "Data Engineer", "Data Scientist", "AI Engineer", "Machine Learning Engineer", 
    "Deep Learning Engineer", "NLP Engineer", "Database Administrator",
    # Infrastructure & Security
    "DevOps Engineer", "Cloud Architect", "AWS Engineer", "Azure Engineer", "Systems Administrator", 
    "Network Engineer", "Security Analyst", "Penetration Tester", "Cybersecurity Engineer",
    # QA & Project Management
    "QA Analyst", "QA Automation Engineer", "SDET", "Scrum Master", "Product Manager", 
    "Project Manager", "Technical Writer",
    # Non-Tech (HR, Sales, Marketing, etc.)
    "HR Executive", "HR Business Partner", "Technical Recruiter", "Sales Executive", 
    "Business Development Manager", "Pre-Sales Consultant", "Marketing Manager", "Digital Marketer", 
    "SEO Specialist", "Content Writer", "Social Media Manager", "Operations Manager", 
    "Supply Chain Analyst", "Financial Analyst", "Accountant", "Legal Counsel", 
    "Customer Success Manager", "Customer Support Executive"
]

LOCATIONS = [
    "Bangalore", "Chennai", "Hyderabad", "Mumbai", "Pune", 
    "Noida", "Gurgaon", "Kolkata", "Delhi", "Ahmedabad", 
    "Kochi", "Chandigarh", "Indore", "Jaipur", "Coimbatore"
]

TEST_MODE = "--test" in sys.argv
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

def parse_date_posted(date_val):
    if not date_val:
        return datetime.now().strftime("%Y-%m-%d")
    date_str = str(date_val).strip().lower()
    
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
        
    return today.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# PORTAL SCRAPERS (NORMAL)
# ---------------------------------------------------------------------------

def scrape_shine(role, city):
    global browser_instance
    if not browser_instance:
        return []
    print("  - Scraping Shine (via Playwright)...")
    role_slug = role.replace(" ", "-").lower()
    city_slug = city.lower().split(",")[0].strip().replace(" ", "-")
    url = f"https://www.shine.com/job-search/{role_slug}-jobs-in-{city_slug}"
    jobs = []
    try:
        context = browser_instance.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()
        page.goto(url, wait_until="load", timeout=30000)
        page.wait_for_timeout(3000)
        content = page.content()
        soup = BeautifulSoup(content, "html.parser")
        next_data = soup.find("script", id="__NEXT_DATA__")
        if next_data:
            try:
                js_data = json.loads(next_data.string)
                page_props = js_data.get("props", {}).get("pageProps", {})
                results = (
                    page_props
                    .get("initialState", {})
                    .get("jsrp", {})
                    .get("searchresult", {})
                    .get("data", {})
                    .get("results", [])
                )
                for item in results:
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
            except Exception as e:
                print(f"    Shine JSON parse error: {e}")
        context.close()
    except Exception as e:
        print(f"    Shine Playwright error: {e}")
    return jobs

def scrape_timesjobs(role, city):
    """Scrape TimesJobs via their internal JSON API (no Playwright needed).
    API: POST https://tjapi.timesjobs.com/search/api/v1/search/jobs/list
    Returns up to 20 jobs per page with rich structured data.
    """
    print("  - Scraping TimesJobs (via API)...")
    jobs = []
    try:
        payload = {
            "keyword": role,
            "location": city,
            "experience": "",
            "page": "1",
            "size": "20",
            "jobFunctions": [],
            "company": "",
            "industry": "",
            "functionAreaId": "",
            "jobFunction": ""
        }
        api_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.timesjobs.com",
            "Referer": "https://www.timesjobs.com/",
        }
        resp = requests.post(
            "https://tjapi.timesjobs.com/search/api/v1/search/jobs/list",
            headers=api_headers,
            json=payload,
            timeout=20,
            verify=False
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("jobs", []):
                title = (item.get("title") or "").strip()
                company = (item.get("company") or item.get("hfCompany") or "").strip()
                loc = (item.get("location") or city).strip()
                date_posted = parse_date_posted(item.get("postDate"))
                job_url = item.get("jobDetailUrl", "")
                if title and job_url:
                    jobs.append({
                        "title": title, "company": company, "location": loc,
                        "date_posted": date_posted, "url": job_url,
                        "source": "timesjobs", "role_search": role
                    })
        else:
            print(f"    TimesJobs API returned {resp.status_code}")
    except Exception as e:
        print(f"    TimesJobs API error: {e}")
    return jobs

# Hirist location IDs mapping
HIRIST_LOC_IDS = {
    "bangalore": 3, "chennai": 17, "hyderabad": 4, "mumbai": 5,
    "pune": 6, "delhi": 1, "noida": 76, "gurgaon": 2,
    "kolkata": 7, "ahmedabad": 8, "kochi": 59, "chandigarh": 82,
    "indore": 73, "jaipur": 64, "coimbatore": 79,
}

def scrape_hirist(role, city):
    """Scrape Hirist via their internal JSON API (no Playwright needed).
    API: GET https://gladiator.hirist.tech/job/keyword/
    Note: The query param has limited filtering — results are primarily
    filtered by location ID. Each page returns ~20-40 jobs.
    """
    print("  - Scraping Hirist (via API)...")
    jobs = []
    city_lower = city.lower().split(",")[0].strip()
    loc_id = HIRIST_LOC_IDS.get(city_lower, 3)  # Default to Bangalore
    try:
        role_enc = urllib.parse.quote(role)
        url = f"https://gladiator.hirist.tech/job/keyword/?query={role_enc}&page=1&loc={loc_id}&industry=&concat=true&id=&size=20"
        api_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        resp = requests.get(url, headers=api_headers, timeout=20, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("data", []):
                title = (item.get("title") or "").strip()
                company_data = item.get("companyData") or {}
                company = (company_data.get("companyName") or "").strip()
                # Skip "hirist.tech" placeholder company names
                if company.lower() in ["hirist.tech", "hirist"]:
                    company = "Confidential"
                locs = item.get("locations") or item.get("location") or []
                if isinstance(locs, list) and locs:
                    loc = ", ".join(l.get("name", "") for l in locs[:3])
                else:
                    loc = city
                # Hirist doesn't return a posted date, use createdTime epoch
                created_ms = item.get("createdTime") or item.get("createdTimeMs")
                if created_ms:
                    date_posted = datetime.fromtimestamp(created_ms / 1000).strftime("%Y-%m-%d")
                else:
                    date_posted = datetime.now().strftime("%Y-%m-%d")
                job_id = item.get("id", "")
                job_url = f"https://www.hirist.tech/j/{job_id}" if job_id else ""
                if title and job_url:
                    jobs.append({
                        "title": title, "company": company, "location": loc,
                        "date_posted": date_posted, "url": job_url,
                        "source": "hirist", "role_search": role
                    })
        else:
            print(f"    Hirist API returned {resp.status_code}")
    except Exception as e:
        print(f"    Hirist API error: {e}")
    return jobs

def scrape_workindia(role, city):
    print("  - Scraping WorkIndia...")
    jobs = []
    try:
        role_fmt = role.lower().replace(" ", "-")
        city_fmt = "bengaluru" if city.lower() == "bangalore" else city.lower().replace(" ", "-")
        url = f"https://www.workindia.in/{role_fmt}-jobs-in-{city_fmt}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = soup.select('div[class*="JobCard"], div.JobCard, a[href*="/company/"]')
            for card in cards:
                title_el = card.select_one('h2, [class*="JobTitle"]')
                company_el = card.select_one('h3, [class*="Company"]')
                
                title = title_el.text.strip() if title_el else ""
                company = company_el.text.strip() if company_el else ""
                
                if card.name == 'a':
                    job_url = "https://www.workindia.in" + card.get('href', '')
                else:
                    link = card.select_one('a')
                    job_url = "https://www.workindia.in" + link.get('href', '') if link else ""
                
                if title and company:
                    jobs.append({
                        "title": title, "company": company, "location": city,
                        "date_posted": datetime.now().strftime("%Y-%m-%d"), 
                        "url": job_url, "source": "workindia", "role_search": role
                    })
    except Exception as e:
        print(f"    WorkIndia error: {e}")
    return jobs

def scrape_internshala(role, city):
    print("  - Scraping Internshala...")
    jobs = []
    try:
        role_fmt = role.lower().replace(" ", "-")
        city_fmt = city.lower().replace(" ", "-")
        url = f"https://internshala.com/jobs/{role_fmt}-jobs-in-{city_fmt}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = soup.select('div.internship_meta, div.job-card, div.individual_internship')
            for card in cards:
                title_el = card.select_one('h3.job-internship-name a, h3.heading_4_5 a')
                company_el = card.select_one('p.company-name, div.company_name a')
                loc_el = card.select_one('p#location_names, div#location_names span')
                
                title = title_el.text.strip() if title_el else ""
                company = company_el.text.strip() if company_el else ""
                loc = loc_el.text.strip() if loc_el else city
                job_url = "https://internshala.com" + title_el.get('href', '') if title_el else ""
                
                if title and company:
                    jobs.append({
                        "title": title, "company": company, "location": loc,
                        "date_posted": datetime.now().strftime("%Y-%m-%d"), 
                        "url": job_url, "source": "internshala", "role_search": role
                    })
    except Exception as e:
        print(f"    Internshala error: {e}")
    return jobs

def scrape_freshersworld(role, city):
    print("  - Scraping Freshersworld...")
    jobs = []
    try:
        role_fmt = role.lower().replace(" ", "-")
        city_fmt = city.lower().replace(" ", "-")
        url = f"https://www.freshersworld.com/jobs/jobsearch/{role_fmt}-jobs-in-{city_fmt}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = soup.select('div.job-container, div.job-detail-block, div.job-desc-block, div.col-md-12.col-lg-12.col-xs-12.padding-none.job-container')
            for card in cards:
                title_el = card.select_one('div.job-desc-title, span.wrap-title')
                company_el = card.select_one('h3.latest-jobs-title, div.job-desc-company')
                loc_el = card.select_one('span.job-location')
                
                title = title_el.text.strip() if title_el else ""
                company = company_el.text.strip() if company_el else ""
                loc = loc_el.text.strip() if loc_el else city
                
                link = card.parent if card.parent and card.parent.name == 'a' else None
                if not link:
                    link = card.select_one('a')
                job_url = link.get('href', '') if link else ""
                
                if title and company:
                    jobs.append({
                        "title": title, "company": company, "location": loc,
                        "date_posted": datetime.now().strftime("%Y-%m-%d"), 
                        "url": job_url, "source": "freshersworld", "role_search": role
                    })
    except Exception as e:
        print(f"    Freshersworld error: {e}")
    return jobs

def scrape_glassdoor(role, city):
    print("  - Scraping Glassdoor (via JobSpy)...")
    jobs = []
    if not scrape_jobs:
        print("    jobspy module not found.")
        return jobs
    try:
        df = scrape_jobs(
            site_name=["glassdoor"],
            search_term=role,
            location=city,
            results_wanted=15,
            country_indeed="india"
        )
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                jobs.append({
                    "title": str(row.get("title", "")),
                    "company": str(row.get("company", "")),
                    "location": str(row.get("location", city)),
                    "date_posted": str(row.get("date_posted", datetime.now().strftime("%Y-%m-%d"))),
                    "url": str(row.get("job_url", "")),
                    "source": "glassdoor",
                    "role_search": role
                })
    except Exception as e:
        print(f"    Glassdoor JobSpy error: {e}")
    return jobs

def scrape_apna(role, city):
    global browser_instance
    if not browser_instance:
        return []
    print("  - Scraping Apna (via Playwright)...")
    role_enc = role.replace(" ", "-").lower()
    city_enc = city.lower().split(",")[0].strip()
    url = f"https://apna.co/jobs/{role_enc}-jobs-in-{city_enc}"
    jobs = []
    try:
        context = browser_instance.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()
        page.goto(url, wait_until="load", timeout=45000)
        page.wait_for_timeout(5000)
        content = page.content()
        soup = BeautifulSoup(content, "html.parser")
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
                            "title": title, "company": company, "location": loc,
                            "date_posted": date_str, "url": job_url,
                            "source": "apna", "role_search": role
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
                        "title": title, "company": company, "location": loc,
                        "date_posted": date_str, "url": job_url,
                        "source": "apna", "role_search": role
                    })
        context.close()
    except Exception as e:
        print(f"    Apna Playwright error: {e}")
    return jobs

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  JOB PORTALS SCRAPER (SHINE, TIMESJOBS, HIRIST, APNA, WORKINDIA, INTERNSHALA, FRESHERSWORLD, GLASSDOOR)")
    print("=" * 70)
    print(f"  📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🔍 Roles Count: {len(SEARCH_ROLES)}")
    print(f"  📍 Cities Count: {len(LOCATIONS)}")
    print(f"  🌐 Portals: Shine (Playwright), TimesJobs (API), Hirist (API), Apna (Playwright), WorkIndia (Requests), Internshala (API), Freshersworld (Requests), Glassdoor (JobSpy)")
    print("=" * 70)

    cleanup_old_jobs()
    init_playwright()

    progress = load_progress()
    start_role = progress.get("role_idx", 0)
    start_loc = progress.get("loc_idx", 0)

    total_inserted = 0
    total_combos = len(SEARCH_ROLES) * len(LOCATIONS)
    combo_num = start_role * len(LOCATIONS) + start_loc
    hit_time_limit = False

    scraped_counts = {"shine": 0, "timesjobs": 0, "hirist": 0, "apna": 0, "workindia": 0, "internshala": 0, "freshersworld": 0, "glassdoor": 0}
    stored_counts = {"shine": 0, "timesjobs": 0, "hirist": 0, "apna": 0, "workindia": 0, "internshala": 0, "freshersworld": 0, "glassdoor": 0}

    for r_idx in range(start_role, len(SEARCH_ROLES)):
        role = SEARCH_ROLES[r_idx]
        curr_start_loc_idx = start_loc if r_idx == start_role else 0
        
        for l_idx in range(curr_start_loc_idx, len(LOCATIONS)):
            city = LOCATIONS[l_idx]
            combo_num += 1

            elapsed = time.time() - START_TIME
            if elapsed >= MAX_RUN_SECONDS:
                print(f"\n⏰ Time limit reached ({elapsed:.0f}s). Saving progress...")
                save_progress(r_idx, l_idx, finished_all=False)
                hit_time_limit = True
                break

            save_progress(r_idx, l_idx, finished_all=False)

            print(f"\n[{combo_num}/{total_combos}] '{role}' in '{city}'...")

            # ── 1. Shine ──
            shine_jobs = scrape_shine(role, city)
            n = len(shine_jobs); ins = store_jobs_batch(shine_jobs)
            scraped_counts["shine"] += n; stored_counts["shine"] += ins
            total_inserted += ins
            print(f"      Shine         : {n:>4} scraped  |  {ins:>4} new stored")

            # ── 2. TimesJobs ──
            tj_jobs = scrape_timesjobs(role, city)
            n = len(tj_jobs); ins = store_jobs_batch(tj_jobs)
            scraped_counts["timesjobs"] += n; stored_counts["timesjobs"] += ins
            total_inserted += ins
            print(f"      TimesJobs     : {n:>4} scraped  |  {ins:>4} new stored")

            # ── 3. Hirist ──
            hirist_jobs = scrape_hirist(role, city)
            n = len(hirist_jobs); ins = store_jobs_batch(hirist_jobs)
            scraped_counts["hirist"] += n; stored_counts["hirist"] += ins
            total_inserted += ins
            print(f"      Hirist        : {n:>4} scraped  |  {ins:>4} new stored")

            # ── 4. Apna ──
            apna_jobs = scrape_apna(role, city)
            n = len(apna_jobs); ins = store_jobs_batch(apna_jobs)
            scraped_counts["apna"] += n; stored_counts["apna"] += ins
            total_inserted += ins
            print(f"      Apna          : {n:>4} scraped  |  {ins:>4} new stored")

            # ── 5. WorkIndia ──
            wi_jobs = scrape_workindia(role, city)
            n = len(wi_jobs); ins = store_jobs_batch(wi_jobs)
            scraped_counts["workindia"] += n; stored_counts["workindia"] += ins
            total_inserted += ins
            print(f"      WorkIndia     : {n:>4} scraped  |  {ins:>4} new stored")

            # ── 6. Internshala ──
            int_jobs = scrape_internshala(role, city)
            n = len(int_jobs); ins = store_jobs_batch(int_jobs)
            scraped_counts["internshala"] += n; stored_counts["internshala"] += ins
            total_inserted += ins
            print(f"      Internshala   : {n:>4} scraped  |  {ins:>4} new stored")

            # ── 7. Freshersworld ──
            fw_jobs = scrape_freshersworld(role, city)
            n = len(fw_jobs); ins = store_jobs_batch(fw_jobs)
            scraped_counts["freshersworld"] += n; stored_counts["freshersworld"] += ins
            total_inserted += ins
            print(f"      Freshersworld : {n:>4} scraped  |  {ins:>4} new stored")

            # ── 8. Glassdoor ──
            gd_jobs = scrape_glassdoor(role, city)
            n = len(gd_jobs); ins = store_jobs_batch(gd_jobs)
            scraped_counts["glassdoor"] += n; stored_counts["glassdoor"] += ins
            total_inserted += ins
            print(f"      Glassdoor     : {n:>4} scraped  |  {ins:>4} new stored")

            # Delay to avoid getting blocked
            time.sleep(2)

        if hit_time_limit:
            break

    close_playwright()

    if not hit_time_limit:
        save_progress(0, 0, finished_all=True)
        print("\n✅ Scraper completed all roles. Progress reset.")

    print("\n" + "=" * 70)
    print("                    JOB PORTAL STATISTICS SUMMARY")
    print("=" * 70)
    print(f"{'Job Portal':<22} | {'Scraped (Raw)':<16} | {'Stored (New D1)':<16}")
    print("-" * 70)
    for portal in scraped_counts:
        print(f"{portal.upper():<22} | {scraped_counts[portal]:<16} | {stored_counts[portal]:<16}")
    print("=" * 70)
    print(f"{'TOTAL SUM':<22} | {sum(scraped_counts.values()):<16} | {total_inserted:<16}")
    print("=" * 70)

if __name__ == "__main__":
    main()
