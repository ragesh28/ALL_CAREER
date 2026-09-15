"""
scripts/optimize_shards.py
Strips redundant and null keys from all generated JSON shards to reduce
file sizes by 30-60%, making them download and parse even faster.
"""

import os
import glob
import json
import time

JOBS_DIR = os.path.join("data", "jobs")

def compact_job(j):
    # Retain core fields needed for display and interaction
    # Redundant fields: role_category, role_search, platform (known from parent folder/file)
    cleaned = {}
    
    # Priority keys to keep compact
    keep_keys = [
        "title", "company", "location", "date_posted", "url",
        "experience", "skills", "is_walkin", "walkin_date", "walkin_time",
        "telegram_url", "contact_email", "contact_phone", "flyer_image_url",
        "description", "venue"
    ]
    
    for k in keep_keys:
        v = j.get(k)
        if v is None or v == "" or v == "null" or v == "None" or v == "nan" or v == []:
            continue
        cleaned[k] = v

    # If any other non-redundant custom key exists, keep it if non-empty
    for k, v in j.items():
        if k in keep_keys or k in ("role_category", "role_search", "source", "platform", "_id", "fetched_at", "fetchedAt", "job_posted_date", "clean_text"):
            continue
        if v is not None and v != "" and v != "null" and v != "None" and v != "nan" and v != []:
            cleaned[k] = v
            
    return cleaned

def main():
    print("=" * 70)
    print("ALL_CAREER: Compacting Granular JSON Shards for Maximum Speed")
    print("=" * 70)

    start_time = time.time()
    files = glob.glob(os.path.join(JOBS_DIR, "*", "*.json"))
    total_files = len(files)
    print(f"Found {total_files:,} shard files to optimize.")

    if total_files == 0:
        print("No shard files found to optimize. Run scripts/split_existing_jobs.py first.")
        return

    bytes_before = 0
    bytes_after = 0
    processed = 0

    for fpath in files:
        try:
            sz_before = os.path.getsize(fpath)
            bytes_before += sz_before

            with open(fpath, "r", encoding="utf-8") as f:
                jobs = json.load(f)

            compacted = [compact_job(j) for j in jobs]

            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(compacted, f, separators=(',', ':'))

            bytes_after += os.path.getsize(fpath)
            processed += 1

            if processed % 2000 == 0 or processed == total_files:
                print(f"  Processed {processed:,} / {total_files:,} files...")
        except Exception as e:
            print(f"Error optimizing {fpath}: {e}")

    duration = time.time() - start_time
    mb_before = bytes_before / (1024 * 1024)
    mb_after = bytes_after / (1024 * 1024)
    saved_mb = mb_before - mb_after
    pct = (saved_mb / mb_before * 100) if mb_before > 0 else 0

    print("=" * 70)
    print("OPTIMIZATION SUMMARY:")
    print(f"  Total Files Optimized:  {processed:,}")
    print(f"  Size Before:            {mb_before:.2f} MB")
    print(f"  Size After:             {mb_after:.2f} MB")
    print(f"  Bandwidth Saved:        {saved_mb:.2f} MB ({pct:.1f}% reduction!)")
    print(f"  Optimization Time:      {duration:.2f} seconds")
    print("=" * 70)

if __name__ == "__main__":
    main()
