"""Test all new API endpoints provided by user."""
import sys, requests, json
sys.stdout.reconfigure(encoding="utf-8")

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json, */*"}

def test(name, method, url, **kwargs):
    try:
        r = getattr(requests, method)(url, headers=H, timeout=12, **kwargs)
        is_json = "json" in r.headers.get("content-type", "") or r.text.strip()[:1] in ["{", "["]
        status = "OK" if r.status_code == 200 else "FAIL"
        snippet = r.text[:200].replace("\n", " ")
        print(f"[{status}] {name} | HTTP {r.status_code} | {snippet}")
    except Exception as e:
        print(f"[ERR] {name} | {str(e)[:100]}")
    print()

# Tiger Analytics - SenseHQ
test("Tiger Analytics (SenseHQ)", "get", "https://tiger-analytics.sensehq.com/careers/jobs/")

# PayPal - Eightfold
test("PayPal (Eightfold)", "get",
     "https://paypal.eightfold.ai/api/pcsx/search?domain=paypal.com&location=india&start=0&sort_by=distance")

# Wells Fargo - Umbraco
test("Wells Fargo (Umbraco)", "get",
     "https://www.wellsfargojobs.com/umbraco/jobboard/CandidateJobs/GetJobs?culture=en")

# Citi - Eightfold
test("Citi (Eightfold)", "get",
     "https://citi.eightfold.ai/api/pcsx/search?domain=citi.com&location=india&start=0&sort_by=distance")

# LatentView - Darwinbox POST
test("LatentView (Darwinbox)", "post",
     "https://latentview.darwinbox.in/ms/candidateapi/job/alljobs?companyId=main",
     json={})

# Turing - Direct API
test("Turing", "get", "https://careers.turing.com/api/v3/job-posts")

# LTIMindtree - SAP SuccessFactors
test("LTIMindtree (SAP SF)", "post",
     "https://careers.ltimindtree.com/services/jobs/options/facetValues/",
     json={"facets": ["city"]})

# Wipro - SAP SuccessFactors
test("Wipro (SAP SF)", "post",
     "https://careers.wipro.com/services/recruiting/v1/jobs",
     json={"facets": ["location"], "limit": 5})

# Accenture - Elasticsearch
test("Accenture (ElasticSearch)", "post",
     "https://www.accenture.com/api/accenture/elastic/findjobs",
     json={"jt": "Experience: 0-2 years", "country": "India"})

# Virtusa - GraphQL
test("Virtusa (GraphQL)", "post",
     "https://prod.agenticweb-marketing.com/careers/graphql",
     json={"query": "{ jobs(first: 2) { nodes { title location } } }"},
     headers={**H, "Content-Type": "application/json"})

print("=== Done ===")
