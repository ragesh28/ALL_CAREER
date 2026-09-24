"""Test the newly added scrapers."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from scrape_all_companies_v2 import (
    scrape_accenture, scrape_tiger_analytics, scrape_virtusa,
    scrape_latentview, scrape_ltimindtree
)

tests = [
    ("Accenture", scrape_accenture, "https://www.accenture.com/in-en/careers/jobsearch?jt=Experience%3A%200-2%20years"),
    ("Tiger Analytics", scrape_tiger_analytics, "https://tiger-analytics.sensehq.com/careers/jobs/"),
    ("Virtusa", scrape_virtusa, "https://www.virtusa.com/careers/job-search"),
    ("LatentView", scrape_latentview, "https://latentview.darwinbox.in"),
    ("LTIMindtree", scrape_ltimindtree, "https://careers.ltimindtree.com"),
]

for name, fn, url in tests:
    try:
        result = fn(url, 2)
        if result and result[0].get("title"):
            t = result[0]["title"][:55]
            l = result[0].get("location", "")[:30]
            n = result[0].get("total_jobs", "?")
            print(f"OK {name}: {t} | {l} | total={n}")
        else:
            print(f"FAIL {name}: empty result")
    except Exception as e:
        print(f"ERR {name}: {e}")
