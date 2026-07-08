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

# Configure stdout to handle UTF-8 printing cleanly on Windows
sys.stdout.reconfigure(encoding='utf-8')

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
CLOUDFLARE_URL = os.environ.get("CLOUDFLARE_D1_URL", "https://api.cloudflare.com/client/v4/accounts/62eacb67a7ee0b199f58ccb540a3eff7/d1/database/20b71b5c-c070-45b5-9542-27ed1cad89e5/query")
CLOUDFLARE_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")

RESULTS_PER_SEARCH = 80
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
                jobs_list = []
                
                # Scrape LinkedIn
                try:
                    li_df = scrape_jobs(
                        site_name=["linkedin"], search_term=role, location=location,
                        results_wanted=RESULTS_PER_SEARCH, hours_old=24,
                        linkedin_fetch_description=True
                    )
                    if li_df is not None and not li_df.empty:
                        jobs_list.append(li_df)
                except TypeError:
                    # Fallback without hours_old if library version is old
                    try:
                        li_df = scrape_jobs(
                            site_name=["linkedin"], search_term=role, location=location,
                            results_wanted=RESULTS_PER_SEARCH,
                            linkedin_fetch_description=True
                        )
                        if li_df is not None and not li_df.empty:
                            jobs_list.append(li_df)
                    except Exception as e:
                        print(f" [LinkedIn Error: {e}]", end="")
                except Exception as e:
                    print(f" [LinkedIn Error: {e}]", end="")

                # Scrape Indeed
                try:
                    ind_df = scrape_jobs(
                        site_name=["indeed"], search_term=role, location=location,
                        results_wanted=RESULTS_PER_SEARCH, hours_old=24, country_indeed="India"
                    )
                    if ind_df is not None and not ind_df.empty:
                        jobs_list.append(ind_df)
                except TypeError:
                    # Fallback without hours_old if library version is old
                    try:
                        ind_df = scrape_jobs(
                            site_name=["indeed"], search_term=role, location=location,
                            results_wanted=RESULTS_PER_SEARCH, country_indeed="India"
                        )
                        if ind_df is not None and not ind_df.empty:
                            jobs_list.append(ind_df)
                    except Exception as e:
                        print(f" [Indeed Error: {e}]", end="")
                except Exception as e:
                    print(f" [Indeed Error: {e}]", end="")

                if jobs_list:
                    jobs_df = pd.concat(jobs_list, ignore_index=True)
                else:
                    jobs_df = pd.DataFrame()

                if jobs_df is None or jobs_df.empty:
                    print("0 jobs found")
                    continue

                from extractor_utils import extract_experience, extract_skills
                
                batch = []
                for _, row in jobs_df.iterrows():
                    title = str(row.get("title", "")).strip()
                    company = str(row.get("company", "")).strip()
                    loc = str(row.get("location", "")).strip()
                    date_posted = str(row.get("date_posted", "")).strip()
                    job_url = str(row.get("job_url", "")).strip()
                    site = str(row.get("site", "")).strip().lower()
                    desc = str(row.get("description", "")).strip()

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

                    # Extract experience and skills from description
                    exp = extract_experience(desc)
                    skills = extract_skills(desc)

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
                        "experience": exp,
                        "skills": skills,
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

    save_progress(0, 0, finished_all=True)
    print("✅ Run complete. Progress reset for next run.")


if __name__ == "__main__":
    main()
