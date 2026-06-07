"""
DIRECT LINKS SCRAPER — GitHub Actions Version
Scrapes 150 top companies via JobSpy → gets direct apply URLs → stores in Turso.

Features:
- Scrapes all companies with linkedin_fetch_description=True (gets job_url_direct)
- Stores ONLY jobs with direct apply links (skips Easy Apply)
- Handles LinkedIn blocks: waits 1 minute then retries (new IP from GitHub Actions)
- Turso DB storage via HTTP API (no local JSON files needed)
- 10-day retention: auto-deletes jobs older than 10 days

Usage (local):   py -3.11 scrape_direct_links.py --test 3
Usage (GitHub):  python scrape_direct_links.py
"""

import os
import sys
import time
import json
import requests
import traceback
from datetime import datetime, timedelta

import pandas as pd

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TURSO_URL = os.environ.get("TURSO_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "")

BATCH_SIZE = 50
COOLDOWN_SECONDS = 60     # 1 minute wait on block (GitHub gives new IP)
MAX_RETRIES = 3
RESULTS_PER_SEARCH = 50
KEEP_DAYS = 20            # Delete jobs older than 20 days

START_TIME = time.time()
MAX_RUN_SECONDS = 5 * 3600 + 50 * 60  # 5 hours 50 minutes (safe margin)

LOCATIONS = [
    "Bangalore, India",
    "Chennai, India",
    "Hyderabad, India",
    "Mumbai, India",
    "Delhi, India",
    "Pune, India",
]

# 150 Top Companies
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

# Deduplicate
seen = set()
UNIQUE_COMPANIES = []
for c in TOP_COMPANIES:
    if c not in seen:
        seen.add(c)
        UNIQUE_COMPANIES.append(c)
TOP_COMPANIES = UNIQUE_COMPANIES


# ---------------------------------------------------------------------------
# TURSO DB HELPERS
# ---------------------------------------------------------------------------
def turso_execute(statements):
    pass

def setup_database():
    pass

import storage
def store_jobs_batch(jobs):
    for j in jobs:
        if "url" not in j:
            j["url"] = j.get("direct_url") or j.get("linkedin_url")
    return storage.store_jobs_batch(jobs)

def cleanup_old_jobs():
    pass

def get_total_jobs():
    return 0


# ---------------------------------------------------------------------------
# SCRAPING
# ---------------------------------------------------------------------------
def is_linkedin_block(error):
    """Check if error indicates LinkedIn block."""
    error_str = str(error).lower()
    indicators = [
        "429", "too many requests", "rate limit", "blocked",
        "captcha", "forbidden", "access denied", "authwall",
        "connectionerror", "connection reset", "timeout",
        "max retries exceeded",
    ]
    return any(ind in error_str for ind in indicators)


def scrape_company(company_name, locations):
    """Scrape one company across all locations. Returns (direct_jobs, was_blocked)."""
    from jobspy import scrape_jobs

    direct_jobs = []
    fetched_at = datetime.now().strftime("%Y-%m-%d")

    for location in locations:
        try:
            print(f"   📍 {location}...", end=" ", flush=True)
            jobs_df = scrape_jobs(
                site_name=["linkedin"],
                search_term=company_name,
                location=location,
                results_wanted=RESULTS_PER_SEARCH,
                country_indeed="India",
                hours_old=24,
                linkedin_fetch_description=True,  # Gets job_url_direct!
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
                direct_url = str(row.get("job_url_direct", ""))
                if direct_url in ("", "nan", "None"):
                    continue  # Skip — no direct link

                direct_jobs.append({
                    "title": str(row.get("title", "Unknown")),
                    "company": str(row.get("company", company_name)),
                    "location": str(row.get("location", location.split(",")[0])),
                    "date_posted": str(row.get("date_posted", "")),
                    "linkedin_url": str(row.get("job_url", "")),
                    "direct_url": direct_url,
                    "job_type": str(row.get("job_type", "")),
                    "is_remote": str(row.get("is_remote", "")),
                    "fetched_at": fetched_at,
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


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run(test_limit=None):
    companies = TOP_COMPANIES
    if test_limit:
        companies = companies[:test_limit]
        print(f"\n🧪 TEST MODE: {test_limit} companies only\n")

    total_companies = len(companies)
    print("=" * 60)
    print(f"  DIRECT LINKS SCRAPER ({total_companies} companies → Turso)")
    print("=" * 60)
    print(f"  📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  📍 Locations: {len(LOCATIONS)}")
    print(f"  ⏱️  Block cooldown: {COOLDOWN_SECONDS}s")
    print(f"  📆 Retention: {KEEP_DAYS} days")
    print("=" * 60)

    # Setup DB
    if not setup_database():
        print("❌ Failed to setup database. Exiting.")
        sys.exit(1)

    # Clean old jobs first
    cleanup_old_jobs()
    print(f"📊 Current jobs in DB: {get_total_jobs()}")

    total_inserted = 0
    blocked_count = 0

    for i, company in enumerate(companies):
        # Time limit check
        elapsed = time.time() - START_TIME
        if elapsed >= MAX_RUN_SECONDS:
            print(f"\n⏰ TIME LIMIT ({int(elapsed/60)} min). Stopping gracefully.")
            break

        print(f"\n[{i+1}/{total_companies}] 🏢 {company}")

        retries = 0
        while retries <= MAX_RETRIES:
            company_jobs, was_blocked = scrape_company(company, LOCATIONS)

            # Store whatever we got
            if company_jobs:
                inserted = store_jobs_batch(company_jobs)
                total_inserted += inserted
                print(f"   💾 Stored {inserted} new direct-link jobs")

            if was_blocked:
                blocked_count += 1
                retries += 1
                if retries <= MAX_RETRIES:
                    print(f"\n⏳ Blocked! Waiting {COOLDOWN_SECONDS}s... (retry {retries}/{MAX_RETRIES})")
                    time.sleep(COOLDOWN_SECONDS)
                else:
                    print(f"   ❌ Max retries for {company}. Moving on.")
            else:
                break

        # Batch transitions
        if (i + 1) % BATCH_SIZE == 0 and i > 0:
            print(f"\n{'─' * 50}")
            print(f"  📊 Batch checkpoint: {total_inserted} new jobs so far")
            print(f"  📦 Total in DB: {get_total_jobs()}")
            print(f"{'─' * 50}")
            time.sleep(3)

    # Final summary
    final_total = get_total_jobs()
    print(f"\n{'=' * 60}")
    print(f"  📊 RESULTS:")
    print(f"     🆕 New direct-link jobs inserted: {total_inserted}")
    print(f"     📦 Total jobs in Turso: {final_total}")
    print(f"     🚫 Times blocked: {blocked_count}")
    print(f"{'=' * 60}")
    print(f"\n✅ DONE!")


if __name__ == "__main__":
    # Local testing fallback
    if not TURSO_URL:
        TURSO_URL = "https://jobsdata-ragesh.aws-ap-south-1.turso.io"
    if not TURSO_TOKEN:
        TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE3NzM5MDA3MDAsImlhdCI6MTc3MzI5NTkwMCwiaWQiOiIwMTljZTBhYi0xZDAxLTczMGMtYTBiNS01ZWU0ZGMxZDA4ZDgiLCJyaWQiOiIwY2NlZjMxYy1lMWM3LTQwMzctODA3YS1iMWNkODJmNGQ0YTYifQ.HtmuTZP3oqCa22fOJBPneLQDzmg8G45VXtqpZ0SK4ffxryf371ohb5ir88TXjmgjjGUGwcclBEWt7t81AD0yBg"

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
