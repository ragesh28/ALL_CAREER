"""
Glassdoor Scraping Test Script — tries EVERY method and logs diagnostics.
Run on GitHub Actions to identify which approach works from their IPs.
"""
import json
import re
import os
import sys
import time
import requests
from datetime import datetime, timedelta

# ── Config ──
ROLE = "Software Engineer"
CITY_ID = 2940587  # Bangalore
CITY_TYPE = "CITY"
CITY_NAME = "Bangalore"

FALLBACK_TOKEN = "Ft6oHEWlRZrxDww95Cpazw:0pGUrkb2y3TyOpAIqF2vbPmUXoXVkD3oEGDVkvfeCerceQ5-n8mBg3BovySUIjmCPHCaW0H2nQVdqzbtsYqf4Q:wcqRqeegRUa9MVLJGyujVXB7vWFPjdaS1CtrrzJq-ok"

GD_GRAPHQL_QUERY = """
query JobSearchResultsQuery(
    $excludeJobListingIds: [Long!], $keyword: String, $locationId: Int,
    $locationType: LocationTypeEnum, $numJobsToShow: Int!, $pageCursor: String,
    $pageNumber: Int, $filterParams: [FilterParams], $parameterUrlInput: String
) {
    jobListings(contextHolder: {searchParams: {
        excludeJobListingIds: $excludeJobListingIds, keyword: $keyword,
        locationId: $locationId, locationType: $locationType,
        numPerPage: $numJobsToShow, pageCursor: $pageCursor,
        pageNumber: $pageNumber, filterParams: $filterParams,
        parameterUrlInput: $parameterUrlInput, searchType: SR
    }}) {
        jobListings { jobview {
            header { ageInDays employerNameFromSearch jobTitleText locationName __typename }
            job { jobTitleText listingId __typename }
            __typename } __typename }
        totalJobsCount __typename
    }
}
"""

SCRAPERAPI_KEYS = [k.strip() for k in os.environ.get("SCRAPERAPI_KEYS_LIST", "").split(",") if k.strip()]

