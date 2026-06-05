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
                    print(f"✅ Selected ScraperAPI Key starting with '{key[:4]}' ({remaining} credits remaining this month)")
                    return key
        except Exception as e:
            print(f"⚠️ Error checking key {key[:4]}...: {e}")
            continue
    print("❌ No ScraperAPI keys have enough credits left!")
    return None

SCRAPERAPI_KEY = get_active_scraperapi_key()

# Global Playwright Browser Instances
playwright_instance = None
browser_instance = None

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
# PORTAL SCRAPERS (PREMIUM ONLY)
# ---------------------------------------------------------------------------

def scrape_naukri(role, city):
    global browser_instance
    if not browser_instance or not SCRAPERAPI_KEY:
        return []
    print("  - Scraping Naukri (via ScraperAPI Premium Proxy)...")
    role_clean = role.replace(" ", "-").lower()
    city_clean = city.lower().split(",")[0].strip()
    # Adding ?jobAge=1 to only get 1-day old jobs
    url = f"https://www.naukri.com/{role_clean}-jobs-in-{city_clean}?jobAge=1"

    jobs = []
    try:
        # Configure ScraperAPI Proxy for Playwright
        proxy_config = {
            "server": "http://proxy-server.scraperapi.com:8001",
            "username": "scraperapi.premium=true",
            "password": SCRAPERAPI_KEY
        }
        
        context = browser_instance.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            proxy=proxy_config,
            ignore_https_errors=True
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)

        # Scroll down to trigger lazy-loaded job cards
        page.evaluate("window.scrollBy(0, 800)")
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollBy(0, 800)")
        page.wait_for_timeout(2000)

        content = page.content()
        soup = BeautifulSoup(content, "html.parser")

        card_selector = ".srp-jobtuple-wrapper, .cust-job-tuple, article.jobTuple, [class*='jobTuple'], .job-tuple-container"
        job_cards = soup.select(card_selector)

        for card in job_cards:
            title_el = card.select_one("a.title") or card.select_one("a[class*='title']")
            company_el = card.select_one("a.comp-name") or card.select_one("a[class*='comp']")
            location_el = card.select_one("span.locWdth") or card.select_one("[class*='loc']")
            post_el = card.select_one("span.job-post-day") or card.select_one("[class*='posted']")

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

def scrape_foundit(role, city):
    global browser_instance
    if not browser_instance or not SCRAPERAPI_KEY:
        return []
    print("  - Scraping Foundit (via ScraperAPI Premium Proxy)...")
    role_enc = urllib.parse.quote(role)
    city_enc = urllib.parse.quote(city)
    url = f"https://www.foundit.in/srp/results?query={role_enc}&locations={city_enc}&searchId=123"

    jobs = []
    try:
        # Configure ScraperAPI Proxy for Playwright
        proxy_config = {
            "server": "http://proxy-server.scraperapi.com:8001",
            "username": "scraperapi.premium=true",
            "password": SCRAPERAPI_KEY
        }
        
        context = browser_instance.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            proxy=proxy_config,
            ignore_https_errors=True
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        
        content = page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        cards = soup.select(".card-apply-content, .job-tuple")
        for card in cards:
            title_el = card.select_one(".jobTitle") or card.select_one("h3 a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            job_url = title_el.get("href", "")
            if job_url and job_url.startswith("/"):
                job_url = "https://www.foundit.in" + job_url
            
            comp_el = card.select_one(".companyName a") or card.select_one(".companyName")
            company = comp_el.get_text(strip=True) if comp_el else ""
            
            loc_el = card.select_one(".details .loc") or card.select_one("[class*='loc']")
            loc = loc_el.get_text(strip=True) if loc_el else city
            
            # Foundit sometimes hides date or puts it as "Updated: X days ago"
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            if title and job_url:
                jobs.append({
                    "title": title, "company": company, "location": loc,
                    "date_posted": date_str, "url": job_url,
                    "source": "foundit", "role_search": role
                })
        context.close()
    except Exception as e:
        print(f"    Foundit Playwright error: {e}")
    return jobs

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  PREMIUM JOB PORTALS SCRAPER (NAUKRI & FOUNDIT)")
    print("=" * 70)
    print(f"  📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🔍 Roles Count: {len(SEARCH_ROLES)}")
    print(f"  📍 Cities Count: {len(LOCATIONS)}")
    print("=" * 70)

    if not SCRAPERAPI_KEY:
        print("❌ CRITICAL ERROR: Could not find any valid ScraperAPI keys with credits remaining.")
        print("Please check your SCRAPERAPI_KEYS_LIST variable.")
        sys.exit(1)

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
                print(f"\n⏰ Time limit reached ({elapsed:.0f}s). Saving progress...")
                save_progress(r_idx, l_idx, finished_all=False)
                hit_time_limit = True
                break

            save_progress(r_idx, l_idx, finished_all=False)

            print(f"\n[{combo_num}/{total_combos}] '{role}' in '{city}'...")

            # ── 1. Naukri ──
            naukri_jobs = scrape_naukri(role, city)
            n = len(naukri_jobs); ins = store_jobs_batch(naukri_jobs)
            scraped_counts["naukri"] += n; stored_counts["naukri"] += ins
            total_inserted += ins
            print(f"      Naukri        : {n:>4} scraped  |  {ins:>4} new stored")

            # ── 2. Foundit ──
            foundit_jobs = scrape_foundit(role, city)
            n = len(foundit_jobs); ins = store_jobs_batch(foundit_jobs)
            scraped_counts["foundit"] += n; stored_counts["foundit"] += ins
            total_inserted += ins
            print(f"      Foundit       : {n:>4} scraped  |  {ins:>4} new stored")

            # Delay to avoid overloading the proxy immediately
            time.sleep(3)

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
