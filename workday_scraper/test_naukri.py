import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = "https://www.naukri.com/jobapi/v3/search?noOfResults=20&urlType=search_by_key_loc&searchType=adv&location=chennai&keyword=software%20developer%20fresher&pageNo=1&seoKey=software-developer-fresher-jobs-in-chennai&src=directSearch&latLong="

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "appid": "109",
    "systemid": "Naukri",
    "clientid": "d3skt0p",
    "accept": "application/json"
}

print("Testing Naukri API...")
try:
    r = requests.get(url, headers=headers, timeout=15)
    print("Status Code:", r.status_code)
    data = r.json()
    jobs = data.get("jobDetails", [])
    print(f"Found {len(jobs)} jobs!")
    if len(jobs) > 0:
        for j in jobs[:3]:
            print(f" - {j.get('title')} at {j.get('companyName')}")
except Exception as e:
    print("Error:", e)
