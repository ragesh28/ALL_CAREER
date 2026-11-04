import unittest
from scripts.portal_extractors import parse_listing, scrape_public_listing


class PortalExtractorTests(unittest.TestCase):
    def test_modern_apna_html_without_next_data(self):
        html = '''<a data-testid="job-card" href="/job/123"><div><img alt="Company A"><div><h2>Engineer</h2><span>Company A</span></div></div><div><svg data-testid="LocationOnIcon"></svg>Bengaluru/Bangalore</div><span>Min. 2 years</span></a>'''
        jobs = parse_listing(html, 'apna', 'Bangalore')
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['company'], 'Company A')
        self.assertEqual(jobs[0]['url'], 'https://apna.co/job/123')
        self.assertNotIn('date_posted', jobs[0], 'do not invent an undisclosed posting date')

    def test_freshersworld_card_attribute_url(self):
        html = '''<div class="job-container" job_display_url="https://www.freshersworld.com/jobs/test-123"><span class="wrap-title">Engineer</span><h3 class="company-name">Company B</h3><span class="job-location">Chennai</span></div>'''
        jobs = parse_listing(html, 'freshersworld', 'Bangalore')
        self.assertEqual(jobs[0]['company'], 'Company B')
        self.assertEqual(jobs[0]['location'], 'Chennai')

    def test_workindia_route_data_with_semicolon(self):
        html = '''<script>window.__ROUTE_DATA__ = {"data":[{"id":12,"profile_job_title":"Engineer","branch_company_name":"Company C"}]};</script>'''
        jobs = parse_listing(html, 'workindia', 'Chennai')
        self.assertEqual(jobs[0]['url'], 'https://www.workindia.in/jobs/12/')

    def test_blocked_response_is_not_a_successful_empty_scrape(self):
        class Response:
            status_code = 403
            text = 'Forbidden'
        jobs, report = scrape_public_listing('workindia', 'Engineer', 'Chennai', requester=lambda *a, **kw: Response())
        self.assertEqual(jobs, [])
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['http_status'], 403)


if __name__ == '__main__':
    unittest.main()
