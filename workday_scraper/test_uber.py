import requests, json, sys
sys.stdout.reconfigure(encoding="utf-8")

resp = requests.post(
    "https://www.uber.com/api/loadSearchJobsResults?localeCode=en",
    headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0","x-csrf-token":"x"},
    json={"params":{"location":[{"country":"IND"}],"department":[],"team":[]},"limit":3,"page":1},
    timeout=10
)
data = resp.json()
results = data.get("data",{}).get("results",[])
total = data.get("data",{}).get("totalResults",{})
print("Total:", total)
for j in results[:3]:
    loc = j.get("allLocations",[])
    loc_str = ", ".join([l.get("city","") + " " + l.get("country","") for l in loc]) if loc else "N/A"
    print("Title:", j.get("title"))
    print("Location:", loc_str)
    print("Team:", j.get("team",""))
    print("Dept:", j.get("department",""))
    print()
