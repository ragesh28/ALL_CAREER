"""
Interactive CLI Image-to-Job Tester for ALL_CAREER.
Extracts Role, MCA-verified Company, Location, Walk-in Dates, Salary, Contacts,
and Signal Scores from image URLs or local files.

Usage:
    # 1. Direct Image URL:
    python scripts/interactive_image_tester.py "https://example.com/poster.jpg"

    # 2. Local File or Directory:
    python scripts/interactive_image_tester.py "C:/path/to/poster.jpg"

    # 3. Interactive Prompt:
    python scripts/interactive_image_tester.py
"""
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Disable insecure request warnings when downloading flyers
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests

# Set up utf-8 encoding for Windows console
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from image_pipeline.pipeline import ImageToJobPipeline
from company_db.resolver import CompanyResolver
from company_db.config import DEFAULT_DB_PATH


def print_banner():
    print("\n" + "=" * 80)
    print("🎯 ALL_CAREER — INTERACTIVE WALK-IN IMAGE EXTRACTION & OCR TESTER")
    print("=" * 80)
    print("📌 You can paste or type:")
    print("   • An Image URL (e.g. https://example.com/hiring_poster.jpg)")
    print("   • A local image file (e.g. C:/Users/Downloads/flyer.png)")
    print("   • A folder containing images (e.g. ./downloaded_walkins/)")
    print("   • Type 'q' or 'exit' to quit.\n")


