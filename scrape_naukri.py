import os
import sys
import re
import json
import time
import requests
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")
requests.packages.urllib3.disable_warnings()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
ACCOUNT_ID          = "62eacb67a7ee0b199f58ccb540a3eff7"
DATABASE_ID         = "20b71b5c-c070-45b5-9542-27ed1cad89e5"

PROGRESS_FILE   = "naukri_progress.json"
START_TIME      = time.time()
MAX_RUN_SECONDS = 5 * 3600 + 50 * 60   # 5 h 50 m

# Pages to scrape per (role, city) combination
PAGES = [1, 2, 3, 4]

# 50+ roles — tech + non-tech
SEARCH_ROLES = [
    # Tech roles
    "Software Engineer", "Software Developer", "Frontend Developer",
    "Backend Developer", "Full Stack Developer", "Mobile App Developer",
    "Android Developer", "iOS Developer", "React Developer",
    "Node.js Developer", "Python Developer", "Java Developer",
    "DevOps Engineer", "Site Reliability Engineer", "Cloud Engineer",
    "Data Analyst", "Data Engineer", "Data Scientist",
    "Machine Learning Engineer", "AI Engineer", "Deep Learning Engineer",
    "Business Intelligence Analyst", "ETL Developer",
    "QA Engineer", "Test Automation Engineer", "SDET",
    "Cybersecurity Analyst", "Network Engineer", "System Administrator",
    "Database Administrator", "SAP Consultant", "Salesforce Developer",
    "UI UX Designer", "Product Manager", "Technical Project Manager",
    "Embedded Systems Engineer", "VLSI Engineer", "Hardware Engineer",
    "Blockchain Developer", "Game Developer",
    # Non-tech roles
    "HR Manager", "HR Executive", "Talent Acquisition Specialist",
    "Business Development Executive", "Sales Executive", "Sales Manager",
    "Marketing Executive", "Digital Marketing Manager", "Content Writer",
    "Finance Executive", "Accountant", "Financial Analyst",
    "Operations Manager", "Supply Chain Manager", "Logistics Executive",
    "Customer Support Executive", "Customer Success Manager",
    "Graphic Designer", "Video Editor",
]

# Big Indian cities
LOCATIONS = [
    "Bangalore", "Chennai", "Hyderabad", "Mumbai",
    "Pune", "Delhi", "Noida", "Gurgaon",
    "Kolkata", "Ahmedabad", "Coimbatore", "Kochi",
]

TEST_MODE = "--test" in sys.argv
if TEST_MODE:
    print("TEST MODE: 1 role, 1 city, 1 page only")
    SEARCH_ROLES = ["Software Engineer"]
    LOCATIONS    = ["Chennai"]
    PAGES        = [1]

# ---------------------------------------------------------------------------
# PROGRESS CHECKPOINT
# ---------------------------------------------------------------------------
def load_progress():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(PROGRESS_FILE) as f:
            data = json.load(f)
        if data.get("date") != today:
            print(f"New day — resetting progress (was {data.get('date')}, now {today})")
            return {"role_idx": 0, "loc_idx": 0, "date": today, "finished": False}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"role_idx": 0, "loc_idx": 0, "date": today, "finished": False}

def save_progress(role_idx, loc_idx, finished=False):
    today = datetime.now().strftime("%Y-%m-%d")
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"role_idx": role_idx, "loc_idx": loc_idx,
                   "date": today, "finished": finished}, f)

# ---------------------------------------------------------------------------
# CLOUDFLARE D1 DATABASE
# ---------------------------------------------------------------------------
def d1_execute(sql, params=None):
    pass

import storage
def store_jobs_batch(jobs):
    return storage.store_jobs_batch(jobs)

def cleanup_old_jobs():
    pass

def parse_date_posted(text):
    if not text:
        return datetime.now().strftime("%Y-%m-%d")
    s = str(text).strip().lower()
    today = datetime.now()
    if any(k in s for k in ["just now", "today", "hour", "minute", "second"]):
        return today.strftime("%Y-%m-%d")
    if "yesterday" in s or "1 day" in s:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    m = re.search(r"(\d+)\s+day", s)
    if m:
        return (today - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return today.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# PLAYWRIGHT BROWSER (headful for Naukri)
# ---------------------------------------------------------------------------
_pw = None
_browser = None
_context = None

def init_playwright():
    global _pw, _browser, _context
    from playwright.sync_api import sync_playwright
    _pw      = sync_playwright().start()
    _browser = _pw.chromium.launch(
        headless=False,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--window-size=1920,1080",
        ],
    )
    _context = _browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="en-IN",
        timezone_id="Asia/Kolkata",
    )
    print("Playwright browser ready (headful mode)")

def close_playwright():
    global _pw, _browser, _context
    for obj in [_context, _browser]:
        try:
            obj.close()
        except Exception:
            pass
    try:
        _pw.stop()
    except Exception:
        pass
    print("Playwright browser closed")

# ---------------------------------------------------------------------------
# NAUKRI URL BUILDER
# Naukri URL formats:
#   Page 1:  /software-engineer-jobs-in-chennai?jobAge=1
#   Page 2:  /software-engineer-jobs-in-chennai-2?jobAge=1
#   Page 3:  /software-engineer-jobs-in-chennai-3?jobAge=1
#
# Generic city-only (all roles):
#   Page 1:  /jobs-in-chennai?jobAge=1
#   Page 2:  /jobs-in-chennai-2?jobAge=1
# ---------------------------------------------------------------------------
def naukri_url(role, city, page):
    role_slug = role.strip().lower().replace(" ", "-")
    city_slug = city.strip().lower().split(",")[0].strip().replace(" ", "-")
    suffix    = "" if page == 1 else f"-{page}"
    return f"https://www.naukri.com/{role_slug}-jobs-in-{city_slug}{suffix}?jobAge=1"

