import os
import json
import shutil
import re
import sys
from collections import Counter
import storage
import role_classifier

def run_pipeline():
    print("=== STARTING UNIFIED DATABASE CLEANUP PIPELINE ===")
    sys.stdout.flush()
    
    # 1. Get files and load
    chunk_files = storage.get_all_chunk_files()
    print(f"Found chunk files to clean: {chunk_files}")
    sys.stdout.flush()
    
    # Backup files
    backup_dir = "backup_jobs_before_cleanup"
    os.makedirs(backup_dir, exist_ok=True)
    for f in chunk_files:
        shutil.copy(f, os.path.join(backup_dir, f))
        
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
    
    # 2. Deduplicate, filter garbage, and classify
    seen_urls = set()
    seen_tc_keys = set()
    clean_jobs = []
    
    from datetime import datetime, timedelta
    cutoff_date = (datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d")
    
    stats = Counter()
    category_counts = Counter()
    
    for idx, j in enumerate(all_jobs):
        if not storage.is_valid_job(j):
            stats["invalid_garbage"] += 1
            continue
            
        date_str = storage.get_job_date(j)
        if not date_str:
            stats["missing_date"] += 1
            continue
            
        if len(date_str) >= 10 and date_str[:10] < cutoff_date:
            stats["old_date"] += 1
            continue
            
        url = storage.get_job_url(j)
        if url and url in seen_urls:
            stats["duplicate_url"] += 1
            continue
            
        tc_key = storage.get_job_title_company_key(j)
        if tc_key and tc_key in seen_tc_keys:
            stats["duplicate_tc"] += 1
            continue
            
        # Classify and add role_category
        cat = role_classifier.classify_job(j)
        j['role_category'] = cat
        category_counts[cat] += 1
        
        clean_jobs.append(j)
        if url:
            seen_urls.add(url)
        if tc_key:
            seen_tc_keys.add(tc_key)
        stats["valid"] += 1
        
    print("\nCleanup and Classification Statistics:")
    print(f"  Invalid/Garbage filtered: {stats['invalid_garbage']}")
    print(f"  Missing/Invalid date filtered: {stats['missing_date']}")
    print(f"  Older than 25 days: {stats['old_date']}")
    print(f"  URL duplicates filtered: {stats['duplicate_url']}")
    print(f"  Title+Company+Location duplicates filtered: {stats['duplicate_tc']}")
    print(f"  Clean unique jobs remaining: {stats['valid']}")
    sys.stdout.flush()
    
    # 3. Write role_index.json
    with open("role_index.json", 'w', encoding='utf-8') as fh:
        json.dump(dict(category_counts), fh, indent=2)
    print("Wrote role_index.json")
    
    # 4. Remove old master chunk files
    for f in chunk_files:
        try:
            os.remove(f)
        except Exception as e:
            print(f"Error removing {f}: {e}")
            
    # 5. Write new master chunk files in O(N)
    current_chunk = 1
    current_chunk_data = []
    current_chunk_bytes = 2 # '[]'
    
    for j in clean_jobs:
        j_str = json.dumps(j, separators=(',', ':'))
        j_bytes = len(j_str.encode('utf-8'))
        
        comma_overhead = 1 if current_chunk_data else 0
        if current_chunk_bytes + j_bytes + comma_overhead > storage.MAX_FILE_SIZE:
            chunk_file = f"all_jobs_{current_chunk}.json"
            with open(chunk_file, 'w', encoding='utf-8') as fh:
                json.dump(current_chunk_data, fh, separators=(',', ':'))
            print(f"Wrote master chunk {chunk_file} ({len(current_chunk_data)} jobs)")
            
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
        print(f"Wrote master chunk {chunk_file} ({len(current_chunk_data)} jobs)")
        
    # 6. Rebuild jobs_by_role folder
    output_dir = "jobs_by_role"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    grouped_jobs = {}
    for j in clean_jobs:
        cat = j.get('role_category') or 'Other'
        if cat not in grouped_jobs:
            grouped_jobs[cat] = []
        grouped_jobs[cat].append(j)
        
    for cat, jobs in grouped_jobs.items():
        filename = storage.get_category_filename(cat)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as fh:
            json.dump(jobs, fh, separators=(',', ':'))
            
    print(f"Split completed. Wrote {len(grouped_jobs)} role files in {output_dir}/")
    print("=== PIPELINE RUN COMPLETED SUCCESSFULLY ===")
    sys.stdout.flush()

if __name__ == "__main__":
    run_pipeline()
