import unittest
from scripts.build_web_catalog import normalize
class LogoDataTest(unittest.TestCase):
 def test_preserves_job_and_organization_logo_fields(self):
  j=normalize({'title':'Developer','company':{'name':'Example','logo':'https://example.org/logo.png','website':'https://example.org'}})
  self.assertEqual(j['company_logo'],'https://example.org/logo.png'); self.assertEqual(j['company_website'],'https://example.org')
  j=normalize({'title':'Developer','hiringOrganization':{'logo':'https://example.org/job.png','sameAs':'https://example.org'}})
  self.assertEqual(j['company_logo'],'https://example.org/job.png')
if __name__ == '__main__': unittest.main()
