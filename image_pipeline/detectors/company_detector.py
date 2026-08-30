"""
Multi-signal Company Detection for Job Flyers.
Does NOT assume unknown words are companies.
Combines:
1. Known company database (TCS, Infosys, Wipro, Lamprell, Cognizant, Accenture, Zoho, etc.)
2. Legal & enterprise company suffix patterns (Pvt Ltd, Technologies, Solutions, LLP, Systems, etc.)
3. OCR bounding-box positioning (Top 30% header of poster has high company prior)
4. Context patterns ("at [Company]", "Hiring for [Company]")
5. Strict guardrail filtering against generic English words
"""
import re
from typing import Optional, List, Dict, Set
from ..schema.job_schema import CompanyResult, OCRBoundingBox


# Top 150+ Known Indian IT, Core, and MNC Employers
KNOWN_COMPANIES = {
    "tcs": "Tata Consultancy Services",
    "tata consultancy services": "Tata Consultancy Services",
    "infosys": "Infosys",
    "wipro": "Wipro",
    "hcl": "HCLTech",
    "hcltech": "HCLTech",
    "hcl technologies": "HCLTech",
    "cognizant": "Cognizant",
    "accenture": "Accenture",
    "capgemini": "Capgemini",
    "tech mahindra": "Tech Mahindra",
    "ltimindtree": "LTIMindtree",
    "mindtree": "LTIMindtree",
    "l&t": "Larsen & Toubro",
    "larsen & toubro": "Larsen & Toubro",
    "mphasis": "Mphasis",
    "hexaware": "Hexaware",
    "persistent": "Persistent Systems",
    "lamprell": "Lamprell",
    "zoho": "Zoho",
    "freshworks": "Freshworks",
    "conduent": "Conduent",
    "genpact": "Genpact",
    "sutherland": "Sutherland",
    "concentrix": "Concentrix",
    "teleperformance": "Teleperformance",
    "quess": "Quess Corp",
    "randstad": "Randstad",
    "adecco": "Adecco",
    "amazon": "Amazon",
    "google": "Google",
    "microsoft": "Microsoft",
    "flipkart": "Flipkart",
    "swiggy": "Swiggy",
    "zomato": "Zomato",
    "paytm": "Paytm",
    "phonepe": "PhonePe",
    "razorpay": "Razorpay",
    "hdfc": "HDFC Bank",
    "icici": "ICICI Bank",
    "axis bank": "Axis Bank",
    "sbi": "State Bank of India",
    "kotak": "Kotak Mahindra Bank",
    "deloitte": "Deloitte",
    "pwc": "PwC",
    "ey": "EY",
    "kpmg": "KPMG",
    "bosch": "Bosch",
    "siemens": "Siemens",
    "honeywell": "Honeywell",
    "reliance": "Reliance Industries",
    "jio": "Reliance Jio",
    "airtel": "Bharti Airtel",
    "modenik": "Modenik Lifestyle",
    "modenik lifestyle": "Modenik Lifestyle",
    "apollo": "Apollo Hospitals",
    "fortis": "Fortis Healthcare"
}

# Legal and corporate suffix regex
COMPANY_SUFFIX_REGEX = re.compile(
    r'\b([A-Z0-9][A-Za-z0-9&\s\.\-]{2,40}\s+(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Ltd\.?|Limited|LLP|Inc\.?|Corp\.?|Corporation|Technologies|Technology|Solutions|Systems|Services|Industries|Enterprises|Consulting|Labs|Digital|Software|Infotech|Healthcare|Hospital|Motors|Lifestyle))\b',
    re.IGNORECASE
)

# Blacklist of generic words that should NEVER be accepted as company names
GENERIC_WORDS_BLACKLIST: Set[str] = {
    "walk in", "walk-in", "walkin", "interview", "interviews", "hiring",
    "we are hiring", "we're hiring", "we are", "we're", "join our", "join us",
    "urgent hiring", "immediate opening", "immediate openings", "now hiring",
    "job opening", "job openings", "career opportunity", "selection drive",
    "recruitment drive", "chennai", "bangalore", "bengaluru", "hyderabad",
    "pune", "mumbai", "delhi", "noida", "gurgaon", "experience", "salary",
    "qualification", "skills", "venue", "contact", "apply now", "register now",
    "send resume", "share cv", "fresher", "experienced", "notice period",
    "candidates", "requirement", "requirements", "eligibility", "criteria",
    "role", "roles", "position", "positions", "job title", "location", "freshers",
    "great careers", "assessment", "office openings", "careers"
}


