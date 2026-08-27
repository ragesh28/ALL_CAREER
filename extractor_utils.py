import re
from skills_dictionary import SKILLS_DICT

# Word-to-number mapping for 0–30 (used by extract_experience)
_WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30,
}
# Add compound numbers: twenty-one through twenty-nine (with hyphen and space forms)
for _ones_word, _ones_val in [("one",1),("two",2),("three",3),("four",4),("five",5),
                               ("six",6),("seven",7),("eight",8),("nine",9)]:
    _WORD_TO_NUM[f"twenty {_ones_word}"] = 20 + _ones_val
    _WORD_TO_NUM[f"twenty-{_ones_word}"] = 20 + _ones_val

# Build regex pattern: match longest words first to avoid partial matches
# e.g. "twenty five" before "twenty" and before "five"
_WORD_NUM_PATTERN = re.compile(
    r'\b(' + '|'.join(
        re.escape(w) for w in sorted(_WORD_TO_NUM.keys(), key=len, reverse=True)
    ) + r')\b',
    re.IGNORECASE
)

def _replace_word_numbers(text):
    """Replace English word-numbers (zero–thirty) with their digit equivalents.
    Also converts the word 'plus' to '+' so '3 plus years' becomes '3+ years'."""
    def _repl(m):
        return str(_WORD_TO_NUM[m.group(0).lower()])
    result = _WORD_NUM_PATTERN.sub(_repl, text)
    # Convert "plus" to "+" so "3 plus years" → "3+ years"
    result = re.sub(r'\bplus\b', '+', result, flags=re.IGNORECASE)
    return result


PHONE_REGEX = re.compile(
    r'(?:\+?91[\-\s]?)?(?:[6-9]\d{9}|[6-9]\d{4}[\-\s]\d{5}|[6-9]\d{2}[\-\s]\d{3}[\-\s]\d{4})\b'
)

def extract_phone_number(text):
    """
    Extract 10-digit Indian mobile/phone numbers (+91 XXXXX XXXXX).
    """
    if not text or not isinstance(text, str):
        return ""
    match = PHONE_REGEX.search(text)
    if match:
        raw_phone = match.group(0).strip()
        clean = re.sub(r'[^\d+]', '', raw_phone)
        if len(clean) == 10:
            return f"+91 {clean[:5]} {clean[5:]}"
        elif len(clean) == 12 and clean.startswith("91"):
            return f"+91 {clean[2:7]} {clean[7:]}"
        elif clean.startswith("+91") and len(clean) == 13:
            return f"+91 {clean[3:8]} {clean[8:]}"
        return raw_phone
    return ""


def extract_experience(description, title=""):
    """
    Extract experience requirements from job description (and optionally title).
    Returns a clean string like '2-5 Yrs', '3+ Yrs', 'Fresher', 'Lead', 'Senior', or ''.

    **Priority order:**
    1. Numeric experience from description (e.g. "7+ years", "3-5 Yrs")
    2. Seniority keywords from title + description as fallback only

    Supports both digit numbers ("3-5 years") and English word numbers
    ("seven years", "five to ten years") in the range 0–30.
    """
    if (not description or not isinstance(description, str)) and not title:
        return ""
    description = description or ""

    # ── STEP 1: Try to extract a numeric experience value (HIGHEST PRIORITY) ──
    # Convert word-numbers to digits so the regex can match them
    #    e.g. "seven years of experience" → "7 years of experience"
    converted = _replace_word_numbers(description)

    # Look for experience ranges or years
    # Matches:
    # "3-5 years", "2 to 5 Yrs", "1 - 3 year", "5+ years", "10+ Yrs", "2 years"
    pattern = r'\b(\d+)\s*(?:-|to|\+)?\s*(\d*)\s*(?:year|yr|Yr)s?\b'
    matches = re.finditer(pattern, converted, re.IGNORECASE)

    # We want to find the first reasonable match in the text
    for match in matches:
        full_match = match.group(0)
        min_val = int(match.group(1))
        max_val_str = match.group(2)

        # Guard: limit max experience to 30 years to avoid matching phone numbers or zip codes
        if min_val > 30:
            continue

        # Determine format
        if "+" in full_match:
            return f"{min_val}+ Yrs"
        elif max_val_str:
            try:
                max_val = int(max_val_str)
                if max_val <= 30:
                    return f"{min_val}-{max_val} Yrs"
            except ValueError:
                pass
        else:
            # Check if "+" is just outside the match (e.g. "3 + years")
            # Or if it's "3 years+"
            start, end = match.span()
            context = converted[start:end+2]
            if "+" in context:
                return f"{min_val}+ Yrs"
            return f"{min_val} Yrs"

    # ── STEP 2: No number found — fall back to seniority keywords ──
    # Combine title + description for keyword search
    combined = ((title or "") + " " + description).lower()

    # Check for fresher keywords
    if re.search(r'\b(fresher|freshers|entry[\s-]?level|no experience required|no experience needed)\b', combined):
        # Double check it doesn't say "not for freshers"
        if not re.search(r'\b(not\s+(?:for|open\s+to)\s+freshers?|no\s+freshers?)\b', combined):
            return "Fresher"

    # Check for intern keywords (but exclude "non-internship" which means NOT an intern)
    if re.search(r'\b(intern|internship|trainee|apprentice)\b', combined):
        if not re.search(r'\bnon[-\s]?internship\b', combined):
            return "Intern"

    # Check for seniority keywords (only from title to avoid false positives in descriptions)
    title_lower = (title or "").lower()
    if title_lower:
        if re.search(r'\b(principal|staff|distinguished|fellow)\b', title_lower):
            return "Principal"
        if re.search(r'\b(lead|tech\s*lead|team\s*lead)\b', title_lower):
            return "Lead"
        if re.search(r'\b(senior|sr\.?)\b', title_lower):
            return "Senior"
        if re.search(r'\b(manager|director|head|vp|vice\s*president)\b', title_lower):
            return "Manager"

    return ""

