"""
Download job portal logos and save to logos/portals/ directory.
"""
import os
import sys
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

LOGOS_DIR = os.path.join(os.path.dirname(__file__), "logos", "portals")
os.makedirs(LOGOS_DIR, exist_ok=True)

# Job portals with their official domain names (used for Clearbit + fallback)
PORTALS = {
    "linkedin":       "linkedin.com",
    "indeed":         "indeed.com",
    "naukri":         "naukri.com",
    "internshala":    "internshala.com",
    "glassdoor":      "glassdoor.com",
    "shine":          "shine.com",
    "timesjobs":      "timesjobs.com",
    "hirist":         "hirist.tech",
    "workindia":      "workindia.in",
    "foundit":        "foundit.in",
    "apna":           "apna.co",
    "freshersworld":  "freshersworld.com",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def try_download(url, filepath, label):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and len(r.content) > 500:
            with open(filepath, "wb") as f:
                f.write(r.content)
            print(f"  ✅ {label} → saved ({len(r.content)} bytes)")
            return True
        else:
            print(f"  ⚠️  {label} → status {r.status_code}, size {len(r.content)} (skipped)")
            return False
    except Exception as e:
        print(f"  ❌ {label} → error: {e}")
        return False

for name, domain in PORTALS.items():
    print(f"\n📦 Fetching: {name} ({domain})")
    
    png_path = os.path.join(LOGOS_DIR, f"{name}.png")
    ico_path = os.path.join(LOGOS_DIR, f"{name}.ico")
    
    if os.path.exists(png_path):
        print(f"  ⏭️  Already exists: {png_path}")
        continue

    # Try 1: Clearbit (high quality PNG)
    clearbit_url = f"https://logo.clearbit.com/{domain}"
    if try_download(clearbit_url, png_path, f"Clearbit PNG for {name}"):
        time.sleep(0.5)
        continue

    # Try 2: Google Favicons (128px)
    google_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    if try_download(google_url, png_path, f"Google favicon for {name}"):
        time.sleep(0.5)
        continue
    
    # Try 3: DuckDuckGo favicon
    ddg_url = f"https://icons.duckduckgo.com/ip3/{domain}.ico"
    if try_download(ddg_url, ico_path, f"DDG favicon for {name}"):
        time.sleep(0.5)
        continue
    
    print(f"  ❌ Failed all sources for {name}")
    time.sleep(0.5)

print("\n\n✅ Done! All logos saved to:", LOGOS_DIR)
print("Files:")
for f in sorted(os.listdir(LOGOS_DIR)):
    full = os.path.join(LOGOS_DIR, f)
    print(f"  {f} ({os.path.getsize(full):,} bytes)")
