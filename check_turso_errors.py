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

res = execute("SELECT id, title, company, location, url, source FROM all_jobs ORDER BY fetched_at DESC LIMIT 50")
with open("C:/Users/Ragesh.l/Documents/VS code/ALL_CAREER_3/output_turso.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)

res2 = execute("SELECT count(*) FROM all_jobs WHERE title LIKE '%error%' OR company LIKE '%error%'")
res3 = execute("SELECT count(*) FROM all_jobs WHERE title = 'nan' OR company = 'nan' OR url = 'nan'")
print("Rows with 'error':", res2['results'][0]['response']['result']['rows'][0][0]['value'])
print("Rows with 'nan':", res3['results'][0]['response']['result']['rows'][0][0]['value'])
