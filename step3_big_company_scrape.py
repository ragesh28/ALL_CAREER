"""
STEP 3: Big Company Job Scraper (150 Top Companies)
Uses jobspy to scrape LinkedIn for job listings across multiple locations.
Gets ORIGINAL direct apply links (not LinkedIn redirect URLs).

Features:
- Scrapes 150 top companies across 6 Indian cities
- Uses linkedin_fetch_description=True to get job_url_direct (original company links)
- Stores ONLY jobs with direct apply links (skips LinkedIn-only links)
- Processes in batches of 50 companies (fresh session per batch)
- LinkedIn block detection with 1-minute cooldown + auto-resume
- Merges results into big_jobs.json and big_jobs_data.js (no duplicates)
- Progress tracking via scrape_progress.json
- 10-day retention: removes old jobs

Usage:
  py -3.11 step3_big_company_scrape.py           # Full run (all 150 companies)
  py -3.11 step3_big_company_scrape.py --test 3   # Test mode (first 3 companies)

For GitHub Actions: python step3_big_company_scrape.py
"""

import os
import sys
import json
import time
import traceback
from datetime import datetime, timedelta

import pandas as pd

# ---------------------------------------------------------------------------
# TIMER — gracefully stop before GitHub's 6-hour hard kill
# ---------------------------------------------------------------------------
START_TIME = time.time()
MAX_RUN_SECONDS = 5 * 3600 + 50 * 60  # 5 hours 50 minutes

def is_time_limit_approaching():
    elapsed = time.time() - START_TIME
    return elapsed >= MAX_RUN_SECONDS

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
BATCH_SIZE = 50
COOLDOWN_SECONDS = 60       # 1 minute wait on block (GitHub gives new IP)
MAX_RETRIES = 3
RESULTS_PER_SEARCH = 50
KEEP_DAYS = 10              # Delete jobs older than 10 days

LOCATIONS = [
    "Bangalore, India",
    "Chennai, India",
    "Hyderabad, India",
    "Mumbai, India",
    "Delhi, India",
    "Pune, India",
]

PROGRESS_FILE = "scrape_progress.json"
JOBS_JSON = "big_jobs.json"
JOBS_DATA_JS = "big_jobs_data.js"

# ---------------------------------------------------------------------------
# 150 TOP COMPANIES
# ---------------------------------------------------------------------------
TOP_COMPANIES = [
    "Google", "Microsoft", "Amazon", "Apple", "Meta",
    "Netflix", "Adobe", "Salesforce", "Oracle", "SAP",
    "IBM", "Intel", "Cisco", "Qualcomm", "NVIDIA",
    "Samsung", "Sony", "Dell", "HP", "Lenovo",
    "Accenture", "TCS", "Infosys", "Wipro", "HCLTech",
    "Cognizant", "Capgemini", "LTIMindtree", "Tech Mahindra", "Persistent Systems",
    "Flipkart", "Swiggy", "Zomato", "Paytm", "PhonePe",
    "Razorpay", "CRED", "Meesho", "Zerodha", "Groww",
    "Uber", "Ola", "Myntra", "Nykaa", "BigBasket",
    "JPMorgan Chase", "Goldman Sachs", "Morgan Stanley", "Bank of America", "Citibank",
    "Wells Fargo", "Barclays", "HSBC", "Deutsche Bank", "Standard Chartered",
    "Deloitte", "PwC", "EY", "KPMG", "McKinsey",
    "Boston Consulting Group", "Bain & Company", "Mu Sigma", "Fractal Analytics", "Tiger Analytics",
    "Walmart", "Target", "Visa", "Mastercard", "American Express",
    "PayPal", "Stripe", "Intuit", "ServiceNow", "Workday",
    "Snowflake", "Databricks", "Cloudera", "Confluent", "MongoDB",
    "Atlassian", "Freshworks", "Zoho", "Postman", "BrowserStack",
    "Thoughtworks", "Hasura", "Chargebee", "InMobi",
    "Honeywell", "Bosch", "Siemens", "ABB", "Schneider Electric",
    "GE", "Philips", "3M", "Johnson Controls", "Emerson",
    "Mercedes Benz", "BMW", "Volkswagen", "Toyota", "Ford",
    "Continental", "Caterpillar", "John Deere", "Cummins", "Eaton",
    "Shell", "Schlumberger", "Baker Hughes", "Halliburton", "TotalEnergies",
    "Ericsson", "Nokia", "Juniper Networks", "Broadcom", "Marvell",
    "Nutanix", "Rubrik", "Cohesity", "VMware", "Palo Alto Networks",
    "CrowdStrike", "Fortinet", "Zscaler", "Splunk", "Elastic",
    "Twilio", "Datadog", "New Relic", "PagerDuty", "Okta",
    "UiPath", "Automation Anywhere", "Blue Prism", "Celonis", "Appian",
    "Epic Games", "Unity", "EA Sports", "Riot Games", "Ubisoft",
    "Spotify", "Twitter", "LinkedIn", "Pinterest", "Snap",
]

