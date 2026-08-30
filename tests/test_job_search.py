"""
Unit Tests for Job Search Engine (FTS5 + B-Tree Filters & Total Job Count).
"""
import unittest
from pathlib import Path
from job_db.database import JobDatabase
from job_db.importer import JobImporter
from job_db.search import JobSearchEngine


class TestJobSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = Path("data/test_jobs_search_unit.db")
        if cls.test_db_path.exists():
            try: cls.test_db_path.unlink()
            except Exception: pass

        cls.db = JobDatabase(db_path=str(cls.test_db_path))
        cls.importer = JobImporter(db=cls.db)
        cls.search_engine = JobSearchEngine(db=cls.db)

        # Seed sample job records
        sample_jobs = [
            {
                "title": "Senior Python Backend Developer",
                "company": "Tata Consultancy Services Limited",
                "location": "Chennai, Tamil Nadu",
                "source": "naukri",
                "role_search": "Python Developer",
                "date_posted": "2026-08-30",
                "experience": "2 - 5 yrs",
                "skills": ["Python", "Django", "PostgreSQL"],
                "url": "https://naukri.com/job/1",
                "description": "Looking for expert Python developer in Chennai with Django."
            },
            {
                "title": "Junior Python Developer",
                "company": "Infosys Limited",
                "location": "Chennai, Tamil Nadu",
                "source": "indeed",
                "role_search": "Python Developer",
                "date_posted": "2026-08-30",
                "experience": "0 - 1 yrs",
                "skills": ["Python", "Flask"],
                "url": "https://indeed.com/job/2",
                "description": "Fresher Python opening in Chennai."
            },
            {
                "title": "React Frontend Engineer",
                "company": "Accenture Solutions Private Limited",
                "location": "Bengaluru, Karnataka",
                "source": "linkedin",
                "role_search": "React Developer",
                "date_posted": "2026-08-29",
                "experience": "1 - 3 yrs",
                "skills": ["React", "TypeScript"],
                "url": "https://linkedin.com/job/3",
                "description": "Frontend React developer needed in Bangalore."
            },
            {
                "title": "Walk-in Interview for Java Developer",
                "company": "Wipro Limited",
                "location": "Chennai, Tamil Nadu",
                "source": "naukri",
                "role_search": "Java Developer",
                "date_posted": "2026-08-30",
                "is_walkin": 1,
                "walkin_date": "2026-09-02",
                "url": "https://naukri.com/job/4",
                "description": "Walkin drive in Chennai for Java backend."
            }
        ]
        cls.importer.import_batch(sample_jobs)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "test_db_path") and cls.test_db_path.exists():
            try: cls.test_db_path.unlink()
            except Exception: pass

    def test_filter_by_city(self):
        res = self.search_engine.search(city="Chennai", use_cache=False)
        self.assertEqual(res["total_jobs"], 3)
        self.assertEqual(len(res["jobs"]), 3)
        for j in res["jobs"]:
            self.assertEqual(j["city"].lower(), "chennai")

    def test_filter_by_city_and_role(self):
        res = self.search_engine.search(city="Chennai", role="Python Developer", use_cache=False)
        self.assertEqual(res["total_jobs"], 2)
        for j in res["jobs"]:
            self.assertEqual(j["role_search"], "Python Developer")

    def test_filter_by_city_role_and_source(self):
        res = self.search_engine.search(city="Chennai", role="Python Developer", source="naukri", use_cache=False)
        self.assertEqual(res["total_jobs"], 1)
        self.assertEqual(res["jobs"][0]["company"], "Tata Consultancy Services Limited")

    def test_filter_walkin(self):
        res = self.search_engine.search(is_walkin=True, use_cache=False)
        self.assertEqual(res["total_jobs"], 1)
        self.assertTrue(res["jobs"][0]["is_walkin"])
        self.assertEqual(res["jobs"][0]["walkin_date"], "2026-09-02")

    def test_fts5_text_search(self):
        res = self.search_engine.search(query_text="Django PostgreSQL", use_cache=False)
        self.assertEqual(res["total_jobs"], 1)
        self.assertEqual(res["jobs"][0]["company"], "Tata Consultancy Services Limited")

    def test_fts5_combined_with_structured_filters(self):
        res = self.search_engine.search(query_text="Python", city="Chennai", source="indeed", use_cache=False)
        self.assertEqual(res["total_jobs"], 1)
        self.assertEqual(res["jobs"][0]["company"], "Infosys Limited")


if __name__ == "__main__":
    unittest.main()
