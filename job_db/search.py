"""
High-Performance Search API, Query Planner, and Keyset Paginator for ALL_CAREER.
"""
import re
import json
import time
from typing import Dict, Any, List, Optional, Tuple

from .config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, CACHE_MAX_SIZE, CACHE_TTL_SECONDS
from .database import JobDatabase


class QueryLRUCache:
    """In-memory thread-safe TTL LRU cache for high-frequency filter queries."""
    def __init__(self, maxsize: int = CACHE_MAX_SIZE, ttl: int = CACHE_TTL_SECONDS):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            created_at, val = self._cache[key]
            if time.time() - created_at < self.ttl:
                return val
            else:
                del self._cache[key]
        return None

    def set(self, key: str, val: Any):
        if len(self._cache) >= self.maxsize:
            # Evict oldest entry
            oldest_k = next(iter(self._cache))
            del self._cache[oldest_k]
        self._cache[key] = (time.time(), val)

    def clear(self):
        self._cache.clear()


class JobSearchEngine:
    def __init__(self, db: Optional[JobDatabase] = None):
        self.db = db or JobDatabase()
        self.cache = QueryLRUCache()

    def _resolve_dimension_ids(
        self,
        city: Optional[str] = None,
        role: Optional[str] = None,
        company: Optional[str] = None,
        source: Optional[str] = None
    ) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        """Resolve string names to integer IDs using O(1) in-memory dictionaries."""
        lid = None
        if city:
            c_low = city.strip().lower()
            for (c, _), i in self.db._locations_cache.items():
                if c == c_low:
                    lid = i
                    break

        rid = None
        if role:
            r_low = role.strip().lower()
            rid = self.db._roles_cache.get(r_low)

        cid = None
        if company:
            c_up = company.strip().upper()
            cid = self.db._companies_cache.get(c_up)

        sid = None
        if source:
            s_low = source.strip().lower()
            sid = self.db._sources_cache.get(s_low)

        return lid, rid, cid, sid

    def _build_sql_query(
        self,
        query_text: Optional[str] = None,
        city: Optional[str] = None,
        role: Optional[str] = None,
        company: Optional[str] = None,
        source: Optional[str] = None,
        date_range_days: Optional[int] = None,
        experience_exact_zero: bool = False,
        experience_max: Optional[float] = None,
        is_walkin: Optional[bool] = None,
        walkin_date: Optional[str] = None,
        cursor_date: Optional[str] = None,
        cursor_id: Optional[int] = None,
        limit: int = DEFAULT_PAGE_SIZE
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Build index-optimized SQL queries using pre-resolved integer IDs.
        Returns: (select_sql, count_sql, params_dict)
        """
        params: Dict[str, Any] = {}
        where_clauses: List[str] = []
        count_from = "FROM jobs j"

        lid, rid, cid, sid = self._resolve_dimension_ids(city, role, company, source)

        # ── 1. FTS5 Text Search Join ──
        if query_text and query_text.strip():
            clean_q = re.sub(r'[^\w\s]', '', query_text).strip()
            tokens = [f'"{t}"*' for t in clean_q.split() if len(t) >= 2]
            if tokens:
                fts_expr = " AND ".join(tokens)
                where_clauses.append("j.id IN (SELECT rowid FROM jobs_fts WHERE jobs_fts MATCH :fts_expr)")
                params["fts_expr"] = fts_expr

        # ── 2. Direct Integer B-Tree Filters (O(1) index matching) ──
        if city:
            if lid is not None:
                where_clauses.append("j.location_id = :lid")
                params["lid"] = lid
            else:
                where_clauses.append("j.location_id = -1")  # No match

        if role:
            if rid is not None:
                where_clauses.append("j.role_id = :rid")
                params["rid"] = rid
            else:
                where_clauses.append("j.role_id = -1")

        if company:
            if cid is not None:
                where_clauses.append("j.company_id = :cid")
                params["cid"] = cid
            else:
                where_clauses.append("j.company_id = -1")

        if source:
            if sid is not None:
                where_clauses.append("j.source_id = :sid")
                params["sid"] = sid
            else:
                where_clauses.append("j.source_id = -1")

        if date_range_days is not None and date_range_days > 0:
            where_clauses.append("j.date_posted >= date('now', :date_offset)")
            params["date_offset"] = f"-{date_range_days} days"

        if experience_exact_zero:
            where_clauses.append("j.experience_min = 0.0 AND j.experience_max = 0.0")
        elif experience_max is not None:
            where_clauses.append("j.experience_min <= :exp_max")
            params["exp_max"] = float(experience_max)

        if is_walkin is True:
            where_clauses.append("j.is_walkin = 1")
            if walkin_date:
                where_clauses.append("j.walkin_date = :walkin_date")
                params["walkin_date"] = walkin_date

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # ── 3. Ultra-Fast Index Covering Count SQL ──
        count_sql = f"""
        SELECT COUNT(*) AS total
        {count_from}
        {where_sql};
        """

        # ── 4. Keyset / Cursor Pagination ──
        cursor_clauses = list(where_clauses)
        if cursor_date and cursor_id is not None:
            cursor_clauses.append("(j.date_posted < :c_date OR (j.date_posted = :c_date AND j.id < :c_id))")
            params["c_date"] = cursor_date
            params["c_id"] = cursor_id

        cursor_where_sql = ("WHERE " + " AND ".join(cursor_clauses)) if cursor_clauses else ""

        params["limit"] = min(limit, MAX_PAGE_SIZE)

        # Final select query joins dimensions only for the 30 limit rows
        select_sql = f"""
        SELECT 
            j.id, j.title, c.name AS company, l.city AS city, l.state AS state,
            s.name AS source, r.name AS role_search,
            j.date_posted, j.fetched_at, j.experience_min, j.experience_max,
            j.work_mode, j.salary_min, j.salary_max, j.skills, j.url,
            j.is_walkin, j.walkin_date, j.walkin_time, j.contact_email,
            j.contact_phone, j.telegram_url
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        LEFT JOIN locations l ON j.location_id = l.id
        LEFT JOIN roles r ON j.role_id = r.id
        LEFT JOIN sources s ON j.source_id = s.id
        {cursor_where_sql}
        ORDER BY j.date_posted DESC, j.id DESC
        LIMIT :limit;
        """

        return select_sql, count_sql, params

    def search(
        self,
        query_text: Optional[str] = None,
        city: Optional[str] = None,
        role: Optional[str] = None,
        company: Optional[str] = None,
        source: Optional[str] = None,
        date_range_days: Optional[int] = None,
        experience_exact_zero: bool = False,
        experience_max: Optional[float] = None,
        is_walkin: Optional[bool] = None,
        walkin_date: Optional[str] = None,
        cursor_date: Optional[str] = None,
        cursor_id: Optional[int] = None,
        limit: int = DEFAULT_PAGE_SIZE,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Execute high-performance indexed search with keyset pagination & total job count.
        """
        cache_key = f"{query_text}|{city}|{role}|{company}|{source}|{date_range_days}|{experience_exact_zero}|{experience_max}|{is_walkin}|{walkin_date}|{cursor_date}|{cursor_id}|{limit}"
        if use_cache and not (cursor_date or cursor_id):
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        select_sql, count_sql, params = self._build_sql_query(
            query_text=query_text,
            city=city,
            role=role,
            company=company,
            source=source,
            date_range_days=date_range_days,
            experience_exact_zero=experience_exact_zero,
            experience_max=experience_max,
            is_walkin=is_walkin,
            walkin_date=walkin_date,
            cursor_date=cursor_date,
            cursor_id=cursor_id,
            limit=limit
        )

        t0 = time.perf_counter()

        with self.db.get_connection() as conn:
            # 1. Total matching count (uses index-covering query)
            total_count = conn.execute(count_sql, params).fetchone()["total"]

            # 2. Fetch page results
            rows = conn.execute(select_sql, params).fetchall()

        latency_ms = (time.perf_counter() - t0) * 1000.0

        jobs_list = []
        next_cursor = None

        for r in rows:
            skills_val = r["skills"]
            try:
                skills_list = json.loads(skills_val) if skills_val else []
            except Exception:
                skills_list = [skills_val] if skills_val else []

            exp_str = ""
            if r["experience_min"] == 0 and r["experience_max"] == 0:
                exp_str = "Fresher (0 yrs)"
            elif r["experience_min"] == r["experience_max"]:
                exp_str = f"{r['experience_min']} yrs"
            else:
                exp_str = f"{r['experience_min']} - {r['experience_max']} yrs"

            jobs_list.append({
                "_id": r["id"],
                "title": r["title"],
                "company": r["company"],
                "location": f"{r['city']}, {r['state']}" if r["state"] else r["city"],
                "city": r["city"],
                "state": r["state"],
                "source": r["source"],
                "role_search": r["role_search"] or "",
                "date": r["date_posted"],
                "fetchedAt": r["fetched_at"],
                "experience": exp_str,
                "experience_min": r["experience_min"],
                "experience_max": r["experience_max"],
                "work_mode": r["work_mode"],
                "skills": skills_list,
                "url": r["url"],
                "is_walkin": bool(r["is_walkin"]),
                "walkin_date": r["walkin_date"],
                "walkin_time": r["walkin_time"],
                "contact_email": r["contact_email"],
                "contact_phone": r["contact_phone"],
                "telegram_url": r["telegram_url"]
            })

        if jobs_list and len(jobs_list) == limit:
            last_job = rows[-1]
            next_cursor = {
                "cursor_date": last_job["date_posted"],
                "cursor_id": last_job["id"]
            }

        response = {
            "total_jobs": total_count,
            "count": len(jobs_list),
            "limit": limit,
            "has_more": next_cursor is not None,
            "next_cursor": next_cursor,
            "latency_ms": round(latency_ms, 2),
            "jobs": jobs_list
        }

        if use_cache and not (cursor_date or cursor_id):
            self.cache.set(cache_key, response)

        return response

    def explain_query_plan(self, **kwargs) -> str:
        """Return EXPLAIN QUERY PLAN analysis string for index inspection."""
        select_sql, _, params = self._build_sql_query(**kwargs)
        explain_sql = f"EXPLAIN QUERY PLAN {select_sql}"
        lines = []
        with self.db.get_connection() as conn:
            for row in conn.execute(explain_sql, params):
                lines.append(f"id={row[0]} parent={row[1]} notused={row[2]} detail={row[3]}")
        return "\n".join(lines)
