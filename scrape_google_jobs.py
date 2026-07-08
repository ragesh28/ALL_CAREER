"""
ALL JOBS Aggregator Scraper via JobSpy → Turso + JS file
Scrapes ALL portals (LinkedIn, Indeed, Google, Glassdoor, ZipRecruiter)
for jobs across ALL tech & non-tech roles.
Stores in Turso database AND generates all_jobs_data.js for GitHub Pages.

Priority: LinkedIn > Google > Indeed > Glassdoor > ZipRecruiter.

Usage (local):   py -3.11 scrape_google_jobs.py --test 3
Usage (GitHub):  python scrape_google_jobs.py
"""

import os
import sys
import json
import time
import requests
import traceback
import urllib.parse
from datetime import datetime, timedelta
import pandas as pd
import random

# Configure stdout to handle UTF-8 printing cleanly on Windows
sys.stdout.reconfigure(encoding='utf-8')

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
ACCOUNT_ID = "283008c384af43c0a9f25f7e501fdd53"
DATABASE_ID = "019ce14b-1801-72d6-b42c-8b3a645a1f15"
SCRAPERAPI_KEYS = []
if os.environ.get("SCRAPERAPI_KEY"):
    SCRAPERAPI_KEYS.append(os.environ.get("SCRAPERAPI_KEY"))
keys_list = os.environ.get("SCRAPERAPI_KEYS_LIST", "")
if keys_list:
    for k in keys_list.split(","):
        if k.strip() and k.strip() not in SCRAPERAPI_KEYS:
            SCRAPERAPI_KEYS.append(k.strip())

_scraper_key_idx = 0
def _get_scraperapi_key():
    global _scraper_key_idx
    if not SCRAPERAPI_KEYS:
        return None
    key = SCRAPERAPI_KEYS[_scraper_key_idx % len(SCRAPERAPI_KEYS)]
    _scraper_key_idx += 1
    return key

MAX_JOBS = 500000           # Per run cap
RESULTS_PER_SEARCH = 20    # Per role+location combo
KEEP_DAYS = 30              # Delete jobs older than 20 days
COOLDOWN_SECONDS = 60       # Wait on block
MAX_RETRIES = 3

START_TIME = time.time()
MAX_RUN_SECONDS = 5 * 3600 + 50 * 60  # 5h50m safe margin

# ---------------------------------------------------------------------------
# ROLES — All Tech + Non-Tech
# ---------------------------------------------------------------------------
SEARCH_ROLES = [
    # --- Software Development & Engineering ---
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Mobile App Developer",
    "Software Architect",
    "Software Engineer",

    # --- AI & Data Science ---
    "AI Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",

    # --- Cloud, Infrastructure & DevOps ---
    "DevOps Engineer",
    "Cloud Architect",
    "Systems Administrator",
    "Database Administrator",

    # --- Cybersecurity & Networking ---
    "Security Analyst",
    "Penetration Tester",
    "Network Engineer",

    # --- QA & Testing ---
    "QA Analyst",
    "SDET",

    # --- Product & Project Management ---
    "Product Manager",
    "Project Manager",
    "Scrum Master",

    # --- Design & UX ---
    "UI UX Designer",
    "UX Researcher",
    "Technical Writer",

    # --- Sales & Marketing ---
    "Sales Executive",
    "Pre-Sales Consultant",
    "Digital Marketer",
    "Product Marketing Manager",

    # --- HR & Talent ---
    "Technical Recruiter",
    "HR Business Partner",

    # --- Customer Success & Support ---
    "Customer Success Manager",
    "IT Support Specialist",

    # --- Operations & Finance ---
    "Operations Manager",
    "Financial Analyst",
    "Legal Counsel",
]

LOCATIONS = [
    "Bangalore, India",
    "Chennai, India",
    "Hyderabad, India",
    "Mumbai, India",
]


# ---------------------------------------------------------------------------
# CLOUDFLARE D1 HELPERS
# ---------------------------------------------------------------------------
def d1_execute(sql, params=None):
    pass

def setup_database():
    pass

