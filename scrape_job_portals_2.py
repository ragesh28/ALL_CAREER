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
try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

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
    pass

import storage
def store_jobs_batch(jobs):
    return storage.store_jobs_batch(jobs)

def cleanup_old_jobs():
    pass

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
    jobs = []
    
    cutoff_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    try:
        context = browser_instance.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page_obj = context.new_page()
        
        for page in range(1, 5):
            if page == 1:
                url = f"https://www.shine.com/job-search/{role_slug}-jobs-in-{city_slug}"
            else:
                url = f"https://www.shine.com/job-search/{role_slug}-jobs-in-{city_slug}-{page}"
                
            print(f"    Page {page}: {url}")
            try:
                page_obj.goto(url, wait_until="load", timeout=30000)
                page_obj.wait_for_timeout(3000)
                content = page_obj.content()
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
                        if not results:
                            break
                        for item in results:
                            date_posted = item.get("jPDate") or item.get("postedDate")
                            date_str = parse_date_posted(date_posted)
                            if date_str < cutoff_date:
                                continue  # Skip older than 3 days
                            
                            title = (item.get("jJT") or item.get("title") or "").strip()
                            company = (item.get("jCName") or item.get("companyName") or "").strip()
                            loc = item.get("jLoc") or item.get("location") or city
                            if isinstance(loc, list):
                                loc = ", ".join(loc)
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
                            # Experience
                            experience = item.get("jExp", "")
                            if title and job_url:
                                jobs.append({
                                    "title": title, "company": company,
                                    "location": loc, "date_posted": date_str,
                                    "url": job_url, "source": "shine", "role_search": role,
                                    "experience": experience
                                })
                    except Exception as e:
                        print(f"    Shine JSON parse error: {e}")
            except Exception as e:
                print(f"    Shine Playwright page error: {e}")
                break
            time.sleep(1)
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
    
    cutoff_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    try:
        api_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.timesjobs.com",
            "Referer": "https://www.timesjobs.com/",
        }
        
        for page in range(1, 5):
            payload = {
                "keyword": role,
                "location": city,
                "experience": "",
                "page": str(page),
                "size": "20",
                "jobFunctions": [],
                "company": "",
                "industry": "",
                "functionAreaId": "",
                "jobFunction": ""
            }
            url = "https://tjapi.timesjobs.com/search/api/v1/search/jobs/list"
            print(f"    Page {page}: {url}")
            resp = requests.post(
                url,
                headers=api_headers,
                json=payload,
                timeout=20,
                verify=False
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("jobs", [])
                if not items:
                    break
                for item in items:
                    date_posted = parse_date_posted(item.get("postDate"))
                    if date_posted < cutoff_date:
                        continue  # Skip jobs older than 3 days
                    
                    title = (item.get("title") or "").strip()
                    company = (item.get("company") or item.get("hfCompany") or "").strip()
                    loc = (item.get("location") or city).strip()
                    job_url = item.get("jobDetailUrl", "")
                    # Experience
                    exp_from = item.get("experienceFrom", "")
                    exp_to = item.get("experienceTo", "")
                    experience = f"{exp_from}-{exp_to} Yrs" if exp_from and exp_to else ""
                    if title and job_url:
                        jobs.append({
                            "title": title, "company": company, "location": loc,
                            "date_posted": date_posted, "url": job_url,
                            "source": "timesjobs", "role_search": role,
                            "experience": experience
                        })
            else:
                print(f"    TimesJobs API returned {resp.status_code}")
                break
            time.sleep(1)
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
    
    cutoff_ms = (datetime.now() - timedelta(days=3)).timestamp() * 1000
    
    try:
        role_enc = urllib.parse.quote(role)
        api_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        
        for page in range(1, 5):
            url = f"https://gladiator.hirist.tech/job/keyword/?query={role_enc}&page={page}&loc={loc_id}&industry=&concat=true&id=&size=20"
            print(f"    Page {page}: {url}")
            resp = requests.get(url, headers=api_headers, timeout=20, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", [])
                if not items:
                    break
                for item in items:
                    created_ms = item.get("createdTime") or item.get("createdTimeMs")
                    if created_ms and created_ms < cutoff_ms:
                        continue  # Skip jobs older than 3 days
                    
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
                        
                    if created_ms:
                        date_posted = datetime.fromtimestamp(created_ms / 1000).strftime("%Y-%m-%d")
                    else:
                        date_posted = datetime.now().strftime("%Y-%m-%d")
                        
                    job_id = item.get("id", "")
                    job_url = f"https://www.hirist.tech/j/{job_id}" if job_id else ""
                    # Experience
                    min_exp = item.get("min", "")
                    max_exp = item.get("max", "")
                    experience = f"{min_exp}-{max_exp} Yrs" if min_exp is not None and max_exp is not None else ""
                    if title and job_url:
                        jobs.append({
                            "title": title, "company": company, "location": loc,
                            "date_posted": date_posted, "url": job_url,
                            "source": "hirist", "role_search": role,
                            "experience": experience
                        })
            else:
                print(f"    Hirist API returned {resp.status_code}")
                break
            time.sleep(1)
    except Exception as e:
        print(f"    Hirist API error: {e}")
    return jobs

def scrape_workindia(role, city):
    """Scrape WorkIndia using Playwright to bypass anti-bot, extract __ROUTE_DATA__."""
    global browser_instance
    print("  - Scraping WorkIndia (Playwright + __ROUTE_DATA__)...")
    jobs = []
    
    EXP_MAP = {"fresher": "Fresher", "lt_1_year": "0-1 Yrs", "1_to_2_years": "1-2 Yrs",
               "gt_2_years": "2+ Yrs", "experience": "Experienced"}
    try:
        role_fmt = role.lower().replace(" ", "-")
        city_fmt = "bengaluru" if city.lower() == "bangalore" else city.lower().replace(" ", "-")
        
        url = f"https://www.workindia.in/{role_fmt}-jobs-in-{city_fmt}/"
        print(f"    URL: {url}")
        
        page_content = ""
        if browser_instance:
            try:
                context = browser_instance.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1440, "height": 900}
                )
                page_obj = context.new_page()
                page_obj.goto(url, wait_until="load", timeout=30000)
                page_obj.wait_for_timeout(3000)
                page_content = page_obj.content()
                page_obj.close()
                context.close()
            except Exception as e:
                print(f"    Playwright error: {e}")
        elif curl_requests:
            try:
                r = curl_requests.get(url, impersonate="chrome124", timeout=30, verify=False)
                if r.status_code == 200:
                    page_content = r.text
                else:
                    print(f"    WorkIndia returned {r.status_code}")
            except Exception as e:
                print(f"    curl_cffi error: {e}")
        else:
            print("    No Playwright or curl_cffi available!")
            return []
        
        if page_content:
            match = re.search(r'__ROUTE_DATA__\s*=\s*(.*?)\s*</script>', page_content, re.DOTALL)
            if match:
                try:
                    route_data = json.loads(match.group(1))
                    data_list = route_data.get("data", [])
                    for j in data_list:
                        title = j.get("profile_job_title", "")
                        company = j.get("branch_company_name", "")
                        loc = j.get("branch_location_city_name", "").title() or city
                        date_posted = str(j.get("created_at", ""))[:10] or datetime.now().strftime("%Y-%m-%d")
                        job_id = j.get("id", "")
                        job_url = f"https://www.workindia.in/jobs/{job_id}/" if job_id else ""
                        exp_raw = j.get("job_experience", "")
                        experience = EXP_MAP.get(exp_raw, exp_raw)
                        if title and company:
                            jobs.append({
                                "title": title, "company": company, "location": loc,
                                "date_posted": date_posted, "url": job_url,
                                "source": "workindia", "role_search": role,
                                "experience": experience
                            })
                except Exception as e:
                    print(f"    WorkIndia JSON parse error: {e}")
            else:
                print("    No __ROUTE_DATA__ found in page")
    except Exception as e:
        print(f"    WorkIndia error: {e}")
    return jobs

