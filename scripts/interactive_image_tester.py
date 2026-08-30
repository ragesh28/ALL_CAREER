"""
Interactive CLI Image-to-Job Tester for ALL_CAREER.
Continuously accepts image paths or directories and extracts role, MCA-verified company,
location, walk-in dates, salary, and contact info.

Usage:
    python scripts/interactive_image_tester.py
"""
import os
import sys
from pathlib import Path

# Set up utf-8 encoding for Windows console
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from image_pipeline.pipeline import ImageToJobPipeline
from company_db.resolver import CompanyResolver
from company_db.config import DEFAULT_DB_PATH


def print_banner():
    print("\n" + "=" * 80)
    print("🎯 ALL_CAREER — INTERACTIVE WALK-IN IMAGE EXTRACTION & MCA TESTER")
    print("=" * 80)
    print("📌 You can type or drag-and-drop:")
    print("   • A single image file (e.g., C:/Users/Downloads/flyer.jpg)")
    print("   • A folder containing images (e.g., downloaded_walkin_images)")
    print("   • Type 'q' or 'exit' to quit.\n")


def process_single_image(pipeline: ImageToJobPipeline, resolver: CompanyResolver, img_path: Path):
    if not img_path.exists():
        print(f"\n❌ Error: File not found at '{img_path}'")
        return

    print(f"\n🔍 Processing: {img_path.name}")
    print("-" * 80)

    res = pipeline.process_image(str(img_path))
    ocr_raw = (res.raw_ocr_text or "").strip()

    # Step 1: Direct MCA Deep Lookup on OCR Text
    mca_match = None
    if resolver and ocr_raw:
        mca_match = resolver.find_company(ocr_raw)

    print("📝 RAW OCR TEXT DETECTED:")
    if ocr_raw:
        for line in ocr_raw.splitlines()[:12]:
            if line.strip():
                print(f"   │ {line.strip()}")
        if len(ocr_raw.splitlines()) > 12:
            print("   │ ... [truncated]")
    else:
        print("   (No text detected on image)")

    print("\n" + "-" * 80)
    print("📊 STRUCTURED EXTRACTION RESULTS:")
    print("-" * 80)

    # 1. Company Name & MCA Verification
    comp_name = res.company.name
    comp_method = res.company.detection_method
    comp_conf = res.company.confidence

    if mca_match and mca_match.get("matched"):
        print(f"🏢 COMPANY NAME (MCA Verified):  \033[92m{mca_match['company_name']}\033[0m")
        print(f"   ├─ Resolution Match Type:     {mca_match.get('match_type')} (Score: {mca_match.get('score')}%)")
        print(f"   ├─ Match Confidence:          {mca_match.get('confidence'):.2f}")
        if mca_match.get("cin"):
            print(f"   └─ MCA CIN Number:            {mca_match.get('cin')}")
        else:
            print(f"   └─ Canonical Source:          Official MCA Master Data")
    elif comp_name:
        print(f"🏢 COMPANY NAME:                 \033[93m{comp_name}\033[0m (Method: {comp_method}, Conf: {comp_conf:.2f})")
    else:
        print(f"🏢 COMPANY NAME:                 \033[91mUnknown / Not Mentioned\033[0m")

    # 2. Roles
    roles = [r.name for r in res.roles] if res.roles else []
    if roles:
        print(f"💼 ROLES / DESIGNATIONS:         \033[96m{', '.join(roles)}\033[0m")
    else:
        print(f"💼 ROLES / DESIGNATIONS:         General Recruitment Drive")

    # 3. Location
    loc_parts = []
    if res.location.locality:
        loc_parts.append(res.location.locality)
    if res.location.city:
        loc_parts.append(res.location.city)
    if res.location.state:
        loc_parts.append(res.location.state)
    loc_str = ", ".join(loc_parts) if loc_parts else "Not Specified"
    print(f"📍 LOCATION / VENUE:             {loc_str}")

    # 4. Walk-in Date & Time
    if res.date:
        t_str = f" ({res.time.start} - {res.time.end})" if res.time.start else ""
        print(f"📅 WALK-IN DATE & TIME:          \033[95m{res.date}{t_str}\033[0m")
    else:
        print(f"📅 WALK-IN DATE & TIME:          Upcoming / Check Poster")

    # 5. Venue Address & Apply URL
    if res.location.venue:
        print(f"🏢 VENUE / ADDRESS:              {res.location.venue}")
    if res.apply_url:
        print(f"🔗 APPLICATION LINK / URL:       {res.apply_url}")

    # 6. Contact Info & QR
    if res.contact_email:
        print(f"✉️  EMAIL ADDRESS:                {res.contact_email}")
    if res.contact_phone:
        print(f"📞 PHONE NUMBER:                 {res.contact_phone}")
    if res.qr.found:
        print(f"📱 QR CODE DETECTED:             [{res.qr.payload_type}] {res.qr.raw_data}")

    # 7. Overall Validity
    status_color = "\033[92mVALID JOB POSTER\033[0m" if res.is_job else "\033[91mNON-JOB / NOISE IMAGE\033[0m"
    print(f"\n🛡️  VALIDITY STATUS:              {status_color} (Signal Score: {res.signal_score}, Conf: {res.confidence:.2f})")
    print("=" * 80)


def main():
    print_banner()

    # Initialize pipeline and company resolver
    print("⚙️ Initializing AI OCR Engine & 3.67M MCA Company Database...")
    pipeline = ImageToJobPipeline(enable_ai_verification=True)
    
    resolver = None
    if DEFAULT_DB_PATH.exists():
        resolver = CompanyResolver()
        print("✅ MCA Company Master Database Connected (3,674,322 companies ready)\n")
    else:
        print("⚠️ Warning: company_master.db not found. Running in fallback mode.\n")

    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

    while True:
        try:
            user_input = input("👉 Enter Image Path or Directory (or 'q' to quit): ").strip()
            
            # Remove surrounding quotes if pasted from file explorer
            user_input = user_input.strip("\"'").strip()

            if not user_input:
                continue

            if user_input.lower() in ("q", "quit", "exit"):
                print("\n👋 Exiting Interactive Image Tester. Goodbye!\n")
                break

            target_path = Path(user_input)

            if not target_path.exists():
                print(f"❌ Path not found: {target_path}\n")
                continue

            if target_path.is_dir():
                image_files = [p for p in target_path.iterdir() if p.suffix.lower() in valid_extensions]
                if not image_files:
                    print(f"⚠️ No image files found in folder: {target_path}\n")
                    continue

                print(f"\n📂 Found {len(image_files)} image(s) in folder. Processing one by one...")
                for idx, img_file in enumerate(sorted(image_files), 1):
                    print(f"\n[{idx}/{len(image_files)}]")
                    process_single_image(pipeline, resolver, img_file)
            else:
                process_single_image(pipeline, resolver, target_path)

            print()

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Exiting.\n")
            break
        except Exception as e:
            print(f"❌ Error during processing: {e}\n")


if __name__ == "__main__":
    main()
