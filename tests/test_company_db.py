"""
Unit Tests for SQLite Company Database and FTS5 Search.
"""
import os
import unittest
from pathlib import Path
from company_db.database import CompanyDatabase


class TestCompanyDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = Path("data/test_company_master_unit.db")
        if cls.test_db_path.exists():
            try: cls.test_db_path.unlink()
            except Exception: pass
        cls.db = CompanyDatabase(db_path=str(cls.test_db_path))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "test_db_path") and cls.test_db_path.exists():
            try: cls.test_db_path.unlink()
            except Exception: pass

    def setUp(self):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM companies;")
            conn.commit()

    def test_schema_and_metadata_initialization(self):
        stats = self.db.get_stats()
        self.assertEqual(stats["total_companies"], 0)
        self.assertGreater(stats["total_aliases"], 0)  # Seeded from company_aliases.json

    def test_batch_upsert_and_deduplication(self):
        records = [
            {
                "cin": "L22210MH1995PLC084781",
                "company_name": "Tata Consultancy Services Limited",
                "company_status": "Active",
                "registered_state": "Maharashtra",
                "date_of_registration": "1995-01-19"
            },
            {
                "cin": "U72900MH2001PTC132450",
                "company_name": "Accenture Solutions Private Limited",
                "company_status": "Active",
                "registered_state": "Maharashtra",
                "date_of_registration": "2001-07-16"
            }
        ]
        inserted = self.db.upsert_batch(records)
        self.assertEqual(inserted, 2)

        # Re-insert same CIN with updated status
        updated_records = [
            {
                "cin": "L22210MH1995PLC084781",
                "company_name": "Tata Consultancy Services Limited",
                "company_status": "Active (Listed)",
                "registered_state": "Maharashtra",
                "date_of_registration": "1995-01-19"
            }
        ]
        re_inserted = self.db.upsert_batch(updated_records)
        self.assertEqual(re_inserted, 1)

        # Verify total count is still 2 (no duplicate CIN)
        stats = self.db.get_stats()
        self.assertEqual(stats["total_companies"], 2)

        # Verify updated status
        tcs = self.db.exact_lookup("tata consultancy services")
        self.assertIsNotNone(tcs)
        self.assertEqual(tcs["company_status"], "Active (Listed)")

    def test_exact_lookup(self):
        records = [
            {
                "cin": "U74200TN2008PTC068132",
                "company_name": "Lamprell Energy India Private Limited",
                "company_status": "Active",
                "registered_state": "Tamil Nadu"
            }
        ]
        self.db.upsert_batch(records)

        # Lookup with normalized name
        res = self.db.exact_lookup("lamprell energy")
        self.assertIsNotNone(res)
        self.assertEqual(res["company_name"], "Lamprell Energy India Private Limited")
        self.assertEqual(res["cin"], "U74200TN2008PTC068132")

    def test_fts5_prefix_search(self):
        records = [
            {
                "cin": "U72900MH2001PTC132450",
                "company_name": "Accenture Solutions Private Limited",
                "company_status": "Active"
            },
            {
                "cin": "L85110KA1981PLC013115",
                "company_name": "Infosys Limited",
                "company_status": "Active"
            }
        ]
        self.db.upsert_batch(records)

        # FTS5 search with partial prefix 'accentur'
        candidates = self.db.search_fts5(["accentur"])
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["cin"], "U72900MH2001PTC132450")

        # FTS5 search with 'infosy'
        candidates_infy = self.db.search_fts5(["infosy"])
        self.assertGreaterEqual(len(candidates_infy), 1)
        self.assertEqual(candidates_infy[0]["cin"], "L85110KA1981PLC013115")


if __name__ == "__main__":
    unittest.main()
