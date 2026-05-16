"""
New Company Scrapers — SEPARATE file from scrape_all_companies_v2.py
Companies: Bosch, Siemens, GE Healthcare, Honeywell, Qualcomm, Ericsson, Amadeus, Maersk
Uses two-step pagination: Step 1 = discover total, Step 2 = loop all pages.
See .agents/rules/rules.md for coding rules.
"""
import requests
import json
import time
import re
import os
from bs4 import BeautifulSoup
from jobspy import scrape_jobs

# ─── SHARED HELPERS ───────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

def clean(text):
    """Clean whitespace and HTML tags from text."""
    if not text or str(text) == "nan":
        return ""
    text = re.sub(r"<[^>]+>", "", str(text))
    return " ".join(str(text).split()).strip()

def safe_json(resp):
    """Parse JSON safely, handling BOM and encoding issues on Linux."""
    raw = resp.text.lstrip("\ufeff").strip()
    return json.loads(raw)

def jobspy_fallback(company_keyword, limit):
    """Fallback: scrape via JobSpy/LinkedIn across Indian cities."""
    jobs = []
    seen = set()
    cities = ["Chennai", "Bangalore", "Hyderabad", "Mumbai", "Pune", "Delhi", "Kolkata"]
    for city in cities:
        if len(jobs) >= limit:
            break
        try:
            df = scrape_jobs(
                site_name=["linkedin"],
                search_term=company_keyword,
                location=f"{city}, India",
                results_wanted=min(5, limit - len(jobs)),
                country_indeed="India",
            )
            for _, row in df.iterrows():
                if len(jobs) >= limit:
                    break
                url = str(row.get("job_url", ""))
                if url in seen:
                    continue
                seen.add(url)
                loc = str(row.get("location", ""))
                if not loc or loc == "nan":
                    loc = f"{city}, India"
                jobs.append({
                    "title": str(row.get("title", "")),
                    "location": loc,
                    "posted": str(row.get("date_posted", "")),
                    "apply_url": url,
                })
        except Exception:
            continue
    return jobs[:limit]


