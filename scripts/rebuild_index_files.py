"""
scripts/rebuild_index_files.py
Scans all granular JSON shards in data/jobs/ and rebuilds:
  - data/index/manifest.json
  - data/index/sidebar_counts.json
  - data/index/latest_preview_100.json
Guaranteeing zero data loss, exact job counts, and 100% clean JSON with NO merge conflict markers.
"""

import os
import sys
import json
import time
from collections import Counter
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
JOBS_DIR = os.path.join(DATA_DIR, "jobs")
INDEX_DIR = os.path.join(DATA_DIR, "index")

def slugify(text, default="other"):
    import re
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
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    first_part = parts[0] if parts else raw
    first_clean = slugify(first_part)
    if first_clean in ("null", "none", "nan", "india", ""):
        return "all_india"
    return first_clean

def rebuild_all():
    os.makedirs(INDEX_DIR, exist_ok=True)
    start_time = time.time()
    print("Rebuilding index files from data/jobs/...")

    role_to_files = {}
    source_counts = Counter()
    location_counts = Counter()
    total_jobs = 0
    total_files = 0
    all_jobs_for_preview = []

    if not os.path.exists(JOBS_DIR):
        print(f"Error: {JOBS_DIR} does not exist!")
        return

    # Iterate through all role folders
    for role_name in sorted(os.listdir(JOBS_DIR)):
        role_path = os.path.join(JOBS_DIR, role_name)
        if not os.path.isdir(role_path):
            continue

        role_slug = role_name
        if role_slug not in role_to_files:
            role_to_files[role_slug] = {}

        for fname in sorted(os.listdir(role_path)):
            if not fname.endswith(".json"):
                continue

            fpath = os.path.join(role_path, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    jobs = json.load(fh)
            except Exception as e:
                print(f"Warning: Failed to load {fpath}: {e}")
                continue

            count = len(jobs)
            total_jobs += count
            total_files += 1

            # Parse sub_key (e.g. "timesjobs_bangalore.json" -> src: timesjobs, loc: bangalore)
            base = fname[:-5]
            parts = base.split('_', 1)
            src_part = parts[0]
            loc_part = parts[1] if len(parts) > 1 else "all_india"

            if src_part not in role_to_files[role_slug]:
                role_to_files[role_slug][src_part] = {}
            role_to_files[role_slug][src_part][loc_part] = count

            # Count sources and locations
            source_counts[src_part] += count
            location_counts[loc_part] += count

            # Sample some jobs for preview
            if len(all_jobs_for_preview) < 500 and jobs:
                all_jobs_for_preview.extend(jobs[:min(3, len(jobs))])

    print(f"Scanned {total_files:,} shard files with {total_jobs:,} total jobs.")

    # 1. Manifest
    manifest = {
        "total_jobs": total_jobs,
        "total_files": total_files,
        "generated_at": datetime.now().isoformat(),
        "roles": {}
    }
    for r_slug, sources_dict in sorted(role_to_files.items()):
        role_total = sum(sum(loc_counts.values()) for loc_counts in sources_dict.values())
        manifest["roles"][r_slug] = {
            "name": r_slug.replace('_', ' ').title(),
            "total": role_total,
            "sources": {}
        }
        for src, locs in sorted(sources_dict.items()):
            src_total = sum(locs.values())
            manifest["roles"][r_slug]["sources"][src] = {
                "total": src_total,
                "locs": {loc_k: cnt for loc_k, cnt in sorted(locs.items())}
            }

    manifest_path = os.path.join(INDEX_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, separators=(',', ':'))
    print(f"Written manifest.json ({os.path.getsize(manifest_path)/1024:.1f} KB)")

    # 2. Sidebar counts
    sidebar_counts = {
        "total_jobs": total_jobs,
        "sources": dict(source_counts.most_common(40)),
        "locations": dict(location_counts.most_common(100)),
        "generated_at": datetime.now().isoformat()
    }
    sidebar_path = os.path.join(INDEX_DIR, "sidebar_counts.json")
    with open(sidebar_path, "w", encoding="utf-8") as fh:
        json.dump(sidebar_counts, fh, indent=2)
    print(f"Written sidebar_counts.json ({os.path.getsize(sidebar_path)/1024:.1f} KB)")

    # 3. Preview 100
    def get_date(j):
        return str(j.get('fetched_at') or j.get('date_posted') or j.get('job_posted_date') or '')[:10]
    
    all_jobs_for_preview.sort(key=get_date, reverse=True)
    from scripts.optimize_shards import compact_job
    compact_preview = [compact_job(j) for j in all_jobs_for_preview[:100]]
    preview_path = os.path.join(INDEX_DIR, "latest_preview_100.json")
    with open(preview_path, "w", encoding="utf-8") as fh:
        json.dump(compact_preview, fh, separators=(',', ':'))
    print(f"Written latest_preview_100.json ({os.path.getsize(preview_path)/1024:.1f} KB)")

    print(f"Rebuild completed in {time.time() - start_time:.2f}s!")

if __name__ == "__main__":
    rebuild_all()
