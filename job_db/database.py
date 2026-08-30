"""
High-Performance SQLite Connection and Transaction Manager for ALL_CAREER.
"""
import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from contextlib import contextmanager

from .config import DEFAULT_JOB_DB_PATH, SQLITE_PRAGMAS
from .schema import SCHEMA_SQL, TRIGGERS_SQL


class JobDatabase:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_JOB_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory dimension caches for ultra-fast bulk imports
        self._companies_cache: Dict[str, int] = {}
        self._locations_cache: Dict[Tuple[str, str], int] = {}
        self._roles_cache: Dict[str, int] = {}
        self._sources_cache: Dict[str, int] = {}

        self.init_db()

    @contextmanager
    def get_connection(self):
        """Create an optimized connection with WAL mode and fast pragmas."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            for pragma in SQLITE_PRAGMAS:
                conn.execute(pragma)
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Initialize database schema, indexes, and triggers."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.executescript(TRIGGERS_SQL)
            conn.commit()
        self._preload_dimension_caches()

    def _preload_dimension_caches(self):
        """Preload ID lookups for companies, locations, roles, and sources."""
        with self.get_connection() as conn:
            for row in conn.execute("SELECT id, name FROM companies"):
                self._companies_cache[row["name"].upper().strip()] = row["id"]
            for row in conn.execute("SELECT id, city, state FROM locations"):
                self._locations_cache[(row["city"].lower().strip(), (row["state"] or "").lower().strip())] = row["id"]
            for row in conn.execute("SELECT id, name FROM roles"):
                self._roles_cache[row["name"].lower().strip()] = row["id"]
            for row in conn.execute("SELECT id, name FROM sources"):
                self._sources_cache[row["name"].lower().strip()] = row["id"]

    def get_or_create_company(self, name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        if not name:
            return None
        clean_name = str(name).strip()
        key = clean_name.upper()
        if key in self._companies_cache:
            return self._companies_cache[key]

        norm_name = clean_name.lower()
        if conn is None:
            with self.get_connection() as c:
                c.execute("INSERT OR IGNORE INTO companies(name, normalized_name) VALUES (?, ?)", (clean_name, norm_name))
                cid = c.execute("SELECT id FROM companies WHERE name = ?", (clean_name,)).fetchone()[0]
                c.commit()
        else:
            conn.execute("INSERT OR IGNORE INTO companies(name, normalized_name) VALUES (?, ?)", (clean_name, norm_name))
            cid = conn.execute("SELECT id FROM companies WHERE name = ?", (clean_name,)).fetchone()[0]

        self._companies_cache[key] = cid
        return cid

    def get_or_create_location(self, city: str, state: str = "", conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        if not city:
            return None
        clean_city = str(city).strip()
        clean_state = str(state).strip() if state else ""
        key = (clean_city.lower(), clean_state.lower())
        if key in self._locations_cache:
            return self._locations_cache[key]

        if conn is None:
            with self.get_connection() as c:
                c.execute("INSERT OR IGNORE INTO locations(city, state) VALUES (?, ?)", (clean_city, clean_state))
                lid = c.execute("SELECT id FROM locations WHERE city = ? AND (state = ? OR (state IS NULL AND ? = ''))", (clean_city, clean_state, clean_state)).fetchone()[0]
                c.commit()
        else:
            conn.execute("INSERT OR IGNORE INTO locations(city, state) VALUES (?, ?)", (clean_city, clean_state))
            lid = conn.execute("SELECT id FROM locations WHERE city = ? AND (state = ? OR (state IS NULL AND ? = ''))", (clean_city, clean_state, clean_state)).fetchone()[0]

        self._locations_cache[key] = lid
        return lid

    def get_or_create_role(self, name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        if not name:
            return None
        clean_name = str(name).strip()
        key = clean_name.lower()
        if key in self._roles_cache:
            return self._roles_cache[key]

        norm_name = clean_name.lower()
        if conn is None:
            with self.get_connection() as c:
                c.execute("INSERT OR IGNORE INTO roles(name, normalized_name) VALUES (?, ?)", (clean_name, norm_name))
                rid = c.execute("SELECT id FROM roles WHERE name = ?", (clean_name,)).fetchone()[0]
                c.commit()
        else:
            conn.execute("INSERT OR IGNORE INTO roles(name, normalized_name) VALUES (?, ?)", (clean_name, norm_name))
            rid = conn.execute("SELECT id FROM roles WHERE name = ?", (clean_name,)).fetchone()[0]

        self._roles_cache[key] = rid
        return rid

    def get_or_create_source(self, name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        if not name:
            return None
        clean_name = str(name).strip().lower()
        if clean_name in self._sources_cache:
            return self._sources_cache[clean_name]

        if conn is None:
            with self.get_connection() as c:
                c.execute("INSERT OR IGNORE INTO sources(name) VALUES (?, ?)", (clean_name,))
                sid = c.execute("SELECT id FROM sources WHERE name = ?", (clean_name,)).fetchone()[0]
                c.commit()
        else:
            conn.execute("INSERT OR IGNORE INTO sources(name) VALUES (?)", (clean_name,))
            sid = conn.execute("SELECT id FROM sources WHERE name = ?", (clean_name,)).fetchone()[0]

        self._sources_cache[clean_name] = sid
        return sid

    def optimize_db(self):
        """Optimize FTS5 index, run ANALYZE, and checkpoint WAL log."""
        with self.get_connection() as conn:
            try:
                conn.execute("INSERT INTO jobs_fts(jobs_fts) VALUES('optimize');")
            except Exception:
                pass
            conn.execute("ANALYZE;")
            conn.commit()
            try:
                conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        """Return total counts and file metrics."""
        with self.get_connection() as conn:
            j_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            c_count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
            l_count = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
            r_count = conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
            w_count = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_walkin = 1").fetchone()[0]

        size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0.0
        return {
            "total_jobs": j_count,
            "walkin_jobs": w_count,
            "total_companies": c_count,
            "total_locations": l_count,
            "total_roles": r_count,
            "db_size_mb": round(size_mb, 2),
            "db_path": str(self.db_path)
        }
