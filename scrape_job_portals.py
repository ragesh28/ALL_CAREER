import os
import sys
import re
import json
import time
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

def get_active_scraperapi_key():
    keys_str = os.environ.get("SCRAPERAPI_KEYS_LIST", "")
    if not keys_str:
        # Fallback to older env var for local testing if needed
        keys_str = os.environ.get("SCRAPERAPI_KEY_2", "")
    
    if not keys_str:
        return None
        
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    for key in keys:
        try:
            url = f"http://api.scraperapi.com/account?api_key={key}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                request_count = data.get("requestCount", 0)
                request_limit = data.get("requestLimit", 0)
                remaining = request_limit - request_count
                # If key has at least 100 credits, we can use it
                if remaining >= 100:
                    print(f"Selected ScraperAPI Key starting with '{key[:4]}' ({remaining} credits remaining this month)")
                    return key
        except Exception as e:
            print(f"Error checking key {key[:4]}...: {e}")
            continue
    print("No ScraperAPI keys have enough credits left!")
    return None

SCRAPERAPI_KEY = get_active_scraperapi_key()

# Global Playwright Browser Instances
playwright_instance = None
browser_instance = None
browser_context = None

# Progress Checkpointing Configuration
PROGRESS_FILE = "job_portals_progress.json"
START_TIME = time.time()
MAX_RUN_SECONDS = 5 * 3600 + 50 * 60  # 5 hours 50 minutes

def load_progress():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
        if data.get("date") != today:
            print(f"New day detected (was {data.get('date')}, now {today}). Resetting progress to start.")
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
    """Initialize Playwright in HEADFUL mode with anti-detection for Naukri."""
    global playwright_instance, browser_instance, browser_context
    try:
        from playwright.sync_api import sync_playwright
        playwright_instance = sync_playwright().start()
        browser_instance = playwright_instance.chromium.launch(
            headless=False,  # HEADFUL mode is critical for Naukri
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--window-size=1920,1080",
            ]
        )
        browser_context = browser_instance.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        print("Playwright Chromium browser initialized (HEADFUL mode for Naukri)!")
    except Exception as e:
        print(f"Playwright initialization error: {e}")

def close_playwright():
    global playwright_instance, browser_instance, browser_context
    try:
        if browser_context:
            browser_context.close()
        if browser_instance:
            browser_instance.close()
        if playwright_instance:
            playwright_instance.stop()
        print("Playwright Chromium browser closed.")
    except Exception as e:
        pass

# Roles & Cities (Restricted to 12 tech roles and 4 locations for Premium to save credits)
SEARCH_ROLES = [
    "Software Developer", "Software Engineer", "Frontend Developer", 
    "Backend Developer", "Full Stack Developer", "Mobile App Developer", 
    "DevOps Engineer", "Data Analyst", "Data Engineer", "Data Scientist", 
    "AI Engineer", "Machine Learning Engineer"
]

LOCATIONS = [
    "Bangalore", "Chennai", "Hyderabad", "Mumbai"
]

TEST_MODE = "--test" in sys.argv
if TEST_MODE:
    print("RUNNING IN TEST MODE: Only 1 role and 1 location will be scraped.")
    SEARCH_ROLES = ["Software Engineer"]
    LOCATIONS = ["Bangalore"]

