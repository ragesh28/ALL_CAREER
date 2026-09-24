"""Test 6 newly added scrapers."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from scrape_all_companies_v2 import (
    scrape_paypal, scrape_citi, scrape_turing,
    scrape_ltimindtree, scrape_latentview, scrape_wipro
)

tests = [
    ("PayPal", scrape_paypal, "https://paypal.eightfold.ai/careers"),
    ("Citi", scrape_citi, "https://jobs.citi.com"),
    ("Turing", scrape_turing, "https://careers.turing.com"),
    ("LTIMindtree", scrape_ltimindtree, "https://careers.ltimindtree.com"),
    ("LatentView", scrape_latentview, "https://latentview.darwinbox.in"),
    ("Wipro", scrape_wipro, "https://careers.wipro.com"),
]

for name, fn, url in tests:
    try:
        result = fn(url, 1)
        if result and result[0].get("title"):
            t = result[0]["title"][:55]
            l = result[0].get("location", "")[:30]
            n = result[0].get("total_jobs", "?")
            print(f"OK {name}: {t} | {l} | total={n}")
        else:
            print(f"FAIL {name}: empty result")
    except Exception as e:
        print(f"ERR {name}: {e}")
