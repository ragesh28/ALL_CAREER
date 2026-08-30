"""
ALL_CAREER — Google Images Walk-in Extraction Workflow.
Combines:
1. Google Images (glimcrawl / Playwright) with 24-hour filter (tbs=qdr:d)
2. Production Image-to-Job Pipeline (Multi-pass OCR, Taxonomy, Signal Scoring, Multi-signal Company Detection, QR Decoding)
3. Structured Output & Database Ingestion
"""
import os
import sys
import json
import asyncio
from datetime import datetime
from image_pipeline.pipeline import ImageToJobPipeline
from playwright.async_api import async_playwright
from urllib.parse import quote_plus

sys.stdout.reconfigure(encoding='utf-8')

SEARCH_QUERIES = [
    "walkin interview chennai",
    "walkin interview bangalore",
    "walkin interview hyderabad",
    "walkin drive pune",
    "walk in interview mumbai",
    "we are hiring drive fresher experience india"
]


async def scrape_google_images_for_query(
    page,
    query: str,
    save_dir: str,
    max_images: int = 15
) -> list:
    """Scrape and download high-resolution flyer images for a given query (last 24 hours)."""
    search_url = f"https://www.google.com/search?q={quote_plus(query)}&udm=2&tbs=qdr:d"
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"\n🔍 Searching Google Images for: '{query}' (Last 24 Hours)...")
    await page.goto(search_url, wait_until="domcontentloaded")
    await asyncio.sleep(2)

    # Handle consent button if present
    try:
        btn = await page.query_selector('button:has-text("Accept all"), button:has-text("I agree"), button:has-text("Stay signed out")')
        if btn:
            await btn.click()
            await asyncio.sleep(1)
    except Exception:
        pass

    # Scroll down to load images
    for _ in range(4):
        await page.mouse.wheel(0, 1000)
        await asyncio.sleep(1)

    image_urls = await page.evaluate('''() => {
        const results = [];
        const seen = new Set();
        const imgs = document.querySelectorAll('div#rso img, div[data-ved] img, img.YQ4gaf, div.H80Q8c img');
        for (const img of imgs) {
            const src = img.src || img.getAttribute('data-src') || img.currentSrc;
            if (!src) continue;
            if (src.includes('google.com/logos') || src.includes('favicon.ico') || src.includes('cleardot.gif')) continue;
            if (!seen.has(src)) {
                seen.add(src);
                results.push(src);
            }
        }
        return results;
    }''')

    print(f"📷 Found {len(image_urls)} flyer images on Google Images")

    import aiohttp
    import aiofiles

    saved_paths = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    async with aiohttp.ClientSession(headers=headers) as session:
        count = 1
        for url in image_urls:
            ext = "png" if ".png" in url.lower() else "webp" if ".webp" in url.lower() else "jpg"
            clean_q = query.replace(" ", "_").replace("-", "_")
            file_name = f"{clean_q}_{datetime.now().strftime('%Y%m%d')}_{count:02d}.{ext}"
            file_path = os.path.join(save_dir, file_name)

            try:
                if url.startswith("data:image/"):
                    import base64
                    header, data = url.split(",", 1)
                    img_data = base64.b64decode(data)
                    if len(img_data) > 1200:
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(img_data)
                        saved_paths.append(file_path)
                        count += 1
                else:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            if len(content) > 2000:
                                async with aiofiles.open(file_path, "wb") as f:
                                    await f.write(content)
                                saved_paths.append(file_path)
                                count += 1
            except Exception:
                pass

            if count > max_images:
                break

    print(f"📥 Successfully downloaded {len(saved_paths)} images")
    return saved_paths


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Google Images Walk-in Extraction Workflow")
    parser.add_argument("--query", type=str, default="chennai walk in interview", help="Search query")
    parser.add_argument("--last24h", action="store_true", default=True, help="Filter last 24 hours")
    parser.add_argument("--max-images", type=int, default=6, help="Max images to download")
    args = parser.parse_args()

    save_folder = "downloaded_walkin_images"
    os.makedirs(save_folder, exist_ok=True)

    print("=" * 75)
    print("🚀 ALL_CAREER — GOOGLE IMAGES WALK-IN EXTRACTION & MCA VALIDATION")
    print(f"📅 Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔍 Target Query: '{args.query}' (Last 24h Filter: {args.last24h})")
    print(f"📂 Image Cache: {os.path.abspath(save_folder)}")
    print("=" * 75)

    # 1. Download fresh images via Playwright
    all_downloaded = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        downloaded = await scrape_google_images_for_query(page, args.query, save_folder, max_images=args.max_images)
        all_downloaded.extend(downloaded)

        await browser.close()

    # 2. Run Image-to-Job Pipeline with MCA Master Data & OCR
    print("\n" + "=" * 75)
    print("🧠 RUNNING OCR, ROLE, LOCATION, & MCA COMPANY RESOLVER PIPELINE")
    print("=" * 75)

    pipeline = ImageToJobPipeline(enable_ai_verification=True)
    extracted_jobs = []

    for idx, img_path in enumerate(all_downloaded, 1):
        print(f"\n{'='*30} [Image {idx}/{len(all_downloaded)}] {'='*30}")
        print(f"📷 File: {os.path.basename(img_path)}")
        res = pipeline.process_image(img_path)
        
        # Display extracted OCR preview
        ocr_snippet = res.raw_ocr_text.strip().replace("\n", " ") if res.raw_ocr_text else "No text detected"
        if len(ocr_snippet) > 160:
            ocr_snippet = ocr_snippet[:160] + "..."
        print(f"  📝 OCR Text: \"{ocr_snippet}\"")

        if res.is_job:
            co = res.company.name or "Unknown / Unnamed Company"
            co_method = res.company.detection_method or "N/A"
            co_conf = res.company.confidence
            roles_str = ", ".join([r.name for r in res.roles[:3]]) if res.roles else "General Vacancy"
            loc_str = f"{res.location.city or ''}{', ' + res.location.state if res.location.state else ''}".strip(", ") or "India"
            dt_str = f"{res.date} ({res.time.start or ''} - {res.time.end or ''})" if res.date else "Upcoming"

            print(f"  🎉 VALID JOB POSTER (Signal Score: {res.signal_score}, Conf: {res.confidence:.2f})")
            print(f"     🏢 Company (MCA Verified): {co}")
            print(f"        └─ Resolution Source:   {co_method} (Conf: {co_conf:.2f})")
            print(f"     💼 Role/Designation:       {roles_str}")
            print(f"     📍 Location / City:        {loc_str}")
            print(f"     📅 Walk-in Date & Time:    {dt_str}")
            if res.qr.found:
                print(f"     📱 QR Code Decoded:        [{res.qr.payload_type}] {res.qr.raw_data}")
            if res.contact_phone:
                print(f"     📞 Phone Number:           {res.contact_phone}")
            if res.contact_email:
                print(f"     ✉️ Email Address:          {res.contact_email}")

            extracted_jobs.append(res.to_dict())
        else:
            print(f"  ⏩ Non-job image / noise filtered out (Signal Score: {res.signal_score})")

    # 3. Save Structured Extraction Output
    output_file = "scraped_image_walkin_jobs.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(extracted_jobs, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 75)
    print("📊 EXTRACTION SUMMARY")
    print(f"   🖼️ Images Analyzed: {len(all_downloaded)}")
    print(f"   ✅ Valid Jobs Extracted: {len(extracted_jobs)}")
    print(f"   💾 Saved to: {os.path.abspath(output_file)}")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())
