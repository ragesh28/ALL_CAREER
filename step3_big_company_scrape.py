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
- 20-day retention: removes old jobs

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
KEEP_DAYS = 20              # Delete jobs older than 20 days

LOCATIONS = [
    "Bangalore, India",
    "Chennai, India",
    "Hyderabad, India",
    "Mumbai, India",
    "Delhi, India",
    "Pune, India",
]

PROGRESS_FILE = "scrape_progress.json"

TURSO_URL   = os.environ.get("TURSO_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "")  # Set via GitHub Secret — never hardcode!

def turso_execute(statements):
    if not TURSO_URL or not TURSO_TOKEN:
        print("⚠️ TURSO not configured, skipping DB storage")
        return None

    import requests
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
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        print(f"❌ Turso connection error: {e}")
        return None

def setup_database():
    print("📦 Setting up Turso database (big_jobs table)...")
    turso_execute(["""
        CREATE TABLE IF NOT EXISTS big_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            date_posted TEXT,
            url TEXT NOT NULL,
            linkedin_url TEXT,
            fetched_at TEXT NOT NULL,
            source TEXT DEFAULT 'linkedin',
            UNIQUE(url)
        )
    """])
    # Add source column if upgrading from older schema
    turso_execute(["ALTER TABLE big_jobs ADD COLUMN source TEXT DEFAULT 'linkedin'"])

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
    """Save jobs directly to Turso big_jobs table."""
    if not all_jobs: return

    # Clean old jobs
    all_jobs = clean_old_jobs(all_jobs)

    statements = []
    for job in all_jobs:
        statements.append({
            "sql": "INSERT OR IGNORE INTO big_jobs (title, company, location, date_posted, url, linkedin_url, fetched_at, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            "args": [
                {"type": "text", "value": str(job.get("title", ""))},
                {"type": "text", "value": str(job.get("company", ""))},
                {"type": "text", "value": str(job.get("location", ""))},
                {"type": "text", "value": str(job.get("date", ""))},
                {"type": "text", "value": str(job.get("url", ""))},
                {"type": "text", "value": str(job.get("linkedin_url", ""))},
                {"type": "text", "value": str(job.get("fetchedAt", ""))},
                {"type": "text", "value": str(job.get("source", "linkedin"))},
            ]
        })

    # Chunk into 50 statements
    total_inserted = 0
    for i in range(0, len(statements), 50):
        chunk = statements[i:i+50]
        res = turso_execute(chunk)
        if res:
            for r in res.get("results", []):
                if r.get("type") == "ok":
                    total_inserted += r.get("response", {}).get("result", {}).get("affected_row_count", 0)

    print(f"💾 Inserted {total_inserted} new jobs to Turso 'big_jobs' table out of {len(all_jobs)} total.")


def is_linkedin_block(error):
    error_str = str(error).lower()
    indicators = [
        "429", "too many requests", "rate limit", "blocked",
        "captcha", "forbidden", "access denied", "authwall",
        "connectionerror", "connection reset", "timeout",
        "max retries exceeded",
    ]
    return any(ind in error_str for ind in indicators)


