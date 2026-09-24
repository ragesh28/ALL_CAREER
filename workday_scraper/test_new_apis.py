"""Batch test new company APIs."""
import sys, requests, json
sys.stdout.reconfigure(encoding="utf-8")

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json, */*"}

def test(name, method, url, **kwargs):
    try:
        r = getattr(requests, method)(url, headers=H, timeout=12, **kwargs)
        ct = r.headers.get("content-type", "")
        is_json = "json" in ct or r.text.strip()[:1] in ["{", "["]
        snippet = r.text[:150].replace("\n", " ")
        status = "OK" if r.status_code == 200 and is_json else "FAIL"
        print(f"[{status}] {name} | {r.status_code} | {snippet}")
    except Exception as e:
        print(f"[ERR] {name} | {str(e)[:80]}")
    print()

# Sify Tech
test("Sify - job_list", "post",
     "https://sify.tallite.com/api_sify/icrweb/home/tallite_career_portal_job_list?lngId=1&sellerShortCode=SIF")
test("Sify - search_master", "post",
     "https://sify.tallite.com/api_sify/icrweb/home/tallite_career_portal_job_search_master?lngId=1&sellerShortCode=SIF")

# Tata Elxsi
test("Tata Elxsi - ip-api", "get", "https://ip-api.io/json/")

# Greenhouse companies
for co, board in [
    ("PhonePe", "phonepe"),
    ("Razorpay", "razorpaysoftwareprivatelimited"),
    ("Postman", "postman"),
    ("InMobi", "inmobi"),
    ("Groww", "groww"),
]:
    test(f"{co} (Greenhouse)", "get", f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")

# Lever companies
test("Zeta Suite (Lever)", "get", "https://api.lever.co/v0/postings/zeta?group=team&mode=json")
test("Meesho (Lever)", "get", "https://api.lever.co/v0/postings/meesho?limit=15")

# Cure.fit (Zwayam)
test("Cure.fit (Zwayam)", "post", "https://public.zwayam.com/jobs/search",
     json={"page": 1, "pageSize": 5})

# Goldman Sachs (GraphQL)
gql_payload = {
    "query": """query { jobListings(filter: { location: "Bengaluru" }, first: 3) { edges { node { title jobId location } } } }"""
}
test("Goldman Sachs (GraphQL)", "post", "https://api-higher.gs.com/gateway/api/v1/graphql",
     json=gql_payload, headers={**H, "Content-Type": "application/json"})

# Intuit (Phenom)
test("Intuit (Phenom)", "post", "https://jobs.intuit.com/module/postmodule",
     data={"search": "india"})

# Target India
test("Target India", "post",
     "https://indiajobs.target.com/search-jobs/SetSearchRequestGeoLocation",
     json={"lat": 12.9716, "lng": 77.5946})

print("=== Done ===")
