"""
CLI Search Tool for Fast Local MCA Company Lookups & OCR Typo Resolution.
Uses Exact -> Brand Aliases -> FTS5 -> RapidFuzz Candidate Ranking.

Usage:
    python -m scripts.search_company "Accenture"
    python -m scripts.search_company "ACCENTURF"
    python -m scripts.search_company --ocr-text "Walk-in interview at TCS Chennai"
"""
import os
import sys
import json
import argparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from company_db.resolver import CompanyResolver
from company_db.database import CompanyDatabase


def main():
    parser = argparse.ArgumentParser(description="Fast Local Company Search using SQLite FTS5 + RapidFuzz")
    parser.add_argument("query", type=str, nargs="?", default=None, help="Company name or typo string to search")
    parser.add_argument("--ocr-text", type=str, default=None, help="Raw OCR multi-line text to extract company from")
    parser.add_argument("--db-path", type=str, default=None, help="Custom SQLite DB path")
    args = parser.parse_args()

    input_text = args.ocr_text if args.ocr_text else args.query
    if not input_text:
        print("❌ Error: Please provide a company name query or --ocr-text.")
        print("Example: python -m scripts.search_company 'ACCENTURF'")
        sys.exit(1)

    db = CompanyDatabase(db_path=args.db_path)
    resolver = CompanyResolver(db=db)

    print("=" * 65)
    print("🏢 ALL_CAREER — LOCAL MCA COMPANY RESOLVER")
    print("=" * 65)
    print(f"🔍 Input Text: \"{input_text.strip()}\"")
    print("=" * 65)

    res = resolver.find_company(input_text)

    # Print Formatted JSON Output
    print(json.dumps(res, indent=2, ensure_ascii=False))

    print("\n" + "=" * 65)
    if res.get("matched"):
        print(f"✅ MATCH FOUND: {res.get('company_name')}")
        print(f"   🆔 CIN:        {res.get('cin')}")
        print(f"   🎯 Confidence: {res.get('confidence')} ({res.get('match_type')})")
    else:
        print(f"⏩ NO DEFINITIVE MATCH (Confidence: {res.get('confidence')})")
        if res.get("candidates"):
            print(f"   Top candidate suggestions: {[c['company_name'] for c in res['candidates'][:3]]}")
    print("=" * 65)


if __name__ == "__main__":
    main()
