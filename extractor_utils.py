import re
from skills_dictionary import SKILLS_DICT

def extract_experience(description):
    """
    Extract experience requirements from job description text.
    Returns a clean string like '2-5 Yrs', '3+ Yrs', 'Fresher', or ''.
    Only extracts the experience part, omitting any surrounding context.
    """
    if not description or not isinstance(description, str):
        return ""
        
    s = description.lower()
    
    # 1. Check for fresher keywords
    if re.search(r'\b(fresher|freshers|entry level|no experience required|no experience needed)\b', s):
        # Double check it doesn't say "not for freshers"
        if not re.search(r'\b(not\s+(?:for|open\s+to)\s+freshers?|no\s+freshers?)\b', s):
            return "Fresher"
            
    # 2. Look for experience ranges or years
    # Matches:
    # "3-5 years", "2 to 5 Yrs", "1 - 3 year", "5+ years", "10+ Yrs", "2 years"
    pattern = r'\b(\d+)\s*(?:-|to|\+)?\s*(\d*)\s*(?:year|yr|Yr)s?\b'
    matches = re.finditer(pattern, description, re.IGNORECASE)
    
    # We want to find the first reasonable match in the text
    for match in matches:
        full_match = match.group(0)
        min_val = int(match.group(1))
        max_val_str = match.group(2)
        
        # Guard: limit max experience to 30 years to avoid matching phone numbers or zip codes
        if min_val > 25:
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
            context = description[start:end+2]
            if "+" in context:
                return f"{min_val}+ Yrs"
            return f"{min_val} Yrs"
            
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
