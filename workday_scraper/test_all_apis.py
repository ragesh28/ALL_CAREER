"""
Final test: Extract 1 real job from every discovered API.
Combine all 3 batches of discovery results.
"""
import sys, json, requests, re
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*",
}

results = []

def add(name, title, location, total, api_type, api_url):
    results.append({"company":name,"title":title,"location":location,"total":total,"api_type":api_type,"api_url":api_url})
    print(f"  [+] {name}: {title[:55]} | {location[:30]} | Total:{total} | {api_type}")

def fail(name, reason):
    results.append({"company":name,"title":"NEEDS_WORK","location":"","total":0,"api_type":reason,"api_url":""})
    print(f"  [X] {name}: {reason}")

# === 1. GOOGLE (no API found - needs special handling) ===
print("Testing Google...")
fail("Google", "JS-rendered, no API discovered. Need Playwright + DOM parse")

# === 2. MICROSOFT ===
print("Testing Microsoft...")
try:
    resp = requests.get("https://careers.microsoft.com/professionals/us/en/search-results?keywords=India",
        headers={**HEADERS,"Accept":"text/html"}, timeout=15, verify=False)
    # Try to find embedded JSON data in the page
    import warnings
    warnings.filterwarnings("ignore")
    soup = BeautifulSoup(resp.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if script:
        data = json.loads(script.string)
        jobs = data.get("props",{}).get("pageProps",{}).get("jobs",[])
        if jobs:
            j = jobs[0]
            add("Microsoft", j.get("title",""), j.get("location",""), len(jobs), "Next.js SSR", "__NEXT_DATA__")
        else:
            fail("Microsoft", "Next.js but no jobs in SSR data")
    else:
        fail("Microsoft", "No __NEXT_DATA__, needs Playwright")
except Exception as e:
    fail("Microsoft", f"Error: {str(e)[:60]}")

# === 3. ZOHO ===
print("Testing Zoho...")
try:
    resp = requests.get("https://careers.zohocorp.com/recruit/v2/public/Job_Openings?pagename=Careers&source=CareerSite&extra=true",
        headers=HEADERS, timeout=10)
    data = resp.json()
    if isinstance(data, dict):
        jobs = data.get("data",[]) or data.get("jobs",[]) or data.get("records",[])
        if not jobs:
            for k,v in data.items():
                if isinstance(v, list) and v:
                    jobs = v
                    break
        if jobs:
            j = jobs[0]
            add("Zoho", j.get("Posting_Title",j.get("title",str(j)[:50])), j.get("City",j.get("location","")), len(jobs), "Zoho Recruit API", resp.url)
        else:
            fail("Zoho", f"API returned empty. Keys: {list(data.keys())[:5]}")
    elif isinstance(data, list):
        if data:
            j = data[0]
            add("Zoho", str(j.get("Posting_Title",j.get("title","")))[:50], str(j.get("City",""))[:30], len(data), "Zoho Recruit API", resp.url)
except Exception as e:
    fail("Zoho", f"Error: {str(e)[:60]}")

# === 6. PAYPAL (Eightfold) ===
print("Testing PayPal...")
try:
    resp = requests.get("https://paypal.eightfold.ai/api/apply/v2/jobs?num=1&domain=paypal.com&sort_by=relevance&location=india",
        headers=HEADERS, timeout=10)
    data = resp.json()
    positions = data.get("positions",[])
    total = data.get("count",0)
    if positions:
        j = positions[0]
        loc = ", ".join(j.get("location",[])) if isinstance(j.get("location"),list) else str(j.get("location",""))
        add("PayPal", j.get("name",""), loc, total, "Eightfold API", resp.url)
    else:
        fail("PayPal", f"No positions. Keys: {list(data.keys())}")
except Exception as e:
    fail("PayPal", f"Error: {str(e)[:60]}")

# === 7. AMAZON ===
print("Testing Amazon...")
try:
    resp = requests.get("https://www.amazon.jobs/en/search.json?offset=0&result_limit=1&sort=relevant&country=IND",
        headers={**HEADERS,"Accept":"application/json, text/html"}, timeout=10)
    data = resp.json()
    jobs = data.get("jobs",[])
    if jobs:
        j = jobs[0]
        add("Amazon", j.get("title",""), j.get("normalized_location",""), data.get("hits",0), "Amazon JSON API", resp.url)
except Exception as e:
    fail("Amazon", f"Error: {str(e)[:60]}")

# === 9. INFOSYS ===
print("Testing Infosys...")
try:
    resp = requests.get("https://intapgateway.infosysapps.com/careersci/search/intapjbsrch/getCareerSearchJobs?sourceId=1,21&pageNo=1&pageSize=1&sortField=postedDate&sortOrder=desc&jobCountryCode=IN",
        headers=HEADERS, timeout=10)
    data = resp.json()
    jobs = data.get("hits",{}).get("hits",[]) or data.get("results",[]) or data.get("jobs",[]) or data.get("data",[])
    total = data.get("hits",{}).get("total",{})
    if isinstance(total, dict):
        total = total.get("value",0)
    if not jobs:
        for k,v in data.items():
            if isinstance(v, list) and v:
                jobs = v; break
            if isinstance(v, dict):
                for k2,v2 in v.items():
                    if isinstance(v2, list) and v2:
                        jobs = v2; break
    if jobs:
        j = jobs[0]
        src = j.get("_source",j)
        add("Infosys", src.get("jobTitle",src.get("title",str(src)[:50])), src.get("jobLocation",src.get("location","")), total, "Infosys Gateway API", "intapgateway.infosysapps.com")
    else:
        fail("Infosys", f"No jobs. Keys: {list(data.keys())[:5]}")
except Exception as e:
    fail("Infosys", f"Error: {str(e)[:60]}")

# === 13. SWIGGY ===
print("Testing Swiggy...")
fail("Swiggy", "MyNextHire POST - needs Playwright session token")

# === 15. UBER ===
print("Testing Uber...")
try:
    resp = requests.post("https://www.uber.com/api/loadSearchJobsResults?localeCode=en",
        headers={**HEADERS,"Content-Type":"application/json","x-csrf-token":"x"},
        json={"params":{"location":[{"country":"IND"}],"department":[],"team":[]},"limit":1,"page":1}, timeout=10)
    data = resp.json()
    jobs = data.get("data",{}).get("results",[])
    total_obj = data.get("data",{}).get("totalResults",{})
    total = total_obj.get("low",0) if isinstance(total_obj,dict) else total_obj
    if jobs:
        j = jobs[0]
        locs = j.get("allLocations",[])
        loc = ", ".join([f"{l.get('city','')} {l.get('country','')}".strip() for l in locs]) if locs else ""
        add("Uber", j.get("title",""), loc, total, "Uber API", "uber.com/api/loadSearchJobsResults")
except Exception as e:
    fail("Uber", f"Error: {str(e)[:60]}")

# === 17. SALESFORCE ===
print("Testing Salesforce...")
fail("Salesforce", "Phenom People - discovered cookie consent only, not job API")

# === 18. ATLASSIAN ===
print("Testing Atlassian...")
try:
    resp = requests.get("https://www.atlassian.com/endpoint/careers/listings?location=India",
        headers=HEADERS, timeout=10)
    data = resp.json()
    if isinstance(data, list) and data:
        j = data[0]
        post = j.get("portalJobPost",{})
        locs = post.get("locations",[])
        loc = locs[0].get("name","") if locs else ""
        add("Atlassian", post.get("title",""), loc, len(data), "Atlassian REST API", resp.url)
except Exception as e:
    fail("Atlassian", f"Error: {str(e)[:60]}")

# === 19. ROCKETLANE ===
print("Testing Rocketlane...")
try:
    resp = requests.get("https://careers.kula.ai/api/internal/ats_job_posts?accountName=rocketlane&page=1&type=ats_job_post.index",
        headers=HEADERS, timeout=10)
    data = resp.json()
    jobs = data.get("data",[]) if isinstance(data,dict) else data
    if isinstance(jobs, list) and jobs:
        j = jobs[0]
        add("Rocketlane", j.get("title",j.get("name",str(j)[:50])), j.get("location",""), len(jobs), "Kula API", resp.url)
    else:
        fail("Rocketlane", f"Keys: {list(data.keys()) if isinstance(data,dict) else type(data)}")
except Exception as e:
    fail("Rocketlane", f"Error: {str(e)[:60]}")

# === 26. JPMORGAN ===
print("Testing JPMorgan...")
try:
    resp = requests.get("https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations,flexFieldsFacet.values&finder=findReqs;siteNumber=CX_1001,facetsList=LOCATIONS;WORK_LOCATIONS;WORKPLACE_TYPES;TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS&limit=1&offset=0&sortBy=POSTING_DATES_DESC",
        headers={**HEADERS,"Accept":"application/json"}, timeout=20)
    data = resp.json()
    items = data.get("items",[])
    if items:
        reqs = items[0].get("requisitionList",[])
        total = items[0].get("TotalJobsCount", len(reqs))
        if reqs:
            r = reqs[0]
            add("JPMorgan", r.get("Title",""), r.get("PrimaryLocation",""), total, "Oracle Cloud", "jpmc.fa.oraclecloud.com")
except Exception as e:
    fail("JPMorgan", f"Error: {str(e)[:60]}")

# === 27. WELLS FARGO ===
print("Testing Wells Fargo...")
fail("Wells Fargo", "Phenom People - no job data via API (needs specific params)")

# === 28. CITI ===
print("Testing Citi...")
try:
    resp = requests.get("https://jobs.citi.com/search-jobs/India/287/2/1269750/22/79/50/2", headers={**HEADERS,"Accept":"text/html"}, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = soup.select("#search-results-list li")
    total_match = re.search(r"(\d[\d,]*)\s*Results", soup.get_text())
    total = int(total_match.group(1).replace(",","")) if total_match else 0
    if jobs:
        t = jobs[0].select_one("h2")
        l = jobs[0].select_one(".job-location, [class*=location]")
        add("Citi", t.get_text(strip=True) if t else "", l.get_text(strip=True) if l else "", total, "Server HTML", "jobs.citi.com")
except Exception as e:
    fail("Citi", f"Error: {str(e)[:60]}")

# === 25. CISCO ===
print("Testing Cisco...")
try:
    resp = requests.post("https://careers.cisco.com/widgets",
        headers={**HEADERS,"Content-Type":"application/json"},
        json={"lang":"en_global","deviceType":"desktop","country":"global","pageName":"search-results",
              "ddoKey":"refineSearch","from":0,"jobs":True,"counts":True,
              "all_fields":["category","country","state","city","type"],"size":1,"keywords":"india","jdsource":"facets","is498":True}, timeout=15)
    data = resp.json()
    hits = data.get("refineSearch",{}).get("data",{}).get("jobs",[])
    total = data.get("refineSearch",{}).get("totalHits",0)
    if hits:
        j = hits[0]
        add("Cisco", j.get("title",""), f"{j.get('city','')}, {j.get('country','')}", total, "Phenom People", "careers.cisco.com/widgets")
except Exception as e:
    fail("Cisco", f"Error: {str(e)[:60]}")

# === 35. COMCAST ===
print("Testing Comcast...")
try:
    resp = requests.get("https://jobs.comcast.com/search-jobs/India/45483/2/1269750/22/79/25/2", headers={**HEADERS,"Accept":"text/html"}, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = soup.select("#search-results-list li")
    total_match = re.search(r"(\d[\d,]*)\s*Results", soup.get_text())
    total = int(total_match.group(1).replace(",","")) if total_match else 0
    if jobs:
        t = jobs[0].select_one("h2")
        l = jobs[0].select_one(".job-location")
        add("Comcast", t.get_text(strip=True) if t else "", l.get_text(strip=True) if l else "", total, "Server HTML", "jobs.comcast.com")
except Exception as e:
    fail("Comcast", f"Error: {str(e)[:60]}")

# === 38. TURING ===
print("Testing Turing...")
try:
    resp = requests.get("https://careers.turing.com/api/v3/job-posts", headers=HEADERS, timeout=10)
    data = resp.json()
    jobs = data if isinstance(data, list) else data.get("data",[]) or data.get("jobs",[])
    if jobs:
        j = jobs[0]
        add("Turing", j.get("title",j.get("name","")), j.get("location",""), len(jobs), "Turing REST API", resp.url)
    else:
        fail("Turing", f"No jobs. Type={type(data)}")
except Exception as e:
    fail("Turing", f"Error: {str(e)[:60]}")

# === 39. ACCENTURE ===
print("Testing Accenture...")
try:
    resp = requests.post("https://www.accenture.com/api/accenture/elastic/findjobs",
        headers={**HEADERS,"Content-Type":"application/json"},
        json={"keyword":"","city":"","state":"","country":"India","pageSize":1,"page":1}, timeout=10)
    data = resp.json()
    jobs = data.get("data",[]) or data.get("jobs",[]) or data.get("results",[])
    total = data.get("totalHits",data.get("total",0))
    if not jobs:
        for k,v in data.items():
            if isinstance(v, list) and v:
                jobs = v; break
    if jobs:
        j = jobs[0]
        add("Accenture", j.get("title",j.get("jobTitle","")), j.get("location",j.get("city","")), total, "Accenture Elastic API", "accenture.com/api/accenture/elastic/findjobs")
    else:
        fail("Accenture", f"No jobs. Keys: {list(data.keys())[:5]}")
except Exception as e:
    fail("Accenture", f"Error: {str(e)[:60]}")

# === 40. WIPRO ===
print("Testing Wipro...")
fail("Wipro", "POST /services/recruiting/v1/jobs - needs session/CSRF token from Playwright")

# === 42. CAPGEMINI ===
print("Testing Capgemini...")
fail("Capgemini", "No API found - JS-rendered, needs Playwright DOM parse")

# === 48. ATHENAHEALTH ===
print("Testing Athenahealth...")
try:
    resp = requests.post("https://careers.athenahealth.com/widgets",
        headers={**HEADERS,"Content-Type":"application/json"},
        json={"lang":"en_us","deviceType":"desktop","country":"us","pageName":"search-results",
              "ddoKey":"refineSearch","from":0,"jobs":True,"counts":True,
              "all_fields":["category","country","state","city","type"],"size":1,"keywords":"","jdsource":"facets","is498":True}, timeout=15)
    data = resp.json()
    hits = data.get("refineSearch",{}).get("data",{}).get("jobs",[])
    total = data.get("refineSearch",{}).get("totalHits",0)
    if hits:
        j = hits[0]
        add("Athenahealth", j.get("title",""), f"{j.get('city','')}, {j.get('country','')}", total, "Phenom People", "careers.athenahealth.com/widgets")
except Exception as e:
    fail("Athenahealth", f"Error: {str(e)[:60]}")

# === SKIP COMPANIES ===
fail("TCS", "Use jobspy (LinkedIn)")
fail("Chargebee", "Use jobspy (LinkedIn)")
fail("Kissflow", "Use jobspy (LinkedIn)")
fail("Walmart", "Use jobspy (LinkedIn)")
fail("HCLTech", "Use jobspy (LinkedIn)")
fail("Zomato", "No jobs available")
fail("LTIMindtree", "No API found - needs Playwright or HTML analysis")
fail("Hexaware", "Oracle Cloud timeout - needs retry with correct tenant")
fail("LatentView", "Darwinbox - no API found")
fail("Tiger Analytics", "Small company - HTML scrape or manual")
fail("Ramco Systems", "Small company - HTML scrape")

# === FINAL SUMMARY ===
print("\n" + "=" * 70)
print("  FINAL API DISCOVERY RESULTS - ALL COMPANIES")
print("=" * 70)

working = [r for r in results if r["title"] != "NEEDS_WORK"]
needs_work = [r for r in results if r["title"] == "NEEDS_WORK"]

print(f"\n  WORKING ({len(working)}/{len(results)}):")
for r in working:
    print(f"    {r['company']:20s} | {r['api_type']:25s} | {r['total']:>5} jobs | {r['title'][:40]}")

print(f"\n  NEEDS WORK ({len(needs_work)}/{len(results)}):")
for r in needs_work:
    print(f"    {r['company']:20s} | {r['api_type']}")

with open("final_api_map.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\n  Full results saved to final_api_map.json")