def scrape_internshala(role, city):
    print("  - Scraping Internshala (Playwright)...")
    global browser_instance
    jobs = []
    try:
        role_fmt = role.lower().replace(" ", "-")
        city_fmt = city.lower().replace(" ", "-")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        for page in range(1, 5):
            if page == 1:
                url = f"https://internshala.com/jobs/{role_fmt}-jobs-in-{city_fmt}/"
            else:
                url = f"https://internshala.com/jobs/{role_fmt}-jobs-in-{city_fmt}/page-{page}/"
                
            print(f"    Page {page}: {url}")
            
            page_content = ""
            if browser_instance:
                try:
                    context = browser_instance.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                        viewport={"width": 1440, "height": 900}
                    )
                    page_obj = context.new_page()
                    page_obj.goto(url, wait_until="load", timeout=30000)
                    page_obj.wait_for_timeout(2000)
                    page_content = page_obj.content()
                    page_obj.close()
                    context.close()
                except Exception as e:
                    print(f"    Playwright error: {e}")
            else:
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code == 200:
                    page_content = r.text
                else:
                    print(f"    Internshala page {page} returned {r.status_code}")
                    break
            
            if page_content:
                soup = BeautifulSoup(page_content, 'html.parser')
                cards = soup.select('div.internship_meta, div.job-card, div.individual_internship')
                if not cards:
                    break
                for card in cards:
                    title_el = card.select_one('a.job-title-href, h3.job-internship-name a, h3.heading_4_5 a')
                    company_el = card.select_one('p.company-name, div.company_name a')
                    loc_el = card.select_one('p#location_names, div#location_names span, p.locations a, span.locations a, .locations a')
                    
                    title = title_el.text.strip() if title_el else ""
                    company = company_el.text.strip() if company_el else ""
                    loc = loc_el.text.strip() if loc_el else city
                    job_url = "https://internshala.com" + title_el.get('href', '') if title_el else ""
                    # Experience: find text like "1 year(s)" but NOT salary
                    experience = ""
                    for el in card.find_all(['span', 'p', 'div']):
                        txt = el.get_text(strip=True)
                        if txt and re.match(r'^\d+\s*(?:[-–]\s*\d+\s*)?year', txt, re.I) and '₹' not in txt:
                            experience = txt
                            break
                    
                    if title and company:
                        jobs.append({
                            "title": title, "company": company, "location": loc,
                            "date_posted": datetime.now().strftime("%Y-%m-%d"), 
                            "url": job_url, "source": "internshala", "role_search": role,
                            "experience": experience
                        })
            time.sleep(1)
    except Exception as e:
        print(f"    Internshala error: {e}")
    return jobs