# ---------------------------------------------------------------------------
# DATABASE HELPERS (Cloudflare D1 REST API)
# ---------------------------------------------------------------------------
def d1_execute(sql, params=None):
    if not CLOUDFLARE_API_TOKEN:
        print("CLOUDFLARE_API_TOKEN not configured, skipping D1 database execution.")
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
        print(f"D1 Error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"D1 Connection error: {e}")
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
    print(f"Cleaning jobs older than {cutoff} (30 days retention)...")
    result = d1_execute("DELETE FROM all_jobs WHERE job_posted_date < ?", [cutoff])
    if result and result.get("success"):
        for res in result.get("result", []):
            deleted = res.get("meta", {}).get("changes", 0)
            print(f"Removed {deleted} old jobs from D1 database.")

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
# NAUKRI SCRAPER - Playwright HEADFUL + API Interception (FREE, 0 credits)
# ---------------------------------------------------------------------------
def scrape_naukri(role, city):
    """Scrape Naukri using Playwright headful mode + API interception.
    This is completely FREE - no proxy, no ScraperAPI credits needed.
    Playwright opens a real Chrome browser, navigates to the search page,
    and intercepts the internal jobapi/v3/search JSON response."""
    global browser_context
    
    if not browser_context:
        print("    Naukri: Playwright not initialized, skipping.")
        return []
    
    print("  - Scraping Naukri (Playwright headful - FREE, 0 credits)...")
    role_clean = role.replace(" ", "-").lower()
    city_clean = city.lower().split(",")[0].strip()
    url = f"https://www.naukri.com/{role_clean}-jobs-in-{city_clean}?jobAge=1"
    
    jobs = []
    api_jobs_data = []
    
    def handle_response(response):
        """Intercept Naukri's internal jobapi/v3/search API call."""
        try:
            resp_url = response.url
            if 'jobapi/v3/search' in resp_url:
                ct = response.headers.get('content-type', '')
                if 'json' in ct:
                    body = response.json()
                    api_jobs_data.append(body)
        except:
            pass
    
    try:
        page = browser_context.new_page()
        
        # Anti-detection: remove navigator.webdriver flag
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)
        
        page.on("response", handle_response)
        page.goto(url, wait_until="networkidle", timeout=60000)
        
        # Simulate human scrolling
        page.mouse.move(500, 300)
        time.sleep(1)
        page.mouse.wheel(0, 500)
        time.sleep(2)
        
        # Extract jobs from intercepted API data
        for api_data in api_jobs_data:
            if not isinstance(api_data, dict):
                continue
            job_details = api_data.get('jobDetails', [])
            for job_obj in job_details:
                if not isinstance(job_obj, dict):
                    continue
                title = job_obj.get('title', '')
                company = job_obj.get('companyName', '')
                loc = job_obj.get('placeholders', [{}])
                location = ''
                if isinstance(loc, list):
                    for ph in loc:
                        if isinstance(ph, dict) and ph.get('type') == 'location':
                            location = ph.get('label', city)
                            break
                if not location:
                    location = city
                
                job_url = job_obj.get('jdURL', '')
                if job_url and not job_url.startswith('http'):
                    job_url = f"https://www.naukri.com{job_url}"
                
                date_str = job_obj.get('footerPlaceholderLabel', '')
                date_posted = parse_date_posted(date_str)
                
                if title and job_url:
                    jobs.append({
                        "title": title, "company": company, "location": location,
                        "date_posted": date_posted, "url": job_url,
                        "source": "naukri", "role_search": role
                    })
        
        page.close()
        
    except Exception as e:
        print(f"    Naukri Playwright error: {e}")
    
    return jobs

