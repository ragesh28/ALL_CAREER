import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from company_db.resolver import CompanyResolver

resolver = CompanyResolver()
queries = [
    "jayvik labs",
    "IDA",
    "METASIT PRIVATE LIMITED",
    "TRIDIAGONAL SOFTWARE PRIVATE LIMITED",
    "sp accure labs private limited"
]

conn = sqlite3.connect("data/company_master.db")
conn.row_factory = sqlite3.Row

print("=" * 85)
print("🔍 MCA GOVERNMENT COMPANY MASTER DATA LOOKUP (3,674,322 COMPANIES)")
print("=" * 85)

for q in queries:
    print(f"\n🏢 Search Input: \"{q}\"")
    print("-" * 85)
    
    # 1. Exact Match
    clean_q = q.upper().strip()
    direct_row = conn.execute("SELECT * FROM companies WHERE company_name = ? OR normalized_name = ?", (clean_q, q.lower().strip())).fetchone()
    
    if direct_row:
        print(f"  ✅ EXACT OFFICIAL RECORD FOUND:")
        print(f"     • Official Name:     {direct_row['company_name']}")
        print(f"     • CIN Number:        {direct_row['cin']}")
        print(f"     • Company Status:    {direct_row['company_status']}")
        print(f"     • Registered State:  {direct_row['registered_state']}")
        print(f"     • Class / Category:  {direct_row['company_class']} / {direct_row['company_category']}")
        print(f"     • Registration Date: {direct_row['date_of_registration']}")
    else:
        # 2. Substring & FTS5 Prefix Lookup
        tokens = [t for t in q.replace('PRIVATE LIMITED', '').replace('PVT LTD', '').replace('LIMITED', '').replace('LTD', '').split() if len(t) >= 2]
        pattern = "%" + "%".join([t.lower() for t in tokens]) + "%"
        
        matches = conn.execute("SELECT * FROM companies WHERE normalized_name LIKE ? LIMIT 5", (pattern,)).fetchall()
        
        if not matches and len(tokens) >= 2:
            # Try matching individual key tokens
            main_token = "%" + tokens[0].lower() + "%"
            matches = conn.execute("SELECT * FROM companies WHERE normalized_name LIKE ? LIMIT 5", (main_token,)).fetchall()

        if matches:
            print(f"  ✅ MATCHES FOUND IN MCA DATABASE ({len(matches)} record(s)):")
            for r in matches:
                print(f"     👉 {r['company_name']}")
                print(f"        ├─ CIN:     {r['cin']}")
                print(f"        ├─ State:   {r['registered_state']}")
                print(f"        ├─ Status:  {r['company_status']}")
                print(f"        └─ Class:   {r['company_class']} (Reg: {r['date_of_registration']})")
        else:
            print(f"  ❌ NOT FOUND IN MCA MASTER LIST (No registered entity under this name)")
