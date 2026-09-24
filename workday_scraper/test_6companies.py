"""Test 6 specific companies only."""
import sys, requests
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json"}

# ── 1. LatentView (Darwinbox) ──
print("\n=== LatentView ===")
try:
    raw = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.on("response", lambda r: raw.append(r.body()) if "alljobs" in r.url else None)
        pg.goto("https://latentview.darwinbox.in/ms/candidatev2/main/careers/allJobs", wait_until="domcontentloaded", timeout=20000)
        pg.wait_for_timeout(8000)
        b.close()
    print(f"API responses caught: {len(raw)}")
    if raw:
        print("Sample:", raw[0][:200])
    else:
        print("FAIL - no API response caught")
except Exception as e:
    print(f"ERROR: {e}")

# ── 2. Tiger Analytics (WordPress admin-ajax) ──
print("\n=== Tiger Analytics ===")
try:
    r = requests.post("https://www.tigeranalytics.com/wp-admin/admin-ajax.php",
        headers={**H, "Content-Type": "application/x-www-form-urlencoded", "Referer": "https://www.tigeranalytics.com/"},
        data="action=refill", timeout=10)
    print(f"Status: {r.status_code} | Content-Type: {r.headers.get('content-type','')}")
    print("Body:", r.text[:300])
except Exception as e:
    print(f"ERROR: {e}")

# ── 3. Accenture ──
print("\n=== Accenture ===")
try:
    raw = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.on("response", lambda r: raw.append((r.url, r.body())) if "GetResults" in r.url else None)
        pg.goto("https://www.accenture.com/in-en/careers/jobsearch?jt=Experience%3A%200-2%20years", wait_until="domcontentloaded", timeout=20000)
        pg.wait_for_timeout(10000)
        b.close()
    print(f"API responses caught: {len(raw)}")
    if raw:
        print("URL:", raw[0][0])
        print("Sample:", raw[0][1][:300])
    else:
        print("FAIL - no GetResults API caught")
except Exception as e:
    print(f"ERROR: {e}")

# ── 4. Wipro ──
print("\n=== Wipro ===")
try:
    raw = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.on("response", lambda r: raw.append((r.url, r.body())) if "/api/v1/jobs" in r.url else None)
        pg.goto("https://careers.wipro.com/search/?q=&locationsearch=india", wait_until="domcontentloaded", timeout=20000)
        pg.wait_for_timeout(10000)
        b.close()
    print(f"API responses caught: {len(raw)}")
    if raw:
        print("URL:", raw[0][0])
        print("Sample:", raw[0][1][:300])
    else:
        print("FAIL - no /api/v1/jobs caught")
except Exception as e:
    print(f"ERROR: {e}")

# ── 5. Virtusa (GraphQL) ──
print("\n=== Virtusa ===")
try:
    raw = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.on("response", lambda r: raw.append((r.url, r.body())) if "graphql" in r.url.lower() else None)
        pg.goto("https://www.virtusa.com/careers/job-search#india", wait_until="domcontentloaded", timeout=20000)
        pg.wait_for_timeout(10000)
        b.close()
    print(f"API responses caught: {len(raw)}")
    if raw:
        print("URL:", raw[0][0])
        print("Sample:", raw[0][1][:300])
    else:
        print("FAIL - no graphql caught")
except Exception as e:
    print(f"ERROR: {e}")

# ── 6. Hexaware (Oracle Cloud) ──
print("\n=== Hexaware ===")
try:
    # Try to find the correct Oracle Cloud base URL
    for base in ["https://hexaware.fa.us2.oraclecloud.com", "https://hexaware.fa.oraclecloud.com", "https://eeho.fa.us2.oraclecloud.com"]:
        try:
            r = requests.get(f"{base}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=CX_1,limit=1,sortBy=POSTING_DATES_DESC", headers=H, timeout=15)
            print(f"{base}: {r.status_code} | {r.text[:200]}")
        except Exception as e:
            print(f"{base}: {e}")
except Exception as e:
    print(f"ERROR: {e}")

print("\nDone.")
