"""
Configuration for ALL_CAREER High-Performance Job Database Module.
"""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_JOB_DB_PATH = Path(os.environ.get("JOB_DB_PATH", str(DATA_DIR / "jobs_master.db")))

# SQLite Performance & Durability Pragmas
SQLITE_PRAGMAS = [
    "PRAGMA journal_mode = WAL;",         # Write-Ahead Logging for concurrent non-blocking reads
    "PRAGMA synchronous = NORMAL;",       # Safe ACID durability with high write speed
    "PRAGMA temp_store = MEMORY;",        # In-memory temporary tables & sorts
    "PRAGMA cache_size = -64000;",        # 64MB memory page cache
    "PRAGMA mmap_size = 268435456;",      # 256MB memory-mapped I/O for fast reads
    "PRAGMA foreign_keys = ON;",          # Relational integrity
]

# Importer & Batch Settings
IMPORT_BATCH_SIZE = 10000              # Rows per transaction during bulk import
FTS5_BATCH_REBUILD_THRESHOLD = 50000   # Optimize FTS index after large batch operations

# Search & Pagination Settings
DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100
CACHE_MAX_SIZE = 2048                 # In-memory LRU query cache size
CACHE_TTL_SECONDS = 300               # 5 minutes TTL
