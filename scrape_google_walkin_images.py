"""
ALL_CAREER — Google & High-Res Walk-in Flyer Extractor Workflow (v2.1: ScrapingAnt Proxy Mode).
Combines:
1. 50-City Deep Search Mode: "walk in interview" + "we are hiring" role-based queries
2. ScrapingAnt Rotating Proxy Port (1 Credit/query, masks GitHub Actions datacenter IP)
3. 5-Key Dynamic Daily Rotation (anti-detection across accounts)
4. Top 20 Metros @ 100 images, Next 30 Cities @ 20 images
5. 30-Day Rolling Credit Usage Tracker
6. Memory-Streamed RapidOCR + MCA Company Resolution + QR Decoding
"""
import os
import sys
import re
import json
import time
import asyncio
import hashlib
import aiohttp
import requests
import urllib.parse
import urllib3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Set, Tuple, Any

# Disable SSL verification warnings for proxy mode
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout.reconfigure(encoding='utf-8')

# Ensure root is in path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from image_pipeline.pipeline import ImageToJobPipeline
from image_pipeline.ingestion.deduplicator import JobDeduplicator

# ═════════════════════════════════════════════════════════════════════════════
# CITY TIERS: Top 20 Metros (100 images) + Next 30 Small Cities (20 images)
# ═════════════════════════════════════════════════════════════════════════════
TOP_20_CITIES = [
    "chennai", "bengaluru", "hyderabad", "pune", "mumbai",
    "delhi", "noida", "gurgaon", "kolkata", "ahmedabad",
    "jaipur", "lucknow", "chandigarh", "indore", "kochi",
    "coimbatore", "nagpur", "surat", "bhopal", "patna"
]

NEXT_30_CITIES = [
    "madurai", "trichy", "salem", "trivandrum", "kozhikode",
    "visakhapatnam", "vijayawada", "guntur", "tirupati", "mysuru",
    "hubli", "mangalore", "mohali", "kanpur", "varanasi",
    "agra", "bhubaneswar", "cuttack", "nashik", "aurangabad",
    "vadodara", "rajkot", "ranchi", "jamshedpur", "raipur",
    "dehradun", "guwahati", "gwalior", "ludhiana", "vellore"
]

# ═════════════════════════════════════════════════════════════════════════════
# "WE ARE HIRING" ROLE-BASED SEARCH QUERIES (Rotating Daily)
# ═════════════════════════════════════════════════════════════════════════════
HIRING_ROLES = [
    "software developer", "python developer", "data analyst",
    "fresher", "IT jobs", "full stack developer", "java developer",
    "web developer", "customer support", "accountant",
    "HR executive", "sales executive", "marketing",
    "mechanical engineer", "electrical engineer",
    "business analyst", "telecaller", "BPO", "back office", "devops engineer"
]

PROGRESS_FILE = ROOT_DIR / "data" / "walkin_scrape_progress.json"
OUTPUT_JOBS_FILE = ROOT_DIR / "scraped_image_walkin_jobs.json"
CREDIT_TRACKER_FILE = ROOT_DIR / "data" / "scrapingant_credit_tracker.json"
NOT_EXTRACTED_JSON = ROOT_DIR / "google_image_not_extracted.json"
NOT_EXTRACTED_TXT = ROOT_DIR / "google_image_not_extracted.txt"
MAX_RUN_SECONDS = 5 * 3600 + 50 * 60  # 5 hours 50 minutes watchdog limit

# ═════════════════════════════════════════════════════════════════════════════
# SCRAPINGANT PROXY CONFIGURATION (Proxy Port 8080, 1 Credit per Request)
# ═════════════════════════════════════════════════════════════════════════════
SCRAPINGANT_PROXY_HOST = "proxy.scrapingant.com:8080"


