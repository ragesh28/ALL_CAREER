import json
import unittest
from unittest.mock import Mock, patch

from scripts.company_job_details import confirmed_india_location, details_from_record, fetch_details, inline_job_data
from scripts.company_recovery import jobs_from_html, posting_url, records_from_json
from scripts.company_sources import fetch_feed_pages, next_page
from bs4 import BeautifulSoup


class CareerRecoveryTests(unittest.TestCase):
    def tearDown(self):
        fetch_details.cache_clear()

    def test_navigation_and_media_cannot_be_postings(self):
        for url in ["https://example.com/careers/life-at-company", "https://example.com/jobs/saved", "https://example.com/go/India/9553955", "https://cdn.example.com/7beb5311-75a4-0049-50f5-8f58fd55aba7/icon.svg", "https://example.com/company/careers/all-jobs"]:
            self.assertFalse(posting_url(url), url)
        self.assertTrue(posting_url("https://jobs.example.com/job/chennai/engineer/123"))
        self.assertEqual(jobs_from_html('<a href="/jobs/saved">0 Saved Jobs</a>', "https://example.com/"), [])

    def test_smartrecruiters_preserves_country_and_links_to_posting(self):
        rows = records_from_json({"content": [{"id": "123", "name": "Engineer", "location": {"city": "Tirupati", "country": "in"}, "ref": "https://api.smartrecruiters.com/v1/companies/ACME/postings/123"}]}, "https://api.smartrecruiters.com/v1/companies/ACME/postings?limit=100")
        self.assertEqual(rows[0]["location"], "Tirupati, India")
        self.assertTrue(confirmed_india_location(rows[0]["location"]))
        self.assertEqual(rows[0]["apply_url"], "https://jobs.smartrecruiters.com/ACME/123")

    def test_kula_nested_description_office_and_canonical_url(self):
        source = "https://careers.kula.ai/api/internal/ats_job_posts?accountName=rocketlane"
        row = {"id": 2112, "title": "Technical Account Manager", "ats_job": {"job_description": "Actual duties", "offices": [{"city": "Chennai", "country": "India"}]}}
        jobs = records_from_json({"data": [row]}, source)
        self.assertEqual(jobs[0]["apply_url"], "https://careers.kula.ai/rocketlane/2112-technical-account-manager")
        self.assertEqual(jobs[0]["location"], "Chennai, India")
        self.assertEqual(jobs[0]["description"], "Actual duties")
        self.assertEqual(records_from_json({"data": [{**row, "is_confidential": True}]}, source), [])

    def test_phonepe_only_public_postings(self):
        rows = [{"title": "Engineer", "status": s, "applyUrl": f"https://jobs.smartrecruiters.com/PHONEPELIMITED/{i}"} for i,s in enumerate(["PUBLIC", "PRIVATE", "INTERNAL", "NOT_PUBLISHED"])]
        self.assertEqual(len(records_from_json({"results": rows}, "https://www.phonepe.com/apollo/job-postings/latest.json")), 1)

    def test_tcs_job_id_and_experience_but_apply_by_is_not_posted_date(self):
        jobs = records_from_json({"payload": {"content": [{"id": "376658J", "title": "Engineer", "location": "Mumbai", "minimumExperienceInYears": 0, "maximumExperienceInYears": 3, "applyBy": "2026-11-30"}]}}, "https://ibegin.tcsapps.com/candidate/next/api/en-IN/search/jobs")
        self.assertEqual(jobs[0]["apply_url"], "https://ibegin.tcsapps.com/candidate/next/en-IN/jobs/376658J")
        self.assertEqual(jobs[0]["experience"], "0-3 years")
        self.assertNotIn("date_posted", jobs[0])

    @patch("scripts.company_job_details.requests.get")
    def test_workday_apply_url_requests_description_without_apply_suffix(self, get):
        response = Mock(status_code=200, headers={"Content-Type": "application/json"})
        response.json.return_value = {"jobPostingInfo": {"jobDescription": "Full duties for this job"}}
        get.return_value = response
        result = fetch_details("https://adobe.wd5.myworkdayjobs.com/external/job/India/Engineer_R1/apply")
        self.assertEqual(get.call_args.args[0], "https://adobe.wd5.myworkdayjobs.com/wday/cxs/adobe/external/job/India/Engineer_R1")
        self.assertEqual(result["description"], "Full duties for this job")

    @patch("scripts.company_job_details.requests.get")
    def test_wipro_uses_role_description_instead_of_company_intro(self, get):
        get.return_value = Mock(status_code=200, headers={"Content-Type": "text/html"}, text='<div class="joblayouttoken">About Wipro '+('company ' * 100)+'</div><div class="joblayouttoken">Job Description Role: Engineer, requirements and duties</div>')
        result = fetch_details("https://careers.wipro.com/jobs/123")
        self.assertIn("Role: Engineer", result["description"])
        self.assertNotIn("About Wipro", result["description"])

    def test_zoho_public_inline_json_is_decoded_without_running_script(self):
        data = [{"id": "123", "Posting_Title": "Engineer", "Job_Description": "Full duties", "Publish": True, "Keep_on_Career_Site": False}]
        encoded = json.dumps(data).replace('"', r'\x22')
        html = "<script>var jobs = JSON.parse('" + encoded + "'); maliciousCode();</script>"
        rows = jobs_from_html(html, "https://careers.zohocorp.com/jobs/Careers/123/Engineer")
        self.assertEqual(rows[0]["description"], "Full duties")

    def test_pagination_stops_repeated_page_and_preserves_all_new_jobs(self):
        feed = {"url": "https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/careers/jobs", "method": "POST", "payload": {"offset": 0, "limit": 20}}
        payload = {"total": 200, "jobPostings": [{"title": "Engineer", "externalPath": "/job/India/Engineer_R1", "locationsText": "India"}]}
        response = Mock(status_code=200)
        response.json.return_value = payload
        session = Mock()
        session.request.return_value = response
        rows, attempts = fetch_feed_pages(feed, session=session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(session.request.call_count, 2)
        self.assertEqual(feed["payload"]["offset"], 0)
        self.assertIsNone(next_page(feed, {"total": 1}, 1))

    def test_unknown_and_foreign_remote_are_not_confirmed_india(self):
        for location in ["", "Remote", "US - Remote", "Indiana", "Indonesia"]:
            self.assertFalse(confirmed_india_location(location))
        self.assertEqual(details_from_record({"location": {"name": "Chennai, India"}})["location"], "Chennai, India")


if __name__ == "__main__":
    unittest.main()
