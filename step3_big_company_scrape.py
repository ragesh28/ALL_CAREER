"""
STEP 3: Big Company Job Scraper (150 Top Companies)
Uses JobSpy to scrape INDEED ONLY for job listings across multiple Indian cities.
Gets ORIGINAL DIRECT APPLY LINKS (company career page URLs via job_url_direct).

Features:
- Scrapes 150 top companies from Indeed (India)
- Uses job_url_direct for original company apply links
- Falls back to Indeed URL if no direct link available
- Processes in batches of 50 companies (fresh session per batch)
- Indeed block detection with 1-minute cooldown + auto-resume
- Stores to Turso DB with deduplication via UNIQUE(url)
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
COOLDOWN_SECONDS = 60       # 1 minute wait on block
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

CLOUDFLARE_URL = os.environ.get("CLOUDFLARE_D1_URL", "https://api.cloudflare.com/client/v4/accounts/62eacb67a7ee0b199f58ccb540a3eff7/d1/database/20b71b5c-c070-45b5-9542-27ed1cad89e5/query")
CLOUDFLARE_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")

def d1_execute(sql, params=None):
    if not CLOUDFLARE_URL or not CLOUDFLARE_TOKEN:
        print("  [WARN] Cloudflare D1 not configured, skipping DB storage")
        return None

    import requests
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_TOKEN}",
        "Content-Type": "application/json",
    }
    body = {"sql": sql}
    if params:
        body["params"] = params

    try:
        resp = requests.post(CLOUDFLARE_URL, headers=headers, json=body, timeout=30)
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        print(f"  [ERR] D1 connection error: {e}")
        return None

def setup_database():
    print("  Setting up D1 database (big_company_jobs table)...")
    d1_execute("""
        CREATE TABLE IF NOT EXISTS big_company_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            location TEXT,
            role TEXT NOT NULL,
            job_posted_date TEXT,
            apply_link TEXT NOT NULL,
            UNIQUE(apply_link)
        )
    """)

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
        print(f"  Cleaned {removed} jobs older than {cutoff}")
    return jobs


def save_jobs(all_jobs):
    """Save jobs directly to D1 big_company_jobs table."""
    if not all_jobs:
        return 0

    all_jobs = clean_old_jobs(all_jobs)

    # 1. Fetch existing jobs natively from Cloudflare worker for strictly pure python deduplication
    existing_urls = set()
    try:
        import requests
        print("  [Deduplication] Fetching existing records from Cloudflare D1 API...")
        resp = requests.get("https://all-career-api.ragesh-jobs.workers.dev/api/big_company_jobs", timeout=20)
        if resp.status_code == 200:
            existing_jobs = resp.json()
            existing_urls = {str(j.get("url", "")) for j in existing_jobs if j.get("url")}
    except Exception as e:
        print(f"  [WARN] Failed to quickly fetch D1 existing jobs: {e}")

    # 2. Deduplicate strictly in Python memory (ignoring D1 matches and internal duplicates)
    new_jobs = []
    seen_local_urls = set()
    for job in all_jobs:
        u = str(job.get("url", ""))
        # Ignore if it exists already in Cloudflare, OR if we already saw it in this exact batch repeatedly!
        if u and u not in existing_urls and u not in seen_local_urls:
            new_jobs.append(job)
            seen_local_urls.add(u)
            
    skipped = len(all_jobs) - len(new_jobs)
    if skipped > 0:
        print(f"  [Deduplication] Skipped {skipped} duplicate job URLs (either already in D1 or duplicate across cities).")

    if not new_jobs:
        print(f"  -> Inserted 0 new jobs out of {len(all_jobs)} total.")
        return 0

    # 3. Securely batch and insert the truly new UNIQUE jobs
    total_inserted = 0
    for i in range(0, len(new_jobs), 16):
        chunk = new_jobs[i:i+16]
        params = []
        placeholders = []
        for job in chunk:
            placeholders.append("(?, ?, ?, ?, ?)")
            params.extend([
                str(job.get("company", "")),
                str(job.get("location", "")),
                str(job.get("title", "")),
                str(job.get("date", datetime.now().strftime("%Y-%m-%d"))),
                str(job.get("url", ""))
            ])
            
        sql = f"INSERT OR IGNORE INTO big_company_jobs (company_name, location, role, job_posted_date, apply_link) VALUES {','.join(placeholders)}"
        res = d1_execute(sql, params)
        if res and res.get("success"):
            for r in res.get("result", []):
                total_inserted += r.get("meta", {}).get("changes", 0)

    print(f"  -> Inserted {total_inserted} strictly new jobs out of {len(all_jobs)} total parsed.")
    return total_inserted


def is_blocked(error):
    error_str = str(error).lower()
    indicators = [
        "429", "too many requests", "rate limit", "blocked",
        "captcha", "forbidden", "access denied",
        "connectionerror", "connection reset", "timeout",
        "max retries exceeded",
    ]
    return any(ind in error_str for ind in indicators)


def scrape_company(company_name, locations, results_wanted=50, proxy_list=None):
    """
    Scrape jobs for a single company from Indeed ONLY.
    Uses job_url_direct for original company apply links.
    Falls back to Indeed URL if no direct link found.
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
            print(f"   > {location}...", end=" ", flush=True)
            jobs_df = scrape_jobs(
                site_name=["indeed"],           # Indeed ONLY
                search_term=company_name,
                location=location,
                results_wanted=results_wanted,
                country_indeed="India",
                hours_old=72,                   # Last 3 days
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
                # Prefer job_url_direct (original company apply link)
                direct_url = str(row.get("job_url_direct", ""))
                indeed_url = str(row.get("job_url", ""))

                # Use direct link (original company career page) if available
                if direct_url not in ("", "nan", "None"):
                    apply_url = direct_url
                elif indeed_url not in ("", "nan", "None"):
                    apply_url = indeed_url
                else:
                    continue

                all_jobs.append({
                    "company":    str(row.get("company", company_name)),
                    "title":      str(row.get("title", "Unknown")),
                    "url":        apply_url,         # Original company apply link (or Indeed fallback)
                    "indeed_url": indeed_url,         # Keep Indeed URL as reference
                    "location":   str(row.get("location", location.split(",")[0])),
                    "date":       str(row.get("date_posted", "None")),
                    "fetchedAt":  date_stamp,
                    "source":     "indeed",
                })
                count += 1

            print(f"{count} jobs")

        except Exception as e:
            if is_blocked(e):
                print(f"BLOCKED!")
                return all_jobs, True
            else:
                print(f"Error: {str(e)[:80]}")
                continue

    return all_jobs, False


def run(test_limit=None):
    companies = TOP_COMPANIES
    if test_limit:
        companies = companies[:test_limit]
        print(f"\n  TEST MODE: Scraping only {test_limit} companies\n")

    total = len(companies)
    print("=" * 60)
    print(f"  BIG COMPANY SCRAPER ({total} companies via Indeed)")
    print("=" * 60)
    print(f"  Date: {get_date_stamp()}")
    print(f"  Locations: {len(LOCATIONS)}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Cooldown on block: {COOLDOWN_SECONDS}s")
    print(f"  Retention: {KEEP_DAYS} days")
    print(f"  Mode: Indeed -> Original Direct Apply Links")
    print("=" * 60)

    setup_database()

    # Also clean old jobs from DB on startup
    if CLOUDFLARE_URL and CLOUDFLARE_TOKEN:
        cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
        d1_execute("DELETE FROM big_company_jobs WHERE job_posted_date < ?", [cutoff])
        print(f"  Cleaned DB jobs older than {cutoff}")
        
        # Clean up incorrect OpenAI jobs (e.g. from LinkedIn search with general matches)
        d1_execute("DELETE FROM big_company_jobs WHERE company_name = 'OpenAI' AND apply_link NOT LIKE '%openai.com%' AND apply_link NOT LIKE '%greenhouse.io/openai%'")
        print("  Cleaned incorrect OpenAI jobs from D1 DB")

    # Check for resume from previous blocked run
    progress = load_progress()
    start_index = 0
    if progress["date"] == get_date_stamp() and progress["last_completed_index"] >= 0:
        start_index = progress["last_completed_index"] + 1
        if start_index < total:
            print(f"\n  Resuming from company #{start_index + 1}: {companies[start_index]}")
        else:
            print(f"\n  All companies already scraped today!")
            return

    print("  Turso UNIQUE(url) handles deduplication.")

    new_jobs_count = 0
    global_scraped_count = 0
    blocked_count = 0

    for i in range(start_index, total):
        company = companies[i]
        batch_num = (i // BATCH_SIZE) + 1

        # Log batch transitions
        if i > start_index and i % BATCH_SIZE == 0:
            print(f"\n{'_' * 50}")
            print(f"  Starting batch {batch_num}")
            print(f"  Jobs saved so far: {new_jobs_count}")
            print(f"{'_' * 50}\n")
            time.sleep(5)

        print(f"\n[{i + 1}/{total}] {company}")

        # Time limit check
        if is_time_limit_approaching():
            elapsed_min = int((time.time() - START_TIME) / 60)
            print(f"\n  TIME LIMIT ({elapsed_min} min). Saving progress and stopping.")
            save_progress(i - 1)
            print(f"  Progress saved. GitHub Action will restart in 10 minutes.")
            return

        retries = 0
        while retries <= MAX_RETRIES:
            company_jobs, was_blocked = scrape_company(
                company, LOCATIONS, RESULTS_PER_SEARCH
            )

            if company_jobs:
                inserted = save_jobs(company_jobs)
                total_parsed = len(company_jobs)
                inserted_count = inserted if inserted else 0
                new_jobs_count += inserted_count
                global_scraped_count += total_parsed
                print(f"  [{company}] Summary: Scraped {total_parsed} jobs | Added {inserted_count} new jobs")

            if was_blocked:
                blocked_count += 1
                retries += 1

                # Save progress before cooldown
                save_progress(i - 1)

                if retries <= MAX_RETRIES:
                    print(f"\n  Blocked! Waiting {COOLDOWN_SECONDS}s... (retry {retries}/{MAX_RETRIES})")
                    time.sleep(COOLDOWN_SECONDS)
                else:
                    print(f"\n  Max retries for {company}. Moving on.")
                    break
            else:
                save_progress(i)
                break

        # Periodic save every 10 companies
        if (i + 1) % 10 == 0:
            print(f"  Checkpoint: {new_jobs_count} jobs processed")

    # Clean up progress file (all done)
    try:
        os.remove(PROGRESS_FILE)
    except FileNotFoundError:
        pass

    print(f"\n{'=' * 60}")
    print(f"  FINAL SUMMARY (All Companies):")
    print(f"     Total jobs scraped  : {global_scraped_count}")
    print(f"     Total new jobs added: {new_jobs_count}")
    print(f"     Times blocked       : {blocked_count}")
    print("=" * 60)
    print(f"\n  DONE!")


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
        print(f"\n  Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
