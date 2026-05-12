"""Download ALL jobs data from Turso (all_jobs table only, not big_jobs)."""
import sys, json, requests
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TURSO_URL = "https://jobsdata-ragesh.aws-ap-south-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzYxNjMxNDksImlkIjoiMDE5Y2UwYWItMWQwMS03MzBjLWEwYjUtNWVlNGRjMWQwOGQ4IiwicmlkIjoiMGNjZWYzMWMtZTFjNy00MDM3LTgwN2EtYjFjZDgyZjRkNGE2In0.bFlqY1nlnLXlkvIe90aAFlz9o2Hjx1f3O2-tVQmzEMmhXxNdLee-gYwPqBWHwz-ckyVx64wy6X53RYHbu3f9AA"

HEADERS = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}

def query(sql):
    resp = requests.post(
        f"{TURSO_URL}/v2/pipeline",
        headers=HEADERS,
        json={"requests": [{"type": "execute", "stmt": {"sql": sql}}, {"type": "close"}]},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"HTTP {resp.status_code}: {resp.text[:300]}")
        return None
    data = resp.json()
    if data["results"][0]["type"] != "ok":
        print(f"Error: {data['results'][0]}")
        return None
    return data["results"][0]["response"]["result"]

# Step 1: Check connection and list tables
print("=" * 60)
print("  Step 1: Checking Turso connection")
print("=" * 60)

result = query("SELECT name FROM sqlite_master WHERE type='table'")
if not result:
    print("Connection failed!")
    sys.exit(1)

tables = [row[0]["value"] for row in result["rows"]]
print(f"  Tables found: {tables}")

# Step 2: Get counts for each table
print("\n" + "=" * 60)
print("  Step 2: Table row counts")
print("=" * 60)

for table in tables:
    if table.startswith("_") or table == "sqlite_sequence":
        continue
    r = query(f"SELECT COUNT(*) FROM {table}")
    if r:
        count = r["rows"][0][0]["value"]
        print(f"  {table}: {count} rows")

# Step 3: Get schema of all_jobs related tables
print("\n" + "=" * 60)
print("  Step 3: Downloading all_jobs data")
print("=" * 60)

# Find the right table name for "all jobs"
all_jobs_tables = [t for t in tables if "job" in t.lower() and "big" not in t.lower()]
print(f"  Candidate tables: {all_jobs_tables}")

# Download each candidate table
for table_name in all_jobs_tables:
    # Get schema first
    schema = query(f"PRAGMA table_info({table_name})")
    if schema:
        cols = [row[1]["value"] for row in schema["rows"]]
        print(f"\n  Table '{table_name}' columns: {cols}")

    # Download all rows (paginated to avoid timeout)
    all_rows = []
    offset = 0
    page_size = 1000

    while True:
        print(f"    Fetching rows {offset} to {offset + page_size}...", end=" ", flush=True)
        result = query(f"SELECT * FROM {table_name} LIMIT {page_size} OFFSET {offset}")
        if not result or not result["rows"]:
            print("done")
            break

        row_cols = [c["name"] for c in result["cols"]]
        for row in result["rows"]:
            job = {}
            for i, col in enumerate(row_cols):
                job[col] = row[i]["value"] if row[i]["type"] != "null" else None
            all_rows.append(job)

        fetched = len(result["rows"])
        print(f"{fetched} rows")
        offset += page_size

        if fetched < page_size:
            break

    # Save to file
    filename = f"turso_backup_{table_name}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved {len(all_rows)} rows to {filename}")

print("\nDone! All jobs data downloaded.")
