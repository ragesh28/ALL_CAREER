"""
Extract ONLY Company Names into an Ultra-Compact, Minimalist SQLite Database.
Maximizes storage efficiency and read performance.

Usage:
    python -m scripts.create_compact_company_names_db
"""
import os
import sys
import time
import sqlite3
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SOURCE_DB_PATH = DATA_DIR / "company_master.db"
COMPACT_DB_PATH = DATA_DIR / "company_names.db"


def build_compact_database():
    print("=" * 65)
    print("📦 ULTRA-COMPACT COMPANY NAMES DATABASE GENERATOR")
    print("=" * 65)

    if not SOURCE_DB_PATH.exists():
        print(f"❌ Error: Source database not found at {SOURCE_DB_PATH}")
        return

    source_size_mb = SOURCE_DB_PATH.stat().st_size / (1024 * 1024)
    print(f"🗄️  Source Database: {SOURCE_DB_PATH} ({source_size_mb:.2f} MB)")
    print(f"🎯 Target Database: {COMPACT_DB_PATH}")

    # Remove existing compact DB if present
    if COMPACT_DB_PATH.exists():
        try:
            COMPACT_DB_PATH.unlink()
        except Exception:
            pass

    # Initialize compact target SQLite DB with space-saving pragmas
    dest_conn = sqlite3.connect(str(COMPACT_DB_PATH))
    dest_conn.execute("PRAGMA page_size = 4096;")
    dest_conn.execute("PRAGMA journal_mode = OFF;")
    dest_conn.execute("PRAGMA synchronous = OFF;")
    dest_conn.execute("PRAGMA cache_size = -64000;")
    dest_conn.execute("PRAGMA temp_store = MEMORY;")

    dest_conn.execute("""
    CREATE TABLE companies (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    );
    """)

    # Stream distinct company names in batches from source DB
    src_conn = sqlite3.connect(str(SOURCE_DB_PATH))
    src_conn.row_factory = sqlite3.Row
    src_cursor = src_conn.cursor()

    print("\n⏳ Extracting and writing company names...")
    start_time = time.time()
    batch_size = 50000
    total_count = 0
    seen_names = set()

    src_cursor.execute("SELECT DISTINCT company_name FROM companies WHERE company_name IS NOT NULL AND trim(company_name) != ''")

    batch = []
    while True:
        rows = src_cursor.fetchmany(batch_size)
        if not rows:
            break

        for row in rows:
            raw_name = row[0].strip()
            # De-duplicate in memory if casing differs
            if raw_name.upper() not in seen_names:
                seen_names.add(raw_name.upper())
                total_count += 1
                batch.append((total_count, raw_name))

        if len(batch) >= batch_size:
            dest_conn.executemany("INSERT INTO companies (id, name) VALUES (?, ?)", batch)
            dest_conn.commit()
            elapsed = time.time() - start_time
            print(f"  ⚡ Written: {total_count:,} company names... ({total_count/elapsed:.0f} rec/s)", flush=True)
            batch = []

    # Insert remaining records
    if batch:
        dest_conn.executemany("INSERT INTO companies (id, name) VALUES (?, ?)", batch)
        dest_conn.commit()

    src_conn.close()

    # Create index on name for instant lookups
    print("🔍 Building lightweight index on company name...")
    dest_conn.execute("CREATE INDEX idx_company_name ON companies(name COLLATE NOCASE);")
    dest_conn.commit()

    # VACUUM to eliminate all unused space
    print("🧹 Running VACUUM for maximum disk compaction...")
    dest_conn.execute("VACUUM;")
    dest_conn.close()

    elapsed = time.time() - start_time
    compact_size_mb = COMPACT_DB_PATH.stat().st_size / (1024 * 1024)
    reduction = ((source_size_mb - compact_size_mb) / source_size_mb) * 100

    print("\n" + "=" * 65)
    print("🎉 COMPACT DATABASE CREATION COMPLETE!")
    print(f"   📊 Total Unique Companies: {total_count:,}")
    print(f"   ⏱️  Time Taken:             {elapsed:.1f} seconds")
    print(f"   💾 Original Database Size:  {source_size_mb:.2f} MB ({source_size_mb/1024:.2f} GB)")
    print(f"   📉 Compact Database Size:   {compact_size_mb:.2f} MB ({compact_size_mb/1024:.2f} GB)")
    print(f"   🔥 Space Saved:             {reduction:.1f}% reduction")
    print(f"   📁 Saved File:              {COMPACT_DB_PATH}")
    print("=" * 65)


if __name__ == "__main__":
    build_compact_database()
