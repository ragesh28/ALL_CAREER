"""
ALL_CAREER — Google Images Walk-in Flyer Extractor Workflow (v4.5: HasData 100-Image Engine).
Combines:
1. Top 20 Indian Metros & Tech Hubs @ 100 Images per City
2. HasData Google Images Engine (100 images per single request, 5 credits/city)
3. Dynamic Multi-Key Rotation across 4 accounts with automatic failover
4. 1,000+ Role Taxonomy with compound suffix expansion ("Python Developer", "MERN Developer", etc.)
5. "Unknown Company" fallback (never drop flyers when company is unlisted)
6. Queried City fallback for locations (never drop flyers when city is unwritten)
7. Walk-in interview vs Direct hiring classification (is_walkin: True/False)
8. Direct image links on top source (flyer_image_url, url, raw_flyer_src)
9. Dual-Database Sync: scraped_image_walkin_jobs.json + data/index/walkin_jobs.json
10. Live per-request credit progress tracker with quota gauge
11. Automatic 1-Month Billing Cycle Reset (auto-resets to 100% full credits each month)
12. Workflow End Credit & Job Dashboard (Console + GitHub Actions Step Summary)
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

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout.reconfigure(encoding='utf-8')

# Ensure root is in path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from image_pipeline.pipeline import ImageToJobPipeline
from image_pipeline.ingestion.deduplicator import JobDeduplicator

# ═════════════════════════════════════════════════════════════════════════════
# TOP 20 INDIAN CITIES (100 Images per City)
# ═════════════════════════════════════════════════════════════════════════════
TOP_20_CITIES = [
    "chennai", "bengaluru", "hyderabad", "pune", "mumbai",
    "delhi", "noida", "gurgaon", "kolkata", "ahmedabad",
    "coimbatore", "kochi", "chandigarh", "jaipur", "lucknow",
    "indore", "madurai", "trichy", "visakhapatnam", "nagpur"
]

PROGRESS_FILE = ROOT_DIR / "data" / "walkin_scrape_progress.json"
OUTPUT_JOBS_FILE = ROOT_DIR / "scraped_image_walkin_jobs.json"
WALKIN_INDEX_FILE = ROOT_DIR / "data" / "index" / "walkin_jobs.json"
CREDIT_TRACKER_FILE = ROOT_DIR / "data" / "hasdata_credit_tracker.json"
NOT_EXTRACTED_JSON = ROOT_DIR / "google_image_not_extracted.json"
NOT_EXTRACTED_TXT = ROOT_DIR / "google_image_not_extracted.txt"
MAX_RUN_SECONDS = 5 * 3600 + 50 * 60  # 5 hours 50 minutes watchdog limit

# Blocked foreign job aggregator domains & template websites
BLOCKED_DOMAINS = [
    "binhadis.com", "gccwalkins.com", "mailyourjob.com", "gulflive.com",
    "dubaivacancy.ae", "naukrigulf.com", "khaleejtimes.com", "gulfjobvacancy.in",
    "livegulfjobs.com", "jobsatgulf.org", "gulfjobpaper.com", "iswkoman.com",
    "freepik.com", "canva.com", "shutterstock.com", "designwiz.com",
    "graphicsfamily.com", "alamy.com", "vecteezy.com", "istockphoto.com",
    "behance.net", "slidesharecdn.com", "d1csarkz8obe9u.cloudfront.net"
]

BLOCKED_URL_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r'/dubai/', r'/uae/', r'/qatar/', r'/kuwait/', r'/oman/', r'/saudi/',
        r'/sharjah/', r'/fujairah/', r'/abu-?dhabi/', r'/gulf/', r'/middle-?east/',
        r'/poland/', r'gcc-', r'dubai-', r'walk-in-interview-in-dubai',
        r'dubai-job', r'gulf-job'
    ]
]


def is_blocked_flyer_url(url: str) -> bool:
    """Check if flyer URL is from a foreign domain or template site."""
    if not url:
        return False
    u_low = url.lower()
    for d in BLOCKED_DOMAINS:
        if d in u_low:
            return True
    for pat in BLOCKED_URL_PATTERNS:
        if pat.search(url):
            return True
    return False


# ═════════════════════════════════════════════════════════════════════════════
# HASDATA API CONFIGURATION & KEY ROTATION (Primary Engine)
# ═════════════════════════════════════════════════════════════════════════════
HASDATA_ENDPOINT = "https://api.hasdata.com/scrape/google/images"

DEFAULT_HASDATA_KEYS = [
    "a5fe3246-ab05-4a08-b147-b2cbc5191361",  # lraagesh28
    "a2bbef91-2979-4670-b738-bfd93512b6d5",  # lragesh104
    "19031b73-9726-44bd-af2c-1d63081dc7f4",  # lrageshmail28
    "89136063-d185-470d-b397-6088a321ef8c"   # lragesh1
]


def get_hasdata_keys() -> List[str]:
    """
    Load HasData API keys from environment variables:
    - HASDATA_API_KEYS (comma or newline separated)
    - HASDATA_API_KEY
    Falls back to user's 4 active accounts.
    """
    keys = []
    for env_name in ["HASDATA_API_KEYS", "HASDATA_API_KEY", "HASDATA_KEYS"]:
        val = os.environ.get(env_name, "").strip()
        if val:
            for k in re.split(r'[\r\n,]+', val):
                k = k.strip()
                if k and k not in keys:
                    keys.append(k)
    if not keys:
        keys = list(DEFAULT_HASDATA_KEYS)
    return keys


_hasdata_key_cursor = 0


def get_next_hasdata_key(keys: List[str]) -> Tuple[str, int]:
    """Rotate sequentially across available HasData keys."""
    global _hasdata_key_cursor
    if not keys:
        return "", -1
    idx = _hasdata_key_cursor % len(keys)
    _hasdata_key_cursor += 1
    return keys[idx], idx


# ═════════════════════════════════════════════════════════════════════════════
# MONTHLY CREDIT TRACKER WITH AUTOMATIC 1-MONTH RESET & LIVE PROGRESS
# ═════════════════════════════════════════════════════════════════════════════
def check_and_reset_monthly_cycle(tracker: dict, key_count: int) -> Tuple[dict, bool]:
    """
    Evaluate if 1 month has ended (calendar month change or 30 days elapsed).
    When 1 month ends, archives previous cycle and resets cycle_used_credits to 0 (100% full pool).
    """
    current_utc = datetime.now(timezone.utc)
    current_month = current_utc.strftime("%Y-%m")
    current_date = current_utc.strftime("%Y-%m-%d")
    total_pool = key_count * 1000

    tracker["total_pool"] = total_pool
    tracker.setdefault("cycle_history", [])
    tracker.setdefault("daily_log", [])

    cycle_month = tracker.get("cycle_month")
    cycle_start = tracker.get("cycle_start_date")

    days_elapsed = 0
    if cycle_start:
        try:
            start_dt = datetime.strptime(cycle_start, "%Y-%m-%d")
            days_elapsed = (current_utc.date() - start_dt.date()).days
        except Exception:
            days_elapsed = 0

    is_reset = False
    if not cycle_month:
        # First time initialization
        tracker["cycle_month"] = current_month
        tracker["cycle_start_date"] = current_date
        tracker["cycle_used_credits"] = 0
    elif cycle_month != current_month or days_elapsed >= 30:
        # 1-Month Reset condition met
        is_reset = True
        tracker["cycle_history"].append({
            "month": cycle_month,
            "start_date": cycle_start or current_date,
            "end_date": current_date,
            "credits_used": tracker.get("cycle_used_credits", 0),
            "total_pool": tracker.get("total_pool", total_pool)
        })
        tracker["cycle_used_credits"] = 0
        tracker["cycle_month"] = current_month
        tracker["cycle_start_date"] = current_date

    return tracker, is_reset


def load_credit_tracker(key_count: int) -> Tuple[dict, bool]:
    """Load persistent credit tracker and evaluate monthly auto-reset."""
    tracker = {}
    if CREDIT_TRACKER_FILE.exists():
        try:
            with open(CREDIT_TRACKER_FILE, "r", encoding="utf-8") as f:
                tracker = json.load(f)
        except Exception:
            tracker = {}

    tracker, is_reset = check_and_reset_monthly_cycle(tracker, key_count)
    save_credit_tracker(tracker)
    return tracker, is_reset


def save_credit_tracker(tracker: dict):
    """Save credit tracker to JSON file, keeping the latest 60 daily log entries."""
    if "daily_log" in tracker and len(tracker["daily_log"]) > 60:
        tracker["daily_log"] = tracker["daily_log"][-60:]
    CREDIT_TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CREDIT_TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)


def record_request_credits(tracker: dict, credits_used: int, city_name: str):
    """Update cycle usage and daily log atomically after every request."""
    tracker["cycle_used_credits"] = tracker.get("cycle_used_credits", 0) + credits_used
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry = next((e for e in tracker.setdefault("daily_log", []) if e.get("date") == today_str), None)
    if entry:
        entry["credits_used"] += credits_used
        entry["cities_processed"] += 1
    else:
        tracker["daily_log"].append({
            "date": today_str,
            "credits_used": credits_used,
            "jobs_extracted": 0,
            "cities_processed": 1
        })
    save_credit_tracker(tracker)


def record_city_extracted_jobs(tracker: dict, new_jobs_count: int):
    """Update job count in today's daily log."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = next((e for e in tracker.setdefault("daily_log", []) if e.get("date") == today_str), None)
    if entry:
        entry["jobs_extracted"] = entry.get("jobs_extracted", 0) + new_jobs_count
        save_credit_tracker(tracker)


