"""
Unit tests for Job Signal Detector.
"""
import unittest
from image_pipeline.detectors.signal_detector import JobSignalDetector


class TestJobSignals(unittest.TestCase):
    def test_explicit_walkin_poster(self):
        text = "LAMPRELL WALK-IN INTERVIEW CHENNAI\nSenior Engineer Required\nVenue: OMR Chennai"
        is_job, score, details = JobSignalDetector.evaluate(text, has_role=True, has_location=True, has_company=True)
        self.assertTrue(is_job)
        self.assertGreaterEqual(score, 8)
        self.assertTrue(any("walk_in" in d for d in details))

    def test_hiring_drive_without_walkin_keyword(self):
        # A poster that says "Hiring Drive - Chennai" without the word "walk-in"
        text = "WE ARE HIRING!\nFull Stack Developer Needed\nImmediate Openings in Bengaluru\nApply now: hr@tech.com"
        is_job, score, details = JobSignalDetector.evaluate(text, has_role=True, has_location=True)
        self.assertTrue(is_job)
        self.assertGreaterEqual(score, 5)

    def test_non_job_promotional_flyer(self):
        # An advertisement/promotional flyer with no hiring keywords
        text = "GRAND SALE 50% DISCOUNT!\nVisit our electronics showroom today in Chennai Mount Road"
        is_job, score, details = JobSignalDetector.evaluate(text)
        self.assertFalse(is_job)
        self.assertLess(score, 5)


if __name__ == "__main__":
    unittest.main()