class CompanyDetector:
    @classmethod
    def is_blacklisted(cls, name: str) -> bool:
        low = name.lower().strip(" ,.-:")
        if low in GENERIC_WORDS_BLACKLIST or len(low) < 3:
            return True
        # If phrase contains only numbers or generic symbols
        if not re.search(r'[a-zA-Z]', low):
            return True
        return False

    @classmethod
    def detect_company(
        cls,
        text: str,
        boxes: Optional[List[OCRBoundingBox]] = None
    ) -> CompanyResult:
        """
        Detect company name using multi-signal hierarchy:
        1. Official MCA Company Database & Brand Aliases (3.67M+ records + FTS5 + RapidFuzz)
        2. Known company dictionary match
        3. Legal/corporate suffix pattern match
        4. Top 30% header bounding box evaluation
        """
        if not text:
            return CompanyResult()

        # ── 1. Check Official MCA Company Database (3.67M+ Records) & Curated Brand Aliases ──
        try:
            from company_db.resolver import CompanyResolver
            from company_db.config import DEFAULT_DB_PATH
            if DEFAULT_DB_PATH.exists():
                resolver = CompanyResolver()
                mca_res = resolver.find_company(text)
                if mca_res.get("matched") and mca_res.get("confidence", 0) >= 0.85:
                    return CompanyResult(
                        name=mca_res["company_name"],
                        canonical=mca_res["company_name"],
                        confidence=mca_res["confidence"],
                        detection_method=f"mca_{mca_res.get('match_type', 'match')}"
                    )
        except Exception:
            pass

        low_text = " " + text.lower() + " "

        # ── 2. Check Known Company Dictionary ──
        for key, canonical in KNOWN_COMPANIES.items():
            if f" {key} " in low_text or f"\n{key}\n" in low_text or f"\n{key} " in low_text or f" {key}\n" in low_text or f"at {key}" in low_text or f"for {key}" in low_text:
                return CompanyResult(
                    name=canonical,
                    canonical=canonical,
                    confidence=0.98,
                    detection_method="dictionary"
                )

        # ── 3. Check Legal Suffix Pattern (High Precision for new/unlisted registered companies) ──
        suffix_matches = COMPANY_SUFFIX_REGEX.findall(text)
        for match in suffix_matches:
            cleaned = match.strip(" ,.-:\n")
            if not cls.is_blacklisted(cleaned) and len(cleaned.split()) <= 6:
                return CompanyResult(
                    name=cleaned.title(),
                    canonical=cleaned.title(),
                    confidence=0.90,
                    detection_method="legal_suffix"
                )

        # ── 4. Check OCR Bounding Box Positioning (Top 30% header region) ──
        if boxes:
            top_boxes = [b for b in boxes if b.relative_top <= 0.30 and b.confidence >= 0.65]
            for b in top_boxes:
                candidate = b.text.strip(" ,.-:\n")
                # Strip leading slogan words
                candidate = re.sub(r'^(?:we[\'’]?re|we are|join our|join us|urgent|urgently|now|welcome to)\s+', '', candidate, flags=re.IGNORECASE).strip()
                # Look for standalone prominent header text
                if not cls.is_blacklisted(candidate) and 3 <= len(candidate) <= 45:
                    # Check if candidate isn't just a role or city
                    if not any(k in candidate.lower() for k in ["interview", "walkin", "walk-in", "engineer", "developer", "executive", "chennai", "bangalore", "hiring"]):
                        return CompanyResult(
                            name=candidate.title(),
                            confidence=0.75,
                            detection_method="bounding_box_header"
                        )

        return CompanyResult(name=None, confidence=0.0)
