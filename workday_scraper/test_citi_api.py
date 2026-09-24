"""Test Citi's discovered JSON API."""
import sys
import json
import requests

sys.stdout.reconfigure(encoding="utf-8")

url = "https://jobs.citi.com/search-jobs/results"
params = {
    "q": "India",
    "limit": 5,
    "p": 1,
}
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}

resp = requests.get(url, params=params, headers=headers, timeout=10)
print(f"Status: {resp.status_code}")

data = resp.json()
print(f"Top keys: {list(data.keys())}")
print(f"Has jobs: {data.get('hasJobs')}")

results = data.get("results", {})
if isinstance(results, dict):
    print(f"Results keys: {list(results.keys())}")
    total = results.get("totalResults") or results.get("total") or results.get("count")
    print(f"Total results: {total}")
    
    # Try to find the job list
    for key in results:
        val = results[key]
        if isinstance(val, list) and len(val) > 0:
            print(f"\nFound list at key '{key}' with {len(val)} items")
            sample = val[0]
            if isinstance(sample, dict):
                print(f"  Item keys: {list(sample.keys())[:15]}")
                print(f"  Title: {sample.get('title','')}")
                print(f"  Location: {sample.get('location','')}")
            elif isinstance(sample, str):
                print(f"  First item (string): {sample[:200]}")
            break
    
    # Maybe results is the HTML string?
    if isinstance(results, dict) and "SearchResults" in results:
        html = results["SearchResults"]
        print(f"\nSearchResults is HTML ({len(html)} chars)")
        print(f"Preview: {html[:300]}")
elif isinstance(results, str):
    print(f"Results is a string of {len(results)} chars")
    print(f"Preview: {results[:300]}")

# Print full structure at shallow level
print(f"\n--- Full data structure ---")
for k, v in data.items():
    if isinstance(v, str) and len(v) > 200:
        print(f"  {k}: string({len(v)} chars)")
    elif isinstance(v, (dict, list)):
        print(f"  {k}: {type(v).__name__}({len(v)})")
    else:
        print(f"  {k}: {v}")