# ---------------------------------------------------------------------------
# FOUNDIT SCRAPER - curl_cffi + ScraperAPI (1 credit per request)
# ---------------------------------------------------------------------------
def scrape_foundit(role, city):
    """Scrape Foundit using curl_cffi TLS fingerprint + ScraperAPI proxy.
    Uses only 1 credit per request (no premium, no render).
    curl_cffi impersonates Chrome's TLS fingerprint to bypass Cloudflare."""
    if not SCRAPERAPI_KEY:
        return []
    
    print("  - Scraping Foundit (curl_cffi + ScraperAPI - 1 credit)...")
    role_clean = role.replace(" ", "-").lower()
    city_clean = city.lower().split(",")[0].strip()
    url = f"https://www.foundit.in/search/{role_clean}-jobs-in-{city_clean}?jobFreshness=1"
    
    jobs = []
    try:
        from curl_cffi import requests as curl_requests
        
        proxy_url = f"http://scraperapi:{SCRAPERAPI_KEY}@proxy-server.scraperapi.com:8001"
        
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        
        resp = curl_requests.get(
            url, headers=headers, impersonate="chrome124",
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=60, verify=False
        )
        
        if resp.status_code == 200:
            html = resp.text
            
            # Parse Next.js RSC payload to extract job data
            push_payloads = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.DOTALL)
            all_rsc = ""
            for payload in push_payloads:
                unescaped = payload.replace('\\n', '\n').replace('\\t', '\t')
                unescaped = unescaped.replace('\\"', '"').replace('\\\\', '\\')
                all_rsc += unescaped + "\n"
            
            # Extract job objects from RSC data
            seen_ids = set()
            for match in re.finditer(r'"jobId"\s*:\s*(\d+)', all_rsc):
                job_id = match.group(1)
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                
                # Find enclosing JSON object
                pos = match.start()
                brace_count = 0
                start_pos = pos
                while start_pos > 0:
                    start_pos -= 1
                    if all_rsc[start_pos] == '}':
                        brace_count += 1
                    elif all_rsc[start_pos] == '{':
                        if brace_count == 0:
                            break
                        brace_count -= 1
                
                brace_count = 0
                end_pos = start_pos
                while end_pos < len(all_rsc):
                    if all_rsc[end_pos] == '{':
                        brace_count += 1
                    elif all_rsc[end_pos] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos += 1
                            break
                    end_pos += 1
                
                json_str = all_rsc[start_pos:end_pos]
                
                try:
                    job_obj = json.loads(json_str)
                    
                    title = job_obj.get("title", "")
                    company = ""
                    company_data = job_obj.get("company", {})
                    if isinstance(company_data, dict):
                        company = company_data.get("name", "")
                    if not company:
                        company = job_obj.get("recruiterName", "")
                    
                    # Location
                    loc_list = job_obj.get("locations", [])
                    loc_str = city
                    if isinstance(loc_list, list) and loc_list:
                        loc_names = []
                        for loc in loc_list:
                            if isinstance(loc, dict):
                                loc_names.append(loc.get("label", loc.get("name", "")))
                            elif isinstance(loc, str):
                                loc_names.append(loc)
                        if loc_names:
                            loc_str = ", ".join(loc_names)
                    
                    # URL
                    jd_url = job_obj.get("jdUrl", "")
                    full_url = f"https://www.foundit.in{jd_url}" if jd_url else ""
                    
                    # Posted date
                    date_posted = datetime.now().strftime("%Y-%m-%d")
                    updated_at = job_obj.get("updatedAt", 0)
                    if updated_at:
                        try:
                            date_posted = datetime.fromtimestamp(updated_at / 1000).strftime("%Y-%m-%d")
                        except:
                            pass
                    
                    if title and full_url:
                        jobs.append({
                            "title": title, "company": company, "location": loc_str,
                            "date_posted": date_posted, "url": full_url,
                            "source": "foundit", "role_search": role
                        })
                except json.JSONDecodeError:
                    pass
        else:
            print(f"    Foundit returned {resp.status_code}")
    except ImportError:
        print("    curl_cffi not installed! Run: pip install curl_cffi")
    except Exception as e:
        print(f"    Foundit error: {e}")
    
    return jobs

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  JOB PORTALS SCRAPER (NAUKRI & FOUNDIT)")
    print("  Naukri: Playwright headful + API interception (FREE)")
    print("  Foundit: curl_cffi + ScraperAPI proxy (1 credit each)")
    print("=" * 70)
    print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Roles Count: {len(SEARCH_ROLES)}")
    print(f"  Cities Count: {len(LOCATIONS)}")
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

    scraped_counts = {"naukri": 0, "foundit": 0}
    stored_counts = {"naukri": 0, "foundit": 0}

    for r_idx in range(start_role, len(SEARCH_ROLES)):
        role = SEARCH_ROLES[r_idx]
        curr_start_loc_idx = start_loc if r_idx == start_role else 0
        
        for l_idx in range(curr_start_loc_idx, len(LOCATIONS)):
            city = LOCATIONS[l_idx]
            combo_num += 1

            elapsed = time.time() - START_TIME
            if elapsed >= MAX_RUN_SECONDS:
                print(f"\nTime limit reached ({elapsed:.0f}s). Saving progress...")
                save_progress(r_idx, l_idx, finished_all=False)
                hit_time_limit = True
                break

            save_progress(r_idx, l_idx, finished_all=False)

            print(f"\n[{combo_num}/{total_combos}] '{role}' in '{city}'...")

            # -- 1. Naukri (FREE via Playwright) --
            naukri_jobs = scrape_naukri(role, city)
            n = len(naukri_jobs); ins = store_jobs_batch(naukri_jobs)
            scraped_counts["naukri"] += n; stored_counts["naukri"] += ins
            total_inserted += ins
            print(f"      Naukri        : {n:>4} scraped  |  {ins:>4} new stored")

            # -- 2. Foundit (1 credit via curl_cffi) --
            foundit_jobs = scrape_foundit(role, city)
            n = len(foundit_jobs); ins = store_jobs_batch(foundit_jobs)
            scraped_counts["foundit"] += n; stored_counts["foundit"] += ins
            total_inserted += ins
            print(f"      Foundit       : {n:>4} scraped  |  {ins:>4} new stored")

            # Delay between searches
            time.sleep(3)

        if hit_time_limit:
            break

    close_playwright()

    if not hit_time_limit:
        save_progress(0, 0, finished_all=True)
        print("\nScraper completed all roles. Progress reset.")

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
