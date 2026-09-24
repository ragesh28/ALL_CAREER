"""Test Lever scraper directly."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from scrape_all_companies_v2 import scrape_lever, scrape_greenhouse

print("Meesho:", scrape_lever("https://api.lever.co/v0/postings/meesho?mode=json", 1))
print("Zeta:", scrape_lever("https://api.lever.co/v0/postings/zeta?mode=json", 1))
print("InMobi:", scrape_greenhouse("https://boards-api.greenhouse.io/v1/boards/inmobi/jobs?content=true", 1))
print("Groww:", scrape_greenhouse("https://boards-api.greenhouse.io/v1/boards/groww/jobs?content=true", 1))