def render_gauge_bar(used: int, total: int, width: int = 24) -> str:
    """Render a visual ASCII gauge bar for quota availability."""
    if total <= 0:
        return "[------------------------] 0.0% Available"
    avail = max(0, total - used)
    pct = min(1.0, max(0.0, avail / total))
    filled = int(round(width * pct))
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct*100:.1f}% Available ({avail:,} / {total:,})"


def print_request_progress(
    city_idx: int,
    total_cities: int,
    city_name: str,
    req_credits: int,
    run_credits: int,
    tracker: dict,
    key_info: str,
    images_count: int
):
    """
    Print a live, beautiful progress box on EVERY single search request.
    Displays:
    - Current city progress (X / 20)
    - Credits consumed for this request (+5)
    - Credits used this run
    - Monthly cycle credits consumed & remaining
    - Visual quota gauge bar
    - Active key info
    """
    pool = tracker.get("total_pool", 4000)
    month_used = tracker.get("cycle_used_credits", 0)
    month_left = max(0, pool - month_used)
    gauge = render_gauge_bar(month_used, pool, width=22)
    cycle_month = tracker.get("cycle_month", "Current Month")

    print("\n  ┌" + "─" * 74 + "┐")
    header_line = f"🌐 [REQUEST PROGRESS: {city_idx}/{total_cities}]"
    print(f"  │  {header_line:<70}  │")
    print(f"  │  🏙️ City        : {city_name.upper():<22} ({images_count} candidate images returned) │")
    print(f"  │  💳 This Request : +{req_credits} Credits consumed {' '*42}│")
    print(f"  │  📊 Today's Run  : {run_credits} Credits used ({city_idx}/{total_cities} requests completed) {' '*18}│")
    print(f"  │  📅 Monthly Cycle: {month_used:,} / {pool:,} Credits consumed (Cycle: {cycle_month}) │")
    print(f"  │  ✨ Remaining    : {month_left:,} / {pool:,} Credits available │")
    print(f"  │  🔋 Quota Gauge  : {gauge:<50}  │")
    print(f"  │  🔑 Active Key   : {key_info:<50}  │")
    print("  └" + "─" * 74 + "┘")


