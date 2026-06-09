import os
import json
import glob
import re
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

def normalize_url(url):
    if not url or not isinstance(url, str):
        return ""
    url = url.strip()
    if url.startswith("http://"):
        url = "https://" + url[7:]
    # Strip trailing slash and trailing hash/fragments
    url = url.rstrip('/')
    return url

def get_job_url(job):
    """Single source of truth for job URL extraction."""
    raw_url = (
        job.get("url") or 
        job.get("apply_link") or 
        job.get("linkedin_url") or 
        job.get("permanent_url") or 
        ""
    )
    return normalize_url(raw_url)

NON_ALPHANUM = re.compile(r'[^a-z0-9]')
HAS_ALPHA = re.compile(r'[a-zA-Z]')

def get_job_title_company_key(job):
    """Create a normalized key based on title, company, and location."""
    title = job.get("title") or job.get("role") or ""
    company = job.get("company") or job.get("company_name") or ""
    location = job.get("location") or ""
    
    # Normalize: lowercase, keep only alphanumeric
    t_clean = NON_ALPHANUM.sub('', str(title).lower())
    c_clean = NON_ALPHANUM.sub('', str(company).lower())
    l_clean = NON_ALPHANUM.sub('', str(location).lower())
    
    if t_clean and c_clean:
        return f"{t_clean}|||{c_clean}|||{l_clean}"
    return ""

def is_valid_job(job):
    """Filter out garbage entries (empty titles, nan values, etc.)."""
    title = str(job.get("title") or job.get("role") or "").strip()
    company = str(job.get("company") or job.get("company_name") or "").strip()
    
    if not title or not company:
        return False
        
    title_lower = title.lower()
    company_lower = company.lower()
    
    if title_lower in ("nan", "none", "null") or company_lower in ("nan", "none", "null"):
        return False
        
    # Check that title has at least some alphabetical characters
    if not HAS_ALPHA.search(title):
        return False
        
    return True

def load_all_existing_urls():
    """Maintain backward compatibility, returns set of normalized URLs."""
    seen_urls, _ = load_existing_keys()
    return seen_urls

def load_existing_keys():
    seen_urls = set()
    seen_tc_keys = set()
    for f in get_all_chunk_files():
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for j in data:
                    url = get_job_url(j)
                    if url:
                        seen_urls.add(url)
                    tc_key = get_job_title_company_key(j)
                    if tc_key:
                        seen_tc_keys.add(tc_key)
        except Exception as e:
            print(f"Error loading {f}: {e}")
    return seen_urls, seen_tc_keys

def get_category_filename(category):
    s = category.lower().replace('/', '_').replace('-', '_')
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'[^a-z0-9_]', '', s)
    return f"{s}.json"

def store_jobs_batch(jobs):
    if not jobs:
        return 0
        
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    seen_urls, seen_tc_keys = load_existing_keys()
    new_jobs = []
    
    for j in jobs:
        if not is_valid_job(j):
            continue
            
        url = get_job_url(j)
        tc_key = get_job_title_company_key(j)
        
        date_str = j.get("date_posted", "") or j.get("fetchedAt", "") or j.get("date", "")
        # Filter older than 30 days
        if date_str and len(date_str) >= 10 and date_str[:10] < cutoff_date:
            continue
            
        # Check URL duplicate
        if url and url in seen_urls:
            continue
            
        # Check Title+Company+Location duplicate
        if tc_key and tc_key in seen_tc_keys:
            continue
            
        new_jobs.append(j)
        if url:
            seen_urls.add(url)
        if tc_key:
            seen_tc_keys.add(tc_key)
            
    if not new_jobs:
        return 0
        
    # Classify new jobs and add role_category field
    import role_classifier
    for j in new_jobs:
        category = role_classifier.classify_job(j)
        j['role_category'] = category
        
    # Update role_index.json
    role_index_file = "role_index.json"
    role_counts = {}
    if os.path.exists(role_index_file):
        try:
            with open(role_index_file, 'r', encoding='utf-8') as fh:
                role_counts = json.load(fh)
        except Exception:
            role_counts = {}
            
    # Group new jobs by category for file writing
    jobs_by_cat = {}
    for j in new_jobs:
        cat = j.get('role_category') or 'Other'
        role_counts[cat] = role_counts.get(cat, 0) + 1
        
        if cat not in jobs_by_cat:
            jobs_by_cat[cat] = []
        jobs_by_cat[cat].append(j)
        
    # Save updated role_index.json
    try:
        with open(role_index_file, 'w', encoding='utf-8') as fh:
            json.dump(role_counts, fh, indent=2)
    except Exception as e:
        print(f"Error updating role_index.json: {e}")
        
    # Save incremental jobs to jobs_by_role files
    os.makedirs("jobs_by_role", exist_ok=True)
    for cat, cat_jobs in jobs_by_cat.items():
        filename = get_category_filename(cat)
        filepath = os.path.join("jobs_by_role", filename)
        
        existing_cat_jobs = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as fh:
                    existing_cat_jobs = json.load(fh)
            except Exception:
                existing_cat_jobs = []
                
        existing_cat_jobs.extend(cat_jobs)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as fh:
                json.dump(existing_cat_jobs, fh, separators=(',', ':'))
        except Exception as e:
            print(f"Error writing to {filepath}: {e}")
            
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


