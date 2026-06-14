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

def get_job_date(job):
    """Extract and normalize date from any possible date field."""
    date_keys = ["date_posted", "job_posted_date", "date", "fetched_at", "fetchedAt"]
    for key in date_keys:
        val = job.get(key)
        if val:
            val_str = str(val).strip()
            if val_str.lower() not in ("none", "nan", "null", "undefined", ""):
                if len(val_str) >= 10:
                    match = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})', val_str)
                    if match:
                        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
                return val_str
    return ""

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
        
    cutoff_date = (datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d")
    
    # Load all existing jobs from all chunks
    all_existing_jobs = []
    chunk_files = get_all_chunk_files()
    for f in chunk_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if isinstance(data, list):
                    all_existing_jobs.extend(data)
        except Exception as e:
            print(f"Error loading {f}: {e}")
            
    # Index them by tc_key and url for quick lookup
    url_map = {}
    tc_map = {}
    for j in all_existing_jobs:
        url = get_job_url(j)
        if url:
            url_map[url] = j
        tc_key = get_job_title_company_key(j)
        if tc_key:
            tc_map[tc_key] = j
            
    new_jobs_added = 0
    db_changed = False
    
    for j in jobs:
        if not is_valid_job(j):
            continue
            
        url = get_job_url(j)
        tc_key = get_job_title_company_key(j)
        
        date_str = get_job_date(j)
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            j["date_posted"] = date_str
            if "job_posted_date" in j or "platform" in j:
                j["job_posted_date"] = date_str
                
        # Filter older than 25 days
        if date_str and len(date_str) >= 10 and date_str[:10] < cutoff_date:
            continue
            
        # Check if it already exists
        existing_job = None
        if url and url in url_map:
            existing_job = url_map[url]
        elif tc_key and tc_key in tc_map:
            existing_job = tc_map[tc_key]
            
        if existing_job is not None:
            # We found a duplicate! Let's check if we should enrich/update it.
            job_updated = False
            
            # 1. Update walking_interview
            # If the new job is walking_interview=True, and the existing is not, update it
            new_walking = j.get("walking_interview")
            old_walking = existing_job.get("walking_interview")
            if new_walking is True and old_walking is not True:
                existing_job["walking_interview"] = True
                job_updated = True
                print(f"      Enriched existing job with walking_interview=True: {existing_job.get('title')} @ {existing_job.get('company')}")
                
            # 2. Enrich other missing fields
            enrich_fields = ["experience", "salary", "qualification", "last_date", "other_details"]
            for field in enrich_fields:
                new_val = j.get(field)
                old_val = existing_job.get(field)
                if new_val not in (None, "", "null") and old_val in (None, "", "null"):
                    existing_job[field] = new_val
                    job_updated = True
                    print(f"      Enriched field '{field}' for existing job: {new_val}")
            
            if job_updated:
                db_changed = True
            continue
            
        # It's a brand new job!
        # Classify role
        import role_classifier
        category = role_classifier.classify_job(j)
        j['role_category'] = category
        
        all_existing_jobs.append(j)
        if url:
            url_map[url] = j
        if tc_key:
            tc_map[tc_key] = j
            
        new_jobs_added += 1
        db_changed = True

    if not db_changed:
        return 0
        
    import shutil
    # Re-write all chunks, rebuild jobs_by_role, and update role_index.json
    
    # 1. Rewrite chunk files
    for f in chunk_files:
        try:
            os.remove(f)
        except Exception:
            pass
            
    current_chunk = 1
    current_data = []
    current_bytes = 2  # for '[]'
    
    for j in all_existing_jobs:
        j_str = json.dumps(j, separators=(',', ':'))
        j_bytes = len(j_str.encode('utf-8'))
        comma = 1 if current_data else 0
        
        if current_bytes + j_bytes + comma > MAX_FILE_SIZE:
            with open(f"all_jobs_{current_chunk}.json", 'w', encoding='utf-8') as fh:
                json.dump(current_data, fh, separators=(',', ':'))
            current_chunk += 1
            current_data = [j]
            current_bytes = 2 + j_bytes
        else:
            current_data.append(j)
            current_bytes += j_bytes + comma
            
    if current_data:
        with open(f"all_jobs_{current_chunk}.json", 'w', encoding='utf-8') as fh:
            json.dump(current_data, fh, separators=(',', ':'))
            
    # 2. Rebuild jobs_by_role/
    role_dir = "jobs_by_role"
    if os.path.exists(role_dir):
        try:
            shutil.rmtree(role_dir)
        except Exception as e:
            print(f"Error removing jobs_by_role: {e}")
    os.makedirs(role_dir, exist_ok=True)
    
    grouped = {}
    role_counts = {}
    for j in all_existing_jobs:
        cat = j.get('role_category', 'Other')
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(j)
        role_counts[cat] = role_counts.get(cat, 0) + 1
        
    for cat, cat_jobs in grouped.items():
        filename = get_category_filename(cat)
        filepath = os.path.join(role_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as fh:
                json.dump(cat_jobs, fh, separators=(',', ':'))
        except Exception as e:
            print(f"Error writing to {filepath}: {e}")
            
    # 3. Update role_index.json
    try:
        with open("role_index.json", 'w', encoding='utf-8') as fh:
            json.dump(role_counts, fh, indent=2)
    except Exception as e:
        print(f"Error writing to role_index.json: {e}")
        
    return new_jobs_added


