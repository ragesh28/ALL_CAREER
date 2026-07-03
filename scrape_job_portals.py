import os
import sys
import re
import json
import time
import urllib.parse
import requests
from datetime import datetime, timedelta
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

# Progress Checkpointing Configuration
PROGRESS_FILE = "foundit_progress.json"
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
# FOUNDIT SCRAPER - Middleware API with ScraperAPI fallback
# ---------------------------------------------------------------------------
SCRAPERAPI_KEYS = [k.strip() for k in os.environ.get("SCRAPERAPI_KEYS_LIST", "").split(",") if k.strip()]
_scraper_key_idx = 0

def _get_scraperapi_key():
    global _scraper_key_idx
    if not SCRAPERAPI_KEYS:
        return None
    key = SCRAPERAPI_KEYS[_scraper_key_idx % len(SCRAPERAPI_KEYS)]
    _scraper_key_idx += 1
    return key

def _parse_foundit_items(items, city, role):
    """Parse Foundit middleware API items into job dicts."""
    jobs = []
    for item in items:
        title = item.get("title", "")
        # Company
        co = item.get("company", "")
        company = co.get("name", "") if isinstance(co, dict) else str(co)
        if not company:
            company = item.get("recruiterName", "")
        # Location
        loc_list = item.get("locations", [])
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
        jd_url = item.get("jdUrl", "")
        full_url = f"https://www.foundit.in{jd_url}" if jd_url else ""
        # Date
        date_posted = datetime.now().strftime("%Y-%m-%d")
        updated_at = item.get("updatedAt", 0)
        if updated_at:
            try:
                date_posted = datetime.fromtimestamp(updated_at / 1000).strftime("%Y-%m-%d")
            except:
                pass
        # Experience
        experience = item.get("exp", "")
        
        if title and full_url:
            jobs.append({
                "title": title, "company": company, "location": loc_str,
                "date_posted": date_posted, "url": full_url,
                "source": "foundit", "role_search": role,
                "experience": experience
            })
    return jobs

def _scrape_foundit_middleware(role, city):
    """Try middleware API: plain requests first, then curl_cffi fallback."""
    jobs = []
    keyword = urllib.parse.quote(role)
    city_clean = city.lower().split(",")[0].strip()
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.foundit.in/",
        "Origin": "https://www.foundit.in",
        "Sec-Ch-Ua": '"Chromium";v="126", "Google Chrome";v="126", "Not=A?Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }
    
    # Try plain requests first (works from many IPs including GitHub Actions)
    for page in range(1, 5):
        start = (page - 1) * 20 + 1
        url = f"https://www.foundit.in/middleware/jobsearch?keyword={keyword}&location={city_clean}&limit=20&sort=1&start={start}&jobFreshness=1"
        try:
            resp = requests.get(url, headers=headers, timeout=30, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("jobSearchResponse", {}).get("data", [])
                if not items:
                    break
                jobs.extend(_parse_foundit_items(items, city, role))
                print(f"    Page {page}: {url}")
            else:
                print(f"    Plain requests returned {resp.status_code} on page {page}")
                if page == 1:
                    # First page failed — try curl_cffi
                    break
                else:
                    break  # We got some jobs already
        except Exception as e:
            print(f"    Plain requests error: {e}")
            if page == 1:
                break
            else:
                break
        time.sleep(1)
    
    # If plain requests got nothing on page 1, try curl_cffi
    if not jobs and curl_requests:
        print("    Trying curl_cffi fallback...")
        for page in range(1, 5):
            start = (page - 1) * 20 + 1
            url = f"https://www.foundit.in/middleware/jobsearch?keyword={keyword}&location={city_clean}&limit=20&sort=1&start={start}&jobFreshness=1"
            try:
                resp = curl_requests.get(url, headers=headers, impersonate="chrome124",
                                         timeout=30, verify=False)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("jobSearchResponse", {}).get("data", [])
                    if not items:
                        break
                    jobs.extend(_parse_foundit_items(items, city, role))
                else:
                    print(f"    curl_cffi returned {resp.status_code}")
                    return None  # Signal to try ScraperAPI fallback
            except Exception as e:
                print(f"    curl_cffi error: {e}")
                return None
            time.sleep(1)
    
    if not jobs:
        return None  # Signal to try ScraperAPI fallback
    
    return jobs

def _scrape_foundit_scraperapi(role, city):
    """Fallback: use ScraperAPI proxy to hit the middleware API."""
    jobs = []
    api_key = _get_scraperapi_key()
    if not api_key:
        print("    No ScraperAPI keys available!")
        return []
    
    keyword = urllib.parse.quote(role)
    city_clean = city.lower().split(",")[0].strip()
    
    for page in range(1, 5):
        start = (page - 1) * 20 + 1
        target_url = f"https://www.foundit.in/middleware/jobsearch?keyword={keyword}&location={city_clean}&limit=20&sort=1&start={start}&jobFreshness=1"
        proxy_url = f"https://api.scraperapi.com?api_key={api_key}&url={urllib.parse.quote(target_url)}&render=false"
        try:
            resp = requests.get(proxy_url, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("jobSearchResponse", {}).get("data", [])
                if not items:
                    break
                jobs.extend(_parse_foundit_items(items, city, role))
            else:
                print(f"    ScraperAPI returned {resp.status_code}")
                break
        except Exception as e:
            print(f"    ScraperAPI error: {e}")
            break
        time.sleep(2)
    
    return jobs

def scrape_foundit(role, city):
    """Scrape Foundit: try middleware API first, fallback to ScraperAPI proxy."""
    # Try middleware first (free, fast)
    print("  - Scraping Foundit (middleware API - requests + curl_cffi + ScraperAPI)...")
    jobs = _scrape_foundit_middleware(role, city)
    
    if jobs is not None and len(jobs) > 0:
        print(f"    Middleware API worked! Got {len(jobs)} jobs")
        return jobs
    
    # Fallback to ScraperAPI
    if SCRAPERAPI_KEYS:
        print("    Middleware blocked/failed. Falling back to ScraperAPI proxy...")
        jobs = _scrape_foundit_scraperapi(role, city)
        if jobs:
            print(f"    ScraperAPI got {len(jobs)} jobs")
            return jobs
    
    print("    Both methods failed. No Foundit jobs scraped.")
    return []

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  JOB PORTALS SCRAPER (FOUNDIT ONLY)")
    print("  Foundit: Middleware API (NO PROXY - FREE!)")
    print("=" * 70)
    print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Roles Count: {len(SEARCH_ROLES)}")
    print(f"  Cities Count: {len(LOCATIONS)}")
    print("=" * 70)

    cleanup_old_jobs()

    progress = load_progress()
    start_role = progress.get("role_idx", 0)
    start_loc = progress.get("loc_idx", 0)

    total_inserted = 0
    total_combos = len(SEARCH_ROLES) * len(LOCATIONS)
    combo_num = start_role * len(LOCATIONS) + start_loc
    hit_time_limit = False

    scraped_counts = {"foundit": 0}
    stored_counts = {"foundit": 0}

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

            # -- 1. Foundit (1 credit via curl_cffi) --
            foundit_jobs = scrape_foundit(role, city)
            n = len(foundit_jobs); ins = store_jobs_batch(foundit_jobs)
            scraped_counts["foundit"] += n; stored_counts["foundit"] += ins
            total_inserted += ins
            print(f"      Foundit       : {n:>4} scraped  |  {ins:>4} new stored")

            # Delay between searches
            time.sleep(3)

        if hit_time_limit:
            break

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
