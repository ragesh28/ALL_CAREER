"""
STEP 2: Get Direct Apply Links using Selenium
Reads jobs.csv from Step 1, opens each LinkedIn job page
in a real browser, and extracts the original apply URL.

Uses Selenium (installed with linkedin-jobs-scraper).

Usage: py -3.11 step2_get_links.py
"""

import csv
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CSV_FILE = "jobs.csv"


def create_browser():
    """Create a headless Chrome browser."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    # Suppress logging
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(20)
    return driver


def get_direct_link(driver, linkedin_url):
    """
    Visit a LinkedIn job page and extract the direct apply URL.
    LinkedIn shows either:
    1. "Apply" button that links to company website (what we want)
    2. "Easy Apply" button (stays on LinkedIn - no external link)
    """
    try:
        driver.get(linkedin_url)
        time.sleep(2)  # Let page load

        # Method 1: Look for the apply button with external link
        # LinkedIn public job pages have an apply button that redirects
        selectors = [
            # Main apply button (external)
            "a.apply-button",
            "a[data-tracking-control-name='public_jobs_apply-link-offsite']",
            "a[data-tracking-control-name='public_jobs_apply-link-offsite_sign-up-modal']",
            # Apply button variations
            "a.sign-up-modal__outlet-btn",
            "a.topcard__org-name-link",
            # Generic apply links
            "a[href*='careers.google.com']",
            "a[href*='myworkdayjobs.com']",
            "a[href*='jobs.lever.co']",
            "a[href*='boards.greenhouse.io']",
        ]

        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    href = el.get_attribute("href") or ""
                    if href and "linkedin.com" not in href:
                        return href
            except:
                pass

        # Method 2: Look for any link with the apply flow
        # LinkedIn wraps external apply in a redirect URL
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            try:
                href = link.get_attribute("href") or ""
                # LinkedIn redirect format
                if "linkedin.com/rj/" in href or "linkedin.com/jobs/view/" in href:
                    continue
                if "careers.google.com" in href:
                    return href
                if "applyUrl" in href:
                    return href
            except:
                pass

        # Method 3: Check page source for applyUrl
        page_source = driver.page_source
        import re
        # Look for the apply URL in script tags
        patterns = [
            r'"companyApplyUrl"\s*:\s*"(https?://[^"]+)"',
            r'"applyUrl"\s*:\s*"(https?://[^"]+)"',
            r'"applyMethod".*?"url"\s*:\s*"(https?://[^"]+)"',
            r'careers\.google\.com/jobs/results/[^"\'<>\s]+',
        ]
        for pattern in patterns:
            match = re.search(pattern, page_source)
            if match:
                url = match.group(1) if match.lastindex else match.group(0)
                if "linkedin.com" not in url:
                    # Clean up escaped characters
                    url = url.replace("\\u002F", "/").replace("\\/", "/")
                    if not url.startswith("http"):
                        url = "https://" + url
                    return url

        return None

    except Exception as e:
        return None


def run():
    print("=" * 55)
    print("  STEP 2: Getting Direct Apply Links (Selenium)")
    print("=" * 55)

    # Read jobs from step 1
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print(f"\n❌ {CSV_FILE} not found! Run step1_jobspy.py first.")
        return

    if df.empty:
        print("\n⚠️ No jobs in CSV.")
        return

    total = len(df)
    print(f"\n📋 Found {total} jobs in {CSV_FILE}")
    print(f"🌐 Opening headless Chrome browser...\n")

    driver = create_browser()
    found = 0
    failed = 0

    try:
        for idx, row in df.iterrows():
            job_url = str(row.get("job_url", ""))
            title = str(row.get("title", "Unknown"))

            # Skip if already has a direct link
            existing = str(row.get("direct_apply_url", ""))
            if existing and existing != "" and existing != "nan":
                print(f"  [{idx+1}/{total}] ⏭️  {title} — already done")
                found += 1
                continue

            if not job_url or "linkedin.com" not in job_url:
                print(f"  [{idx+1}/{total}] ⏭️  {title} — not LinkedIn")
                continue

            print(f"  [{idx+1}/{total}] 🔗 {title}")
            direct_url = get_direct_link(driver, job_url)

            if direct_url:
                df.at[idx, "direct_apply_url"] = direct_url
                df.at[idx, "apply_url"] = direct_url
                found += 1
                print(f"           ✅ {direct_url[:70]}...")
            else:
                failed += 1
                print(f"           ⚠️ No direct link found")

            time.sleep(1)  # Be polite

    finally:
        driver.quit()
        print(f"\n🔒 Browser closed")

    # Save updated CSV
    df.to_csv(CSV_FILE, index=False, quoting=csv.QUOTE_ALL)

    print(f"\n{'=' * 55}")
    print(f"  📊 Results:")
    print(f"     🟢 Direct links found: {found}/{total}")
    print(f"     🔴 Failed: {failed}/{total}")
    print(f"{'=' * 55}")
    print(f"\n💾 Updated {CSV_FILE}")
    print(f"\n🌐 Start web server: py -3.11 app.py")
    print(f"   Then open: http://127.0.0.1:5000")


if __name__ == "__main__":
    run()
