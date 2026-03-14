import os
import json
import time
import urllib.parse
from playwright.sync_api import sync_playwright
import requests

# Set Turso Details
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "https://jobsdata-ragesh.aws-ap-south-1.turso.io")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE3NzM5MDA3MDAsImlhdCI6MTc3MzI5NTkwMCwiaWQiOiIwMTljZTBhYi0xZDAxLTczMGMtYTBiNS01ZWU0ZGMxZDA4ZDgiLCJyaWQiOiIwY2NlZjMxYy1lMWM3LTQwMzctODA3YS1iMWNkODJmNGQ0YTYifQ.HtmuTZP3oqCa22fOJBPneLQDzmg8G45VXtqpZ0SK4ffxryf371ohb5ir88TXjmgjjGUGwcclBEWt7t81AD0yBg")

def turso_execute(sql, args=None):
    url = f"{TURSO_DATABASE_URL}/v2/pipeline"
    headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}", "Content-Type": "application/json"}
    stmt = {"sql": sql}
    if args: stmt["args"] = args
    body = {"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]}
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        out = resp.json()
        if resp.status_code != 200 or "error" in str(out):
            print(f"❌ TURSO EXECUTE FAIL: {resp.text}")
        return out
    except Exception as e:
        print(f"❌ DB connection error: {e}")
        return None

def setup_db():
    turso_execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            date_posted TEXT,
            linkedin_url TEXT,
            direct_url TEXT NOT NULL,
            job_type TEXT,
            is_remote TEXT,
            fetched_at TEXT NOT NULL,
            UNIQUE(direct_url)
        )
    """)

def scrape_google_jobs(search_query, max_jobs=50000):
    print(f"\n[START] Launching Playwright to scrape: '{search_query}'")
    jobs = []
    
    with sync_playwright() as p:
        # Launching Chromium. We use headless=True but inject a script to bypass simple bot detection.
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
        
        encoded_query = urllib.parse.quote_plus(search_query)
        job_url = f"https://www.google.com/search?q={encoded_query}&ibp=htl;jobs#htivrt=jobs&htichips=date_posted:today&fpstate=tldetail"
        
        print(f"🌐 Navigating to URL...")
        page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        
        # Wait for the exact card selector provided by user: a.MQUd2b
        try:
            page.wait_for_selector('a.MQUd2b', timeout=10000)
            print("✅ Found job listings container!")
        except Exception:
            print("⚠️ Could not find Job list UI. Saving HTML for debugging and trying one trick...")
            with open("google_blocked.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            page.screenshot(path="google_blocked.png")
            browser.close()
            return jobs
            
        # Scroll the left pane to load more jobs
        print("🔽 Scrolling to load job cards...")
        page.mouse.move(300, 500) # Move mouse over the left pane
        for _ in range(5):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(1000)
            
        # Get all list items that match the user's specific class
        list_items = page.locator('a.MQUd2b').all()
        print(f"📋 Found {len(list_items)} job cards on the page. Processing up to {max_jobs}...")
        
        count = 0
        for card in list_items:
            if count >= max_jobs:
                break
                
            try:
                # Based on user HTML: <div class="tNxQIb PUpOsf">Software Engineer-II</div>
                title_loc = card.locator('.tNxQIb')
                title = title_loc.inner_text().strip() if title_loc.count() > 0 else ""
                
                # Company and Location are in .wHYlTd
                comp_locs = card.locator('.wHYlTd').all()
                company = comp_locs[0].inner_text().strip() if len(comp_locs) > 0 else ""
                
                loc_via = comp_locs[1].inner_text().strip() if len(comp_locs) > 1 else ""
                location = loc_via.split('•')[0].strip() if '•' in loc_via else loc_via
                site = "google"
                if 'via' in loc_via:
                    site = loc_via.split('via')[-1].strip().lower()
                    
                if not title or not company:
                    continue
                    
                # Click the card to open details on the right side
                # This fetches the "Apply directly on Jobaaj" link
                card.click(force=True)
                page.wait_for_timeout(1000) # give right pane time to update
                
                # Based on user HTML for right pane: <div class="yVRmze-s2gQvd ..."> <a href="...">
                direct_url = ""
                apply_links = page.locator('.yVRmze-s2gQvd a').all()
                if apply_links:
                    direct_url = apply_links[0].get_attribute('href')
                    
                # Fallback to the Google Job Card URL if direct link fails
                if not direct_url:
                    direct_url = card.get_attribute('href')
                    
                # Store it
                # Store it
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "date_posted": "Recent",
                    "linkedin_url": "",
                    "direct_url": direct_url or card.get_attribute('href'),
                    "site": site,
                    "job_type": "Full-time",
                    "is_remote": "Remote" if "remote" in location.lower() else "On-site",
                    "fetched_at": time.strftime("%Y-%m-%d")
                })
                count += 1
                
            except Exception as e:
                # Skip to next item if extraction fails
                continue
                
        browser.close()
    return jobs

def main():
    setup_db()
    
    search_term = "data science jobs in Hyderabad"
    jobs = scrape_google_jobs(search_term, max_jobs=50000)
    
    if not jobs:
        print("\n❌ Failed to scrape Google Jobs.")
        return
        
    print(f"\n📊 Extracted {len(jobs)} jobs. Inserting into Turso...")
    print("-" * 80)
    
    inserted = 0
    for j in jobs:
        print(f"JOB: {j['title']}")
        print(f"COMP: {j['company']}")
        print(f"LOC: {j['location']}  |  via {j['site'].title()}")
        print(f"URL: {j['direct_url']}")
        print("-" * 60)
        
        sql = "INSERT OR IGNORE INTO jobs (title, company, location, date_posted, linkedin_url, direct_url, job_type, is_remote, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        args = [
            {"type": "text", "value": j['title']},
            {"type": "text", "value": j['company']},
            {"type": "text", "value": j['location']},
            {"type": "text", "value": j['date_posted']},
            {"type": "text", "value": j['linkedin_url']},
            {"type": "text", "value": j['direct_url']},
            {"type": "text", "value": j['job_type']},
            {"type": "text", "value": j['is_remote']},
            {"type": "text", "value": j['fetched_at']}
        ]
        
        res = turso_execute(sql, args)
        if res:
            print(f"  DB response: {json.dumps(res)[:200]}")
            for r in res.get("results", []):
                if r.get("type") == "ok":
                    inserted += r.get("response", {}).get("result", {}).get("affected_row_count", 0)
        else:
            print(f"  DB response: None (failed)")
    
    print("=" * 80)
    print(f"[DONE] Inserted {inserted} NEW jobs into the Turso 'jobs' table.")

if __name__ == "__main__":
    main()
