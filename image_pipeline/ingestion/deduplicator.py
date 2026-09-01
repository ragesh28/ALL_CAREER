"""
Multi-Layer Job & Poster Flyer Deduplication Engine.
Prevents duplicate jobs from being scraped or added across multiple runs/days.
Layers:
1. URL & Raw Image Byte Hash (MD5/SHA-256)
2. Perceptual Image Hashing (pHash with Hamming distance threshold)
3. Normalized Semantic Signatures (Company + Location + Role + Date + Contact Email/Phone)
"""
import re
import hashlib
from typing import Dict, List, Optional, Set, Tuple
from PIL import Image
import io

try:
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False


def normalize_string(text: Optional[str]) -> str:
    """Strip punctuation, lowercase, and collapse whitespace."""
    if not text:
        return ""
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', str(text).lower())
    # Remove common company suffix noise for strict company matching
    clean = re.sub(r'\b(pvt|ltd|private|limited|llp|inc|corp|company|services|solutions|technologies|group)\b', '', clean)
    return " ".join(clean.split())


def normalize_phone(phone: Optional[str]) -> str:
    """Extract only the last 10 digits of a phone number."""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_email(email: Optional[str]) -> str:
    """Normalize email address."""
    if not email:
        return ""
    return str(email).lower().strip()


