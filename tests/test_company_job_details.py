import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.company_job_details import details_from_record, fetch_details, jobspy_options, upgrade_details, jobs_from_payload, is_india_location


class CompanyDetailsTests(unittest.TestCase):
    def tearDown(self):
        fetch_details.cache_clear()

    def test_foreign_remote_and_indiana_are_not_india(self):
        for place in ("US - Remote", "London, United Kingdom", "Indianapolis, Indiana", "Indonesia"):
            self.assertFalse(is_india_location(place), place)
        self.assertTrue(is_india_location("Chennai, Tamil Nadu, India"))
        self.assertTrue(is_india_location("Bengaluru, Karnataka"))

    def test_spent_detail_budget_still_preserves_inline_descriptions(self):
        import scripts.company_job_details as details
        rows = [{"url": "https://example.com/jobs/1"}, {"jobDescription": "Inline source content"}]
        with patch.object(details, "_detail_seconds_used", 9999), patch.object(details, "fetch_details") as fetch:
            details.enrich_jobs(rows)
            fetch.assert_not_called()
        self.assertEqual(rows[1]["description"], "Inline source content")

    def test_missing_salary_stays_missing_and_experience_is_explicit(self):
        details = details_from_record({"description": "We require 3-5 years of experience in HR operations."})
        self.assertEqual(details["experience"], "3-5 years of experience")
        self.assertNotIn("salary", details)
        self.assertNotIn("experience", details_from_record({"description": "The company has 30 years of history."}))

    def test_jobspy_uses_supported_proxy_and_description_parameters(self):
        def scrape(proxies=None, linkedin_fetch_description=False):
            pass
        self.assertEqual(jobspy_options(scrape, ["private-proxy"]), {"proxies": ["private-proxy"], "linkedin_fetch_description": True})

    def test_upgrade_adds_details_without_erasing_old_values(self):
        old = {"description": "Existing detailed description", "salary": "INR 1000000"}
        self.assertTrue(upgrade_details(old, {"description": "Short", "experience": "3-5 years"}))
        self.assertEqual(old["description"], "Existing detailed description")
        self.assertEqual(old["salary"], "INR 1000000")

    def test_nested_generic_api_returns_records_not_just_a_count(self):
        rows = jobs_from_payload({"total": 1, "data": {"positions": [{"name": "Engineer", "positionUrl": "/careers/job/1", "locations": ["Chennai"], "jobDescription": "Actual duties"}]}}, "https://example.com/api/search")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["apply_url"], "https://example.com/careers/job/1")
        self.assertEqual(rows[0]["description"], "Actual duties")
        self.assertEqual(jobs_from_payload({"total": 200}, "https://example.com"), [])
        self.assertEqual(jobs_from_payload({"name": "Company", "url": "https://example.com"}, "https://example.com"), [])

    @patch("scripts.company_job_details.requests.get")
    def test_siemens_uses_full_article_and_explicit_posted_date(self, get):
        description = "Engineering requirements and responsibilities. " * 40
        get.return_value = Mock(status_code=200, headers={"Content-Type": "text/html"}, text='<p>Posted since 21-Nov-2026</p><article class="article--details"><div class="article__content__view"><div class="article__content__view__field__value">Label:</div>'+description+'</div></article>')
        details = fetch_details("https://jobs.siemens.com/en_US/externaljobs/JobDetail/1")
        self.assertGreater(len(details["description"]), 1000)
        self.assertEqual(details["date_posted"], "21-Nov-2026")

    def test_wipro_stops_repeated_pages_and_keeps_job_links(self):
        import scrape_from_md as scraper
        payload = {"jobSearchResult": [{"response": {"id": "123", "unifiedStandardTitle": "Engineer", "jobLocationShort": ["Chennai"]}}]}
        response = Mock(status_code=200, text=json.dumps(payload))
        with patch.object(scraper.requests, "post", return_value=response) as post, patch.object(scraper.time, "sleep"):
            rows = scraper._scrape_wipro_paginated({})["all_jobs"]
        self.assertEqual(post.call_count, 2)
        self.assertEqual(rows[0]["apply_url"], "https://careers.wipro.com/jobs/123")
        self.assertEqual(rows[0]["location"], "Chennai")

    @patch("scripts.company_job_details.requests.request")
    def test_workday_detail_route_and_structured_metadata(self, get):
        get.return_value = Mock(status_code=200, headers={"Content-Type": "application/json"})
        get.return_value.json.return_value = {"jobPostingInfo": {"jobDescription": "<p>Minimum 5 years of experience</p>", "datePosted": "2026-11-21", "employmentType": "Full-time"}}
        details = fetch_details("https://acme.wd1.myworkdayjobs.com/en-US/External/job/Chennai/Engineer_R1")
        self.assertIn("/wday/cxs/acme/External/job/Chennai/Engineer_R1", get.call_args.args[1])
        self.assertEqual(details["date_posted"], "2026-11-21")
        self.assertEqual(details["description"], "Minimum 5 years of experience")

    @patch("scripts.company_job_details.requests.get")
    def test_does_not_use_a_different_job_from_jsonld(self, get):
        record = {"@type": "JobPosting", "url": "https://example.com/jobs/another", "description": "Unrelated description"}
        get.return_value = Mock(status_code=200, headers={"Content-Type": "text/html"}, text='<script type="application/ld+json">'+json.dumps(record)+'</script>')
        self.assertEqual(fetch_details("https://example.com/jobs/requested"), {})

    def test_indeed_save_extracts_metadata_without_persisting_description(self):
        import step3_big_company_scrape as scraper
        import os
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temp, patch.object(scraper, "enrich_jobs", side_effect=lambda rows: rows):
            try:
                os.chdir(temp)
                scraper.save_jobs([{"title": "Engineer", "company": "Example", "location": "Chennai", "url": "https://example.com/jobs/1", "date": "2026-11-23", "description": "Minimum 5 years of experience", "salary": "INR 1000000"}])
                rows = json.loads(Path("workday_scraper/big_company_jobs.json").read_text())
                self.assertNotIn('description', rows[0])
                self.assertEqual(rows[0]['experience'], 'Minimum 5 years of experience')
                self.assertEqual(rows[0]["salary"], "INR 1000000")
                self.assertEqual(rows[0]["posted"], "2026-11-23")
            finally:
                os.chdir(previous)

    def test_md_save_and_seen_job_upgrade_retain_details(self):
        import scrape_from_md as scraper
        import os
        previous = Path.cwd()
        job = {"title": "HR Administrator", "location": "Chennai", "apply_url": "https://example.com/jobs/2", "description": "Requires 3-5 years of experience", "date_posted": "2026-11-20"}
        results = {"1. Example": {"status": "OK", "all_jobs": [job]}}
        with tempfile.TemporaryDirectory() as temp, patch.object(scraper, "enrich_jobs", side_effect=lambda rows: rows):
            try:
                os.chdir(temp)
                scraper.update_big_company_jobs(results, {})
                job["salary"] = "INR 800000"
                scraper.update_big_company_jobs(results, {})
                rows = json.loads(Path("workday_scraper/big_company_jobs.json").read_text())
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["posted"], "2026-11-20")
                self.assertEqual(rows[0]["salary"], "INR 800000")
                self.assertNotIn('description', rows[0])
                self.assertEqual(rows[0]['experience'], '3-5 years of experience')
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