# ─── 1. QUALCOMM (Phenom People API) ────────────────────────
def scrape_qualcomm(limit=500):
    """Two-step: GET total from first response, then paginate with start param."""
    print("  [Qualcomm] Phenom People API...")
    API = "https://careers.qualcomm.com/api/pcsx/search"
    hdrs = {**HEADERS, "Referer": "https://careers.qualcomm.com/"}
    PAGE = 10
    jobs = []

    try:
        # Step 1: Discovery
        r = requests.get(f"{API}?location=india&start=0&num={PAGE}&domain=qualcomm.com", headers=hdrs, timeout=15)
        r.raise_for_status()
        data = safe_json(r)
        total = data.get("data", {}).get("numFound", 0)
        if total == 0:
            # numFound may be 0 but positions still returned
            total = len(data.get("data", {}).get("positions", []))
        positions = data.get("data", {}).get("positions", [])
        print(f"  [Qualcomm] Total jobs: {total}")

        # Parse first page
        for p in positions:
            locs = p.get("locations", [])
            jobs.append({
                "title": clean(p.get("name", "")),
                "location": clean(locs[0] if locs else "India"),
                "posted": "",
                "apply_url": f"https://careers.qualcomm.com/careers/job/{p.get('id', '')}",
                "total_jobs": max(total, len(positions)),
            })

        # Step 2: Paginate
        max_jobs = min(limit, max(total, 100))
        start = PAGE
        while len(jobs) < max_jobs:
            try:
                r = requests.get(f"{API}?location=india&start={start}&num={PAGE}&domain=qualcomm.com", headers=hdrs, timeout=15)
                r.raise_for_status()
                data = safe_json(r)
                positions = data.get("data", {}).get("positions", [])
                if not positions:
                    break
                for p in positions:
                    if len(jobs) >= max_jobs:
                        break
                    locs = p.get("locations", [])
                    jobs.append({
                        "title": clean(p.get("name", "")),
                        "location": clean(locs[0] if locs else "India"),
                        "posted": "",
                        "apply_url": f"https://careers.qualcomm.com/careers/job/{p.get('id', '')}",
                        "total_jobs": max(total, len(positions)),
                    })
                start += PAGE
                if (start // PAGE) % 50 == 0:
                    print(f"  [Qualcomm] Progress: {len(jobs)} jobs...")
                time.sleep(0.3)
            except Exception as e:
                print(f"  [Qualcomm] Page error at start={start}: {e}")
                time.sleep(1)
                start += PAGE
                continue

        print(f"  [Qualcomm] Done: {len(jobs)} jobs")
        return jobs

    except Exception as e:
        print(f"  [Qualcomm] API failed ({e}), using JobSpy fallback")
        return jobspy_fallback("Qualcomm", limit)


# ─── 2. ERICSSON (Phenom People API — same as Qualcomm) ─────
def scrape_ericsson(limit=500):
    """Same Phenom People API as Qualcomm, different domain."""
    print("  [Ericsson] Phenom People API...")
    API = "https://jobs.ericsson.com/api/pcsx/search"
    hdrs = {**HEADERS, "Referer": "https://jobs.ericsson.com/"}
    PAGE = 10
    jobs = []

    try:
        r = requests.get(f"{API}?location=India&start=0&num={PAGE}&domain=ericsson.com", headers=hdrs, timeout=15)
        r.raise_for_status()
        data = safe_json(r)
        total = data.get("data", {}).get("numFound", 0)
        positions = data.get("data", {}).get("positions", [])
        if total == 0:
            total = len(positions)
        print(f"  [Ericsson] Total jobs: {total}")

        for p in positions:
            locs = p.get("locations", [])
            jobs.append({
                "title": clean(p.get("name", "")),
                "location": clean(locs[0] if locs else "India"),
                "posted": "",
                "apply_url": f"https://jobs.ericsson.com/careers/job/{p.get('id', '')}",
                "total_jobs": max(total, len(positions)),
            })

        max_jobs = min(limit, max(total, 100))
        start = PAGE
        while len(jobs) < max_jobs:
            try:
                r = requests.get(f"{API}?location=India&start={start}&num={PAGE}&domain=ericsson.com", headers=hdrs, timeout=15)
                r.raise_for_status()
                data = safe_json(r)
                positions = data.get("data", {}).get("positions", [])
                if not positions:
                    break
                for p in positions:
                    if len(jobs) >= max_jobs:
                        break
                    locs = p.get("locations", [])
                    jobs.append({
                        "title": clean(p.get("name", "")),
                        "location": clean(locs[0] if locs else "India"),
                        "posted": "",
                        "apply_url": f"https://jobs.ericsson.com/careers/job/{p.get('id', '')}",
                        "total_jobs": max(total, len(positions)),
                    })
                start += PAGE
                if (start // PAGE) % 50 == 0:
                    print(f"  [Ericsson] Progress: {len(jobs)} jobs...")
                time.sleep(0.3)
            except Exception as e:
                print(f"  [Ericsson] Page error: {e}")
                time.sleep(1)
                start += PAGE
                continue

        print(f"  [Ericsson] Done: {len(jobs)} jobs")
        return jobs

    except Exception as e:
        print(f"  [Ericsson] API failed ({e}), using JobSpy fallback")
        return jobspy_fallback("Ericsson", limit)


# ─── 3. SIEMENS (SSR HTML Pagination) ───────────────────────
def scrape_siemens(limit=500):
    """HTML SSR: parse article.article--result, paginate via folderOffset."""
    print("  [Siemens] HTML SSR scraper...")
    BASE = "https://jobs.siemens.com/en_US/externaljobs/SearchJobs/?42414=[812053]"
    hdrs = {**HEADERS, "Accept": "text/html"}
    PAGE = 10
    jobs = []

    try:
        # Step 1: First page + discover total
        r = requests.get(f"{BASE}&folderRecordsPerPage={PAGE}", headers=hdrs, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Find total count from page text
        total = 0
        for el in soup.find_all(True):
            text = el.get_text(strip=True)
            m = re.match(r"^(\d[\d,]+)\s+results?\s+found", text, re.I)
            if m:
                total = int(m.group(1).replace(",", ""))
                break
        if total == 0:
            # Fallback: count pages from pagination
            articles = soup.select("article.article--result")
            total = len(articles) * 10  # estimate

        print(f"  [Siemens] Estimated total: {total}")

        def _parse_articles(soup_obj):
            parsed = []
            for art in soup_obj.select("article.article--result"):
                title_el = art.find("h2") or art.find("h3") or art.find("a")
                loc_el = art.find(class_=re.compile(r"location", re.I))
                link_el = art.find("a", href=True)
                title = title_el.get_text(strip=True) if title_el else ""
                loc = loc_el.get_text(strip=True) if loc_el else "India"
                href = link_el["href"] if link_el else ""
                if title:
                    parsed.append({
                        "title": clean(title),
                        "location": clean(loc),
                        "posted": "",
                        "apply_url": href,
                        "total_jobs": total,
                    })
            return parsed

        # Parse first page
        jobs.extend(_parse_articles(soup))

        # Step 2: Paginate
        max_jobs = min(limit, max(total, 100))
        offset = PAGE
        while len(jobs) < max_jobs:
            try:
                r = requests.get(f"{BASE}&folderOffset={offset}&folderRecordsPerPage={PAGE}", headers=hdrs, timeout=15)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                page_jobs = _parse_articles(soup)
                if not page_jobs:
                    break
                jobs.extend(page_jobs)
                offset += PAGE
                if (offset // PAGE) % 50 == 0:
                    print(f"  [Siemens] Progress: {len(jobs)} jobs...")
                time.sleep(0.3)
            except Exception as e:
                print(f"  [Siemens] Page error: {e}")
                time.sleep(1)
                offset += PAGE
                continue

        print(f"  [Siemens] Done: {len(jobs)} jobs")
        return jobs[:limit]

    except Exception as e:
        print(f"  [Siemens] HTML failed ({e}), using JobSpy fallback")
        return jobspy_fallback("Siemens", limit)


# ─── 4. AMADEUS (Workday API) ───────────────────────────────
def scrape_amadeus(limit=500):
    """Workday POST API with offset pagination."""
    print("  [Amadeus] Workday API...")
    API = "https://amadeus.wd502.myworkdayjobs.com/wday/cxs/amadeus/jobs/jobs"
    hdrs = {**HEADERS, "Content-Type": "application/json"}
    PAGE = 20
    jobs = []

    try:
        # Step 1: Discovery
        r = requests.post(API, headers=hdrs, json={"appliedFacets": {}, "limit": PAGE, "offset": 0, "searchText": "India"}, timeout=15)
        r.raise_for_status()
        data = safe_json(r)
        total = data.get("total", 0)
        print(f"  [Amadeus] Total jobs: {total}")

        def _parse_workday(data_obj):
            parsed = []
            for jp in data_obj.get("jobPostings", []):
                parsed.append({
                    "title": clean(jp.get("title", "")),
                    "location": clean(jp.get("locationsText", "India")),
                    "posted": clean(jp.get("postedOn", "")),
                    "apply_url": f"https://amadeus.wd502.myworkdayjobs.com{jp.get('externalPath', '')}",
                    "total_jobs": total,
                })
            return parsed

        jobs.extend(_parse_workday(data))

        # Step 2: Paginate
        max_jobs = min(limit, total)
        offset = PAGE
        while len(jobs) < max_jobs:
            try:
                r = requests.post(API, headers=hdrs,
                    json={"appliedFacets": {}, "limit": PAGE, "offset": offset, "searchText": "India"}, timeout=15)
                r.raise_for_status()
                data = safe_json(r)
                page_jobs = _parse_workday(data)
                if not page_jobs:
                    break
                jobs.extend(page_jobs)
                offset += PAGE
                if (offset // PAGE) % 50 == 0:
                    print(f"  [Amadeus] Progress: {len(jobs)} jobs...")
                time.sleep(0.3)
            except Exception as e:
                print(f"  [Amadeus] Page error: {e}")
                time.sleep(1)
                offset += PAGE
                continue

        print(f"  [Amadeus] Done: {len(jobs)} jobs")
        return jobs[:limit]

    except Exception as e:
        print(f"  [Amadeus] API failed ({e}), using JobSpy fallback")
        return jobspy_fallback("Amadeus", limit)


# ─── 5. GE HEALTHCARE (Phenom /widgets API) ─────────────────
def scrape_ge_healthcare(limit=500):
    """Phenom /widgets API. Unlocked: Extract x-csrf-token from search page first."""
    print("  [GE Healthcare] Phenom /widgets API...")
    API = "https://careers.gehealthcare.com/widgets"
    PAGE = 10
    jobs = []

    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        # Step 1: Get CSRF token
        page_url = "https://careers.gehealthcare.com/global/en/search-results?location=India"
        pr = s.get(page_url, timeout=15)
        pr.raise_for_status()
        
        token_match = re.search(r'"csrfToken":"([^"]+)"', pr.text)
        if not token_match:
            raise ValueError("Could not extract x-csrf-token from page HTML")
        csrf_token = token_match.group(1)
        print(f"  [GE Healthcare] Found CSRF Token: {csrf_token[:15]}...")

        hdrs = {
            **HEADERS,
            "x-csrf-token": csrf_token,
            "Content-Type": "application/json",
            "Referer": page_url,
            "Origin": "https://careers.gehealthcare.com",
        }

        # Step 2: Paginate
        payload = {
            "lang": "en_global", "deviceType": "desktop", "pageName": "search-results",
            "ddoKey": "refineSearch",
            "payload": {"from": 0, "size": PAGE, "location": "India"}
        }

        # Initial call to get total
        r = s.post(API, headers=hdrs, json=payload, timeout=15)
        r.raise_for_status()
        data = safe_json(r)
        rs = data.get("refineSearch", {})
        total = rs.get("totalHits", 0)
        print(f"  [GE Healthcare] Total jobs: {total}")

        max_jobs = min(limit, total)
        offset = 0
        while len(jobs) < max_jobs:
            try:
                payload["payload"]["from"] = offset
                r = s.post(API, headers=hdrs, json=payload, timeout=15)
                r.raise_for_status()
                data = safe_json(r)
                page_jobs = data.get("refineSearch", {}).get("data", {}).get("jobs", [])
                if not page_jobs:
                    break
                for j in page_jobs:
                    if len(jobs) >= max_jobs:
                        break
                    jobs.append({
                        "title": clean(j.get("title", "")),
                        "location": clean(j.get("city", j.get("multi_location", ["India"])[0] if j.get("multi_location") else "India")),
                        "posted": clean(j.get("postedDate", "")),
                        "apply_url": f"https://careers.gehealthcare.com/global/en/job/{j.get('jobId', '')}",
                        "total_jobs": total,
                    })
                offset += PAGE
                if (offset // PAGE) % 10 == 0:
                    print(f"  [GE Healthcare] Progress: {len(jobs)} jobs...")
                time.sleep(0.3)
            except Exception as e:
                print(f"  [GE Healthcare] Page error: {e}")
                time.sleep(1)
                offset += PAGE
                continue

        print(f"  [GE Healthcare] Done: {len(jobs)} jobs")
        return jobs[:limit]

    except Exception as e:
        print(f"  [GE Healthcare] API issue ({e}), using JobSpy fallback")
        return jobspy_fallback("GE Healthcare", limit)


# ─── 6. HONEYWELL (Oracle HCM REST API) ───────────────────────
def scrape_honeywell(limit=500):
    """Honeywell Oracle HCM API. Unlocked: finder requires locationId."""
    print("  [Honeywell] Oracle HCM API...")
    BASE_URL = "https://ibqbjb.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    # Added expand=requisitionList because Oracle puts jobs inside the items[0].requisitionList
    API = f"{BASE_URL}?onlyData=true&expand=requisitionList.secondaryLocations,flexFieldsFacet.values&finder=findReqs;siteNumber=CX_1,locationId=300000000469485,sortBy=POSTING_DATES_DESC"
    PAGE = 25
    jobs = []

    try:
        # Step 1: Discovery
        r = requests.get(f"{API},limit={PAGE}", headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = safe_json(r)
        items = data.get("items", [])
        if not items:
            raise ValueError("Empty items from Oracle HCM")
        
        total = items[0].get("TotalJobsCount", 0)
        print(f"  [Honeywell] Total jobs: {total}")

        def _parse_oracle(items_obj):
            parsed = []
            if not items_obj: return parsed
            req_list = items_obj[0].get("requisitionList", [])
            for j in req_list:
                loc = j.get("PrimaryLocation", "India")
                other_locs = [l.get("Name", "") for l in j.get("otherWorkLocations", [])]
                if other_locs:
                    loc += " / " + " / ".join(filter(None, other_locs))
                parsed.append({
                    "title": clean(j.get("Title", "")),
                    "location": clean(loc),
                    "posted": clean(j.get("PostedDate", "")),
                    "apply_url": f"https://careers.honeywell.com/us/en/job/{j.get('Id', '')}",
                    "total_jobs": total,
                })
            return parsed

        jobs.extend(_parse_oracle(items))

        # Step 2: Paginate
        max_jobs = min(limit, total)
        offset = PAGE
        while len(jobs) < max_jobs:
            try:
                r = requests.get(f"{API},limit={PAGE}&offset={offset}", headers=HEADERS, timeout=15)
                r.raise_for_status()
                data = safe_json(r)
                page_jobs = _parse_oracle(data.get("items", []))
                if not page_jobs:
                    break
                jobs.extend(page_jobs)
                offset += PAGE
                if (offset // PAGE) % 5 == 0:
                    print(f"  [Honeywell] Progress: {len(jobs)} jobs...")
                time.sleep(0.3)
            except Exception as e:
                print(f"  [Honeywell] Page error: {e}")
                time.sleep(1)
                offset += PAGE
                continue

        print(f"  [Honeywell] Done: {len(jobs)} jobs")
        return jobs[:limit]

    except Exception as e:
        print(f"  [Honeywell] API failed ({e}), using JobSpy fallback")
        return jobspy_fallback("Honeywell", limit)


# ─── 7. BOSCH (Session Bearer Token → JobSpy fallback) ──────
def scrape_bosch(limit=500):
    """Bosch CaaS API requires a session Bearer token extracted from the career page.
    Falls back to JobSpy if token extraction fails."""
    print("  [Bosch] Extracting session token...")
    API = "https://bosch-i3-caas-api.e-spirit.cloud/bosch-i3-prod/bosch-de.jobs.content/_aggrs/get_jobs"
    PAGE = 8
    jobs = []

    try:
        # Visit main page to extract Bearer token from embedded JS
        s = requests.Session()
        s.headers.update(HEADERS)
        page_r = s.get("https://jobs.bosch.com/en?country=in", timeout=15)
        page_r.raise_for_status()

        # Extract Bearer token from page source
        tokens = re.findall(r'Bearer\s+([a-zA-Z0-9._-]{20,})', page_r.text)
        if not tokens:
            # Try finding it in script tags as a variable
            tokens = re.findall(r'accessToken["\s:=]+["\']([^"\']+ )["\']', page_r.text, re.I)
        if not tokens:
            raise ValueError("Could not extract Bearer token from page")

        token = tokens[0]
        print(f"  [Bosch] Token found: {token[:20]}...")

        # Step 1: Get count
        count_url = f"https://bosch-i3-caas-api.e-spirit.cloud/bosch-i3-prod/bosch-de.jobs.content/?count&filter=%7B%22location.country%22%3A%22in%22%7D"
        cr = s.get(count_url, headers={"Authorization": f"Bearer {token}", "Referer": "https://jobs.bosch.com/"}, timeout=10)
        total = int(cr.text.strip()) if cr.status_code == 200 and cr.text.strip().isdigit() else 0
        print(f"  [Bosch] Total jobs: {total}")

        if total == 0:
            raise ValueError("Count returned 0")

        # Step 2: Paginate
        max_pages = min((limit + PAGE - 1) // PAGE, (total + PAGE - 1) // PAGE)
        for page in range(1, max_pages + 1):
            if len(jobs) >= limit:
                break
            try:
                r = s.get(f"{API}?page={page}&pagesize={PAGE}&avars=%7B%22country%22%3A%5B%22in%22%5D%7D",
                    headers={"Authorization": f"Bearer {token}", "Referer": "https://jobs.bosch.com/"}, timeout=15)
                r.raise_for_status()
                data = safe_json(r)
                items = data if isinstance(data, list) else data.get("items", data.get("_embedded", []))
                if not items:
                    break
                for item in items:
                    if len(jobs) >= limit:
                        break
                    title = item.get("title", item.get("name", ""))
                    loc = item.get("location", {}).get("city", "India") if isinstance(item.get("location"), dict) else str(item.get("location", "India"))
                    jobs.append({
                        "title": clean(str(title)),
                        "location": clean(str(loc)),
                        "posted": "",
                        "apply_url": f"https://jobs.bosch.com/en/job/{item.get('id', '')}",
                        "total_jobs": total,
                    })
                if page % 50 == 0:
                    print(f"  [Bosch] Progress: {len(jobs)} jobs...")
                time.sleep(0.3)
            except Exception as e:
                print(f"  [Bosch] Page {page} error: {e}")
                time.sleep(1)
                continue

        if jobs:
            print(f"  [Bosch] Done: {len(jobs)} jobs")
            return jobs[:limit]
        raise ValueError("Token worked but got 0 jobs")

    except Exception as e:
        print(f"  [Bosch] API failed ({e}), using JobSpy fallback")
        return jobspy_fallback("Bosch", limit)


# ─── 8. MAERSK (Native GraphQL/REST API) ──────────────────────
def scrape_maersk(limit=500):
    """Maersk Careers API. Unlocked: uses api.maersk.com with consumer-key."""
    print("  [Maersk] Native API...")
    API = "https://api.maersk.com/careers/vacancies"
    PAGE = 24
    jobs = []

    try:
        # We can extract the latest consumer-key from the main HTML page
        # but for now we'll use the working one or fallback if it fails.
        consumer_key = "ean6qqcQIuGza1IZ1Rg9dgfjZhlGE7Dw"
        
        # Try dynamic extraction
        try:
            r_html = requests.get("https://www.maersk.com/careers/vacancies", headers=HEADERS, timeout=10)
            key_match = re.search(r'consumer[-_]?key["\']?\s*:\s*["\']([a-zA-Z0-9]+)["\']', r_html.text, re.I)
            if key_match:
                consumer_key = key_match.group(1)
                print(f"  [Maersk] Extracted dynamic consumer-key: {consumer_key[:10]}...")
        except Exception:
            pass

        hdrs = {**HEADERS, "consumer-key": consumer_key}

        # Step 1: Discovery
        r = requests.get(f"{API}?limit={PAGE}&offset=0&city=india", headers=hdrs, timeout=15)
        r.raise_for_status()
        data = safe_json(r)
        total = data.get("ResultCount", 0)
        print(f"  [Maersk] Total jobs: {total}")

        def _parse_maersk(data_obj):
            parsed = []
            for j in data_obj.get("Results", []):
                loc = j.get("City", j.get("Location", "India"))
                parsed.append({
                    "title": clean(j.get("Title", "")),
                    "location": clean(loc),
                    "posted": clean(j.get("PostedDT", "")),
                    "apply_url": f"https://www.maersk.com/careers/vacancies/{j.get('Key', '')}",
                    "total_jobs": total,
                })
            return parsed

        jobs.extend(_parse_maersk(data))

        # Step 2: Paginate
        max_jobs = min(limit, total)
        offset = PAGE
        while len(jobs) < max_jobs:
            try:
                r = requests.get(f"{API}?limit={PAGE}&offset={offset}&city=india", headers=hdrs, timeout=15)
                r.raise_for_status()
                data = safe_json(r)
                page_jobs = _parse_maersk(data)
                if not page_jobs:
                    break
                jobs.extend(page_jobs)
                offset += PAGE
                if (offset // PAGE) % 5 == 0:
                    print(f"  [Maersk] Progress: {len(jobs)} jobs...")
                time.sleep(0.3)
            except Exception as e:
                print(f"  [Maersk] Page error: {e}")
                time.sleep(1)
                offset += PAGE
                continue

        print(f"  [Maersk] Done: {len(jobs)} jobs")
        return jobs[:limit]

    except Exception as e:
        print(f"  [Maersk] API failed ({e}), using JobSpy fallback")
        return jobspy_fallback("Maersk", limit)


# ─── 9. BANK OF AMERICA (REST API with security headers) ────
def scrape_bofa(limit=500):
    """BofA job search API with x-requested-with + Referer headers.
    Two-step: totalMatches for count, paginate with start param."""
    print("  [Bank of America] REST API...")
    API = "https://careers.bankofamerica.com/services/jobssearchservlet"
    hdrs = {
        **HEADERS,
        "Referer": "https://careers.bankofamerica.com/en-us/job-search/india",
        "x-requested-with": "XMLHttpRequest",
    }
    PAGE = 10
    jobs = []

    try:
        # Step 1: Discovery
        r = requests.get(f"{API}?start=0&rows={PAGE}&search=jobsByLocation&searchstring=India", headers=hdrs, timeout=15)
        r.raise_for_status()
        data = safe_json(r)
        total = data.get("totalMatches", 0)
        print(f"  [Bank of America] Total jobs: {total}")

        def _parse_bofa(data_obj):
            parsed = []
            for j in data_obj.get("jobsList", []):
                title = j.get("postingTitle", "")
                loc = j.get("primaryLocation", j.get("location", "India"))
                jcr_url = j.get("jcrURL", "")
                apply_url = f"https://careers.bankofamerica.com{jcr_url}" if jcr_url else "https://careers.bankofamerica.com"
                parsed.append({
                    "title": clean(title),
                    "location": clean(loc),
                    "posted": clean(j.get("postedDate", j.get("externalPostedDate", ""))),
                    "apply_url": apply_url,
                    "total_jobs": total,
                })
            return parsed

        jobs.extend(_parse_bofa(data))

        # Step 2: Paginate
        max_jobs = min(limit, total)
        start = PAGE
        while len(jobs) < max_jobs:
            try:
                r = requests.get(f"{API}?start={start}&rows={PAGE}&search=jobsByLocation&searchstring=India", headers=hdrs, timeout=15)
                r.raise_for_status()
                data = safe_json(r)
                page_jobs = _parse_bofa(data)
                if not page_jobs:
                    break
                jobs.extend(page_jobs)
                start += PAGE
                if (start // PAGE) % 10 == 0:
                    print(f"  [Bank of America] Progress: {len(jobs)} jobs...")
                time.sleep(0.3)
            except Exception as e:
                print(f"  [Bank of America] Page error: {e}")
                time.sleep(1)
                start += PAGE
                continue

        print(f"  [Bank of America] Done: {len(jobs)} jobs")
        return jobs[:limit]

    except Exception as e:
        print(f"  [Bank of America] API failed ({e}), using JobSpy fallback")
        return jobspy_fallback("Bank of America", limit)


# ─── COMPANY REGISTRY ────────────────────────────────────────
COMPANIES = {
    "Qualcomm": scrape_qualcomm,
    "Ericsson": scrape_ericsson,
    "Siemens": scrape_siemens,
    "Amadeus": scrape_amadeus,
    "GE Healthcare": scrape_ge_healthcare,
    "Honeywell": scrape_honeywell,
    "Bosch": scrape_bosch,
    "Maersk": scrape_maersk,
    "Bank of America": scrape_bofa,
}


# ─── MAIN ────────────────────────────────────────────────────
def scrape_all_new_companies(limit=500, output_file="new_company_jobs.json"):
    """Scrape all new companies and save to JSON."""
    all_results = {}
    total_jobs = 0

    print(f"\n{'='*60}")
    print(f"Scraping {len(COMPANIES)} new companies (limit={limit} per company)")
    print(f"{'='*60}\n")

    for i, (name, scraper) in enumerate(COMPANIES.items(), 1):
        print(f"[{i}/{len(COMPANIES)}] {name}")
        try:
            jobs = scraper(limit)
            all_results[name] = {
                "jobs": jobs,
                "count": len(jobs),
                "status": "OK" if jobs else "EMPTY",
            }
            total_jobs += len(jobs)
            status = f"✅ {len(jobs)} jobs" if jobs else "⚠️ 0 jobs"
            print(f"  -> {status}\n")
        except Exception as e:
            all_results[name] = {"jobs": [], "count": 0, "status": f"FAILED: {e}"}
            print(f"  -> ❌ FAILED: {e}\n")

    # Save results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n{'='*60}")
    print(f"Total: {total_jobs} jobs from {len(COMPANIES)} companies")
    print(f"Saved to {output_file}")
    print(f"{'='*60}")

    return all_results


if __name__ == "__main__":
    # Default: scrape with limit=500 per company
    scrape_all_new_companies(limit=500)