def download_image_from_url(url: str, dest_path: Path) -> bool:
    """Download image buffer from URL with realistic browser headers."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    print(f"📥 Downloading image from URL: {url[:90]}...")
    try:
        resp = requests.get(url, headers=headers, timeout=15, verify=False)
        if resp.status_code == 200 and len(resp.content) >= 1000:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            print(f"   ✅ Successfully downloaded ({len(resp.content) / 1024:.1f} KB)")
            return True
        else:
            print(f"   ❌ Download failed: HTTP {resp.status_code} ({len(resp.content)} bytes)")
            return False
    except Exception as e:
        print(f"   ❌ Network error downloading image: {e}")
        return False


def process_single_image(
    pipeline: ImageToJobPipeline,
    resolver: Optional[CompanyResolver],
    img_path: Path,
    source_label: Optional[str] = None
):
    if not img_path.exists():
        print(f"\n❌ Error: File not found at '{img_path}'")
        return

    label = source_label or img_path.name
    print(f"\n🔍 Processing Flyer: {label}")
    print("-" * 80)

    res = pipeline.process_image(str(img_path))
    ocr_raw = (res.raw_ocr_text or "").strip()

    # Display Raw OCR Lines
    print("📝 RAW OCR TEXT DETECTED:")
    if ocr_raw:
        lines = [line.strip() for line in ocr_raw.splitlines() if line.strip()]
        for line in lines[:15]:
            print(f"   │ {line}")
        if len(lines) > 15:
            print(f"   │ ... [{len(lines) - 15} more lines detected]")
    else:
        print("   (No text detected on image)")

    print("\n" + "-" * 80)
    print("📊 STRUCTURED EXTRACTION RESULTS:")
    print("-" * 80)

    # 1. Job Type & Category
    is_walkin = (res.job_type == "walk_in_interview")
    job_type_str = "WALK-IN INTERVIEW" if is_walkin else "DIRECT HIRING / JOB VACANCY"
    print(f"📋 JOB TYPE:                     \033[94m{job_type_str}\033[0m")

    # 2. Roles & Designations (From 32 Canonicals / 581 Aliases)
    if res.roles:
        print(f"💼 ROLES / DESIGNATIONS ({len(res.roles)} Detected):")
        for idx, r in enumerate(res.roles, 1):
            print(f"   ├─ [{idx}] \033[96m{r.name}\033[0m (Canonical: {r.canonical})")
            print(f"   │     Sector: {r.sector} | Category: {r.category} | Confidence: {r.confidence:.2f}")
    else:
        fallback_role = res.title or "General Recruitment Drive"
        print(f"💼 ROLES / DESIGNATIONS:         \033[90m{fallback_role} (No specific taxonomy match)\033[0m")

    # 3. Company Name & MCA Verification
    comp_name = res.company.name
    comp_method = res.company.detection_method or "N/A"
    comp_conf = res.company.confidence

    if comp_name:
        cin_num = None
        comp_status = "Active"
        reg_state = None
        if resolver:
            try:
                with resolver.db.get_connection() as conn:
                    row = conn.execute(
                        "SELECT cin, company_status, registered_state FROM companies WHERE company_name = ? OR normalized_name = ? LIMIT 1",
                        (comp_name.upper().strip(), comp_name.lower().strip())
                    ).fetchone()
                    if row:
                        cin_num = row["cin"]
                        comp_status = row["company_status"]
                        reg_state = row["registered_state"]
            except Exception:
                pass

        print(f"🏢 COMPANY NAME (MCA Verified):  \033[92m{comp_name}\033[0m")
        print(f"   ├─ Resolution Source:         {comp_method} (Confidence: {comp_conf:.2f})")
        if cin_num:
            print(f"   ├─ MCA CIN Number:            {cin_num}")
            print(f"   ├─ Registration State:        {reg_state.title() if reg_state else 'India'}")
            print(f"   └─ Company Status:            {comp_status}")
        else:
            print(f"   └─ Master Data Match:         Verified corporate entity")
    else:
        print(f"🏢 COMPANY NAME:                 \033[91mUnknown / Not Mentioned\033[0m")

    # 4. Location & Venue
    loc_parts = []
    if res.location.locality:
        loc_parts.append(res.location.locality)
    if res.location.city:
        loc_parts.append(res.location.city)
    if res.location.state:
        loc_parts.append(res.location.state)
    loc_str = ", ".join(loc_parts) if loc_parts else "Not Specified"
    print(f"📍 LOCATION:                     {loc_str}")
    if res.location.venue:
        print(f"   └─ Venue Address:             {res.location.venue}")

    # 5. Walk-in Date & Time
    if res.date:
        t_str = f" ({res.time.start} - {res.time.end})" if res.time.start else ""
        print(f"📅 WALK-IN DATE & TIME:          \033[95m{res.date}{t_str}\033[0m")
    elif is_walkin:
        print(f"📅 WALK-IN DATE & TIME:          \033[93mUpcoming / Date Not Explicitly Detected\033[0m")
    else:
        print(f"📅 WALK-IN DATE & TIME:          \033[90mN/A (Direct Application Vacancy)\033[0m")

    # 6. Experience & Salary
    exp_val = res.experience or "Fresher / Experienced"
    print(f"🎓 EXPERIENCE REQUIRED:          \033[93m{exp_val}\033[0m")

    sal_val = res.salary or "Competitive / Best in Industry"
    print(f"💰 SALARY / CTC:                 \033[92m{sal_val}\033[0m")

    # 7. Contacts & Links
    if res.contact_email:
        print(f"✉️  EMAIL ADDRESS:                {res.contact_email}")
    if res.contact_phone:
        print(f"📞 PHONE NUMBER:                 {res.contact_phone}")
    if res.apply_url:
        print(f"🔗 APPLICATION LINK:             {res.apply_url}")
    if res.qr.found:
        print(f"📱 QR CODE DETECTED:             [{res.qr.payload_type}] {res.qr.raw_data}")

    # 8. Overall Validity & Signal Score
    print("-" * 80)
    if res.is_job:
        print(f"🛡️  VALIDITY STATUS:              \033[92m✅ VALID JOB POSTER\033[0m (Score: {res.signal_score}, Confidence: {res.confidence:.2f})")
        if res.signal_details:
            print(f"   ├─ Detected Signals:          {', '.join(res.signal_details[:5])}")
    else:
        rejections = [s for s in res.signal_details if s.startswith("rejected:")]
        reason_txt = f" ({'; '.join(rejections)})" if rejections else " (Below signal threshold or expired)"
        print(f"🛡️  VALIDITY STATUS:              \033[91m❌ REJECTED / NOISE IMAGE\033[0m (Score: {res.signal_score}){reason_txt}")
    print("=" * 80)


def handle_input(pipeline: ImageToJobPipeline, resolver: Optional[CompanyResolver], raw_input: str):
    raw_input = raw_input.strip("\"'").strip()
    if not raw_input:
        return

    # Check if input is a Web URL
    if raw_input.startswith("http://") or raw_input.startswith("https://"):
        temp_file = ROOT_DIR / "data" / "temp_cli_tester.jpg"
        if download_image_from_url(raw_input, temp_file):
            process_single_image(pipeline, resolver, temp_file, source_label=raw_input)
        return

    # Local Path
    target_path = Path(raw_input)
    if not target_path.exists():
        print(f"❌ Path not found: {target_path}\n")
        return

    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    if target_path.is_dir():
        image_files = [p for p in target_path.iterdir() if p.suffix.lower() in valid_extensions]
        if not image_files:
            print(f"⚠️ No image files found in folder: {target_path}\n")
            return
        print(f"\n📂 Found {len(image_files)} image(s) in folder. Processing...")
        for idx, img_file in enumerate(sorted(image_files), 1):
            print(f"\n[{idx}/{len(image_files)}]")
            process_single_image(pipeline, resolver, img_file)
    else:
        process_single_image(pipeline, resolver, target_path)


def main():
    print_banner()

    print("⚙️ Initializing AI OCR Engine (RapidOCR ONNX Runtime)...")
    pipeline = ImageToJobPipeline(enable_ai_verification=False)
    
    resolver = None
    if DEFAULT_DB_PATH.exists():
        try:
            resolver = CompanyResolver()
            print("✅ MCA Company Master Database Connected\n")
        except Exception:
            print("⚠️ Warning: MCA database connection failed. Running in fallback mode.\n")
    else:
        print("⚠️ Warning: company_master.db not found. Running in fallback mode.\n")

    # If CLI argument passed (e.g. python test_image.py "https://...")
    if len(sys.argv) > 1:
        arg_input = sys.argv[1].strip()
        print(f"👉 Testing provided argument: {arg_input}\n")
        handle_input(pipeline, resolver, arg_input)
        return

    # Interactive loop
    while True:
        try:
            user_input = input("👉 Enter Image URL or Local File Path (or 'q' to quit): ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("q", "quit", "exit"):
                print("\n👋 Exiting Image Tester. Goodbye!\n")
                break

            handle_input(pipeline, resolver, user_input)
            print()

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Exiting.\n")
            break
        except Exception as e:
            print(f"❌ Error during processing: {e}\n")


if __name__ == "__main__":
    main()
