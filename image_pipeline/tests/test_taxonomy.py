"""
Unit tests for Role and Location Taxonomy Resolvers.
"""
import unittest
from image_pipeline.taxonomy.role_taxonomy import RoleTaxonomyResolver
from image_pipeline.taxonomy.location_taxonomy import LocationTaxonomyResolver


class TestTaxonomy(unittest.TestCase):
    def test_role_resolution(self):
        # Canonical & Alias resolution
        r1 = RoleTaxonomyResolver.resolve_role("software development engineer")
        self.assertIsNotNone(r1)
        self.assertEqual(r1["canonical"], "Software Engineer")

        r2 = RoleTaxonomyResolver.resolve_role("sdet")
        self.assertIsNotNone(r2)
        self.assertEqual(r2["canonical"], "QA / Software Tester")

        # Non-IT roles
        r3 = RoleTaxonomyResolver.resolve_role("mechanical engineer")
        self.assertIsNotNone(r3)
        self.assertEqual(r3["canonical"], "Mechanical Design / Production Engineer")

        r4 = RoleTaxonomyResolver.resolve_role("electrical engineer")
        self.assertIsNotNone(r4)
        self.assertEqual(r4["canonical"], "Electrical & Electronics Engineer")

    def test_location_and_locality_resolution(self):
        # OMR -> Chennai
        loc_omr = LocationTaxonomyResolver.resolve_location("Interview Venue: OMR Chennai")
        self.assertIsNotNone(loc_omr)
        self.assertEqual(loc_omr["city"], "Chennai")
        self.assertEqual(loc_omr["state"], "Tamil Nadu")

        # Guindy -> Chennai
        loc_guindy = LocationTaxonomyResolver.resolve_location("Walkin at Olympia Tech Park, Guindy")
        self.assertIsNotNone(loc_guindy)
        self.assertEqual(loc_guindy["city"], "Chennai")

        # Hitec City -> Hyderabad
        loc_hyd = LocationTaxonomyResolver.resolve_location("Building 12, Hitec City, Madhapur")
        self.assertIsNotNone(loc_hyd)
        self.assertEqual(loc_hyd["city"], "Hyderabad")
        self.assertEqual(loc_hyd["state"], "Telangana")

        # Hinjewadi -> Pune
        loc_pune = LocationTaxonomyResolver.resolve_location("Phase 1, Hinjewadi")
        self.assertIsNotNone(loc_pune)
        self.assertEqual(loc_pune["city"], "Pune")
        self.assertEqual(loc_pune["state"], "Maharashtra")

        # Whitefield -> Bengaluru
        loc_blr = LocationTaxonomyResolver.resolve_location("ITPB Whitefield")
        self.assertIsNotNone(loc_blr)
        self.assertEqual(loc_blr["city"], "Bengaluru")
        self.assertEqual(loc_blr["state"], "Karnataka")


if __name__ == "__main__":
    unittest.main()
