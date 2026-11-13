import os
import requests
import json

TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL", "https://jobsdata-ragesh.aws-ap-south-1.turso.io")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN") or os.environ["TURSO_TOKEN"]

url = f"{TURSO_DATABASE_URL}/v2/pipeline"
headers = {"Authorization": f"Bearer {TURSO_AUTH_TOKEN}", "Content-Type": "application/json"}
body = {"requests": [{"type": "execute", "stmt": {"sql": "SELECT title, company, location FROM jobs ORDER BY id DESC LIMIT 10"}}, {"type": "close"}]}

resp = requests.post(url, headers=headers, json=body)
data = resp.json()
rows = data['results'][0]['response']['result']['rows']
for i, row in enumerate(rows):
    print(f"- **{row[0]['value']}** at {row[1]['value']} ({row[2]['value']})")
