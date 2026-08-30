"""
Database Schema, B-Tree Indexes, and FTS5 Definitions for ALL_CAREER.
"""

SCHEMA_SQL = """
-- 1. Normalized Reference Tables
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    normalized_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    state TEXT,
    UNIQUE(city, state)
);

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    normalized_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- 2. Core Jobs Table
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_hash TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company_id INTEGER REFERENCES companies(id),
    location_id INTEGER REFERENCES locations(id),
    role_id INTEGER REFERENCES roles(id),
    source_id INTEGER REFERENCES sources(id),
    date_posted TEXT,
    fetched_at TEXT,
    experience_min REAL DEFAULT 0.0,
    experience_max REAL DEFAULT 0.0,
    work_mode TEXT,
    salary_min INTEGER DEFAULT 0,
    salary_max INTEGER DEFAULT 0,
    skills TEXT,
    url TEXT,
    is_walkin INTEGER DEFAULT 0,
    walkin_date TEXT,
    walkin_time TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    telegram_url TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. High-Performance B-Tree Composite Indexes
-- Fast Keyset / Cursor Pagination (date_posted DESC, id DESC)
CREATE INDEX IF NOT EXISTS idx_jobs_date_id ON jobs(date_posted DESC, id DESC);

-- Targeted Multi-Filter Composite Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_loc_role_date ON jobs(location_id, role_id, date_posted DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_loc_role_source_date ON jobs(location_id, role_id, source_id, date_posted DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_loc_date ON jobs(location_id, date_posted DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_role_date ON jobs(role_id, date_posted DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_source_date ON jobs(source_id, date_posted DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_company_date ON jobs(company_id, date_posted DESC, id DESC);

-- Walk-in Interview Index
CREATE INDEX IF NOT EXISTS idx_jobs_walkin_loc_date ON jobs(is_walkin, location_id, walkin_date, date_posted DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_walkin ON jobs(is_walkin, walkin_date, date_posted DESC, id DESC);

-- Experience Filter Index
CREATE INDEX IF NOT EXISTS idx_jobs_exp ON jobs(experience_min, experience_max, date_posted DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_loc_exp ON jobs(location_id, experience_max, date_posted DESC, id DESC);

-- Hash index for ultra-fast O(1) deduplication
CREATE INDEX IF NOT EXISTS idx_jobs_hash ON jobs(job_hash);

-- Dimension Lookup Indexes
CREATE INDEX IF NOT EXISTS idx_comp_norm ON companies(normalized_name);
CREATE INDEX IF NOT EXISTS idx_loc_city ON locations(city COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_role_norm ON roles(normalized_name);
CREATE INDEX IF NOT EXISTS idx_source_name ON sources(name COLLATE NOCASE);

-- 4. SQLite FTS5 Full-Text & Prefix Search Virtual Table (External Content)
CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5 (
    title,
    skills,
    description,
    content='jobs',
    content_rowid='id',
    prefix='2,3,4',
    tokenize='unicode61 remove_diacritics 2'
);
"""

TRIGGERS_SQL = """
-- Automated FTS5 Synchronization Triggers
CREATE TRIGGER IF NOT EXISTS trg_jobs_ai AFTER INSERT ON jobs BEGIN
    INSERT INTO jobs_fts(rowid, title, skills, description)
    VALUES (new.id, new.title, new.skills, new.description);
END;

CREATE TRIGGER IF NOT EXISTS trg_jobs_ad AFTER DELETE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, skills, description)
    VALUES ('delete', old.id, old.title, old.skills, old.description);
END;

CREATE TRIGGER IF NOT EXISTS trg_jobs_au AFTER UPDATE ON jobs BEGIN
    INSERT INTO jobs_fts(jobs_fts, rowid, title, skills, description)
    VALUES ('delete', old.id, old.title, old.skills, old.description);
    INSERT INTO jobs_fts(rowid, title, skills, description)
    VALUES (new.id, new.title, new.skills, new.description);
END;
"""
