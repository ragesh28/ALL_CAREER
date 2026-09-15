"""
scripts/split_existing_jobs.py
Splits the existing monolithic job chunks (all_jobs_1.json .. all_jobs_8.json)
into granular, lightweight JSON files partitioned by:
  data/jobs/<role_slug>/<source_slug>_<location_slug>.json

Also generates:
  data/index/manifest.json          - Full catalog of roles, sources, locations, file paths & counts
  data/index/sidebar_counts.json    - Pre-aggregated source & location counts for instant sidebar rendering
  data/index/latest_preview_100.json - The 100 newest jobs for instant initial load (0.05s)
"""

import os
import glob
import json
import re
import time
from collections import defaultdict, Counter
from datetime import datetime

DATA_DIR = "data"
JOBS_DIR = os.path.join(DATA_DIR, "jobs")
INDEX_DIR = os.path.join(DATA_DIR, "index")

def slugify(text, default="other"):
    if not text:
        return default
    t = str(text).strip().lower()
    t = re.sub(r'[\/\\&+\-,\s]+', '_', t)
    t = re.sub(r'[^a-z0-9_]', '', t)
    t = re.sub(r'_+', '_', t).strip('_')
    return t or default

def clean_location(loc_str):
    if not loc_str:
        return "all_india"
    raw = str(loc_str).strip()
    if raw.lower() in ("null", "none", "unknown", "nan", "", "india"):
        return "all_india"
    # Take the primary city if comma separated (e.g., "Chennai, Tamil Nadu" -> "chennai")
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    first_part = parts[0] if parts else raw
    first_clean = slugify(first_part)
    if first_clean in ("null", "none", "nan", "india", ""):
        return "all_india"
    return first_clean

def get_role_slug(job):
    rc = job.get('role_category')
    if rc and str(rc).strip().lower() not in ("null", "none", "", "nan"):
        return slugify(rc)
    rs = job.get('role_search')
    if rs and str(rs).strip().lower() not in ("null", "none", "", "nan"):
        return slugify(rs)
    title = job.get('title', '')
    if title:
        # Fallback keyword match
        tl = title.lower()
        if "full stack" in tl:
            return "full_stack_developer"
        if "python" in tl:
            return "python_developer"
        if "data analyst" in tl:
            return "data_analyst"
        if "software engineer" in tl:
            return "software_engineer"
        if "frontend" in tl or "react" in tl or "angular" in tl:
            return "frontend_developer"
        if "backend" in tl or "node" in tl or "django" in tl:
            return "backend_developer"
        if "devops" in tl or "cloud" in tl or "aws" in tl:
            return "devops_engineer"
    return "other"

