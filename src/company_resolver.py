"""
Entry Point Proxy for Company Resolver.
Exposes find_company(ocr_text) function for direct import.
"""
from typing import Dict, Any, Optional
from company_db.resolver import CompanyResolver
from company_db.database import CompanyDatabase

# Singleton instance
_RESOLVER = None


def get_default_resolver() -> CompanyResolver:
    global _RESOLVER
    if _RESOLVER is None:
        _RESOLVER = CompanyResolver()
    return _RESOLVER


def find_company(ocr_text: str, db: Optional[CompanyDatabase] = None) -> Dict[str, Any]:
    """
    Resolve company name from OCR text using exact, brand aliases, FTS5, and RapidFuzz matching.
    Input example:
        "Walk-in Interview
         ACCENTURF
         Chennai"

    Output example:
        {
            "matched": true,
            "company_name": "Accenture Solutions Private Limited",
            "cin": "U72900MH2001PTC132450",
            "confidence": 0.96,
            "match_type": "fuzzy_high",
            "candidate_count": 5
        }
    """
    if db is not None:
        resolver = CompanyResolver(db=db)
    else:
        resolver = get_default_resolver()

    return resolver.find_company(ocr_text)
