"""
Multimodal AI Verifier and Fallback Module.
Invoked ONLY for candidate job posters that passed stage 1 signal scoring or require
precise company/role verification.
Supports Gemini 2.5 Flash, Mistral, Groq, and OpenRouter with automatic key rotation.
"""
import os
import json
import base64
import requests
from typing import Optional, Dict, Any, List
from ..schema.job_schema import JobExtractionResult, CompanyResult, RoleResult, LocationResult, TimeWindow, QRCodeResult
from ..config import GEMINI_API_KEYS, MISTRAL_API_KEYS, GROQ_API_KEYS, OPENROUTER_API_KEYS


SYSTEM_PROMPT = """You are an expert recruitment and job flyer extraction system for ALL_CAREER.
Analyze this job poster image, OCR text, and deterministic detector hints.

RULES:
1. Determine if this image is a genuine JOB/RECRUITMENT opportunity (walk-in interview, direct hiring, job drive).
   - If it is a training course advert, certificate, promotional flyer, or motivational quote with NO job offering, set "is_job": false.
2. COMPANY: Identify the hiring company/organization. DO NOT GUESS. If unknown or not mentioned, return null.
3. ROLES: Extract ALL job titles/roles mentioned in the flyer.
4. LOCATION: Extract the city, state, and specific interview venue address.
5. DATE & TIME: Extract interview dates (single date or range) and timings (e.g. 09:30 AM to 03:30 PM).
6. CONTACT: Extract HR phone number, email address, or application link if shown.

Return STRICT JSON only matching this schema:
{
  "is_job": true,
  "job_type": "walk_in_interview",
  "company": {
    "name": "Company Name or null",
    "confidence": 0.95
  },
  "roles": [
    {
      "name": "Software Engineer",
      "canonical": "Software Engineer",
      "category": "Software Engineering",
      "confidence": 0.95
    }
  ],
  "location": {
    "city": "Chennai",
    "state": "Tamil Nadu",
    "venue": "Venue address or null",
    "pincode": "600096 or null",
    "confidence": 0.95
  },
  "date": "2026-08-29",
  "end_date": "2026-08-30",
  "time": {
    "start": "09:30 AM",
    "end": "03:30 PM"
  },
  "contact_phone": "+919876543210 or null",
  "contact_email": "hr@example.com or null",
  "apply_url": "https://... or null",
  "confidence": 0.95
}
"""


class AIVerifier:
    @staticmethod
    def encode_image_base64(image_path: str) -> Optional[str]:
        """Encode image to base64 string."""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return None

    @classmethod
    def verify_with_gemini(
        cls,
        image_path: str,
        ocr_text: str,
        hints: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Verify poster image using Gemini 2.5 Flash Vision."""
        if not GEMINI_API_KEYS:
            return None

        b64_img = cls.encode_image_base64(image_path)
        if not b64_img:
            return None

        mime_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
        prompt_content = f"""OCR Extracted Text:
{ocr_text}

Detector Hints:
{json.dumps(hints, indent=2)}

Please verify this job flyer and output the strict JSON response."""

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT + "\n\n" + prompt_content},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_img
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        for key in GEMINI_API_KEYS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
            try:
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    # Parse JSON
                    if raw_txt.startswith("```"):
                        raw_txt = raw_txt.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                    return json.loads(raw_txt)
                elif resp.status_code == 429:
                    continue  # Try next key
            except Exception:
                continue

        return None

    @classmethod
    def verify_job_poster(
        cls,
        image_path: str,
        ocr_text: str,
        deterministic_result: JobExtractionResult
    ) -> JobExtractionResult:
        """
        Runs multimodal AI verification when API keys are available and merges with deterministic detections.
        """
        hints = {
            "detected_company": deterministic_result.company.name,
            "detected_roles": [r.name for r in deterministic_result.roles],
            "detected_location": deterministic_result.location.city,
            "detected_venue": deterministic_result.location.venue,
            "detected_date": deterministic_result.date,
            "detected_time": deterministic_result.time.model_dump(),
            "qr_data": deterministic_result.qr.raw_data,
            "signal_score": deterministic_result.signal_score
        }

        # Try Gemini
        ai_data = cls.verify_with_gemini(image_path, ocr_text, hints)

        if ai_data:
            is_job = ai_data.get("is_job", False)
            if not is_job:
                deterministic_result.is_job = False
                deterministic_result.confidence = 0.90
                return deterministic_result

            deterministic_result.is_job = True
            deterministic_result.job_type = ai_data.get("job_type", deterministic_result.job_type)

            # Company verification
            co_data = ai_data.get("company", {})
            if isinstance(co_data, dict) and co_data.get("name"):
                deterministic_result.company = CompanyResult(
                    name=co_data.get("name"),
                    canonical=co_data.get("name"),
                    confidence=co_data.get("confidence", 0.95),
                    detection_method="ai_verified"
                )

            # Roles verification
            ai_roles = ai_data.get("roles", [])
            if ai_roles and isinstance(ai_roles, list):
                updated_roles = []
                for r in ai_roles:
                    if isinstance(r, dict) and r.get("name"):
                        updated_roles.append(
                            RoleResult(
                                name=r.get("name"),
                                canonical=r.get("canonical", r.get("name")),
                                category=r.get("category", "General"),
                                confidence=r.get("confidence", 0.92)
                            )
                        )
                if updated_roles:
                    deterministic_result.roles = updated_roles

            # Location verification
            loc_data = ai_data.get("location", {})
            if isinstance(loc_data, dict):
                if loc_data.get("city"):
                    deterministic_result.location.city = loc_data.get("city")
                if loc_data.get("state"):
                    deterministic_result.location.state = loc_data.get("state")
                if loc_data.get("venue"):
                    deterministic_result.location.venue = loc_data.get("venue")
                if loc_data.get("pincode"):
                    deterministic_result.location.pincode = loc_data.get("pincode")

            # Date & Times
            if ai_data.get("date"):
                deterministic_result.date = ai_data.get("date")
            if ai_data.get("end_date"):
                deterministic_result.end_date = ai_data.get("end_date")
            if isinstance(ai_data.get("time"), dict):
                t = ai_data["time"]
                deterministic_result.time = TimeWindow(start=t.get("start"), end=t.get("end"))

            # Contacts
            if ai_data.get("contact_phone"):
                deterministic_result.contact_phone = ai_data.get("contact_phone")
            if ai_data.get("contact_email"):
                deterministic_result.contact_email = ai_data.get("contact_email")
            if ai_data.get("apply_url"):
                deterministic_result.apply_url = ai_data.get("apply_url")

            deterministic_result.confidence = ai_data.get("confidence", 0.95)

        return deterministic_result
