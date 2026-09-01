"""
ALL_CAREER — Google Images Walk-in Extraction Workflow.
Combines:
1. 50-City Multi-Tier Scraping (Top 10 Metros @ 100 images, Next 40 Cities @ 10 images)
2. 5-Hour 50-Minute Watchdog Timer with Checkpoint Resuming
3. Memory-Streamed RapidOCR + MCA Company Resolution + QR Decoding
4. Zero-Storage Image URL Linking for UI Flyer Viewers
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
from datetime import datetime, timezone
from urllib.parse import quote_plus
from typing import Optional, List, Dict, Set, Tuple, Any

sys.stdout.reconfigure(encoding='utf-8')

# Ensure root is in path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from image_pipeline.pipeline import ImageToJobPipeline
from image_pipeline.ingestion.deduplicator import JobDeduplicator
from playwright.async_api import async_playwright

# ── 50 Indian Cities Target Matrix ──
TOP_10_CITIES = [
    "chennai", "bengaluru", "hyderabad", "pune", "mumbai",
    "delhi", "noida", "gurgaon", "kolkata", "ahmedabad"
]

NEXT_40_CITIES = [
    "coimbatore", "madurai", "trichy", "salem", "kochi",
    "trivandrum", "kozhikode", "visakhapatnam", "vijayawada", "guntur",
    "tirupati", "mysuru", "hubli", "mangalore", "jaipur",
    "indore", "bhopal", "chandigarh", "mohali", "lucknow",
    "kanpur", "varanasi", "agra", "patna", "bhubaneswar",
    "cuttack", "nagpur", "nashik", "aurangabad", "surat",
    "vadodara", "rajkot", "ranchi", "jamshedpur", "raipur",
    "dehradun", "guwahati", "gwalior", "ludhiana", "vellore"
]

PROGRESS_FILE = ROOT_DIR / "data" / "walkin_scrape_progress.json"
OUTPUT_JOBS_FILE = ROOT_DIR / "scraped_image_walkin_jobs.json"
MAX_RUN_SECONDS = 5 * 3600 + 50 * 60  # 5 hours 50 minutes watchdog limit


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


def fetch_bing_image_candidates_sync(city: str, max_count: int = 50) -> list:
    """Fetch high-res direct flyer image URLs from Bing search."""
    queries = [
        f'"{city}" ("walk in interview" OR "walkin drive") flyer',
        f'"{city}" "walk in interview" "hiring" poster',
        f'"{city}" "walk-in interview" "experience" "salary"',
        f'site:blogspot.com "{city}" "walk in interview"',
        f'"{city}" "walk in interview" 2026',
        f'"{city}" "walking interview" hiring'
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


async def scrape_google_images_for_city(
    page,
    city: str,
    max_images: int = 100,
    last24h: bool = False
) -> list:
    """Scrape flyer image URLs and byte buffers for a given city query with multi-engine resilience."""
    query = f"{city} walk in interview flyer poster"
    tbs_param = "&tbs=qdr:w" if last24h else ""
    search_url = f"https://www.google.com/search?q={quote_plus(query)}&udm=2{tbs_param}"

    print(f"\n🔍 Searching Image Flyers for '{city}': '{query}' (Max: {max_images})...")
    image_urls = []

    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(1.5)

        # Check if blocked by Google Sorry/Captcha
        current_url = page.url
        if "sorry/index" not in current_url:
            # Dismiss overlays
            for btn_txt in ["Accept all", "I agree", "Stay signed out"]:
                try:
                    btn = await page.query_selector(f'button:has-text("{btn_txt}")')
                    if btn:
                        await btn.click()
                        await asyncio.sleep(0.5)
                except Exception:
                    pass

            # Scroll
            scroll_loops = min(8, max(3, max_images // 15))
            for _ in range(scroll_loops):
                await page.mouse.wheel(0, 1500)
                await asyncio.sleep(0.8)

            image_urls = await page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                const imgs = document.querySelectorAll('img');
                for (const img of imgs) {
                    const src = img.src || img.getAttribute('data-src') || img.getAttribute('src') || img.getAttribute('data-iurl') || img.currentSrc;
                    if (!src) continue;
                    if (src.includes('google.com/logos') || src.includes('favicon.ico') || src.includes('cleardot.gif') || src.includes('google_logo')) continue;
                    if (src.startsWith('data:image/') || src.startsWith('http')) {
                        if (!seen.has(src) && src.length > 60) {
                            seen.add(src);
                            results.push(src);
                        }
                    }
                }
                return results;
            }''')
    except Exception as e:
        print(f"  ⚠️ Google Images note: {e}")

    # Fallback to Bing direct high-res stream if Google returned few images
    if len(image_urls) < 10:
        print(f"  ⚡ Activating high-res multi-engine stream for '{city}'...")
        bing_urls = await fetch_bing_image_candidates(city, max_count=max_images)
        for u in bing_urls:
            if u not in image_urls:
                image_urls.append(u)

    print(f"📷 Found {len(image_urls)} candidate image streams for '{city}'")

    downloaded_images = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    conn = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(headers=headers, connector=conn) as session:
        tasks = [download_image_buffer(session, u, city) for u in image_urls[:max_images]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, dict) and res:
                downloaded_images.append(res)

    print(f"📥 Successfully captured {len(downloaded_images)} high-res flyer buffers for '{city}'")
    return downloaded_images


async def main():
    start_time = time.time()
    progress = load_progress()
    existing_jobs = load_existing_jobs()
    deduplicator = JobDeduplicator(existing_jobs)

    print("=" * 80)
    print(f"🚀 ALL_CAREER — 50-CITY GOOGLE IMAGE EXTRACTOR WORKFLOW")
    print(f"📅 Start Time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ Maximum Run Budget: 5 Hours 50 Minutes ({MAX_RUN_SECONDS}s)")
    print(f"📊 Previously Scraped Jobs: {len(existing_jobs):,}")
    print("=" * 80)

    # Initialize OCR Pipeline
    pipeline = ImageToJobPipeline(enable_ai_verification=False)

    # Build queue: Top 10 Metros (100 images) + Next 40 Cities (10 images)
    city_queue = []
    for c in TOP_10_CITIES:
        city_queue.append({"city": c, "max_images": 100, "tier": "Tier-1"})
    for c in NEXT_40_CITIES:
        city_queue.append({"city": c, "max_images": 10, "tier": "Tier-2/3"})

    # Checkpoint rotation cursor
    start_cursor = progress.get("city_cursor", 0) % len(city_queue)
    reordered_queue = city_queue[start_cursor:] + city_queue[:start_cursor]

    new_jobs_count = 0
    temp_dir = ROOT_DIR / "data" / "temp_ocr_buffers"
    temp_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1920,1080"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

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

            flyers = await scrape_google_images_for_city(page, city_name, max_images=max_imgs, last24h=False)

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
            print(f"\n📊 [{city_name.upper()} SUMMARY]")
            print(f"   📥 Total Flyers Processed: {len(flyers)}")
            print(f"   ✨ Walk-in Jobs Extracted: {city_extracted_count}")
            print(f"   💾 Cumulative Database Jobs: {len(existing_jobs)} (+{new_jobs_count} this run)")
            print("-" * 65)

            # Update checkpoint after each city
            progress["city_cursor"] = (start_cursor + idx + 1) % len(city_queue)
            progress["total_jobs_scraped"] = len(existing_jobs)
            progress["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
            save_progress(progress)
            save_jobs(existing_jobs)

        await browser.close()

    # Clean temp dir
    try:
        for p in temp_dir.glob("*.jpg"):
            p.unlink(missing_ok=True)
        temp_dir.rmdir()
    except Exception:
        pass

    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"🏆 GOOGLE IMAGE EXTRACTOR RUN COMPLETE")
    print(f"⏱️ Total Execution Time: {total_time / 60:.1f} minutes")
    print(f"✨ New Walk-ins Added: {new_jobs_count}")
    print(f"💾 Total Database Walk-ins: {len(existing_jobs):,}")
    print(f"📁 Output Saved: {OUTPUT_JOBS_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
