"""
Unit Tests for Company Normalizer.
"""
import unittest
from company_db.normalizer import CompanyNormalizer


class TestCompanyNormalizer(unittest.TestCase):
    def test_consistent_normalization(self):
        variations = [
            "Tata Consultancy Services Limited",
            "TATA CONSULTANCY SERVICES LTD",
            "Tata Consultancy Services Ltd.",
            " TATA CONSULTANCY SERVICES ",
            "Tata Consultancy Services Private Limited",
            "Tata Consultancy Services Pvt. Ltd."
        ]
        expected = "tata consultancy services"
        for var in variations:
            norm = CompanyNormalizer.normalize_name(var, strip_legal_suffix=True)
            self.assertEqual(norm, expected, f"Failed for variant: {var}")

    def test_corporate_variants(self):
        # Accenture
        acc1 = CompanyNormalizer.normalize_name("Accenture Solutions Private Limited")
        acc2 = CompanyNormalizer.normalize_name("ACCENTURE SOLUTIONS PVT LTD")
        self.assertEqual(acc1, "accenture solutions")
        self.assertEqual(acc1, acc2)

        # Zoho
        zoho1 = CompanyNormalizer.normalize_name("Zoho Corporation Private Limited")
        zoho2 = CompanyNormalizer.normalize_name("ZOHO CORPORATION PVT. LTD.")
        self.assertEqual(zoho1, "zoho corporation")
        self.assertEqual(zoho1, zoho2)

        # Lamprell
        lamp1 = CompanyNormalizer.normalize_name("Lamprell Energy India Private Limited")
        lamp2 = CompanyNormalizer.normalize_name("LAMPRELL ENERGY INDIA PVT. LTD.")
        self.assertEqual(lamp1, "lamprell energy")
        self.assertEqual(lamp1, lamp2)

    def test_preserve_core_company_words(self):
        # Ensure words like Solutions, Technologies, Systems, Energy are not destroyed
        norm1 = CompanyNormalizer.normalize_name("Apex Technologies Private Limited")
        self.assertEqual(norm1, "apex technologies")

        norm2 = CompanyNormalizer.normalize_name("Global Systems and Solutions Ltd.")
        self.assertEqual(norm2, "global systems and solutions")

    def test_generic_poster_words_rejection(self):
        generic_phrases = [
            "WALK IN INTERVIEW",
            "Walk-in Drive",
            "Urgent Hiring",
            "Immediate Openings",
            "Software Engineer",
            "Chennai",
            "Bengaluru",
            "Apply Now",
            "Send Resume",
            "Experience Required"
        ]
        for phrase in generic_phrases:
            self.assertTrue(
                CompanyNormalizer.is_generic_word(phrase),
                f"Generic phrase should be rejected: {phrase}"
            )

    def test_get_search_tokens(self):
        tokens = CompanyNormalizer.get_search_tokens("tata consultancy services")
        self.assertEqual(tokens, ["tata", "consultancy", "services"])


if __name__ == "__main__":
    unittest.main()
