"""
LinkedIn Original Apply Link Extractor
=======================================
Attempts to extract the REAL company apply link from LinkedIn job postings.

IMPORTANT FINDINGS:
- LinkedIn's guest API does NOT expose external apply URLs
- The "Apply" button always redirects to LinkedIn login for guests
- JobSpy's LinkedIn scraper also doesn't return job_url_direct
- The ONLY reliable way to get external apply links is:
  1. Indeed jobs via JobSpy (job_url_direct field) - WORKS
  2. Google Jobs via Playwright (direct click extraction) - WORKS
  3. LinkedIn - requires authenticated session (NOT possible without login)

This script demonstrates what CAN be extracted from LinkedIn guest pages
and shows the best alternative approach using Indeed.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import re
import requests
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}

# ──────────────────────────────────────────────────────────────────────
# LINKEDIN GUEST API EXTRACTION
# ──────────────────────────────────────────────────────────────────────
def extract_job_id(linkedin_url):
    match = re.search(r'/jobs/view/(\d+)', str(linkedin_url))
    return match.group(1) if match else None


def fetch_linkedin_job_info(job_id):
    """Fetch whatever info is available from LinkedIn's guest API."""
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        html = resp.text
    except Exception as e:
        print(f"  Error: {e}")
        return None

    info = {"job_id": job_id, "html_length": len(html)}

    # Extract title
    m = re.search(r'<h2[^>]*>([^<]+)</h2>', html)
    info["title"] = m.group(1).strip() if m else "Unknown"

    # Extract company
    m = re.search(r'topcard__org-name[^>]*>\s*([^<]+)', html)
    info["company"] = m.group(1).strip() if m else "Unknown"

    # Extract location
    m = re.search(r'topcard__flavor--bullet[^>]*>([^<]+)', html)
    info["location"] = m.group(1).strip() if m else ""

    # Check apply type
    info["is_offsite"] = "offsite" in html.lower()
    info["is_easy_apply"] = "Easy Apply" in html

    # Attempt to find external URL (usually blocked for guests)
    apply_url = None
    for pattern in [
        r'"companyApplyUrl"\s*:\s*"([^"]+)"',
        r'"offsiteApplyUrl"\s*:\s*"([^"]+)"',
        r'"applyUrl"\s*:\s*"([^"]+)"',
        r'href="(https://www\.linkedin\.com/jobs/view/externalApply/[^"]+)"',
    ]:
        m = re.search(pattern, html)
        if m:
            apply_url = m.group(1).replace("&amp;", "&")
            break

    # Find external (non-linkedin) URLs if any
    all_urls = re.findall(r'href="(https?://[^"]+)"', html)
    external_urls = [
        u.replace("&amp;", "&") for u in all_urls
        if "linkedin.com" not in u and "licdn.com" not in u
    ]

    info["apply_url"] = apply_url
    info["external_urls"] = external_urls
    return info


# ──────────────────────────────────────────────────────────────────────
# INDEED DIRECT LINK (THE APPROACH THAT ACTUALLY WORKS)
# ──────────────────────────────────────────────────────────────────────
def demo_indeed_direct_links():
    """Show that Indeed via JobSpy CAN return direct company apply links."""
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("  JobSpy not installed!")
        return

    print("\n  Scraping Indeed for 'Google' jobs (these have direct apply links)...")
    jobs_df = scrape_jobs(
        site_name=["indeed"],
        search_term="Google",
        location="Bangalore, India",
        results_wanted=5,
        country_indeed="India",
    )

    if jobs_df is None or jobs_df.empty:
        print("  No Indeed jobs returned")
        return

    print(f"  Got {len(jobs_df)} Indeed jobs\n")
    print(f"  Columns available: {list(jobs_df.columns)}\n")

    has_direct = "job_url_direct" in jobs_df.columns
    for idx, row in jobs_df.iterrows():
        company = str(row.get("company", "?"))[:30]
        title = str(row.get("title", "?"))[:45]
        job_url = str(row.get("job_url", ""))
        direct_url = str(row.get("job_url_direct", "")) if has_direct else ""

        is_real = direct_url and direct_url not in ("nan", "None", "")

        print(f"  {'DIRECT' if is_real else 'INDEED'} | {company} - {title}")
        print(f"    Indeed URL:  {job_url[:100]}")
        if is_real:
            print(f"    DIRECT URL:  {direct_url[:100]}")
        print()


# ──────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 80)
    print("  ORIGINAL APPLY LINK EXTRACTOR")
    print("=" * 80)

    # ── Test LinkedIn jobs ──
    test_jobs = [
        "https://www.linkedin.com/jobs/view/4398164736/",  # Google - offsite apply
        "https://www.linkedin.com/jobs/view/4364800054/",   # Microsoft
        "https://www.linkedin.com/jobs/view/4390932569/",   # Groww
    ]

    print("\n" + "─" * 80)
    print("  PART 1: LINKEDIN GUEST API EXTRACTION")
    print("─" * 80)

    for job_url in test_jobs:
        job_id = extract_job_id(job_url)
        if not job_id:
            continue

        print(f"\n  Job ID: {job_id}")
        info = fetch_linkedin_job_info(job_id)
        if not info:
            print(f"  Could not fetch (404 or blocked)")
            continue

        print(f"  Title:      {info['title']}")
        print(f"  Company:    {info['company']}")
        print(f"  Location:   {info['location']}")
        print(f"  Apply Type: {'Offsite (External)' if info['is_offsite'] else 'Easy Apply (LinkedIn)'}")

        if info["apply_url"]:
            print(f"  Apply URL:  {info['apply_url'][:120]}")
        elif info["external_urls"]:
            print(f"  External URLs found: {len(info['external_urls'])}")
            for eu in info["external_urls"][:3]:
                print(f"    -> {eu[:120]}")
        else:
            print(f"  Apply URL:  HIDDEN (LinkedIn requires login to reveal external link)")

        time.sleep(1)

    # ── Test Indeed (direct links) ──
    print("\n\n" + "─" * 80)
    print("  PART 2: INDEED DIRECT APPLY LINKS (VIA JOBSPY)")
    print("─" * 80)
    demo_indeed_direct_links()

    # ── Summary ──
    print("\n" + "=" * 80)
    print("  CONCLUSION")
    print("=" * 80)
    print("""
  LinkedIn: The guest API does NOT expose external apply URLs.
            The 'Apply' button forces login even for offsite jobs.
            There is NO way to extract the real company URL without
            an authenticated LinkedIn session.

  Indeed:   JobSpy CAN extract direct company apply links via the
            'job_url_direct' field. Your big_company_scrape.py
            already uses this correctly.

  Google:   Your scrape_google_jobs.py Playwright scraper already 
            clicks the apply button and extracts the direct URL.

  RECOMMENDATION: Your current setup already captures original 
  apply links from Indeed and Google. LinkedIn is the only source
  that blocks this, and there is no legal/safe workaround without
  risking your LinkedIn account being banned.
""")
    print("=" * 80)
