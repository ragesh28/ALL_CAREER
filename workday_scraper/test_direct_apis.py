"""Test discovered APIs directly without Playwright."""
import sys
import json
import requests

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# ===== 1. SWIGGY (MyNextHire) =====
print("=" * 60)
print("  1. SWIGGY - MyNextHire API")
print("=" * 60)
try:
    resp = requests.post(
        "https://swiggy.mynexthire.com/employer/careers/reqlist/get",
        headers=HEADERS, json={}, timeout=10
    )
    data = resp.json()
    reqs = data.get("reqDetailsBOList", [])
    print(f"  Status: {resp.status_code} | Total Jobs: {len(reqs)}")
    for j in reqs[:3]:
        title = j.get("reqTitle", "")
        location = j.get("location", "")
        dept = j.get("departmentName", "")
        exp = j.get("experience", "")
        print(f"  Title:      {title}")
        print(f"  Location:   {location}")
        print(f"  Department: {dept}")
        print(f"  Experience: {exp}")
        print()
except Exception as e:
    print(f"  Error: {e}")


# ===== 2. CISCO (Phenom People) =====
print("=" * 60)
print("  2. CISCO - Phenom People API")
print("=" * 60)
try:
    resp = requests.post(
        "https://careers.cisco.com/widgets",
        headers=HEADERS,
        json={
            "lang": "en_global",
            "deviceType": "desktop",
            "country": "global",
            "pageName": "search-results",
            "ddoKey": "refineSearch",
            "sortBy": "",
            "subs498": "",
            "from": 0,
            "jobs": True,
            "counts": True,
            "all_fields": ["category", "country", "state", "city", "type", "workerSubType", "reqId"],
            "size": 3,
            "clear498": False,
            "jdsource": "facets",
            "is498": True,
            "keywords": "india",
        },
        timeout=10
    )
    data = resp.json()
    print(f"  Status: {resp.status_code}")
    # Phenom uses nested structure
    ref = data.get("refineSearch", {})
    if ref:
        hits = ref.get("data", {}).get("jobs", [])
        total = ref.get("totalHits", 0)
        print(f"  Total Jobs: {total}")
        for j in hits[:3]:
            print(f"  Title:    {j.get('title', '')}")
            print(f"  Location: {j.get('city', '')}, {j.get('country', '')}")
            print(f"  Category: {j.get('category', '')}")
            print(f"  Type:     {j.get('type', '')}")
            print(f"  URL:      https://careers.cisco.com{j.get('canonicalPositionUrl', '')}")
            print()
    else:
        print(f"  Keys: {list(data.keys())}")
except Exception as e:
    print(f"  Error: {e}")


# ===== 3. AMAZON (Direct API) =====
print("=" * 60)
print("  3. AMAZON - Direct Search API")
print("=" * 60)
try:
    resp = requests.get(
        "https://www.amazon.jobs/en/search.json?offset=0&result_limit=3&sort=relevant&country=IND",
        headers={**HEADERS, "Accept": "application/json, text/html"},
        timeout=10
    )
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        jobs = data.get("jobs", [])
        total = data.get("hits", 0)
        print(f"  Total Jobs: {total}")
        for j in jobs[:3]:
            print(f"  Title:    {j.get('title', '')}")
            print(f"  Location: {j.get('normalized_location', '') or j.get('location', '')}")
            print(f"  Category: {j.get('job_category', '')}")
            print(f"  Posted:   {j.get('posted_date', '')}")
            print(f"  URL:      https://www.amazon.jobs{j.get('job_path', '')}")
            print()
except Exception as e:
    print(f"  Error: {e}")


# ===== 4. UBER (Direct API) =====
print("=" * 60)
print("  4. UBER - Careers API")
print("=" * 60)
try:
    resp = requests.post(
        "https://www.uber.com/api/loadSearchJobsResults?localeCode=en",
        headers={
            **HEADERS,
            "x-csrf-token": "x",
        },
        json={
            "params": {
                "location": [{"country": "IND", "region": "Karnataka", "city": "Bangalore"}],
                "department": [],
                "team": [],
            },
            "limit": 3,
            "page": 1,
        },
        timeout=10
    )
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        jobs_data = data.get("data", {}).get("results", [])
        total = data.get("data", {}).get("totalResults", 0)
        print(f"  Total: {total}")
        for j in jobs_data[:3]:
            print(f"  Title:    {j.get('title', '')}")
            print(f"  Location: {j.get('location', '')}")
            print(f"  Team:     {j.get('team', '')}")
            print()
    else:
        print(f"  Response: {resp.text[:200]}")
except Exception as e:
    print(f"  Error: {e}")


print("\nDone!")
