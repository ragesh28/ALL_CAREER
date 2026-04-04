"""
Indeed Job Scraper with Permanent Links (Playwright)
Scrapes Indeed India using Playwright, extracts "jk" for permanent URLs,
stores in Turso, and generates test_results.html.

JobSpy gets 403 blocked, so we use Playwright directly (same as Google scraper).

What is "jk"?
  Indeed assigns each job a unique 16-character hex ID called "jk".
  Normal Indeed URLs expire after days.
  https://www.indeed.com/viewjob?jk=<ID> is PERMANENT and never expires.

Usage:
  python scrape_indeed_permanent.py              # Full run (all roles)
  python scrape_indeed_permanent.py --test 5     # Test mode (5 jobs only)
"""

import os
import sys
import re
import json
import time
import random
import requests
import urllib.parse
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TURSO_URL = "https://alljobs-ragesh.aws-ap-south-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzM5MDk4NjQsImlkIjoiMDE5Y2UxNGItMTgwMS03MmQ2LWI0MmMtOGIzYTY0NWExZjE1IiwicmlkIjoiMjgzMDA4YzMtODRhZi00M2MwLWE5ZjItNWY3ZTUwMWZkZDUzIn0.RTp-3zplnbqlpx6qgu_XwxAWOokQIY1TmR9kQtGmC2J1tyRqy5n7LuitSbYdRmD2zBKQEnDLB_Ca4AUm7wt4CQ"

RESULTS_WANTED = 50
KEEP_DAYS = 10

ROLES = [
    "Frontend Developer", "Backend Developer", "Full Stack Developer",
    "Software Engineer", "Data Scientist", "Data Analyst",
    "DevOps Engineer", "Product Manager", "UI UX Designer",
]

LOCATIONS = ["Bangalore", "Chennai", "Hyderabad", "Mumbai"]

# Parse --test flag
TEST_MODE = "--test" in sys.argv
TEST_LIMIT = 5
if TEST_MODE:
    try:
        TEST_LIMIT = int(sys.argv[sys.argv.index("--test") + 1])
    except (IndexError, ValueError):
        TEST_LIMIT = 5

# ---------------------------------------------------------------------------
# TURSO HELPERS
# ---------------------------------------------------------------------------
def turso_execute(statements):
    url = f"{TURSO_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json",
    }
    body = []
    for stmt in statements:
        if isinstance(stmt, str):
            body.append({"type": "execute", "stmt": {"sql": stmt}})
        elif isinstance(stmt, dict):
            body.append({"type": "execute", "stmt": stmt})
    body.append({"type": "close"})
    try:
        resp = requests.post(url, headers=headers, json={"requests": body}, timeout=30)
        if resp.status_code != 200:
            print(f"  ❌ Turso error {resp.status_code}")
            return None
        return resp.json()
    except Exception as e:
        print(f"  ❌ Turso error: {e}")
        return None


def setup_database():
    turso_execute(["""
        CREATE TABLE IF NOT EXISTS all_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, company TEXT NOT NULL,
            location TEXT, date_posted TEXT, url TEXT NOT NULL,
            linkedin_url TEXT, source TEXT, role_search TEXT,
            fetched_at TEXT NOT NULL, indeed_jk TEXT, permanent_url TEXT,
            UNIQUE(url)
        )
    """])
    # Add columns if they don't exist
    turso_execute(["ALTER TABLE all_jobs ADD COLUMN indeed_jk TEXT"])
    turso_execute(["ALTER TABLE all_jobs ADD COLUMN permanent_url TEXT"])


