"""
Master Production Image-to-Job Pipeline for ALL_CAREER.
Orchestrates:
1. Ingestion & Validation
2. Perceptual Hashing & Deduplication
3. Dual-pass QR Code Scanning
4. Multi-pass OCR with Bounding Box Preservation
5. Deterministic Detectors (Role Taxonomy, Indian Location, Company Multi-signal, Date/Time Regex)
6. High-Recall Stage 1 Job Signal Scoring
7. Multimodal AI Verification & Fallback
8. Strict Structured JSON Output with Confidence Scoring
"""
import os
import re
import time
from typing import Optional, List, Dict, Any, Tuple
from .config import MIN_JOB_SIGNAL_SCORE, DUPLICATE_HASH_THRESHOLD
from .schema.job_schema import (
    JobExtractionResult, CompanyResult, RoleResult, LocationResult,
    TimeWindow, QRCodeResult, OCRBoundingBox
)
from .ingestion.validator import ImageValidator
from .ingestion.hasher import ImageHasher, DuplicateTracker
from .preprocessing.preprocessor import ImagePreprocessor
from .ocr.ocr_engine import OCREngine
from .ocr.merger import OCRMerger
from .qr.qr_scanner import QRScanner
from .detectors.signal_detector import JobSignalDetector
from .detectors.role_detector import RoleDetector
from .detectors.location_detector import LocationDetector
from .detectors.company_detector import CompanyDetector
from .detectors.date_time_detector import DateTimeDetector
from .ai.ai_verifier import AIVerifier