def extract_skills(text):
    """
    Search text for technical and non-technical skills from SKILLS_DICT.
    Returns a list of unique matched skill IDs.
    """
    if not text or not isinstance(text, str):
        return []
        
    s = text.lower()
    matched_ids = set()
    
    for skill_name, info in SKILLS_DICT.items():
        skill_id = info["id"]
        for synonym in info["synonyms"]:
            # Use word boundaries to avoid partial matches
            # Handle special characters like C++ and .NET safely by escaping
            escaped = synonym
            # Special check: if synonym ends or starts with special chars, word boundaries \b might fail in python's re
            # E.g. "c++" -> re.escape("c++") is "c\+\+"
            # If we do \bc\+\+\b, it won't match because "+" is not a word character.
            # So for special chars, we use custom boundary patterns:
            if "+" in synonym or "#" in synonym or "." in synonym:
                # Custom boundary matching: not preceded or followed by alphanumeric
                pattern = r'(?<![a-zA-Z0-9])' + escaped + r'(?![a-zA-Z0-9])'
            else:
                pattern = r'\b' + escaped + r'\b'
                
            if re.search(pattern, s):
                matched_ids.add(skill_id)
                break  # Matched this skill, no need to check other synonyms for it
                
    return sorted(list(matched_ids))


# ══════════════════════════════════════════════════════════════════════════════
#  WALK-IN INTERVIEW & DATE EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

WALKIN_REGEX = re.compile(
    r'\b(walk[\s-]?in|walking[\s-]?interview|walk[\s-]?in[\s-]?drive|direct[\s-]?walkin|walkin)\b',
    re.IGNORECASE
)

MONTHS = (
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
)

# 1. Date Ranges with Month Names (e.g. "21st August - 30 September", "12th Aug - 15th Aug", "25th July")
DATE_RANGE_REGEX = re.compile(
    rf'\b(\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,\s*\d{{1,2}}(?:st|nd|rd|th)?)*(?:\s+{MONTHS})?'
    rf'\s*(?:-|–|—|to|&)\s*'
    rf'\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}(?:\s*,?\s*(?:20\d{{2}}|19\d{{2}}|\b\d{{2}}\b(?!\s*[:.])))?)\b',
    re.IGNORECASE
)

# 2. Single Date with Month Name (e.g. "25th July", "24th August 2026", "9th July", "13-May-26")
SINGLE_DATE_REGEX = re.compile(
    rf'\b(\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}(?:\s*,?\s*(?:20\d{{2}}|19\d{{2}}|\b\d{{2}}\b(?!\s*[:.])))?|'
    rf'\d{{1,2}}-{MONTHS}-\d{{2,4}})\b',
    re.IGNORECASE
)

