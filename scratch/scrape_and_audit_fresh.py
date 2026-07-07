import os
import sys
import re
import json
import time
import datetime
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

# Ensure we can import curl_cffi
try:
    from curl_cffi import requests
except ImportError:
    import requests

from jobspy import scrape_jobs

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
SEARCH_TERMS = ["developer", "software engineer", "full stack", "react", "python"]
LOCATION = "India"
DAYS_LIMIT = 3
TARGET_JOBS_COUNT = 100

# ---------------------------------------------------------------------------
# KEYWORDS & PATTERNS
# ---------------------------------------------------------------------------
EXP_KEYWORDS = ['experience', 'experienced', 'year', 'years', 'yr', 'yrs', 'exp', 'range']
LEVEL_KEYWORDS = {
    'fresher': 'Fresher (0 years)',
    'freshers': 'Fresher (0 years)'
}

NUM_PATTERN = re.compile(
    r'(\b\d+(?:\+)?(?:\s*(?:-|–|—|~|to)\s*\d+(?:\+)?)?\+?)', 
    re.IGNORECASE
)

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def is_range_match(match_str):
    nums = re.findall(r'\d+', match_str)
    if len(nums) >= 2:
        if any(c in match_str.lower() for c in ['-', '–', '—', '~', 'to']):
            return True
    return False

def format_experience_ranges(ranges):
    if not ranges:
        return ""
    
    # Prioritize true range matches (e.g. 8-12)
    range_matches = [r for r in ranges if is_range_match(r)]
    if range_matches:
        unique_ranges = []
        seen = set()
        for r in range_matches:
            val = r.strip()
            norm = val.replace(" ", "").replace("–", "-").replace("—", "-").replace("~", "-").replace("to", "-")
            if norm not in seen:
                seen.add(norm)
                nums = re.findall(r'\d+', r)
                if len(nums) >= 2:
                    unique_ranges.append(f"{nums[0]} to {nums[1]}")
                else:
                    unique_ranges.append(r)
        return ", ".join(unique_ranges)

    # Fallback to minimum values range
    first_numbers = []
    for r in ranges:
        nums = [int(x) for x in re.findall(r'\d+', r)]
        if nums:
            first_numbers.append(nums[0])
    if not first_numbers:
        return ", ".join(ranges)
    unique_first_nums = sorted(list(set(first_numbers)))
    if len(unique_first_nums) == 1:
        return ranges[0]
    else:
        return f"{unique_first_nums[0]} to {unique_first_nums[-1]}"

def is_dirty_linkedin_page(text):
    text_lower = text.lower()
    indicators = [
        "skip to main content",
        "expand search",
        "this button displays the currently selected search type",
        "sign up | linkedin",
        "sign in to linkedin",
        "authwall"
    ]
    if "this button displays the currently selected search type" in text_lower:
        return True
    if sum(1 for ind in indicators if ind in text_lower) >= 2:
        return True
    return False

def extract_level_contexts(text, title):
    title_lower = title.lower()
    keywords = []
    if "senior" in title_lower or "sr." in title_lower or "sr " in title_lower or title_lower.startswith("sr "):
        keywords = ["senior", "sr"]
    elif "junior" in title_lower or "jr." in title_lower or "jr " in title_lower or title_lower.startswith("jr "):
        keywords = ["junior", "jr"]
    elif "lead" in title_lower or "principal" in title_lower or "staff" in title_lower:
        keywords = ["lead", "principal", "staff"]
    elif "intern" in title_lower or "internship" in title_lower:
        keywords = ["intern", "internship"]
    elif "fresher" in title_lower or "freshers" in title_lower or "trainee" in title_lower:
        keywords = ["fresher", "freshers", "trainee"]
    else:
        prof_kws = ["developer", "engineer", "analyst", "programmer", "consultant", "architect", "administrator", "specialist", "designer"]
        for pk in prof_kws:
            if pk in title_lower:
                keywords.append(pk)
        
    if not keywords:
        return []
        
    snippets = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines:
        line_lower = line.lower()
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', line_lower):
                snippets.append({
                    "matched": kw.capitalize() if kw == "sr" else kw,
                    "context": line
                })
                break
    if not snippets:
        snippets.append({
            "matched": "Job Title",
            "context": f"Experience level inferred from Job Title: {title}"
        })
    return snippets

