"""
ALL JOBS Aggregator Scraper via JobSpy → Turso + JS file
Scrapes ALL portals (LinkedIn, Indeed, Google, Glassdoor, ZipRecruiter)
for jobs across ALL tech & non-tech roles.
Stores in Turso database AND generates all_jobs_data.js for GitHub Pages.

Priority: LinkedIn > Google > Indeed > Glassdoor > ZipRecruiter.

Usage (local):   py -3.11 scrape_google_jobs.py --test 3
Usage (GitHub):  python scrape_google_jobs.py
"""

import os
import sys
import json
import time
import requests
import traceback
import urllib.parse
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TURSO_URL = os.environ.get("TURSO_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "")

MAX_JOBS = 500              # Per run cap
RESULTS_PER_SEARCH = 10    # Per role+location combo
KEEP_DAYS = 10              # Delete jobs older than 10 days
COOLDOWN_SECONDS = 60       # Wait on block
MAX_RETRIES = 3

START_TIME = time.time()
MAX_RUN_SECONDS = 5 * 3600 + 50 * 60  # 5h50m safe margin

# ---------------------------------------------------------------------------
# ROLES — All Tech + Non-Tech
# ---------------------------------------------------------------------------
SEARCH_ROLES = [
    # --- Software Development & Engineering ---
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Mobile App Developer",
    "Software Architect",
    "Software Engineer",

    # --- AI & Data Science ---
    "AI Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",

    # --- Cloud, Infrastructure & DevOps ---
    "DevOps Engineer",
    "Cloud Architect",
    "Systems Administrator",
    "Database Administrator",

    # --- Cybersecurity & Networking ---
    "Security Analyst",
    "Penetration Tester",
    "Network Engineer",

    # --- QA & Testing ---
    "QA Analyst",
    "SDET",

    # --- Product & Project Management ---
    "Product Manager",
    "Project Manager",
    "Scrum Master",

    # --- Design & UX ---
    "UI UX Designer",
    "UX Researcher",
    "Technical Writer",

    # --- Sales & Marketing ---
    "Sales Executive",
    "Pre-Sales Consultant",
    "Digital Marketer",
    "Product Marketing Manager",

    # --- HR & Talent ---
    "Technical Recruiter",
    "HR Business Partner",

    # --- Customer Success & Support ---
    "Customer Success Manager",
    "IT Support Specialist",

    # --- Operations & Finance ---
    "Operations Manager",
    "Financial Analyst",
    "Legal Counsel",
]

LOCATIONS = [
    "Bangalore, India",
    "Chennai, India",
    "Hyderabad, India",
    "Mumbai, India",
]


# ---------------------------------------------------------------------------
# TURSO HELPERS
# ---------------------------------------------------------------------------
def turso_execute(statements):
    """Execute SQL statements via Turso HTTP API."""
    if not TURSO_URL or not TURSO_TOKEN:
        print("⚠️ TURSO not configured, skipping DB storage")
        return None

    url = f"{TURSO_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json",
    }

    requests_body = []
    for stmt in statements:
        if isinstance(stmt, str):
            requests_body.append({"type": "execute", "stmt": {"sql": stmt}})
        elif isinstance(stmt, dict):
            requests_body.append({"type": "execute", "stmt": stmt})
    requests_body.append({"type": "close"})

    try:
        resp = requests.post(url, headers=headers, json={"requests": requests_body}, timeout=30)
        if resp.status_code != 200:
            print(f"❌ Turso API error {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()
    except Exception as e:
        print(f"❌ Turso connection error: {e}")
        return None


def setup_database():
    """Create all_jobs table if not exists."""
    print("📦 Setting up Turso database (all_jobs table)...")
    sql = """
    CREATE TABLE IF NOT EXISTS all_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT,
        date_posted TEXT,
        url TEXT NOT NULL,
        linkedin_url TEXT,
        source TEXT,
        role_search TEXT,
        fetched_at TEXT NOT NULL,
        UNIQUE(url)
    )
    """
    result = turso_execute([sql])
    if result:
        print("✅ Database ready!")
    return result is not None


def store_jobs_batch(jobs):
    """Store a batch of jobs in Turso. Returns count inserted."""
    if not jobs or not TURSO_URL:
        return 0

    # Send in chunks of 50 to avoid payload limits
    total_inserted = 0
    for i in range(0, len(jobs), 50):
        chunk = jobs[i:i + 50]
        statements = []
        for job in chunk:
            stmt = {
                "sql": """INSERT OR IGNORE INTO all_jobs
                          (title, company, location, date_posted, url, linkedin_url, source, role_search, fetched_at)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                "args": [
                    {"type": "text", "value": str(job.get("title", ""))},
                    {"type": "text", "value": str(job.get("company", ""))},
                    {"type": "text", "value": str(job.get("location", ""))},
                    {"type": "text", "value": str(job.get("date", ""))},
                    {"type": "text", "value": str(job.get("url", ""))},
                    {"type": "text", "value": str(job.get("linkedin_url", ""))},
                    {"type": "text", "value": str(job.get("source", ""))},
                    {"type": "text", "value": str(job.get("role_search", ""))},
                    {"type": "text", "value": str(job.get("fetchedAt", ""))},
                ],
            }
            statements.append(stmt)

        result = turso_execute(statements)
        if result:
            for r in result.get("results", []):
                if r.get("type") == "ok":
                    total_inserted += r.get("response", {}).get("result", {}).get("affected_row_count", 0)

    return total_inserted


def cleanup_old_jobs():
    """Delete jobs older than KEEP_DAYS days."""
    if not TURSO_URL:
        return 0
    cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    print(f"🧹 Cleaning jobs older than {cutoff}...")
    result = turso_execute([{
        "sql": "DELETE FROM all_jobs WHERE fetched_at < ?",
        "args": [{"type": "text", "value": cutoff}]
    }])
    if result:
        for r in result.get("results", []):
            if r.get("type") == "ok":
                deleted = r.get("response", {}).get("result", {}).get("affected_row_count", 0)
                print(f"🗑️ Removed {deleted} old jobs")
                return deleted
    return 0


def fetch_all_from_turso():
    """Fetch all jobs from Turso for JS file generation."""
    if not TURSO_URL:
        return []

    result = turso_execute(["SELECT title, company, location, date_posted, url, linkedin_url, source, role_search, fetched_at FROM all_jobs ORDER BY fetched_at DESC"])
    if not result:
        return []

    jobs = []
    for r in result.get("results", []):
        if r.get("type") == "ok":
            cols = [c.get("name", "") for c in r.get("response", {}).get("result", {}).get("cols", [])]
            for row in r.get("response", {}).get("result", {}).get("rows", []):
                job = {}
                for ci, col_name in enumerate(cols):
                    val = row[ci].get("value", "") if ci < len(row) else ""
                    job[col_name] = val
                # Map to JS-compatible keys
                jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", ""),
                    "date": job.get("date_posted", ""),
                    "url": job.get("url", ""),
                    "linkedin_url": job.get("linkedin_url", ""),
                    "source": job.get("source", ""),
                    "role_search": job.get("role_search", ""),
                    "fetchedAt": job.get("fetched_at", ""),
                })
    return jobs


def get_total_jobs():
    """Get total job count from Turso."""
    if not TURSO_URL:
        return 0
    result = turso_execute(["SELECT COUNT(*) FROM all_jobs"])
    if result:
        for r in result.get("results", []):
            if r.get("type") == "ok":
                rows = r.get("response", {}).get("result", {}).get("rows", [])
                if rows:
                    return int(rows[0][0].get("value", 0))
    return 0


# ---------------------------------------------------------------------------
# SCRAPE
# ---------------------------------------------------------------------------
def is_blocked(error):
    err = str(error).lower()
    return any(x in err for x in ["429", "blocked", "rate limit", "timeout", "captcha", "forbidden"])

def scrape_all_jobs(test_limit=None):
    roles = SEARCH_ROLES
    if test_limit:
        roles = roles[:test_limit]
        print(f"\n🧪 TEST MODE: {test_limit} roles only\n")

    all_jobs = []
    seen_keys = set()
    fetched_at = datetime.now().strftime("%Y-%m-%d")
    total_combos = len(roles) * len(LOCATIONS)
    combo_num = 0
    total_stored = 0

    with sync_playwright() as p:
        # Launching Chromium with automation bypass flags
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        # Stealth bypass for navigator.webdriver
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        for role in roles:
            for location in LOCATIONS:
                combo_num += 1

                # Time limit check
                if time.time() - START_TIME >= MAX_RUN_SECONDS:
                    print(f"\n⏰ TIME LIMIT. Saving and stopping.")
                    break

                print(f"[{combo_num}/{total_combos}] 🔍 '{role}' in {location.split(',')[0]}...", end=" ", flush=True)

                encoded_query = urllib.parse.quote_plus(f"{role} jobs in {location}")
                job_url = f"https://www.google.com/search?q={encoded_query}&ibp=htl;jobs#htivrt=jobs&htichips=date_posted:today&fpstate=tldetail"

                retries = 0
                success = False
                while retries <= MAX_RETRIES and not success:
                    try:
                        page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(3000)
                        
                        try:
                            # Wait for job container
                            page.wait_for_selector('a.MQUd2b', timeout=10000)
                        except Exception:
                            # Usually means 0 jobs found
                            print("0 jobs found")
                            success = True
                            break
                            
                        # Scroll to load a few more
                        page.mouse.move(300, 500)
                        for _ in range(3):
                            page.mouse.wheel(0, 1500)
                            page.wait_for_timeout(1000)
                            
                        list_items = page.locator('a.MQUd2b').all()
                        
                        batch = []
                        count = 0
                        
                        for card in list_items:
                            if count >= RESULTS_PER_SEARCH:
                                break
                                
                            try:
                                title_loc = card.locator('.tNxQIb')
                                title = title_loc.inner_text().strip() if title_loc.count() > 0 else ""
                                
                                comp_locs = card.locator('.wHYlTd').all()
                                company = comp_locs[0].inner_text().strip() if len(comp_locs) > 0 else ""
                                
                                loc_via = comp_locs[1].inner_text().strip() if len(comp_locs) > 1 else ""
                                loc_clean = loc_via.split('•')[0].strip() if '•' in loc_via else loc_via
                                site = "google"
                                if 'via' in loc_via:
                                    site = loc_via.split('via')[-1].strip().lower()
                                    
                                if not title or not company:
                                    continue
                                    
                                key = f"{title.lower().strip()}|{company.lower().strip()}"
                                if key in seen_keys:
                                    continue
                                seen_keys.add(key)
                                
                                # Fetch direct URL from right pane by clicking
                                card.click(force=True)
                                page.wait_for_timeout(1000)
                                
                                direct_url = ""
                                apply_links = page.locator('.yVRmze-s2gQvd a').all()
                                if apply_links:
                                    direct_url = apply_links[0].get_attribute('href')
                                if not direct_url:
                                    direct_url = card.get_attribute('href')
                                    
                                batch.append({
                                    "title": title,
                                    "company": company,
                                    "location": loc_clean,
                                    "url": direct_url or "#",
                                    "linkedin_url": "",
                                    "date": "Recent",
                                    "source": site,
                                    "role_search": role,
                                    "fetchedAt": fetched_at,
                                })
                                count += 1
                                
                            except Exception:
                                continue
                                
                        all_jobs.extend(batch)

                        # Store batch in Turso
                        if batch and TURSO_URL:
                            inserted = store_jobs_batch(batch)
                            total_stored += inserted

                        print(f"✅ {len(batch)} new (total: {len(all_jobs)}, stored: {total_stored})")
                        success = True

                    except Exception as e:
                        retries += 1
                        if retries <= MAX_RETRIES:
                            print(f"🚫 Error: {e}. Retrying {retries}/{MAX_RETRIES}...")
                            time.sleep(COOLDOWN_SECONDS)
                        else:
                            print(f"❌ Max retries. Skipping.")
                if len(all_jobs) >= MAX_JOBS or (time.time() - START_TIME >= MAX_RUN_SECONDS):
                    break
            if len(all_jobs) >= MAX_JOBS or (time.time() - START_TIME >= MAX_RUN_SECONDS):
                break

    return all_jobs, total_stored

# ---------------------------------------------------------------------------
# JS FILE GENERATION
# ---------------------------------------------------------------------------
def generate_js_file(jobs):
    """Generate all_jobs_data.js from jobs list."""
    js = f"const allJobsData = {json.dumps(jobs, indent=2, ensure_ascii=False)};"
    with open("all_jobs_data.js", "w", encoding="utf-8") as f:
        f.write(js)
    print(f"✅ all_jobs_data.js ({len(jobs)} jobs)")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  ALL JOBS AGGREGATOR (All Portals → Turso)")
    print("=" * 60)
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  🔍 Roles: {len(SEARCH_ROLES)}")
    print(f"  📍 Locations: {len(LOCATIONS)}")
    print(f"  📊 {RESULTS_PER_SEARCH}/combo, max {MAX_JOBS}")
    print(f"  🌐 Sources: LinkedIn, Indeed, Google, Glassdoor, ZipRecruiter")
    print(f"  📦 Turso: {'✅ configured' if TURSO_URL else '❌ not configured (local only)'}")
    print(f"  📆 Retention: {KEEP_DAYS} days")
    print("=" * 60)

    # Local testing fallback
    if not TURSO_URL:
        TURSO_URL = "https://jobsdata-ragesh.aws-ap-south-1.turso.io"
    if not TURSO_TOKEN:
        TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE3NzM5MDA3MDAsImlhdCI6MTc3MzI5NTkwMCwiaWQiOiIwMTljZTBhYi0xZDAxLTczMGMtYTBiNS01ZWU0ZGMxZDA4ZDgiLCJyaWQiOiIwY2NlZjMxYy1lMWM3LTQwMzctODA3YS1iMWNkODJmNGQ0YTYifQ.HtmuTZP3oqCa22fOJBPneLQDzmg8G45VXtqpZ0SK4ffxryf371ohb5ir88TXjmgjjGUGwcclBEWt7t81AD0yBg"

    test_count = None
    if "--test" in sys.argv:
        try:
            idx = sys.argv.index("--test")
            test_count = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            test_count = 3

    try:
        # Setup DB
        if TURSO_URL:
            setup_database()
            cleanup_old_jobs()
            print(f"📊 Current jobs in Turso: {get_total_jobs()}")

        # Scrape
        jobs, stored = scrape_all_jobs(test_limit=test_count)
        print(f"\n📊 Scraped: {len(jobs)} unique jobs, Stored: {stored} new in Turso")

        # Fetch ALL jobs from Turso (including previous days) for JS file
        if TURSO_URL:
            all_turso_jobs = fetch_all_from_turso()
            print(f"📦 Total in Turso: {len(all_turso_jobs)} jobs")
            generate_js_file(all_turso_jobs)
        else:
            generate_js_file(jobs)

        # Also save JSON
        with open("google_jobs.json", "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)

        final = get_total_jobs() if TURSO_URL else len(jobs)
        print(f"\n{'=' * 60}")
        print(f"  📊 RESULTS:")
        print(f"     🆕 New jobs scraped: {len(jobs)}")
        print(f"     💾 Stored in Turso: {stored}")
        print(f"     📦 Total in DB: {final}")
        print(f"{'=' * 60}")
        print(f"\n✅ DONE!")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
