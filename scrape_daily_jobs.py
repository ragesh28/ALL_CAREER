"""
Scrape 100 software jobs from LinkedIn + Indeed via JobSpy → Store in Turso → Generate HTML page

Usage: py -3.11 scrape_daily_jobs.py
"""

import json
import requests
from datetime import datetime
from jobspy import scrape_jobs

# ---- TURSO CONFIG ----
TURSO_URL = "https://jobsdata-ragesh.aws-ap-south-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE3NzM5MDA3MDAsImlhdCI6MTc3MzI5NTkwMCwiaWQiOiIwMTljZTBhYi0xZDAxLTczMGMtYTBiNS01ZWU0ZGMxZDA4ZDgiLCJyaWQiOiIwY2NlZjMxYy1lMWM3LTQwMzctODA3YS1iMWNkODJmNGQ0YTYifQ.HtmuTZP3oqCa22fOJBPneLQDzmg8G45VXtqpZ0SK4ffxryf371ohb5ir88TXjmgjjGUGwcclBEWt7t81AD0yBg"

RESULTS_WANTED = 100
LOCATION = "India"
HOURS_OLD = 72  # Last 3 days


def turso_execute(statements):
    """Execute SQL via Turso HTTP API."""
    url = f"{TURSO_URL}/v2/pipeline"
    headers = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}
    body = []
    for stmt in statements:
        if isinstance(stmt, str):
            body.append({"type": "execute", "stmt": {"sql": stmt}})
        elif isinstance(stmt, dict):
            body.append({"type": "execute", "stmt": stmt})
    body.append({"type": "close"})
    resp = requests.post(url, headers=headers, json={"requests": body}, timeout=30)
    if resp.status_code != 200:
        print(f"❌ Turso error: {resp.text[:200]}")
        return None
    return resp.json()


def setup_db():
    """Create daily_jobs table."""
    print("📦 Setting up daily_jobs table...")
    turso_execute(["""
        CREATE TABLE IF NOT EXISTS daily_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            date_posted TEXT,
            job_url TEXT NOT NULL,
            direct_url TEXT,
            site TEXT,
            job_type TEXT,
            is_remote TEXT,
            fetched_at TEXT NOT NULL,
            UNIQUE(job_url)
        )
    """])
    print("✅ Table ready!")


def scrape_jobs_data():
    """Scrape 100 software jobs from LinkedIn + Indeed."""
    print(f"\n🔍 Scraping software jobs from LinkedIn + Indeed...")
    print(f"   Location: {LOCATION} | Limit: {RESULTS_WANTED}\n")

    jobs = scrape_jobs(
        site_name=["linkedin", "indeed"],
        search_term="software engineer",
        location=LOCATION,
        results_wanted=RESULTS_WANTED,
        country_indeed="India",
        hours_old=HOURS_OLD,
        linkedin_fetch_description=True,
        verbose=1,
    )

    if jobs.empty:
        print("❌ No jobs found.")
        return []

    print(f"\n📋 Total results: {len(jobs)}")
    jobs = jobs.drop_duplicates(subset=["job_url"], keep="first")
    print(f"📋 After dedup: {len(jobs)}")

    fetched_at = datetime.now().strftime("%Y-%m-%d")
    results = []
    for _, row in jobs.iterrows():
        job_url = str(row.get("job_url", ""))
        if not job_url or job_url == "nan":
            continue

        direct_url = str(row.get("job_url_direct", ""))
        if direct_url in ("nan", "None"):
            direct_url = ""

        results.append({
            "title": str(row.get("title", "Unknown")),
            "company": str(row.get("company", "Unknown")),
            "location": str(row.get("location", "")),
            "date_posted": str(row.get("date_posted", "")),
            "job_url": job_url,
            "direct_url": direct_url,
            "site": str(row.get("site", "")),
            "job_type": str(row.get("job_type", "")),
            "is_remote": str(row.get("is_remote", "")),
            "fetched_at": fetched_at,
        })

    return results[:RESULTS_WANTED]


