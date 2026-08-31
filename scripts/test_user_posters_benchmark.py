"""
Benchmarking OCR & Extraction Accuracy on User's 7 Test Posters.
"""
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from image_pipeline.pipeline import ImageToJobPipeline
from company_db.resolver import CompanyResolver

image_paths = [
    r"C:\Users\lrage\Downloads\photo_6080326587988514257_y.jpg",
    r"C:\Users\lrage\Downloads\photo_6084772128247977683_y.jpg",
    r"C:\Users\lrage\Downloads\photo_6073427775294476239_y.jpg",
    r"C:\Users\lrage\Downloads\photo_6086743178934424295_y.jpg",
    r"C:\Users\lrage\Downloads\photo_6082578387802199224_y.jpg",
    r"C:\Users\lrage\Downloads\photo_6082578387802199225_y.jpg",
    r"C:\Users\lrage\Downloads\photo_6086743178934424134_y.jpg"
]

print("=" * 85)
print("🚀 ALL_CAREER — FULL 7-POSTER OCR & MCA MASTER EXTRACTION BENCHMARK")
print("=" * 85)

pipeline = ImageToJobPipeline(enable_ai_verification=True)
resolver = CompanyResolver()

results = []

for idx, img_p in enumerate(image_paths, 1):
    path_obj = Path(img_p)
    print(f"\n{'='*30} [Image #{idx}: {path_obj.name}] {'='*30}")
    
    res = pipeline.process_image(str(path_obj))
    ocr_raw = (res.raw_ocr_text or "").strip()

    # Step 1: Company Lookup in MCA DB
    comp_name = res.company.name
    comp_method = res.company.detection_method
    comp_conf = res.company.confidence
    
    cin_num = None
    status = None
    state = None
    
    if comp_name:
        with resolver.db.get_connection() as conn:
            row = conn.execute(
                "SELECT cin, company_status, registered_state FROM companies WHERE company_name = ? OR normalized_name = ? LIMIT 1",
                (comp_name.upper().strip(), comp_name.lower().strip())
            ).fetchone()
            if row:
                cin_num = row["cin"]
                status = row["company_status"]
                state = row["registered_state"]

    roles_str = ", ".join([r.name for r in res.roles]) if res.roles else "General Vacancy"
    loc_str = f"{res.location.city or ''}{', ' + res.location.state if res.location.state else ''}".strip(", ") or "Not Specified"
    dt_str = f"{res.date} ({res.time.start or ''} - {res.time.end or ''})".strip() if res.date else "Upcoming"

    print("📝 RAW OCR TEXT EXTRACTED:")
    for line in ocr_raw.splitlines()[:10]:
        if line.strip():
            print(f"   │ {line.strip()}")
    if len(ocr_raw.splitlines()) > 10:
        print("   │ ... [truncated]")

    print("\n📊 EXTRACTED & MCA VERIFIED FIELDS:")
    print(f"   🏢 Company:       {comp_name or 'Unknown'} (Method: {comp_method}, Conf: {comp_conf:.2f})")
    if cin_num:
        print(f"      └─ MCA CIN:    {cin_num} | State: {state.title() if state else ''} | Status: {status}")
    print(f"   💼 Role / Title:  {roles_str}")
    print(f"   📍 Location:      {loc_str}")
    if res.location.venue:
        print(f"      └─ Venue:      {res.location.venue}")
    print(f"   📅 Walk-in Date:  {dt_str}")
    if res.contact_email:
        print(f"   ✉️ Email:         {res.contact_email}")
    if res.contact_phone:
        print(f"   📞 Phone:         {res.contact_phone}")
    if res.qr.found:
        print(f"   📱 QR Decoded:    [{res.qr.payload_type}] {res.qr.raw_data}")
    if res.apply_url:
        print(f"   🔗 Website / URL: {res.apply_url}")

    results.append({
        "file": path_obj.name,
        "company": comp_name,
        "cin": cin_num,
        "role": roles_str,
        "location": loc_str,
        "date": dt_str,
        "email": res.contact_email,
        "phone": res.contact_phone,
        "qr": res.qr.raw_data if res.qr.found else None,
        "valid": res.is_job
    })

print("\n" + "=" * 85)
print("🏆 SUMMARY TABLE:")
print(f"{'#':<3} | {'Image File':<32} | {'MCA Company':<28} | {'Role':<20} | {'City':<12}")
print("-" * 105)
for idx, r in enumerate(results, 1):
    co = (r['company'] or 'Unknown')[:26]
    ro = (r['role'] or 'General')[:18]
    ci = (r['location'] or 'N/A')[:10]
    print(f"{idx:<3} | {r['file']:<32} | {co:<28} | {ro:<20} | {ci:<12}")
print("=" * 105)
