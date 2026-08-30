# 🏢 ALL_CAREER — MCA Company Database Module

A high-performance local SQLite database and fuzzy company name resolver powered by the official **Government of India Ministry of Corporate Affairs (MCA) Company Master Data** via `data.gov.in`.

---

## 🎯 Architecture & Objective

1. **Zero API Calls During Normal Flyer / Image Processing**: The `data.gov.in` API is used strictly for offline construction and periodic database synchronization. All image/OCR company resolutions happen **100% locally** in under **5 milliseconds** per image.
2. **Multi-Stage Resolution Pipeline**:
   - **Stage 1**: Curated Brand Aliases Table lookup ($O(1)$ B-Tree).
   - **Stage 2**: Exact Normalized Name lookup on SQLite Index ($O(1)$ B-Tree).
   - **Stage 3**: SQLite **FTS5** Prefix Virtual Index query (retrieves 5–25 candidates).
   - **Stage 4**: **RapidFuzz** re-ranking on the candidate set only (never a full table scan!).
   - **Stage 5**: Confidence scoring (High $\ge 0.95$, Medium $0.85 - 0.94$, Low/Uncertain $< 0.85$).

---

## 📅 Official Dataset Information & Limitations

> [!IMPORTANT]
> **Source**: `https://api.data.gov.in/resource/4dbe5667-7b6b-41d7-82af-211562424d9a`  
> **Catalog Update Date**: 22 July 2026  
> **Dataset Cutoff Note**: The official catalog states that company registration records are available up to **3 November 2023**. New companies registered after this cutoff will be resolved using brand aliases, legal suffix heuristics, or multimodal AI fallback.

---

## 🔑 Configuration & Environment Variables

The system **never hardcodes or logs API keys**. Configure `DATA_GOV_API_KEY` via your environment:

### Windows PowerShell:
```powershell
$env:DATA_GOV_API_KEY = "your_data_gov_in_api_key_here"
```

### Linux / macOS:
```bash
export DATA_GOV_API_KEY="your_data_gov_in_api_key_here"
```

### GitHub Actions Secrets:
Add `DATA_GOV_API_KEY` under **Repository Settings → Secrets and variables → Actions**.

---

## 🗄️ Database Schema & SQLite FTS5 Indexing

Database path: `data/company_master.db`

### 1. `companies` Table
| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY` | Auto-increment primary key |
| `cin` | `TEXT UNIQUE` | Corporate Identification Number (e.g. `L22210MH1995PLC084781`) |
| `company_name` | `TEXT NOT NULL` | Full registered legal company name |
| `normalized_name` | `TEXT NOT NULL` | Lowercase, punctuation-stripped, legal-suffix-normalized search key |
| `company_status` | `TEXT` | `Active`, `Under Liquidation`, `Dormant`, etc. |
| `company_class` | `TEXT` | `Private`, `Public` |
| `company_category` | `TEXT` | `Company limited by Shares`, etc. |
| `date_of_registration` | `TEXT` | `YYYY-MM-DD` registration date |
| `registered_state` | `TEXT` | Two-letter state code (`MH`, `TN`, `KA`, `DL`, etc.) |
| `roc` | `TEXT` | Registrar of Companies office (`RoC-Chennai`, `RoC-Mumbai`) |
| `registered_address` | `TEXT` | Full registered office address |

### 2. `company_aliases` Table
Maps commercial recruitment brand names to canonical legal companies:
* `"TCS"` → `"Tata Consultancy Services Limited"`
* `"Infy"` / `"Infosys Technologies"` → `"Infosys Limited"`
* `"Cognizant"` / `"CTS"` → `"Cognizant Technology Solutions India Private Limited"`
* `"Zoho"` / `"AdventNet"` → `"Zoho Corporation Private Limited"`
* `"Lamprell"` → `"Lamprell Energy India Private Limited"`

### 3. `company_search` (SQLite FTS5 Virtual Table)
```sql
CREATE VIRTUAL TABLE company_search USING fts5 (
    company_name,
    normalized_name,
    cin UNINDEXED,
    prefix='2,3,4,5,6',
    tokenize='unicode61 remove_diacritics 2'
);
```

---

## 🚀 CLI Commands & Usage

### 1. Test API Connectivity (10-record sanity check)
```powershell
python -m scripts.test_mca_api
```

### 2. Download Company Data (Full or State-by-State)
```powershell
# Download all states (default page size 5000)
python -m scripts.download_mca_companies

# Download specific state (e.g. Tamil Nadu)
python -m scripts.download_mca_companies --state TN

# Download Karnataka with 20,000 ceiling limit
python -m scripts.download_mca_companies --state KA --max-records 20000

# Reset checkpoint to offset 0
python -m scripts.download_mca_companies --reset
```

### 3. Periodic Incremental Update
```powershell
python -m scripts.update_mca_companies
```

### 4. Search & OCR Typo Resolution CLI
```powershell
# Exact Brand search
python -m scripts.search_company "Accenture"

# OCR Typo Correction search
python -m scripts.search_company "ACCENTURF"

# Multi-line Raw OCR Poster Text search
python -m scripts.search_company --ocr-text "WALK-IN INTERVIEW AT TCS CHENNAI FOR JAVA DEVELOPER"
```

---

## 🐍 Python Code Integration

```python
from src.company_resolver import find_company

# 1. Resolving from OCR typo
result = find_company("ACCENTURF")
print(result)
# Output:
# {
#   "matched": True,
#   "company_name": "Accenture Solutions Private Limited",
#   "cin": "U72900MH2001PTC132450",
#   "confidence": 0.894,
#   "match_type": "fuzzy_medium"
# }

# 2. Resolving from multi-line poster text
poster_ocr = """
WALK-IN INTERVIEW
URGENT HIRING
CHENNAI
SOFTWARE ENGINEER
LAMP RELL ENERGY
"""
result = find_company(poster_ocr)
print(result["company_name"]) # "Lamprell Energy India Private Limited"
```

---

## 🧪 Unit Test Suite

Run the full unit test suite covering normalizer, database, FTS5, RapidFuzz ranking, and API client:

```powershell
python -m unittest discover -s tests
```
Output:
```
..................
----------------------------------------------------------------------
Ran 18 tests in 0.072s

OK
```