def sep(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def diagnose_environment():
    """Log environment info to help debug."""
    sep("ENVIRONMENT DIAGNOSTICS")
    
    # Check our public IP
    try:
        ip_resp = requests.get("https://api.ipify.org?format=json", timeout=10)
        ip_data = ip_resp.json()
        print(f"  Public IP: {ip_data.get('ip', 'unknown')}")
    except Exception as e:
        print(f"  Public IP: Failed to detect ({e})")
    
    # Check IP geolocation
    try:
        geo_resp = requests.get("https://ipinfo.io/json", timeout=10)
        geo = geo_resp.json()
        print(f"  Location: {geo.get('city', '?')}, {geo.get('region', '?')}, {geo.get('country', '?')}")
        print(f"  Org: {geo.get('org', '?')}")
    except Exception as e:
        print(f"  Geolocation: Failed ({e})")
    
    # Check if ScraperAPI keys are available
    print(f"  ScraperAPI keys: {len(SCRAPERAPI_KEYS)} found")
    
    # Check Python version
    print(f"  Python: {sys.version}")
    
    # Check if curl_cffi is available
    try:
        from curl_cffi import requests as cr
        print(f"  curl_cffi: Available")
    except ImportError:
        print(f"  curl_cffi: NOT installed")


def test_glassdoor_reachability():
    """Test basic connectivity to Glassdoor."""
    sep("TEST 1: Basic Glassdoor Connectivity")
    
    urls = [
        ("Glassdoor .co.in homepage", "https://www.glassdoor.co.in/"),
        ("Glassdoor .com homepage", "https://www.glassdoor.com/"),
        ("Glassdoor .co.in /graph", "https://www.glassdoor.co.in/graph"),
        ("Glassdoor .com /graph", "https://www.glassdoor.com/graph"),
    ]
    
    for label, url in urls:
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            blocked = "cloudflare" in resp.text.lower() or "cf-" in str(resp.headers)
            print(f"  {label}: HTTP {resp.status_code} | {'CLOUDFLARE BLOCKED' if blocked else 'OK'} | {len(resp.text)} bytes")
        except Exception as e:
            print(f"  {label}: FAILED ({e})")


def test_method_1_requests_graphql():
    """Method 1: Plain requests → GraphQL API with .co.in domain."""
    sep("TEST 2: Plain requests → glassdoor.co.in/graph")
    
    headers = {
        "authority": "www.glassdoor.co.in",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "apollographql-client-name": "job-search-next",
        "apollographql-client-version": "4.65.5",
        "content-type": "application/json",
        "origin": "https://www.glassdoor.co.in",
        "referer": "https://www.glassdoor.co.in/",
        "gd-csrf-token": FALLBACK_TOKEN,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }
    
    payload = json.dumps([{
        "operationName": "JobSearchResultsQuery",
        "variables": {
            "excludeJobListingIds": [],
            "filterParams": [{"filterKey": "fromAge", "values": "3"}],
            "keyword": ROLE,
            "numJobsToShow": 30,
            "locationType": CITY_TYPE,
            "locationId": CITY_ID,
            "parameterUrlInput": f"IL.0,12_I{CITY_TYPE}{CITY_ID}",
            "pageNumber": 1,
            "pageCursor": None,
        },
        "query": GD_GRAPHQL_QUERY,
    }])
    
    try:
        resp = requests.post("https://www.glassdoor.co.in/graph", headers=headers, data=payload, timeout=20)
        print(f"  Status: {resp.status_code}")
        print(f"  Response headers: {dict(list(resp.headers.items())[:5])}")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    job_data = data[0].get("data", {}).get("jobListings", {})
                    total = job_data.get("totalJobsCount", 0)
                    listings = job_data.get("jobListings", [])
                    print(f"  RESULT: {len(listings)} jobs returned, API total: {total}")
                    if listings:
                        first = listings[0]["jobview"]["header"]
                        print(f"  Sample: {first.get('jobTitleText')} at {first.get('employerNameFromSearch')} ({first.get('locationName')})")
                    return len(listings)
                else:
                    print(f"  Response (not a list): {str(data)[:500]}")
            except Exception as e:
                print(f"  JSON parse error: {e}")
                print(f"  Raw response: {resp.text[:500]}")
        else:
            print(f"  Response body: {resp.text[:500]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    return 0


def test_method_2_requests_graphql_dotcom():
    """Method 2: Plain requests → GraphQL API with .com domain."""
    sep("TEST 3: Plain requests → glassdoor.com/graph")
    
    headers = {
        "authority": "www.glassdoor.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "apollographql-client-name": "job-search-next",
        "apollographql-client-version": "4.65.5",
        "content-type": "application/json",
        "origin": "https://www.glassdoor.com",
        "referer": "https://www.glassdoor.com/",
        "gd-csrf-token": FALLBACK_TOKEN,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }
    
    payload = json.dumps([{
        "operationName": "JobSearchResultsQuery",
        "variables": {
            "excludeJobListingIds": [],
            "filterParams": [{"filterKey": "fromAge", "values": "3"}],
            "keyword": ROLE,
            "numJobsToShow": 30,
            "locationType": CITY_TYPE,
            "locationId": CITY_ID,
            "parameterUrlInput": f"IL.0,12_I{CITY_TYPE}{CITY_ID}",
            "pageNumber": 1,
            "pageCursor": None,
        },
        "query": GD_GRAPHQL_QUERY,
    }])
    
    try:
        resp = requests.post("https://www.glassdoor.com/graph", headers=headers, data=payload, timeout=20)
        print(f"  Status: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    job_data = data[0].get("data", {}).get("jobListings", {})
                    total = job_data.get("totalJobsCount", 0)
                    listings = job_data.get("jobListings", [])
                    print(f"  RESULT: {len(listings)} jobs returned, API total: {total}")
                    if listings:
                        first = listings[0]["jobview"]["header"]
                        print(f"  Sample: {first.get('jobTitleText')} at {first.get('employerNameFromSearch')} ({first.get('locationName')})")
                    return len(listings)
                else:
                    print(f"  Response: {str(data)[:500]}")
            except:
                print(f"  Raw: {resp.text[:500]}")
        else:
            print(f"  Response: {resp.text[:300]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    return 0


def test_method_3_fresh_csrf_token():
    """Method 3: Fetch a fresh CSRF token first, then GraphQL."""
    sep("TEST 4: Fresh CSRF token → glassdoor.co.in/graph")
    
    # Step 1: Get fresh CSRF token
    print("  Step 1: Fetching fresh CSRF token...")
    token = None
    for token_url in [
        "https://www.glassdoor.co.in/Job/computer-science-jobs.htm",
        "https://www.glassdoor.com/Job/computer-science-jobs.htm",
    ]:
        try:
            resp = requests.get(token_url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            })
            print(f"    {token_url}: HTTP {resp.status_code}")
            if resp.status_code == 200:
                matches = re.findall(r'"token":\s*"([^"]+)"', resp.text)
                if matches:
                    token = matches[0]
                    print(f"    Got fresh token: {token[:50]}...")
                    break
                else:
                    print(f"    No token found in response ({len(resp.text)} bytes)")
            else:
                print(f"    Response: {resp.text[:200]}")
        except Exception as e:
            print(f"    Error: {e}")
    
    if not token:
        print("  Using fallback token")
        token = FALLBACK_TOKEN
    
    # Step 2: Use token for GraphQL
    print("  Step 2: GraphQL query with token...")
    headers = {
        "authority": "www.glassdoor.co.in",
        "accept": "*/*",
        "apollographql-client-name": "job-search-next",
        "apollographql-client-version": "4.65.5",
        "content-type": "application/json",
        "origin": "https://www.glassdoor.co.in",
        "referer": "https://www.glassdoor.co.in/",
        "gd-csrf-token": token,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }
    
    payload = json.dumps([{
        "operationName": "JobSearchResultsQuery",
        "variables": {
            "excludeJobListingIds": [],
            "filterParams": [{"filterKey": "fromAge", "values": "3"}],
            "keyword": ROLE,
            "numJobsToShow": 30,
            "locationType": CITY_TYPE,
            "locationId": CITY_ID,
            "parameterUrlInput": f"IL.0,12_I{CITY_TYPE}{CITY_ID}",
            "pageNumber": 1,
            "pageCursor": None,
        },
        "query": GD_GRAPHQL_QUERY,
    }])
    
    try:
        resp = requests.post("https://www.glassdoor.co.in/graph", headers=headers, data=payload, timeout=20)
        print(f"    Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                job_data = data[0].get("data", {}).get("jobListings", {})
                total = job_data.get("totalJobsCount", 0)
                listings = job_data.get("jobListings", [])
                print(f"    RESULT: {len(listings)} jobs, API total: {total}")
                return len(listings)
            else:
                print(f"    Response: {str(data)[:500]}")
        else:
            print(f"    Response: {resp.text[:500]}")
    except Exception as e:
        print(f"    ERROR: {e}")
    return 0


def test_method_4_curl_cffi():
    """Method 4: curl_cffi with TLS impersonation."""
    sep("TEST 5: curl_cffi TLS impersonation → GraphQL")
    
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        print("  SKIPPED: curl_cffi not installed")
        return 0
    
    headers = {
        "authority": "www.glassdoor.co.in",
        "accept": "*/*",
        "apollographql-client-name": "job-search-next",
        "apollographql-client-version": "4.65.5",
        "content-type": "application/json",
        "origin": "https://www.glassdoor.co.in",
        "referer": "https://www.glassdoor.co.in/",
        "gd-csrf-token": FALLBACK_TOKEN,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }
    
    payload = json.dumps([{
        "operationName": "JobSearchResultsQuery",
        "variables": {
            "excludeJobListingIds": [],
            "filterParams": [{"filterKey": "fromAge", "values": "3"}],
            "keyword": ROLE,
            "numJobsToShow": 30,
            "locationType": CITY_TYPE,
            "locationId": CITY_ID,
            "parameterUrlInput": f"IL.0,12_I{CITY_TYPE}{CITY_ID}",
            "pageNumber": 1,
            "pageCursor": None,
        },
        "query": GD_GRAPHQL_QUERY,
    }])
    
    for impersonate_version in ["chrome120", "chrome110", "chrome124"]:
        print(f"  Trying impersonate={impersonate_version}...")
        try:
            resp = cffi_requests.post(
                "https://www.glassdoor.co.in/graph",
                headers=headers,
                data=payload,
                impersonate=impersonate_version,
                timeout=20
            )
            print(f"    Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    job_data = data[0].get("data", {}).get("jobListings", {})
                    total = job_data.get("totalJobsCount", 0)
                    listings = job_data.get("jobListings", [])
                    print(f"    RESULT: {len(listings)} jobs, API total: {total}")
                    if listings:
                        return len(listings)
                else:
                    print(f"    Response: {str(data)[:300]}")
            else:
                print(f"    Response: {resp.text[:300]}")
        except Exception as e:
            print(f"    Error: {e}")
    return 0


def test_method_5_scraperapi_graphql():
    """Method 5: ScraperAPI proxy → GraphQL API."""
    sep("TEST 6: ScraperAPI proxy → GraphQL API")
    
    if not SCRAPERAPI_KEYS:
        print("  SKIPPED: No SCRAPERAPI_KEYS_LIST")
        return 0
    
    import random
    api_key = random.choice(SCRAPERAPI_KEYS)
    
    # Use ScraperAPI as a proxy for the GraphQL POST request
    proxies = {
        "http": f"http://scraperapi:{api_key}@proxy-server.scraperapi.com:8001",
        "https": f"http://scraperapi:{api_key}@proxy-server.scraperapi.com:8001",
    }
    
    headers = {
        "authority": "www.glassdoor.co.in",
        "accept": "*/*",
        "apollographql-client-name": "job-search-next",
        "apollographql-client-version": "4.65.5",
        "content-type": "application/json",
        "origin": "https://www.glassdoor.co.in",
        "referer": "https://www.glassdoor.co.in/",
        "gd-csrf-token": FALLBACK_TOKEN,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }
    
    payload = json.dumps([{
        "operationName": "JobSearchResultsQuery",
        "variables": {
            "excludeJobListingIds": [],
            "filterParams": [{"filterKey": "fromAge", "values": "3"}],
            "keyword": ROLE,
            "numJobsToShow": 30,
            "locationType": CITY_TYPE,
            "locationId": CITY_ID,
            "parameterUrlInput": f"IL.0,12_I{CITY_TYPE}{CITY_ID}",
            "pageNumber": 1,
            "pageCursor": None,
        },
        "query": GD_GRAPHQL_QUERY,
    }])
    
    print(f"  Using ScraperAPI key: {api_key[:8]}...")
    try:
        resp = requests.post(
            "https://www.glassdoor.co.in/graph",
            headers=headers,
            data=payload,
            proxies=proxies,
            timeout=60,
            verify=False
        )
        print(f"  Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                job_data = data[0].get("data", {}).get("jobListings", {})
                total = job_data.get("totalJobsCount", 0)
                listings = job_data.get("jobListings", [])
                print(f"  RESULT: {len(listings)} jobs, API total: {total}")
                if listings:
                    first = listings[0]["jobview"]["header"]
                    print(f"  Sample: {first.get('jobTitleText')} at {first.get('employerNameFromSearch')}")
                return len(listings)
            else:
                print(f"  Response: {str(data)[:500]}")
        else:
            print(f"  Response: {resp.text[:500]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    return 0


def test_method_6_scraperapi_url():
    """Method 6: ScraperAPI URL mode → GraphQL (as GET with encoded URL)."""
    sep("TEST 7: ScraperAPI URL mode → Glassdoor HTML page")
    
    if not SCRAPERAPI_KEYS:
        print("  SKIPPED: No SCRAPERAPI_KEYS_LIST")
        return 0
    
    import random, urllib.parse
    api_key = random.choice(SCRAPERAPI_KEYS)
    
    target_url = f"https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={urllib.parse.quote(ROLE + ' ' + CITY_NAME)}"
    scraper_url = f"https://api.scraperapi.com?api_key={api_key}&url={urllib.parse.quote(target_url)}&render=true"
    
    print(f"  Target: {target_url}")
    try:
        resp = requests.get(scraper_url, timeout=90)
        print(f"  Status: {resp.status_code}")
        print(f"  Response size: {len(resp.text)} bytes")
        
        if resp.status_code == 200:
            # Check for job listings in HTML
            job_count = resp.text.count('jobview') + resp.text.count('JobCard') + resp.text.count('job-listing')
            cloudflare = 'cloudflare' in resp.text.lower()
            print(f"  Job markers found: {job_count}")
            print(f"  Cloudflare detected: {cloudflare}")
            
            # Try to find Apollo state
            apollo_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*(\{.*?\});', resp.text)
            if apollo_match:
                print(f"  Apollo state found! Length: {len(apollo_match.group(1))}")
                try:
                    state = json.loads(apollo_match.group(1))
                    jobs_found = sum(1 for k, v in state.items() if isinstance(v, dict) and 'jobview' in v)
                    print(f"  Jobs in Apollo state: {jobs_found}")
                    return jobs_found
                except:
                    pass
            
            # Try __NEXT_DATA__
            next_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text)
            if next_match:
                print(f"  __NEXT_DATA__ found! Length: {len(next_match.group(1))}")
                try:
                    next_data = json.loads(next_match.group(1))
                    print(f"  Keys: {list(next_data.keys())[:5]}")
                except:
                    pass
            
            return job_count
        else:
            print(f"  Response: {resp.text[:300]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    return 0


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("  GLASSDOOR SCRAPING TEST - ALL METHODS")
    print(f"  Role: {ROLE} | City: {CITY_NAME}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    results = {}
    
    diagnose_environment()
    
    test_glassdoor_reachability()
    
    results["requests_co_in"] = test_method_1_requests_graphql()
    time.sleep(1)
    
    results["requests_dotcom"] = test_method_2_requests_graphql_dotcom()
    time.sleep(1)
    
    results["fresh_csrf"] = test_method_3_fresh_csrf_token()
    time.sleep(1)
    
    results["curl_cffi"] = test_method_4_curl_cffi()
    time.sleep(1)
    
    results["scraperapi_proxy"] = test_method_5_scraperapi_graphql()
    time.sleep(1)
    
    results["scraperapi_url"] = test_method_6_scraperapi_url()
    
    # Final summary
    sep("FINAL RESULTS SUMMARY")
    for method, count in results.items():
        status = "WORKS" if count > 0 else "FAILED"
        emoji = "+" if count > 0 else "-"
        print(f"  [{emoji}] {method:25s}: {count:3d} jobs  ({status})")
    
    working = [m for m, c in results.items() if c > 0]
    if working:
        print(f"\n  BEST METHOD: {working[0]} ({results[working[0]]} jobs)")
    else:
        print(f"\n  ALL METHODS FAILED - Glassdoor blocks GitHub Actions IPs")
    
    print("=" * 70)
