"""
High-Throughput Batch Job Importer and Normalizer for ALL_CAREER.
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from .config import IMPORT_BATCH_SIZE
from .database import JobDatabase
from .deduplicator import compute_job_hash


def parse_experience_range(exp_val: Any) -> Tuple[float, float]:
    """Parse experience strings like '0-2 Yrs', '3 to 5 years', 'Fresher' into (min_exp, max_exp)."""
    if exp_val is None:
        return 0.0, 0.0
    s = str(exp_val).strip().lower()
    if not s or s in ('nan', 'none', 'null', 'not specified'):
        return 0.0, 0.0
    if 'fresher' in s or 'freshers' in s or s == '0':
        return 0.0, 0.0

    match_range = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)', s)
    if match_range:
        try:
            return float(match_range.group(1)), float(match_range.group(2))
        except ValueError:
            pass

    match_single = re.search(r'(\d+(?:\.\d+)?)', s)
    if match_single:
        try:
            val = float(match_single.group(1))
            return val, val
        except ValueError:
            pass

    return 0.0, 0.0


def parse_salary_range(salary_val: Any) -> Tuple[int, int]:
    """Parse salary values into integer range."""
    if salary_val is None:
        return 0, 0
    s = str(salary_val).strip().replace(',', '')
    match_range = re.findall(r'\b(\d{4,8})\b', s)
    if len(match_range) >= 2:
        try:
            return int(match_range[0]), int(match_range[1])
        except ValueError:
            pass
    return 0, 0


class JobImporter:
    def __init__(self, db: Optional[JobDatabase] = None):
        self.db = db or JobDatabase()

    def import_batch(self, jobs: List[Dict[str, Any]]) -> int:
        """
        Batch insert job records with deduplication inside a single transaction.
        Returns count of new records inserted.
        """
        if not jobs:
            return 0

        prepared_rows = []
        with self.db.get_connection() as conn:
            conn.execute("BEGIN TRANSACTION;")

            for job in jobs:
                title = str(job.get("title") or job.get("role") or "").strip()
                if not title:
                    continue

                company_name = str(job.get("company") or job.get("company_name") or "").strip()
                cid = self.db.get_or_create_company(company_name, conn=conn) if company_name else None

                loc_raw = str(job.get("location") or job.get("city") or "").strip()
                city = loc_raw.split(",")[0].strip() if loc_raw else ""
                state = loc_raw.split(",")[1].strip() if "," in loc_raw else ""
                lid = self.db.get_or_create_location(city, state, conn=conn) if city else None

                role_raw = str(job.get("role_search") or job.get("search_keyword") or "").strip()
                rid = self.db.get_or_create_role(role_raw, conn=conn) if role_raw else None

                src_raw = str(job.get("source") or job.get("platform") or "other").strip()
                sid = self.db.get_or_create_source(src_raw, conn=conn)

                job_hash = str(job.get("job_hash") or compute_job_hash(job))
                date_posted = str(job.get("date_posted") or job.get("date") or job.get("fetched_at") or "")[:10]
                fetched_at = str(job.get("fetched_at") or job.get("fetchedAt") or date_posted)
                
                exp_min, exp_max = parse_experience_range(job.get("experience"))
                work_mode = str(job.get("work_mode") or "")
                sal_min, sal_max = parse_salary_range(job.get("salary"))

                skills_data = job.get("skills", [])
                skills_str = json.dumps(skills_data) if isinstance(skills_data, list) else str(skills_data)

                url = str(job.get("url") or job.get("apply_link") or job.get("apply_url") or "")
                
                is_walk = 1 if bool(job.get("is_walkin") or job.get("walking_interview") or "walk" in title.lower()) else 0
                walk_date = str(job.get("walkin_date") or "")
                walk_time = str(job.get("walkin_time") or "")
                email = str(job.get("contact_email") or "")
                phone = str(job.get("contact_phone") or "")
                tg_url = str(job.get("telegram_url") or "")
                desc = str(job.get("description") or "")

                prepared_rows.append((
                    job_hash, title, cid, lid, rid, sid,
                    date_posted, fetched_at, exp_min, exp_max, work_mode,
                    sal_min, sal_max, skills_str, url, is_walk,
                    walk_date, walk_time, email, phone, tg_url, desc
                ))

            insert_sql = """
            INSERT OR IGNORE INTO jobs (
                job_hash, title, company_id, location_id, role_id, source_id,
                date_posted, fetched_at, experience_min, experience_max, work_mode,
                salary_min, salary_max, skills, url, is_walkin,
                walkin_date, walkin_time, contact_email, contact_phone, telegram_url, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """

            cursor = conn.cursor()
            cursor.executemany(insert_sql, prepared_rows)
            inserted_count = cursor.rowcount
            conn.commit()

        return inserted_count

    def import_from_json_file(self, json_path: Path) -> int:
        """Import jobs from a JSON file."""
        if not json_path.exists():
            return 0

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return 0

        total_inserted = 0
        for i in range(0, len(data), IMPORT_BATCH_SIZE):
            chunk = data[i:i + IMPORT_BATCH_SIZE]
            total_inserted += self.import_batch(chunk)

        return total_inserted