def store_to_turso(jobs):
    """Store jobs in Turso."""
    if not jobs:
        return 0
    print(f"\n💾 Storing {len(jobs)} jobs in Turso...")
    stmts = []
    for j in jobs:
        stmts.append({
            "sql": """INSERT OR IGNORE INTO daily_jobs
                      (title,company,location,date_posted,job_url,direct_url,site,job_type,is_remote,fetched_at)
                      VALUES (?,?,?,?,?,?,?,?,?,?)""",
            "args": [
                {"type": "text", "value": j["title"]},
                {"type": "text", "value": j["company"]},
                {"type": "text", "value": j["location"]},
                {"type": "text", "value": j["date_posted"]},
                {"type": "text", "value": j["job_url"]},
                {"type": "text", "value": j["direct_url"]},
                {"type": "text", "value": j["site"]},
                {"type": "text", "value": j["job_type"]},
                {"type": "text", "value": j["is_remote"]},
                {"type": "text", "value": j["fetched_at"]},
            ],
        })
    result = turso_execute(stmts)
    if result:
        inserted = sum(
            r.get("response", {}).get("result", {}).get("affected_row_count", 0)
            for r in result.get("results", []) if r.get("type") == "ok"
        )
        print(f"✅ Inserted {inserted} new jobs")
        return inserted
    return 0


