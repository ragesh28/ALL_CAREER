import glob
import json
import re
import os

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALKIN_REGEX = re.compile(r'\b(walk[\s-]?in|walking[\s-]?interview|walkin|walk-in drive|direct interview)\b', re.IGNORECASE)

def extract_date(text):
    if not text:
        return ""
    # Matches patterns like: 19-Sep-26, 19-Sept-2026, 22nd Aug, 2026-09-22, 05-Sep-26, etc.
    m = re.search(r'\b(\d{1,2}(?:st|nd|rd|th)?[-/\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*[-/\s]*(?:\d{2,4})?|\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b', text, re.I)
    return m.group(0).strip() if m else ""

def main():
    seen_keys = set()
    all_walkins = []

    # 1. First load shards from data/jobs
    shards = glob.glob(os.path.join(WORKSPACE_DIR, 'data', 'jobs', '**', '*.json'), recursive=True)
    print(f"Scanning {len(shards)} shards in data/jobs/...")
    
    for sf in shards:
        try:
            with open(sf, 'r', encoding='utf-8', errors='ignore') as f:
                jobs = json.load(f)
                if not isinstance(jobs, list):
                    continue
                for j in jobs:
                    title = str(j.get('title') or j.get('role') or '')
                    desc = str(j.get('description') or j.get('other_details') or '')
                    src = str(j.get('source') or j.get('platform') or '').lower().strip()
                    if not src:
                        base = os.path.basename(sf)
                        src = base.split('_')[0].lower()
                    
                    is_walk = False
                    if 'google' in src or 'image' in src or j.get('flyer_image_url'):
                        is_walk = True
                    elif WALKIN_REGEX.search(title) or WALKIN_REGEX.search(desc) or j.get('is_walkin') is True:
                        is_walk = True
                    
                    if is_walk:
                        j['source'] = src
                        # Normalize date if missing
                        if not j.get('walkin_date'):
                            d = extract_date(title) or extract_date(desc)
                            if d:
                                j['walkin_date'] = d
                        if not j.get('date'):
                            j['date'] = j.get('walkin_date') or j.get('posted') or j.get('fetched_at') or 'Today'
                        
                        key = j.get('url') or (title.lower() + '|||' + str(j.get('company')).lower() + '|||' + str(j.get('location')).lower())
                        if key not in seen_keys:
                            seen_keys.add(key)
                            all_walkins.append(j)
        except Exception:
            pass

    print(f"Loaded {len(all_walkins)} unique walkin jobs from shards.")

    # 2. Load scraped_image_walkin_jobs.json
    img_path = os.path.join(WORKSPACE_DIR, 'scraped_image_walkin_jobs.json')
    if os.path.exists(img_path):
        with open(img_path, 'r', encoding='utf-8', errors='ignore') as f:
            img_jobs = json.load(f)
            for j in img_jobs:
                j['source'] = 'google_images'
                if not j.get('date'):
                    j['date'] = j.get('walkin_date') or '2026-09-22'
                key = j.get('url') or j.get('flyer_image_url') or (str(j.get('title')).lower() + '|||' + str(j.get('company')).lower())
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_walkins.append(j)
        print(f"Total after adding image walk-ins: {len(all_walkins)}")

    # 3. Source counts
    sources = {}
    for j in all_walkins:
        s = j.get('source') or 'other'
        sources[s] = sources.get(s, 0) + 1

    print("Source distribution in all_walkins:")
    print(json.dumps(sources, indent=2))

    # Save to all-career-app/public/data/walkin_jobs.json
    out_dir = os.path.join(WORKSPACE_DIR, 'all-career-app', 'public', 'data')
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'walkin_jobs.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(all_walkins, f, indent=None)
    print(f"Saved {len(all_walkins)} walkin jobs to {out_file} ({os.path.getsize(out_file) / 1024 / 1024:.2f} MB).")

    # Also save to data/index/walkin_jobs.json so all sources stay updated
    idx_file = os.path.join(WORKSPACE_DIR, 'data', 'index', 'walkin_jobs.json')
    with open(idx_file, 'w', encoding='utf-8') as f:
        json.dump(all_walkins, f, indent=None)
    print(f"Saved to {idx_file}.")

if __name__ == '__main__':
    main()
