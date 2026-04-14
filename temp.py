"""Backup all big_jobs, then clear the table."""
import sys, json, requests
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Big company jobs database
TURSO_URL = "https://jobsdata-ragesh.aws-ap-south-1.turso.io"
# Try the non-expiring token from local_scraper.py (alljobs DB)
# If that doesn't work, we need the jobsdata token
TOKENS = [
    # local_scraper token (no expiry, but for alljobs DB)
    "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzM5MDk4NjQsImlkIjoiMDE5Y2UxNGItMTgwMS03MmQ2LWI0MmMtOGIzYTY0NWExZjE1IiwicmlkIjoiMjgzMDA4YzMtODRhZi00M2MwLWE5ZjItNWY3ZTUwMWZkZDUzIn0.RTp-3zplnbqlpx6qgu_XwxAWOokQIY1TmR9kQtGmC2J1tyRqy5n7LuitSbYdRmD2zBKQEnDLB_Ca4AUm7wt4CQ",
    # check_turso token (for alljobs DB, no expiry)
    "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzM1NTM5OTksImlkIjoiMDE5Y2UxNGItMTgwMS03MmQ2LWI0MmMtOGIzYTY0NWExZjE1IiwicmlkIjoiMjgzMDA4YzMtODRhZi00M2MwLWE5ZjItNWY3ZTUwMWZkZDUzIn0.mtjC1aL0M1rcwS2pJsM70Ytqk06Jqct2dVChPGcgEV0zvcv8hAb9opCC5L76xuEXnO6ZuUZU-Edlex7ABWgVCg",
    # expired jobsdata token
    "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE3NzM5MDA3MDAsImlhdCI6MTc3MzI5NTkwMCwiaWQiOiIwMTljZTBhYi0xZDAxLTczMGMtYTBiNS01ZWU0ZGMxZDA4ZDgiLCJyaWQiOiIwY2NlZjMxYy1lMWM3LTQwMzctODA3YS1iMWNkODJmNGQ0YTYifQ.HtmuTZP3oqCa22fOJBPneLQDzmg8G45VXtqpZ0SK4ffxryf371ohb5ir88TXjmgjjGUGwcclBEWt7t81AD0yBg",
]

def try_query(sql):
    for token in TOKENS:
        try:
            resp = requests.post(
                f"{TURSO_URL}/v2/pipeline",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"requests": [{"type": "execute", "stmt": {"sql": sql}}, {"type": "close"}]},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results") and data["results"][0].get("type") == "ok":
                    print(f"  Token works! (ends ...{token[-10:]})")
                    return data, token
                else:
                    print(f"  Token auth OK but query error: {data}")
            else:
                print(f"  Token ...{token[-10:]} -> HTTP {resp.status_code}")
        except Exception as e:
            print(f"  Token ...{token[-10:]} -> Error: {e}")
    return None, None

# Step 1: Test connection
print("=" * 60)
print("  Testing Turso connection to jobsdata DB")
print("=" * 60)
result, working_token = try_query("SELECT COUNT(*) FROM big_jobs")

if not result:
    print("\nNo working token found for jobsdata-ragesh DB.")
    print("You need to generate a new Turso token.")
    sys.exit(1)

# Get count
count = result["results"][0]["response"]["result"]["rows"][0][0]["value"]
print(f"\n  Total big_jobs in DB: {count}")

# Step 2: Download all jobs
print("\n" + "=" * 60)
print("  Downloading all big_jobs...")
print("=" * 60)

resp = requests.post(
    f"{TURSO_URL}/v2/pipeline",
    headers={"Authorization": f"Bearer {working_token}", "Content-Type": "application/json"},
    json={"requests": [
        {"type": "execute", "stmt": {"sql": "SELECT * FROM big_jobs"}},
        {"type": "close"}
    ]},
    timeout=30,
)
data = resp.json()
rows = data["results"][0]["response"]["result"]["rows"]
cols = [c["name"] for c in data["results"][0]["response"]["result"]["cols"]]

jobs = []
for row in rows:
    job = {}
    for i, col in enumerate(cols):
        job[col] = row[i]["value"] if row[i]["type"] != "null" else None
    jobs.append(job)

backup_file = "big_jobs_backup.json"
with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(jobs, f, indent=2, ensure_ascii=False)

print(f"  Backed up {len(jobs)} jobs to {backup_file}")

# Step 3: Clear all big_jobs
print("\n" + "=" * 60)
print("  Clearing all big_jobs from Turso...")
print("=" * 60)

resp = requests.post(
    f"{TURSO_URL}/v2/pipeline",
    headers={"Authorization": f"Bearer {working_token}", "Content-Type": "application/json"},
    json={"requests": [
        {"type": "execute", "stmt": {"sql": "DELETE FROM big_jobs"}},
        {"type": "close"}
    ]},
    timeout=15,
)
del_result = resp.json()
if del_result["results"][0]["type"] == "ok":
    affected = del_result["results"][0]["response"]["result"]["affected_row_count"]
    print(f"  Deleted {affected} rows from big_jobs")
else:
    print(f"  Error: {del_result}")

# Verify empty
result2, _ = try_query("SELECT COUNT(*) FROM big_jobs")
if result2:
    remaining = result2["results"][0]["response"]["result"]["rows"][0][0]["value"]
    print(f"  Remaining rows: {remaining}")

print("\nDone!")
