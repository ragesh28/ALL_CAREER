import argparse
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.report_company_investigation import build


class InvestigationReportTests(unittest.TestCase):
    def test_multiple_sources_are_one_employer_and_foreign_description_is_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = {"companies": [{"id": "example", "company": "Example", "career_url": "https://example.com/careers", "sources": [{"engine": "direct", "index": 0, "company_label": "Example", "previous_status": "no_jobs_returned"}, {"engine": "indeed", "index": 0, "company_label": "Example", "previous_status": "no_jobs_returned"}], "state": "unresolved", "attempts": []}]}
            (root / "baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
            (root / "direct.json").write_text(json.dumps([{"engine": "direct", "index": 0, "company": "Example", "status": "sample_found", "sample": {"title": "Engineer", "apply_url": "https://example.com/jobs/1", "location": "Chennai", "description": ""}}]), encoding="utf-8")
            (root / "indeed.json").write_text(json.dumps([{"engine": "indeed", "index": 0, "company": "Example", "status": "sample_found", "sample": {"title": "US Engineer", "apply_url": "https://example.com/jobs/2", "location": "US - Remote", "description": "Responsibilities and qualifications " * 20}}]), encoding="utf-8")
            args = argparse.Namespace(baseline=root / "baseline.json", browser=[], source_audit=[root], output=root / "out", run_url=[])
            with patch("scripts.report_company_investigation.configuration", return_value=None), contextlib.redirect_stdout(io.StringIO()):
                build(args)
            result = json.loads((root / "out/company-investigation-monitor.json").read_text(encoding="utf-8"))
            self.assertEqual(result["summary"]["employers"], 1)
            self.assertEqual(result["summary"]["source_entries_retested"], 2)
            self.assertEqual(result["companies"][0]["overall_status"], "working_description_missing")
            self.assertNotIn("description", result["companies"][0]["current_source_checks"][1]["sample"])


if __name__ == "__main__":
    unittest.main()