# Remove duplicates while preserving order
seen = set()
UNIQUE_COMPANIES = []
for c in TOP_COMPANIES:
    if c not in seen:
        seen.add(c)
        UNIQUE_COMPANIES.append(c)
TOP_COMPANIES = UNIQUE_COMPANIES


def get_date_stamp():
    now = datetime.now()
    return f"{now.year}-{str(now.month).zfill(2)}-{str(now.day).zfill(2)}"


def load_progress():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_completed_index": -1, "date": ""}


def save_progress(index):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "last_completed_index": index,
            "date": get_date_stamp()
        }, f)


def load_existing_jobs():
    try:
        with open(JOBS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def clean_old_jobs(jobs):
    """Remove jobs older than KEEP_DAYS days."""
    cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    before = len(jobs)
    jobs = [j for j in jobs if j.get("fetchedAt", "9999") >= cutoff]
    removed = before - len(jobs)
    if removed > 0:
        print(f"🧹 Removed {removed} jobs older than {cutoff}")
    return jobs


def save_jobs(all_jobs):
    """Save jobs to both big_jobs.json and big_jobs_data.js."""
    # Clean old jobs before saving
    all_jobs = clean_old_jobs(all_jobs)

    with open(JOBS_JSON, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=2, ensure_ascii=False)

    # IMPORTANT: variable name must be 'bigJobs' to match big_company_jobs.html
    js_content = f"const bigJobs = {json.dumps(all_jobs, indent=2, ensure_ascii=False)};"
    with open(JOBS_DATA_JS, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"💾 Saved {len(all_jobs)} total jobs to {JOBS_JSON} and {JOBS_DATA_JS}")


def is_linkedin_block(error):
    error_str = str(error).lower()
    indicators = [
        "429", "too many requests", "rate limit", "blocked",
        "captcha", "forbidden", "access denied", "authwall",
        "connectionerror", "connection reset", "timeout",
        "max retries exceeded",
    ]
    return any(ind in error_str for ind in indicators)


def scrape_company(company_name, locations, results_wanted=50):
    """
    Scrape jobs for a single company across all locations.
    Uses linkedin_fetch_description=True to get job_url_direct (original links).
    Only keeps jobs with direct apply links (ignores LinkedIn-only links).
    Returns a list of job dicts and a flag indicating if blocked.
    """
    from jobspy import scrape_jobs

    direct_jobs = []
    date_stamp = get_date_stamp()

    for location in locations:
        try:
            print(f"   📍 {location}...", end=" ", flush=True)
            jobs_df = scrape_jobs(
                site_name=["linkedin"],
                search_term=company_name,
                location=location,
                results_wanted=results_wanted,
                country_indeed="India",
                hours_old=24,
                linkedin_fetch_description=True,  # Gets job_url_direct (original links)!
                verbose=0,
            )

            if jobs_df is None or jobs_df.empty:
                print("0 jobs")
                continue

            # Filter to matching company
            mask = jobs_df["company"].str.lower().str.contains(
                company_name.lower().split()[0], na=False
            )
            matched = jobs_df[mask]

            direct_count = 0
            for _, row in matched.iterrows():
                # Get the direct URL (original company career page link)
                direct_url = str(row.get("job_url_direct", ""))
                linkedin_url = str(row.get("job_url", ""))

                # Only keep jobs with direct apply links
                if direct_url in ("", "nan", "None"):
                    continue  # Skip — no direct link, only LinkedIn redirect

                direct_jobs.append({
                    "company": str(row.get("company", company_name)),
                    "title": str(row.get("title", "Unknown")),
                    "url": direct_url,  # Original company career page URL
                    "linkedin_url": linkedin_url,
                    "location": str(row.get("location", location.split(",")[0])),
                    "date": str(row.get("date_posted", "None")),
                    "fetchedAt": date_stamp,
                })
                direct_count += 1

            print(f"✅ {direct_count} direct links")

        except Exception as e:
            if is_linkedin_block(e):
                print(f"🚫 BLOCKED!")
                return direct_jobs, True
            else:
                print(f"⚠️ Error: {str(e)[:80]}")
                continue

    return direct_jobs, False


def run(test_limit=None):
    companies = TOP_COMPANIES
    if test_limit:
        companies = companies[:test_limit]
        print(f"\n🧪 TEST MODE: Scraping only {test_limit} companies\n")

    total = len(companies)
    print("=" * 60)
    print(f"  BIG COMPANY SCRAPER ({total} companies → Direct Links)")
    print("=" * 60)
    print(f"  📅 Date: {get_date_stamp()}")
    print(f"  📍 Locations: {len(LOCATIONS)}")
    print(f"  📦 Batch size: {BATCH_SIZE}")
    print(f"  ⏱️  Cooldown on block: {COOLDOWN_SECONDS}s")
    print(f"  📆 Retention: {KEEP_DAYS} days")
    print(f"  🔗 Mode: Direct links only (linkedin_fetch_description=True)")
    print("=" * 60)

    # Check for resume from previous blocked run
    progress = load_progress()
    start_index = 0
    if progress["date"] == get_date_stamp() and progress["last_completed_index"] >= 0:
        start_index = progress["last_completed_index"] + 1
        if start_index < total:
            print(f"\n🔄 Resuming from company #{start_index + 1}: {companies[start_index]}")
        else:
            print(f"\n✅ All companies already scraped today!")
            return

    # Load existing jobs
    existing_jobs = load_existing_jobs()
    existing_urls = set(job.get("url", "") for job in existing_jobs)
    print(f"📊 Existing jobs in database: {len(existing_jobs)}")

    new_jobs = []
    blocked_count = 0

    for i in range(start_index, total):
        company = companies[i]
        batch_num = (i // BATCH_SIZE) + 1

        # Log batch transitions
        if i > start_index and i % BATCH_SIZE == 0:
            print(f"\n{'─' * 50}")
            print(f"  🔄 Starting batch {batch_num} (fresh session)")
            print(f"  📊 New direct-link jobs so far: {len(new_jobs)}")
            print(f"{'─' * 50}\n")
            time.sleep(5)

        print(f"\n[{i + 1}/{total}] 🏢 {company}")

        # Time limit check
        if is_time_limit_approaching():
            elapsed_min = int((time.time() - START_TIME) / 60)
            print(f"\n⏰ TIME LIMIT ({elapsed_min} min). Saving progress and stopping.")
            save_progress(i - 1)
            merged = new_jobs + existing_jobs
            save_jobs(merged)
            print(f"✅ Progress saved. GitHub Action will restart in 10 minutes.")
            return

        retries = 0
        while retries <= MAX_RETRIES:
            company_jobs, was_blocked = scrape_company(
                company, LOCATIONS, RESULTS_PER_SEARCH
            )

            # Add non-duplicate jobs
            for job in company_jobs:
                if job["url"] not in existing_urls:
                    new_jobs.append(job)
                    existing_urls.add(job["url"])

            if was_blocked:
                blocked_count += 1
                retries += 1

                # Save progress before cooldown
                save_progress(i - 1)
                merged = new_jobs + existing_jobs
                save_jobs(merged)

                if retries <= MAX_RETRIES:
                    print(f"\n⏳ Blocked! Waiting {COOLDOWN_SECONDS}s... (retry {retries}/{MAX_RETRIES})")
                    time.sleep(COOLDOWN_SECONDS)
                else:
                    print(f"\n❌ Max retries for {company}. Moving on.")
                    break
            else:
                save_progress(i)
                break

        # Periodic save every 10 companies
        if (i + 1) % 10 == 0:
            merged = new_jobs + existing_jobs
            save_jobs(merged)
            print(f"💾 Checkpoint: {len(new_jobs)} new direct-link jobs saved")

    # Final save
    merged = new_jobs + existing_jobs
    save_jobs(merged)

    # Clean up progress file (all done)
    try:
        os.remove(PROGRESS_FILE)
    except FileNotFoundError:
        pass

    print(f"\n{'=' * 60}")
    print(f"  📊 RESULTS:")
    print(f"     🆕 New direct-link jobs found: {len(new_jobs)}")
    print(f"     📦 Total jobs in DB: {len(merged)}")
    print(f"     🚫 Times blocked: {blocked_count}")
    print(f"={'=' * 59}")
    print(f"\n✅ DONE!")


if __name__ == "__main__":
    test_count = None
    if "--test" in sys.argv:
        try:
            idx = sys.argv.index("--test")
            test_count = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            test_count = 3

    try:
        run(test_limit=test_count)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        try:
            existing = load_existing_jobs()
            save_jobs(existing)
        except Exception:
            pass
        sys.exit(1)
