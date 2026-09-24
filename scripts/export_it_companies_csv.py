import os
import sys
import re
import csv
import time
import sqlite3
from pathlib import Path

# Ensure UTF-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "company_master.db"
OUTPUT_CSV = DATA_DIR / "it_companies_locations.csv"

# Comprehensive list of Indian tech hub cities and districts
CITY_PATTERNS = [
    ("bangalore", "Bangalore"),
    ("bengaluru", "Bangalore"),
    ("chennai", "Chennai"),
    ("madras", "Chennai"),
    ("hyderabad", "Hyderabad"),
    ("secunderabad", "Hyderabad"),
    ("mumbai", "Mumbai"),
    ("bombay", "Mumbai"),
    ("navi mumbai", "Navi Mumbai"),
    ("thane", "Thane"),
    ("pune", "Pune"),
    ("delhi", "Delhi"),
    ("new delhi", "New Delhi"),
    ("gurgaon", "Gurgaon"),
    ("gurugram", "Gurgaon"),
    ("noida", "Noida"),
    ("greater noida", "Greater Noida"),
    ("faridabad", "Faridabad"),
    ("ghaziabad", "Ghaziabad"),
    ("kolkata", "Kolkata"),
    ("calcutta", "Kolkata"),
    ("ahmedabad", "Ahmedabad"),
    ("surat", "Surat"),
    ("vadodara", "Vadodara"),
    ("coimbatore", "Coimbatore"),
    ("kochi", "Kochi"),
    ("cochin", "Kochi"),
    ("thiruvananthapuram", "Trivandrum"),
    ("trivandrum", "Trivandrum"),
    ("kozhikode", "Kozhikode"),
    ("calicut", "Kozhikode"),
    ("madurai", "Madurai"),
    ("trichy", "Trichy"),
    ("tiruchirappalli", "Trichy"),
    ("salem", "Salem"),
    ("kanchipuram", "Kanchipuram"),
    ("chengalpattu", "Chengalpattu"),
    ("chinglepet", "Chengalpattu"),
    ("tiruvallur", "Tiruvallur"),
    ("vellore", "Vellore"),
    ("mysore", "Mysore"),
    ("mysuru", "Mysore"),
    ("mangalore", "Mangalore"),
    ("mangaluru", "Mangalore"),
    ("hubli", "Hubli"),
    ("dharwad", "Dharwad"),
    ("belgaum", "Belgaum"),
    ("chandigarh", "Chandigarh"),
    ("mohali", "Mohali"),
    ("panchkula", "Panchkula"),
    ("jaipur", "Jaipur"),
    ("lucknow", "Lucknow"),
    ("kanpur", "Kanpur"),
    ("indore", "Indore"),
    ("bhopal", "Bhopal"),
    ("bhubaneswar", "Bhubaneswar"),
    ("cuttack", "Cuttack"),
    ("visakhapatnam", "Visakhapatnam"),
    ("vizag", "Visakhapatnam"),
    ("vijayawada", "Vijayawada"),
    ("nagpur", "Nagpur"),
    ("nashik", "Nashik"),
    ("patna", "Patna"),
    ("ranchi", "Ranchi"),
    ("dehradun", "Dehradun"),
    ("guwahati", "Guwahati"),
]

# Compile regex for fast lookup
COMPILED_CITIES = [(re.compile(r'\b' + re.escape(pat) + r'\b', re.IGNORECASE), norm) for pat, norm in CITY_PATTERNS]

def clean_state_name(st):
    if not st or st.lower() in ("null", "none", "india", "nan"):
        return ""
    return st.strip().title()

def extract_cities_from_address(addr_str):
    if not addr_str:
        return []
    found = []
    seen = set()
    for regex, city_name in COMPILED_CITIES:
        if regex.search(addr_str):
            if city_name not in seen:
                seen.add(city_name)
                found.append(city_name)
    return found

def main():
    print(f"Reading from: {DB_PATH}")
    print(f"Output target: {OUTPUT_CSV}")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Query all companies with NIC 72 or 62, PLUS legacy IT giants (like TCS, Infosys, Wipro, Google)
    query = """
    SELECT company_name, registered_state, roc, registered_address, cin
    FROM companies
    WHERE cin LIKE '_72%' 
       OR cin LIKE '_62%'
       OR cin IN (SELECT DISTINCT cin FROM company_aliases WHERE cin IS NOT NULL)
       OR company_name IN (
           'TATA CONSULTANCY SERVICES LIMITED',
           'INFOSYS LIMITED',
           'WIPRO LIMITED',
           'HCL TECHNOLOGIES LIMITED',
           'TECH MAHINDRA LIMITED',
           'PERSISTENT SYSTEMS LIMITED',
           'L&T TECHNOLOGY SERVICES LIMITED'
       )
    ORDER BY company_name ASC
    """
    
    start_time = time.time()
    cursor.execute(query)
    
    count = 0
    with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        # Header row
        writer.writerow(["Company Name", "City", "State", "All Locations", "CIN"])
        
        batch = []
        while True:
            rows = cursor.fetchmany(10000)
            if not rows:
                break
                
            for row in rows:
                comp_name, reg_state, roc, addr, cin = row
                comp_name = (comp_name or "").strip()
                state = clean_state_name(reg_state)
                addr_str = (addr or "").strip()
                
                # Extract city/locations
                cities = extract_cities_from_address(addr_str)
                primary_city = cities[0] if cities else ""
                
                # If no city matched from text, try extracting from ROC (e.g. 'ROC Chennai' -> Chennai)
                if not primary_city and roc:
                    roc_cities = extract_cities_from_address(roc)
                    if roc_cities:
                        primary_city = roc_cities[0]
                        if primary_city not in cities:
                            cities.append(primary_city)
                
                # Format All Locations string (e.g., "Chennai, Tamil Nadu" or "Bangalore, Mysore, Karnataka")
                loc_tokens = list(cities)
                if state and state not in loc_tokens:
                    loc_tokens.append(state)
                all_locations_str = ", ".join(loc_tokens) if loc_tokens else "India"
                
                batch.append([comp_name, primary_city, state, all_locations_str, cin or ""])
                count += 1
                
            writer.writerows(batch)
            batch = []
            print(f"  Processed {count:,} companies...", flush=True)

    conn.close()
    elapsed = time.time() - start_time
    file_size_mb = OUTPUT_CSV.stat().st_size / (1024 * 1024)
    print(f"\n Export Complete!")
    print(f"  Total IT Companies exported: {count:,}")
    print(f"  Saved File: {OUTPUT_CSV}")
    print(f"  File Size: {file_size_mb:.2f} MB")
    print(f"  Time taken: {elapsed:.2f} seconds")

if __name__ == "__main__":
    main()
