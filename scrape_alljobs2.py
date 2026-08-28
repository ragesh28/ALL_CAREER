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
from bs4 import BeautifulSoup
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
    # 🚶 Walk-in Interview Keywords
    "Walkin Interview", "Walk-in Drive", "Walk In",
    # Tech & Business Roles
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
    "Pune, India",
    "Delhi, India",
    "Noida, India",
    "Gurgaon, India",
    "Kolkata, India",
    "Ahmedabad, India",
    "Coimbatore, India",
    "Kochi, India",
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
            return {"role_idx": 0, "loc_idx": 0, "date": today, "blocked_jobs": []}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"role_idx": 0, "loc_idx": 0, "date": datetime.now().strftime("%Y-%m-%d"), "blocked_jobs": []}


def save_progress(role_idx, loc_idx, finished_all=False, blocked_jobs=None):
    today = datetime.now().strftime("%Y-%m-%d")
    if finished_all:
        data = {"role_idx": 0, "loc_idx": 0, "date": today, "finished": True, "blocked_jobs": []}
    else:
        data = {
            "role_idx": role_idx, "loc_idx": loc_idx,
            "date": today, "finished": False,
            "blocked_jobs": blocked_jobs or []
        }
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


def fetch_indeed_description(job_url, max_retries=2):
    """
    Fetch full job description from Indeed's viewjob page.
    Retries up to max_retries times. Returns description text or ''.
    """
    if not job_url:
        return ""

    # Try to build the Indeed viewjob URL from jk
    urls_to_try = [job_url]
    jk_match = re.search(r'jk=([a-f0-9]{16})', str(job_url))
    if jk_match:
        jk_url = f"https://www.indeed.com/viewjob?jk={jk_match.group(1)}&from=serp&vjs=3"
        if jk_url != job_url:
            urls_to_try.insert(0, jk_url)
    # Also try in.indeed.com for India jobs
    for url in list(urls_to_try):
        if 'www.indeed.com' in url:
            urls_to_try.append(url.replace('www.indeed.com', 'in.indeed.com'))

    for attempt_url in urls_to_try:
        for attempt in range(max_retries):
            try:
                resp = requests.get(
                    attempt_url,
                    timeout=12,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                                       "Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                )
                if resp.status_code == 429:
                    delay = 5 * (2 ** attempt)  # 5s, 10s
                    print(f" [Indeed 429, waiting {delay}s]", end="", flush=True)
                    time.sleep(delay)
                    continue
                if resp.status_code != 200:
                    break  # Try next URL

                soup = BeautifulSoup(resp.text, "html.parser")

                # Indeed uses #jobDescriptionText for the description
                desc_div = soup.find("div", id="jobDescriptionText")
                if not desc_div:
                    # Fallback: try class-based selectors
                    desc_div = soup.find("div", class_=lambda x: x and "jobsearch-jobDescriptionText" in x)
                if not desc_div:
                    desc_div = soup.find("div", class_=lambda x: x and "job-description" in str(x).lower())

                if desc_div:
                    desc = " ".join(desc_div.get_text().split()).strip()
                    if len(desc) >= 80:
                        return desc
                break  # Got a 200 but no description — try next URL
            except Exception:
                time.sleep(3)
                continue

    return ""


# ---------------------------------------------------------------------------
# LINKEDIN FULL DESCRIPTION FETCHER
# ---------------------------------------------------------------------------
def extract_linkedin_job_id(url):
    """Extract the numeric job ID from a LinkedIn URL."""
    match = re.search(r'/jobs/view/(\d+)', str(url))
    return match.group(1) if match else None


def fetch_linkedin_description(job_url, max_retries=2):
    """
    Fetch the full job description from LinkedIn using the guest API endpoint.
    This is an alternative to visiting the full job page (which JobSpy does).
    Returns the full description text, or '' if blocked.
    """
    job_id = extract_linkedin_job_id(job_url)
    if not job_id:
        return ""

    # Try the alternative guest API endpoint first, then fall back to the full page
    urls_to_try = [
        f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}",
        f"https://www.linkedin.com/jobs/view/{job_id}/",
    ]

    for attempt_url in urls_to_try:
        for attempt in range(max_retries):
            try:
                resp = requests.get(
                    attempt_url,
                    timeout=10,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                                       "Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                )
                if resp.status_code == 429:
                    delay = 5 * (2 ** attempt)  # 5s, 10s
                    print(f" [429 rate-limit, waiting {delay}s]", end="", flush=True)
                    time.sleep(delay)
                    continue
                if resp.status_code != 200:
                    break  # Try next URL

                soup = BeautifulSoup(resp.text, "html.parser")
                div = soup.find(
                    "div",
                    class_=lambda x: x and "show-more-less-html__markup" in x
                )
                if div:
                    desc = " ".join(div.get_text().split()).strip()
                    if len(desc) >= 100:
                        return desc
                break  # Got a 200 but no description div — try next URL
            except Exception:
                time.sleep(3)
                continue

    return ""


def refetch_blocked_descriptions(batch, max_consecutive_failures=5):
    """
    For LinkedIn AND Indeed jobs in the batch that have empty/short descriptions,
    try to re-fetch the full description (max 2 retries per job).

    Returns:
        (updated_batch, linkedin_blocked)
        - updated_batch: the batch with descriptions filled in where possible
        - linkedin_blocked: True if LinkedIn has fully blocked this IP
    """
    from extractor_utils import extract_experience, extract_skills

    # ── LinkedIn retry ──
    linkedin_blocked_jobs = [
        (i, job) for i, job in enumerate(batch)
        if "linkedin" in job.get("source", "") and len(job.get("_description", "")) < 100
    ]

    linkedin_blocked = False
    if linkedin_blocked_jobs:
        print(f"\n    🔄 Re-fetching {len(linkedin_blocked_jobs)} blocked LinkedIn descriptions...", flush=True)
        consecutive_failures = 0
        refetched = 0
        still_blocked = 0

        for idx, job in linkedin_blocked_jobs:
            desc = fetch_linkedin_description(job.get("url", ""))
            if len(desc) >= 100:
                batch[idx]["_description"] = desc
                batch[idx]["experience"] = extract_experience(desc, title=job.get("title", ""))
                batch[idx]["skills"] = extract_skills(desc)
                refetched += 1
                consecutive_failures = 0
                print(f"    ✅ Got description for: {job.get('title', '')[:50]}", flush=True)
            else:
                still_blocked += 1
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    print(f"    🛑 LinkedIn blocked this IP ({consecutive_failures} consecutive failures)", flush=True)
                    linkedin_blocked = True
                    break

            time.sleep(1)

        print(f"    📊 LinkedIn re-fetched: {refetched}, Still blocked: {still_blocked}", flush=True)

    # ── Indeed retry (2 attempts max per job) ──
    indeed_no_desc_jobs = [
        (i, job) for i, job in enumerate(batch)
        if "indeed" in job.get("source", "") and len(job.get("_description", "")) < 80
    ]

    if indeed_no_desc_jobs:
        print(f"    🔄 Re-fetching {len(indeed_no_desc_jobs)} Indeed jobs with missing descriptions...", flush=True)
        indeed_refetched = 0
        indeed_still_missing = 0

        for idx, job in indeed_no_desc_jobs:
            desc = fetch_indeed_description(job.get("url", ""), max_retries=2)
            if len(desc) >= 80:
                batch[idx]["_description"] = desc
                batch[idx]["experience"] = extract_experience(desc, title=job.get("title", ""))
                batch[idx]["skills"] = extract_skills(desc)
                indeed_refetched += 1
                print(f"    ✅ Indeed desc: {job.get('title', '')[:50]}", flush=True)
            else:
                indeed_still_missing += 1
                # Job is still saved — just without experience/description

            time.sleep(1)

        print(f"    📊 Indeed re-fetched: {indeed_refetched}, Still missing: {indeed_still_missing}", flush=True)

    return batch, linkedin_blocked


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
    blocked_jobs_from_prev = progress.get("blocked_jobs", [])
    fetched_at = datetime.now().strftime("%Y-%m-%d")

    total_combos = len(SEARCH_ROLES) * len(LOCATIONS)
    combo_num = 0
    total_new = 0
    total_found = 0
    pending_blocked_jobs = []  # Track jobs that still need descriptions

    if start_role > 0 or start_loc > 0:
        role_name = SEARCH_ROLES[start_role] if start_role < len(SEARCH_ROLES) else SEARCH_ROLES[0]
        print(f"\n🔄 Resuming from Role Index: {start_role}/{len(SEARCH_ROLES)}, Location Index: {start_loc}/{len(LOCATIONS)}")
        print(f"   Starting from: '{role_name}'")

    # ── Re-fetch blocked descriptions from previous run (new IP!) ──
    if blocked_jobs_from_prev:
        print(f"\n🔁 Re-fetching {len(blocked_jobs_from_prev)} blocked LinkedIn descriptions from previous run (new IP)...")
        from extractor_utils import extract_experience, extract_skills
        refetched_count = 0
        still_blocked_count = 0
        consecutive_failures = 0

        for blocked_job in blocked_jobs_from_prev:
            url = blocked_job.get("url", "")
            title = blocked_job.get("title", "")
            desc = fetch_linkedin_description(url)

            if len(desc) >= 100:
                exp = extract_experience(desc, title=title)
                skills = extract_skills(desc)
                # Update the job in the database with the correct experience
                update_job = blocked_job.copy()
                update_job["experience"] = exp
                update_job["skills"] = skills
                store_jobs_batch([update_job])
                refetched_count += 1
                consecutive_failures = 0
                print(f"  ✅ {title[:50]} → {exp}")
            else:
                still_blocked_count += 1
                consecutive_failures += 1
                pending_blocked_jobs.append(blocked_job)
                if consecutive_failures >= 5:
                    print(f"  🛑 Still blocked after 5 consecutive failures. Will retry on next run.")
                    # Add remaining jobs to pending
                    remaining_idx = blocked_jobs_from_prev.index(blocked_job) + 1
                    pending_blocked_jobs.extend(blocked_jobs_from_prev[remaining_idx:])
                    break

            time.sleep(1)

        print(f"  📊 Re-fetched: {refetched_count}, Still blocked: {still_blocked_count}")

        if pending_blocked_jobs:
            print(f"  ⚠️  {len(pending_blocked_jobs)} jobs still need descriptions. Will save for next run.")
            save_progress(start_role, start_loc, blocked_jobs=pending_blocked_jobs)
            # Don't exit — continue with normal scraping, the blocked jobs are saved

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
                save_progress(r_idx, l_idx, blocked_jobs=pending_blocked_jobs)
                print(f"💾 Progress saved: role={r_idx}, loc={l_idx}, blocked_jobs={len(pending_blocked_jobs)}")
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

                from extractor_utils import extract_experience, extract_skills, extract_walkin_info
                
                batch = []
                for _, row in jobs_df.iterrows():
                    title = str(row.get("title", "")).strip()
                    company = str(row.get("company", "")).strip()
                    loc = str(row.get("location", "")).strip()
                    date_posted = str(row.get("date_posted", "")).strip()
                    job_url = str(row.get("job_url", "")).strip()
                    site = str(row.get("site", "")).strip().lower()
                    desc = str(row.get("description", "")).strip()
                    if desc == "None":
                        desc = ""

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

                    # Only extract experience from FULL descriptions (>=100 chars)
                    desc_is_full = len(desc) >= 100
                    if desc_is_full:
                        exp = extract_experience(desc, title=title)
                        skills = extract_skills(desc)
                    else:
                        exp = ""
                        skills = []

                    # Extract Walk-in Interview status & Date
                    w_info = extract_walkin_info(title=title, description=desc)

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
                        "is_walkin": w_info.get("is_walkin", False),
                        "walkin_date": w_info.get("walkin_date"),
                        "walkin_time": w_info.get("walkin_time"),
                        "_description": desc,  # Keep for re-fetch check (not saved to DB)
                    })

                # ── Re-fetch blocked LinkedIn + Indeed descriptions ──
                batch, linkedin_blocked = refetch_blocked_descriptions(batch)

                # Remove internal _description field before storing
                for job in batch:
                    job.pop("_description", None)

                stored = store_jobs_batch(batch)
                total_new += stored
                total_found += len(batch)

                li_count = sum(1 for j in batch if "linkedin" in j["source"])
                in_count = sum(1 for j in batch if "indeed" in j["source"])
                perm_count = sum(1 for j in batch if j["indeed_jk"])
                li_no_desc = sum(1 for j in batch if "linkedin" in j["source"] and not j.get("experience"))
                in_no_desc = sum(1 for j in batch if "indeed" in j["source"] and not j.get("experience"))

                no_desc_info = ""
                if li_no_desc or in_no_desc:
                    parts = []
                    if li_no_desc: parts.append(f"LI_noDesc:{li_no_desc}")
                    if in_no_desc: parts.append(f"IN_noDesc:{in_no_desc}")
                    no_desc_info = f", {', '.join(parts)}"
                print(f"✅ {len(batch)} found (LI:{li_count}, Indeed:{in_count}, perm:{perm_count}{no_desc_info}), {stored} new (total: {total_new})")

                # If LinkedIn blocked us, save checkpoint with blocked jobs and exit
                if linkedin_blocked:
                    blocked_jobs_to_save = [
                        {"url": j["url"], "title": j["title"], "company": j["company"],
                         "location": j["location"], "date_posted": j["date_posted"],
                         "source": j["source"], "role_search": j["role_search"],
                         "fetched_at": j["fetched_at"], "linkedin_url": j.get("linkedin_url", ""),
                         "indeed_jk": "", "permanent_url": j["url"]}
                        for j in batch
                        if "linkedin" in j.get("source", "") and not j.get("experience")
                    ] + pending_blocked_jobs

                    print(f"\n🛑 LinkedIn blocked this IP! Saving {len(blocked_jobs_to_save)} blocked jobs.")
                    print(f"💾 Saving checkpoint for restart with new IP...")
                    save_progress(r_idx, l_idx, blocked_jobs=blocked_jobs_to_save)
                    print(f"📊 Total new jobs this run: {total_new}")
                    return  # Exit → workflow will auto-restart with new IP

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
