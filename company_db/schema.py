"""
SQLite Database Schema & FTS5 Index Definitions.
"""

SCHEMA_SQL = """
-- 1. Main Companies Table
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cin TEXT UNIQUE NOT NULL,
    company_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    company_status TEXT,
    company_class TEXT,
    company_category TEXT,
    date_of_registration TEXT,
    registered_state TEXT,
    roc TEXT,
    registered_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Indexes for High-Speed B-Tree Lookups
CREATE INDEX IF NOT EXISTS idx_companies_normalized_name ON companies(normalized_name);
CREATE INDEX IF NOT EXISTS idx_companies_cin ON companies(cin);
CREATE INDEX IF NOT EXISTS idx_companies_state ON companies(registered_state);

-- 3. Brand Aliases Table
CREATE TABLE IF NOT EXISTS company_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    cin TEXT,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL UNIQUE,
    canonical_name TEXT NOT NULL,
    source TEXT DEFAULT 'curated',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_aliases_norm ON company_aliases(normalized_alias);

-- 4. Database Metadata Table
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. SQLite FTS5 Full-Text & Prefix Search Virtual Table
CREATE VIRTUAL TABLE IF NOT EXISTS company_search USING fts5 (
    company_name,
    normalized_name,
    cin UNINDEXED,
    prefix='2,3,4,5,6',
    tokenize='unicode61 remove_diacritics 2'
);
"""

# FTS5 Synchronization Triggers
TRIGGERS_SQL = """
-- Trigger: Insert into FTS5 when a company is added
CREATE TRIGGER IF NOT EXISTS trg_companies_ai AFTER INSERT ON companies BEGIN
    INSERT INTO company_search(rowid, company_name, normalized_name, cin)
    VALUES (new.id, new.company_name, new.normalized_name, new.cin);
END;

-- Trigger: Delete from FTS5 when a company is deleted
CREATE TRIGGER IF NOT EXISTS trg_companies_ad AFTER DELETE ON companies BEGIN
    DELETE FROM company_search WHERE rowid = old.id;
END;

-- Trigger: Update FTS5 when a company is modified
CREATE TRIGGER IF NOT EXISTS trg_companies_au AFTER UPDATE ON companies BEGIN
    DELETE FROM company_search WHERE rowid = old.id;
    INSERT INTO company_search(rowid, company_name, normalized_name, cin)
    VALUES (new.id, new.company_name, new.normalized_name, new.cin);
END;
"""
