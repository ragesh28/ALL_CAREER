import sys
import json
from scrape_all_companies_v2 import detect_and_scrape

sys.stdout.reconfigure(encoding='utf-8')

test_cases = [
    ("Honeywell", "Oracle", "https://ibqbjb.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"),
    ("Qualcomm", "Eightfold", "https://careers.qualcomm.com/api/pcsx/search"),
    ("Ericsson", "Eightfold", "https://jobs.ericsson.com/api/pcsx/search"),
    ("Bank of America", "Custom", "https://careers.bankofamerica.com/services/jobssearchservlet"),
    ("Amadeus", "Workday", "https://amadeus.wd502.myworkdayjobs.com/wday/cxs/amadeus/jobs/jobs")
]

print("Testing the newly added JSON integrations through the main routing engine...\n")

for name, ats, url in test_cases:
    print(f"Testing {name}...")
    try:
        jobs = detect_and_scrape(name, ats, url, limit=2)
        if jobs:
            print(f"  ✅ SUCCESS: Found {len(jobs)} jobs (Total reported: {jobs[0].get('total_jobs', 'Unknown')})")
            for j in jobs:
                print(f"      - {j['title']} | {j['location']}")
        else:
            print(f"  ❌ FAILED: Returned empty list.")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
    print("-" * 50)
