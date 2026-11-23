import json
import unittest
from unittest.mock import Mock, patch

from scripts.company_job_details import confirmed_india_location, details_from_record, enrich_jobs, fetch_details, inline_job_data, public_request
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
        self.assertTrue(posting_url("https://www.pinterestcareers.com/jobs/?gh_jid=123"))
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

    @patch("scripts.company_job_details.requests.request")
    def test_workday_apply_url_requests_description_without_apply_suffix(self, get):
        response = Mock(status_code=200, headers={"Content-Type": "application/json"})
        response.json.return_value = {"jobPostingInfo": {"jobDescription": "Full duties for this job"}}
        get.return_value = response
        result = fetch_details("https://adobe.wd5.myworkdayjobs.com/external/job/India/Engineer_R1/apply")
        self.assertEqual(get.call_args.args[1], "https://adobe.wd5.myworkdayjobs.com/wday/cxs/adobe/external/job/India/Engineer_R1")
        self.assertEqual(result["description"], "Full duties for this job")

    @patch("scripts.company_job_details.requests.get")
    def test_wipro_uses_role_description_instead_of_company_intro(self, get):
        get.return_value = Mock(status_code=200, headers={"Content-Type": "text/html"}, text='<div class="joblayouttoken">About Wipro '+('company ' * 100)+'</div><div class="joblayouttoken">Location Bangalore Job Description Role: Engineer, requirements and duties</div><p>Posting Start Date: 1/15/26</p>')
        result = fetch_details("https://careers.wipro.com/jobs/123")
        self.assertIn("Role: Engineer", result["description"])
        self.assertNotIn("About Wipro", result["description"])
        self.assertEqual(result["date_posted"], "2026-01-15")

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

    @patch("scripts.company_job_details.requests.get")
    def test_turing_uses_observed_public_detail_api(self, get):
        response = Mock(status_code=200, headers={"Content-Type": "application/json"})
        response.json.return_value = {"id": "6192725004", "content": "<p>Full job duties and qualifications</p>"}
        get.return_value = response
        self.assertEqual(fetch_details("https://careers.turing.com/job/6192725004")["description"], "Full job duties and qualifications")
        self.assertEqual(get.call_args.args[0], "https://careers.turing.com/api/v3/job-posts/6192725004")

    @patch("scripts.company_job_details.requests.request")
    def test_workday_retry_after_does_not_trigger_another_http_client(self, request):
        response = Mock(status_code=429, headers={"Retry-After": "60"})
        request.return_value = response
        alternate = Mock()
        import types
        with patch.dict("sys.modules", {"curl_cffi": types.SimpleNamespace(requests=alternate)}):
            self.assertIs(public_request("GET", "https://acme.wd1.myworkdayjobs.com/careers"), response)
        alternate.request.assert_not_called()

    def test_capgemini_keeps_inline_description_and_individual_apply_link(self):
        payload = {"data": [{"title": "Software Engineer", "location": "Pune", "description": "Full duties", "apply_job_url": "https://careers.capgemini.com/job/Pune-Engineer/123/", "status": "1"}]}
        rows = records_from_json(payload, "https://cg-jobstream-api.azurewebsites.net/api/job-search?page=1")
        self.assertEqual(rows[0]["description"], "Full duties")
        self.assertIn("/job/Pune-Engineer/123/", rows[0]["apply_url"])

    def test_explicit_zoho_summary_is_upgraded_by_detail_page(self):
        rows = [{"apply_url": "https://example.com/jobs/1", "description": "Truncated source text..."}]
        with patch("scripts.company_job_details._detail_seconds_used", 0), patch("scripts.company_job_details.fetch_details", return_value={"description": "Actual full responsibilities and qualifications"}):
            enrich_jobs(rows, limit=1)
        self.assertEqual(rows[0]["description"], "Actual full responsibilities and qualifications")

    def test_wipro_posting_uses_public_slug_when_available(self):
        rows = records_from_json({"jobSearchResult": [{"response": {"id": "40585", "unifiedUrlTitle": "Configurator-L4", "unifiedStandardTitle": "Configurator - L4"}}]}, "https://careers.wipro.com/services/recruiting/v1/jobs")
        self.assertEqual(rows[0]["apply_url"], "https://careers.wipro.com/job/Configurator-L4/40585-en_US")

    def test_citi_updated_heading_is_a_real_job_title(self):
        from workday_scraper import scrape_all_companies_v2 as scraper
        response = Mock(text='<div id="search-results-list"><li><h3 class="sr-job-item__title"><a data-job-id="123" href="/job/mumbai/auditor/287/123">Auditor</a></h3><span class="sr-job-location">Mumbai, India</span></li></div>')
        with patch.object(scraper.requests, "get", return_value=response):
            rows = scraper.scrape_citi_html("https://jobs.citi.com", limit=1)
        self.assertEqual(rows[0]["title"], "Auditor")
        self.assertEqual(rows[0]["apply_url"], "https://jobs.citi.com/job/mumbai/auditor/287/123")

    @patch("scripts.company_job_details.requests.post")
    def test_goldman_uses_external_id_and_preserves_description(self, post):
        response = Mock(status_code=200)
        response.json.return_value = {"data": {"role": {"descriptionHtml": "<p>Actual role requirements</p>", "locations": [{"city": "Bengaluru", "country": "India"}]}}}
        post.return_value = response
        details = fetch_details("https://higher.gs.com/roles/189275_GS_MID_CAREER")
        self.assertEqual(post.call_args.kwargs["json"]["variables"]["externalSourceId"], "189275")
        self.assertEqual(details["description"], "Actual role requirements")
        self.assertEqual(details["description_source"], "https://higher.gs.com/roles/189275")


if __name__ == "__main__":
    unittest.main()
