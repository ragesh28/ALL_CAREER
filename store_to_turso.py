"""
Scrape Google jobs with direct apply links and store in Turso database.
Uses JobSpy (linkedin_fetch_description=True) → filters to direct links only → stores in Turso.

Usage: py -3.11 store_to_turso.py
"""

import json
import requests
from datetime import datetime
from jobspy import scrape_jobs


# ---- TURSO CONFIG ----
TURSO_URL = "https://jobsdata-ragesh.aws-ap-south-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE3NzM5MDA3MDAsImlhdCI6MTc3MzI5NTkwMCwiaWQiOiIwMTljZTBhYi0xZDAxLTczMGMtYTBiNS01ZWU0ZGMxZDA4ZDgiLCJyaWQiOiIwY2NlZjMxYy1lMWM3LTQwMzctODA3YS1iMWNkODJmNGQ0YTYifQ.HtmuTZP3oqCa22fOJBPneLQDzmg8G45VXtqpZ0SK4ffxryf371ohb5ir88TXjmgjjGUGwcclBEWt7t81AD0yBg"

# ---- SCRAPER CONFIG ----
SEARCH_TERM = "Google"
LOCATION = "Bangalore, India"
RESULTS_WANTED = 30
HOURS_OLD = 168  # 7 days


def turso_execute(statements):
    """Execute SQL statements via Turso HTTP API pipeline."""
    url = f"{TURSO_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json",
    }

    # Build pipeline requests
    requests_body = []
    for stmt in statements:
        if isinstance(stmt, str):
            requests_body.append({"type": "execute", "stmt": {"sql": stmt}})
        elif isinstance(stmt, dict):
            requests_body.append({"type": "execute", "stmt": stmt})

    # Close the stream
    requests_body.append({"type": "close"})

    payload = {"requests": requests_body}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)

    if resp.status_code != 200:
        print(f"❌ Turso API error {resp.status_code}: {resp.text[:300]}")
        return None

    return resp.json()


def create_table():
    """Create the jobs table in Turso if it doesn't exist."""
    print("📦 Creating jobs table in Turso...")

    sql = """
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT,
        date_posted TEXT,
        linkedin_url TEXT,
        direct_url TEXT NOT NULL,
        job_type TEXT,
        is_remote TEXT,
        fetched_at TEXT NOT NULL,
        UNIQUE(direct_url)
    )
    """
    result = turso_execute([sql])
    if result:
        print("✅ Table ready!")
    return result


def get_google_jobs():
    """Use JobSpy to get Google jobs with direct apply URLs."""
    print(f"\n🔍 Searching LinkedIn for '{SEARCH_TERM}' jobs...")
    print(f"   Location: {LOCATION}")
    print(f"   linkedin_fetch_description=True\n")

    jobs = scrape_jobs(
        site_name=["linkedin"],
        search_term=SEARCH_TERM,
        location=LOCATION,
        results_wanted=RESULTS_WANTED,
        country_indeed="India",
        hours_old=HOURS_OLD,
        linkedin_fetch_description=True,
        verbose=1,
    )

    if jobs.empty:
        print("❌ No jobs found.")
        return []

    print(f"\n📋 Total LinkedIn results: {len(jobs)}")

    # Filter to Google company
    google_jobs = jobs[jobs["company"].str.lower().str.contains("google", na=False)]
    google_jobs = google_jobs.drop_duplicates(subset=["job_url"], keep="first")
    print(f"🏢 Google jobs: {len(google_jobs)}")

    # Build results — ONLY keep jobs with direct URLs
    results = []
    for _, row in google_jobs.iterrows():
        direct_url = str(row.get("job_url_direct", ""))
        if direct_url in ("", "nan", "None"):
            continue  # Skip — no direct link

        results.append({
            "title": str(row.get("title", "Unknown")),
            "company": str(row.get("company", SEARCH_TERM)),
            "location": str(row.get("location", "")),
            "date_posted": str(row.get("date_posted", "")),
            "linkedin_url": str(row.get("job_url", "")),
            "direct_url": direct_url,
            "job_type": str(row.get("job_type", "")),
            "is_remote": str(row.get("is_remote", "")),
        })

    print(f"🎯 Jobs with direct apply links: {len(results)}")
    return results


def store_jobs(jobs):
    """Store jobs in Turso database."""
    if not jobs:
        print("⚠️ No jobs to store.")
        return

    fetched_at = datetime.now().strftime("%Y-%m-%d")
    print(f"\n💾 Storing {len(jobs)} jobs in Turso...")

    statements = []
    for job in jobs:
        stmt = {
            "sql": """INSERT OR IGNORE INTO jobs
                      (title, company, location, date_posted, linkedin_url, direct_url, job_type, is_remote, fetched_at)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            "args": [
                {"type": "text", "value": job["title"]},
                {"type": "text", "value": job["company"]},
                {"type": "text", "value": job["location"]},
                {"type": "text", "value": job["date_posted"]},
                {"type": "text", "value": job["linkedin_url"]},
                {"type": "text", "value": job["direct_url"]},
                {"type": "text", "value": job["job_type"]},
                {"type": "text", "value": job["is_remote"]},
                {"type": "text", "value": fetched_at},
            ],
        }
        statements.append(stmt)

    result = turso_execute(statements)
    if result:
        # Count how many were inserted
        inserted = 0
        for r in result.get("results", []):
            if r.get("type") == "ok":
                affected = r.get("response", {}).get("result", {}).get("affected_row_count", 0)
                inserted += affected
        print(f"✅ Inserted {inserted} new jobs (duplicates skipped)")
    else:
        print("❌ Failed to store jobs")


def verify_data():
    """Query Turso to verify stored data."""
    print("\n🔎 Verifying data in Turso...")

    result = turso_execute(["SELECT COUNT(*) as total FROM jobs"])
    if result:
        for r in result.get("results", []):
            if r.get("type") == "ok":
                rows = r.get("response", {}).get("result", {}).get("rows", [])
                if rows:
                    total = rows[0][0].get("value", 0)
                    print(f"📊 Total jobs in Turso: {total}")

    # Get the jobs we just stored
    result = turso_execute(["SELECT title, company, direct_url, fetched_at FROM jobs ORDER BY id DESC LIMIT 10"])
    if result:
        print(f"\n{'─' * 60}")
        print(f"  LATEST JOBS IN TURSO:")
        print(f"{'─' * 60}")
        for r in result.get("results", []):
            if r.get("type") == "ok":
                rows = r.get("response", {}).get("result", {}).get("rows", [])
                for i, row in enumerate(rows, 1):
                    title = row[0].get("value", "?")
                    company = row[1].get("value", "?")
                    url = row[2].get("value", "?")
                    date = row[3].get("value", "?")
                    print(f"  {i}. {title}")
                    print(f"     {company} | Fetched: {date}")
                    print(f"     → {url[:80]}")
                    print()


def main():
    print("=" * 60)
    print("  STORE DIRECT-LINK JOBS TO TURSO")
    print("=" * 60)

    # Step 1: Create table
    if not create_table():
        return

    # Step 2: Scrape jobs
    jobs = get_google_jobs()

    # Step 3: Store in Turso
    store_jobs(jobs)

    # Step 4: Verify
    verify_data()

    print(f"\n✅ DONE! Jobs stored in Turso database.")


if __name__ == "__main__":
    main()
