import json
import time
from scrape_all_companies_v2 import detect_and_scrape

def run():
    with open('companies_links.json', encoding='utf-8') as f:
        companies = json.load(f)
        
    working = []
    not_working = []
    
    for i, c in enumerate(companies):
        name = c['company']
        ats = c.get('ats', 'Unknown')
        urls = c.get('urls', [])
        if not urls:
            not_working.append((name, "No URL provided"))
            continue
            
        print(f"Testing [{i+1}/{len(companies)}] {name}...")
        try:
            # We wrap with a quick timeout or just let requests timeout (15s usually)
            jobs = detect_and_scrape(name, ats, urls[0], limit=1)
            if jobs and len(jobs) > 0 and jobs[0].get('title'):
                working.append((name, jobs[0].get('title')))
                print(f"  -> OK: {jobs[0]['title']}")
            else:
                not_working.append((name, "Empty results"))
                print(f"  -> FAIL: Empty results")
        except Exception as e:
            not_working.append((name, str(e)))
            print(f"  -> ERR: {e}")
            
    print("\n" + "="*50)
    print(f"SUMMARY: {len(working)} WORKING, {len(not_working)} NOT WORKING")
    print("="*50)
    print("WORKING:")
    for n, t in working:
        print(f" - {n}")
    print("\nNOT WORKING:")
    for n, e in not_working:
        print(f" - {n}: {e}")

if __name__ == '__main__':
    run()
