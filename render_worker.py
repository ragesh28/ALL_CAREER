"""
Render Background Worker — Daily Job Scraper Scheduler
Runs both scrapers (Google Jobs + Big Company) on a daily schedule.
This stays alive 24/7 as a Render Background Worker (750 free hrs/month).
"""

import os
import sys
import time
import subprocess
import schedule
from datetime import datetime

def run_google_scraper():
    """Run the Google Jobs scraper."""
    print(f"\n{'='*60}")
    print(f"  🚀 STARTING GOOGLE JOBS SCRAPER — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    try:
        result = subprocess.run(
            [sys.executable, "scrape_google_jobs.py"],
            timeout=6 * 3600,  # 6 hour max
            capture_output=False
        )
        print(f"\n✅ Google Jobs Scraper finished with exit code: {result.returncode}")
    except subprocess.TimeoutExpired:
        print("\n⏰ Google Jobs Scraper hit 6-hour time limit")
    except Exception as e:
        print(f"\n❌ Google Jobs Scraper error: {e}")

def run_big_company_scraper():
    """Run the Big Company scraper."""
    print(f"\n{'='*60}")
    print(f"  🚀 STARTING BIG COMPANY SCRAPER — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    try:
        result = subprocess.run(
            [sys.executable, "step3_big_company_scrape.py"],
            timeout=6 * 3600,  # 6 hour max
            capture_output=False
        )
        print(f"\n✅ Big Company Scraper finished with exit code: {result.returncode}")
    except subprocess.TimeoutExpired:
        print("\n⏰ Big Company Scraper hit 6-hour time limit")
    except Exception as e:
        print(f"\n❌ Big Company Scraper error: {e}")

def main():
    print("=" * 60)
    print("  🏭 RENDER BACKGROUND WORKER — Job Scraper Scheduler")
    print("=" * 60)
    print(f"  📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🕐 Google Jobs Scraper: Daily at 03:00 AM IST (21:30 UTC)")
    print(f"  🕐 Big Company Scraper: Daily at 07:00 AM IST (01:30 UTC)")
    print("=" * 60)

    # Schedule: Google Jobs at 21:30 UTC (3:00 AM IST)
    schedule.every().day.at("21:30").do(run_google_scraper)

    # Schedule: Big Company at 01:30 UTC (7:00 AM IST)
    schedule.every().day.at("01:30").do(run_big_company_scraper)

    # Run both once on startup so you can verify they work
    print("\n🔄 Running both scrapers once on startup for verification...\n")
    run_big_company_scraper()
    run_google_scraper()

    print("\n⏳ Scheduler is now running. Waiting for next scheduled time...\n")

    # Keep alive forever
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