def store_jobs_batch(jobs):
    if not jobs:
        return 0
    total_inserted = 0
    for i in range(0, len(jobs), 50):
        chunk = jobs[i:i+50]
        statements = []
        for job in chunk:
            stmt = {
                "sql": """INSERT OR IGNORE INTO all_jobs
                          (title, company, location, date_posted, url, linkedin_url,
                           source, role_search, fetched_at, indeed_jk, permanent_url)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                "args": [
                    {"type": "text", "value": str(job.get("title", ""))},
                    {"type": "text", "value": str(job.get("company", ""))},
                    {"type": "text", "value": str(job.get("location", ""))},
                    {"type": "text", "value": str(job.get("date", ""))},
                    {"type": "text", "value": str(job.get("url", ""))},
                    {"type": "text", "value": ""},
                    {"type": "text", "value": str(job.get("source", "indeed"))},
                    {"type": "text", "value": str(job.get("role_search", ""))},
                    {"type": "text", "value": str(job.get("fetchedAt", ""))},
                    {"type": "text", "value": str(job.get("indeed_jk", ""))},
                    {"type": "text", "value": str(job.get("permanent_url", ""))},
                ],
            }
            statements.append(stmt)
        result = turso_execute(statements)
        if result:
            for r in result.get("results", []):
                if r.get("type") == "ok":
                    total_inserted += r.get("response", {}).get("result", {}).get("affected_row_count", 0)
    return total_inserted


def get_total_jobs():
    result = turso_execute(["SELECT COUNT(*) FROM all_jobs"])
    if result:
        for r in result.get("results", []):
            if r.get("type") == "ok":
                rows = r.get("response", {}).get("result", {}).get("rows", [])
                if rows:
                    return int(rows[0][0].get("value", 0))
    return 0


# ---------------------------------------------------------------------------
# INDEED PERMANENT LINK HELPER
# ---------------------------------------------------------------------------
def extract_jk(url):
    """
    Extract Indeed's unique job key (jk) from the URL.

    Indeed assigns each job a permanent 16-hex-character ID called "jk".
    Normal scraped Indeed URLs like:
      https://in.indeed.com/rc/clk?jk=abc123...&fccid=...
    Expire after a few days.

    But this permanent URL format ALWAYS works:
      https://www.indeed.com/viewjob?jk=abc123def456&from=serp&vjs=3

    Returns: (jk, permanent_url)
    """
    if not url:
        return None, url
    match = re.search(r'jk=([a-f0-9]{16})', str(url))
    if match:
        jk = match.group(1)
        return jk, f"https://www.indeed.com/viewjob?jk={jk}&from=serp&vjs=3"
    return None, url


# ---------------------------------------------------------------------------
# PLAYWRIGHT INDEED SCRAPER
# ---------------------------------------------------------------------------
def scrape_indeed(role, location, max_results=50):
    """Scrape Indeed India for a specific role + location using Playwright."""
    all_jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )

        def abort_resources(route):
            if route.request.resource_type in ["image", "stylesheet", "font", "media"]:
                route.abort()
            else:
                route.continue_()

        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page.route("**/*", abort_resources)

        fetched_at = datetime.now().strftime("%Y-%m-%d")
        start = 0
        seen = set()

        while len(all_jobs) < max_results:
            # Indeed India URL with pagination
            query = urllib.parse.quote_plus(role)
            loc = urllib.parse.quote_plus(location)
            url = f"https://in.indeed.com/jobs?q={query}&l={loc}&fromage=1&start={start}"

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                break

            page.wait_for_timeout(3000)

            # Check for CAPTCHA
            title = page.title().lower()
            if "security" in title or "captcha" in title or "verify" in title:
                print("🚫 CAPTCHA!", end=" ", flush=True)
                break

            # Get job cards
            cards = page.locator('div.job_seen_beacon, div.jobsearch-ResultsList > div').all()
            if not cards:
                break

            found_new = False
            for card in cards:
                if len(all_jobs) >= max_results:
                    break
                try:
                    # Get title and link
                    title_el = card.locator('h2.jobTitle a, a.jcs-JobTitle')
                    if title_el.count() == 0:
                        continue

                    job_title = title_el.inner_text().strip()
                    href = title_el.get_attribute("href") or ""

                    # Build full URL
                    if href.startswith("/"):
                        href = f"https://in.indeed.com{href}"

                    # Get company
                    comp_el = card.locator('[data-testid="company-name"], span.css-1h7lukg')
                    company = comp_el.inner_text().strip() if comp_el.count() > 0 else ""

                    # Get location
                    loc_el = card.locator('[data-testid="text-location"], div.css-1restlb')
                    job_loc = loc_el.inner_text().strip() if loc_el.count() > 0 else location

                    if not job_title or not company:
                        continue

                    key = f"{job_title.lower()}|{company.lower()}"
                    if key in seen:
                        continue
                    seen.add(key)
                    found_new = True

                    # Extract jk for permanent URL
                    jk, permanent_url = extract_jk(href)

                    # Also try to get jk from data attribute or id
                    if not jk:
                        card_id = card.get_attribute("data-jk") or ""
                        if re.match(r'^[a-f0-9]{16}$', card_id):
                            jk = card_id
                            permanent_url = f"https://www.indeed.com/viewjob?jk={jk}&from=serp&vjs=3"

                    job = {
                        "title": job_title,
                        "company": company,
                        "location": job_loc,
                        "date": "Recent",
                        "url": permanent_url or href,
                        "source": "indeed",
                        "role_search": role,
                        "fetchedAt": fetched_at,
                        "indeed_jk": jk or "",
                        "permanent_url": permanent_url or href,
                    }
                    all_jobs.append(job)

                except Exception:
                    continue

            if not found_new:
                break

            start += 10  # Next page
            time.sleep(random.uniform(1, 3))

        browser.close()

    return all_jobs


# ---------------------------------------------------------------------------
# HTML REPORT
# ---------------------------------------------------------------------------
def generate_html(jobs):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "test_results.html")
    perm_count = sum(1 for j in jobs if j.get("indeed_jk"))

    def card(j):
        perm_badge = ""
        jk_info = ""
        if j.get("indeed_jk"):
            perm_badge = '<span style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;margin-left:6px;">🔗 PERMANENT</span>'
            jk_info = f'<div style="color:#16a34a;font-size:12px;margin-top:4px;">JK: {j["indeed_jk"]}</div>'

        return f"""
        <div style="background:#1e1e2e;border:1px solid #333;border-radius:12px;padding:16px;margin-bottom:12px;
                    transition:transform 0.2s,box-shadow 0.2s;"
             onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 8px 25px rgba(0,0,0,0.3)'"
             onmouseout="this.style.transform='none';this.style.boxShadow='none'">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="background:#2557a7;color:#fff;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:600;">Indeed</span>
                {perm_badge}
            </div>
            <h3 style="margin:0 0 6px;color:#e0e0e0;font-size:16px;">{j['title']}</h3>
            <div style="color:#a0a0a0;font-size:14px;margin-bottom:4px;">🏢 {j['company']}</div>
            <div style="color:#a0a0a0;font-size:13px;margin-bottom:4px;">📍 {j['location']}</div>
            <div style="color:#a0a0a0;font-size:12px;">🔍 Role: {j['role_search']}</div>
            {jk_info}
            <a href="{j.get('permanent_url', j['url'])}" target="_blank"
               style="display:inline-block;margin-top:10px;background:linear-gradient(135deg,#2557a7,#6366f1);
                      color:#fff;padding:8px 20px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;">
                Apply Now →
            </a>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Indeed Jobs — Permanent Links</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:'Inter',sans-serif; background:#0f0f1a; color:#e0e0e0; }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            padding: 40px 20px; text-align: center; border-bottom: 2px solid #2557a7;
        }}
        .header h1 {{ font-size:28px; background:linear-gradient(90deg,#2557a7,#6366f1);
                       -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
        .stats {{ display:flex; justify-content:center; gap:20px; margin-top:20px; flex-wrap:wrap; }}
        .stat {{ background:rgba(255,255,255,0.05); border:1px solid #333; border-radius:12px; padding:12px 24px; }}
        .stat-num {{ font-size:24px; font-weight:700; color:#2557a7; }}
        .stat-label {{ font-size:12px; color:#888; margin-top:4px; }}
        .container {{ max-width:1200px; margin:0 auto; padding:20px; }}
        .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(350px,1fr)); gap:12px; }}
        .info-box {{ background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.3); border-radius:12px; padding:16px; margin-bottom:20px; }}
        .info-box h3 {{ color:#22c55e; margin-bottom:8px; }}
        .info-box code {{ background:#1e1e2e; padding:2px 6px; border-radius:4px; color:#f59e0b; font-size:13px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Indeed Jobs — Permanent Links</h1>
        <p style="color:#a0a0a0;margin-top:8px;">Scraped {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <div class="stats">
            <div class="stat"><div class="stat-num">{len(jobs)}</div><div class="stat-label">Total Jobs</div></div>
            <div class="stat"><div class="stat-num" style="color:#22c55e;">{perm_count}</div><div class="stat-label">Permanent Links</div></div>
        </div>
    </div>
    <div class="container">
        <div class="info-box">
            <h3>🔗 About Permanent Indeed Links</h3>
            <p>Normal Indeed URLs expire after days. This scraper extracts the <code>jk</code> parameter
            (Indeed's permanent 16-hex job ID) and builds URLs like:<br>
            <code>https://www.indeed.com/viewjob?jk=abc123def456</code><br>
            Jobs with green <b>PERMANENT</b> badges have links that never expire!</p>
        </div>
        <div class="grid">{"".join(card(j) for j in jobs)}</div>
    </div>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n📄 HTML report saved: {html_path}")
    return html_path


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  🔍 Indeed Job Scraper — Permanent Links (Playwright)")
    print("=" * 60)
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  🔍 Roles: {len(ROLES)}")
    print(f"  📍 Locations: {len(LOCATIONS)}")
    print(f"  📊 {RESULTS_WANTED} jobs per role+location")
    print(f"  📦 Turso: ✅ configured")
    if TEST_MODE:
        print(f"  🧪 TEST MODE: {TEST_LIMIT} jobs per combo")
    print("=" * 60)

    setup_database()
    print(f"✅ Database ready! Current jobs: {get_total_jobs()}\n")

    all_jobs = []
    total_stored = 0

    for role in ROLES:
        for location in LOCATIONS:
            limit = TEST_LIMIT if TEST_MODE else RESULTS_WANTED
            print(f"🔍 '{role}' in {location}...", end=" ", flush=True)

            jobs = scrape_indeed(role, location, limit)
            perm = sum(1 for j in jobs if j.get("indeed_jk"))
            stored = store_jobs_batch(jobs)
            total_stored += stored
            all_jobs.extend(jobs)

            print(f"✅ {len(jobs)} found ({perm} permanent), {stored} new → Turso")

            # Print permanent links
            for j in jobs:
                if j.get("indeed_jk"):
                    print(f"    📎 {j['title']} @ {j['company']}")
                    print(f"       🔗 {j['permanent_url']}")
                    print(f"       JK: {j['indeed_jk']}")

            time.sleep(2)

            if TEST_MODE:
                break
        if TEST_MODE and len(all_jobs) >= TEST_LIMIT:
            break

    # Summary
    total_db = get_total_jobs()
    perm_total = sum(1 for j in all_jobs if j.get("indeed_jk"))
    print(f"\n{'='*60}")
    print(f"  ✅ DONE!")
    print(f"     📦 Found: {len(all_jobs)} jobs")
    print(f"     🔗 Permanent links: {perm_total}")
    print(f"     🆕 New in Turso: {total_stored}")
    print(f"     📊 Total in DB: {total_db}")
    print(f"{'='*60}")

    if all_jobs:
        generate_html(all_jobs)
