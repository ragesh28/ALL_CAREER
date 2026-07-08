"""
Remove LinkedIn Jobs — strips all LinkedIn-sourced jobs from all_jobs_*.json chunks
and rebuilds the chunk files + role index cleanly.

Usage: python remove_linkedin_jobs.py
"""

import os
import json
import sys
import glob
import re
import shutil

sys.stdout.reconfigure(encoding='utf-8')

import storage
import role_classifier


def run():
    print("=" * 60)
    print("  REMOVE LINKEDIN JOBS")
    print("=" * 60)
    sys.stdout.flush()

    # 1. Find and load all chunk files
    chunk_files = storage.get_all_chunk_files()
    print(f"Found {len(chunk_files)} chunk files: {chunk_files}")
    sys.stdout.flush()

    if not chunk_files:
        print("No chunk files found. Nothing to do.")
        return

    all_jobs = []
    for f in chunk_files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                all_jobs.extend(json.load(fh))
        except Exception as e:
            print(f"Error loading {f}: {e}")

    total_loaded = len(all_jobs)
    print(f"Total jobs loaded: {total_loaded}")
    sys.stdout.flush()

    # 2. Filter out LinkedIn jobs ONLY
    kept_jobs = []
    removed_count = 0

    for j in all_jobs:
        source = str(j.get("source", "") or j.get("platform", "") or "").lower().strip()
        job_url = str(j.get("url", "") or j.get("apply_link", "") or j.get("linkedin_url", "") or "").lower()

        is_linkedin = False

        # Check source field
        if source == "linkedin":
            is_linkedin = True

        # Check URL for linkedin.com
        if "linkedin.com" in job_url:
            is_linkedin = True

        if is_linkedin:
            removed_count += 1
        else:
            kept_jobs.append(j)

    print(f"\n{'=' * 40}")
    print(f"  LinkedIn jobs removed : {removed_count}")
    print(f"  Other jobs kept       : {len(kept_jobs)}")
    print(f"{'=' * 40}")
    sys.stdout.flush()

    if removed_count == 0:
        print("No LinkedIn jobs found. Nothing to remove.")
        return

    # 3. Remove old chunk files from disk
    for f in chunk_files:
        try:
            os.remove(f)
            print(f"  Deleted old chunk: {f}")
        except Exception as e:
            print(f"  Error removing {f}: {e}")

    # 4. Rebuild chunk files
    current_chunk = 1
    current_chunk_data = []
    current_chunk_bytes = 2  # '[]'

    for j in kept_jobs:
        j_str = json.dumps(j, separators=(',', ':'))
        j_bytes = len(j_str.encode('utf-8'))

        comma_overhead = 1 if current_chunk_data else 0
        if current_chunk_bytes + j_bytes + comma_overhead > storage.MAX_FILE_SIZE:
            chunk_file = f"all_jobs_{current_chunk}.json"
            with open(chunk_file, 'w', encoding='utf-8') as fh:
                json.dump(current_chunk_data, fh, separators=(',', ':'))
            print(f"  Wrote {chunk_file} ({len(current_chunk_data)} jobs)")

            current_chunk += 1
            current_chunk_data = [j]
            current_chunk_bytes = 2 + j_bytes
        else:
            current_chunk_data.append(j)
            current_chunk_bytes += j_bytes + comma_overhead

    if current_chunk_data:
        chunk_file = f"all_jobs_{current_chunk}.json"
        with open(chunk_file, 'w', encoding='utf-8') as fh:
            json.dump(current_chunk_data, fh, separators=(',', ':'))
        print(f"  Wrote {chunk_file} ({len(current_chunk_data)} jobs)")

    # 5. Rebuild role_index.json and jobs_by_role/
    from collections import Counter
    category_counts = Counter()
    for j in kept_jobs:
        cat = j.get('role_category') or role_classifier.classify_job(j)
        j['role_category'] = cat
        category_counts[cat] += 1

    with open("role_index.json", 'w', encoding='utf-8') as fh:
        json.dump(dict(category_counts), fh, indent=2)
    print("  Wrote role_index.json")

    output_dir = "jobs_by_role"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    grouped_jobs = {}
    for j in kept_jobs:
        cat = j.get('role_category') or 'Other'
        if cat not in grouped_jobs:
            grouped_jobs[cat] = []
        grouped_jobs[cat].append(j)

    for cat, jobs in grouped_jobs.items():
        filename = storage.get_category_filename(cat)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as fh:
            json.dump(jobs, fh, separators=(',', ':'))

    print(f"  Wrote {len(grouped_jobs)} role files in {output_dir}/")

    print(f"\n{'=' * 60}")
    print(f"  ✅ DONE! Removed {removed_count} LinkedIn jobs.")
    print(f"     Remaining jobs: {len(kept_jobs)}")
    print(f"{'=' * 60}")
    sys.stdout.flush()


if __name__ == "__main__":
    run()