class JobDeduplicator:
    """High-speed in-memory & persistent deduplication engine for walk-in jobs."""

    def __init__(self, existing_jobs: Optional[List[Dict]] = None, phash_threshold: int = 6):
        self.phash_threshold = phash_threshold
        self.seen_urls: Set[str] = set()
        self.seen_md5s: Set[str] = set()
        self.seen_phashes: List[str] = []
        self.seen_signatures: Set[str] = set()
        self.seen_email_keys: Set[str] = set()
        self.seen_phone_keys: Set[str] = set()

        if existing_jobs:
            for job in existing_jobs:
                self.index_existing_job(job)

    def index_existing_job(self, job: Dict):
        """Index a job record into all deduplication lookup tables."""
        # 1. URL & Hashes
        url = job.get("flyer_image_url") or job.get("url") or job.get("raw_flyer_src") or job.get("source_url")
        if url and isinstance(url, str):
            self.seen_urls.add(url.strip())

        raw_md5 = job.get("image_hash") or job.get("dedup_hash")
        if raw_md5:
            self.seen_md5s.add(str(raw_md5))

        ph = job.get("phash")
        if ph and ph not in self.seen_phashes:
            self.seen_phashes.append(str(ph))

        # 2. Extract normalized components
        co = ""
        if isinstance(job.get("company"), dict):
            co = job["company"].get("canonical") or job["company"].get("name") or ""
        else:
            co = job.get("company_canonical") or job.get("company") or ""
        co_norm = normalize_string(co)

        loc = ""
        if isinstance(job.get("location"), dict):
            loc = job["location"].get("city") or ""
        else:
            loc = str(job.get("location") or "").split(",")[0]
        loc_norm = normalize_string(loc)

        role = ""
        if job.get("roles") and isinstance(job["roles"], list) and len(job["roles"]) > 0:
            role = job["roles"][0] if isinstance(job["roles"][0], str) else job["roles"][0].get("name", "")
        else:
            role = str(job.get("title") or "")
        role_norm = normalize_string(role)

        date_norm = normalize_string(job.get("walkin_date") or job.get("date") or "")
        email_norm = normalize_email(job.get("contact_email"))
        phone_norm = normalize_phone(job.get("contact_phone"))

        # 3. Register composite signatures
        if co_norm and loc_norm:
            # Match company + city + role
            self.seen_signatures.add(f"co_loc_role:{co_norm}|{loc_norm}|{role_norm}")
            # Match company + city + date
            if date_norm:
                self.seen_signatures.add(f"co_loc_date:{co_norm}|{loc_norm}|{date_norm}")

        if co_norm and email_norm:
            self.seen_email_keys.add(f"co_email:{co_norm}|{email_norm}")

        if co_norm and phone_norm:
            self.seen_phone_keys.add(f"co_phone:{co_norm}|{phone_norm}")

        if email_norm and date_norm:
            self.seen_email_keys.add(f"email_date:{email_norm}|{date_norm}")

    def is_image_duplicate(self, image_bytes: bytes, url: Optional[str] = None) -> Tuple[bool, str]:
        """
        Fast pre-check before running heavy OCR:
        Returns: (is_duplicate: bool, reason: str)
        """
        if url and url in self.seen_urls:
            return True, f"Exact URL duplicate: {url[:60]}"

        if not image_bytes:
            return False, ""

        # Check MD5 byte hash
        md5_hash = hashlib.md5(image_bytes).hexdigest()
        if md5_hash in self.seen_md5s:
            return True, f"Exact byte MD5 duplicate: {md5_hash}"

        # Check perceptual hash
        if HAS_IMAGEHASH:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                ph = str(imagehash.phash(img))
                h1 = imagehash.hex_to_hash(ph)
                for existing_ph in self.seen_phashes:
                    h2 = imagehash.hex_to_hash(existing_ph)
                    if (h1 - h2) <= self.phash_threshold:
                        return True, f"Visual perceptual pHash duplicate (distance: {h1 - h2})"
            except Exception:
                pass

        return False, ""

    def is_job_duplicate(
        self,
        company: Optional[str],
        title: Optional[str],
        roles: Optional[List[str]] = None,
        location: Optional[str] = None,
        walkin_date: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Post-extraction verification before adding to dataset:
        Returns: (is_duplicate: bool, reason: str)
        """
        co_norm = normalize_string(company)
        loc_norm = normalize_string(location)
        role = (roles[0] if roles else title) or ""
        role_norm = normalize_string(role)
        date_norm = normalize_string(walkin_date)
        email_norm = normalize_email(contact_email)
        phone_norm = normalize_phone(contact_phone)

        # Check Company + Contact Email match
        if co_norm and email_norm and f"co_email:{co_norm}|{email_norm}" in self.seen_email_keys:
            return True, f"Duplicate job by company & email: {co_norm} ({email_norm})"

        # Check Company + Contact Phone match
        if co_norm and phone_norm and f"co_phone:{co_norm}|{phone_norm}" in self.seen_phone_keys:
            return True, f"Duplicate job by company & phone: {co_norm} ({phone_norm})"

        # Check Email + Date match
        if email_norm and date_norm and f"email_date:{email_norm}|{date_norm}" in self.seen_email_keys:
            return True, f"Duplicate job by email & date: {email_norm} on {date_norm}"

        # Check Company + City + Date match
        if co_norm and loc_norm and date_norm and f"co_loc_date:{co_norm}|{loc_norm}|{date_norm}" in self.seen_signatures:
            return True, f"Duplicate drive by company, city & date: {co_norm} in {loc_norm} ({date_norm})"

        # Check Company + City + Role match
        if co_norm and loc_norm and role_norm and f"co_loc_role:{co_norm}|{loc_norm}|{role_norm}" in self.seen_signatures:
            return True, f"Duplicate job by company, city & role: {co_norm} for {role_norm}"

        return False, ""

    def register_new_job(
        self,
        job_record: Dict,
        image_bytes: Optional[bytes] = None,
        url: Optional[str] = None
    ):
        """Register newly verified job into deduplicator state."""
        if url:
            self.seen_urls.add(url.strip())

        if image_bytes:
            md5_hash = hashlib.md5(image_bytes).hexdigest()
            self.seen_md5s.add(md5_hash)
            job_record["image_hash"] = md5_hash
            if HAS_IMAGEHASH:
                try:
                    img = Image.open(io.BytesIO(image_bytes))
                    ph = str(imagehash.phash(img))
                    self.seen_phashes.append(ph)
                    job_record["phash"] = ph
                except Exception:
                    pass

        self.index_existing_job(job_record)
