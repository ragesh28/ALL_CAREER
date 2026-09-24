"""Quick test of all companies - 1 job each."""
import sys, json, time
sys.stdout.reconfigure(encoding="utf-8")
from scrape_all_companies_v2 import detect_and_scrape

with open("companies_links.json", "r", encoding="utf-8") as f:
    companies = json.load(f)

success = []
failed = []

for c in companies:
    name = c["company"]
    ats = c.get("ats", "Unknown")
    urls = c.get("urls", [])
    if not urls:
        failed.append(name + " (NO URL)")
        print("SKIP " + name + " - no URL")
        continue
    url = urls[0]
    try:
        jobs = detect_and_scrape(name, ats, url, limit=1)
        if jobs and jobs[0].get("title"):
            t = jobs[0]["title"][:50]
            l = jobs[0].get("location", "")[:30]
            n = jobs[0].get("total_jobs", "?")
            success.append(name + ": " + t + " | " + l + " | total=" + str(n))
            print("OK " + name + " => " + t)
        else:
            failed.append(name + " (empty result)")
            print("FAIL " + name + " - empty")
    except Exception as e:
        failed.append(name + " (" + str(e)[:40] + ")")
        print("ERR " + name + ": " + str(e)[:60])
    time.sleep(0.5)

print("\n" + "=" * 60)
print("SUCCESS: " + str(len(success)) + "/" + str(len(companies)))
for s in success:
    print("  OK " + s)
print("\nFAILED: " + str(len(failed)) + "/" + str(len(companies)))
for f2 in failed:
    print("  FAIL " + f2)
print("=" * 60)