# ---------------------------------------------------------------------------
# SCRAPE ONE PAGE
# Opens Naukri in a real browser, waits for the internal
# jobapi/v3/search XHR to fire, then reads the JSON payload.
# Returns a list of job dicts.
# ---------------------------------------------------------------------------
def scrape_naukri_page(role, city, page):
    global _context
    url = naukri_url(role, city, page)
    captured = []

    def on_response(response):
        try:
            if "jobapi/v3/search" in response.url:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    captured.append(response.json())
        except Exception:
            pass

    page_obj = _context.new_page()
    try:
        page_obj.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};"
        )
        page_obj.on("response", on_response)
        page_obj.goto(url, wait_until="networkidle", timeout=60_000)

        # Brief human-like scroll to trigger lazy loads
        page_obj.mouse.wheel(0, 600)
        time.sleep(1.5)
        page_obj.mouse.wheel(0, 600)
        time.sleep(1.0)
    except Exception as e:
        print(f"    Page error ({url}): {e}")
    finally:
        page_obj.close()

    jobs = []
    for api_body in captured:
        if not isinstance(api_body, dict):
            continue
        for job_obj in api_body.get("jobDetails", []):
            if not isinstance(job_obj, dict):
                continue

            title   = job_obj.get("title", "").strip()
            company = job_obj.get("companyName", "").strip()

            # location and experience from placeholders array
            loc = city
            experience = ""
            for ph in job_obj.get("placeholders", []):
                if isinstance(ph, dict):
                    if ph.get("type") == "location":
                        loc = ph.get("label", city)
                    elif ph.get("type") == "experience":
                        experience = ph.get("label", "")

            jd_url = job_obj.get("jdURL", "")
            if jd_url and not jd_url.startswith("http"):
                jd_url = "https://www.naukri.com" + jd_url

            posted_label = job_obj.get("footerPlaceholderLabel", "")
            date_posted  = parse_date_posted(posted_label)

            if title and jd_url:
                jobs.append({
                    "title":       title,
                    "company":     company,
                    "location":    loc,
                    "date_posted": date_posted,
                    "url":         jd_url,
                    "source":      "naukri",
                    "role_search": role,
                    "experience":  experience,
                })
    return jobs

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print("=" * 72)
    print("  NAUKRI DEDICATED SCRAPER")
    print("  Method : Playwright headful + jobapi/v3 interception (FREE)")
    print(f"  Roles  : {len(SEARCH_ROLES)}")
    print(f"  Cities : {len(LOCATIONS)}")
    print(f"  Pages  : {PAGES}")
    print(f"  Start  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)

    cleanup_old_jobs()
    init_playwright()

    progress   = load_progress()
    start_r    = progress.get("role_idx", 0)
    start_l    = progress.get("loc_idx",  0)

    total_combos = len(SEARCH_ROLES) * len(LOCATIONS)
    combo_num    = start_r * len(LOCATIONS) + start_l

    grand_scraped  = 0
    grand_stored   = 0
    hit_time_limit = False

    for r_idx in range(start_r, len(SEARCH_ROLES)):
        role          = SEARCH_ROLES[r_idx]
        start_l_this  = start_l if r_idx == start_r else 0

        for l_idx in range(start_l_this, len(LOCATIONS)):
            city      = LOCATIONS[l_idx]
            combo_num += 1

            # ── Time-limit check ──────────────────────────────────────────
            elapsed = time.time() - START_TIME
            if elapsed >= MAX_RUN_SECONDS:
                print(f"\n[CHECKPOINT] Time limit reached ({elapsed/3600:.2f}h). Saving progress...")
                save_progress(r_idx, l_idx)
                hit_time_limit = True
                break

            save_progress(r_idx, l_idx)

            print(f"\n[{combo_num}/{total_combos}] Role='{role}'  City='{city}'")

            combo_scraped = 0
            combo_stored  = 0

            for page in PAGES:
                print(f"  Page {page}: {naukri_url(role, city, page)}")
                jobs = scrape_naukri_page(role, city, page)
                ins  = store_jobs_batch(jobs)
                combo_scraped += len(jobs)
                combo_stored  += ins
                print(f"    => scraped={len(jobs):>3}  new_stored={ins:>3}")
                time.sleep(2)           # polite delay between pages

            grand_scraped += combo_scraped
            grand_stored  += combo_stored
            print(f"  COMBO TOTAL: scraped={combo_scraped}  new_stored={combo_stored}")
            time.sleep(3)               # polite delay between role/city combos

        if hit_time_limit:
            break

    close_playwright()

    if not hit_time_limit:
        save_progress(0, 0, finished=True)
        print("\nAll combinations finished. Progress reset.")

    # ── Summary report ────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  NAUKRI SCRAPER — FINAL SUMMARY")
    print("=" * 72)
    print(f"  Total jobs scraped  : {grand_scraped:>6}")
    print(f"  New jobs stored (D1): {grand_stored:>6}")
    print(f"  Elapsed time        : {(time.time()-START_TIME)/60:.1f} min")
    print("=" * 72)


if __name__ == "__main__":
    main()
