"""
STEP 1: Get All Google Job Listings from LinkedIn (FAST)
Uses jobspy WITHOUT linkedin_fetch_description — just gets the job list.
Direct links will be extracted in Step 2 using Selenium.

Usage: py -3.11 step1_jobspy.py
"""

import csv
import pandas as pd
from jobspy import scrape_jobs

# ---- CONFIG ----
LOCATION = "Bangalore, India"
RESULTS_WANTED = 500
OUTPUT_FILE = "jobs.csv"

KEEP_COLUMNS = [
    "site", "title", "company", "location",
    "job_url", "job_type", "date_posted", "is_remote",
    "job_level",
]


def run():
    print(f"\n🔍 Getting ALL Google job listings from LinkedIn...")
    print(f"   Location: {LOCATION}")
    print(f"   (FAST mode — no page visits, ~10 seconds)\n")

    try:
        jobs = scrape_jobs(
            site_name=["linkedin"],
            search_term="Google",
            location=LOCATION,
            results_wanted=RESULTS_WANTED,
            country_indeed="India",
            hours_old=168,
            linkedin_fetch_description=False,  # FAST — just listings
            verbose=1,
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    if jobs.empty:
        print("⚠️ No jobs found.")
        return

    print(f"\n📋 Total LinkedIn results: {len(jobs)}")

    # Filter: only Google
    jobs = jobs[jobs["company"].str.lower().str.contains("google", na=False)]
    jobs = jobs.drop_duplicates(subset=["job_url"], keep="first")
    jobs["search_location"] = "Bangalore"
    print(f"🏢 Google jobs: {len(jobs)}")

    if jobs.empty:
        print("⚠️ No Google jobs found.")
        return

    # Keep only essential columns
    keep = [c for c in KEEP_COLUMNS if c in jobs.columns]
    keep.append("search_location")
    keep = list(dict.fromkeys(keep))
    jobs = jobs[keep]

    # Add empty columns for step 2
    jobs["direct_apply_url"] = ""
    jobs["apply_url"] = jobs["job_url"]  # Default to LinkedIn, step2 will update

    # Save
    jobs.to_csv(OUTPUT_FILE, index=False, quoting=csv.QUOTE_ALL)
    print(f"\n💾 Saved {len(jobs)} Google jobs to {OUTPUT_FILE}")
    print(f"\n✅ STEP 1 DONE! Now run: py -3.11 step2_get_links.py")


if __name__ == "__main__":
    run()
