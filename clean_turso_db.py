import requests
import json
import os

TURSO_URL = "https://alljobs-ragesh.aws-ap-south-1.turso.io"
TURSO_TOKEN = os.environ.get("TURSO_TOKEN") or os.environ["TURSO_AUTH_TOKEN"]

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
