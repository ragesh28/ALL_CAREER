"""
STEP 3: Big Company Job Scraper (150 Top Companies)
Uses jobspy to scrape LinkedIn for job listings across multiple locations.

Features:
- Scrapes 150 top companies across 6 Indian cities
- Processes in batches of 50 companies (fresh session per batch)
- LinkedIn block detection with 5-minute cooldown + auto-resume
- Merges results into jobs.json and jobs_data.js (no duplicates)
- Progress tracking via scrape_progress.json

Usage:
  py -3.11 step3_big_company_scrape.py           # Full run (all 150 companies)
  py -3.11 step3_big_company_scrape.py --test 3   # Test mode (first 3 companies)

For GitHub Actions: python step3_big_company_scrape.py
"""

import os
import sys
import json
import time
import csv
import traceback
from datetime import datetime

import pandas as pd

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
BATCH_SIZE = 50
COOLDOWN_SECONDS = 300  # 5 minutes
MAX_RETRIES = 3         # Max retries per company on block
RESULTS_PER_SEARCH = 50 # Results per company+location combo

LOCATIONS = [
    "Bangalore, India",
    "Chennai, India",
    "Hyderabad, India",
    "Mumbai, India",
    "Delhi, India",
    "Pune, India",
]

PROGRESS_FILE = "scrape_progress.json"
# Big company scraper uses SEPARATE files from the daily Puppeteer scraper
# daily_jobs.html uses jobs.json/jobs_data.js (from scrape.js/companies.json only)
# Big company jobs go to big_jobs.json/big_jobs_data.js
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
    "Thoughtworks", "Hasura", "Chargebee", "Razorpay", "InMobi",
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
    """Get today's date stamp in YYYY-MM-DD format (local time)."""
    now = datetime.now()
    return f"{now.year}-{str(now.month).zfill(2)}-{str(now.day).zfill(2)}"


def load_progress():
    """Load scrape progress from file."""
    try:
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_completed_index": -1, "date": ""}


def save_progress(index):
    """Save scrape progress to file."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "last_completed_index": index,
            "date": get_date_stamp()
        }, f)


def load_existing_jobs():
    """Load existing big company jobs from big_jobs.json."""
    try:
        with open(JOBS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_jobs(all_jobs):
    """Save jobs to both jobs.json and jobs_data.js."""
    with open(JOBS_JSON, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=2, ensure_ascii=False)

    js_content = f"const activeJobs = {json.dumps(all_jobs, indent=2, ensure_ascii=False)};"
    with open(JOBS_DATA_JS, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"💾 Saved {len(all_jobs)} total jobs to {JOBS_JSON} and {JOBS_DATA_JS}")


def is_linkedin_block(error):
    """Check if an error indicates a LinkedIn block/rate-limit."""
    error_str = str(error).lower()
    block_indicators = [
        "429", "too many requests", "rate limit", "blocked",
        "captcha", "challenge", "forbidden", "access denied",
        "authwall", "auth_wall", "login required",
        "connectionerror", "connection reset", "timeout",
        "max retries exceeded",
    ]
    return any(indicator in error_str for indicator in block_indicators)


def scrape_company(company_name, locations, results_wanted=50):
    """
    Scrape jobs for a single company across all locations.
    Returns a list of job dicts and a flag indicating if blocked.
    """
    from jobspy import scrape_jobs

    all_company_jobs = []
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
                hours_old=168,  # Last 7 days
                linkedin_fetch_description=False,  # FAST mode
                verbose=0,
            )

            if jobs_df is not None and not jobs_df.empty:
                # Filter to matching company
                mask = jobs_df["company"].str.lower().str.contains(
                    company_name.lower().split()[0], na=False
                )
                matched = jobs_df[mask]

                for _, row in matched.iterrows():
                    job_url = str(row.get("job_url", ""))
                    if not job_url or job_url == "nan":
                        continue

                    job_entry = {
                        "company": str(row.get("company", company_name)),
                        "title": str(row.get("title", "Unknown")),
                        "url": job_url,
                        "location": str(row.get("location", location.split(",")[0])),
                        "date": str(row.get("date_posted", "Check Link")),
                        "fetchedAt": date_stamp,
                    }
                    all_company_jobs.append(job_entry)

                print(f"✅ {len(matched)} jobs")
            else:
                print("0 jobs")

        except Exception as e:
            error_msg = str(e)
            if is_linkedin_block(e):
                print(f"🚫 BLOCKED!")
                return all_company_jobs, True  # Return what we have + blocked flag
            else:
                print(f"⚠️ Error: {error_msg[:80]}")
                continue

    return all_company_jobs, False


def run(test_limit=None):
    """Main scraper function."""
    companies = TOP_COMPANIES
    if test_limit:
        companies = companies[:test_limit]
        print(f"\n🧪 TEST MODE: Scraping only {test_limit} companies\n")

    total = len(companies)
    print("=" * 60)
    print(f"  STEP 3: Big Company Job Scraper ({total} companies)")
    print("=" * 60)
    print(f"  📅 Date: {get_date_stamp()}")
    print(f"  📍 Locations: {len(LOCATIONS)}")
    print(f"  📦 Batch size: {BATCH_SIZE}")
    print(f"  ⏱️  Cooldown on block: {COOLDOWN_SECONDS}s")
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
            print(f"  📊 New jobs so far: {len(new_jobs)}")
            print(f"{'─' * 50}\n")
            # Small pause between batches to rotate session
            time.sleep(5)

        print(f"\n[{i + 1}/{total}] 🏢 {company}")

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
                save_progress(i - 1)  # Mark previous as last completed
                merged = new_jobs + existing_jobs
                save_jobs(merged)

                if retries <= MAX_RETRIES:
                    print(f"\n⏳ LinkedIn block detected! Waiting {COOLDOWN_SECONDS}s before retry...")
                    print(f"   (Retry {retries}/{MAX_RETRIES} for {company})")
                    time.sleep(COOLDOWN_SECONDS)
                    print(f"   🔄 Resuming scrape for {company}...")
                else:
                    print(f"\n❌ Max retries reached for {company}. Moving to next company.")
                    break
            else:
                # Success - save progress
                save_progress(i)
                break

        # Periodic save every 10 companies
        if (i + 1) % 10 == 0:
            merged = new_jobs + existing_jobs
            save_jobs(merged)
            print(f"💾 Checkpoint: {len(new_jobs)} new jobs saved")

    # Final save
    merged = new_jobs + existing_jobs
    save_jobs(merged)

    # Clean up progress file
    try:
        os.remove(PROGRESS_FILE)
    except FileNotFoundError:
        pass

    print(f"\n{'=' * 60}")
    print(f"  📊 RESULTS:")
    print(f"     🆕 New jobs found: {len(new_jobs)}")
    print(f"     📦 Total jobs in DB: {len(merged)}")
    print(f"     🚫 Times blocked: {blocked_count}")
    print(f"{'=' * 60}")
    print(f"\n✅ STEP 3 DONE!")


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
        # Save whatever we have
        try:
            existing = load_existing_jobs()
            save_jobs(existing)
        except Exception:
            pass
        sys.exit(1)
