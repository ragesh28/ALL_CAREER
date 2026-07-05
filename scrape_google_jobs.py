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

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
ACCOUNT_ID = "283008c384af43c0a9f25f7e501fdd53"
DATABASE_ID = "019ce14b-1801-72d6-b42c-8b3a645a1f15"
SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

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

def scrape_all_jobs(test_limit=None):
    # Build ScraperAPI proxy config (single endpoint, ScraperAPI handles rotation)
    proxy_config = None
    if SCRAPERAPI_KEY:
        proxy_config = {
            "server": "http://proxy-server.scraperapi.com:8001",
            "username": "scraperapi",
            "password": SCRAPERAPI_KEY,
        }
        print(f"🌍 ScraperAPI proxy configured (proxy-server.scraperapi.com:8001)")
    else:
        print(f"⚠️  No SCRAPERAPI_KEY set — running without proxy (Google may block)")

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

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
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

                # --- RETRY ---
                max_retries = 3 if proxy_config else 1
                success = False
                
                for attempt in range(max_retries):

                    try:
                        context = browser.new_context(
                            proxy=proxy_config,
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                            viewport={'width': 1920, 'height': 1080}
                        )
                        def abort_resources(route):
                            if route.request.resource_type in ["image", "stylesheet", "font", "media"]:
                                route.abort()
                            else:
                                route.continue_()

                        page = context.new_page()
                        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                        page.route("**/*", abort_resources)

                        encoded_query = urllib.parse.quote_plus(f"{role} jobs in {location}")
                        job_url = f"https://www.google.com/search?q={encoded_query}&ibp=htl;jobs#htivrt=jobs&htichips=date_posted:today&fpstate=tldetail"

                        try:
                            page.goto(job_url, wait_until="commit", timeout=30000)
                        except Exception:
                            pass  # Will try to parse DOM anyway
                            
                        page.wait_for_timeout(5000)
                        
                        try:
                            page.wait_for_selector('a.MQUd2b', timeout=15000)
                            success = True
                        except Exception:
                            title_lower = page.title().lower()
                            context.close()
                            if "sorry" in title_lower or "captcha" in title_lower or "robot" in title_lower:
                                if attempt < max_retries - 1:
                                    print(f"🔄 Proxy blocked, retrying ({attempt+2}/{max_retries})...", end=" ", flush=True)
                                    continue
                                else:
                                    print("🚫 All proxies blocked by Google CAPTCHA")
                            else:
                                if attempt < max_retries - 1:
                                    print(f"🔄 Retry ({attempt+2}/{max_retries})...", end=" ", flush=True)
                                    continue
                                else:
                                    print("0 jobs found (all retries failed)")
                            break
                    except Exception as e:
                        try:
                            context.close()
                        except Exception:
                            pass
                        if attempt < max_retries - 1:
                            print(f"🔄 Error, retrying ({attempt+2}/{max_retries})...", end=" ", flush=True)
                            continue
                        else:
                            print(f"🚫 Error after {max_retries} retries: {e}")
                        break
                    
                    # If we got here, success=True, break out of retry loop
                    break
                
                if not success:
                    continue

                # --- Scrape job cards (we have a working page + context) ---
                try:
                    page.mouse.move(300, 500)
                    for _ in range(3):
                        page.mouse.wheel(0, 1500)
                        page.wait_for_timeout(1000)
                        
                    list_items = page.locator('a.MQUd2b').all()
                    
                    batch = []
                    count = 0
                    
                    for card in list_items:
                        if count >= RESULTS_PER_SEARCH:
                            break
                            
                        try:
                            title_loc = card.locator('.tNxQIb')
                            title = title_loc.inner_text().strip() if title_loc.count() > 0 else ""
                            
                            comp_locs = card.locator('.wHYlTd').all()
                            company = comp_locs[0].inner_text().strip() if len(comp_locs) > 0 else ""
                            
                            loc_via = comp_locs[1].inner_text().strip() if len(comp_locs) > 1 else ""
                            loc_clean = loc_via.split('•')[0].strip() if '•' in loc_via else loc_via
                            site = "google"
                            if 'via' in loc_via:
                                site = loc_via.split('via')[-1].strip().lower()
                                
                            if not title or not company:
                                continue
                                
                            key = f"{title.lower().strip()}|{company.lower().strip()}"
                            if key in seen_keys:
                                continue
                            seen_keys.add(key)
                            
                            card.click(force=True)
                            page.wait_for_timeout(1000)
                            
                            direct_url = ""
                            apply_links = page.locator('.yVRmze-s2gQvd a').all()
                            if apply_links:
                                direct_url = apply_links[0].get_attribute('href')
                            if not direct_url:
                                direct_url = card.get_attribute('href')
                                
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
                            
                        except Exception:
                            continue
                            
                    all_jobs.extend(batch)

                    if batch:
                        inserted = store_jobs_batch(batch)
                        total_stored += inserted

                    print(f"✅ {len(batch)} new (total: {len(all_jobs)}, stored: {total_stored})")
                    context.close()

                except Exception as e:
                    print(f"🚫 Scrape error: {e}")
                    try:
                        context.close()
                    except Exception:
                        pass

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
