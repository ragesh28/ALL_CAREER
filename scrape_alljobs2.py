"""
ALL JOBS 2 — LinkedIn + Indeed Scraper (JobSpy → Turso)
GitHub Actions workflow scraper for LinkedIn and Indeed.

Features:
- Uses JobSpy to scrape LinkedIn + Indeed
- Extracts Indeed "jk" parameter for PERMANENT links
- Progress saving to alljobs2_progress.json (resumes after timeout/block)
- 5h50m time limit, auto-restart from saved position
- Only scrapes last 24 hours jobs
- Retries all roles if finished within the time window
- Stores in Turso all_jobs table

What is "jk"?
  Indeed assigns each job a unique 16-char hex ID called "jk".
  Normal scraped URLs expire after days.
  https://www.indeed.com/viewjob?jk=<ID>&from=serp&vjs=3 is PERMANENT.

Usage (GitHub Actions): python scrape_alljobs2.py
Usage (local test):     python scrape_alljobs2.py --test 3
"""

import os
import sys
import re
import json
import time
import requests
import traceback
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CLOUDFLARE_URL = os.environ.get("CLOUDFLARE_D1_URL", "https://api.cloudflare.com/client/v4/accounts/62eacb67a7ee0b199f58ccb540a3eff7/d1/database/20b71b5c-c070-45b5-9542-27ed1cad89e5/query")
CLOUDFLARE_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")

RESULTS_PER_SEARCH = 20
KEEP_DAYS = 30
PROGRESS_FILE = "alljobs2_progress.json"

START_TIME = time.time()
MAX_RUN_SECONDS = 5 * 3600 + 40 * 60  # 5h40m (leaves buffer before 355m GitHub Action limit)

# Parse --test
TEST_MODE = "--test" in sys.argv
TEST_LIMIT = 3
if TEST_MODE:
    try:
        TEST_LIMIT = int(sys.argv[sys.argv.index("--test") + 1])
    except (IndexError, ValueError):
        TEST_LIMIT = 3
    RESULTS_PER_SEARCH = TEST_LIMIT

# ---------------------------------------------------------------------------
# ROLES & LOCATIONS
# ---------------------------------------------------------------------------
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
    "Bangalore, India",
    "Chennai, India",
    "Hyderabad, India",
    "Mumbai, India",
]


# ---------------------------------------------------------------------------
# PROGRESS SAVE/LOAD
# ---------------------------------------------------------------------------
def load_progress():
    try:
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
        # Auto-reset if from a different day
        saved_date = data.get("date", "")
        today = datetime.now().strftime("%Y-%m-%d")
        if saved_date != today:
            print(f"📅 New day ({today}), resetting progress from {saved_date}")
            return {"role_idx": 0, "loc_idx": 0, "date": today}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"role_idx": 0, "loc_idx": 0, "date": datetime.now().strftime("%Y-%m-%d")}


