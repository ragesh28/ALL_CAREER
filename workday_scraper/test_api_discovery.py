"""
Test API discovery for companies without known ATS platforms.
Uses Playwright to intercept network requests and find hidden JSON APIs.
"""
import sys
import json
import requests
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

def discover_apis(url, company_name):
    """Visit a URL with Playwright, intercept all XHR/fetch responses, and find job APIs."""
    print(f"\n{'='*60}")
    print(f"  API Discovery: {company_name}")
    print(f"  URL: {url}")
    print(f"{'='*60}")
    
    discovered_apis = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        def handle_response(response):
            req = response.request
            if req.resource_type in ["fetch", "xhr"]:
                content_type = response.headers.get("content-type", "")
                if "json" in content_type or "javascript" in content_type:
                    try:
                        data = response.json()
                        # Check if the response looks like job data
                        data_str = json.dumps(data).lower()
                        job_keywords = ["job", "position", "title", "location", "career", "posting", "requisition", "opening"]
                        matches = [kw for kw in job_keywords if kw in data_str[:2000]]
                        
                        if len(matches) >= 2:  # At least 2 job-related keywords
                            discovered_apis.append({
                                "url": response.url,
                                "method": req.method,
                                "status": response.status,
                                "keywords_found": matches,
                                "data_sample": data,
                            })
                            print(f"\n  [HIT] {req.method} {response.url[:100]}")
                            print(f"         Keywords: {matches}")
                            if isinstance(data, dict):
                                print(f"         Keys: {list(data.keys())[:10]}")
                            elif isinstance(data, list):
                                print(f"         List of {len(data)} items")
                    except:
                        pass
        
        page.on("response", handle_response)
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(5000)  # Wait for JS to make API calls
        except Exception as e:
            print(f"  Navigation error: {e}")
        
        browser.close()
    
    if not discovered_apis:
        print("\n  No job-related APIs found.")
    else:
        print(f"\n  Found {len(discovered_apis)} potential job API(s)!")
    
    return discovered_apis


def extract_jobs_from_api(api_info, limit=3):
    """Try to extract job details from a discovered API."""
    data = api_info["data_sample"]
    jobs = []
    
    # Strategy 1: Look for common list patterns
    if isinstance(data, list):
        for item in data[:limit]:
            if isinstance(item, dict):
                title = item.get("title") or item.get("name") or item.get("jobTitle") or item.get("reqTitle") or ""
                location = item.get("location") or item.get("city") or item.get("locationName") or ""
                dept = item.get("department") or item.get("departmentName") or item.get("team") or ""
                if isinstance(location, list):
                    location = ", ".join(str(l) for l in location)
                if isinstance(location, dict):
                    location = location.get("name", "") or location.get("city", "")
                if title:
                    jobs.append({"title": title, "location": str(location), "department": str(dept)})
    
    elif isinstance(data, dict):
        # Try common wrapper keys
        for key in ["jobs", "results", "data", "content", "postings", "positions", 
                     "jobPostings", "items", "openings", "reqDetailsBOList", "requisitions",
                     "records", "list", "hits"]:
            if key in data and isinstance(data[key], list):
                for item in data[key][:limit]:
                    if isinstance(item, dict):
                        title = (item.get("title") or item.get("name") or item.get("jobTitle") 
                                or item.get("reqTitle") or item.get("position_name") or "")
                        location = (item.get("location") or item.get("city") or item.get("locationName")
                                   or item.get("primary_location") or "")
                        dept = (item.get("department") or item.get("departmentName") or item.get("team")
                               or item.get("category") or "")
                        exp = item.get("experience") or item.get("experienceLevel") or ""
                        job_type = item.get("jobType") or item.get("type") or item.get("employment_type") or ""
                        
                        if isinstance(location, list):
                            location = ", ".join(str(l) for l in location)
                        if isinstance(location, dict):
                            location = location.get("name", "") or location.get("city", "")
                        
                        if title:
                            jobs.append({
                                "title": str(title), 
                                "location": str(location), 
                                "department": str(dept),
                                "experience": str(exp),
                                "job_type": str(job_type),
                            })
                break
    
    return jobs


# ============================================================================
#  TEST: Companies that currently fail
# ============================================================================

test_companies = [
    ("Swiggy", "https://careers.swiggy.com/#/careers?src=careers"),
    ("Zomato", "https://www.eternal.com/careers/"),
    ("Uber", "https://www.uber.com/in/en/careers/list/?location=IND-Karn%C4%81taka-Bangalore"),
    ("Salesforce", "https://careers.salesforce.com/en/jobs/?search=&country=India&pagesize=20#results"),
    ("Cisco", "https://careers.cisco.com/global/en/search-results?keywords=india"),
    ("Amazon", "https://www.amazon.jobs/en/search?offset=0&result_limit=10&sort=relevant&distanceType=Mi&radius=24km&latitude=&longitude=&loc_group_id=&loc_query=India&base_query=&city=&country=IND&region=&county=&query_options=&"),
]

print("=" * 60)
print("  API DISCOVERY TOOL - Finding Hidden Job APIs")
print("=" * 60)

for company_name, url in test_companies:
    apis = discover_apis(url, company_name)
    
    for api in apis:
        jobs = extract_jobs_from_api(api)
        if jobs:
            print(f"\n  Extracted {len(jobs)} jobs from {company_name}:")
            for j in jobs:
                print(f"    Title: {j['title']}")
                print(f"    Location: {j['location']}")
                if j.get('department'):
                    print(f"    Department: {j['department']}")
                if j.get('experience'):
                    print(f"    Experience: {j['experience']}")
                if j.get('job_type'):
                    print(f"    Type: {j['job_type']}")
                print()

print("\n\nDone!")
