"""Fix Wipro payload and Accenture payload, and test Virtusa properly."""
import sys, requests, json
sys.stdout.reconfigure(encoding="utf-8")

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json, */*"}
JH = {**H, "Content-Type": "application/json"}

# Wipro - fix locale
print("=== Wipro ===")
r = requests.post("https://careers.wipro.com/services/recruiting/v1/jobs",
    headers=JH, timeout=12,
    json={"locale": "en_US", "limit": 5, "offset": 0, "facets": {"location": ["India"]}})
print(f"Status: {r.status_code} | {r.text[:300]}")
print()

# Wipro - try with different payload
print("=== Wipro v2 ===")
r = requests.post("https://careers.wipro.com/services/recruiting/v1/jobs",
    headers=JH, timeout=12,
    json={"locale": "en_US", "limit": 5})
print(f"Status: {r.status_code} | {r.text[:300]}")
print()

# Accenture - correct payload
print("=== Accenture ===")
r = requests.post("https://www.accenture.com/api/accenture/elastic/findjobs",
    headers=JH, timeout=12,
    json={"startIndex": 0, "maxResultSize": 5, "jobCountry": "IN", "jobLanguage": "en", "countrySite": "in-en", "sortBy": "Relevancy"})
print(f"Status: {r.status_code} | {r.text[:400]}")
print()

# Virtusa GraphQL - correct way
print("=== Virtusa GraphQL ===")
r = requests.post("https://prod.agenticweb-marketing.com/careers/graphql",
    headers=JH, timeout=12,
    json={"query": "{ jobs(first: 2, filter: {country: \"India\"}) { nodes { title location department } } }"})
print(f"Status: {r.status_code} | {r.text[:400]}")
print()

# Wells Fargo - try alternate endpoints
print("=== Wells Fargo v2 ===")
for url in [
    "https://www.wellsfargojobs.com/umbraco/jobboard/CandidateJobs/GetJobs?culture=en&Keywords=",
    "https://wellsfargo.eightfold.ai/api/pcsx/search?domain=wellsfargo.com&location=india&start=0",
]:
    try:
        r = requests.get(url, headers=H, timeout=10)
        print(f"  {r.status_code} {url[:60]} | {r.text[:150]}")
    except Exception as e:
        print(f"  ERR {url[:60]} | {e}")
print()

print("=== Done ===")