def print_credit_dashboard(
    tracker: dict,
    run_credits: int,
    key_count: int,
    run_duration_str: str,
    stats: dict
):
    """Print grand credit and extraction dashboard at the end of the workflow."""
    pool = tracker.get("total_pool", key_count * 1000)
    month_used = tracker.get("cycle_used_credits", 0)
    month_left = max(0, pool - month_used)
    pct_left = (month_left / pool * 100) if pool > 0 else 0.0
    cycle_month = tracker.get("cycle_month", "Current Month")
    cycle_start = tracker.get("cycle_start_date", "N/A")
    gauge = render_gauge_bar(month_used, pool, width=26)
    cities_done = stats.get("cities_processed", 20)
    new_jobs = stats.get("new_jobs", 0)
    total_db = stats.get("total_db_jobs", 0)

    print("\n╔" + "═" * 76 + "╗")
    print("║        💳 HASDATA GOOGLE IMAGES MONTHLY CREDIT USAGE DASHBOARD            ║")
    print("╠" + "═" * 76 + "╣")
    print(f"║  🔑 Active API Keys       : {key_count} accounts in rotation pool {' '*(33 - len(str(key_count)))}║")
    print(f"║  🏊 Total Monthly Pool    : {pool:,} Credits {' '*(45 - len(f'{pool:,}'))}║")
    print(f"║  📊 This Run Consumed     : {run_credits:,} Credits ({cities_done} cities × 5 credits) {' '*(27 - len(f'{run_credits:,}') - len(str(cities_done)))}║")
    print(f"║  📅 Current Month Cycle   : {cycle_month} (Cycle Started: {cycle_start}) {' '*(27 - len(cycle_month) - len(cycle_start))}║")
    print(f"║  📈 Month-to-Date Used    : {month_used:,} / {pool:,} Credits ({100 - pct_left:.1f}% used) │")
    print(f"║  ✨ Monthly Credits Left  : {month_left:,} / {pool:,} Credits ({pct_left:.1f}% Available) │")
    print(f"║  🔋 Quota Gauge           : {gauge:<50} ║")
    print(f"║  ⚡ Image Downloads       : 0 Credits (Direct host stream, 100% free)          ║")
    print("╠" + "═" * 76 + "╣")
    print("║  🏆 WORKFLOW EXTRACTION SUMMARY:                                           ║")
    print(f"║  ⏱️ Run Duration          : {run_duration_str:<50} ║")
    print(f"║  🏙️ Cities Processed      : {cities_done} / {stats.get('total_cities', 20)} {' '*(48 - len(str(cities_done)) - len(str(stats.get('total_cities', 20))))}║")
    print(f"║  ✨ New Walk-ins Added    : {new_jobs} jobs {' '*(48 - len(str(new_jobs)))}║")
    print(f"║  💾 Total Database Size   : {total_db:,} Walk-in Opportunities {' '*(32 - len(f'{total_db:,}'))}║")
    print("║  📁 Database Files Synced : scraped_image_walkin_jobs.json                   ║")
    print("║                             data/index/walkin_jobs.json                      ║")
    print("╚" + "═" * 76 + "╝\n")