def scrape_freshersworld(role, city):
    print("  - Scraping Freshersworld (Playwright)...")
    global browser_instance
    jobs = []
    try:
        role_fmt = role.lower().replace(" ", "-")
        city_fmt = city.lower().replace(" ", "-")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        for page in range(1, 5):
            if page == 1:
                url = f"https://www.freshersworld.com/jobs/jobsearch/{role_fmt}-jobs-in-{city_fmt}"
            else:
                offset = (page - 1) * 20
                url = f"https://www.freshersworld.com/jobs/jobsearch/{role_fmt}-jobs-in-{city_fmt}?limit=20&offset={offset}"
                
            print(f"    Page {page}: {url}")
            
            page_content = ""
            if browser_instance:
                try:
                    context = browser_instance.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                        viewport={"width": 1440, "height": 900}
                    )
                    page_obj = context.new_page()
                    page_obj.goto(url, wait_until="load", timeout=30000)
                    page_obj.wait_for_timeout(2000)
                    page_content = page_obj.content()
                    page_obj.close()
                    context.close()
                except Exception as e:
                    print(f"    Playwright error: {e}")
            else:
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code == 200:
                    page_content = r.text
                else:
                    print(f"    Freshersworld page {page} returned {r.status_code}")
                    break
            
            if page_content:
                soup = BeautifulSoup(page_content, 'html.parser')
                cards = soup.select('div.job-container, div.job-detail-block, div.job-desc-block, div.col-md-12.col-lg-12.col-xs-12.padding-none.job-container')
                if not cards:
                    break
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
                    
                    # Experience
                    exp_el = card.select_one('span.experience, [class*="experience"]')
                    experience = exp_el.get_text(strip=True) if exp_el else ""
                    if title and company:
                        jobs.append({
                            "title": title, "company": company, "location": loc,
                            "date_posted": datetime.now().strftime("%Y-%m-%d"), 
                            "url": job_url, "source": "freshersworld", "role_search": role,
                            "experience": experience
                        })
            time.sleep(1)
    except Exception as e:
        print(f"    Freshersworld error: {e}")
    return jobs

