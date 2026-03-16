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
from jobspy import scrape_jobs
import pandas as pd
import random

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TURSO_URL = os.environ.get("TURSO_ALLJOBS_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_ALLJOBS_TOKEN", "")

MAX_JOBS = 500000           # Per run cap
RESULTS_PER_SEARCH = 20    # Per role+location combo
KEEP_DAYS = 10              # Delete jobs older than 10 days
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
# TURSO HELPERS
# ---------------------------------------------------------------------------
def turso_execute(statements):
    """Execute SQL statements via Turso HTTP API."""
    if not TURSO_URL or not TURSO_TOKEN:
        print("⚠️ TURSO not configured, skipping DB storage")
        return None

    url = f"{TURSO_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json",
    }

    requests_body = []
    for stmt in statements:
        if isinstance(stmt, str):
            requests_body.append({"type": "execute", "stmt": {"sql": stmt}})
        elif isinstance(stmt, dict):
            requests_body.append({"type": "execute", "stmt": stmt})
    requests_body.append({"type": "close"})

    try:
        resp = requests.post(url, headers=headers, json={"requests": requests_body}, timeout=30)
        if resp.status_code != 200:
            print(f"❌ Turso API error {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()
    except Exception as e:
        print(f"❌ Turso connection error: {e}")
        return None


def setup_database():
    """Create all_jobs table if not exists."""
    print("📦 Setting up Turso database (all_jobs table)...")
    sql = """
    CREATE TABLE IF NOT EXISTS all_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT,
        date_posted TEXT,
        url TEXT NOT NULL,
        linkedin_url TEXT,
        source TEXT,
        role_search TEXT,
        fetched_at TEXT NOT NULL,
        UNIQUE(url)
    )
    """
    result = turso_execute([sql])
    if result:
        print("✅ Database ready!")
    return result is not None


def store_jobs_batch(jobs):
    """Store a batch of jobs in Turso. Returns count inserted."""
    if not jobs or not TURSO_URL:
        return 0

    # Send in chunks of 50 to avoid payload limits
    total_inserted = 0
    for i in range(0, len(jobs), 50):
        chunk = jobs[i:i + 50]
        statements = []
        for job in chunk:
            stmt = {
                "sql": """INSERT OR IGNORE INTO all_jobs
                          (title, company, location, date_posted, url, linkedin_url, source, role_search, fetched_at)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                "args": [
                    {"type": "text", "value": str(job.get("title", ""))},
                    {"type": "text", "value": str(job.get("company", ""))},
                    {"type": "text", "value": str(job.get("location", ""))},
                    {"type": "text", "value": str(job.get("date", ""))},
                    {"type": "text", "value": str(job.get("url", ""))},
                    {"type": "text", "value": str(job.get("linkedin_url", ""))},
                    {"type": "text", "value": str(job.get("source", ""))},
                    {"type": "text", "value": str(job.get("role_search", ""))},
                    {"type": "text", "value": str(job.get("fetchedAt", ""))},
                ],
            }
            statements.append(stmt)

        result = turso_execute(statements)
        if result:
            for r in result.get("results", []):
                if r.get("type") == "ok":
                    total_inserted += r.get("response", {}).get("result", {}).get("affected_row_count", 0)

    return total_inserted


def cleanup_old_jobs():
    """Delete jobs older than KEEP_DAYS days."""
    if not TURSO_URL:
        return 0
    cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    print(f"🧹 Cleaning jobs older than {cutoff}...")
    result = turso_execute([{
        "sql": "DELETE FROM all_jobs WHERE fetched_at < ?",
        "args": [{"type": "text", "value": cutoff}]
    }])
    if result:
        for r in result.get("results", []):
            if r.get("type") == "ok":
                deleted = r.get("response", {}).get("result", {}).get("affected_row_count", 0)
                print(f"🗑️ Removed {deleted} old jobs")
                return deleted
    return 0


def fetch_all_from_turso():
    """Fetch all jobs from Turso for JS file generation."""
    if not TURSO_URL:
        return []

    result = turso_execute(["SELECT title, company, location, date_posted, url, linkedin_url, source, role_search, fetched_at FROM all_jobs ORDER BY fetched_at DESC"])
    if not result:
        return []

    jobs = []
    for r in result.get("results", []):
        if r.get("type") == "ok":
            cols = [c.get("name", "") for c in r.get("response", {}).get("result", {}).get("cols", [])]
            for row in r.get("response", {}).get("result", {}).get("rows", []):
                job = {}
                for ci, col_name in enumerate(cols):
                    val = row[ci].get("value", "") if ci < len(row) else ""
                    job[col_name] = val
                # Map to JS-compatible keys
                jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", ""),
                    "date": job.get("date_posted", ""),
                    "url": job.get("url", ""),
                    "linkedin_url": job.get("linkedin_url", ""),
                    "source": job.get("source", ""),
                    "role_search": job.get("role_search", ""),
                    "fetchedAt": job.get("fetched_at", ""),
                })
    return jobs


def get_total_jobs():
    """Get total job count from Turso."""
    if not TURSO_URL:
        return 0
    result = turso_execute(["SELECT COUNT(*) FROM all_jobs"])
    if result:
        for r in result.get("results", []):
            if r.get("type") == "ok":
                rows = r.get("response", {}).get("result", {}).get("rows", [])
                if rows:
                    return int(rows[0][0].get("value", 0))
    return 0


# ---------------------------------------------------------------------------
# SCRAPE
# ---------------------------------------------------------------------------


def load_progress():
    try:
        with open("google_progress.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"role_idx": 0, "loc_idx": 0, "date": datetime.now().strftime("%Y-%m-%d")}

def save_progress(role_idx, loc_idx, finished_all=False):
    # If finished_all is True, we erase the file, next run starts fresh
    if finished_all:
        try:
            os.remove("google_progress.json")
        except FileNotFoundError:
            pass
        return

    with open("google_progress.json", "w") as f:
        json.dump({
            "role_idx": role_idx,
            "loc_idx": loc_idx,
            "date": datetime.now().strftime("%Y-%m-%d")
        }, f)

def scrape_all_jobs(test_limit=None):
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

            try:
                jobs_df = scrape_jobs(
                    site_name=["linkedin", "indeed", "glassdoor", "zip_recruiter", "google"],
                    search_term=role,
                    location=location,
                    results_wanted=RESULTS_PER_SEARCH,
                    country_indeed='India',
                    hours_old=72,
                    linkedin_fetch_description=False,
                    verbose=0,
                )
                
                if jobs_df is not None and not jobs_df.empty:
                    jobs_df = jobs_df.fillna("")
                    batch = []
                    
                    for _, row in jobs_df.iterrows():
                        title = str(row.get('title', '')).strip()
                        company = str(row.get('company', '')).strip()
                        loc = str(row.get('location', '')).strip()
                        job_url = str(row.get('job_url', '')).strip()
                        site = str(row.get('site', 'unknown')).strip()
                        date_str = str(row.get('date_posted', 'Recent')).strip()

                        if not title or not company:
                            continue
                            
                        # Unique keys
                        key = f"{title.lower()}|{company.lower()}"
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        
                        batch.append({
                            "title": title,
                            "company": company,
                            "location": loc,
                            "url": job_url if job_url != "nan" else "#",
                            "linkedin_url": "",
                            "date": date_str if date_str and date_str != "nan" else "Recent",
                            "source": site.lower() if site != "nan" else "unknown",
                            "role_search": role,
                            "fetchedAt": fetched_at,
                        })
                        
                    all_jobs.extend(batch)
                    if batch and TURSO_URL:
                        inserted = store_jobs_batch(batch)
                        total_stored += inserted
                    print(f"✅ {len(batch)} new (total: {len(all_jobs)}, stored: {total_stored})")
                else:
                    print("0 jobs found")

            except Exception as e:
                print(f"🚫 Error: {e}")

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
    print("  ALL JOBS AGGREGATOR (All Portals → Turso)")
    print("=" * 60)
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  🔍 Roles: {len(SEARCH_ROLES)}")
    print(f"  📍 Locations: {len(LOCATIONS)}")
    print(f"  📊 {RESULTS_PER_SEARCH}/combo, max {MAX_JOBS}")
    print(f"  🌐 Sources: LinkedIn, Indeed, Google, Glassdoor, ZipRecruiter")
    print(f"  📦 Turso: {'✅ configured' if TURSO_URL else '❌ not configured (local only)'}")
    print(f"  📆 Retention: {KEEP_DAYS} days")
    print("=" * 60)

    # Local testing fallback
    if not TURSO_URL:
        TURSO_URL = "https://alljobs-ragesh.aws-ap-south-1.turso.io"
    if not TURSO_TOKEN:
        TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzM1NTM5OTksImlkIjoiMDE5Y2UxNGItMTgwMS03MmQ2LWI0MmMtOGIzYTY0NWExZjE1IiwicmlkIjoiMjgzMDA4YzMtODRhZi00M2MwLWE5ZjItNWY3ZTUwMWZkZDUzIn0.mtjC1aL0M1rcwS2pJsM70Ytqk06Jqct2dVChPGcgEV0zvcv8hAb9opCC5L76xuEXnO6ZuUZU-Edlex7ABWgVCg"

    test_count = None
    if "--test" in sys.argv:
        try:
            idx = sys.argv.index("--test")
            test_count = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            test_count = 3

    try:
        # Setup DB
        if TURSO_URL:
            setup_database()
            cleanup_old_jobs()
            print(f"📊 Current jobs in Turso: {get_total_jobs()}")

        # Scrape
        jobs, stored = scrape_all_jobs(test_limit=test_count)
        print(f"\\n📊 Scraped: {len(jobs)} unique jobs, Stored: {stored} new in Turso")

        # Removed JS file generation to prevent saving to Github repository storage.
        # Data is exclusively stored in Turso now.


        final = get_total_jobs() if TURSO_URL else len(jobs)
        print(f"\n{'=' * 60}")
        print(f"  📊 RESULTS:")
        print(f"     🆕 New jobs scraped: {len(jobs)}")
        print(f"     💾 Stored in Turso: {stored}")
        print(f"     📦 Total in DB: {final}")
        print(f"{'=' * 60}")
        print(f"\n✅ DONE!")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
