import sys, requests, json
sys.path.insert(0, ".")
from scrape_all_companies_v2 import scrape_virtusa
jobs = scrape_virtusa('https://www.virtusa.com/careers/job-search', 10)
print(jobs)

headers = {"User-Agent":"Mozilla/5.0","Accept":"application/json","Content-Type":"application/json","x-cache-graphql": "true"}
q='''query JobListResultsQuery($isList: String!) { jobListResults(isList: $isList) { results { title careerCtaLink country city state postedDate contestNumber jobField employeeStatus } } }'''
r=requests.post('https://prod.agenticweb-marketing.com/careers/graphql',headers=headers,json={'query':q,'variables':{'isList':'true'}},timeout=20)
results = r.json().get("data", {}).get("jobListResults", {}).get("results", [])
print(len(results))
print(results[:2])
india_jobs = [j for j in results if j.get("country", "") == "India"]
print("India:", len(india_jobs))
