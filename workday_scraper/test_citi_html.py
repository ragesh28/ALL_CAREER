import sys, requests, re
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html",
}

url = "https://jobs.citi.com/search-jobs/India/287/2/1269750/22/79/50/2"
resp = requests.get(url, headers=headers, timeout=10)
print(f"Status: {resp.status_code}")

soup = BeautifulSoup(resp.text, "html.parser")

# Find total count
count_el = soup.select_one("#results-count, .result-count, [id*=result]")
if count_el:
    print(f"Result count element: {count_el.get_text(strip=True)}")

# Find all h1/h2 with numbers
for h in soup.find_all(["h1", "h2"]):
    text = h.get_text(strip=True)
    if any(c.isdigit() for c in text):
        print(f"Header with number: {text}")

# Try to find job items
job_items = soup.select("#search-results-list li")
if not job_items:
    job_items = soup.select(".search-results li")
if not job_items:
    job_items = soup.select('[data-job-id]')

print(f"\nJob items found: {len(job_items)}")

for item in job_items[:3]:
    title = item.select_one("h2, h3, .job-title, a")
    location = item.select_one(".job-location, [class*=location]")
    date = item.select_one(".job-date, [class*=date]")
    link = item.select_one("a")
    
    print(f"  Title: {title.get_text(strip=True) if title else 'N/A'}")
    print(f"  Location: {location.get_text(strip=True) if location else 'N/A'}")
    print(f"  Date: {date.get_text(strip=True) if date else 'N/A'}")
    print(f"  Link: {'https://jobs.citi.com' + link['href'] if link and link.get('href') else 'N/A'}")
    print()

# Find total results count from text
all_text = soup.get_text()
matches = re.findall(r"(\d[\d,]*)\s*(?:Result|Job|Opening|Position|result)", all_text)
if matches:
    print(f"Total count from text: {matches}")

# Also check pagination
pages = soup.select(".pagination a, [class*=pager] a")
print(f"Pagination links: {len(pages)}")
for pg in pages[:5]:
    print(f"  Page: {pg.get_text(strip=True)} -> {pg.get('href','')}")