def save_progress(role_idx, loc_idx, finished_all=False):
    today = datetime.now().strftime("%Y-%m-%d")
    if finished_all:
        # Reset to 0 for next run (retry today's jobs)
        data = {"role_idx": 0, "loc_idx": 0, "date": today, "finished": True}
    else:
        data = {"role_idx": role_idx, "loc_idx": loc_idx, "date": today, "finished": False}
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# TURSO HELPERS
# ---------------------------------------------------------------------------
def d1_execute(sql, params=None):
    if not CLOUDFLARE_URL or not CLOUDFLARE_TOKEN:
        print("❌ Cloudflare D1 not configured!")
        return None
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_TOKEN}",
        "Content-Type": "application/json",
    }
    body = {"sql": sql}
    if params:
        body["params"] = params
        
    try:
        resp = requests.post(CLOUDFLARE_URL, headers=headers, json=body, timeout=30)
        if resp.status_code != 200:
            print(f"❌ D1 error {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()
    except Exception as e:
        print(f"❌ D1 connection error: {e}")
        return None


def setup_database():
    print("📦 Setting up D1 database (all_jobs table)...")
    d1_execute("""
        CREATE TABLE IF NOT EXISTS all_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT, location TEXT, 
            role TEXT, job_posted_date TEXT, 
            apply_link TEXT, platform TEXT, search_keyword TEXT, UNIQUE(apply_link)
        )
    """)
    print("✅ Database ready!")


def store_jobs_batch(jobs):
    if not jobs:
        return 0

    # 1. Fetch existing jobs natively from Cloudflare worker for strictly pure python deduplication
    existing_urls = set()
    try:
        import requests
        print("  [Deduplication] Fetching existing records from Cloudflare D1 API...")
        resp = requests.get("https://all-career-api.ragesh-jobs.workers.dev/api/all_jobs", timeout=20)
        if resp.status_code == 200:
            existing_jobs = resp.json()
            existing_urls = {str(j.get("url", "")) for j in existing_jobs if j.get("url")}
    except Exception as e:
        print(f"  [WARN] Failed to quickly fetch D1 existing jobs: {e}")

    # 2. Deduplicate strictly in Python memory (ignoring D1 matches and internal duplicates)
    new_jobs = []
    seen_local_urls = set()
    for job in jobs:
        u = str(job.get("url", ""))
        # Ignore if it exists already in Cloudflare, OR if we already saw it in this exact batch repeatedly!
        if u and u not in existing_urls and u not in seen_local_urls:
            new_jobs.append(job)
            seen_local_urls.add(u)
            
    skipped = len(jobs) - len(new_jobs)
    if skipped > 0:
        print(f"  [Deduplication] Skipped {skipped} duplicate job URLs (either already in D1 or duplicate across cities).")

    if not new_jobs:
        return 0

    total_inserted = 0
    from datetime import datetime
    for i in range(0, len(new_jobs), 14):
        chunk = new_jobs[i:i + 14]
        params = []
        placeholders = []
        for job in chunk:
            placeholders.append("(?, ?, ?, ?, ?, ?, ?)")
            params.extend([
                str(job.get("company", "")),
                str(job.get("location", "")),
                str(job.get("title", "")),       # Map title to role
                str(job.get("date_posted", datetime.now().strftime("%Y-%m-%d"))),
                str(job.get("url", "")),
                str(job.get("source", "")),      # Map source to platform
                str(job.get("role_search", ""))  
            ])
            
        sql = f"INSERT OR IGNORE INTO all_jobs (company_name, location, role, job_posted_date, apply_link, platform, search_keyword) VALUES {','.join(placeholders)}"
        result = d1_execute(sql, params)
        if result and result.get("success"):
            for res in result.get("result", []):
                total_inserted += res.get("meta", {}).get("changes", 0)
    return total_inserted


def cleanup_old_jobs():
    cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    print(f"🧹 Cleaning jobs older than {cutoff}...")
    result = d1_execute("DELETE FROM all_jobs WHERE job_posted_date < ?", [cutoff])
    if result and result.get("success"):
        for res in result.get("result", []):
            deleted = res.get("meta", {}).get("changes", 0)
            print(f"🗑️ Removed {deleted} old jobs")


def get_total_jobs():
    result = d1_execute("SELECT COUNT(*) as c FROM all_jobs")
    if result and result.get("success"):
        for res in result.get("result", []):
            rows = res.get("results", [])
            if rows:
                return int(rows[0].get("c", 0))
    return 0


# ---------------------------------------------------------------------------
# INDEED PERMANENT LINK
# ---------------------------------------------------------------------------
def extract_indeed_jk(url):
    """
    Indeed assigns each job a unique 16-hex-character ID called "jk".
    Normal scraped URLs expire after days.
    https://www.indeed.com/viewjob?jk=<ID>&from=serp&vjs=3 is PERMANENT.
    """
    if not url:
        return None, url
    match = re.search(r'jk=([a-f0-9]{16})', str(url))
    if match:
        jk = match.group(1)
        return jk, f"https://www.indeed.com/viewjob?jk={jk}&from=serp&vjs=3"
    return None, url


# ---------------------------------------------------------------------------
# MAIN SCRAPER
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  ALL JOBS 2 — LinkedIn + Indeed (JobSpy → Cloudflare D1)")
    print("=" * 60)
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  🔍 Roles: {len(SEARCH_ROLES)}")
    print(f"  📍 Locations: {len(LOCATIONS)}")
    print(f"  📊 {RESULTS_PER_SEARCH}/combo")
    print(f"  🌐 Sources: LinkedIn, Indeed")
    print(f"  📦 D1 Database: {'✅' if CLOUDFLARE_TOKEN else '❌'}")
    if TEST_MODE:
        print(f"  🧪 TEST MODE: {TEST_LIMIT} results")
    print("=" * 60)

    setup_database()
    cleanup_old_jobs()
    print(f"📊 Current jobs in D1: {get_total_jobs()}")

    # Import jobspy
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("❌ python-jobspy not installed! Run: pip install python-jobspy")
        sys.exit(1)

    import pandas as pd

    # Load progress
    progress = load_progress()
    start_role = progress.get("role_idx", 0)
    start_loc = progress.get("loc_idx", 0)
    fetched_at = datetime.now().strftime("%Y-%m-%d")

    total_combos = len(SEARCH_ROLES) * len(LOCATIONS)
    combo_num = 0
    total_new = 0
    total_found = 0

    if start_role > 0 or start_loc > 0:
        role_name = SEARCH_ROLES[start_role] if start_role < len(SEARCH_ROLES) else SEARCH_ROLES[0]
        print(f"\n🔄 Resuming from Role Index: {start_role}/{len(SEARCH_ROLES)}, Location Index: {start_loc}/{len(LOCATIONS)}")
        print(f"   Starting from: '{role_name}'")

    for r_idx in range(len(SEARCH_ROLES)):
        if r_idx < start_role:
            combo_num += len(LOCATIONS)
            continue

        role = SEARCH_ROLES[r_idx]

        for l_idx in range(len(LOCATIONS)):
            if r_idx == start_role and l_idx < start_loc:
                combo_num += 1
                continue

            # Check time limit
            elapsed = time.time() - START_TIME
            if elapsed >= MAX_RUN_SECONDS:
                print(f"\n⏰ Time limit ({MAX_RUN_SECONDS // 3600}h{(MAX_RUN_SECONDS % 3600) // 60}m) reached!")
                save_progress(r_idx, l_idx)
                print(f"💾 Progress saved: role={r_idx}, loc={l_idx}")
                print(f"📊 Total new jobs this run: {total_new}")
                return

            combo_num += 1
            location = LOCATIONS[l_idx]
            city = location.split(",")[0]
            print(f"[{combo_num}/{total_combos}] 🔍 '{role}' in {city}...", end=" ", flush=True)

            # Save progress BEFORE search
            save_progress(r_idx, l_idx)

            try:
                # Try with hours_old first, fallback without
                try:
                    jobs_df = scrape_jobs(
                        site_name=["indeed", "linkedin"],
                        search_term=role,
                        location=location,
                        results_wanted=RESULTS_PER_SEARCH,
                        hours_old=24,
                        country_indeed="India",
                    )
                except TypeError:
                    jobs_df = scrape_jobs(
                        site_name=["indeed", "linkedin"],
                        search_term=role,
                        location=location,
                        results_wanted=RESULTS_PER_SEARCH,
                        country_indeed="India",
                    )

                if jobs_df is None or jobs_df.empty:
                    print("0 jobs found")
                    continue

                batch = []
                for _, row in jobs_df.iterrows():
                    title = str(row.get("title", "")).strip()
                    company = str(row.get("company", "")).strip()
                    loc = str(row.get("location", "")).strip()
                    date_posted = str(row.get("date_posted", "")).strip()
                    job_url = str(row.get("job_url", "")).strip()
                    site = str(row.get("site", "")).strip().lower()

                    if not title or not company or title == "nan":
                        continue

                    # Extract Indeed permanent link
                    indeed_jk = ""
                    permanent_url = job_url
                    linkedin_url = ""

                    if "indeed" in site:
                        jk, perm = extract_indeed_jk(job_url)
                        indeed_jk = jk or ""
                        permanent_url = perm

                    if "linkedin" in site:
                        linkedin_url = job_url

                    final_url = permanent_url if permanent_url else job_url

                    batch.append({
                        "title": title,
                        "company": company,
                        "location": loc if loc != "nan" else "",
                        "date_posted": date_posted if date_posted != "nan" else "",
                        "url": final_url,
                        "linkedin_url": linkedin_url,
                        "source": site,
                        "role_search": role,
                        "fetched_at": fetched_at,
                        "indeed_jk": indeed_jk,
                        "permanent_url": permanent_url,
                    })

                stored = store_jobs_batch(batch)
                total_new += stored
                total_found += len(batch)

                li_count = sum(1 for j in batch if "linkedin" in j["source"])
                in_count = sum(1 for j in batch if "indeed" in j["source"])
                perm_count = sum(1 for j in batch if j["indeed_jk"])

                print(f"✅ {len(batch)} found (LI:{li_count}, Indeed:{in_count}, perm:{perm_count}), {stored} new (total: {total_new})")

            except Exception as e:
                err = str(e)
                if "block" in err.lower() or "429" in err or "403" in err:
                    print(f"🚫 Blocked! Cooling down 60s...")
                    time.sleep(60)
                else:
                    print(f"❌ Error: {err[:80]}")

            # Rate limit
            time.sleep(2)

            if TEST_MODE:
                break

        if TEST_MODE:
            break

    # All roles finished
    print(f"\n{'='*60}")
    print(f"  ✅ ALL ROLES COMPLETE!")
    print(f"     📦 Jobs found: {total_found}")
    print(f"     🆕 New stored: {total_new}")
    print(f"     📊 Total in Turso: {get_total_jobs()}")
    print(f"{'='*60}")

    # Check time remaining — if we have time, retry all roles
    elapsed = time.time() - START_TIME
    remaining = MAX_RUN_SECONDS - elapsed
    if remaining > 600 and not TEST_MODE:  # More than 10 min left
        print(f"\n⏳ {int(remaining // 60)} minutes remaining. Restarting from beginning to scrape more today's jobs...")
        save_progress(0, 0, finished_all=False)
        # Recursive call to scrape again
        main()
    else:
        save_progress(0, 0, finished_all=True)
        print("✅ Run complete. Progress reset for next run.")


if __name__ == "__main__":
    main()
