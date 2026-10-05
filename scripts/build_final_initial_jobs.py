import json
import os
import re

MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WALKIN_REGEX = re.compile(r'\b(walk[\s-]?in|walking[\s-]?interview|walkin|walk-in drive|direct interview)\b', re.IGNORECASE)

def clean_time_and_noise(text):
    if not text: return ""
    s = text
    s = re.sub(r'\b\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm)\b(?:\s*(?:-|–|—|to)\s*\b\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm)\b)?', ' ', s)
    s = re.sub(r'\b\d{1,2}[:.]\d{2}\b', ' ', s)
    s = re.sub(r'\b\d{1,2}\s*(?:-|–|to)\s*\d{1,2}\s*(?:years?|yrs?)\b', ' ', s, flags=re.I)
    s = re.sub(r'\b\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?\s*(?:lacs?|lpa|ctc)\b', ' ', s, flags=re.I)
    s = re.sub(r'\b(?:\+?91|0)?[6-9]\d{9}\b', ' ', s)
    return s

def extract_walkin_date_from_text(text):
    if not text or not isinstance(text, str): return None
    label_match = re.search(r'(?:walk[\s-]?in\s*(?:date|drive)?|interview\s*date|time\s*and\s*venue|date\s*&?\s*time)\s*[:\-]?\s*([^\n\r]+)', text, re.I)
    if label_match:
        candidate = label_match.group(1).strip()
        d_match = re.search(r'\b(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\s*(?:-|–|—|to|&)\s*\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}|\d{1,2}(?:st|nd|rd|th)?\s*(?:-|–|—|to|&)\s*\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}(?:\s*,?\s*\d{4})?|\d{1,2}[-/.](?:\d{1,2}|[A-Za-z]{3})[-/.]\d{2,4})\b', candidate, re.I)
        if d_match: return d_match.group(0).strip()
    
    range_both = re.search(r'\b(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\s*(?:-|–|—|to|&)\s*\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}(?:\s*,?\s*\d{4})?)\b', text, re.I)
    if range_both: return range_both.group(1).strip()
    
    range_same = re.search(r'\b(\d{1,2}(?:st|nd|rd|th)?\s*(?:-|–|—|to|&)\s*\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}(?:\s*,?\s*\d{4})?)\b', text, re.I)
    if range_same: return range_same.group(1).strip()
    
    single = re.search(r'\b(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}(?:\s*,?\s*\d{4})?)\b', text, re.I)
    if single: return single.group(1).strip()
    
    std = re.search(r'\b(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b', text)
    if std: return std.group(1).strip()
    return None

def parse_walkin_dates(raw_str):
    if not raw_str: return []
    text = clean_time_and_noise(str(raw_str).replace('_', ' '))
    text = re.sub(r'\b(\d{1,2}(?:st|nd|rd|th)?)([A-Za-z]{3,9})\b', r'\1 \2', text)
    
    results = []
    
    def get_month_idx(m_str):
        if not m_str: return -1
        s = m_str.lower()[:3]
        for idx, m in enumerate(MONTH_SHORT):
            if m.lower() == s: return idx
        return -1

    def add_d(y, m, d):
        if 0 <= m <= 11 and 1 <= d <= 31:
            lbl = f"{MONTH_SHORT[m]} {d}"
            if lbl not in results:
                results.append(lbl)

    iso = re.search(r'\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b', text)
    if iso:
        add_d(int(iso.group(1)), int(iso.group(2)) - 1, int(iso.group(3)))

    dmy = re.search(r'\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2}|\d{2})\b', text)
    if dmy:
        y = int(dmy.group(3))
        if y < 100: y += 2000
        add_d(y, int(dmy.group(2)) - 1, int(dmy.group(1)))

    dm = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?[-/\s]+([A-Za-z]{3,9})(?:[-/\s]+(20\d{2}|\d{2}))?\b', text)
    if dm:
        m_idx = get_month_idx(dm.group(2))
        if m_idx != -1:
            y = int(dm.group(3)) if dm.group(3) else 2026
            if y < 100: y += 2000
            add_d(y, m_idx, int(dm.group(1)))

    md = re.search(r'\b([A-Za-z]{3,9})[-/\s]+(\d{1,2})(?:st|nd|rd|th)?(?:[-/\s]+(20\d{2}|\d{2}))?\b', text)
    if md:
        m_idx = get_month_idx(md.group(1))
        if m_idx != -1:
            y = int(md.group(3)) if md.group(3) else 2026
            if y < 100: y += 2000
            add_d(y, m_idx, int(md.group(2)))

    rng_both = re.search(r'\b(\d{1,2})[-/\s]+([A-Za-z]{3,9})\s*(?:-|–|to)\s*(\d{1,2})[-/\s]+([A-Za-z]{3,9})\b', text, re.I)
    if rng_both:
        m1 = get_month_idx(rng_both.group(2))
        m2 = get_month_idx(rng_both.group(4))
        d1 = int(rng_both.group(1))
        d2 = int(rng_both.group(3))
        if m1 != -1 and m2 != -1:
            add_d(2026, m1, d1)
            add_d(2026, m2, d2)

    rng_same = re.search(r'\b(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s+([A-Za-z]{3,9})\b', text, re.I)
    if rng_same:
        m_idx = get_month_idx(rng_same.group(3))
        if m_idx != -1:
            d1 = int(rng_same.group(1))
            d2 = int(rng_same.group(2))
            for day in range(min(d1, d2), max(d1, d2) + 1):
                add_d(2026, m_idx, day)

    return results