def scrape_glassdoor(role, city):
    print("  - Scraping Glassdoor (via ScraperAPI)...")
    
    import os, random, urllib.parse, re, json, bs4
    scraperapi_keys = [k.strip() for k in os.environ.get("SCRAPERAPI_KEYS_LIST", "").split(",") if k.strip()]
    if not scraperapi_keys:
        print("    No SCRAPERAPI_KEYS_LIST found in environment. Skipping Glassdoor.")
        return []
        
    api_key = random.choice(scraperapi_keys)
    target_url = f"https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={urllib.parse.quote(role)}%20{urllib.parse.quote(city)}"
    proxy_url = f"https://api.scraperapi.com?api_key={api_key}&url={urllib.parse.quote(target_url)}&render=true"
    
    jobs = []
    fetched_at = datetime.now().strftime("%Y-%m-%d")
    
    try:
        r = requests.get(proxy_url, timeout=90)
        if r.status_code == 200:
            html_content = r.text
            soup = bs4.BeautifulSoup(html_content, 'html.parser')
            
            apollo_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*(\{.*?\});', html_content)
            if apollo_match:
                try:
                    state = json.loads(apollo_match.group(1))
                    for key, val in state.items():
                        if isinstance(val, dict) and (val.get('__typename') == 'JobListingSearchResult' or 'jobview' in val):
                            jobview = val.get('jobview', {})
                            header = jobview.get('header', {})
                            job_info = jobview.get('job', {})
                            
                            title = header.get('jobTitleText') or job_info.get('jobTitleText')
                            company = header.get('employerNameFromSearch') or header.get('employer', {}).get('name')
                            location = header.get('locationName', '')
                            job_id = job_info.get('listingId')
                            
                            if title and company and job_id:
                                direct_url = f"https://www.glassdoor.co.in/job-listing/j?jl={job_id}"
                                jobs.append({
                                    "title": title.strip(),
                                    "company": company.strip(),
                                    "location": location.strip(),
                                    "url": direct_url,
                                    "linkedin_url": "",
                                    "date": "Recent",
                                    "source": "glassdoor",
                                    "role_search": role,
                                    "fetchedAt": fetched_at
                                })
                except Exception as e:
                    print(f"    Error parsing Glassdoor Apollo state: {e}")
            
            if not jobs:
                cards = soup.find_all(attrs={"data-test": "jobListing"})
                if not cards:
                    cards = soup.find_all("li", class_=re.compile("jobListing|JobCard", re.I))
                
                for card in cards:
                    try:
                        title_elem = card.find(attrs={"data-test": "job-title"}) or card.find("a", class_=re.compile("JobCard_jobTitle"))
                        title = title_elem.text.strip() if title_elem else ""
                        
                        comp_elem = card.find(attrs={"data-test": "employer-name"}) or card.find("span", class_=re.compile("EmployerProfile_employerName"))
                        company = comp_elem.text.strip() if comp_elem else ""
                        if company and "\n" in company: company = company.split("\n")[0]
                        if company and "★" in company: company = company.split("★")[0]
                        
                        loc_elem = card.find(attrs={"data-test": "emp-location"}) or card.find(attrs={"data-test": "location"})
                        location = loc_elem.text.strip() if loc_elem else ""
                        
                        a_tag = card.find("a", href=re.compile("/job-listing/"))
                        url = a_tag["href"] if a_tag else ""
                        if url and url.startswith("/"):
                            url = "https://www.glassdoor.co.in" + url
                            
                        if title and company and url:
                            jobs.append({
                                "title": title,
                                "company": company.strip(),
                                "location": location,
                                "url": url,
                                "linkedin_url": "",
                                "date": "Recent",
                                "source": "glassdoor",
                                "role_search": role,
                                "fetchedAt": fetched_at
                            })
                    except:
                        continue
                        
        else:
            print(f"    Glassdoor ScraperAPI error: Status {r.status_code}")
    except Exception as e:
        print(f"    Glassdoor fetch error: {e}")
        
    # Deduplicate jobs by URL/title
    unique_jobs = []
    seen_urls = set()
    for job in jobs:
        if job["url"] not in seen_urls:
            unique_jobs.append(job)
            seen_urls.add(job["url"])
            
    print(f"    Found {len(unique_jobs)} Glassdoor jobs")
    return unique_jobs

