"""
High-Precision Company Name Normalizer.
Provides deterministic, reversible, and search-optimized company name normalization.
"""
import re
from typing import Tuple, List, Set


# Common legal entity suffixes in Indian & Global corporate registrations
# Ordered from longest/most-specific to shortest
LEGAL_SUFFIX_PATTERNS = [
    r'\bindia\s+private\s+limited\s+company\b',
    r'\bindia\s+private\s+limited\b',
    r'\bindia\s+pvt\s*\.?\s*ltd\s*\.?\b',
    r'\bindia\s+limited\b',
    r'\bindia\s+ltd\s*\.?\b',
    r'\bprivate\s+limited\s+company\b',
    r'\bprivate\s+limited\b',
    r'\bpvt\s*\.?\s*ltd\s*\.?\b',
    r'\bpvt\s+limited\b',
    r'\bpublic\s+limited\s+company\b',
    r'\bpublic\s+limited\b',
    r'\blimited\s+liability\s+partnership\b',
    r'\bllp\b',
    r'\bco\s*\.?\s*ltd\s*\.?\b',
    r'\bcompany\s+limited\b',
    r'\bltd\s*\.?\b',
    r'\blimited\b',
    r'\bincorporated\b',
    r'\binc\s*\.?\b',
    r'\b\(india\)\b',
]

# Combined compiled regex for stripping legal suffixes from normalized search strings
LEGAL_SUFFIX_REGEX = re.compile(
    r'(?:' + '|'.join(LEGAL_SUFFIX_PATTERNS) + r')$',
    re.IGNORECASE
)

# Common generic words on job posters that must not be accepted as company names
GENERIC_POSTER_WORDS: Set[str] = {
    "walk in", "walkin", "walk in drive", "walkin drive", "walk-in drive",
    "interview", "interviews", "hiring", "we are hiring", "we're hiring",
    "urgent hiring", "immediate opening", "immediate openings", "now hiring",
    "job opening", "job openings", "career opportunity", "selection drive",
    "recruitment drive", "chennai", "bangalore", "bengaluru", "hyderabad",
    "pune", "mumbai", "delhi", "noida", "gurgaon", "experience", "salary",
    "qualification", "skills", "venue", "contact", "apply now", "register now",
    "send resume", "share cv", "fresher", "experienced", "notice period",
    "candidates", "requirement", "requirements", "eligibility", "criteria",
    "role", "roles", "position", "positions", "job title", "location", "freshers",
    "great careers", "assessment", "office openings", "careers", "walk in interview",
    "date", "time", "venue address", "contact us", "mail your cv", "spot offer",
    "software engineer", "software developer", "developer", "engineer", "executive"
}


class CompanyNormalizer:
    @staticmethod
    def clean_whitespace(text: str) -> str:
        """Trim and collapse multiple whitespace characters."""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', str(text)).strip()

    @classmethod
    def normalize_name(cls, company_name: str, strip_legal_suffix: bool = True) -> str:
        """
        Produce a normalized string for exact & FTS5 indexing.
        Examples:
          "Tata Consultancy Services Limited" -> "tata consultancy services"
          "TATA CONSULTANCY SERVICES LTD."    -> "tata consultancy services"
          "Accenture Solutions Private Limited"-> "accenture solutions"
          "  ZOHO CORPORATION PVT. LTD. "     -> "zoho corporation"
        """
        if not company_name:
            return ""

        # 1. Lowercase
        s = str(company_name).lower().strip()

        # 2. Normalize common character variants & punctuation
        s = s.replace("&", " and ")
        s = re.sub(r'[\(\)\[\]\{\}\'\"`’]', ' ', s)
        s = re.sub(r'[\.,;:\-_/\\#@!+*]', ' ', s)

        # 3. Collapse whitespace
        s = cls.clean_whitespace(s)

        # 4. Optionally strip legal entity suffixes (Pvt Ltd, Limited, LLP, Inc, etc.)
        if strip_legal_suffix:
            # Repeatedly strip suffixes from the end if multiple present
            prev = None
            while prev != s:
                prev = s
                s = LEGAL_SUFFIX_REGEX.sub('', s)
                s = cls.clean_whitespace(s)

        return s

    @classmethod
    def get_search_tokens(cls, normalized_name: str) -> List[str]:
        """Split normalized name into alphanumeric tokens for FTS5 queries."""
        tokens = [t for t in re.split(r'\W+', normalized_name) if len(t) >= 2]
        return tokens

    @classmethod
    def is_generic_word(cls, text: str) -> bool:
        """Check if a candidate phrase is a generic job poster keyword."""
        low = cls.normalize_name(text, strip_legal_suffix=True)
        if not low or len(low) < 3:
            return True
        if low in GENERIC_POSTER_WORDS:
            return True
        # Check if phrase consists solely of generic terms
        generic_roots = [
            "experience", "required", "requirement", "qualification", "salary",
            "candidate", "eligibility", "criteria", "walk in", "walkin",
            "interview", "urgent hiring", "immediate opening", "software engineer",
            "full stack developer", "apply now", "send resume", "share cv"
        ]
        if any(r == low or low.startswith(r) or low.endswith(r) for r in generic_roots):
            return True
        # If purely numeric or symbols
        if not re.search(r'[a-z]', low):
            return True
        return False
