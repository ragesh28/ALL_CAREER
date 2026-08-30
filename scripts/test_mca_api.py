"""
CLI Script to Test data.gov.in MCA API Connectivity & Schema.
Usage:
    python -m scripts.test_mca_api
"""
import sys
import os

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from company_db.client import DataGovMCAClient
from company_db.config import get_api_key, DATA_SOURCE_DESCRIPTION, DATA_SOURCE_DATE


def main():
    print("=" * 65)
    print("🏢 MCA COMPANY MASTER DATA API — DIAGNOSTIC TEST")
    print("=" * 65)
    print(f"ℹ️  Data Source: {DATA_SOURCE_DESCRIPTION}")
    print(f"📅 Record Cutoff: {DATA_SOURCE_DATE}")
    print("=" * 65)

    api_key = get_api_key()
    if not api_key:
        print("\n❌ Error: DATA_GOV_API_KEY environment variable is NOT set.")
        print("\nTo set it:")
        print("  Windows PowerShell: $env:DATA_GOV_API_KEY='your_api_key_here'")
        print("  Linux/macOS:        export DATA_GOV_API_KEY='your_api_key_here'")
        print("  GitHub Actions:     Add DATA_GOV_API_KEY to Repository Secrets")
        sys.exit(1)

    print(f"🔑 API Key Status: Configured (length: {len(api_key)} chars, masked: {'*' * (len(api_key) - 4) + api_key[-4:]})")
    print("🌐 Connecting to data.gov.in MCA endpoint (10-record sanity check)...")

    client = DataGovMCAClient(api_key=api_key)
    res = client.test_connection()

    if res.get("success"):
        print("\n✅ API CONNECTION SUCCESSFUL!")
        print(f"📊 HTTP Status:           {res.get('http_status')}")
        print(f"📦 Records Returned:      {res.get('records_returned')}")
        print(f"📚 Total in Government DB: {res.get('total_available_in_catalog'):,}")
        print(f"🏢 Sample Company:        {res.get('sample_company')}")
        print(f"🆔 Sample CIN:            {res.get('sample_cin')}")
        print(f"📋 Field Keys:            {', '.join(res.get('field_keys', []))}")
        print("\n🎉 The API is fully operational and ready for download/updates.")
    else:
        print(f"\n❌ Connection Failed: {res.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