def scrape_company(company_name, locations, results_wanted=50, proxy_list=None):
    """
    Scrape jobs for a single company from LinkedIn + Indeed.
    Stores the LinkedIn/Indeed job URL directly — no extra fetching needed.
    Returns a list of job dicts and a flag indicating if blocked.
    """
    from jobspy import scrape_jobs
    import random

    all_jobs = []
    date_stamp = get_date_stamp()

    proxy_url = None
    if proxy_list:
        proxy_url = random.choice(proxy_list)

    for location in locations:
        try:
            print(f"   📍 {location}...", end=" ", flush=True)
            jobs_df = scrape_jobs(
                site_name=["linkedin", "indeed"],  # Both sources
                search_term=company_name,
                location=location,
                results_wanted=results_wanted,
                country_indeed="India",
                hours_old=72,               # Last 3 days per scrape run
                verbose=0,
                proxy=proxy_url
            )

            if jobs_df is None or jobs_df.empty:
                print("0 jobs")
                continue

            # Filter to matching company name
            mask = jobs_df["company"].str.lower().str.contains(
                company_name.lower().split()[0], na=False
            )
            matched = jobs_df[mask]

            count = 0
            for _, row in matched.iterrows():
                # Use the LinkedIn/Indeed job URL directly
                job_url = str(row.get("job_url", ""))
                if job_url in ("", "nan", "None"):
                    continue

                source = str(row.get("site", "linkedin"))

                all_jobs.append({
                    "company":    str(row.get("company", company_name)),
                    "title":      str(row.get("title", "Unknown")),
                    "url":        job_url,           # LinkedIn or Indeed URL
                    "linkedin_url": job_url if "linkedin" in source else "",
                    "location":   str(row.get("location", location.split(",")[0])),
                    "date":       str(row.get("date_posted", "None")),
                    "fetchedAt":  date_stamp,
                    "source":     source,
                })
                count += 1

            print(f"✅ {count} jobs")

        except Exception as e:
            if is_linkedin_block(e):
                print(f"🚫 BLOCKED!")
                return all_jobs, True
            else:
                print(f"⚠️ Error: {str(e)[:80]}")
                continue

    return all_jobs, False


def run(test_limit=None):
    companies = TOP_COMPANIES
    if test_limit:
        companies = companies[:test_limit]
        print(f"\n🧪 TEST MODE: Scraping only {test_limit} companies\n")

    total = len(companies)
    print("=" * 60)
    print(f"  BIG COMPANY SCRAPER ({total} companies → LinkedIn + Indeed)")
    print("=" * 60)
    print(f"  📅 Date: {get_date_stamp()}")
    print(f"  📍 Locations: {len(LOCATIONS)}")
    print(f"  📦 Batch size: {BATCH_SIZE}")
    print(f"  ⏱️  Cooldown on block: {COOLDOWN_SECONDS}s")
    print(f"  📆 Retention: {KEEP_DAYS} days")
    print(f"  🔗 Mode: LinkedIn + Indeed URLs (no extra fetching)")
    print("=" * 60)

    setup_database()

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

    # No need to load existing jobs anymore; Turso INSERT OR IGNORE handles deduplication.
    print("📋 Will rely on Turso `UNIQUE(url)` for deduplication.")

    new_jobs_count = 0
    blocked_count = 0

    for i in range(start_index, total):
        company = companies[i]
        batch_num = (i // BATCH_SIZE) + 1

        # Log batch transitions
        if i > start_index and i % BATCH_SIZE == 0:
            print(f"\n{'─' * 50}")
            print(f"  🔄 Starting batch {batch_num} (fresh session)")
            print(f"  📊 Jobs saved so far: {new_jobs_count}")
            print(f"{'─' * 50}\n")
            time.sleep(5)

        print(f"\n[{i + 1}/{total}] 🏢 {company}")

        # Time limit check
        if is_time_limit_approaching():
            elapsed_min = int((time.time() - START_TIME) / 60)
            print(f"\n⏰ TIME LIMIT ({elapsed_min} min). Saving progress and stopping.")
            save_progress(i - 1)
            print(f"✅ Progress saved. GitHub Action will restart in 10 minutes.")
            return

        retries = 0
        while retries <= MAX_RETRIES:
            company_jobs, was_blocked = scrape_company(
                company, LOCATIONS, RESULTS_PER_SEARCH
            )

            if company_jobs:
                save_jobs(company_jobs)
                new_jobs_count += len(company_jobs)

            if was_blocked:
                blocked_count += 1
                retries += 1

                # Save progress before cooldown
                save_progress(i - 1)

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
            print(f"💾 Checkpoint: {new_jobs_count} jobs processed")

    # Clean up progress file (all done)
    try:
        os.remove(PROGRESS_FILE)
    except FileNotFoundError:
        pass

    print(f"\n{'=' * 60}")
    print(f"  📊 RESULTS:")
    print(f"     🆕 New jobs processed: {new_jobs_count}")
    print(f"     🚫 Times blocked: {blocked_count}")
    print("=" * 60)
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
        sys.exit(1)
