from jobspy import scrape_jobs
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("Fetching Walmart jobs from LinkedIn via JobSpy...")

try:
    jobs = scrape_jobs(
        site_name=["linkedin"],
        search_term="Walmart",
        location="India",
        results_wanted=5
    )
    
    if jobs.empty:
        print("No jobs found or JobSpy failed to fetch jobs for Walmart.")
    else:
        print(f"Found {len(jobs)} jobs!")
        print(jobs[["title", "company", "location", "job_url"]].head())
except Exception as e:
    print(f"Error fetching jobs: {e}")
