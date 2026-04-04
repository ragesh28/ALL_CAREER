"""
LinkedIn + Indeed Job Scraper with Permanent Indeed Links
Uses JobSpy to scrape jobs, extracts Indeed's "jk" parameter for permanent URLs,
stores in Turso, and generates a beautiful test_results.html page.

What is "jk"?
  Indeed assigns each job a unique 16-character hex ID called "jk".
  Normal Indeed URLs often expire or redirect after a few days.
  But https://www.indeed.com/viewjob?jk=<ID>&from=serp&vjs=3 is PERMANENT.
  This script extracts that ID and builds permanent links.

Usage:
  python scrape_jobs_with_permanent_indeed.py
  python scrape_jobs_with_permanent_indeed.py --test 5   # Only 5 jobs per site
"""

import os
import sys
import re
import json
import time
import requests
from datetime import datetime, timedelta
from jobspy import scrape_jobs

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TURSO_URL = "https://alljobs-ragesh.aws-ap-south-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzM5MDk4NjQsImlkIjoiMDE5Y2UxNGItMTgwMS03MmQ2LWI0MmMtOGIzYTY0NWExZjE1IiwicmlkIjoiMjgzMDA4YzMtODRhZi00M2MwLWE5ZjItNWY3ZTUwMWZkZDUzIn0.RTp-3zplnbqlpx6qgu_XwxAWOokQIY1TmR9kQtGmC2J1tyRqy5n7LuitSbYdRmD2zBKQEnDLB_Ca4AUm7wt4CQ"

ROLES = [
    "Frontend Developer", "Backend Developer", "Full Stack Developer",
    "Software Engineer", "Data Scientist", "Data Analyst",
    "DevOps Engineer", "Product Manager", "UI UX Designer",
]

LOCATIONS = ["Bangalore, India", "Chennai, India", "Hyderabad, India", "Mumbai, India"]

RESULTS_PER_SITE = 50  # 50 from LinkedIn + 50 from Indeed
KEEP_DAYS = 10