def get_scrapingant_keys() -> List[str]:
    """Load all ScrapingAnt API keys from environment variable (comma-separated)."""
    raw = os.environ.get("SCRAPINGANT_API_KEYS", "").strip()
    if not raw:
        # Check individual keys as fallback
        keys = []
        for i in range(1, 10):
            k = os.environ.get(f"SCRAPINGANT_KEY_{i}", "").strip()
            if k:
                keys.append(k)
        return keys
    return [k.strip() for k in raw.split(",") if k.strip()]


def get_todays_api_key(keys: List[str]) -> Tuple[str, int]:
    """
    Select today's API key using day-of-year rotation: (day - 1) % len(keys).
    Day 1 -> Key 1, Day 2 -> Key 2, ..., Day 5 -> Key 5, Day 6 -> Key 1 (repeats).
    """
    if not keys:
        return "", -1
    day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
    key_index = (day_of_year - 1) % len(keys)
    return keys[key_index], key_index


def get_proxy_dict(api_key: str) -> Optional[dict]:
    """Build proxy dict for requests using ScrapingAnt proxy port (1 credit mode)."""
    if not api_key:
        return None
    proxy_url = f"http://scrapingant&browser=false:{api_key}@{SCRAPINGANT_PROXY_HOST}"
    return {
        "http": proxy_url,
        "https": proxy_url
    }


