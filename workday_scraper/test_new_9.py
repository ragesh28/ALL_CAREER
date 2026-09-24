import requests
import json
import urllib.parse
import sys

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json"
}

def test_api(name, method, url, **kwargs):
    try:
        if method == "GET":
            r = requests.get(url, headers=HEADERS, timeout=15, **kwargs)
        else:
            r = requests.post(url, headers=HEADERS, timeout=15, **kwargs)
        
        status = r.status_code
        try:
            data = r.json()
            # Try to guess count
            count = "?"
            if isinstance(data, list): count = len(data)
            elif isinstance(data, dict):
                if 'totalCount' in data: count = data['totalCount']
                elif 'total' in data: count = data['total']
                elif 'jobs' in data: count = len(data['jobs'])
                elif 'data' in data: 
                    if isinstance(data['data'], list): count = len(data['data'])
                    elif isinstance(data['data'], dict): count = len(data['data'].get('jobs', [])) or "?"
                elif 'jobRequisitions' in data: count = len(data['jobRequisitions'])
                elif 'jobPostings' in data: count = len(data['jobPostings'])
                elif 'items' in data: count = len(data['items'])
            result = f"JSON, count={count}"
        except:
            result = f"TEXT/HTML, length={len(r.text)}"
            
        print(f"[{status}] {name}: {result}")
        if status != 200:
            print(f"   -> {r.text[:200]}")
    except Exception as e:
        print(f"[ERR] {name}: {e}")

print("Testing 9 New APIs...")

# 71. Bosch
bosch_params = {"page": "1", "pagesize": "10", "avars": '{"country":["in"]}'}
test_api("Bosch", "GET", "https://bosch-i3-caas-api.e-spirit.cloud/bosch-i3-prod/bosch-de.jobs.content/_aggrs/get_jobs", params=bosch_params)

# 72. Siemens (HTML page)
test_api("Siemens", "GET", "https://jobs.siemens.com/en_US/externaljobs/SearchJobs/?folderOffset=0")

# 74. GE Healthcare (Phenom POST)
ge_payload = {
    "keyword": "",
    "exactMatch": True,
    "locationData": {"placeVal": "India"},
    "size": 10,
    "from": 0
}
# Using standard Phenom endpoint to see if it responds correctly instead of widget ddoKey
test_api("GE Healthcare", "POST", "https://careers.gehealthcare.com/api/jobs", json=ge_payload)

# 75. Honeywell (Oracle Cloud)
test_api("Honeywell", "GET", "https://ibqbjb.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?finder=findReqs;siteNumber=CX_1,limit=10")

# 76. Qualcomm (Eightfold GET)
test_api("Qualcomm", "GET", "https://careers.qualcomm.com/api/pcsx/search?domain=qualcomm.com&location=India&start=0&sort_by=relevance")

# 77. Ericsson (Eightfold GET)
test_api("Ericsson", "GET", "https://jobs.ericsson.com/api/pcsx/search?domain=ericsson.com&location=India&start=0&sort_by=relevance")

# 78. Bank of America
test_api("Bank of America", "GET", "https://careers.bankofamerica.com/services/jobssearchservlet?search=jobsByLocation&searchstring=India&start=0&rows=10")

# 79. Amadeus (Workday POST)
amadeus_payload = {
    "appliedFacets": {},
    "limit": 20,
    "offset": 0,
    "searchText": ""
}
test_api("Amadeus", "POST", "https://amadeus.wd502.myworkdayjobs.com/wday/cxs/amadeus/jobs/jobs", json=amadeus_payload)

# 80. Maersk
test_api("Maersk", "GET", "https://api.maersk.com/careers/vacancies?city=India&limit=10&offset=0&language=EN")