# 3. Numeric Date Ranges or Single Dates (e.g. "15/08/2026 to 18/08/2026", "24-08-2026")
NUMERIC_DATE_REGEX = re.compile(
    r'\b(\d{1,2}[-/.](?:\d{1,2}|[A-Za-z]{3})[-/.]\d{2,4}(?:\s*(?:-|–|to)\s*\d{1,2}[-/.](?:\d{1,2}|[A-Za-z]{3})[-/.]\d{2,4})?)\b',
    re.IGNORECASE
)

# 4. Weekday Ranges (e.g. "Monday to Friday")
WEEKDAY_REGEX = re.compile(
    r'\b((?:Every\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)'
    r'(?:\s*(?:-|–|to|&)\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun))?)\b',
    re.IGNORECASE
)

# 5. Time Patterns (e.g. "11.00 AM - 5.30 PM", "9:30 AM to 4:00 PM")
TIME_REGEX = re.compile(
    r'\b(\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm)\s*(?:-|–|to)\s*\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm)|\d{1,2}(?:[:.]\d{2})?\s*(?:AM|PM|am|pm)(?:\s+onwards)?)\b'
)


def _clean_walkin_text(text):
    if not text or not isinstance(text, str):
        return ""
    text = text.replace('\xa0', ' ').replace('\u00a0', ' ').replace('\u2013', '-').replace('\u2014', '-')
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def extract_walkin_info(title="", description="", full_text=""):
    """
    Extract walk-in status, interview dates, and timings from job data.
    Returns:
        dict: {
            "is_walkin": bool,
            "walkin_date": str or None,
            "walkin_time": str or None,
            "matched_snippet": str
        }
    """
    title_clean = _clean_walkin_text(title)
    desc_clean = _clean_walkin_text(description)
    full_clean = _clean_walkin_text(full_text)
    combined = f"{title_clean}\n{desc_clean}\n{full_clean}".strip()

    if not combined:
        return {"is_walkin": False, "walkin_date": None, "walkin_time": None, "matched_snippet": ""}

    is_walkin = False
    walkin_date = None
    walkin_time = None
    matched_snippet = ""

    # 1. Detect if Walk-in
    if WALKIN_REGEX.search(title_clean) or WALKIN_REGEX.search(combined):
        is_walkin = True

    # 2. Contextual search around headers like "Time and Venue", "Walk-in Date:", "Drive on"
    context_patterns = [
        r'(?:Time and Venue|Time & Venue|Walk-in Date|Interview Date|Drive Date|Date & Time|Date\s*:|Venue & Date|Walkin on|Drive on)[^\n\r]+',
        r'(?:Time and Venue[\s\S]{1,250}?(?:AM|PM|\d{4}))',
        r'(?:Date\s*:\s*[^\n\r]+)',
    ]

    for cp in context_patterns:
        m = re.search(cp, combined, re.IGNORECASE)
        if m:
            matched_snippet = _clean_walkin_text(m.group(0))
            d_range = DATE_RANGE_REGEX.search(matched_snippet)
            if d_range:
                walkin_date = d_range.group(1).strip()
                break
            d_single = SINGLE_DATE_REGEX.search(matched_snippet)
            if d_single:
                walkin_date = d_single.group(1).strip()
                break
            d_num = NUMERIC_DATE_REGEX.search(matched_snippet)
            if d_num:
                walkin_date = d_num.group(1).strip()
                break

    # 3. If not in header, search in title then entire combined text
    if not walkin_date:
        for target_text in [title_clean, combined]:
            d_range = DATE_RANGE_REGEX.search(target_text)
            if d_range:
                walkin_date = d_range.group(1).strip()
                if not matched_snippet:
                    matched_snippet = d_range.group(0)
                break

            d_single = SINGLE_DATE_REGEX.search(target_text)
            if d_single:
                walkin_date = d_single.group(1).strip()
                if not matched_snippet:
                    matched_snippet = d_single.group(0)
                break

            d_num = NUMERIC_DATE_REGEX.search(target_text)
            if d_num:
                walkin_date = d_num.group(1).strip()
                if not matched_snippet:
                    matched_snippet = d_num.group(0)
                break

    # 4. Check for Weekday ranges (e.g. "Monday to Friday")
    if not walkin_date and is_walkin:
        wk = WEEKDAY_REGEX.search(combined)
        if wk:
            walkin_date = wk.group(1).strip()

    # 5. Extract time
    t_match = TIME_REGEX.search(matched_snippet or combined)
    if t_match:
        walkin_time = t_match.group(1).strip()

    return {
        "is_walkin": is_walkin,
        "walkin_date": walkin_date,
        "walkin_time": walkin_time,
        "matched_snippet": matched_snippet
    }