# ═════════════════════════════════════════════════════════════════════════════
# 30-DAY ROLLING CREDIT TRACKER
# ═════════════════════════════════════════════════════════════════════════════
def load_credit_tracker() -> dict:
    """Load the 30-day rolling credit usage tracker."""
    if CREDIT_TRACKER_FILE.exists():
        try:
            with open(CREDIT_TRACKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_pool": 50000, "daily_log": []}


def save_credit_tracker(tracker: dict):
    """Save the credit tracker, pruning entries older than 30 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    tracker["daily_log"] = [
        entry for entry in tracker.get("daily_log", [])
        if entry.get("date", "") >= cutoff
    ]
    CREDIT_TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CREDIT_TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)


def get_30day_used_credits(tracker: dict) -> int:
    """Calculate total credits used in the last 30 days."""
    return sum(entry.get("credits_used", 0) for entry in tracker.get("daily_log", []))


def print_credit_dashboard(tracker: dict, today_credits: int, key_index: int):
    """Print a credit usage dashboard at the end of the workflow."""
    total_pool = tracker.get("total_pool", 50000)
    used_30d = get_30day_used_credits(tracker)
    remaining = total_pool - used_30d

    print("\n" + "=" * 70)
    print("  💳 SCRAPINGANT PROXY CREDIT DASHBOARD (30-Day Rolling)")
    print("=" * 70)
    print(f"  🔑 Today's API Key   : Key #{key_index + 1} (rotated daily)")
    print(f"  📊 Today's Credits   : {today_credits} credits consumed")
    print(f"  📅 30-Day Usage      : {used_30d:,} / {total_pool:,} credits")
    print(f"  ⚡ Remaining Balance : {remaining:,} credits ({remaining/total_pool*100:.1f}% left)")
    print("=" * 70)


# ═════════════════════════════════════════════════════════════════════════════
# PROGRESS / JOBS PERSISTENCE
# ═════════════════════════════════════════════════════════════════════════════
def load_progress() -> dict:
    """Load persistent scraper progress checkpoint."""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_run_timestamp": None,
        "completed_cities": [],
        "city_cursor": 0,
        "total_jobs_scraped": 0
    }


def save_progress(progress_data: dict):
    """Save persistent scraper progress checkpoint."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress_data, f, indent=2, ensure_ascii=False)


def load_existing_jobs() -> list:
    """Load existing scraped jobs for deduplication."""
    if OUTPUT_JOBS_FILE.exists():
        try:
            with open(OUTPUT_JOBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_jobs(jobs: list):
    """Save accumulated extracted jobs."""
    OUTPUT_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)


def init_not_extracted_files():
    """Clear/reset unextracted image tracking files at workflow startup."""
    with open(NOT_EXTRACTED_JSON, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    with open(NOT_EXTRACTED_TXT, "w", encoding="utf-8") as f:
        f.write("")


def save_not_extracted_images(items: list):
    """Save unique unextracted image records (JSON) and plain URLs (TXT)."""
    with open(NOT_EXTRACTED_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    # Save clean image URLs, one per line
    urls = [it["url"] for it in items if it.get("url") and it["url"].startswith("http")]
    with open(NOT_EXTRACTED_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(urls) + ("\n" if urls else ""))


# ═════════════════════════════════════════════════════════════════════════════
# HIGH-RES FLYER IMAGE SCRAPING VIA SCRAPINGANT PROXY PORT (1 Credit/Query)
# ═════════════════════════════════════════════════════════════════════════════
def fetch_flyer_urls_via_proxy_sync(
    query: str,
    api_key: str,
    max_count: int = 50
) -> Tuple[List[str], int]:
    """
    Scrape high-res flyer image URLs using ScrapingAnt Rotating Proxy Port.
    1. Routes through ScrapingAnt proxy port (1 credit, masks GitHub IP).
    2. Extracts direct high-resolution flyer image URLs from search responses.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    proxies = get_proxy_dict(api_key)
    found_urls = []
    seen = set()
    credits_used = 0

    # ── 1. Google Images Search (Last 24 Hours: udm=2&tbs=qdr:d, India Only: cr=countryIN) ──
    google_url = f"https://www.google.com/search?udm=2&tbs=qdr:d&cr=countryIN&q={urllib.parse.quote_plus(query)}"
    try:
        resp = requests.get(
            google_url,
            headers=headers,
            proxies=proxies,
            verify=False,
            timeout=20
        )
        if resp.status_code == 200:
            if proxies:
                credits_used += 1
            # Extract high-res image URLs from Google scripts/response
            g_urls = re.findall(r'\["(https?://[^"\\<>\s]+?\.(?:jpg|jpeg|png|webp)(?:\?[^"\s\\]*)?)",\s*\d+,\s*\d+\]', resp.text)
            for u in g_urls:
                clean = u.replace(r'\/', '/').replace('&amp;', '&').strip()
                # Skip expired image URLs containing 2025, 2024, etc.
                if re.search(r'/(?:202[0-5]|201\d)/', clean):
                    continue
                if clean.startswith("http") and clean not in seen:
                    seen.add(clean)
                    found_urls.append(clean)
    except Exception:
        pass

    # ── 2. Bing Images Search (Last 24 Hours: qft=+filterui:age-1d) ──
    if len(found_urls) < max_count:
        for first in [1, 36]:
            bing_url = f"https://www.bing.com/images/search?q={urllib.parse.quote_plus(query)}&qft=+filterui:age-1d&first={first}&count=35"
            try:
                resp = requests.get(
                    bing_url,
                    headers=headers,
                    proxies=proxies,
                    verify=False,
                    timeout=25
                )
                if resp.status_code == 200:
                    if proxies:
                        credits_used += 1
                    # Parse high-res direct image links (murl parameter)
                    murls = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', resp.text)
                    for u in murls:
                        clean = u.replace(r'\/', '/').replace('&amp;', '&').strip()
                        # Skip expired image URLs containing 2025, 2024, etc.
                        if re.search(r'/(?:202[0-5]|201\d)/', clean):
                            continue
                        if clean.startswith("http") and clean not in seen:
                            seen.add(clean)
                            found_urls.append(clean)
                elif resp.status_code in (403, 429):
                    print(f"    ⚠️ Proxy rate-limited ({resp.status_code}), continuing...")
                    break
            except Exception as e:
                # If proxy fails, attempt direct request as fallback
                try:
                    resp = requests.get(bing_url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        murls = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', resp.text)
                        for u in murls:
                            clean = u.replace(r'\/', '/').replace('&amp;', '&').strip()
                            if re.search(r'/(?:202[0-5]|201\d)/', clean):
                                continue
                            if clean.startswith("http") and clean not in seen:
                                seen.add(clean)
                                found_urls.append(clean)
                except Exception:
                    pass

            if len(found_urls) >= max_count:
                break

    return found_urls[:max_count], credits_used


# ═════════════════════════════════════════════════════════════════════════════
# IMAGE BUFFER DOWNLOAD (Async, In-Memory)
# ═════════════════════════════════════════════════════════════════════════════
async def download_image_buffer(session: aiohttp.ClientSession, url: str, city: str) -> Optional[dict]:
    """Concurrently download single flyer image buffer."""
    try:
        if url.startswith("data:image/"):
            import base64
            header, data = url.split(",", 1)
            img_bytes = base64.b64decode(data)
            if len(img_bytes) >= 6000:
                return {
                    "url": url[:120] + "...[base64]",
                    "raw_url": url,
                    "bytes": img_bytes,
                    "city": city
                }
        else:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    if len(content) >= 6000:
                        return {
                            "url": url,
                            "raw_url": url,
                            "bytes": content,
                            "city": city
                        }
    except Exception:
        pass
    return None


# ═════════════════════════════════════════════════════════════════════════════
# DEEP SEARCH MODE: Multi-Query Proxy Extraction per City
# ═════════════════════════════════════════════════════════════════════════════
async def scrape_images_for_city_deep(
    api_key: str,
    city: str,
    max_images: int = 100,
    credit_counter: dict = None
) -> list:
    """
    Deep Search Mode: 2 proxy-backed high-res queries per city.
    Query 1: "walk in interview" {city} hiring poster
    Query 2: "we are hiring" {city} {todays_role}

    Uses ScrapingAnt proxy port (1 credit per query = 2 credits per city).
    """
    all_image_urls = []
    seen = set()
    city_credits = 0

    # ── Query 1: Walk-in Interview Flyers ──
    query1 = f'"walk in interview" {city} hiring poster'
    print(f"\n  🔍 Query 1 (Proxy | 24h India-Only [Google udm=2&tbs=qdr:d&cr=countryIN / Bing age-1d]): {query1}")
    urls1, creds1 = await asyncio.to_thread(fetch_flyer_urls_via_proxy_sync, query1, api_key, max_count=max_images // 2 + 10)
    city_credits += creds1
    for u in urls1:
        if u not in seen:
            seen.add(u)
            all_image_urls.append(u)
    print(f"     Found {len(urls1)} image streams (Credits: {creds1})")

    # ── Query 2: "We Are Hiring" + Rotating Role ──
    day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
    role_index = (day_of_year - 1) % len(HIRING_ROLES)
    todays_role = HIRING_ROLES[role_index]
    query2 = f'"we are hiring" {city} {todays_role}'
    print(f"  🔍 Query 2 (Proxy | 24h India-Only [Google udm=2&tbs=qdr:d&cr=countryIN / Bing age-1d]): {query2}")
    urls2, creds2 = await asyncio.to_thread(fetch_flyer_urls_via_proxy_sync, query2, api_key, max_count=max_images // 2 + 10)
    city_credits += creds2
    for u in urls2:
        if u not in seen:
            seen.add(u)
            all_image_urls.append(u)
    print(f"     Found {len(urls2)} image streams (Credits: {creds2})")

    # Track total credit usage
    if credit_counter is not None:
        credit_counter["total"] += city_credits

    print(f"  📷 Total Candidate Images for '{city}': {len(all_image_urls)} (City Credits: {city_credits})")

    # ── Download all image buffers concurrently ──
    downloaded_images = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    conn = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(headers=headers, connector=conn) as session:
        tasks = [download_image_buffer(session, u, city) for u in all_image_urls[:max_images]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, dict) and res:
                downloaded_images.append(res)

    print(f"  📥 Successfully downloaded {len(downloaded_images)} flyer buffers for '{city}'")
    return downloaded_images


# ═════════════════════════════════════════════════════════════════════════════
# MAIN WORKFLOW
# ═════════════════════════════════════════════════════════════════════════════
async def main():
    start_time = time.time()
    progress = load_progress()
    existing_jobs = load_existing_jobs()
    deduplicator = JobDeduplicator(existing_jobs)
    credit_tracker = load_credit_tracker()

    # ── Reset Unextracted Image Tracking (Fresh start every run) ──
    init_not_extracted_files()
    not_extracted_images = []
    seen_not_extracted_urls = set()

    # ── Dynamic API Key Selection ──
    scrapingant_keys = get_scrapingant_keys()
    today_api_key, key_index = get_todays_api_key(scrapingant_keys)
    key_masked = today_api_key[:6] + "..." + today_api_key[-4:] if len(today_api_key) > 10 else "DIRECT/UNSET"

    # ── Credit Counter for This Run ──
    credit_counter = {"total": 0}

    # ── Today's Rotating Role ──
    day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
    role_index = (day_of_year - 1) % len(HIRING_ROLES)
    todays_role = HIRING_ROLES[role_index]

    print("=" * 80)
    print(f"  🚀 ALL_CAREER — SCRAPINGANT PROXY WALK-IN FLYER EXTRACTOR (v2.1)")
    print(f"  📅 Start Time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  ⏱️ Maximum Run Budget: 5 Hours 50 Minutes ({MAX_RUN_SECONDS}s)")
    print(f"  📊 Previously Scraped Jobs: {len(existing_jobs):,}")
    print(f"  🔑 Today's Proxy Key: Key #{key_index + 1} [{key_masked}]")
    print(f"  👔 Today's Hiring Role: \"{todays_role}\"")
    print(f"  💳 30-Day Credits Used: {get_30day_used_credits(credit_tracker):,} / {credit_tracker.get('total_pool', 50000):,}")
    print("=" * 80)

    # Initialize OCR Pipeline
    pipeline = ImageToJobPipeline(enable_ai_verification=False)

    # ── Build City Queue: Top 20 (100 images) + Next 30 (20 images) ──
    city_queue = []
    for c in TOP_20_CITIES:
        city_queue.append({"city": c, "max_images": 100, "tier": "Top-20"})
    for c in NEXT_30_CITIES:
        city_queue.append({"city": c, "max_images": 20, "tier": "Small-30"})

    # Checkpoint rotation cursor
    start_cursor = progress.get("city_cursor", 0) % len(city_queue)
    reordered_queue = city_queue[start_cursor:] + city_queue[:start_cursor]

    new_jobs_count = 0
    temp_dir = ROOT_DIR / "data" / "temp_ocr_buffers"
    temp_dir.mkdir(parents=True, exist_ok=True)

    for idx, city_item in enumerate(reordered_queue):
        elapsed = time.time() - start_time
        if elapsed >= MAX_RUN_SECONDS:
            print(f"\n⏳ Graceful Watchdog Triggered: 5h 50m reached ({elapsed:.1f}s). Checkpointing...")
            progress["city_cursor"] = (start_cursor + idx) % len(city_queue)
            break

        city_name = city_item["city"]
        max_imgs = city_item["max_images"]
        tier = city_item["tier"]
        city_extracted_count = 0

        print(f"\n{'='*25} [{idx+1}/{len(reordered_queue)}] {city_name.upper()} ({tier}) {'='*25}")

        flyers = await scrape_images_for_city_deep(
            api_key=today_api_key,
            city=city_name,
            max_images=max_imgs,
            credit_counter=credit_counter
        )

        for f_idx, flyer in enumerate(flyers, 1):
            flyer_url = flyer.get("url") or flyer.get("raw_url") or ""
            # ── Deduplication Pre-Check 1: Fast Image Byte / URL Duplicate Check ──
            is_dup_img, dup_img_reason = deduplicator.is_image_duplicate(flyer["bytes"], flyer.get("url"))
            if is_dup_img:
                print(f"  ⏭️ [Skip Existing Flyer #{f_idx}] {dup_img_reason}")
                continue

            # Write temp file for OCR
            temp_img_path = temp_dir / f"temp_{idx}_{f_idx}.jpg"
            try:
                with open(temp_img_path, "wb") as f:
                    f.write(flyer["bytes"])

                # Process via RapidOCR + Taxonomy + MCA Resolver
                res = pipeline.process_image(str(temp_img_path))

                if res.is_job:
                    co_name = res.company.name or "Unknown"
                    co_canonical = res.company.canonical or co_name
                    role_name = res.roles[0].name if res.roles else "Walk-in"
                    city_detected = res.location.city or city_name.title()
                    roles_list = [r.name for r in res.roles]

                    is_walkin = (res.job_type == "walk_in_interview")
                    source_type = "Walk-in Interview Flyer" if is_walkin else "Job Vacancy Flyer (Direct Hiring)"

                    # Clean role / title
                    if is_walkin:
                        job_title = role_name if role_name != "Walk-in" else f"{co_name} Walk-in Drive"
                        walkin_date_val = res.date  # Only if explicitly extracted from flyer
                        walkin_time_val = f"{res.time.start or ''} - {res.time.end or ''}".strip(" -")
                    else:
                        job_title = role_name if role_name != "Walk-in" else f"{co_name} Hiring Vacancy"
                        walkin_date_val = None
                        walkin_time_val = ""

                    # ── Deduplication Post-Check 2: Job Content & Signatures Check ──
                    is_dup_job, dup_job_reason = deduplicator.is_job_duplicate(
                        company=co_canonical,
                        title=job_title,
                        roles=roles_list,
                        location=city_detected,
                        walkin_date=walkin_date_val,
                        contact_email=res.contact_email,
                        contact_phone=res.contact_phone
                    )

                    if is_dup_job:
                        print(f"  ⏭️ [Skip Duplicate Job] {co_name}: {dup_job_reason}")
                        continue

                    # Generate unique dedup hash
                    hash_src = f"{co_canonical}_{job_title}_{walkin_date_val}_{res.contact_email}_{res.contact_phone}_{city_name}"
                    dedup_hash = hashlib.sha256(hash_src.encode("utf-8")).hexdigest()[:16]

                    # Format clean job record with direct web flyer image URL
                    job_record = {
                        "id": f"walkin_{dedup_hash}" if is_walkin else f"job_{dedup_hash}",
                        "dedup_hash": dedup_hash,
                        "source": "Image Flyer (Proxy Scrape)",
                        "source_type": source_type,
                        "company": co_name,
                        "company_canonical": co_canonical,
                        "company_confidence": res.company.confidence,
                        "company_method": res.company.detection_method,
                        "title": job_title,
                        "roles": roles_list,
                        "location": city_detected,
                        "state": res.location.state or "India",
                        "venue": res.location.venue,
                        "pincode": res.location.pincode,
                        "date_posted": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "walkin_date": walkin_date_val,
                        "walkin_time": walkin_time_val,
                        "experience": res.experience if isinstance(res.experience, str) and res.experience else "Fresher / Experienced",
                        "salary": res.salary if isinstance(res.salary, str) and res.salary else "Competitive / Best in Industry",
                        "contact_email": res.contact_email,
                        "contact_phone": res.contact_phone,
                        "apply_url": res.apply_url,
                        "flyer_image_url": flyer["url"] if not flyer["url"].endswith("...[base64]") else None,
                        "raw_flyer_src": flyer["raw_url"] if len(flyer["raw_url"]) < 500 else None,
                        "qr_decoded": res.qr.raw_data if res.qr.found else None,
                        "signal_score": res.signal_score,
                        "confidence": res.confidence
                    }

                    # Register new job into deduplicator
                    deduplicator.register_new_job(job_record, flyer["bytes"], flyer.get("url"))
                    existing_jobs.append(job_record)
                    new_jobs_count += 1
                    city_extracted_count += 1
                    status_tag = "Walk-in" if is_walkin else "Direct Hiring"
                    print(f"  ✅ [New {status_tag} #{new_jobs_count}] {co_name} | {job_title} | {city_detected} (Date: {walkin_date_val or 'N/A'})")
                else:
                    # ── Non-Job / Flyer not detected by OCR ──
                    if flyer_url and not flyer_url.endswith("...[base64]") and flyer_url not in seen_not_extracted_urls:
                        seen_not_extracted_urls.add(flyer_url)
                        not_extracted_images.append({
                            "city": city_name,
                            "url": flyer_url,
                            "reason": f"No hiring signal detected (score: {res.signal_score:.2f})",
                            "ocr_preview": (res.raw_ocr_text[:120] if res.raw_ocr_text else "").strip()
                        })

            except Exception as e:
                print(f"  ⚠️ Extraction error on flyer {f_idx}: {e}")
                if flyer_url and not flyer_url.endswith("...[base64]") and flyer_url not in seen_not_extracted_urls:
                    seen_not_extracted_urls.add(flyer_url)
                    not_extracted_images.append({
                        "city": city_name,
                        "url": flyer_url,
                        "reason": f"Extraction error: {str(e)[:100]}",
                        "ocr_preview": ""
                    })
            finally:
                temp_img_path.unlink(missing_ok=True)

        # ── Per-City Extraction Summary ──
        print(f"\n  📊 [{city_name.upper()} SUMMARY]")
        print(f"     📥 Total Flyers Processed: {len(flyers)}")
        print(f"     ✨ Walk-in Jobs Extracted: {city_extracted_count}")
        print(f"     💾 Cumulative Database Jobs: {len(existing_jobs)} (+{new_jobs_count} this run)")
        print(f"     💳 Total Proxy Credits Used: {credit_counter['total']}")
        print(f"     📁 Unextracted Images Logged: {len(not_extracted_images)}")
        print("-" * 65)

        # Update checkpoint and save unextracted images after each city
        progress["city_cursor"] = (start_cursor + idx + 1) % len(city_queue)
        progress["total_jobs_scraped"] = len(existing_jobs)
        progress["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
        save_progress(progress)
        save_jobs(existing_jobs)
        save_not_extracted_images(not_extracted_images)

    # Clean temp dir
    try:
        for p in temp_dir.glob("*.jpg"):
            p.unlink(missing_ok=True)
        temp_dir.rmdir()
    except Exception:
        pass

    # ── Update Credit Tracker ──
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    credit_tracker.setdefault("daily_log", []).append({
        "date": today_str,
        "key_index": key_index + 1,
        "credits_used": credit_counter["total"],
        "jobs_extracted": new_jobs_count,
        "cities_processed": min(idx + 1, len(reordered_queue))
    })
    save_credit_tracker(credit_tracker)

    total_time = time.time() - start_time
    save_not_extracted_images(not_extracted_images)
    print("\n" + "=" * 80)
    print(f"  🏆 FLYER IMAGE EXTRACTOR RUN COMPLETE")
    print(f"  ⏱️ Total Execution Time: {total_time / 60:.1f} minutes")
    print(f"  ✨ New Walk-ins Added: {new_jobs_count}")
    print(f"  💾 Total Database Walk-ins: {len(existing_jobs):,}")
    print(f"  📁 Output Saved: {OUTPUT_JOBS_FILE}")
    print(f"  📁 Unextracted Links Saved: {NOT_EXTRACTED_JSON} & {NOT_EXTRACTED_TXT} ({len(not_extracted_images)} links)")
    print("=" * 80)

    # ── Print Credit Dashboard ──
    print_credit_dashboard(credit_tracker, credit_counter["total"], key_index)


if __name__ == "__main__":
    asyncio.run(main())
