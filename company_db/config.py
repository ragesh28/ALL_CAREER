import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Paths ──
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = Path(os.environ.get("COMPANY_DB_PATH", str(DATA_DIR / "company_master.db")))
DEFAULT_ALIASES_PATH = DATA_DIR / "company_aliases.json"
DEFAULT_PROGRESS_PATH = DATA_DIR / "mca_download_progress.json"

# ── Official data.gov.in API Configuration ──
# Resource: MCA Company Master Data (India)
MCA_RESOURCE_ID = "4dbe5667-7b6b-41d7-82af-211562424d9a"
MCA_API_BASE_URL = f"https://api.data.gov.in/resource/{MCA_RESOURCE_ID}"

# Important notice regarding dataset cutoff date
DATA_SOURCE_DATE = "2023-11-03"
DATA_SOURCE_DESCRIPTION = (
    "MCA Company Master Data via data.gov.in. "
    "Dataset updated on portal 22 July 2026; company registration records available up to 3 November 2023."
)

# ── Downloader / Client Settings ──
DEFAULT_API_LIMIT = 5000       # Standard page size supported by data.gov.in API
TEST_API_LIMIT = 10           # Initial sanity test limit
REQUEST_TIMEOUT_SECONDS = 30  # HTTP request timeout
MAX_RETRIES = 5               # Retries on 429/500/network errors
BACKOFF_FACTOR = 2.0          # Exponential backoff base (seconds)
BATCH_INSERT_SIZE = 2000      # SQLite bulk insert transaction batch size

# ── Matching & Confidence Thresholds ──
CONFIDENCE_HIGH = 0.95        # Exact or near-exact match
CONFIDENCE_MEDIUM = 0.85      # Strong fuzzy match (e.g. 1-character OCR typo) / alias match
CONFIDENCE_LOW = 0.75         # Partial / ambiguous match threshold
FTS5_CANDIDATE_LIMIT = 25     # Maximum candidates retrieved from FTS5 for RapidFuzz ranking


def get_api_key() -> str:
    """
    Retrieve data.gov.in API key from environment.
    Never logs or exposes the key value.
    """
    key = os.environ.get("DATA_GOV_API_KEY", "").strip()
    return key
