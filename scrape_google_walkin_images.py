"""
ALL_CAREER — Google Images Walk-in Extraction Workflow (v2: ScrapingAnt Proxy + Deep Search).
Combines:
1. 50-City Deep Search Mode: "walk in interview" + "we are hiring" role-based queries
2. ScrapingAnt Proxy with 5-Key Dynamic Daily Rotation (anti-detection)
3. Top 20 Metros @ 100 images, Next 30 Cities @ 20 images
4. 30-Day Rolling Credit Usage Tracker
5. 5-Hour 50-Minute Watchdog Timer with Checkpoint Resuming
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
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus
from typing import Optional, List, Dict, Set, Tuple, Any

sys.stdout.reconfigure(encoding='utf-8')

# Ensure root is in path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from image_pipeline.pipeline import ImageToJobPipeline
from image_pipeline.ingestion.deduplicator import JobDeduplicator
from playwright.async_api import async_playwright

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
    "fresher", "IT jobs", "pharma", "java developer",
    "web developer", "customer support", "accountant",
    "HR executive", "sales executive", "marketing",
    "mechanical engineer", "electrical engineer",
    "nurse", "telecaller", "BPO", "back office", "receptionist"
]

PROGRESS_FILE = ROOT_DIR / "data" / "walkin_scrape_progress.json"
OUTPUT_JOBS_FILE = ROOT_DIR / "scraped_image_walkin_jobs.json"
CREDIT_TRACKER_FILE = ROOT_DIR / "data" / "scrapingant_credit_tracker.json"
MAX_RUN_SECONDS = 5 * 3600 + 50 * 60  # 5 hours 50 minutes watchdog limit

# ═════════════════════════════════════════════════════════════════════════════
# SCRAPINGANT PROXY — DYNAMIC 5-KEY ROTATION
# ═════════════════════════════════════════════════════════════════════════════
SCRAPINGANT_ENDPOINT = "https://api.scrapingant.com/v2/general"


def get_scrapingant_keys() -> List[str]:
    """Load all ScrapingAnt API keys from a single comma-separated env var."""
    raw = os.environ.get("SCRAPINGANT_API_KEYS", "").strip()
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


def get_todays_api_key(keys: List[str]) -> Tuple[str, int]:
    """
    Select today's API key using day-of-year rotation.
    Day 1 → Key 1, Day 2 → Key 2, ..., Day 5 → Key 5, Day 6 → Key 1 (repeats).
    This prevents ScrapingAnt from detecting multi-account usage patterns.
    """
    if not keys:
        return "", -1
    day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
    key_index = (day_of_year - 1) % len(keys)
    return keys[key_index], key_index


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
        entry for entry in tracker["daily_log"]
        if entry.get("date", "") >= cutoff
    ]
    CREDIT_TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CREDIT_TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)


def get_30day_used_credits(tracker: dict) -> int:
    """Calculate total credits used in the last 30 days."""
    return sum(entry.get("credits_used", 0) for entry in tracker.get("daily_log", []))


def print_credit_dashboard(tracker: dict, today_credits: int, key_index: int):
    """Print a beautiful credit usage dashboard at the end of the workflow."""
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
    if remaining < 5000:
        print(f"  ⚠️ WARNING: Low credit balance! Consider reducing queries.")
    elif remaining < 10000:
        print(f"  📌 Note: Credits running moderately low.")
    else:
        print(f"  ✅ Status: Healthy credit pool")
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


# ═════════════════════════════════════════════════════════════════════════════
# SCRAPINGANT PROXY — GOOGLE IMAGE SEARCH (1 Credit per Query)
# ═════════════════════════════════════════════════════════════════════════════
def fetch_google_images_via_proxy(api_key: str, query: str, max_retries: int = 2) -> List[str]:
    """
    Fetch Google Images HTML via ScrapingAnt proxy (1 credit per request).
    Parses the HTML to extract original high-res image URLs.
    Returns list of direct image URLs.
    """
    if not api_key:
        return []

    target_url = f"https://www.google.com/search?q={quote_plus(query)}&udm=2&gl=in&hl=en"
    params = {
        "url": target_url,
        "x-api-key": api_key,
        "browser": "false",
        "proxy_country": "in"
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(SCRAPINGANT_ENDPOINT, params=params, timeout=45)
            if resp.status_code == 200:
                html = resp.text
                image_urls = _extract_image_urls_from_html(html)
                print(f"    ✅ ScrapingAnt OK: {len(image_urls)} image URLs extracted (1 credit used)")
                return image_urls
            elif resp.status_code == 423:
                print(f"    ⚠️ ScrapingAnt 423: Bot detected, retrying with proxy_country=us...")
                params["proxy_country"] = "us"
                time.sleep(2)
            elif resp.status_code == 409:
                print(f"    ⚠️ ScrapingAnt 409: Concurrency limit, waiting 5s...")
                time.sleep(5)
            elif resp.status_code in (401, 403):
                print(f"    ❌ ScrapingAnt auth error: {resp.text[:100]}")
                return []
            else:
                print(f"    ⚠️ ScrapingAnt {resp.status_code}: {resp.text[:100]}")
                time.sleep(2)
        except requests.exceptions.Timeout:
            print(f"    ⏱️ ScrapingAnt timeout (attempt {attempt}/{max_retries})")
            time.sleep(3)
        except Exception as e:
            print(f"    ❌ ScrapingAnt error: {e}")
            time.sleep(2)

    return []


def _extract_image_urls_from_html(html: str) -> List[str]:
    """Extract original high-res image URLs from Google Images HTML response."""
    seen = set()
    urls = []

    # Strategy 1: JSON array pattern ["https://...jpg", width, height]
    for m in re.findall(r'\["(https?://[^"\\<>\s]+?\.(?:jpg|jpeg|png|webp)(?:\?[^"\s\\]*)?)",\s*\d+,\s*\d+\]', html, re.I):
        _add_url(m, seen, urls)

    # Strategy 2: All 3rd-party image URLs in scripts
    for m in re.findall(r'(https?://[^"\'\\<>\s]+?\.(?:jpg|jpeg|png|webp)(?:\?[^"\'\s\\]*)?)', html, re.I):
        _add_url(m, seen, urls)

    return urls


def _add_url(u: str, seen: set, urls: list):
    """Filter and add a URL to the results list."""
    try:
        clean = u.encode().decode('unicode-escape').strip()
    except Exception:
        clean = u.strip()
    clean = clean.replace('\\/', '/').replace('&amp;', '&')
    if (
        clean.startswith("http")
        and "encrypted-tbn" not in clean
        and "gstatic.com" not in clean
        and "google.com" not in clean
        and "schema.org" not in clean
        and "w3.org" not in clean
        and len(clean) > 20
        and clean not in seen
    ):
        seen.add(clean)
        urls.append(clean)


# ═════════════════════════════════════════════════════════════════════════════
# BING DIRECT STREAM FALLBACK (0 Credits — 100% Free)
# ═════════════════════════════════════════════════════════════════════════════
def fetch_bing_image_candidates_sync(city: str, max_count: int = 50) -> list:
    """Fetch high-res direct flyer image URLs from Bing search (free fallback)."""
    queries = [
        f"walk in interview in {city} flyer poster",
        f"urgent walk in interview {city} hiring poster",
        f"walk in drive {city} recruitment poster",
        f"{city} walking interview job vacancy flyer",
        f"{city} walk in interview 2026 poster",
        f"{city} walkin drive IT pharma engineering hiring"
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    found_urls = []
    seen = set()

    for q in queries:
        for first in range(1, 100, 35):
            url = f"https://www.bing.com/images/search?q={quote_plus(q)}&first={first}&count=35"
            try:
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    murls = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', resp.text)
                    for u in murls:
                        clean_u = u.replace(r'\/', '/').replace('&amp;', '&')
                        if clean_u not in seen:
                            seen.add(clean_u)
                            found_urls.append(clean_u)
            except Exception as e:
                print(f"  [Bing Error] {e}")
            if len(found_urls) >= max_count:
                break
        if len(found_urls) >= max_count:
            break

    return found_urls[:max_count]


async def fetch_bing_image_candidates(city: str, max_count: int = 50) -> list:
    return await asyncio.to_thread(fetch_bing_image_candidates_sync, city, max_count)


# ═════════════════════════════════════════════════════════════════════════════
# IMAGE DOWNLOAD (Async, In-Memory)
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
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
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
# DEEP SEARCH MODE: ScrapingAnt Proxy + Bing Fallback per City
# ═════════════════════════════════════════════════════════════════════════════
async def scrape_images_for_city_deep(
    api_key: str,
    city: str,
    max_images: int = 100,
    credit_counter: dict = None
) -> list:
    """
    Deep Search Mode: 2 proxy-backed Google Image queries per city.
    Query 1: "walk in interview" {city} hiring poster
    Query 2: "we are hiring" {city} {rotating_role}

    Uses ScrapingAnt proxy (1 credit per query = 2 credits per city).
    Falls back to Bing free stream if proxy fails.
    """
    all_image_urls = []
    seen = set()
    credits_used = 0

    # ── Query 1: Walk-in Interview Flyers ──
    query1 = f'"walk in interview" {city} hiring poster'
    print(f"\n  🔍 Query 1: {query1}")
    if api_key:
        proxy_urls = await asyncio.to_thread(fetch_google_images_via_proxy, api_key, query1)
        if proxy_urls:
            credits_used += 1
            for u in proxy_urls:
                if u not in seen:
                    seen.add(u)
                    all_image_urls.append(u)

    # ── Query 2: "We Are Hiring" + Role-Based ──
    day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
    role_index = (day_of_year - 1) % len(HIRING_ROLES)
    todays_role = HIRING_ROLES[role_index]
    query2 = f'"we are hiring" {city} {todays_role}'
    print(f"  🔍 Query 2: {query2}")
    if api_key:
        proxy_urls2 = await asyncio.to_thread(fetch_google_images_via_proxy, api_key, query2)
        if proxy_urls2:
            credits_used += 1
            for u in proxy_urls2:
                if u not in seen:
                    seen.add(u)
                    all_image_urls.append(u)

    # ── Bing Free Fallback (if proxy returned few images) ──
    if len(all_image_urls) < 15:
        print(f"  ⚡ Bing free fallback for '{city}'...")
        bing_urls = await fetch_bing_image_candidates(city, max_count=max_images)
        for u in bing_urls:
            if u not in seen:
                seen.add(u)
                all_image_urls.append(u)

    # Track credit usage
    if credit_counter is not None:
        credit_counter["total"] += credits_used

    print(f"  📷 Found {len(all_image_urls)} candidate images for '{city}' (proxy credits: {credits_used})")

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

    print(f"  📥 Downloaded {len(downloaded_images)} high-res flyer buffers for '{city}'")
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

    # ── Dynamic API Key Selection ──
    scrapingant_keys = get_scrapingant_keys()
    today_api_key, key_index = get_todays_api_key(scrapingant_keys)
    key_masked = today_api_key[:6] + "..." + today_api_key[-4:] if len(today_api_key) > 10 else "NOT SET"

    # ── Credit Counter for This Run ──
    credit_counter = {"total": 0}

    # ── Today's Rotating Role ──
    day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
    role_index = (day_of_year - 1) % len(HIRING_ROLES)
    todays_role = HIRING_ROLES[role_index]

    print("=" * 80)
    print(f"  🚀 ALL_CAREER — DEEP SEARCH GOOGLE IMAGE EXTRACTOR (v2)")
    print(f"  📅 Start Time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  ⏱️ Maximum Run Budget: 5 Hours 50 Minutes ({MAX_RUN_SECONDS}s)")
    print(f"  📊 Previously Scraped Jobs: {len(existing_jobs):,}")
    print(f"  🔑 Today's Proxy Key: Key #{key_index + 1} [{key_masked}]")
    print(f"  👔 Today's Hiring Role: \"{todays_role}\"")
    print(f"  💳 30-Day Credits Used: {get_30day_used_credits(credit_tracker):,} / {credit_tracker.get('total_pool', 50000):,}")
    print("=" * 80)

    if not today_api_key:
        print("⚠️ WARNING: No ScrapingAnt API keys found! Using Bing-only free mode.")

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

                    # ── Deduplication Post-Check 2: Job Content & Signatures Check ──
                    is_dup_job, dup_job_reason = deduplicator.is_job_duplicate(
                        company=co_canonical,
                        title=role_name,
                        roles=roles_list,
                        location=city_detected,
                        walkin_date=res.date,
                        contact_email=res.contact_email,
                        contact_phone=res.contact_phone
                    )

                    if is_dup_job:
                        print(f"  ⏭️ [Skip Duplicate Job] {co_name}: {dup_job_reason}")
                        continue

                    # Generate unique dedup hash
                    hash_src = f"{co_canonical}_{role_name}_{res.date}_{res.contact_email}_{res.contact_phone}_{city_name}"
                    dedup_hash = hashlib.sha256(hash_src.encode("utf-8")).hexdigest()[:16]

                    # Format clean job record with direct web flyer image URL
                    job_record = {
                        "id": f"walkin_{dedup_hash}",
                        "dedup_hash": dedup_hash,
                        "source": "Google Images",
                        "source_type": "Walk-in Interview Flyer",
                        "company": co_name,
                        "company_canonical": co_canonical,
                        "company_confidence": res.company.confidence,
                        "company_method": res.company.detection_method,
                        "title": role_name if role_name != "Walk-in" else f"{co_name} Walk-in Drive",
                        "roles": roles_list,
                        "location": city_detected,
                        "state": res.location.state or "India",
                        "venue": res.location.venue,
                        "pincode": res.location.pincode,
                        "date_posted": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "walkin_date": res.date,
                        "walkin_time": f"{res.time.start or ''} - {res.time.end or ''}".strip(" -"),
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
                    print(f"  ✅ [New Walk-in #{new_jobs_count}] {co_name} | {role_name} | {city_detected}")

            except Exception as e:
                print(f"  ⚠️ Extraction error on flyer {f_idx}: {e}")
            finally:
                temp_img_path.unlink(missing_ok=True)

        # ── Per-City Extraction Summary ──
        print(f"\n  📊 [{city_name.upper()} SUMMARY]")
        print(f"     📥 Total Flyers Processed: {len(flyers)}")
        print(f"     ✨ Walk-in Jobs Extracted: {city_extracted_count}")
        print(f"     💾 Cumulative Database Jobs: {len(existing_jobs)} (+{new_jobs_count} this run)")
        print(f"     💳 Proxy Credits Used So Far: {credit_counter['total']}")
        print("-" * 65)

        # Update checkpoint after each city
        progress["city_cursor"] = (start_cursor + idx + 1) % len(city_queue)
        progress["total_jobs_scraped"] = len(existing_jobs)
        progress["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
        save_progress(progress)
        save_jobs(existing_jobs)

    # Clean temp dir
    try:
        for p in temp_dir.glob("*.jpg"):
            p.unlink(missing_ok=True)
        temp_dir.rmdir()
    except Exception:
        pass

    # ── Update Credit Tracker ──
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    credit_tracker["daily_log"].append({
        "date": today_str,
        "key_index": key_index + 1,
        "credits_used": credit_counter["total"],
        "jobs_extracted": new_jobs_count,
        "cities_processed": min(idx + 1, len(reordered_queue))
    })
    save_credit_tracker(credit_tracker)

    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"  🏆 GOOGLE IMAGE EXTRACTOR RUN COMPLETE")
    print(f"  ⏱️ Total Execution Time: {total_time / 60:.1f} minutes")
    print(f"  ✨ New Walk-ins Added: {new_jobs_count}")
    print(f"  💾 Total Database Walk-ins: {len(existing_jobs):,}")
    print(f"  📁 Output Saved: {OUTPUT_JOBS_FILE}")
    print("=" * 80)

    # ── Print Credit Dashboard ──
    print_credit_dashboard(credit_tracker, credit_counter["total"], key_index)


if __name__ == "__main__":
    asyncio.run(main())
