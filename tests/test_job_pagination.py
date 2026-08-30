"""
Unit Tests for Keyset/Cursor Pagination and LRU Caching.
"""
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from job_db.database import JobDatabase
from job_db.importer import JobImporter
from job_db.search import JobSearchEngine


class TestJobPagination(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = Path("data/test_jobs_pag_unit.db")
        if cls.test_db_path.exists():
            try: cls.test_db_path.unlink()
            except Exception: pass

        cls.db = JobDatabase(db_path=str(cls.test_db_path))
        cls.importer = JobImporter(db=cls.db)
        cls.search_engine = JobSearchEngine(db=cls.db)

        # Seed 10 sequential jobs across different dates
        base_d = datetime(2026, 8, 30)
        jobs = []
        for i in range(10):
            d_str = (base_d - timedelta(days=i)).strftime("%Y-%m-%d")
            jobs.append({
                "title": f"Software Engineer #{i:02d}",
                "company": "TCS",
                "location": "Chennai, Tamil Nadu",
                "source": "naukri",
                "date_posted": d_str,
                "url": f"https://naukri.com/job/p_{i}"
            })
        cls.importer.import_batch(jobs)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "test_db_path") and cls.test_db_path.exists():
            try: cls.test_db_path.unlink()
            except Exception: pass

    def test_cursor_keyset_pagination(self):
        # Page 1 (limit 3)
        p1 = self.search_engine.search(city="Chennai", limit=3, use_cache=False)
        self.assertEqual(len(p1["jobs"]), 3)
        self.assertEqual(p1["total_jobs"], 10)
        self.assertTrue(p1["has_more"])
        self.assertIsNotNone(p1["next_cursor"])

        # Page 2 using next_cursor
        c_date = p1["next_cursor"]["cursor_date"]
        c_id = p1["next_cursor"]["cursor_id"]
        p2 = self.search_engine.search(city="Chennai", cursor_date=c_date, cursor_id=c_id, limit=3, use_cache=False)
        self.assertEqual(len(p2["jobs"]), 3)
        self.assertTrue(p2["has_more"])

        # Ensure no overlap between page 1 and page 2
        p1_ids = {j["_id"] for j in p1["jobs"]}
        p2_ids = {j["_id"] for j in p2["jobs"]}
        self.assertEqual(len(p1_ids.intersection(p2_ids)), 0)

    def test_lru_caching(self):
        # 1st call (fills cache)
        res1 = self.search_engine.search(city="Chennai", limit=5, use_cache=True)
        # 2nd call (hits cache)
        res2 = self.search_engine.search(city="Chennai", limit=5, use_cache=True)
        self.assertEqual(res1["total_jobs"], res2["total_jobs"])
        self.assertEqual(len(res1["jobs"]), len(res2["jobs"]))


if __name__ == "__main__":
    unittest.main()
