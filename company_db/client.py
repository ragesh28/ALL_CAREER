"""
Official data.gov.in MCA Company Master Data API Client.
Handles pagination, rate limits, exponential backoff, and field mapping.
NEVER exposes or logs API keys.
"""
import time
import requests
from typing import Dict, Any, List, Optional, Tuple

from .config import (
    MCA_API_BASE_URL,
    MCA_RESOURCE_ID,
    DEFAULT_API_LIMIT,
    REQUEST_TIMEOUT_SECONDS,
    MAX_RETRIES,
    BACKOFF_FACTOR,
    get_api_key
)


class DataGovMCAClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key if api_key is not None else get_api_key()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ALL_CAREER_MCA_Importer/1.0",
            "Accept": "application/json"
        })

    def is_configured(self) -> bool:
        """Check if API key is present."""
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def fetch_page(
        self,
        offset: int = 0,
        limit: int = DEFAULT_API_LIMIT,
        state_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch a single paginated JSON response from data.gov.in MCA resource.
        Returns raw API response dictionary.
        """
        if not self.is_configured():
            raise ValueError(
                "DATA_GOV_API_KEY environment variable is not set. "
                "Please set it with: export DATA_GOV_API_KEY='your_key' or in Windows: $env:DATA_GOV_API_KEY='your_key'"
            )

        params: Dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "offset": offset,
            "limit": limit
        }

        if state_code:
            params["filters[CompanyStateCode]"] = state_code

        last_err = None
        for attempt in range(MAX_RETRIES):
            try:
                # Do NOT log params containing api-key
                resp = self.session.get(
                    MCA_API_BASE_URL,
                    params=params,
                    timeout=REQUEST_TIMEOUT_SECONDS
                )

                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    sleep_time = BACKOFF_FACTOR ** (attempt + 1)
                    print(f"⏳ API Rate Limited (HTTP 429). Backing off for {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                elif resp.status_code in (500, 502, 503, 504):
                    sleep_time = BACKOFF_FACTOR ** (attempt + 1)
                    print(f"⚠️ Server error (HTTP {resp.status_code}). Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                elif resp.status_code in (400, 403, 404):
                    # Client errors (e.g. invalid key or wrong parameter)
                    try:
                        err_json = resp.json()
                        msg = err_json.get("message", resp.text)
                    except Exception:
                        msg = resp.text[:200]
                    raise RuntimeError(f"data.gov.in API Error (HTTP {resp.status_code}): {msg}")
                else:
                    resp.raise_for_status()

            except requests.exceptions.RequestException as e:
                last_err = e
                sleep_time = BACKOFF_FACTOR ** (attempt + 1)
                time.sleep(sleep_time)

        raise RuntimeError(f"Failed to fetch MCA data after {MAX_RETRIES} attempts. Error: {last_err}")

    def parse_records(self, api_response: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Parse and normalize record keys from data.gov.in JSON response.
        Returns: (parsed_records_list, total_records_available)
        """
        records = api_response.get("records", [])
        total_count = int(api_response.get("total", api_response.get("count", 0)))

        normalized_records = []
        for r in records:
            # data.gov.in MCA API may use varying case in column names across versions
            # Inspect and map safely
            cin = (
                r.get("cin") or r.get("CIN") or r.get("corporate_identification_number") or
                r.get("Company_CIN") or ""
            ).strip().upper()

            company_name = (
                r.get("company_name") or r.get("CompanyName") or r.get("Company_Name") or
                r.get("name") or ""
            ).strip()

            if not cin or not company_name:
                continue

            status = r.get("company_status") or r.get("CompanyStatus") or r.get("status")
            c_class = r.get("company_class") or r.get("CompanyClass") or r.get("class")
            cat = r.get("company_category") or r.get("CompanyCategory") or r.get("category")
            reg_date = r.get("CompanyRegistrationdate_date") or r.get("date_of_registration") or r.get("DateOfRegistration") or r.get("registration_date")
            state = r.get("registered_state") or r.get("CompanyStateCode") or r.get("state")
            roc = r.get("CompanyROCcode") or r.get("roc") or r.get("ROC") or r.get("roc_code")
            addr = r.get("registered_address") or r.get("Registered_Office_Address") or r.get("address")

            normalized_records.append({
                "cin": cin,
                "company_name": company_name,
                "company_status": status,
                "company_class": c_class,
                "company_category": cat,
                "date_of_registration": reg_date,
                "registered_state": state,
                "roc": roc,
                "registered_address": addr
            })

        return normalized_records, total_count

    def test_connection(self) -> Dict[str, Any]:
        """
        Perform a 10-record diagnostic test to verify connectivity and schema.
        Never prints or exposes the API key.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "DATA_GOV_API_KEY is not configured in environment variables."
            }

        try:
            raw = self.fetch_page(offset=0, limit=10)
            records, total = self.parse_records(raw)
            return {
                "success": True,
                "http_status": 200,
                "records_returned": len(records),
                "total_available_in_catalog": total,
                "sample_company": records[0]["company_name"] if records else None,
                "sample_cin": records[0]["cin"] if records else None,
                "field_keys": list(raw.get("records", [{}])[0].keys()) if raw.get("records") else []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
