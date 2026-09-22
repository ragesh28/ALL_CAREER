import os
import json
import glob
import re
from datetime import datetime, timedelta

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
INDEX_DIR = os.path.join(DATA_DIR, "index")
JOBS_DIR = os.path.join(DATA_DIR, "jobs")

MAX_FILE_SIZE = 45 * 1024 * 1024  # 45 MB

def safe_load_json(file_path, default=None):
    """
    Safely load JSON, automatically stripping git merge conflict markers
    if any were accidentally committed.
    """
    if not os.path.exists(file_path):
        return default if default is not None else {}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if not content.strip():
            return default if default is not None else {}
        if "<<<<<<<" in content:
            clean_lines = []
            skip = False
            for line in content.splitlines():
                if line.startswith("<<<<<<<"):
                    skip = False
                    continue
                elif line.startswith("======="):
                    skip = True
                    continue
                elif line.startswith(">>>>>>>"):
                    skip = False
                    continue
                if not skip:
                    clean_lines.append(line)
            content = "\n".join(clean_lines)
        return json.loads(content)
    except Exception as e:
        print(f"Warning: safe_load_json on {file_path}: {e}")
        return default if default is not None else {}

def safe_write_json(file_path, data, indent=None, compact=True):
    """
    Safely write JSON using atomic write (.tmp + os.replace) to avoid partial or corrupt files.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    tmp_path = file_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            if indent is not None:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            elif compact:
                json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, file_path)
    except Exception as e:
        print(f"Warning: atomic write error on {file_path} ({e}), falling back to direct write")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                if indent is not None:
                    json.dump(data, f, indent=indent, ensure_ascii=False)
                else:
                    json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
        except Exception as e2:
            print(f"Error direct writing {file_path}: {e2}")

def get_all_chunk_files():
    files = glob.glob(os.path.join(ROOT_DIR, "all_jobs_*.json"))
    valid_files = []
    for f in files:
        parts = os.path.basename(f).split("_")
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
        job.get("apply_url") or 
        job.get("source_url") or 
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
    company_raw = job.get("company") or job.get("company_name") or job.get("company_canonical") or ""
    if isinstance(company_raw, dict):
        company = company_raw.get("name") or company_raw.get("canonical") or ""
    else:
        company = str(company_raw)
    location = job.get("location") or ""
    
    # Normalize: lowercase, keep only alphanumeric
    t_clean = NON_ALPHANUM.sub('', str(title).lower())
    c_clean = NON_ALPHANUM.sub('', company.lower())
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

def normalize_location(loc, title="", description=""):
    loc_str = str(loc or "").strip()
    if not loc_str or loc_str.lower() in ("null", "none", "unknown", "nan", "india"):
        loc_str = ""
    
    loc_clean = loc_str.lower()
    loc_clean = re.sub(r'[^a-z0-9\s,]', ' ', loc_clean)
    loc_clean = re.sub(r'\s+', ' ', loc_clean).strip()
    
    context_text = f"{loc_str} {title} {description}".lower()

    # Cities priority: specific cities checked first
    cities_priority = [
        ("coimbatore", "Coimbatore"),
        ("kovai", "Coimbatore"),
        ("chennai", "Chennai"),
        ("madras", "Chennai"),
        ("madurai", "Madurai"),
        ("tiruchirappalli", "Trichy"),
        ("trichy", "Trichy"),
        ("salem", "Salem"),
        ("tirunelveli", "Tirunelveli"),
        ("erode", "Erode"),
        ("tirupur", "Tirupur"),
        ("vellore", "Vellore"),
        ("bangalore", "Bangalore"),
        ("bengaluru", "Bangalore"),
        ("mysore", "Mysore"),
        ("mysuru", "Mysore"),
        ("mangalore", "Mangalore"),
        ("mangaluru", "Mangalore"),
        ("hubli", "Hubli"),
        ("dharwad", "Hubli"),
        ("belgaum", "Belgaum"),
        ("hyderabad", "Hyderabad"),
        ("secunderabad", "Hyderabad"),
        ("visakhapatnam", "Visakhapatnam"),
        ("vizag", "Visakhapatnam"),
        ("vijayawada", "Vijayawada"),
        ("navi mumbai", "Mumbai"),
        ("mumbai", "Mumbai"),
        ("thane", "Mumbai"),
        ("pune", "Pune"),
        ("nagpur", "Nagpur"),
        ("nashik", "Nashik"),
        ("noida", "Noida"),
        ("greater noida", "Noida"),
        ("gurgaon", "Delhi"),
        ("gurugram", "Delhi"),
        ("new delhi", "Delhi"),
        ("delhi", "Delhi"),
        ("faridabad", "Delhi"),
        ("ghaziabad", "Delhi"),
        ("kolkata", "Kolkata"),
        ("calcutta", "Kolkata"),
        ("ahmedabad", "Ahmedabad"),
        ("surat", "Surat"),
        ("vadodara", "Vadodara"),
        ("rajkot", "Rajkot"),
        ("kochi", "Kochi"),
        ("cochin", "Kochi"),
        ("thiruvananthapuram", "Trivandrum"),
        ("trivandrum", "Trivandrum"),
        ("kozhikode", "Kozhikode"),
        ("calicut", "Kozhikode"),
        ("chandigarh", "Chandigarh"),
        ("mohali", "Chandigarh"),
        ("jaipur", "Jaipur"),
        ("lucknow", "Lucknow"),
        ("kanpur", "Kanpur"),
        ("indore", "Indore"),
        ("bhopal", "Bhopal"),
        ("bhubaneswar", "Bhubaneswar"),
        ("patna", "Patna"),
        ("remote", "Remote"),
        ("wfh", "Remote"),
    ]

    for kw, city_name in cities_priority:
        if re.search(r'\b' + re.escape(kw) + r'\b', loc_clean):
            return city_name

    state_names = {
        "tamil nadu": "Tamil Nadu",
        "tn": "Tamil Nadu",
        "karnataka": "Karnataka",
        "ka": "Karnataka",
        "maharashtra": "Maharashtra",
        "mh": "Maharashtra",
        "telangana": "Telangana",
        "ts": "Telangana",
        "andhra pradesh": "Andhra Pradesh",
        "ap": "Andhra Pradesh",
        "uttar pradesh": "Uttar Pradesh",
        "up": "Uttar Pradesh",
        "haryana": "Haryana",
        "hr": "Haryana",
        "kerala": "Kerala",
        "kl": "Kerala",
        "gujarat": "Gujarat",
        "gj": "Gujarat",
        "west bengal": "West Bengal",
        "wb": "West Bengal",
        "rajasthan": "Rajasthan",
        "rj": "Rajasthan",
        "madhya pradesh": "Madhya Pradesh",
        "mp": "Madhya Pradesh",
        "odisha": "Odisha",
        "punjab": "Punjab",
        "pb": "Punjab",
        "bihar": "Bihar",
        "assam": "Assam",
    }

    # If loc mentions a state or is empty/India, inspect title & description for specific city
    is_state_or_empty = (not loc_clean) or any(re.search(r'\b' + re.escape(st) + r'\b', loc_clean) for st in state_names)
    if is_state_or_empty and context_text.strip():
        for kw, city_name in cities_priority:
            if re.search(r'\b' + re.escape(kw) + r'\b', context_text):
                return city_name

    # If it's a state and no city found, preserve the clean state name (NEVER map to a capital city)
    for st_kw, st_name in state_names.items():
        if re.search(r'\b' + re.escape(st_kw) + r'\b', loc_clean):
            return st_name

    parts = [p.strip() for p in loc_str.split(',') if p.strip()]
    if parts:
        first_part = parts[0]
        if first_part.lower() not in ("india", "null", "none", "nan"):
            return first_part.title()
    return ""

def append_to_archival_chunks(new_jobs):
    if not new_jobs:
        return
    chunk_files = get_all_chunk_files()
    if not chunk_files:
        latest_chunk = "all_jobs_1.json"
        existing_data = []
    else:
        latest_chunk = chunk_files[-1]
        try:
            with open(latest_chunk, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            existing_data = []
            
    current_size = os.path.getsize(latest_chunk) if os.path.exists(latest_chunk) else 0
    if current_size >= MAX_FILE_SIZE:
        chunk_num = len(chunk_files) + 1
        latest_chunk = f"all_jobs_{chunk_num}.json"
        existing_data = []
        
    existing_data.extend(new_jobs)
    with open(latest_chunk, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, separators=(',', ':'))

def update_indexes_after_add(newly_added_jobs, new_files_count=0):
    if not newly_added_jobs:
        return
        
    counts_file = os.path.join(INDEX_DIR, "sidebar_counts.json")
    preview_file = os.path.join(INDEX_DIR, "latest_preview_100.json")
    manifest_file = os.path.join(INDEX_DIR, "manifest.json")

    from scripts.optimize_shards import compact_job
    from scripts.split_existing_jobs import slugify, clean_location, get_role_slug

    # 1. Update preview
    try:
        preview_jobs = safe_load_json(preview_file, default=[])
        if not isinstance(preview_jobs, list):
            preview_jobs = []
        compacted_new = [compact_job(j) for j in newly_added_jobs]
        combined = compacted_new + preview_jobs
        seen = set()
        deduped = []
        for j in combined:
            u = j.get("url") or f"{j.get('title')}_{j.get('company')}"
            if u not in seen:
                seen.add(u)
                deduped.append(j)
        safe_write_json(preview_file, deduped[:100], compact=True)
    except Exception as e:
        print(f"Error updating preview: {e}")

    # 2. Update sidebar counts
    try:
        counts = safe_load_json(counts_file, default={})
        counts["total_jobs"] = counts.get("total_jobs", 0) + len(newly_added_jobs)
        sources = counts.get("sources", {})
        locs = counts.get("locations", {})
        for j in newly_added_jobs:
            s = slugify(j.get("source") or "other")
            l = clean_location(j.get("location"))
            sources[s] = sources.get(s, 0) + 1
            locs[l] = locs.get(l, 0) + 1
        counts["sources"] = sources
        counts["locations"] = locs
        counts["generated_at"] = datetime.now().isoformat()
        safe_write_json(counts_file, counts, indent=2)
    except Exception as e:
        print(f"Error updating sidebar counts: {e}")

    # 3. Update manifest
    try:
        manifest = safe_load_json(manifest_file, default={})
        manifest["total_jobs"] = manifest.get("total_jobs", 0) + len(newly_added_jobs)
        if new_files_count > 0:
            manifest["total_files"] = manifest.get("total_files", 0) + new_files_count
        manifest["generated_at"] = datetime.now().isoformat()
        roles = manifest.get("roles", {})
        for j in newly_added_jobs:
            r_slug = get_role_slug(j)
            s_slug = slugify(j.get("source") or "other")
            l_slug = clean_location(j.get("location"))

            if r_slug not in roles:
                roles[r_slug] = {"name": r_slug.replace('_', ' ').title(), "total": 0, "sources": {}}
            roles[r_slug]["total"] = roles[r_slug].get("total", 0) + 1
            
            srcs = roles[r_slug]["sources"]
            if s_slug not in srcs:
                srcs[s_slug] = {"total": 0, "locs": {}}
            srcs[s_slug]["total"] = srcs[s_slug].get("total", 0) + 1
            
            loc_map = srcs[s_slug]["locs"]
            loc_map[l_slug] = loc_map.get(l_slug, 0) + 1

        manifest["roles"] = roles
        safe_write_json(manifest_file, manifest, compact=True)
    except Exception as e:
        print(f"Error updating manifest: {e}")

    # 4. Update walkin_jobs.json if any newly added jobs are walk-ins
    walkin_file = os.path.join(INDEX_DIR, "walkin_jobs.json")
    new_walkins = [j for j in newly_added_jobs if j.get("is_walkin") or j.get("walkin_date")]
    if new_walkins:
        try:
            existing_walkins = safe_load_json(walkin_file, default=[])
            if not isinstance(existing_walkins, list):
                existing_walkins = []
            w_seen = {get_job_url(w) for w in existing_walkins if get_job_url(w)}
            w_tc_seen = {get_job_title_company_key(w) for w in existing_walkins if get_job_title_company_key(w)}
            to_add = []
            for w in new_walkins:
                u = get_job_url(w)
                tc = get_job_title_company_key(w)
                if (u and u in w_seen) or (tc and tc in w_tc_seen):
                    continue
                to_add.append(compact_job(w))
                if u: w_seen.add(u)
                if tc: w_tc_seen.add(tc)
            if to_add:
                combined_walkins = to_add + existing_walkins
                safe_write_json(walkin_file, combined_walkins, compact=True)
        except Exception as e:
            print(f"Error updating walkin_jobs.json: {e}")

def store_jobs_batch(jobs):
    """
    Main entry point for scrapers to save jobs.
    Uses ultra-fast granular shard storage (<30ms) instead of rewriting 335 MB monolithic chunks.
    Also updates indexes and appends to the current archival chunk.
    """
    return store_jobs_granular(jobs)

def store_jobs_granular(jobs):
    """
    Directly upserts scraped jobs into targeted granular shards:
    data/jobs/<role_slug>/<source>_<location>.json
    Instead of rewriting 335 MB across monolithic chunks, this only opens and updates
    the matching small JSON files in milliseconds.
    """
    if not jobs:
        return 0
        
    cutoff_date = (datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d")
    
    from collections import defaultdict
    from scripts.split_existing_jobs import slugify, clean_location, get_role_slug
    import role_classifier
    
    grouped = defaultdict(list)
    
    for j in jobs:
        if not is_valid_job(j):
            continue
            
        canon_url = get_job_url(j)
        if canon_url and not j.get("url"):
            j["url"] = canon_url
            
        j["location"] = normalize_location(
            j.get("location"),
            title=str(j.get("title") or j.get("role") or ""),
            description=str(j.get("description") or j.get("other_details") or "")
        )
        
        # Walkin info extraction
        try:
            from extractor_utils import extract_walkin_info
            w_info = extract_walkin_info(
                title=str(j.get("title") or j.get("role") or ""),
                description=str(j.get("description") or j.get("other_details") or "")
            )
            src_val = str(j.get("source") or "").lower()
            is_explicit_walkin = ("google" in src_val or "flyer" in src_val or "walkin" in src_val)
            if w_info.get("is_walkin") or is_explicit_walkin:
                j["is_walkin"] = True
                if w_info.get("walkin_date") and not j.get("walkin_date"):
                    j["walkin_date"] = w_info["walkin_date"]
                if w_info.get("walkin_time") and not j.get("walkin_time"):
                    j["walkin_time"] = w_info["walkin_time"]
            else:
                j["is_walkin"] = False
        except Exception:
            pass
            
        date_str = get_job_date(j)
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            j["date_posted"] = date_str
            
        if date_str and len(date_str) >= 10 and date_str[:10] < cutoff_date:
            continue
            
        if not j.get("role_category"):
            j["role_category"] = role_classifier.classify_job(j)
            
        role_slug = get_role_slug(j)
        src_slug = slugify(j.get("source") or "other", default="other")
        loc_slug = clean_location(j.get("location"))
        
        grouped[(role_slug, src_slug, loc_slug)].append(j)
        
    if not grouped:
        return 0
        
    jobs_dir = os.path.join("data", "jobs")
    total_added = 0
    updated_files = 0
    new_files_created = 0
    all_truly_added = []
    
    # Process only the targeted shard files
    for (role_slug, src_slug, loc_slug), new_items in grouped.items():
        role_dir = os.path.join(JOBS_DIR, role_slug)
        os.makedirs(role_dir, exist_ok=True)
        shard_path = os.path.join(role_dir, f"{src_slug}_{loc_slug}.json")
        
        is_new_file = not os.path.exists(shard_path)
        existing_shard = []
        if not is_new_file:
            loaded = safe_load_json(shard_path, default=[])
            if isinstance(loaded, list):
                existing_shard = loaded
                
        # Index existing shard jobs
        url_set = {get_job_url(item) for item in existing_shard if get_job_url(item)}
        tc_set = {get_job_title_company_key(item) for item in existing_shard if get_job_title_company_key(item)}
        
        items_to_add = []
        for item in new_items:
            u = get_job_url(item)
            tc = get_job_title_company_key(item)
            if (u and u in url_set) or (tc and tc in tc_set):
                continue
            items_to_add.append(item)
            if u:
                url_set.add(u)
            if tc:
                tc_set.add(tc)
                
        if items_to_add:
            # Prepend new jobs
            combined = items_to_add + existing_shard
            from scripts.optimize_shards import compact_job
            compacted = [compact_job(x) for x in combined]
            
            safe_write_json(shard_path, compacted, compact=True)
                
            total_added += len(items_to_add)
            updated_files += 1
            if is_new_file:
                new_files_created += 1
            all_truly_added.extend(items_to_add)
            
    if all_truly_added:
        # 1. Update preview and counts
        update_indexes_after_add(all_truly_added, new_files_count=new_files_created)
        
        # 2. Append to archival chunk
        try:
            append_to_archival_chunks(all_truly_added)
        except Exception as e:
            print(f"Error appending to archival chunk: {e}")
            
        # 3. Save newly added jobs to temp_new_jobs.json if not in merging mode
        if not os.environ.get("IS_MERGING_TEMP"):
            temp_file = os.path.join(ROOT_DIR, "temp_new_jobs.json")
            existing_temp = safe_load_json(temp_file, default=[])
            if not isinstance(existing_temp, list):
                existing_temp = []
            existing_temp.extend(all_truly_added)
            safe_write_json(temp_file, existing_temp, compact=True)
            print(f"      Saved {len(all_truly_added)} jobs to temporary buffer temp_new_jobs.json.")

    print(f"[store_jobs_granular] Added {total_added} new jobs across {updated_files} shards.")
    return total_added