import storage
def store_jobs_batch(jobs):
    return storage.store_jobs_batch(jobs)

def cleanup_old_jobs():
    pass

def get_total_jobs():
    return 0


# ---------------------------------------------------------------------------
# SCRAPE
# ---------------------------------------------------------------------------


def load_progress():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open("google_progress.json", "r") as f:
            data = json.load(f)
        # If progress is from a previous day, reset to start
        if data.get("date") != today:
            print(f"📅 New day detected (was {data.get('date')}, now {today}). Resetting progress to start.")
            return {"role_idx": 0, "loc_idx": 0, "date": today}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"role_idx": 0, "loc_idx": 0, "date": today}

def save_progress(role_idx, loc_idx, finished_all=False):
    # If finished_all, reset to 0 so next run starts fresh
    if finished_all:
        role_idx = 0
        loc_idx = 0

    with open("google_progress.json", "w") as f:
        json.dump({
            "role_idx": role_idx,
            "loc_idx": loc_idx,
            "date": datetime.now().strftime("%Y-%m-%d")
        }, f)

import re
from playwright.sync_api import sync_playwright

import requests

def scrape_all_jobs(test_limit=None):
    if not SCRAPERAPI_KEYS:
        print(f"⚠️  No ScraperAPI keys set \u2014 ScraperAPI structured endpoint requires a key.")
        return [], 0
    else:
        print(f"🌍 Using ScraperAPI structured Google Jobs endpoint with {len(SCRAPERAPI_KEYS)} keys")

    roles = SEARCH_ROLES
    if test_limit:
        roles = roles[:test_limit]
        print(f"\n🧪 TEST MODE: {test_limit} roles only\n")

    all_jobs = []
    seen_keys = set()
    fetched_at = datetime.now().strftime("%Y-%m-%d")
    total_combos = len(roles) * len(LOCATIONS)
    total_stored = 0
    
    progress = load_progress()
    start_role_idx = progress.get("role_idx", 0)
    start_loc_idx = progress.get("loc_idx", 0)
    print(f"🔄 Resuming from Role Index: {start_role_idx}/{len(roles)}, Location Index: {start_loc_idx}/{len(LOCATIONS)}")
    
    combo_num = start_role_idx * len(LOCATIONS) + start_loc_idx
    hit_time_limit = False

    for r_idx in range(start_role_idx, len(roles)):
        role = roles[r_idx]
        curr_start_loc_idx = start_loc_idx if r_idx == start_role_idx else 0
        
        for l_idx in range(curr_start_loc_idx, len(LOCATIONS)):
            location = LOCATIONS[l_idx]
            combo_num += 1

            if time.time() - START_TIME >= MAX_RUN_SECONDS:
                print(f"\n⏰ TIME LIMIT REACHED. Saving state and stopping.")
                save_progress(r_idx, l_idx)
                hit_time_limit = True
                break
                
            print(f"[{combo_num}/{total_combos}] 🔍 '{role}' in {location.split(',')[0]}...", end=" ", flush=True)

            query = f"{role} in {location}"

            max_retries = 3
            success = False
            batch = []
            
            for attempt in range(max_retries):
                current_api_key = _get_scraperapi_key()
                if not current_api_key:
                    print("⚠️ No ScraperAPI keys available.")
                    break
                    
                payload = {
                    'api_key': current_api_key,
                    'query': query,
                    'gl': 'in',
                    'hl': 'en'
                }

                try:
                    r = requests.get('http://api.scraperapi.com/structured/google/jobs', params=payload, timeout=60)
                    if r.status_code == 200:
                        data = r.json()
                        results = data.get("jobs_results", [])
                        
                        count = 0
                        for job in results:
                            if count >= RESULTS_PER_SEARCH:
                                break
                                
                            title = job.get("title", "")
                            company = job.get("company_name", "")
                            loc_clean = job.get("location", "")
                            via = job.get("via", "")
                            
                            site = "google"
                            if via:
                                site = via.lower().replace("via ", "").strip()
                                
                            if not title or not company:
                                continue
                                
                            key = f"{title.lower().strip()}|{company.lower().strip()}"
                            if key in seen_keys:
                                continue
                            seen_keys.add(key)
                            
                            direct_url = job.get("related_links", [{}])[0].get("link", "") if job.get("related_links") else ""
                            if not direct_url:
                                direct_url = job.get("share_link", "#")
                                
                            batch.append({
                                "title": title,
                                "company": company,
                                "location": loc_clean,
                                "url": direct_url or "#",
                                "linkedin_url": "",
                                "date": "Recent",
                                "source": site,
                                "role_search": role,
                                "fetchedAt": fetched_at,
                            })
                            count += 1
                        
                        success = True
                        break
                    else:
                        if attempt < max_retries - 1:
                            print(f"🔄 Error {r.status_code}, retrying ({attempt+2}/{max_retries})...", end=" ", flush=True)
                        else:
                            print(f"🚫 Failed after {max_retries} retries: HTTP {r.status_code}")
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"🔄 Error, retrying ({attempt+2}/{max_retries})...", end=" ", flush=True)
                    else:
                        print(f"🚫 Error after {max_retries} retries: {e}")
            
            if not success:
                continue

            all_jobs.extend(batch)

            if batch:
                inserted = store_jobs_batch(batch)
                total_stored += inserted

            print(f"✅ {len(batch)} new (total: {len(all_jobs)}, stored: {total_stored})")

            if not hit_time_limit:
                next_loc_idx = l_idx + 1
                next_role_idx = r_idx
                if next_loc_idx >= len(LOCATIONS):
                    next_loc_idx = 0
                    next_role_idx += 1
                    
                if next_role_idx >= len(roles):
                    save_progress(0, 0, finished_all=True)
                else:
                    save_progress(next_role_idx, next_loc_idx)
                    
            if len(all_jobs) >= MAX_JOBS or hit_time_limit:
                break
                
        if len(all_jobs) >= MAX_JOBS or hit_time_limit:
            break

    return all_jobs, total_stored

