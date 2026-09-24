import requests, json, sys

def test_cure_fit():
    url = "https://public.zwayam.com/jobs/search"
    # multipart/form-data fields
    data = {
        "companyId": "MTU0NzA=",
        "domain": "careers.cult.fit",
        "filterCri": json.dumps({
            "paginationStartNo": 0,
            "selectedCall": "sort",
            "sortCriteria": {"name": "modifiedDate", "isAscending": False},
            "anyOfTheseWords": ""
        })
    }
    try:
        r = requests.post(url, data=data, timeout=15)
        print("Cure.fit status:", r.status_code, "len", len(r.text))
    except Exception as e:
        print("Cure.fit error:", e)

def test_goldman_sachs():
    url = "https://api-higher.gs.com/gateway/api/v1/graphql"
    headers = {"higher-tenant-id": "external", "Content-Type": "application/json"}
    payload = {
        "operationName": "GetRoleFilters",
        "variables": {
            "filterCategories": ["JOB_FUNCTION","EXPERIENCE_LEVEL","DIVISION","SKILLSET","LOCATION"],
            "experiences": ["EARLY_CAREER","PROFESSIONAL"]
        },
        "query": "query GetRoleFilters($filterCategories: [RoleSearchFilterCategoryType!], $experiences: [RoleSearchExperience!]!) { roleSearchFilters(categories: $filterCategories, experiences: $experiences) { filterCategoryType { code description } filters { filter count } } }"
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        print("Goldman Sachs status:", r.status_code, "len", len(r.text))
    except Exception as e:
        print("Goldman Sachs error:", e)

def test_intuit_target(base_url):
    url = base_url + "/module/postmodule"
    headers = {"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/x-www-form-urlencoded"}
    # Test Featured Jobs payload
    data = "name=Job+List+Tabs+-+Featured+Jobs+-+(Section+6)&type=JobList"
    try:
        r = requests.post(url, headers=headers, data=data, timeout=15)
        print(f"{base_url.split('//')[-1]} status:", r.status_code, "len", len(r.text))
    except Exception as e:
        print(f"{base_url} error:", e)

def test_sap_labs():
    # First get CSRF token via GET (simplified: use the page URL)
    token_url = "https://jobs.sap.com/go/India/8807201/"
    try:
        r = requests.get(token_url, timeout=15)
        if r.status_code != 200:
            print("SAP Labs GET page failed:", r.status_code)
            return
        # Try to extract token from response headers (X-CSRF-Token) if present
        token = r.headers.get('x-csrf-token') or r.headers.get('X-CSRF-Token')
        if not token:
            print("SAP Labs token not found in headers, proceeding without token (expected to fail)")
        post_url = "https://jobs.sap.com/services/jobs/options/facetValues/"
        headers = {}
        if token:
            headers['x-csrf-token'] = token
        r2 = requests.post(post_url, headers=headers, json={}, timeout=15)
        print("SAP Labs POST status:", r2.status_code, "len", len(r2.text))
    except Exception as e:
        print("SAP Labs error:", e)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("Testing new endpoints...\n")
    test_cure_fit()
    test_goldman_sachs()
    test_intuit_target("https://jobs.intuit.com")
    test_intuit_target("https://indiajobs.target.com")
    test_sap_labs()