# Parse --test flag
TEST_MODE = False
TEST_LIMIT = 50
if "--test" in sys.argv:
    TEST_MODE = True
    try:
        TEST_LIMIT = int(sys.argv[sys.argv.index("--test") + 1])
    except (IndexError, ValueError):
        TEST_LIMIT = 5
    RESULTS_PER_SITE = TEST_LIMIT

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
            print(f"❌ Turso error {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()
    except Exception as e:
        print(f"❌ Turso connection error: {e}")
        return None


def setup_database():
    """Create the jobs table with indeed_jk and permanent_url columns."""
    print("📦 Setting up Turso database...")

    # Create main table if not exists
    turso_execute(["""
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
            indeed_jk TEXT,
            permanent_url TEXT,
            UNIQUE(url)
        )
    """])

    # Add columns if they don't exist (for existing tables)
    try:
        turso_execute(["ALTER TABLE all_jobs ADD COLUMN indeed_jk TEXT"])
    except Exception:
        pass
    try:
        turso_execute(["ALTER TABLE all_jobs ADD COLUMN permanent_url TEXT"])
    except Exception:
        pass

    print("✅ Database ready!")


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
def extract_indeed_jk(job_url):
    """
    Extract Indeed's unique job key (jk) from the URL.

    Indeed assigns each job posting a unique 16-character hex ID called "jk".
    This ID remains valid even after the original scraped URL expires.

    Normal scraped URLs like:
      https://www.indeed.com/rc/clk?jk=abc123...&fccid=...
    Often disappear after a few days.

    But this permanent URL format ALWAYS works:
      https://www.indeed.com/viewjob?jk=abc123def456&from=serp&vjs=3

    Returns: (jk, permanent_url) tuple
    """
    if not job_url:
        return None, job_url

    # Try to extract jk from URL (16 hex characters)
    jk_match = re.search(r'jk=([a-f0-9]{16})', str(job_url))
    if jk_match:
        jk = jk_match.group(1)
        permanent_url = f"https://www.indeed.com/viewjob?jk={jk}&from=serp&vjs=3"
        return jk, permanent_url

    return None, job_url  # Fallback: use original URL


# ---------------------------------------------------------------------------
# SCRAPER
# ---------------------------------------------------------------------------
def scrape_and_store():
    """Scrape LinkedIn + Indeed using JobSpy, store in Turso."""
    fetched_at = datetime.now().strftime("%Y-%m-%d")
    all_jobs = []
    total_stored = 0

    for role in ROLES:
        for location in LOCATIONS:
            city = location.split(",")[0]
            print(f"\n🔍 '{role}' in {city}...", end=" ", flush=True)

            try:
                # Scrape from both LinkedIn and Indeed
                try:
                    jobs_df = scrape_jobs(
                        site_name=["indeed", "linkedin"],
                        search_term=role,
                        location=location,
                        results_wanted=RESULTS_PER_SITE,
                        hours_old=24,
                        country_indeed="India",
                    )
                except TypeError:
                    # Older jobspy versions don't support hours_old
                    jobs_df = scrape_jobs(
                        site_name=["indeed", "linkedin"],
                        search_term=role,
                        location=location,
                        results_wanted=RESULTS_PER_SITE,
                        country_indeed="India",
                    )

                if jobs_df is None or jobs_df.empty:
                    print("0 jobs found")
                    continue

                batch_statements = []
                batch_jobs = []

                for _, row in jobs_df.iterrows():
                    title = str(row.get("title", "")).strip()
                    company = str(row.get("company", "")).strip()
                    loc = str(row.get("location", "")).strip()
                    date_posted = str(row.get("date_posted", "")).strip()
                    job_url = str(row.get("job_url", "")).strip()
                    site = str(row.get("site", "")).strip().lower()

                    if not title or not company or title == "nan":
                        continue

                    # Extract Indeed permanent link
                    indeed_jk = None
                    permanent_url = job_url

                    if "indeed" in site:
                        indeed_jk, permanent_url = extract_indeed_jk(job_url)

                    # For LinkedIn, keep original URL
                    linkedin_url = job_url if "linkedin" in site else ""

                    # Use permanent_url as the stored URL for Indeed
                    final_url = permanent_url if permanent_url else job_url

                    job_data = {
                        "title": title,
                        "company": company,
                        "location": loc,
                        "date": date_posted,
                        "url": final_url,
                        "linkedin_url": linkedin_url,
                        "source": site,
                        "role_search": role,
                        "fetchedAt": fetched_at,
                        "indeed_jk": indeed_jk or "",
                        "permanent_url": permanent_url or "",
                    }

                    batch_jobs.append(job_data)

                    stmt = {
                        "sql": """INSERT OR IGNORE INTO all_jobs
                                  (title, company, location, date_posted, url, linkedin_url,
                                   source, role_search, fetched_at, indeed_jk, permanent_url)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        "args": [
                            {"type": "text", "value": title},
                            {"type": "text", "value": company},
                            {"type": "text", "value": loc if loc != "nan" else ""},
                            {"type": "text", "value": date_posted if date_posted != "nan" else ""},
                            {"type": "text", "value": final_url},
                            {"type": "text", "value": linkedin_url},
                            {"type": "text", "value": site},
                            {"type": "text", "value": role},
                            {"type": "text", "value": fetched_at},
                            {"type": "text", "value": indeed_jk or ""},
                            {"type": "text", "value": permanent_url or ""},
                        ],
                    }
                    batch_statements.append(stmt)

                # Store batch
                stored = 0
                if batch_statements:
                    for i in range(0, len(batch_statements), 50):
                        chunk = batch_statements[i:i+50]
                        result = turso_execute(chunk)
                        if result:
                            for r in result.get("results", []):
                                if r.get("type") == "ok":
                                    stored += r.get("response", {}).get("result", {}).get("affected_row_count", 0)

                total_stored += stored
                all_jobs.extend(batch_jobs)

                linkedin_count = sum(1 for j in batch_jobs if "linkedin" in j["source"])
                indeed_count = sum(1 for j in batch_jobs if "indeed" in j["source"])
                indeed_perm = sum(1 for j in batch_jobs if j.get("indeed_jk"))

                print(f"✅ {len(batch_jobs)} found (LI: {linkedin_count}, Indeed: {indeed_count}, perm links: {indeed_perm}), {stored} new → Turso")

                # Print Indeed permanent links
                for j in batch_jobs:
                    if j.get("indeed_jk"):
                        print(f"    📎 {j['title']} @ {j['company']}")
                        print(f"       Permanent: {j['permanent_url']}")
                        print(f"       JK ID: {j['indeed_jk']}")

            except Exception as e:
                print(f"❌ Error: {e}")

            time.sleep(2)  # Rate limit

            if TEST_MODE:
                break  # Only first location in test mode
        if TEST_MODE and len(all_jobs) >= TEST_LIMIT:
            break

    return all_jobs, total_stored


# ---------------------------------------------------------------------------
# HTML REPORT GENERATOR
# ---------------------------------------------------------------------------
def generate_html(jobs):
    """Generate a beautiful test_results.html page."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "test_results.html")

    linkedin_jobs = [j for j in jobs if "linkedin" in j.get("source", "")]
    indeed_jobs = [j for j in jobs if "indeed" in j.get("source", "")]
    indeed_perm = [j for j in indeed_jobs if j.get("indeed_jk")]

    def job_card(job):
        source = job.get("source", "unknown")
        is_indeed = "indeed" in source
        badge_color = "#0A66C2" if "linkedin" in source else "#2557a7" if is_indeed else "#4CAF50"
        badge_text = "LinkedIn" if "linkedin" in source else "Indeed" if is_indeed else source.capitalize()

        perm_badge = ""
        if job.get("indeed_jk"):
            perm_badge = '<span style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;margin-left:6px;">🔗 PERMANENT</span>'

        jk_info = ""
        if job.get("indeed_jk"):
            jk_info = f'<div style="color:#16a34a;font-size:12px;margin-top:4px;">JK: {job["indeed_jk"]}</div>'

        return f"""
        <div style="background:#1e1e2e;border:1px solid #333;border-radius:12px;padding:16px;margin-bottom:12px;
                    transition:transform 0.2s,box-shadow 0.2s;cursor:pointer;"
             onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 8px 25px rgba(0,0,0,0.3)'"
             onmouseout="this.style.transform='none';this.style.boxShadow='none'">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="background:{badge_color};color:#fff;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:600;">
                    {badge_text}
                </span>
                {perm_badge}
                <span style="color:#888;font-size:12px;">{job.get('date', '')}</span>
            </div>
            <h3 style="margin:0 0 6px;color:#e0e0e0;font-size:16px;">{job.get('title', 'N/A')}</h3>
            <div style="color:#a0a0a0;font-size:14px;margin-bottom:4px;">🏢 {job.get('company', 'N/A')}</div>
            <div style="color:#a0a0a0;font-size:13px;margin-bottom:8px;">📍 {job.get('location', 'N/A')}</div>
            {jk_info}
            <a href="{job.get('permanent_url', '') or job.get('url', '#')}" target="_blank"
               style="display:inline-block;margin-top:8px;background:linear-gradient(135deg,{badge_color},#6366f1);
                      color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;">
                Apply Now →
            </a>
        </div>"""

    linkedin_cards = "".join(job_card(j) for j in linkedin_jobs[:50])
    indeed_cards = "".join(job_card(j) for j in indeed_jobs[:50])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Scraper Results — LinkedIn + Indeed</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:'Inter',sans-serif; background:#0f0f1a; color:#e0e0e0; }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            padding: 40px 20px;
            text-align: center;
            border-bottom: 2px solid #6366f1;
        }}
        .header h1 {{ font-size:28px; background:linear-gradient(90deg,#6366f1,#ec4899);
                       -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
        .stats {{
            display:flex; justify-content:center; gap:20px; margin-top:20px; flex-wrap:wrap;
        }}
        .stat {{
            background:rgba(255,255,255,0.05); border:1px solid #333; border-radius:12px;
            padding:12px 24px; min-width:120px;
        }}
        .stat-num {{ font-size:24px; font-weight:700; color:#6366f1; }}
        .stat-label {{ font-size:12px; color:#888; margin-top:4px; }}
        .container {{ max-width:1200px; margin:0 auto; padding:20px; }}
        .tabs {{
            display:flex; gap:10px; margin-bottom:20px;
        }}
        .tab {{
            padding:10px 24px; border-radius:8px; cursor:pointer; font-weight:600; font-size:14px;
            border:1px solid #333; background:#1e1e2e; color:#a0a0a0; transition:all 0.3s;
        }}
        .tab.active {{ background:linear-gradient(135deg,#6366f1,#8b5cf6); color:#fff; border-color:#6366f1; }}
        .tab-content {{ display:none; }}
        .tab-content.active {{ display:block; }}
        .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(350px,1fr)); gap:12px; }}
        .info-box {{
            background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.3); border-radius:12px;
            padding:16px; margin-bottom:20px;
        }}
        .info-box h3 {{ color:#22c55e; margin-bottom:8px; }}
        .info-box code {{ background:#1e1e2e; padding:2px 6px; border-radius:4px; color:#f59e0b; font-size:13px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Job Scraper Results</h1>
        <p style="color:#a0a0a0;margin-top:8px;">LinkedIn + Indeed • Scraped {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <div class="stats">
            <div class="stat"><div class="stat-num">{len(jobs)}</div><div class="stat-label">Total Jobs</div></div>
            <div class="stat"><div class="stat-num" style="color:#0A66C2;">{len(linkedin_jobs)}</div><div class="stat-label">LinkedIn</div></div>
            <div class="stat"><div class="stat-num" style="color:#2557a7;">{len(indeed_jobs)}</div><div class="stat-label">Indeed</div></div>
            <div class="stat"><div class="stat-num" style="color:#22c55e;">{len(indeed_perm)}</div><div class="stat-label">Permanent Links</div></div>
        </div>
    </div>

    <div class="container">
        <div class="info-box">
            <h3>🔗 About Permanent Indeed Links</h3>
            <p>Normal Indeed URLs expire after a few days. This scraper extracts the <code>jk</code> parameter
            (Indeed's unique 16-hex-char job ID) and builds permanent URLs like:<br>
            <code>https://www.indeed.com/viewjob?jk=abc123def456&from=serp&vjs=3</code><br>
            Jobs with green <b>PERMANENT</b> badges have reliable links that won't expire!</p>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="showTab('all')">All ({len(jobs)})</div>
            <div class="tab" onclick="showTab('linkedin')" style="border-color:#0A66C2;">LinkedIn ({len(linkedin_jobs)})</div>
            <div class="tab" onclick="showTab('indeed')" style="border-color:#2557a7;">Indeed ({len(indeed_jobs)})</div>
        </div>

        <div id="tab-all" class="tab-content active">
            <div class="grid">{"".join(job_card(j) for j in jobs[:100])}</div>
        </div>
        <div id="tab-linkedin" class="tab-content">
            <div class="grid">{linkedin_cards or '<p style="color:#888;">No LinkedIn jobs found</p>'}</div>
        </div>
        <div id="tab-indeed" class="tab-content">
            <div class="grid">{indeed_cards or '<p style="color:#888;">No Indeed jobs found</p>'}</div>
        </div>
    </div>

    <script>
        function showTab(name) {{
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + name).classList.add('active');
            event.target.classList.add('active');
        }}
    </script>
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
    print("  🔍 LinkedIn + Indeed Job Scraper")
    print("  📎 With Permanent Indeed Links (jk parameter)")
    print("=" * 60)
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  🔍 Roles: {len(ROLES)}")
    print(f"  📍 Locations: {len(LOCATIONS)}")
    print(f"  📊 {RESULTS_PER_SITE} jobs per site per combo")
    print(f"  🌐 Sources: LinkedIn, Indeed")
    print(f"  📦 Turso: ✅ configured")
    if TEST_MODE:
        print(f"  🧪 TEST MODE: {TEST_LIMIT} results")
    print("=" * 60)

    setup_database()
    print(f"📊 Current jobs in Turso: {get_total_jobs()}")

    jobs, stored = scrape_and_store()

    total_db = get_total_jobs()
    print(f"\n{'='*60}")
    print(f"  ✅ SCRAPING COMPLETE!")
    print(f"     📦 Found: {len(jobs)} jobs")
    print(f"     🆕 New stored: {stored}")
    print(f"     📊 Total in Turso: {total_db}")

    linkedin_count = sum(1 for j in jobs if "linkedin" in j.get("source", ""))
    indeed_count = sum(1 for j in jobs if "indeed" in j.get("source", ""))
    perm_count = sum(1 for j in jobs if j.get("indeed_jk"))
    print(f"     🔵 LinkedIn: {linkedin_count}")
    print(f"     🔷 Indeed: {indeed_count} ({perm_count} with permanent links)")
    print(f"{'='*60}")

    # Generate HTML report
    if jobs:
        html_path = generate_html(jobs)
        print(f"\n🌐 Open this file to see results:\n   {html_path}")
    else:
        print("\n⚠️ No jobs found. Try again later.")
