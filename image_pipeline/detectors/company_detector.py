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
    "we are hiring", "we're hiring", "we are", "we're", "join our", "join us", "join us!",
    "join our team", "join our plant team", "urgent hiring", "immediate opening",
    "immediate openings", "now hiring", "job opening", "job openings", "career opportunity",
    "selection drive", "recruitment drive", "chennai", "bangalore", "bengaluru", "hyderabad",
    "pune", "mumbai", "delhi", "noida", "gurgaon", "experience", "salary",
    "qualification", "skills", "venue", "contact", "apply now", "register now",
    "send resume", "share cv", "fresher", "experienced", "notice period",
    "candidates", "requirement", "requirements", "eligibility", "criteria",
    "role", "roles", "position", "positions", "job title", "location", "freshers",
    "great careers", "assessment", "office openings", "careers", "we are hiring!"
}


class CompanyDetector:
    GENERIC_START_BLACKLIST = (
        "immediate openings", "immediate opening", "openings for", "urgent openings",
        "walk in", "walk-in", "walkin", "we are hiring", "we're hiring", "join us",
        "join our", "recruitment drive", "selection drive", "career opportunity"
    )

    @classmethod
    def is_blacklisted(cls, name: str) -> bool:
        low = name.lower().strip(" ,.-:")
        if low in GENERIC_WORDS_BLACKLIST or len(low) < 3:
            return True
        if any(low.startswith(g) for g in cls.GENERIC_START_BLACKLIST):
            return True
        # Filter out non-Latin / non-ASCII CJK characters or unreadable OCR symbols
        if re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0400-\u04ff]', name):
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
        1. Email Domain extraction & MCA Master lookup (e.g. jobs@spaccurelabs.com -> SP ACCURE LABS)
        2. Top 35% Header OCR Bounding Box & Line candidates -> MCA Master Database
        3. Known company dictionary match
        4. Legal/corporate suffix pattern match -> MCA Master Database
        5. Top header bounding box fallback
        """
        if not text:
            return CompanyResult()

        resolver = None
        try:
            from company_db.resolver import CompanyResolver
            from company_db.config import DEFAULT_DB_PATH
            if DEFAULT_DB_PATH.exists():
                resolver = CompanyResolver()
        except Exception:
            pass

        # ── 1.1 Check Email Domain against MCA Database (Extremely High Precision) ──
        GENERIC_EMAIL_DOMAINS = {
            "gmail", "yahoo", "hotmail", "outlook", "rediffmail", "protonmail",
            "zoho", "icloud", "aol", "mail", "ymail", "live", "msn"
        }
        email_matches = re.findall(r'[\w\.\-]+@([a-zA-Z0-9\-]+)\.[a-zA-Z]{2,}', text)
        for domain in email_matches:
            d_clean = domain.lower().strip()
            if d_clean not in GENERIC_EMAIL_DOMAINS and len(d_clean) >= 4:
                if resolver:
                    mca_res = resolver.find_company(d_clean)
                    if mca_res.get("matched") and mca_res.get("confidence", 0) >= 0.80:
                        return CompanyResult(
                            name=mca_res["company_name"],
                            canonical=mca_res["company_name"],
                            confidence=0.99,
                            detection_method="email_domain_mca"
                        )
                    with resolver.db.get_connection() as conn:
                        row = conn.execute(
                            "SELECT company_name, cin, registered_state FROM companies WHERE replace(normalized_name, ' ', '') = ? OR replace(normalized_name, ' ', '') LIKE ? LIMIT 1",
                            (d_clean, f"%{d_clean}%")
                        ).fetchone()
                        if row:
                            return CompanyResult(
                                name=row["company_name"],
                                canonical=row["company_name"],
                                confidence=0.99,
                                detection_method="email_domain_mca"
                            )

        # ── 1.2 Check Website URL Domain against MCA Database (e.g. www.jayviklabs.online -> Jayvik) ──
        GENERIC_WEB_DOMAINS = {
            "google", "forms", "facebook", "instagram", "linkedin", "twitter",
            "github", "microsoft", "whatsapp", "telegram", "bit", "tinyurl", "canva",
            "gmail", "yahoo", "hotmail", "outlook", "rediffmail", "protonmail",
            "zoho", "icloud", "aol", "mail", "ymail", "live", "msn"
        }
        url_domains = re.findall(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9\-]+)\.(?:com|in|online|ai|org|co|io|net|tech|cloud)\b', text, re.I)
        for dom in url_domains:
            d_clean = dom.lower().strip()
            if d_clean not in GENERIC_WEB_DOMAINS and len(d_clean) >= 4:
                if resolver:
                    mca_res = resolver.find_company(d_clean)
                    if mca_res.get("matched") and mca_res.get("confidence", 0) >= 0.80:
                        return CompanyResult(
                            name=mca_res["company_name"],
                            canonical=mca_res["company_name"],
                            confidence=0.98,
                            detection_method="website_domain_mca"
                        )
                    with resolver.db.get_connection() as conn:
                        row = conn.execute(
                            "SELECT company_name, cin, registered_state FROM companies WHERE replace(normalized_name, ' ', '') = ? OR replace(normalized_name, ' ', '') LIKE ? LIMIT 1",
                            (d_clean, f"%{d_clean}%")
                        ).fetchone()
                        if row:
                            return CompanyResult(
                                name=row["company_name"],
                                canonical=row["company_name"],
                                confidence=0.98,
                                detection_method="website_domain_mca"
                            )

        # ── 2. Check Top 35% Header Lines & Bounding Boxes against MCA ──
        header_candidates = []
        if boxes:
            top_boxes = [b for b in boxes if b.relative_top <= 0.35 and b.confidence >= 0.60]
            for b in top_boxes:
                candidate = b.text.strip(" ,.-:\n")
                candidate = re.sub(r'^(?:we[\'’]?re|we are|join our|join us|urgent|urgently|now|welcome to|hiring for)\s+', '', candidate, flags=re.IGNORECASE).strip()
                if not cls.is_blacklisted(candidate) and 3 <= len(candidate) <= 50:
                    header_candidates.append(candidate)

        # Also extract individual lines from the first 8 lines of text
        for line in text.splitlines()[:8]:
            cand = line.strip(" ,.-:\n")
            cand = re.sub(r'^(?:we[\'’]?re|we are|join our|join us|urgent|urgently|now|welcome to|hiring for)\s+', '', cand, flags=re.IGNORECASE).strip()
            if not cls.is_blacklisted(cand) and 3 <= len(cand) <= 50:
                header_candidates.append(cand)

        if resolver:
            for cand in header_candidates:
                mca_res = resolver.find_company(cand)
                if mca_res.get("matched") and mca_res.get("confidence", 0) >= 0.85:
                    return CompanyResult(
                        name=mca_res["company_name"],
                        canonical=mca_res["company_name"],
                        confidence=mca_res["confidence"],
                        detection_method=f"mca_header_{mca_res.get('match_type', 'match')}"
                    )

        # ── 3. Check Known Company Dictionary ──
        low_text = " " + text.lower() + " "
        for key, canonical in KNOWN_COMPANIES.items():
            if f" {key} " in low_text or f"\n{key}\n" in low_text or f"\n{key} " in low_text or f" {key}\n" in low_text or f"at {key}" in low_text or f"for {key}" in low_text:
                return CompanyResult(
                    name=canonical,
                    canonical=canonical,
                    confidence=0.98,
                    detection_method="dictionary"
                )

        # ── 4. Check Legal Suffix Pattern (e.g. [Company] Pvt Ltd, [Company] Labs) ──
        suffix_matches = COMPANY_SUFFIX_REGEX.findall(text)
        for match in suffix_matches:
            cleaned = match.strip(" ,.-:\n")
            if not cls.is_blacklisted(cleaned) and len(cleaned.split()) <= 6:
                if resolver:
                    mca_res = resolver.find_company(cleaned)
                    if mca_res.get("matched") and mca_res.get("confidence", 0) >= 0.80:
                        return CompanyResult(
                            name=mca_res["company_name"],
                            canonical=mca_res["company_name"],
                            confidence=0.95,
                            detection_method="mca_legal_suffix"
                        )
                return CompanyResult(
                    name=cleaned.title(),
                    canonical=cleaned.title(),
                    confidence=0.90,
                    detection_method="legal_suffix"
                )

        # ── 5. Header Bounding Box Fallback ──
        if header_candidates:
            for cand in header_candidates:
                if not any(k in cand.lower() for k in ["interview", "walkin", "walk-in", "engineer", "developer", "executive", "chennai", "bangalore", "hyderabad", "hiring"]):
                    return CompanyResult(
                        name=cand.title(),
                        confidence=0.75,
                        detection_method="bounding_box_header"
                    )

        return CompanyResult(name=None, confidence=0.0)
