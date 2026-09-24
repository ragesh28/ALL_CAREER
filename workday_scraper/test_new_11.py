import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json"
}

def test_api(name, method, url, **kwargs):
    try:
        if method == "GET":
            r = requests.get(url, headers=H, timeout=10, **kwargs)
        else:
            r = requests.post(url, headers=H, timeout=10, **kwargs)
        
        status = r.status_code
        try:
            data = r.json()
            # Try to guess count
            count = "?"
            if isinstance(data, list): count = len(data)
            elif isinstance(data, dict):
                if 'jobs' in data: count = len(data['jobs'])
                elif 'data' in data: 
                    if isinstance(data['data'], list): count = len(data['data'])
                    elif isinstance(data['data'], dict): count = len(data['data'].get('jobs', [])) or "?"
                elif 'jobRequisitions' in data: count = len(data['jobRequisitions'])
                elif 'jobPostings' in data: count = len(data['jobPostings'])
            result = f"JSON, count={count}"
        except:
            result = f"TEXT/HTML, length={len(r.text)}"
            
        print(f"[{status}] {name}: {result}")
    except Exception as e:
        print(f"[ERR] {name}: {e}")

print("Testing 11 New APIs...")

# 59. Zeta
test_api("Zeta Suite", "GET", "https://api.lever.co/v0/postings/zeta?group=team&mode=json")

# 60. Meesho
test_api("Meesho", "GET", "https://api.lever.co/v0/postings/meesho/")

# 61. Groww
test_api("Groww", "GET", "https://boards-api.greenhouse.io/v1/boards/groww/jobs")

# 62. Zerodha
test_api("Zerodha", "GET", "https://careers.zerodha.com/api/jobs")

# 63. Cure.fit (Zwayam needs empty json or something usually)
test_api("Cure.fit", "POST", "https://public.zwayam.com/jobs/search", json={})

# 64. Goldman Sachs (GraphQL usually needs query)
test_api("Goldman Sachs", "POST", "https://api-higher.gs.com/gateway/api/v1/graphql", json={})

# 65. Intuit (Radancy module usually needs x-www-form-urlencoded params)
test_api("Intuit", "POST", "https://jobs.intuit.com/module/postmodule")

# 66. Target (Radancy module)
test_api("Target", "POST", "https://indiajobs.target.com/module/postmodule")

# 67. SAP Labs (Successfactors jobs)
test_api("SAP Labs", "POST", "https://jobs.sap.com/services/recruiting/v1/jobs", json={"locale":"en_US","limit":10,"offset":0})

# 68. Oracle Cloud
test_api("Oracle", "GET", "https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions")

# 69. Shell Workday
test_api("Shell", "POST", "https://shell.wd3.myworkdayjobs.com/wday/cxs/shell/shellcareers/jobs", json={"appliedFacets":{},"limit":10,"offset":0,"searchText":""})