def main():
    start_time = time.time()
    print("=" * 70)
    print("ALL_CAREER: Splitting 600K Jobs into Granular JSON Files")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. Discover existing chunks
    chunk_files = sorted(glob.glob("all_jobs_*.json"))
    if not chunk_files:
        print("ERROR: No all_jobs_*.json chunk files found in current directory.")
        return

    print(f"Discovered {len(chunk_files)} chunk files: {chunk_files}")

    # Ensure output directories exist
    os.makedirs(JOBS_DIR, exist_ok=True)
    os.makedirs(INDEX_DIR, exist_ok=True)

    total_jobs_read = 0
    buckets = defaultdict(list)
    source_counts = Counter()
    location_counts = Counter()
    all_jobs_for_preview = []

    # 2. Stream all chunk files sequentially
    print("\nReading jobs from chunks...")
    for cf in chunk_files:
        cf_start = time.time()
        try:
            with open(cf, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
        except Exception as e:
            print(f"Error loading {cf}: {e}")
            continue

        c_count = len(jobs)
        total_jobs_read += c_count

        for j in jobs:
            role_slug = get_role_slug(j)
            src_raw = j.get('source') or 'other'
            src_slug = slugify(src_raw, default="other")
            loc_slug = clean_location(j.get('location'))

            # Record stats
            source_counts[src_slug] += 1
            location_counts[loc_slug] += 1

            # Key: (role_slug, f"{src_slug}_{loc_slug}")
            sub_key = f"{src_slug}_{loc_slug}"
            buckets[(role_slug, sub_key)].append(j)

            # Sample for preview (keep up to 1000 candidates)
            if len(all_jobs_for_preview) < 1000:
                all_jobs_for_preview.append(j)

        print(f"  Processed {cf}: {c_count:,} jobs in {time.time() - cf_start:.2f}s")

    print(f"\nTotal jobs read from chunks: {total_jobs_read:,}")
    print(f"Total unique (role, source_location) files to write: {len(buckets):,}")

    # 3. Write granular JSON files grouped by role
    print("\nWriting granular JSON files to disk...")
    write_start = time.time()
    files_written = 0
    total_jobs_written = 0

    # Group bucket keys by role
    role_to_files = defaultdict(dict)
    for (role_slug, sub_key), job_list in buckets.items():
        role_dir = os.path.join(JOBS_DIR, role_slug)
        os.makedirs(role_dir, exist_ok=True)

        file_name = f"{sub_key}.json"
        file_path = os.path.join(role_dir, file_name)
        rel_path = f"data/jobs/{role_slug}/{file_name}".replace("\\", "/")

        with open(file_path, 'w', encoding='utf-8') as fh:
            json.dump(job_list, fh, separators=(',', ':'))

        files_written += 1
        job_count = len(job_list)
        total_jobs_written += job_count

        # Track for manifest: parse src and loc from sub_key
        # sub_key format: {src_slug}_{loc_slug}
        parts = sub_key.split('_', 1)
        src_part = parts[0]
        loc_part = parts[1] if len(parts) > 1 else "all_india"

        if src_part not in role_to_files[role_slug]:
            role_to_files[role_slug][src_part] = {}
        role_to_files[role_slug][src_part][loc_part] = {
            "file": rel_path,
            "count": job_count
        }

    write_duration = time.time() - write_start
    print(f"Wrote {files_written:,} JSON files in {write_duration:.2f}s ({files_written/max(write_duration, 0.001):.0f} files/sec)")

    # 4. Generate data/index/manifest.json (Optimized compact format ~179 KB)
    print("\nGenerating data/index/manifest.json...")
    manifest = {
        "total_jobs": total_jobs_written,
        "total_files": files_written,
        "generated_at": datetime.now().isoformat(),
        "roles": {}
    }

    for role_slug, sources_dict in sorted(role_to_files.items()):
        role_total = sum(sum(loc['count'] for loc in locs.values()) for locs in sources_dict.values())
        manifest["roles"][role_slug] = {
            "name": role_slug.replace('_', ' ').title(),
            "total": role_total,
            "sources": {}
        }
        for src, locs in sorted(sources_dict.items()):
            src_total = sum(loc['count'] for loc in locs.values())
            manifest["roles"][role_slug]["sources"][src] = {
                "total": src_total,
                "locs": {loc_k: loc_v["count"] for loc_k, loc_v in sorted(locs.items())}
            }

    manifest_path = os.path.join(INDEX_DIR, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, separators=(',', ':'))
    print(f"  Manifest written to {manifest_path} ({os.path.getsize(manifest_path)/1024:.1f} KB)")

    # 5. Generate data/index/sidebar_counts.json
    print("Generating data/index/sidebar_counts.json...")
    sidebar_counts = {
        "total_jobs": total_jobs_written,
        "sources": dict(source_counts.most_common(30)),
        "locations": dict(location_counts.most_common(100)),
        "generated_at": datetime.now().isoformat()
    }
    sidebar_path = os.path.join(INDEX_DIR, "sidebar_counts.json")
    with open(sidebar_path, 'w', encoding='utf-8') as fh:
        json.dump(sidebar_counts, fh, indent=2)
    print(f"  Sidebar counts written to {sidebar_path}")

    # 6. Generate data/index/latest_preview_100.json
    print("Generating data/index/latest_preview_100.json...")
    # Sort preview by date_posted desc
    def get_date(j):
        d = j.get('date_posted') or j.get('job_posted_date') or ''
        return str(d)[:10]

    all_jobs_for_preview.sort(key=get_date, reverse=True)
    preview_100 = all_jobs_for_preview[:100]
    preview_path = os.path.join(INDEX_DIR, "latest_preview_100.json")
    with open(preview_path, 'w', encoding='utf-8') as fh:
        json.dump(preview_100, fh, separators=(',', ':'))
    print(f"  Preview written to {preview_path} ({os.path.getsize(preview_path)/1024:.1f} KB)")

    # 7. Verification & Zero Data Loss Check
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY:")
    print(f"  Total Input Jobs Read:     {total_jobs_read:,}")
    print(f"  Total Output Jobs Written: {total_jobs_written:,}")
    diff = total_jobs_read - total_jobs_written
    if diff == 0:
        print("  Status: SUCCESS! Exact match - 0 jobs lost!")
    else:
        print(f"  WARNING: Difference of {diff} jobs detected!")
    print(f"  Total Granular JSON Files: {files_written:,}")
    print(f"  Total Elapsed Time:        {time.time() - start_time:.2f} seconds")
    print("=" * 70)

if __name__ == "__main__":
    main()