class ImageToJobPipeline:
    def __init__(
        self,
        min_signal_score: int = MIN_JOB_SIGNAL_SCORE,
        enable_ai_verification: bool = True
    ):
        self.min_signal_score = min_signal_score
        self.enable_ai_verification = enable_ai_verification
        self.ocr_engine = OCREngine()
        self.dup_tracker = DuplicateTracker(threshold=DUPLICATE_HASH_THRESHOLD)

    def extract_contacts_from_text(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract phone (+91), HR email, and apply URLs from OCR text."""
        phone = None
        email = None
        apply_url = None

        # 1. Phone number (Indian mobile pattern: 10 digits starting with 6,7,8,9 or with +91)
        phone_match = re.search(r'(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}', text)
        if phone_match:
            phone = phone_match.group(0).replace(" ", "").replace("-", "")

        # 2. Email (hr@..., careers@..., jobs@...) with OCR artifact handling
        email_match = re.search(r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z]{2,7}|lcom|com|in|org|net))\b', text, re.IGNORECASE)
        if email_match:
            raw_em = email_match.group(1).lower()
            # Normalize common OCR artifacts like "lamprelLcom" -> "lamprell.com"
            raw_em = re.sub(r'([a-z0-9])lcom$', r'\1.com', raw_em)
            if not re.search(r'\.[a-z]{2,7}$', raw_em):
                raw_em = re.sub(r'(com|in|org|net)$', r'.\1', raw_em)
            email = raw_em

        # 3. Apply URL
        url_match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text)
        if url_match:
            raw_u = url_match.group(0)
            apply_url = raw_u if raw_u.startswith("http") else f"https://{raw_u}"

        return phone, email, apply_url

    def process_image(
        self,
        image_path: str,
        source_url: Optional[str] = None
    ) -> JobExtractionResult:
        """
        Execute full end-to-end extraction on a single image.
        """
        start_t = time.time()

        # 1. Image Validation
        is_valid, err_msg, dims = ImageValidator.validate(image_path)
        if not is_valid:
            return JobExtractionResult(
                is_job=False,
                image_path=image_path,
                source_url=source_url,
                confidence=0.0,
                signal_details=[f"Validation Error: {err_msg}"]
            )

        # 2. Perceptual Hashing & Duplicate Detection
        phash, dhash, md5_str = ImageHasher.compute_hashes(image_path)
        is_dup = self.dup_tracker.check_and_add(phash, md5_str)

        # 3. QR Code Scanning
        qr_result = QRScanner.scan_image(image_path)

        # 4. Multi-pass OCR with Bounding Box Preservation
        ocr_boxes: List[OCRBoundingBox] = self.ocr_engine.run_multipass(image_path)
        raw_ocr_text = OCRMerger.get_full_text(ocr_boxes)

        # 5. Deterministic Detectors
        roles: List[RoleResult] = RoleDetector.detect_roles(raw_ocr_text)
        location: LocationResult = LocationDetector.detect_location(raw_ocr_text, ocr_boxes)
        company: CompanyResult = CompanyDetector.detect_company(raw_ocr_text, ocr_boxes)
        date_time_info = DateTimeDetector.detect_date_time(raw_ocr_text)
        phone, email, apply_url = self.extract_contacts_from_text(raw_ocr_text)

        # If QR code has URL or contact info, prioritize/merge it
        if qr_result.found:
            if qr_result.url and not apply_url:
                apply_url = qr_result.url
            if qr_result.phone and not phone:
                phone = qr_result.phone
            if qr_result.email and not email:
                email = qr_result.email

        # 6. High-Recall Stage 1 Job Signal Scoring
        has_role = len(roles) > 0
        has_location = bool(location.city or location.venue)
        has_company = bool(company.name)
        has_datetime = bool(date_time_info["date"] or date_time_info["time"].start)

        is_candidate_job, signal_score, signal_details = JobSignalDetector.evaluate(
            text=raw_ocr_text,
            has_role=has_role,
            has_location=has_location,
            has_company=has_company,
            has_datetime=has_datetime,
            min_threshold=self.min_signal_score
        )

        # Build initial extraction result
        job_type = "walk_in_interview" if any("walk_in" in s for s in signal_details) else "direct_hiring"
        title = roles[0].name if roles else "Job Opportunity"

        result = JobExtractionResult(
            is_job=is_candidate_job,
            job_type=job_type,
            title=title,
            company=company,
            roles=roles,
            location=location,
            date=date_time_info["date"],
            end_date=date_time_info["end_date"],
            time=date_time_info["time"],
            contact_phone=phone,
            contact_email=email,
            apply_url=apply_url,
            qr=qr_result,
            confidence=0.85 if is_candidate_job else 0.20,
            signal_score=signal_score,
            signal_details=signal_details,
            image_path=image_path,
            image_hash=phash,
            source_url=source_url,
            raw_ocr_text=raw_ocr_text
        )

        # 7. AI Verification (Invoked only for candidate job images to verify unknown companies/roles)
        if is_candidate_job and self.enable_ai_verification:
            # If company is unverified or AI is requested
            result = AIVerifier.verify_job_poster(
                image_path=image_path,
                ocr_text=raw_ocr_text,
                deterministic_result=result
            )

        return result

    def process_folder(self, folder_path: str) -> List[JobExtractionResult]:
        """Process all images in a local directory."""
        results = []
        if not os.path.exists(folder_path):
            return results

        valid_exts = (".jpg", ".jpeg", ".png", ".webp")
        files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(valid_exts)
        ]

        print(f"\n📂 Processing {len(files)} images from: {folder_path}")
        for idx, file_path in enumerate(files, 1):
            print(f"[{idx}/{len(files)}] 🔍 Analyzing {os.path.basename(file_path)}...", end=" ", flush=True)
            res = self.process_image(file_path)
            if res.is_job:
                co_name = res.company.name or "Unknown Company"
                city_name = res.location.city or "India"
                roles_str = ", ".join([r.name for r in res.roles[:2]]) if res.roles else "Hiring"
                print(f"✅ JOB FOUND: {co_name} | {roles_str} | {city_name} (Score: {res.signal_score})")
            else:
                print(f"⏩ Skipped (Not a job poster, Score: {res.signal_score})")
            results.append(res)

        return results
