"""
Deterministic Job Hashing and Deduplication Module.
"""
import re
import hashlib
from typing import Dict, Any


def normalize_string_for_hash(val: Any) -> str:
    """Lowercase and strip whitespace/punctuation for hashing."""
    if val is None:
        return ""
    s = str(val).lower().strip()
    return re.sub(r'[\s\W_]+', '', s)


def compute_job_hash(job: Dict[str, Any]) -> str:
    """
    Generate a deterministic, stable 32-character MD5 hash for a job posting.
    Uses: url (if unique job URL exists) or (title + company + city + source + date).
    """
    url = str(job.get("url") or job.get("apply_link") or job.get("apply_url") or "").strip()
    
    # Clean tracking query parameters from job URL for canonical matching
    if url and url.startswith("http"):
        clean_url = re.sub(r'[\?&](utm_[^&]+|ref=[^&]+|source=[^&]+)', '', url, flags=re.I)
        norm_url = clean_url.split("#")[0].strip()
        if len(norm_url) > 15:
            # Hash directly on clean unique URL
            return hashlib.md5(norm_url.encode("utf-8")).hexdigest()

    # Fallback to composite fingerprint
    title = normalize_string_for_hash(job.get("title") or job.get("role") or "")
    company = normalize_string_for_hash(job.get("company") or job.get("company_name") or "")
    location = normalize_string_for_hash(job.get("location") or job.get("city") or "")
    source = normalize_string_for_hash(job.get("source") or job.get("platform") or "")
    date_val = str(job.get("date_posted") or job.get("date") or job.get("fetched_at") or "")[:10]

    fingerprint = f"{company}|{title}|{location}|{source}|{date_val}"
    return hashlib.md5(fingerprint.encode("utf-8")).hexdigest()