def extract_experience(text):
    matches = list(NUM_PATTERN.finditer(text))
    raw_results = []
    for m in matches:
        matched_str = m.group(1)
        start, end = m.span()
        
        left_window = text[max(0, start - 20):start].lower()
        right_window = text[end:min(len(text), end + 20)].lower()
        
        has_exp_keyword = any(k in left_window or k in right_window for k in EXP_KEYWORDS)
        
        # Exclude education/qualification context references
        context_window = text[max(0, start - 50):min(len(text), end + 50)].lower()
        is_edu = any(w in context_window for w in ["education", "qualification", "degree", "academic", "study", "course", "school", "university", "college"])
        
        if has_exp_keyword and not is_edu:
            nums = [int(x) for x in re.findall(r'\d+', matched_str)]
            if nums and all(0 <= n <= 30 for n in nums):
                raw_results.append({
                    "matched": matched_str,
                    "context": text[max(0, start - 20):min(len(text), end + 20)].strip()
                })
            
    # Only keep the first extracted experience match to prevent multiple badges
    if raw_results:
        raw_results = [raw_results[0]]
        
    # We are no longer falling back to level keywords for experience
    return [], raw_results

def get_linkedin_description(job_id):
    url = f"https://www.linkedin.com/jobs/view/{job_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, impersonate="chrome", timeout=12)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            desc_div = soup.find(class_="show-more-less-html__markup") or soup.find(class_="description__text")
            if desc_div:
                return desc_div.get_text(separator="\n").strip()
            return soup.get_text(separator="\n").strip()
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------------
# MAIN WORKFLOW
# ---------------------------------------------------------------------------
def main():
    print(f"=== SCRAPING FRESH {TARGET_JOBS_COUNT} JOBS FROM LAST {DAYS_LIMIT} DAYS ===")
    
    today = datetime.date.today()
    cutoff_date = today - datetime.timedelta(days=DAYS_LIMIT)
    print(f"Cutoff Date: {cutoff_date} (Last {DAYS_LIMIT} days)")
    
    # 1. Load Job Listings from local JSON file
    scratch_dir = os.path.dirname(os.path.abspath(__file__))
    listings_path = os.path.join(scratch_dir, "fresh_job_listings.json")
    all_listings = []
    
    if os.path.exists(listings_path):
        with open(listings_path, "r", encoding="utf-8") as f:
            raw_listings = json.load(f)
        print(f"Loaded {len(raw_listings)} fresh listings from: {listings_path}")
        
        # Deduplicate by title and company
        seen_keys = set()
        for j in raw_listings:
            title = j.get("title", "").strip()
            company = j.get("company", "").strip()
            key = (title.lower(), company.lower())
            if key not in seen_keys:
                seen_keys.add(key)
                all_listings.append(j)
        print(f"Deduplicated to {len(all_listings)} unique listings.")
    else:
        print(f"[ERROR] Listings file not found: {listings_path}")
        
    for j in all_listings:
        j["date_posted"] = str(today)
        
    # Crop to target count
    all_listings = all_listings[:TARGET_JOBS_COUNT]
    print(f"\nTotal fresh listings to scrape: {len(all_listings)}")
    
    # 2. Scrape job descriptions (with caching)
    cache_path = os.path.join(scratch_dir, "scraped_descriptions_cache_batch3.json")
    cached_descriptions = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                for item in cached_data:
                    cached_descriptions[item["url"]] = item["description"]
            print(f"Loaded {len(cached_descriptions)} descriptions from cache.")
        except Exception as e:
            print(f"Failed to load cache: {e}")

    all_scraped_data = []
    for idx, job in enumerate(all_listings):
        url = job["url"]
        
        # Check cache first
        if url in cached_descriptions:
            print(f"[{idx+1}/{len(all_listings)}] Using cached description for: {job['title']} @ {job['company']}")
            all_scraped_data.append({
                "title": job["title"],
                "company": job["company"],
                "url": url,
                "platform": "LinkedIn",
                "description": cached_descriptions[url],
                "date_posted": job["date_posted"]
            })
            continue
            
        print(f"[{idx+1}/{len(all_listings)}] Scraping: {job['title']} @ {job['company']}...")
        
        # Extract job ID
        match = re.search(r'/view/(\d+)', url) or re.search(r'-(\d+)\??', url) or re.search(r'currentJobId=(\d+)', url)
        if not match:
            continue
            
        job_id = match.group(1)
        desc = get_linkedin_description(job_id)
        if desc:
            all_scraped_data.append({
                "title": job["title"],
                "company": job["company"],
                "url": url,
                "platform": "LinkedIn",
                "description": desc,
                "date_posted": job["date_posted"]
            })
            time.sleep(1) # Gentle throttling
        
    print(f"\nScraped {len(all_scraped_data)} job descriptions.")
    
    # Save cache
    scratch_dir = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(scratch_dir, "scraped_descriptions_cache_batch3.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_scraped_data, f, ensure_ascii=False, indent=2)
    print(f"Saved database to: {cache_path}")
    
    # 3. Analyze and Parse
    html_jobs = []
    missing_exp_count = 0
    exp_found_count = 0
    
    for job in all_scraped_data:
        desc = job["description"]
        title = job["title"]
        levels, exp_matches = [], []
        
        if not is_dirty_linkedin_page(desc):
            levels, exp_matches = extract_experience(desc)
            
        # We are no longer using TitleFallback to infer experience level
        # This ensures ONLY explicit numeric experience ranges are shown
                
        # Format experience range for dashboard
        formatted_exp = format_experience_ranges([m["matched"] for m in exp_matches])
        if formatted_exp and not any(c.isdigit() for c in formatted_exp):
            formatted_exp = ""
            
        # Extract minimum years
        min_years = None
        if exp_matches:
            first_numbers = []
            for m in exp_matches:
                nums = [int(x) for x in re.findall(r'\d+', m["matched"])]
                if nums:
                    first_numbers.append(nums[0])
            if first_numbers:
                min_years = min(first_numbers)
        elif levels and any("fresher" in l.lower() for l in levels):
            min_years = 0
            
        has_exp = bool(levels or exp_matches)
        if has_exp:
            exp_found_count += 1
        else:
            missing_exp_count += 1
            
        html_jobs.append({
            "title": job["title"],
            "company": job["company"],
            "url": job["url"],
            "platform": job["platform"],
            "levels": ", ".join(levels),
            "ranges": formatted_exp,
            "min_years": min_years,
            "exp_contexts": [m["context"] for m in exp_matches],
            "salaries": "",
            "sal_contexts": [],
            "has_exp": has_exp,
            "has_sal": False,
            "date_posted": job["date_posted"]
        })
        
    # --- WEB FILTER: ONLY SHOW JOBS THAT HAVE EXPERIENCE ---
    html_jobs = [j for j in html_jobs if j["has_exp"]]
    print(f"Filtered to keep {len(html_jobs)} jobs with experience (removed {missing_exp_count} jobs without experience).")
    
    # 4. Generate Dashboard HTML
    dashboard_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Experience Extraction Audit Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #0B0F19;
            --bg-card: #151D30;
            --accent-primary: #4F46E5;
            --accent-primary-glow: rgba(79, 70, 229, 0.4);
            --text-main: #F3F4F6;
            --text-muted: #9CA3AF;
            --border-color: rgba(255, 255, 255, 0.08);
            --badge-bg: rgba(79, 70, 229, 0.15);
            --badge-text: #818CF8;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background: var(--bg-main);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            padding: 2rem;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            margin-bottom: 2.5rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
        }}

        .title-wrapper {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #FFF 30%, #818CF8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        .subtitle {{
            color: var(--text-muted);
            font-size: 1.1rem;
        }}

        .stats-summary {{
            display: flex;
            gap: 1rem;
        }}

        .stat-badge {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 0.5rem 1.2rem;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-main);
        }}

        .controls-panel {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .search-row {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}

        .search-box {{
            flex: 1;
            background: rgba(0,0,0,0.2);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 0.8rem 1.2rem;
            border-radius: 12px;
            font-size: 1rem;
            font-family: inherit;
            outline: none;
            transition: all 0.2s;
        }}

        .search-box:focus {{
            border-color: var(--accent-primary);
            box-shadow: 0 0 10px var(--accent-primary-glow);
        }}

        .select-input {{
            background: rgba(0,0,0,0.2);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 0.8rem 1.2rem;
            border-radius: 12px;
            font-size: 1rem;
            font-family: inherit;
            outline: none;
            cursor: pointer;
        }}

        .filters-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1.5rem;
        }}

        .filter-tabs {{
            display: flex;
            gap: 0.5rem;
        }}

        .tab-btn {{
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 0.6rem 1.2rem;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }}

        .tab-btn:hover, .tab-btn.active {{
            background: var(--accent-primary);
            color: var(--text-main);
            border-color: var(--accent-primary);
            box-shadow: 0 0 10px var(--accent-primary-glow);
        }}

        .slider-wrapper {{
            display: flex;
            align-items: center;
            gap: 1rem;
            background: rgba(0,0,0,0.2);
            padding: 0.5rem 1.2rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }}

        .slider-label {{
            font-size: 0.9rem;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .slider-input {{
            width: 150px;
            cursor: pointer;
            accent-color: var(--accent-primary);
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 1.5rem;
        }}

        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 250px;
            cursor: pointer;
        }}

        .card:hover {{
            transform: translateY(-5px);
            border-color: var(--accent-primary);
            box-shadow: 0 15px 30px rgba(79, 70, 229, 0.15);
        }}

        .card-header {{
            margin-bottom: 1rem;
        }}

        .card-title {{
            font-size: 1.2rem;
            font-weight: 600;
            line-height: 1.4;
            margin-bottom: 0.25rem;
            color: var(--text-main);
        }}

        .card-company {{
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .platform-tag {{
            font-size: 0.75rem;
            font-weight: 800;
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            text-transform: uppercase;
        }}

        .platform-linkedin {{
            background: rgba(10, 102, 194, 0.15);
            color: #0A66C2;
            border: 1px solid rgba(10, 102, 194, 0.3);
        }}

        .platform-indeed {{
            background: rgba(33, 111, 237, 0.15);
            color: #216FED;
            border: 1px solid rgba(33, 111, 237, 0.3);
        }}

        .badges-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }}

        .badge {{
            background: var(--badge-bg);
            color: var(--badge-text);
            padding: 0.35rem 0.8rem;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            border: 1px solid rgba(79, 70, 229, 0.2);
        }}

        .snippets-container {{
            margin-top: 1rem;
            border-top: 1px solid rgba(255,255,255,0.05);
            padding-top: 1rem;
            display: block; /* Always show reference context */
        }}

        .snippet-block {{
            margin-bottom: 0.75rem;
        }}

        .snippet-block strong {{
            font-size: 0.8rem;
            color: var(--text-muted);
            display: block;
            margin-bottom: 0.25rem;
        }}

        .snippet-list {{
            background: rgba(0,0,0,0.2);
            padding: 0.6rem;
            border-radius: 8px;
            font-size: 0.8rem;
            color: var(--text-muted);
            line-height: 1.4;
            max-height: 120px;
            overflow-y: auto;
        }}

        .snippet-list span.hl-exp {{
            background: rgba(79, 70, 229, 0.3);
            color: #E0E7FF;
            padding: 0.05rem 0.2rem;
            border-radius: 3px;
            font-weight: 600;
        }}

        .card-footer {{
            border-top: 1px solid rgba(255,255,255,0.05);
            padding-top: 0.75rem;
            margin-top: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .post-link {{
            background: transparent;
            border: 1px solid var(--accent-primary);
            color: var(--text-main);
            padding: 0.4rem 1rem;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s;
        }}

        .post-link:hover {{
            background: var(--accent-primary);
            box-shadow: 0 0 10px var(--accent-primary-glow);
        }}
        
        .posted-date {{
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="title-wrapper">
                <div>
                    <h1>Fresh Experience Audit Dashboard</h1>
                    <div class="subtitle">Scraped and filtered jobs from the last {DAYS_LIMIT} days with experience details</div>
                </div>
                <div class="stats-summary">
                    <div class="stat-badge" id="totalJobsStat">Jobs showing: 0</div>
                </div>
            </div>
        </header>

        <div class="controls-panel">
            <div class="search-row">
                <input type="text" id="searchBar" class="search-box" placeholder="Search by job title, company, or experience..." oninput="applyFilters()">
                <select id="platformSelect" class="select-input" onchange="applyFilters()">
                    <option value="all">All Platforms</option>
                    <option value="LinkedIn">LinkedIn Only</option>
                </select>
            </div>
            
            <div class="filters-row">
                <div class="filter-tabs">
                    <button id="tabAll" class="tab-btn active" onclick="setFilterMode('all')">All Jobs</button>
                    <button id="tabExperience" class="tab-btn" onclick="setFilterMode('experience')">Experience Only</button>
                </div>

                <div class="slider-wrapper">
                    <span class="slider-label">Max Min-Exp:</span>
                    <input type="range" id="expSlider" class="slider-input" min="-1" max="15" value="-1" oninput="applyFilters()">
                    <span class="slider-label" id="expSliderVal" style="min-width: 50px; text-align: right;">All</span>
                </div>
            </div>
        </div>

        <div class="grid" id="jobsGrid">
            <!-- Rendered by JS -->
        </div>
    </div>

    <script>
        const jobsData = {json.dumps(html_jobs, indent=2)};
        let activeFilterMode = 'all';

        function setFilterMode(mode) {{
            activeFilterMode = mode;
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            if (mode === 'all') document.getElementById('tabAll').classList.add('active');
            if (mode === 'experience') document.getElementById('tabExperience').classList.add('active');
            applyFilters();
        }}

        function highlightMatch(context, matches, typeClass) {{
            if (!context || !matches) return context;
            let hlText = context;
            const terms = matches.split(',').map(t => t.trim()).filter(Boolean);
            
            terms.forEach(term => {{
                const firstPart = term.split(' ')[0].replace(/[-\/\\^$*+?.()|[\]{{}}]/g, '\\$&').trim();
                if (!firstPart) return;
                try {{
                    const regex = new RegExp(`(${{firstPart}})`, 'gi');
                    hlText = hlText.replace(regex, `<span class="${{typeClass}}">$1</span>`);
                }} catch(e) {{}}
            }});
            return hlText;
        }}

        function applyFilters() {{
            const searchVal = document.getElementById('searchBar').value.toLowerCase().trim();
            const platformVal = document.getElementById('platformSelect').value;
            const expLimit = parseInt(document.getElementById('expSlider').value, 10);
            
            const sliderLabel = document.getElementById('expSliderVal');
            if (expLimit === -1) {{
                sliderLabel.textContent = 'All';
            }} else if (expLimit === 0) {{
                sliderLabel.textContent = 'Fresher';
            }} else {{
                sliderLabel.textContent = expLimit + ' Yrs';
            }}

            const filtered = jobsData.filter(job => {{
                const matchQuery = 
                    job.title.toLowerCase().includes(searchVal) ||
                    job.company.toLowerCase().includes(searchVal) ||
                    (job.ranges && job.ranges.toLowerCase().includes(searchVal)) ||
                    (job.levels && job.levels.toLowerCase().includes(searchVal));
                
                const matchPlatform = platformVal === 'all' || job.platform === platformVal;

                let matchMode = true;
                if (activeFilterMode === 'experience') matchMode = job.has_exp;

                let matchSlider = true;
                if (expLimit !== -1) {{
                    if (job.min_years === null) {{
                        matchSlider = false;
                    }} else {{
                        matchSlider = job.min_years <= expLimit;
                    }}
                }}

                return matchQuery && matchPlatform && matchMode && matchSlider;
            }});

            const grid = document.getElementById('jobsGrid');
            grid.innerHTML = '';

            document.getElementById('totalJobsStat').textContent = 'Jobs showing: ' + filtered.length;

            if (filtered.length === 0) {{
                grid.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; padding: 4rem; color: var(--text-muted);">
                        <h3>No matching jobs found</h3>
                        <p style="margin-top: 0.5rem; font-size: 0.9rem;">Try adjusting your filters or search query.</p>
                    </div>`;
                return;
            }}

            filtered.forEach((job, idx) => {{
                let badgeHTML = '';
                if (job.levels) {{
                    badgeHTML += `<span class="badge">${{job.levels}}</span>`;
                }}
                if (job.ranges) {{
                    badgeHTML += `<span class="badge">Years: ${{job.ranges}}</span>`;
                }}

                let snippetsHTML = '';
                if (job.exp_contexts && job.exp_contexts.length > 0) {{
                    snippetsHTML += `
                        <div class="snippet-block">
                            <strong>Experience Mentions:</strong>
                            <div class="snippet-list">`;
                    job.exp_contexts.forEach(hl => {{
                        const highlighted = highlightMatch(hl, job.ranges || job.levels, 'hl-exp');
                        snippetsHTML += `<div>... ${{highlighted}} ...</div>`;
                    }});
                    snippetsHTML += `</div></div>`;
                }}

                if (snippetsHTML) {{
                    snippetsHTML = `<div class="snippets-container">${{snippetsHTML}}</div>`;
                }}

                const platformClass = job.platform === 'LinkedIn' ? 'platform-linkedin' : 'platform-indeed';

                const cardHTML = `
                    <div class="card" id="card-${{idx}}" onclick="toggleCard(this)">
                        <div class="card-header">
                            <div class="card-title">${{job.title}}</div>
                            <div class="card-company">
                                <span>${{job.company}}</span>
                                <span class="platform-tag ${{platformClass}}">${{job.platform}}</span>
                            </div>
                            <div class="badges-container">
                                ${{badgeHTML}}
                            </div>
                            ${{snippetsHTML}}
                        </div>
                        <div class="card-footer" onclick="event.stopPropagation();">
                            <span class="posted-date">Posted: ${{job.date_posted}}</span>
                            <a href="${{job.url}}" target="_blank" class="post-link">View Job Post</a>
                        </div>
                    </div>
                `;
                grid.insertAdjacentHTML('beforeend', cardHTML);
            }});
        }}

        function toggleCard(card) {{
            card.classList.toggle('expanded');
        }}

        // Initial Load
        applyFilters();
    </script>
</body>
</html>
"""
    
    # Save HTML
    html_path = os.path.join(scratch_dir, "experience_audit_dashboard.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(dashboard_html)
    print(f"Saved HTML Dashboard to: {html_path}")
    
    # Write reports
    with open(os.path.join(scratch_dir, "missing_experience_jobs.txt"), "w", encoding="utf-8") as f:
        for job in html_jobs:
            if not job["has_exp"]:
                f.write(f"Title: {job['title']} | Company: {job['company']} | URL: {job['url']}\n")
                
    with open(os.path.join(scratch_dir, "extracted_experience.txt"), "w", encoding="utf-8") as f:
        for job in html_jobs:
            if job["has_exp"]:
                f.write(f"Title: {job['title']} | Company: {job['company']} | URL: {job['url']}\n")
                f.write(f"Levels: {job['levels']} | Ranges: {job['ranges']}\n")
                for ctx in job["exp_contexts"]:
                    f.write(f"  - Context: {ctx}\n")
                f.write("="*40 + "\n")
                
    print("\n============================================================")
    print("  AUDIT REPORT STATISTICS (BATCH 3)")
    print("============================================================")
    print(f"  Total Scraped Jobs             : {len(all_scraped_data)}")
    print(f"  Experience FOUND & SHOWING     : {exp_found_count}")
    print(f"  Experience NOT FOUND & REMOVED : {missing_exp_count}")
    print("============================================================")

if __name__ == "__main__":
    main()
