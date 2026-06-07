import os
import time
import pandas as pd
import tls_client
from jobspy import scrape_jobs

# ---------------------------------------------------------
# MONKEYPATCH: Bypass ScraperAPI TLS certificate errors
# ---------------------------------------------------------
# ScraperAPI intercepts HTTPS connections when used as an HTTP proxy.
# Since JobSpy uses 'tls_client' under the hood for Indeed, it rigidly 
# enforces CA checks, leading to "x509: certificate signed by unknown authority".
# We bypass this by forcing insecure_skip_verify=True on all requests.
old_execute_request = tls_client.Session.execute_request
def new_execute_request(self, method, url, **kwargs):
    kwargs['insecure_skip_verify'] = True
    return old_execute_request(self, method, url, **kwargs)
tls_client.Session.execute_request = new_execute_request
# ---------------------------------------------------------

def main():
    print("Scraping Oracle jobs in Bangalore from Indeed...")
    
    # User's ScraperAPI key formatted for HTTP Proxy usage
    proxy_url = "http://scraperapi:848135f0730de46500c210f27b3a556d@proxy-server.scraperapi.com:8001"
    
    try:
        # JobSpy parameters as requested
        jobs = scrape_jobs(
            site_name=["indeed"],
            search_term="Oracle",  
            location="Bangalore, Karnataka, India",
            results_wanted=100,
            country_indeed="India",
            proxy=proxy_url
        )
    except Exception as e:
        print(f"Error scraping: {e}")
        return

    if jobs is None or jobs.empty:
        print("No jobs found. (Note: ScraperAPI proxy might be timing out or blocked by Indeed)")
        return
        
    print(f"Found {len(jobs)} total jobs. Filtering specifically for 'Oracle'...")
    
    # Filter for Oracle company explicitly (since scrape_jobs doesn't natively accept 'company' kwarg anymore)
    oracle_jobs = jobs[jobs['company'].str.contains('Oracle', case=False, na=False)]
    
    if oracle_jobs.empty:
        print("No Oracle jobs found in the scraped results.")
        return
        
    print(f"\n✅ SUCCESS! Found {len(oracle_jobs)} Oracle jobs.\n")
    print("=" * 60)
    
    for _, row in oracle_jobs.iterrows():
        title = str(row.get("title", ""))
        company_name = str(row.get("company", ""))
        location = str(row.get("location", ""))
        
        # Extract the original apply link (JobSpy extracts this to 'job_url_direct')
        original_apply_link = str(row.get("job_url_direct", ""))
        if original_apply_link == "nan" or not original_apply_link:
            original_apply_link = ""
            
        print(f"Title: {title}")
        print(f"Company: {company_name}")
        print(f"Location: {location}")
        print(f"Original Apply Link: {original_apply_link or 'Not found'}")
        print("-" * 60)
        
        # 2-3 second delay between processing/printing jobs as requested
        time.sleep(2)

if __name__ == "__main__":
    main()
