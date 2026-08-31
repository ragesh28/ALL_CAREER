"""
SQLite Database Connection Manager & High-Performance FTS5 Operations.
"""
import os
import re
import json
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .config import DEFAULT_DB_PATH, DEFAULT_ALIASES_PATH, DATA_SOURCE_DESCRIPTION, DATA_SOURCE_DATE, FTS5_CANDIDATE_LIMIT
from .schema import SCHEMA_SQL, TRIGGERS_SQL
from .normalizer import CompanyNormalizer


from contextlib import contextmanager


class CompanyDatabase:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Only auto-reassemble for the main company_names.db file if missing
        if not self.db_path.exists() and self.db_path.name == "company_names.db":
            chunks_dir = self.db_path.parent / "company_names_chunks"
            if chunks_dir.exists() and list(chunks_dir.glob("company_names.part*")):
                try:
                    from scripts.split_company_db import reassemble_database
                    reassemble_database(chunks_dir, self.db_path)
                except Exception as e:
                    print(f"⚠️ Auto-reassemble note: {e}")

        self.init_db()

    @contextmanager
    def get_connection(self):
        """Create an optimized SQLite connection with WAL mode and fast pragmas, ensuring clean close."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            # Performance pragmas
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA cache_size = -64000;")  # 64MB memory cache
            conn.execute("PRAGMA temp_store = MEMORY;")
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Initialize tables, indexes, triggers, and seed metadata."""
        with self.get_connection() as conn:
            # Check existing tables and schema
            tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "companies" in tables:
                cols = [c[1] for c in conn.execute("PRAGMA table_info(companies)").fetchall()]
                if "company_name" in cols and "normalized_name" in cols:
                    conn.executescript(TRIGGERS_SQL)
            else:
                conn.executescript(SCHEMA_SQL)
                conn.executescript(TRIGGERS_SQL)
            
            # Ensure metadata table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Set default metadata if not set
            conn.execute(
                "INSERT OR IGNORE INTO metadata (key, value) VALUES (?, ?)",
                ("source_description", DATA_SOURCE_DESCRIPTION)
            )
            conn.execute(
                "INSERT OR IGNORE INTO metadata (key, value) VALUES (?, ?)",
                ("dataset_cutoff_date", DATA_SOURCE_DATE)
            )
            conn.commit()

        # Seed aliases if table is empty
        try:
            self.seed_aliases_if_empty()
        except Exception:
            pass

    def seed_aliases_if_empty(self, aliases_path: Optional[Path] = None):
        """Seed brand aliases and canonical companies from JSON file if company_aliases table is empty."""
        path = aliases_path or DEFAULT_ALIASES_PATH
        if not path.exists():
            return

        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM company_aliases")
            count = cursor.fetchone()[0]
            if count > 0:
                return  # Already seeded

            try:
                with open(path, "r", encoding="utf-8") as f:
                    alias_entries = json.load(f)

                alias_insert_data = []
                company_records = []

                for entry in alias_entries:
                    canonical = entry["canonical"]
                    cin = entry.get("cin") or f"SEED{abs(hash(canonical)) % 100000000:08d}"
                    source = entry.get("source", "curated")
                    company_records.append({
                        "cin": cin,
                        "company_name": canonical,
                        "company_status": "Active",
                        "registered_state": "India"
                    })

                    for alias in entry["aliases"]:
                        norm_alias = CompanyNormalizer.normalize_name(alias, strip_legal_suffix=False)
                        if norm_alias:
                            alias_insert_data.append((cin, alias, norm_alias, canonical, source))

                # Insert canonical companies
                self.upsert_batch(company_records)

                # Insert aliases
                conn.executemany(
                    """INSERT OR IGNORE INTO company_aliases 
                       (cin, alias, normalized_alias, canonical_name, source)
                       VALUES (?, ?, ?, ?, ?)""",
                    alias_insert_data
                )
                conn.commit()
            except Exception as e:
                print(f"⚠️ Warning: Could not seed company aliases: {e}")

    def upsert_batch(self, records: List[Dict[str, Any]]) -> int:
        """
        Batch upsert records into companies table within a single transaction.
        Uses CIN as the primary unique key.
        Returns count of affected records.
        """
        if not records:
            return 0

        prepared_data = []
        for r in records:
            cin = str(r.get("cin", "")).strip().upper()
            raw_name = str(r.get("company_name", "")).strip()
            if not cin or not raw_name:
                continue

            normalized_name = CompanyNormalizer.normalize_name(raw_name, strip_legal_suffix=True)
            status = r.get("company_status")
            c_class = r.get("company_class")
            cat = r.get("company_category")
            reg_date = r.get("date_of_registration")
            state = r.get("registered_state")
            roc = r.get("roc")
            addr = r.get("registered_address")

            prepared_data.append((
                cin, raw_name, normalized_name, status,
                c_class, cat, reg_date, state, roc, addr
            ))

        if not prepared_data:
            return 0

        sql = """
        INSERT INTO companies (
            cin, company_name, normalized_name, company_status,
            company_class, company_category, date_of_registration,
            registered_state, roc, registered_address, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(cin) DO UPDATE SET
            company_name = excluded.company_name,
            normalized_name = excluded.normalized_name,
            company_status = excluded.company_status,
            company_class = excluded.company_class,
            company_category = excluded.company_category,
            date_of_registration = excluded.date_of_registration,
            registered_state = excluded.registered_state,
            roc = excluded.roc,
            registered_address = excluded.registered_address,
            updated_at = CURRENT_TIMESTAMP;
        """

        with self.get_connection() as conn:
            conn.execute("BEGIN TRANSACTION;")
            conn.executemany(sql, prepared_data)
            conn.commit()

        return len(prepared_data)

    def exact_lookup(self, normalized_name: str) -> Optional[Dict[str, Any]]:
        """
        Ultra-fast O(1) indexed B-Tree lookup for exact normalized company name.
        """
        if not normalized_name:
            return None

        sql = """
        SELECT cin, company_name, normalized_name, company_status, registered_state
        FROM companies
        WHERE normalized_name = ?
        LIMIT 1;
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (normalized_name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def lookup_alias(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Check if query matches a curated brand alias (e.g. 'TCS' -> 'Tata Consultancy Services Limited').
        """
        norm_q = CompanyNormalizer.normalize_name(query, strip_legal_suffix=False)
        if not norm_q:
            return None

        sql = """
        SELECT cin, alias, canonical_name, source
        FROM company_aliases
        WHERE normalized_alias = ?
        LIMIT 1;
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (norm_q,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def search_fts5(self, query_tokens: List[str], limit: int = FTS5_CANDIDATE_LIMIT) -> List[Dict[str, Any]]:
        """
        Query SQLite FTS5 index using prefix matching on normalized tokens.
        Example: ['accenturf'] -> queries 'normalized_name:"accenturf"* OR normalized_name:"accentur"* OR normalized_name:"accen"*'
        Returns candidate list for downstream RapidFuzz ranking.
        """
        if not query_tokens:
            return []

        # Sanitize tokens (only alphanumeric)
        clean_tokens = [re.sub(r'[^a-zA-Z0-9]', '', t) for t in query_tokens if len(t) >= 2]
        if not clean_tokens:
            return []

        match_parts = []
        for t in clean_tokens:
            match_parts.append(f'normalized_name:"{t}"*')
            match_parts.append(f'company_name:"{t}"*')
            # For longer tokens (length >= 5), also add prefix roots to catch OCR typos (e.g. accenturf -> accentur*)
            if len(t) >= 5:
                match_parts.append(f'normalized_name:"{t[:-1]}"*')
                match_parts.append(f'normalized_name:"{t[:4]}"*')

        match_query = " OR ".join(match_parts)

        sql = """
        SELECT c.cin, c.company_name, c.normalized_name, c.company_status, c.registered_state,
               rank AS fts_rank
        FROM company_search cs
        JOIN companies c ON cs.rowid = c.id
        WHERE company_search MATCH ?
        ORDER BY rank
        LIMIT ?;
        """

        candidates = []
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(sql, (match_query, limit))
                for row in cursor.fetchall():
                    candidates.append(dict(row))
        except sqlite3.OperationalError:
            pass

        return candidates

    def get_stats(self) -> Dict[str, Any]:
        """Return database statistics (total records, file size, last update)."""
        with self.get_connection() as conn:
            c_count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
            a_count = conn.execute("SELECT COUNT(*) FROM company_aliases").fetchone()[0]
            last_up = conn.execute("SELECT MAX(updated_at) FROM companies").fetchone()[0]

        size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0.0
        return {
            "total_companies": c_count,
            "total_aliases": a_count,
            "db_size_mb": round(size_mb, 2),
            "db_path": str(self.db_path),
            "last_updated": last_up,
            "data_cutoff_date": DATA_SOURCE_DATE
        }
