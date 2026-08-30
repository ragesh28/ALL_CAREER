"""
Unit tests for Company, DateTime, Location, and QR detectors.
"""
import unittest
from image_pipeline.detectors.company_detector import CompanyDetector
from image_pipeline.detectors.date_time_detector import DateTimeDetector
from image_pipeline.detectors.location_detector import LocationDetector
from image_pipeline.qr.qr_scanner import QRScanner


class TestDetectors(unittest.TestCase):
    def test_company_detection(self):
        # 1. Known dictionary company
        res1 = CompanyDetector.detect_company("LAMPRELL WALK-IN INTERVIEW CHENNAI")
        self.assertEqual(res1.name, "Lamprell")
        self.assertEqual(res1.detection_method, "dictionary")

        # 2. Registered legal suffix company
        res2 = CompanyDetector.detect_company("Apex Technologies Pvt Ltd is conducting hiring drive")
        self.assertEqual(res2.name, "Apex Technologies Pvt Ltd")
        self.assertEqual(res2.detection_method, "legal_suffix")

        # 3. Guardrail: generic words should NOT be identified as company
        res3 = CompanyDetector.detect_company("IMMEDIATE OPENINGS FOR EXPERIENCED CANDIDATES")
        self.assertIsNone(res3.name)

    def test_date_time_detection(self):
        # Date range
        dt1 = DateTimeDetector.detect_date_time("Walk-in Drive: 28th to 30th August 2026 | Timing: 09:30 AM to 03:30 PM")
        self.assertEqual(dt1["date"], "2026-08-28")
        self.assertEqual(dt1["end_date"], "2026-08-30")
        self.assertEqual(dt1["time"].start, "09:30 AM")
        self.assertEqual(dt1["time"].end, "03:30 PM")

        # Single date
        dt2 = DateTimeDetector.detect_date_time("Date of Interview: 19th July 2026 from 10:00 AM - 1:00 PM")
        self.assertEqual(dt2["date"], "2026-07-19")
        self.assertIsNone(dt2["end_date"])
        self.assertEqual(dt2["time"].start, "10:00 AM")
        self.assertEqual(dt2["time"].end, "1:00 PM")

    def test_location_with_pincode_and_venue(self):
        text = "Walk-in Interview\nVenue: RMZ Ecoworld, Outer Ring Road, Bangalore - 560103"
        loc = LocationDetector.detect_location(text)
        self.assertEqual(loc.city, "Bengaluru")
        self.assertEqual(loc.state, "Karnataka")
        self.assertEqual(loc.pincode, "560103")
        self.assertIsNotNone(loc.venue)

    def test_qr_payload_classification(self):
        # URL
        qr_url = QRScanner.classify_payload("https://careers.company.com/apply/12345")
        self.assertEqual(qr_url["payload_type"], "url")
        self.assertEqual(qr_url["url"], "https://careers.company.com/apply/12345")

        # WhatsApp link
        qr_wa = QRScanner.classify_payload("https://wa.me/919876543210")
        self.assertEqual(qr_wa["payload_type"], "url")
        self.assertEqual(qr_wa["phone"], "919876543210")

        # Email
        qr_email = QRScanner.classify_payload("mailto:hr@lamprell.com")
        self.assertEqual(qr_email["payload_type"], "email")
        self.assertEqual(qr_email["email"], "hr@lamprell.com")


if __name__ == "__main__":
    unittest.main()