def scrape_apna(role, city):
    print("  - Scraping Apna (via API)...")
    role_enc = role.replace(" ", "-").lower()
    
    city_lower = city.lower().split(",")[0].strip()
    city_slug = "bengaluru" if city_lower == "bangalore" else city_lower.replace(" ", "-")
    url = f"https://apna.co/jobs/{role_enc}-jobs-in-{city_slug}"
    jobs = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
    }
    
    cutoff_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    try:
        r = requests.get(url, headers=headers, timeout=20, verify=False)
        city_id = None
        state_name = None
        
        if r.status_code == 200:
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text)
            if m:
                try:
                    js_data = json.loads(m.group(1))
                    pageProps = js_data.get("props", {}).get("pageProps", {})
                    
                    filter_obj = pageProps.get("filter", {})
                    city_id = filter_obj.get("nb_location_city_id")
                    state_name = filter_obj.get("state_name")
                    
                    # Resolve state_name from cityList if not present in filter
                    if city_id and not state_name:
                        for c_item in pageProps.get("cityList", []):
                            if c_item.get("id") == city_id:
                                state_name = c_item.get("state")
                                break
                                
                    if not city_id and "city" in pageProps.get("filters", {}):
                        city_list = pageProps.get("filters", {}).get("city", [])
                        if city_list:
                            city_id = city_list[0].get("id")
                            state_name = city_list[0].get("state")
                            
                    results = pageProps.get("jobs", []) or pageProps.get("initialState", {}).get("jobs", [])
                    for item in results:
                        title = (item.get("title") or item.get("jobTitle", "")).strip()
                        company = (item.get("companyName") or item.get("company", {}).get("name", "")).strip()
                        loc = item.get("location") or item.get("locationName") or city
                        date_posted = item.get("postedDate") or item.get("created")
                        date_str = parse_date_posted(date_posted)
                        if date_str < cutoff_date:
                            continue
                        job_url = item.get("jobUrl") or item.get("url")
                        if not job_url and item.get("id"):
                            job_url = f"https://apna.co/job/{item.get('id')}"
                        if job_url and job_url.startswith("/"):
                            job_url = "https://apna.co" + job_url
                        # Experience
                        experience = item.get("experience_in_years", "")
                        min_e = item.get("min_experience")
                        max_e = item.get("max_experience")
                        if not experience and min_e is not None:
                            experience = f"{min_e}-{max_e} Yrs"
                        if title and job_url:
                            jobs.append({
                                "title": title, "company": company, "location": loc,
                                "date_posted": date_str, "url": job_url,
                                "source": "apna", "role_search": role,
                                "experience": experience
                            })
                except Exception as je:
                    print(f"    Apna page 1 JSON parse error: {je}")
        else:
            print(f"    Apna landing page returned {r.status_code}")
            
        if city_id and state_name:
            api_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://apna.co",
                "Referer": url,
            }
            state_enc = urllib.parse.quote(state_name)
            
            for page in range(2, 5):
                api_url = f"https://production.apna.co/user-profile-orchestrator/public/v1/jobs/?nb_location_city_id={city_id}&state_name={state_enc}&posted_in=72&page={page}&page_size=25"
                print(f"    Page {page}: {api_url}")
                try:
                    resp = requests.get(api_url, headers=api_headers, timeout=20, verify=False)
                    if resp.status_code == 200:
                        api_data = resp.json()
                        api_jobs = api_data.get("results", {}).get("jobs", [])
                        if not api_jobs:
                            break
                        for item in api_jobs:
                            title = (item.get("title") or "").strip()
                            company = (item.get("organization", {}) or {}).get("name", "").strip()
                            loc = item.get("location_name") or city
                            date_posted = item.get("created_on") or item.get("last_updated")
                            date_str = parse_date_posted(date_posted)
                            if date_str < cutoff_date:
                                continue
                            job_url = item.get("public_url_v2") or item.get("public_url")
                            if not job_url and item.get("id"):
                                job_url = f"https://apna.co/job/{item.get('id')}"
                            # Experience
                            experience = item.get("experience_in_years", "")
                            min_e = item.get("min_experience")
                            max_e = item.get("max_experience")
                            if not experience and min_e is not None:
                                experience = f"{min_e}-{max_e} Yrs"
                            if title and job_url:
                                jobs.append({
                                    "title": title, "company": company, "location": loc,
                                    "date_posted": date_str, "url": job_url,
                                    "source": "apna", "role_search": role,
                                    "experience": experience
                                })
                    else:
                        print(f"    Apna API page {page} returned {resp.status_code}")
                        break
                except Exception as ae:
                    print(f"    Apna API page {page} error: {ae}")
                    break
                time.sleep(1)
        else:
            print("    Warning: Could not extract Apna city/state ID from landing page. Pagination skipped.")
    except Exception as e:
        print(f"    Apna scraper error: {e}")
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
