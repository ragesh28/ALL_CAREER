"""
Unit Tests for ALL_CAREER Job Database Schema and Deduplication.
"""
import unittest
from pathlib import Path
from job_db.database import JobDatabase
from job_db.importer import JobImporter
from job_db.deduplicator import compute_job_hash


class TestJobDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = Path("data/test_jobs_unit.db")
        if cls.test_db_path.exists():
            try: cls.test_db_path.unlink()
            except Exception: pass
        cls.db = JobDatabase(db_path=str(cls.test_db_path))
        cls.importer = JobImporter(db=cls.db)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "test_db_path") and cls.test_db_path.exists():
            try: cls.test_db_path.unlink()
            except Exception: pass

    def setUp(self):
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM jobs;")
            conn.commit()

    def test_deterministic_job_hashing(self):
        job1 = {
            "title": "Python Developer",
            "company": "TCS",
            "location": "Chennai",
            "source": "naukri",
            "date_posted": "2026-08-30"
        }
        job2 = {
            "title": "python developer",
            "company": "tcs",
            "location": "chennai",
            "source": "naukri",
            "date_posted": "2026-08-30"
        }
        hash1 = compute_job_hash(job1)
        hash2 = compute_job_hash(job2)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 32)

    def test_batch_import_and_deduplication(self):
        jobs = [
            {
                "title": "Python Developer",
                "company": "Tata Consultancy Services Limited",
                "location": "Chennai, Tamil Nadu",
                "source": "naukri",
                "role_search": "Python Developer",
                "date_posted": "2026-08-30",
                "experience": "0 - 2 yrs",
                "url": "https://naukri.com/job/101"
            },
            {
                "title": "Java Full Stack Developer",
                "company": "Infosys Limited",
                "location": "Bengaluru, Karnataka",
                "source": "linkedin",
                "role_search": "Java Full Stack Developer",
                "date_posted": "2026-08-29",
                "experience": "Fresher",
                "url": "https://linkedin.com/job/202"
            }
        ]
        inserted = self.importer.import_batch(jobs)
        self.assertEqual(inserted, 2)

        # Attempt to insert identical jobs again
        re_inserted = self.importer.import_batch(jobs)
        self.assertEqual(re_inserted, 0)

        # Verify stats
        stats = self.db.get_stats()
        self.assertEqual(stats["total_jobs"], 2)
        self.assertEqual(stats["total_companies"], 2)
        self.assertEqual(stats["total_locations"], 2)


if __name__ == "__main__":
    unittest.main()