def write_github_step_summary(
    tracker: dict,
    run_credits: int,
    key_count: int,
    run_duration_str: str,
    stats: dict
):
    """Write rich GitHub Actions summary markdown table if running in CI."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    try:
        pool = tracker.get("total_pool", key_count * 1000)
        month_used = tracker.get("cycle_used_credits", 0)
        month_left = max(0, pool - month_used)
        pct_left = (month_left / pool * 100) if pool > 0 else 0.0
        cycle = tracker.get("cycle_month", "Current Month")
        cycle_start = tracker.get("cycle_start_date", "N/A")

        md = f"""## 💳 HasData Google Images Flyer Scraper — Run & Credit Dashboard

| Metric | Status / Value |
|:---|:---|
| **🔑 Active Keys in Pool** | `{key_count}` HasData Accounts (`{pool:,}` monthly credits) |
| **📊 Credits Used This Run** | **`{run_credits:,}` Credits** ({stats.get('cities_processed', 0)} cities × 5 credits) |
| **📅 Month-to-Date Consumed** | **`{month_used:,}` / `{pool:,}` Credits** (`{100 - pct_left:.1f}%` used) |
| **✨ Remaining Monthly Credits** | **`{month_left:,} / {pool:,}` Credits** (`{pct_left:.1f}%` available) |
| **🔄 Billing Cycle** | `{cycle}` (Started: `{cycle_start}` — **Auto-resets to `{pool:,}` credits** at month end) |
| **⏱️ Run Execution Time** | `{run_duration_str}` |
| **✨ New Walk-in Jobs Added** | **`+{stats.get('new_jobs', 0)}` jobs** |
| **💾 Total Walk-ins in Database** | **`{stats.get('total_db_jobs', 0):,}` opportunities** |