# ---------------------------------------------------------------------------
# JS FILE GENERATION
# ---------------------------------------------------------------------------
def generate_js_file(jobs):
    """Generate all_jobs_data.js from jobs list."""
    js = f"const allJobsData = {json.dumps(jobs, indent=2, ensure_ascii=False)};"
    with open("all_jobs_data.js", "w", encoding="utf-8") as f:
        f.write(js)
    print(f"✅ all_jobs_data.js ({len(jobs)} jobs)")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  ALL JOBS AGGREGATOR (All Portals → Cloudflare D1)")
    print("=" * 60)
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  🔍 Roles: {len(SEARCH_ROLES)}")
    print(f"  📍 Locations: {len(LOCATIONS)}")
    print(f"  📊 {RESULTS_PER_SEARCH}/combo, max {MAX_JOBS}")
    print(f"  🌐 Sources: Google Jobs Aggregator")
    print(f"  📦 D1 Database: {'✅ configured' if CLOUDFLARE_API_TOKEN else '❌ not configured (local only)'}")
    print(f"  📆 Retention: {KEEP_DAYS} days")
    print("=" * 60)

    test_count = None
    if "--test" in sys.argv:
        try:
            idx = sys.argv.index("--test")
            test_count = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            test_count = 3

    try:
        # Setup DB
        if CLOUDFLARE_API_TOKEN:
            setup_database()
            cleanup_old_jobs()
            print(f"📊 Current jobs in D1: {get_total_jobs()}")

        # Scrape
        jobs, stored = scrape_all_jobs(test_limit=test_count)
        print(f"\\n📊 Scraped: {len(jobs)} unique jobs, Stored: {stored} new in Cloudflare D1")

        final = get_total_jobs() if CLOUDFLARE_API_TOKEN else len(jobs)
        print(f"\n{'=' * 60}")
        print(f"  📊 RESULTS:")
        print(f"     🆕 New jobs scraped: {len(jobs)}")
        print(f"     💾 Stored in D1: {stored}")
        print(f"     📦 Total in DB: {final}")
        print(f"{'=' * 60}")
        print(f"\n✅ DONE!")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
