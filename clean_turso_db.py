import requests
import json
import os

TURSO_URL = "https://alljobs-ragesh.aws-ap-south-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzM1NTM5OTksImlkIjoiMDE5Y2UxNGItMTgwMS03MmQ2LWI0MmMtOGIzYTY0NWExZjE1IiwicmlkIjoiMjgzMDA4YzMtODRhZi00M2MwLWE5ZjItNWY3ZTUwMWZkZDUzIn0.mtjC1aL0M1rcwS2pJsM70Ytqk06Jqct2dVChPGcgEV0zvcv8hAb9opCC5L76xuEXnO6ZuUZU-Edlex7ABWgVCg"

def execute(sql):
    url = f"{TURSO_URL}/v2/pipeline"
    headers = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}
    body = {"requests": [{"type": "execute", "stmt": {"sql": sql}}, {"type": "close"}]}
    return requests.post(url, headers=headers, json=body).json()

# Look for jobs with no http in URL or very short title/company
sql_bad_jobs = """
SELECT id, title, company, url 
FROM all_jobs 
WHERE url NOT LIKE 'http%'
   OR length(title) < 3 
   OR length(company) < 2
   OR title LIKE '%#%'
   OR company = '0 jobs found'
   OR company = 'nan'
   OR title = 'nan'
"""

res = execute(sql_bad_jobs)
print("Found suspicious jobs:")
print(json.dumps(res, indent=2))

# Delete them automatically
sql_delete = """
DELETE FROM all_jobs 
WHERE url NOT LIKE 'http%'
   OR length(title) < 3 
   OR length(company) < 2
   OR title LIKE '%#%'
   OR company = '0 jobs found'
   OR company = 'nan'
   OR title = 'nan'
"""
execute(sql_delete)
print("Deleted suspicious jobs.")
