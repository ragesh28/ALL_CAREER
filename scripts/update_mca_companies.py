"""
Periodic MCA Company Database Updater.
Synchronizes fresh records from data.gov.in into the local SQLite database
using CIN-based upserts.

Usage:
    python -m scripts.update_mca_companies
    python -m scripts.update_mca_companies --state TN
"""
import os
import sys
import time
import argparse
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from company_db.config import DEFAULT_API_LIMIT, get_api_key
from company_db.client import DataGovMCAClient
from company_db.database import CompanyDatabase


def main():
    parser = argparse.ArgumentParser(description="Synchronize/Update MCA Company Database from data.gov.in")
    parser.add_argument("--state", type=str, default=None, help="Optional State Code filter")
    parser.add_argument("--limit", type=int, default=DEFAULT_API_LIMIT, help="Page size")
    parser.add_argument("--db-path", type=str, default=None, help="Custom SQLite DB path")
    args = parser.parse_args()

    print("=" * 70)
    print("🔄 MCA COMPANY MASTER DATA — PERIODIC SYNCHRONIZATION")
    print("=" * 70)

    api_key = get_api_key()
    if not api_key:
        print("❌ Error: DATA_GOV_API_KEY environment variable is not set.")
        sys.exit(1)

    client = DataGovMCAClient(api_key=api_key)
    db = CompanyDatabase(db_path=args.db_path)

    initial_stats = db.get_stats()
    print(f"📊 Starting Database Records: {initial_stats['total_companies']:,}")

    offset = 0
    updated_total = 0
    start_time = time.time()

    while True:
        try:
            raw_page = client.fetch_page(offset=offset, limit=args.limit, state_code=args.state)
            records, total_count = client.parse_records(raw_page)
        except Exception as e:
            print(f"❌ Error during update fetch (offset {offset}): {e}")
            break

        if not records:
            break

        inserted = db.upsert_batch(records)
        updated_total += inserted
        offset += len(records)

        print(f"  🔄 Processed offset: {offset:,} (+{inserted} upserted)...", flush=True)

        if len(records) < args.limit:
            break

    elapsed = time.time() - start_time
    final_stats = db.get_stats()

    print("\n" + "=" * 70)
    print("✅ SYNCHRONIZATION COMPLETE")
    print(f"   ⏱️  Time Elapsed:     {elapsed / 60:.2f} minutes")
    print(f"   📥 Records Processed: {updated_total:,}")
    print(f"   💾 Final Total Rows:  {final_stats['total_companies']:,}")
    print(f"   📁 Database Size:     {final_stats['db_size_mb']} MB")
    print("=" * 70)


if __name__ == "__main__":
    main()