def generate_html(jobs, filename="test_results.html"):
    """Generate premium styled HTML page."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    direct_count = sum(1 for j in jobs if j["direct_url"])
    linkedin_count = sum(1 for j in jobs if j["site"] == "linkedin")
    indeed_count = sum(1 for j in jobs if j["site"] == "indeed")

    rows = ""
    for i, job in enumerate(jobs, 1):
        has_direct = bool(job["direct_url"])
        apply_url = job["direct_url"] if has_direct else job["job_url"]
        badge = "Direct ✅" if has_direct else "Apply →"
        badge_cls = "badge-direct" if has_direct else "badge-site"
        btn_cls = "btn-direct" if has_direct else "btn-site"
        btn_txt = "Apply Direct" if has_direct else "View Job"

        site_badge = f'<span class="site-{job["site"]}">{job["site"].title()}</span>'
        date_val = job["date_posted"] if job["date_posted"] not in ("nan", "", "None") else "Recent"

        rows += f"""
        <tr>
            <td class="num">{i}</td>
            <td>
                <div class="job-title">{job["title"]}</div>
                <div class="job-meta">{job["company"]} {site_badge}</div>
            </td>
            <td class="loc">{job["location"][:35]}</td>
            <td class="date">{date_val}</td>
            <td><span class="{badge_cls}">{badge}</span></td>
            <td><a href="{apply_url}" target="_blank" class="{btn_cls}">{btn_txt} →</a></td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Job Drops — Software Engineer Jobs</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', system-ui, sans-serif;
            background: #0a0e1a;
            color: #e2e8f0;
            min-height: 100vh;
        }}
        .hero {{
            background: linear-gradient(135deg, #0f172a 0%, #1a1040 40%, #0f172a 100%);
            padding: 3rem 2rem 2rem;
            text-align: center;
            border-bottom: 1px solid rgba(99, 102, 241, 0.15);
        }}
        .hero h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(90deg, #818cf8, #c084fc, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        .hero p {{ color: #94a3b8; font-size: 0.95rem; }}

        .stats {{
            display: flex; gap: 1rem; justify-content: center;
            margin: 1.5rem 0; flex-wrap: wrap;
        }}
        .stat {{
            background: rgba(30, 27, 75, 0.5);
            border: 1px solid rgba(129, 140, 248, 0.12);
            border-radius: 12px;
            padding: 0.8rem 1.5rem;
            text-align: center;
            backdrop-filter: blur(8px);
            min-width: 120px;
        }}
        .stat .n {{ font-size: 1.8rem; font-weight: 700; color: #818cf8; }}
        .stat .l {{ font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
        .stat.green .n {{ color: #4ade80; }}
        .stat.blue .n {{ color: #38bdf8; }}
        .stat.orange .n {{ color: #fb923c; }}

        .container {{ max-width: 1200px; margin: 0 auto; padding: 1.5rem; }}

        .search-bar {{
            display: flex; gap: 0.5rem; margin-bottom: 1.5rem;
        }}
        .search-bar input {{
            flex: 1; padding: 0.7rem 1rem;
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 10px; color: #e2e8f0;
            font-size: 0.9rem; outline: none;
            transition: border 0.2s;
        }}
        .search-bar input:focus {{ border-color: #818cf8; }}
        .search-bar input::placeholder {{ color: #64748b; }}

        table {{
            width: 100%; border-collapse: collapse;
            background: rgba(15, 23, 42, 0.5);
            border-radius: 12px; overflow: hidden;
            box-shadow: 0 4px 30px rgba(0,0,0,0.3);
        }}
        thead {{ background: rgba(30, 27, 75, 0.6); }}
        th {{
            padding: 0.85rem 1rem; text-align: left;
            font-size: 0.72rem; text-transform: uppercase;
            letter-spacing: 0.6px; color: #818cf8;
            border-bottom: 1px solid rgba(99, 102, 241, 0.1);
        }}
        td {{
            padding: 0.7rem 1rem;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            font-size: 0.88rem;
        }}
        tr {{ transition: background 0.15s; }}
        tr:hover {{ background: rgba(99, 102, 241, 0.06); }}
        .num {{ color: #475569; font-size: 0.8rem; width: 40px; }}
        .loc {{ color: #94a3b8; font-size: 0.82rem; }}
        .date {{ color: #64748b; font-size: 0.82rem; white-space: nowrap; }}

        .job-title {{ font-weight: 600; color: #f1f5f9; font-size: 0.92rem; }}
        .job-meta {{ font-size: 0.78rem; color: #94a3b8; margin-top: 3px; display: flex; align-items: center; gap: 6px; }}

        .site-linkedin {{
            background: rgba(10, 102, 194, 0.2); color: #38bdf8;
            padding: 2px 7px; border-radius: 4px; font-size: 0.68rem; font-weight: 600;
        }}
        .site-indeed {{
            background: rgba(255, 87, 34, 0.15); color: #fb923c;
            padding: 2px 7px; border-radius: 4px; font-size: 0.68rem; font-weight: 600;
        }}

        .badge-direct {{
            background: rgba(74, 222, 128, 0.12); color: #4ade80;
            padding: 3px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; white-space: nowrap;
        }}
        .badge-site {{
            background: rgba(148, 163, 184, 0.1); color: #94a3b8;
            padding: 3px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; white-space: nowrap;
        }}

        .btn-direct, .btn-site {{
            display: inline-block; padding: 6px 14px; border-radius: 8px;
            text-decoration: none; font-size: 0.78rem; font-weight: 600;
            transition: all 0.2s; white-space: nowrap;
        }}
        .btn-direct {{
            background: linear-gradient(135deg, #059669, #10b981); color: white;
        }}
        .btn-direct:hover {{ transform: translateY(-1px); box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35); }}
        .btn-site {{
            background: linear-gradient(135deg, #4338ca, #6366f1); color: white;
        }}
        .btn-site:hover {{ transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35); }}

        .footer {{
            text-align: center; color: #475569; font-size: 0.78rem;
            margin-top: 2rem; padding: 1rem;
        }}

        @media (max-width: 768px) {{
            .hero h1 {{ font-size: 1.5rem; }}
            .loc, .date {{ display: none; }}
            td, th {{ padding: 0.5rem; }}
        }}
    </style>
</head>
<body>
    <div class="hero">
        <h1>🚀 Daily Job Drops</h1>
        <p>Software Engineer Jobs — LinkedIn + Indeed | {now}</p>
        <div class="stats">
            <div class="stat"><div class="n">{len(jobs)}</div><div class="l">Total Jobs</div></div>
            <div class="stat green"><div class="n">{direct_count}</div><div class="l">Direct Apply</div></div>
            <div class="stat blue"><div class="n">{linkedin_count}</div><div class="l">LinkedIn</div></div>
            <div class="stat orange"><div class="n">{indeed_count}</div><div class="l">Indeed</div></div>
        </div>
    </div>

    <div class="container">
        <div class="search-bar">
            <input type="text" id="searchBox" placeholder="🔍 Filter by title, company, or location..." oninput="filterJobs()">
        </div>

        <table>
            <thead>
                <tr>
                    <th>#</th><th>Job</th><th>Location</th><th>Posted</th><th>Type</th><th>Action</th>
                </tr>
            </thead>
            <tbody id="jobsTable">
                {rows}
            </tbody>
        </table>
    </div>

    <div class="footer">
        Powered by JobSpy · Stored in Turso · {len(jobs)} jobs loaded
    </div>

    <script>
        function filterJobs() {{
            const q = document.getElementById('searchBox').value.toLowerCase();
            const rows = document.querySelectorAll('#jobsTable tr');
            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(q) ? '' : 'none';
            }});
        }}
    </script>
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n📄 HTML saved to {filename}")


def main():
    print("=" * 60)
    print("  DAILY JOB DROPS — 100 Software Jobs")
    print("=" * 60)

    setup_db()
    jobs = scrape_jobs_data()

    if not jobs:
        print("❌ No jobs found.")
        return

    store_to_turso(jobs)
    generate_html(jobs)

    print(f"\n📊 Summary:")
    print(f"   Total: {len(jobs)}")
    print(f"   Direct links: {sum(1 for j in jobs if j['direct_url'])}")
    print(f"   LinkedIn: {sum(1 for j in jobs if j['site'] == 'linkedin')}")
    print(f"   Indeed: {sum(1 for j in jobs if j['site'] == 'indeed')}")
    print(f"\n🌐 Open test_results.html in your browser!")


if __name__ == "__main__":
    main()