def get_job_walkin_dates(j):
    raw = j.get('walkin_date') or ''
    if not raw:
        raw = extract_walkin_date_from_text(j.get('title') or '') or extract_walkin_date_from_text(j.get('description') or '') or ''
    if not raw:
        raw = j.get('date') or j.get('posted') or j.get('date_posted') or j.get('fetchedAt') or ''
    return parse_walkin_dates(raw)

def main():
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    init_path = os.path.join(workspace, 'all-career-app', 'public', 'data', 'initial_jobs.json')
    walkin_path = os.path.join(workspace, 'all-career-app', 'public', 'data', 'walkin_jobs.json')

    with open(init_path, 'r', encoding='utf-8') as f:
        init_jobs = json.load(f)

    with open(walkin_path, 'r', encoding='utf-8') as f:
        walkin_jobs = json.load(f)

    print(f"Loaded {len(init_jobs)} initial jobs and {len(walkin_jobs)} walkin jobs.")

    seen = set()
    combined = []

    # Process all walkin jobs first
    for j in walkin_jobs:
        src = str(j.get('source') or '').lower().strip()
        if 'google' in src or 'image' in src or j.get('flyer_image_url'):
            j['source'] = 'google_images'
        elif 'telegram' in src:
            j['source'] = 'telegram_post' if 'post' in src else 'telegram_message'
        j['is_walkin'] = True
        
        # Extract parsed walkin dates
        dates = get_job_walkin_dates(j)
        j['walkin_dates'] = dates
        if dates and not j.get('walkin_date'):
            j['walkin_date'] = dates[0]
        
        # Clean date
        if not j.get('date') or j.get('date') == 'Today':
            j['date'] = j.get('walkin_date') or j.get('date_posted') or 'Today'

        key = str(j.get('title')).lower() + '|||' + str(j.get('company')).lower() + '|||' + str(j.get('location')).lower()
        if key not in seen:
            seen.add(key)
            combined.append(j)

    # Process remaining initial jobs
    for j in init_jobs:
        src = str(j.get('source') or '').lower().strip()
        if 'google' in src or 'image' in src or j.get('flyer_image_url'):
            j['source'] = 'google_images'
        elif 'telegram' in src:
            j['source'] = 'telegram_post' if 'post' in src else 'telegram_message'
        
        title = str(j.get('title') or j.get('role') or '')
        desc = str(j.get('description') or j.get('other_details') or '')
        is_w = j.get('is_walkin') is True or WALKIN_REGEX.search(title) or WALKIN_REGEX.search(desc) or j['source'] == 'google_images'
        j['is_walkin'] = bool(is_w)
        if is_w:
            dates = get_job_walkin_dates(j)
            j['walkin_dates'] = dates
            if dates and not j.get('walkin_date'):
                j['walkin_date'] = dates[0]

        key = str(j.get('title')).lower() + '|||' + str(j.get('company')).lower() + '|||' + str(j.get('location')).lower()
        if key not in seen:
            seen.add(key)
            combined.append(j)

    print(f"Total combined jobs: {len(combined)}")

    # Save to initial_jobs.json
    with open(init_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f)
    print(f"Saved {len(combined)} jobs to {init_path} ({os.path.getsize(init_path)/1024/1024:.2f} MB).")

    # Also update walkin_jobs.json with the enriched walkin jobs
    all_walkins = [j for j in combined if j.get('is_walkin')]
    with open(walkin_path, 'w', encoding='utf-8') as f:
        json.dump(all_walkins, f)
    print(f"Saved {len(all_walkins)} walkin jobs to {walkin_path}.")

if __name__ == '__main__':
    main()
