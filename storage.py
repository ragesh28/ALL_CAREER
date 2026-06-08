import os
import json
import glob
from datetime import datetime, timedelta

MAX_FILE_SIZE = 45 * 1024 * 1024  # 45 MB

def get_all_chunk_files():
    files = glob.glob("all_jobs_*.json")
    valid_files = []
    for f in files:
        parts = f.split("_")
        if len(parts) >= 3:
            chunk_part = parts[2].split(".")[0]
            if chunk_part.isdigit():
                valid_files.append((f, int(chunk_part)))
    valid_files.sort(key=lambda x: x[1])
    return [x[0] for x in valid_files]

def load_all_existing_urls():
    seen = set()
    for f in get_all_chunk_files():
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for j in data:
                    url = j.get("url") or j.get("apply_link") or j.get("linkedin_url")
                    if url:
                        seen.add(url)
        except Exception as e:
            print(f"Error loading {f}: {e}")
    return seen

def store_jobs_batch(jobs):
    if not jobs:
        return 0
        
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    seen = load_all_existing_urls()
    new_jobs = []
    for j in jobs:
        url = j.get("url") or j.get("linkedin_url")
        date_str = j.get("date_posted", "") or j.get("fetchedAt", "") or j.get("date", "")
        
        # Filter older than 30 days
        if date_str and len(date_str) >= 10 and date_str[:10] < cutoff_date:
            continue
            
        if url and url not in seen:
            new_jobs.append(j)
            seen.add(url)
            
    if not new_jobs:
        return 0
        
    files = get_all_chunk_files()
    if not files:
        latest_file = "all_jobs_1.json"
        latest_data = []
    else:
        latest_file = files[-1]
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                latest_data = json.load(f)
        except Exception:
            latest_data = []
            
    # Check size, if > 45MB, roll over to a new file
    if os.path.exists(latest_file) and os.path.getsize(latest_file) > MAX_FILE_SIZE:
        chunk_num = 1
        try:
            chunk_num = int(latest_file.split("_")[2].split(".")[0]) + 1
        except Exception:
            chunk_num = len(files) + 1
        latest_file = f"all_jobs_{chunk_num}.json"
        latest_data = []
        
    latest_data.extend(new_jobs)
    
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(latest_data, f, separators=(',', ':'))
        
    return len(new_jobs)
