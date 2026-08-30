"""
End-to-end integration tests for ImageToJobPipeline.
"""
import os
import unittest
from PIL import Image, ImageDraw, ImageFont
from image_pipeline.pipeline import ImageToJobPipeline


class TestPipelineE2E(unittest.TestCase):
    def setUp(self):
        self.test_img_path = "test_synthetic_flyer.jpg"
        # Generate a synthetic high-resolution job flyer image
        img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Header: Company Name
        draw.rectangle([(0, 0), (800, 120)], fill=(20, 35, 60))
        draw.text((250, 45), "LAMPRELL", fill=(255, 255, 255))

        # Event
        draw.text((220, 180), "WALK-IN INTERVIEW", fill=(220, 40, 40))
        draw.text((320, 240), "CHENNAI", fill=(20, 20, 20))

        # Roles
        draw.text((100, 320), "POSITIONS OPEN:", fill=(0, 0, 0))
        draw.text((120, 380), "1. Senior Software Engineer", fill=(40, 40, 40))
        draw.text((120, 430), "2. Full Stack Developer", fill=(40, 40, 40))
        draw.text((120, 480), "3. QA Automation Engineer", fill=(40, 40, 40))

        # Date & Time
        draw.text((100, 560), "Date: 28th to 30th August 2026", fill=(0, 0, 150))
        draw.text((100, 610), "Timing: 09:30 AM to 03:30 PM", fill=(0, 0, 150))

        # Venue
        draw.text((100, 690), "Venue: RMZ Millenia, OMR, Chennai - 600096", fill=(0, 0, 0))

        # Contacts
        draw.text((100, 770), "Contact: +919876543210 | hr@lamprell.com", fill=(0, 100, 0))

        img.save(self.test_img_path)
        self.pipeline = ImageToJobPipeline(enable_ai_verification=False)

    def tearDown(self):
        if os.path.exists(self.test_img_path):
            os.remove(self.test_img_path)

    def test_full_pipeline_extraction(self):
        result = self.pipeline.process_image(self.test_img_path)
        
        self.assertTrue(result.is_job)
        self.assertEqual(result.job_type, "walk_in_interview")
        self.assertGreaterEqual(result.signal_score, 8)
        
        # Verify Company
        self.assertIsNotNone(result.company.name)
        self.assertEqual(result.company.name, "Lamprell")

        # Verify Location
        self.assertEqual(result.location.city, "Chennai")
        self.assertEqual(result.location.state, "Tamil Nadu")

        # Verify Roles
        role_canonicals = [r.canonical for r in result.roles]
        self.assertIn("Software Engineer", role_canonicals)

        # Verify Date & Times
        self.assertEqual(result.date, "2026-08-28")
        self.assertEqual(result.end_date, "2026-08-30")

        # Verify Contacts
        self.assertIsNotNone(result.contact_phone)
        self.assertIsNotNone(result.contact_email)


if __name__ == "__main__":
    unittest.main()
