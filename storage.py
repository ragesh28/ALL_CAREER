import os
import hashlib
import tempfile
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from scripts.job_archive_paths import ARCHIVE_DIRECTORY, ARCHIVE_PREFIX, archive_chunk_number, archive_chunks

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
    """Replace a complete JSON file atomically or report the error to the caller."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     suffix=".tmp", delete=False) as file:
        temporary = Path(file.name)
        try:
            separators = (",", ":") if compact and indent is None else None
            json.dump(data, file, indent=indent, separators=separators, ensure_ascii=False)
            file.close()
            os.replace(temporary, path)
        finally:
            file.close()
            temporary.unlink(missing_ok=True)


def get_all_chunk_files():
    return [str(path) for path in archive_chunks(ROOT_DIR)]


def archive_chunk_path(number):
    path = Path(ROOT_DIR) / ARCHIVE_DIRECTORY / f"{ARCHIVE_PREFIX}{number}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

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
    latest_number = archive_chunk_number(chunk_files[-1]) if chunk_files else 1
    latest_chunk = archive_chunk_path(latest_number)
    existing_data = []
    if chunk_files and (not latest_chunk.is_file() or latest_chunk.stat().st_size >= MAX_FILE_SIZE):
        latest_chunk = archive_chunk_path(latest_number + 1)
    elif latest_chunk.is_file():
        try:
            with open(latest_chunk, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            if not isinstance(existing_data, list):
                raise ValueError("Archive must contain a job array")
        except (OSError, ValueError):
            # Keep the original available for catalog recovery.
            latest_chunk = archive_chunk_path(latest_number + 1)
            existing_data = []
        
    existing_data.extend(new_jobs)
    safe_write_json(latest_chunk, existing_data)


def archive_key(job):
    from scripts.build_web_catalog import city_name

    company = job.get("company")
    if isinstance(company, dict):
        company = company.get("name") or "Unknown"
    identity = [
        get_job_url(job) or job.get("telegram_url") or job.get("flyer_image_url") or "",
        str(job.get("title") or job.get("role") or "Position").strip().lower(),
        str(company or job.get("company_name") or job.get("company_canonical") or "").strip().lower(),
        city_name(job.get("location")),
    ]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).digest()


def read_saved_jobs(path):
    from scripts.build_web_catalog import read_job_array

    rows, _ = read_job_array(Path(path).read_bytes(), path)
    if not isinstance(rows, list):
        raise ValueError(f"Expected a job array in {path}")
    return rows


_archive_root = None
_archived_keys = set()


def archived_keys(refresh=False):
    # Each scraper has a single writer in its checkout. A replay after a Git pull
    # uses a fresh process against the current archives.
    global _archive_root, _archived_keys
    if refresh or _archive_root != ROOT_DIR:
        _archived_keys = {
            archive_key(job) for path in get_all_chunk_files()
            for job in read_saved_jobs(path) if isinstance(job, dict)
        }
        _archive_root = ROOT_DIR
    return _archived_keys


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

class JobStorageError(RuntimeError):
    """A required job save failed. Keep the scraper checkpoint on the current batch."""


def store_jobs_batch(jobs):
    try:
        return store_jobs_granular(jobs)
    except (OSError, ValueError, TypeError) as error:
        raise JobStorageError("Could not save the job batch") from error


def store_jobs_granular(jobs):
    if not jobs:
        return 0
        
    merging = bool(os.environ.get("IS_MERGING_TEMP"))
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
            is_explicit_walkin = (
                j.get("is_walkin") in (True, "true") or j.get("walkin_date") or j.get("walkin_dates")
                or src_val == "google_images" or "flyer" in src_val or "walkin" in src_val
            )
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
            
        if not merging and date_str and len(date_str) >= 10 and date_str[:10] < cutoff_date:
            continue
            
        if not j.get("role_category"):
            j["role_category"] = role_classifier.classify_job(j)
            
        role_slug = get_role_slug(j)
        src_slug = slugify(j.get("source") or "other", default="other")
        loc_slug = clean_location(j.get("location"))
        
        grouped[(role_slug, src_slug, loc_slug)].append(j)
        
    if not grouped:
        return 0
        
    from scripts.optimize_shards import compact_job

    complete = archived_keys()
    additions = {}
    shard_changes = {}
    new_to_shards = []
    new_files = 0
    for (role, source, location), incoming in grouped.items():
        path = Path(JOBS_DIR) / role / f"{source}_{location}.json"
        exists = path.is_file()
        previous = read_saved_jobs(path) if exists else []
        by_url = {get_job_url(job): job for job in previous}
        by_title = {get_job_title_company_key(job): job for job in previous}
        new_rows = []
        for job in incoming:
            url, title = get_job_url(job), get_job_title_company_key(job)
            prior = (by_url.get(url) if url else None) or (by_title.get(title) if title else None)
            if prior is None:
                new_rows.append(job)
                if url:
                    by_url[url] = job
                if title:
                    by_title[title] = job
            # A legacy shard can contain a job that never made it into an archive.
            # A replay also preserves distinct jobs accepted before a concurrent push.
            candidate = job
            if prior is not None and not merging and archive_key(prior) != archive_key(job):
                candidate = prior
            key = archive_key(candidate)
            if key not in complete:
                additions.setdefault(key, candidate)
        if new_rows:
            shard_changes[path] = [compact_job(job) for job in new_rows + previous]
            new_to_shards.extend(new_rows)
            new_files += int(not exists)

    if not merging and (additions or new_to_shards):
        # Journal before changing any shard or archive. The workflow replays this
        # buffer against the upstream snapshot before committing the checkpoint.
        buffer = Path(ROOT_DIR) / "temp_new_jobs.json"
        pending = {archive_key(job): job for job in read_saved_jobs(buffer)} if buffer.is_file() else {}
        pending.update(additions)
        for job in new_to_shards:
            pending[archive_key(job)] = job
        safe_write_json(buffer, list(pending.values()))

    append_to_archival_chunks(list(additions.values()))
    complete.update(additions)
    for path, rows in shard_changes.items():
        safe_write_json(path, rows)
    update_indexes_after_add(new_to_shards, new_files_count=new_files)

    print(f"[store_jobs_granular] Archived {len(additions)} jobs, updated {len(shard_changes)} shards.")
    return len(additions)