> ℹ️ **Monthly Auto-Reset**: At the end of every monthly billing cycle, the credit tracker automatically resets to **`0 / {pool:,}`** (100% full pool). Direct image downloads consume **0 credits**.
"""
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(md + "\n")
        print(f"  📄 [GitHub Actions Summary] Written to GITHUB_STEP_SUMMARY.")
    except Exception as e:
        print(f"  ⚠️ Could not write GITHUB_STEP_SUMMARY: {e}")


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
    """Save accumulated extracted jobs to scraped_image_walkin_jobs.json."""
    OUTPUT_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)


def sync_to_walkin_index(new_jobs: list):
    """Sync newly extracted walk-in and hiring flyer jobs into data/index/walkin_jobs.json."""
    if not new_jobs:
        return
    WALKIN_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing_index = []
    if WALKIN_INDEX_FILE.exists():
        try:
            with open(WALKIN_INDEX_FILE, "r", encoding="utf-8") as f:
                existing_index = json.load(f)
        except Exception:
            existing_index = []

    seen_urls = {j.get("url") for j in existing_index if j.get("url")}
    seen_hashes = {j.get("dedup_hash") for j in existing_index if j.get("dedup_hash")}

    to_add = []
    for job in new_jobs:
        u = job.get("url") or job.get("flyer_image_url")
        h = job.get("dedup_hash")
        if (u and u in seen_urls) or (h and h in seen_hashes):
            continue

        compact_entry = {
            "title": job.get("title") or "Walk-in Opportunity",
            "company": job.get("company") or "Unknown Company",
            "location": job.get("location") or "India",
            "date_posted": job.get("date_posted") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "url": u,
            "source": "Google Images",
            "source_type": job.get("source_type") or "Walk-in Interview Flyer",
            "is_walkin": bool(job.get("is_walkin")),
            "walkin_date": job.get("walkin_date"),
            "walkin_time": job.get("walkin_time") or "",
            "flyer_image_url": job.get("flyer_image_url") or u,
            "contact_phone": job.get("contact_phone") or "",
            "contact_email": job.get("contact_email") or "",
            "experience": job.get("experience") or "Fresher / Experienced",
            "salary": job.get("salary") or "Best in Industry",
            "venue": job.get("venue") or "",
            "dedup_hash": h
        }
        to_add.append(compact_entry)
        if u:
            seen_urls.add(u)
        if h:
            seen_hashes.add(h)

    if to_add:
        combined = to_add + existing_index
        with open(WALKIN_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(combined, f, separators=(',', ':'), ensure_ascii=False)
        print(f"  ⚡ [Index Synced] Added {len(to_add)} flyer jobs to data/index/walkin_jobs.json (Total: {len(combined):,})")


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

    urls = [it["url"] for it in items if it.get("url") and it["url"].startswith("http")]
    with open(NOT_EXTRACTED_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(urls) + ("\n" if urls else ""))


# ═════════════════════════════════════════════════════════════════════════════
# HASDATA GOOGLE IMAGES SCRAPER ENGINE (100 High-Res Images per Request)
# ═════════════════════════════════════════════════════════════════════════════
def fetch_flyer_items_via_hasdata_sync(
    query: str,
    api_keys: List[str],
    max_count: int = 100
) -> Tuple[List[Dict[str, Any]], int, str]:
    """
    Fetch up to 100 high-res image flyer candidates from Google Images via HasData.
    - Consumes exactly 5 credits per search request.
    - Delivers up to 100 images with original link, thumbnail, title, and landing page.
    - Automatically rotates to next key if any key hits quota/rate limits.
    Returns: (clean_items, credits_used, key_info_str)
    """
    params = {
        "q": query,
        "location": "India",
        "gl": "in",
        "hl": "en",
        "tbs": "qdr:d",  # Past 24 hours fresh flyers
        "deviceType": "desktop"
    }

    credits_used = 0
    raw_images = []
    key_info = "Unknown"

    for attempt in range(len(api_keys)):
        key, key_idx = get_next_hasdata_key(api_keys)
        headers = {
            "x-api-key": key,
            "Content-Type": "application/json"
        }
        key_info = f"Key #{key_idx+1} ({key[:8]}...)"

        try:
            resp = requests.get(
                HASDATA_ENDPOINT,
                headers=headers,
                params=params,
                timeout=50
            )

            if resp.status_code == 200:
                credits_used = 5
                data = resp.json()
                raw_images = data.get("imagesResults") or data.get("images") or data.get("imageResults") or []
                break
            elif resp.status_code in (401, 403, 429):
                print(f"     ⚠️ HasData [{key_info}] Quota / Auth issue (HTTP {resp.status_code}). Rotating to next key...")
                continue
            else:
                print(f"     ⚠️ HasData [{key_info}] HTTP {resp.status_code}: {resp.text[:150]}")
                continue
        except Exception as e:
            print(f"     ⚠️ HasData connection error on {key_info}: {e}")
            continue

    # Clean and structure candidate flyer items
    clean_items = []
    seen = set()

    for img in raw_images:
        original = (img.get("original") or "").strip()
        thumbnail = (img.get("thumbnail") or "").strip()
        landing = (img.get("link") or "").strip()
        title = (img.get("title") or "").strip()

        primary_url = original if original and original.startswith("http") else thumbnail
        if not primary_url:
            continue

        if is_blocked_flyer_url(primary_url) or is_blocked_flyer_url(landing):
            continue

        if primary_url in seen:
            continue
        seen.add(primary_url)

        clean_items.append({
            "original": original,
            "thumbnail": thumbnail,
            "landing_url": landing,
            "title_hint": title,
            "source_site": img.get("source") or "Google Images"
        })

    return clean_items[:max_count], credits_used, key_info


# ═════════════════════════════════════════════════════════════════════════════
# IMAGE BUFFER DOWNLOAD (Dual-source: Original with Thumbnail Fallback)
# ═════════════════════════════════════════════════════════════════════════════
async def download_flyer_buffer(
    session: aiohttp.ClientSession,
    item: dict,
    city: str
) -> Optional[dict]:
    """
    Concurrently download image buffer.
    Attempts original high-res URL first; if blocked or HTML returned, falls back to Google thumbnail.
    """
    original_url = item.get("original")
    thumb_url = item.get("thumbnail")
    landing_url = item.get("landing_url") or original_url

    # Attempt 1: Download Original High-Res Image
    if original_url and original_url.startswith("http"):
        try:
            async with session.get(original_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    # Verify real image buffer (JPEG, PNG, WebP)
                    if len(content) >= 4000 and not content.startswith(b"<!DOCTYPE") and not content.startswith(b"<html"):
                        return {
                            "url": original_url,
                            "raw_url": original_url,
                            "landing_url": landing_url,
                            "title_hint": item.get("title_hint", ""),
                            "bytes": content,
                            "city": city
                        }
        except Exception:
            pass

    # Attempt 2: Fallback to Google CDN Thumbnail (100% reliable image delivery)
    if thumb_url and thumb_url.startswith("http"):
        try:
            async with session.get(thumb_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    if len(content) >= 4000:
                        return {
                            "url": original_url or thumb_url,
                            "raw_url": thumb_url,
                            "landing_url": landing_url,
                            "title_hint": item.get("title_hint", ""),
                            "bytes": content,
                            "city": city
                        }
        except Exception:
            pass

    return None


# ═════════════════════════════════════════════════════════════════════════════
# CITY IMAGE SCRAPER WITH LIVE PER-REQUEST PROGRESS DISPLAY
# ═════════════════════════════════════════════════════════════════════════════
async def scrape_images_for_city(
    hasdata_keys: list,
    city: str,
    city_idx: int,
    total_cities: int,
    tracker: dict,
    credit_counter: dict,
    max_images: int = 100
) -> list:
    """
    Scrape 100 flyer candidate images for a city using HasData (5 credits per city).
    Outputs live per-request progress box and updates tracker immediately.
    """
    query = f'"walk in interview" {city} hiring poster'

    candidate_items, credits_used, key_info = await asyncio.to_thread(
        fetch_flyer_items_via_hasdata_sync,
        query,
        hasdata_keys,
        max_count=max_images
    )

    # Record credits and update progress
    credit_counter["total"] += credits_used
    record_request_credits(tracker, credits_used, city)

    # Live progress box on EVERY request
    print_request_progress(
        city_idx=city_idx,
        total_cities=total_cities,
        city_name=city,
        req_credits=credits_used,
        run_credits=credit_counter["total"],
        tracker=tracker,
        key_info=key_info,
        images_count=len(candidate_items)
    )

    # Concurrent buffer download
    downloaded = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }
    conn = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(headers=headers, connector=conn) as session:
        tasks = [download_flyer_buffer(session, item, city) for item in candidate_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, dict) and res:
                downloaded.append(res)

    print(f"  📥 Successfully downloaded {len(downloaded)} valid flyer image buffers for '{city}'")
    return downloaded


# ═════════════════════════════════════════════════════════════════════════════
# MAIN WORKFLOW
# ═════════════════════════════════════════════════════════════════════════════
async def main():
    start_time = time.time()
    progress = load_progress()
    existing_jobs = load_existing_jobs()
    deduplicator = JobDeduplicator(existing_jobs)

    init_not_extracted_files()
    not_extracted_images = []
    seen_not_extracted_urls = set()

    hasdata_keys = get_hasdata_keys()
    credit_counter = {"total": 0}

    # Load credit tracker and evaluate 1-Month Auto-Reset
    tracker, is_reset = load_credit_tracker(len(hasdata_keys))

    print("=" * 80)
    print("  🚀 ALL_CAREER — HASDATA GOOGLE IMAGES WALK-IN EXTRACTOR (v4.5)")
    print(f"  📅 Start Time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  ⏱️ Maximum Run Budget: 5 Hours 50 Minutes ({MAX_RUN_SECONDS}s)")
    print(f"  📊 Previously Scraped Jobs: {len(existing_jobs):,}")
    print(f"  🔑 Active HasData Keys: {len(hasdata_keys)} keys in rotation pool ({tracker.get('total_pool', 4000):,} monthly credits)")
    print(f"  🏙️ Target Cities: Top 20 Indian Cities @ 100 images each")
    print(f"  📅 Billing Cycle: {tracker.get('cycle_month', 'N/A')} (Started: {tracker.get('cycle_start_date', 'N/A')})")
    print(f"  💳 Cycle Credits Used: {tracker.get('cycle_used_credits', 0):,} / {tracker.get('total_pool', 4000):,} ({tracker.get('total_pool', 4000) - tracker.get('cycle_used_credits', 0):,} remaining)")
    print("=" * 80)

    if is_reset:
        c_month = tracker.get('cycle_month', 'N/A')
        p_str = f"{tracker.get('total_pool', 4000):,}"
        print("\n╔" + "═" * 76 + "╗")
        print(f"║  🔄 MONTHLY CREDIT RESET TRIGGERED (NEW CYCLE: {c_month})")
        print(f"║  Previous billing cycle archived. Quota reset to {p_str} / {p_str} (100% full pool)!")
        print("╚" + "═" * 76 + "╝\n")

    # Initialize OCR Pipeline
    pipeline = ImageToJobPipeline(enable_ai_verification=False)

    # Reorder queue based on saved cursor checkpoint
    start_cursor = progress.get("city_cursor", 0) % len(TOP_20_CITIES)
    city_queue = TOP_20_CITIES[start_cursor:] + TOP_20_CITIES[:start_cursor]

    new_jobs_this_run = []
    temp_dir = ROOT_DIR / "data" / "temp_ocr_buffers"
    temp_dir.mkdir(parents=True, exist_ok=True)

    walkin_keywords = [
        "walk-in", "walk in", "walkin", "walking interview", "walk-in drive",
        "walk in drive", "walkin drive", "spot offer", "spot offers", "selection drive",
        "open drive", "mega walk-in", "mega walk in", "direct walkin"
    ]

    for idx, city_name in enumerate(city_queue):
        elapsed = time.time() - start_time
        if elapsed >= MAX_RUN_SECONDS:
            print(f"\n⏳ Watchdog Triggered: 5h 50m reached ({elapsed:.1f}s). Checkpointing...")
            progress["city_cursor"] = (start_cursor + idx) % len(TOP_20_CITIES)
            break

        city_extracted_count = 0
        print(f"\n{'='*25} [{idx+1}/{len(city_queue)}] {city_name.upper()} (100 Images) {'='*25}")

        flyers = await scrape_images_for_city(
            hasdata_keys=hasdata_keys,
            city=city_name,
            city_idx=idx + 1,
            total_cities=len(city_queue),
            tracker=tracker,
            credit_counter=credit_counter,
            max_images=100
        )

        city_new_jobs = []

        for f_idx, flyer in enumerate(flyers, 1):
            flyer_url = flyer.get("url") or flyer.get("raw_url") or ""
            landing_url = flyer.get("landing_url") or flyer_url

            if is_blocked_flyer_url(flyer_url):
                continue

            # Byte / URL duplicate check
            is_dup_img, dup_img_reason = deduplicator.is_image_duplicate(flyer["bytes"], flyer_url)
            if is_dup_img:
                print(f"  ⏭️ [Skip Existing Flyer #{f_idx}] {dup_img_reason}")
                continue

            temp_img_path = temp_dir / f"temp_{idx}_{f_idx}.jpg"
            try:
                with open(temp_img_path, "wb") as f:
                    f.write(flyer["bytes"])

                # Run OCR & Extraction Pipeline
                res = pipeline.process_image(str(temp_img_path), source_url=flyer_url)

                if res.is_job:
                    raw_ocr = (res.raw_ocr_text or "").lower()

                    # 1. Company Name: fallback to "Unknown Company"
                    co_name = res.company.name if (res.company and res.company.name) else "Unknown Company"
                    co_canonical = res.company.canonical if (res.company and res.company.canonical) else co_name

                    # 2. Location: OCR detected or queried city fallback
                    if res.location and res.location.city:
                        city_detected = res.location.city
                    else:
                        city_detected = city_name.title()

                    # 3. Role: Extracted role from 1,000+ taxonomy with compound expansion
                    if res.roles and len(res.roles) > 0:
                        role_name = res.roles[0].name
                        roles_list = [r.name for r in res.roles]
                    else:
                        role_name = "Walk-in Opportunity"
                        roles_list = []

                    # 4. Walk-in vs Direct Hiring determination
                    is_walkin = any(w in raw_ocr for w in walkin_keywords) or (res.job_type == "walk_in_interview")
                    source_type = "Walk-in Interview Flyer" if is_walkin else "Direct Hiring Flyer"

                    # 5. Job Title
                    if role_name and role_name != "Walk-in Opportunity":
                        job_title = role_name
                    elif is_walkin:
                        job_title = f"{co_name} Walk-in Drive" if co_name != "Unknown Company" else "Walk-in Interview Drive"
                    else:
                        job_title = f"{co_name} Hiring Vacancy" if co_name != "Unknown Company" else "Hiring Vacancy"

                    # 6. Walk-in Date & Time
                    walkin_date_val = res.date if is_walkin else None
                    walkin_time_val = f"{res.time.start or ''} - {res.time.end or ''}".strip(" -") if is_walkin else ""

                    # 7. Deduplication Check
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

                    # Unique dedup hash
                    hash_src = f"{co_canonical}_{job_title}_{walkin_date_val}_{res.contact_email}_{res.contact_phone}_{flyer_url[:80]}"
                    dedup_hash = hashlib.sha256(hash_src.encode("utf-8")).hexdigest()[:16]

                    # 8. Clean Job Record (Direct Image URL on top source)
                    job_record = {
                        "id": f"walkin_{dedup_hash}" if is_walkin else f"job_{dedup_hash}",
                        "dedup_hash": dedup_hash,
                        "url": flyer_url,  # Direct image link on top
                        "source": "Google Images (HasData)",
                        "source_type": source_type,
                        "is_walkin": bool(is_walkin),
                        "company": co_name,
                        "company_canonical": co_canonical,
                        "company_confidence": res.company.confidence if res.company else 0.0,
                        "company_method": res.company.detection_method if res.company else "fallback_unknown",
                        "title": job_title,
                        "roles": roles_list,
                        "location": city_detected,
                        "state": (res.location.state if res.location else "India") or "India",
                        "venue": (res.location.venue if res.location else "") or "",
                        "pincode": (res.location.pincode if res.location else "") or "",
                        "date_posted": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "walkin_date": walkin_date_val,
                        "walkin_time": walkin_time_val,
                        "experience": res.experience or "Fresher / Experienced",
                        "salary": res.salary or "Best in Industry",
                        "contact_email": res.contact_email or "",
                        "contact_phone": res.contact_phone or "",
                        "apply_url": landing_url,
                        "flyer_image_url": flyer_url,
                        "raw_flyer_src": flyer.get("raw_url") or flyer_url,
                        "signal_score": res.signal_score,
                        "confidence": res.confidence
                    }

                    # Register into deduplicator & accumulated lists
                    deduplicator.register_new_job(job_record, flyer["bytes"], flyer_url)
                    existing_jobs.append(job_record)
                    new_jobs_this_run.append(job_record)
                    city_new_jobs.append(job_record)
                    city_extracted_count += 1
                    status_tag = "Walk-in" if is_walkin else "Direct Hiring"
                    print(f"  ✅ [New {status_tag} #{len(new_jobs_this_run)}] {co_name} | {job_title} | {city_detected} (Date: {walkin_date_val or 'N/A'})")

                else:
                    # Non-job image tracking
                    if flyer_url and flyer_url not in seen_not_extracted_urls:
                        seen_not_extracted_urls.add(flyer_url)
                        not_extracted_images.append({
                            "city": city_name,
                            "url": flyer_url,
                            "reason": f"No hiring signal (score: {res.signal_score:.2f})",
                            "ocr_preview": (res.raw_ocr_text[:120] if res.raw_ocr_text else "").strip()
                        })

            except Exception as e:
                print(f"  ⚠️ Extraction error on flyer {f_idx}: {e}")
                if flyer_url and flyer_url not in seen_not_extracted_urls:
                    seen_not_extracted_urls.add(flyer_url)
                    not_extracted_images.append({
                        "city": city_name,
                        "url": flyer_url,
                        "reason": f"Extraction error: {str(e)[:100]}",
                        "ocr_preview": ""
                    })
            finally:
                temp_img_path.unlink(missing_ok=True)

        # Update job counts in tracker
        record_city_extracted_jobs(tracker, city_extracted_count)

        # ── Per-City Summary & Database Sync ──
        print(f"\n  📊 [{city_name.upper()} SUMMARY]")
        print(f"     📥 Total Flyers Processed: {len(flyers)}")
        print(f"     ✨ Walk-in Jobs Extracted: {city_extracted_count}")
        print(f"     💾 Total Database Jobs: {len(existing_jobs):,} (+{len(new_jobs_this_run)} this run)")
        print(f"     💳 Total Run Credits Used: {credit_counter['total']}")
        print("-" * 65)

        # Checkpoint & sync files after each city
        progress["city_cursor"] = (start_cursor + idx + 1) % len(TOP_20_CITIES)
        progress["total_jobs_scraped"] = len(existing_jobs)
        progress["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
        save_progress(progress)
        save_jobs(existing_jobs)
        sync_to_walkin_index(city_new_jobs)
        save_not_extracted_images(not_extracted_images)

    # Clean temp dir
    try:
        for p in temp_dir.glob("*.jpg"):
            p.unlink(missing_ok=True)
        temp_dir.rmdir()
    except Exception:
        pass

    total_time = time.time() - start_time
    duration_str = f"{total_time / 60:.1f} minutes"
    save_not_extracted_images(not_extracted_images)

    stats = {
        "cities_processed": min(idx + 1, len(city_queue)),
        "total_cities": len(city_queue),
        "new_jobs": len(new_jobs_this_run),
        "total_db_jobs": len(existing_jobs)
    }

    # ── Print Grand Credit Dashboard (Console) ──
    print_credit_dashboard(
        tracker=tracker,
        run_credits=credit_counter["total"],
        key_count=len(hasdata_keys),
        run_duration_str=duration_str,
        stats=stats
    )

    # ── Write GitHub Actions Step Summary (UI Dashboard) ──
    write_github_step_summary(
        tracker=tracker,
        run_credits=credit_counter["total"],
        key_count=len(hasdata_keys),
        run_duration_str=duration_str,
        stats=stats
    )


if __name__ == "__main__":
    asyncio.run(main())
