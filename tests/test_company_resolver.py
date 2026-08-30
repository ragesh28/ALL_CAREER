"""
Unit Tests for Company Resolver (Exact, Alias, FTS5 + RapidFuzz Typo Resolution).
"""
import unittest
from pathlib import Path
from company_db.database import CompanyDatabase
from company_db.resolver import CompanyResolver


class TestCompanyResolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = Path("data/test_resolver_company_unit.db")
        if cls.test_db_path.exists():
            try: cls.test_db_path.unlink()
            except Exception: pass

        cls.db = CompanyDatabase(db_path=str(cls.test_db_path))

        # Seed sample MCA companies
        sample_companies = [
            {
                "cin": "U72900MH2001PTC132450",
                "company_name": "Accenture Solutions Private Limited",
                "company_status": "Active",
                "registered_state": "Maharashtra"
            },
            {
                "cin": "L22210MH1995PLC084781",
                "company_name": "Tata Consultancy Services Limited",
                "company_status": "Active",
                "registered_state": "Maharashtra"
            },
            {
                "cin": "L85110KA1981PLC013115",
                "company_name": "Infosys Limited",
                "company_status": "Active",
                "registered_state": "Karnataka"
            },
            {
                "cin": "L32102KA1945PLC020800",
                "company_name": "Wipro Limited",
                "company_status": "Active",
                "registered_state": "Karnataka"
            },
            {
                "cin": "U74200TN2008PTC068132",
                "company_name": "Lamprell Energy India Private Limited",
                "company_status": "Active",
                "registered_state": "Tamil Nadu"
            },
            {
                "cin": "U72900TN2010PTC075964",
                "company_name": "Zoho Corporation Private Limited",
                "company_status": "Active",
                "registered_state": "Tamil Nadu"
            }
        ]
        cls.db.upsert_batch(sample_companies)
        cls.resolver = CompanyResolver(db=cls.db)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "test_db_path") and cls.test_db_path.exists():
            try: cls.test_db_path.unlink()
            except Exception: pass

    def test_exact_company_match(self):
        res = self.resolver.find_company("Accenture Solutions Private Limited")
        self.assertTrue(res["matched"])
        self.assertEqual(res["company_name"], "Accenture Solutions Private Limited")
        self.assertEqual(res["match_type"], "exact")
        self.assertEqual(res["confidence"], 1.0)

    def test_brand_alias_match(self):
        # "TCS" -> "Tata Consultancy Services Limited"
        res_tcs = self.resolver.find_company("TCS")
        self.assertTrue(res_tcs["matched"])
        self.assertEqual(res_tcs["company_name"], "Tata Consultancy Services Limited")
        self.assertEqual(res_tcs["match_type"], "alias_exact")

        # "Infy" -> "Infosys Limited"
        res_infy = self.resolver.find_company("Infy")
        self.assertTrue(res_infy["matched"])
        self.assertEqual(res_infy["company_name"], "Infosys Limited")

    def test_ocr_typo_correction_accenturf(self):
        # OCR misread 'Accenture' as 'ACCENTURF'
        res = self.resolver.find_company("ACCENTURF")
        self.assertTrue(res["matched"])
        self.assertEqual(res["company_name"], "Accenture Solutions Private Limited")
        self.assertGreaterEqual(res["confidence"], 0.85)
        self.assertIn(res["match_type"], ["fuzzy_high", "fuzzy_medium"])

    def test_partial_name_match(self):
        res = self.resolver.find_company("Lamprell Energy")
        self.assertTrue(res["matched"])
        self.assertEqual(res["company_name"], "Lamprell Energy India Private Limited")

    def test_raw_multiline_ocr_text(self):
        ocr_poster_text = """
        WALK-IN INTERVIEW
        URGENT HIRING
        CHENNAI
        SOFTWARE ENGINEER
        ACCENTURF
        Date: 29 Aug 2026
        """
        res = self.resolver.find_company(ocr_poster_text)
        self.assertTrue(res["matched"])
        self.assertEqual(res["company_name"], "Accenture Solutions Private Limited")

    def test_unknown_company_rejection_no_hallucination(self):
        # A completely unknown company name not in MCA DB
        res = self.resolver.find_company("Random Nonexistent Startup 998877")
        self.assertFalse(res["matched"])
        self.assertIsNone(res["company_name"])

    def test_generic_poster_keywords_rejection(self):
        # Only generic poster words without any company name
        generic_text = "WALK-IN INTERVIEW\nURGENT HIRING\nCHENNAI\nSOFTWARE ENGINEER"
        res = self.resolver.find_company(generic_text)
        self.assertFalse(res["matched"])
        self.assertIsNone(res["company_name"])


if __name__ == "__main__":
    unittest.main()
