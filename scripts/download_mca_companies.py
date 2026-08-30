"""
Full Paginated Downloader for MCA Company Master Data.
Stores records in local SQLite with FTS5 virtual indexing.
Supports state-by-state downloads and automatic checkpoint resume.

Usage:
    python -m scripts.download_mca_companies
    python -m scripts.download_mca_companies --state TN
    python -m scripts.download_mca_companies --limit 5000 --max-records 50000
    python -m scripts.download_mca_companies --reset
"""
import os
import sys
import json
import time
import signal
import argparse
from pathlib import Path
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from company_db.config import (
    DEFAULT_PROGRESS_PATH,
    DEFAULT_API_LIMIT,
    DATA_SOURCE_DESCRIPTION,
    DATA_SOURCE_DATE,
    get_api_key
)
from company_db.client import DataGovMCAClient
from company_db.database import CompanyDatabase

# Global cancellation flag for graceful exit
_CANCELLED = False


def sigint_handler(signum, frame):
    global _CANCELLED
    print("\n\n🛑 Pause/Cancellation signal received! Saving checkpoint before exit...")
    _CANCELLED = True


signal.signal(signal.SIGINT, sigint_handler)


def load_progress(state_code: str = "ALL") -> dict:
    """Load download progress from checkpoint file."""
    if DEFAULT_PROGRESS_PATH.exists():
        try:
            with open(DEFAULT_PROGRESS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(state_code, {"offset": 0, "total_inserted": 0})
        except Exception:
            pass
    return {"offset": 0, "total_inserted": 0}


def save_progress(state_code: str, offset: int, total_inserted: int):
    """Save download progress to checkpoint file."""
    data = {}
    if DEFAULT_PROGRESS_PATH.exists():
        try:
            with open(DEFAULT_PROGRESS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    data[state_code] = {
        "offset": offset,
        "total_inserted": total_inserted,
        "last_updated": datetime.now().isoformat(),
        "state_code": state_code
    }

    with open(DEFAULT_PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Download MCA Company Master Data into local SQLite DB")
    parser.add_argument("--state", type=str, default=None, help="Filter by State Code (e.g. TN, KA, MH, DL, TS)")
    parser.add_argument("--limit", type=int, default=DEFAULT_API_LIMIT, help=f"Page size (default: {DEFAULT_API_LIMIT})")
    parser.add_argument("--max-records", type=int, default=None, help="Optional ceiling limit for testing")
    parser.add_argument("--reset", action="store_true", help="Reset checkpoint and start from offset 0")
    parser.add_argument("--db-path", type=str, default=None, help="Custom SQLite database file path")
    args = parser.parse_args()

    print("=" * 70)
    print("🚀 MCA COMPANY MASTER DATA DOWNLOADER (data.gov.in → SQLite FTS5)")
    print("=" * 70)
    print(f"ℹ️  Source: {DATA_SOURCE_DESCRIPTION}")
    print(f"📅 Record Cutoff: {DATA_SOURCE_DATE}")
    state_label = args.state.upper() if args.state else "ALL STATES"
    print(f"📍 State Filter: {state_label}")
    print(f"📄 Page Size: {args.limit}")
    print("=" * 70)

    api_key = get_api_key()
    if not api_key:
        print("\n❌ Error: DATA_GOV_API_KEY environment variable is NOT set.")
        print("Please set your API key in environment variables and try again.")
        sys.exit(1)

    client = DataGovMCAClient(api_key=api_key)
    db = CompanyDatabase(db_path=args.db_path)

    # 1. Sanity Test First (10-record fetch)
    print("\n🔍 Running initial 10-record connectivity check...")
    sanity_res = client.test_connection()
    if not sanity_res.get("success"):
        print(f"❌ Sanity check failed: {sanity_res.get('error')}")
        sys.exit(1)

    total_in_gov_catalog = sanity_res.get("total_available_in_catalog", 0)
    print(f"✅ Sanity check passed! Catalog total available: {total_in_gov_catalog:,} records")

    # 2. Checkpoint Resume
    state_key = args.state.upper() if args.state else "ALL"
    if args.reset:
        offset = 0
        total_inserted = 0
        print("🔄 Reset flag active: Starting fresh from offset 0")
    else:
        progress = load_progress(state_key)
        offset = progress.get("offset", 0)
        total_inserted = progress.get("total_inserted", 0)
        if offset > 0:
            print(f"🔁 Resuming previous download at offset: {offset:,} (Previously inserted: {total_inserted:,})")

    start_time = time.time()
    batch_count = 0
    records_this_session = 0

    print("\n📥 Starting Paginated Download Loop...\n")

    while not _CANCELLED:
        page_start = time.time()
        
        try:
            raw_page = client.fetch_page(offset=offset, limit=args.limit, state_code=args.state)
            records, page_total = client.parse_records(raw_page)
        except Exception as e:
            print(f"\n❌ Error fetching offset {offset}: {e}")
            print("💾 Saving current progress checkpoint...")
            save_progress(state_key, offset, total_inserted)
            break

        if not records:
            print("\n🎉 Reached end of available records (0 records returned on page).")
            save_progress(state_key, offset, total_inserted)
            break

        # Batch Upsert into SQLite
        inserted = db.upsert_batch(records)
        total_inserted += inserted
        records_this_session += inserted
        offset += len(records)
        batch_count += 1

        elapsed = time.time() - start_time
        speed = records_this_session / elapsed if elapsed > 0 else 0
        page_elapsed = time.time() - page_start

        print(
            f"  📦 Batch #{batch_count:04d} | Offset: {offset:,} | "
            f"Saved: +{inserted} | Total DB: {total_inserted:,} | "
            f"Speed: {speed:.0f} rec/s | Time: {page_elapsed:.2f}s",
            flush=True
        )

        # Save checkpoint after every batch
        save_progress(state_key, offset, total_inserted)

        # Check maximum records ceiling if set
        if args.max_records and records_this_session >= args.max_records:
            print(f"\n🏁 Reached requested ceiling limit of {args.max_records:,} records.")
            break

        # If fetched records < requested limit, we've reached the final page
        if len(records) < args.limit:
            print("\n🎉 Final page reached! Download complete for this filter.")
            break

    # Summary
    total_elapsed = time.time() - start_time
    stats = db.get_stats()

    print("\n" + "=" * 70)
    print("📊 DOWNLOAD SUMMARY")
    print(f"   ⏱️  Total Elapsed:    {total_elapsed / 60:.2f} minutes")
    print(f"   📥 Records Session:  {records_this_session:,}")
    print(f"   💾 Total Companies:  {stats['total_companies']:,}")
    print(f"   🏷️ Total Aliases:    {stats['total_aliases']:,}")
    print(f"   📁 Database Size:    {stats['db_size_mb']} MB")
    print(f"   🗄️ Database Path:    {stats['db_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
