"""
Unit Tests for data.gov.in MCA API Client.
"""
import unittest
from company_db.client import DataGovMCAClient


class TestDataGovMCAClient(unittest.TestCase):
    def test_missing_api_key_validation(self):
        client = DataGovMCAClient(api_key="")
        self.assertFalse(client.is_configured())
        with self.assertRaises(ValueError):
            client.fetch_page(offset=0, limit=10)

    def test_record_parsing_normalization(self):
        mock_api_response = {
            "total": 1250000,
            "count": 2,
            "records": [
                {
                    "Company_CIN": "U72900MH2001PTC132450",
                    "CompanyName": "ACCENTURE SOLUTIONS PRIVATE LIMITED",
                    "CompanyStatus": "Active",
                    "CompanyClass": "Private",
                    "CompanyCategory": "Company limited by Shares",
                    "CompanyStateCode": "MH",
                    "DateOfRegistration": "16/07/2001",
                    "ROC": "RoC-Mumbai",
                    "Registered_Office_Address": "Plant 3, Godrej & Boyce Complex, Vikhroli, Mumbai"
                },
                {
                    "cin": "L22210MH1995PLC084781",
                    "company_name": "TATA CONSULTANCY SERVICES LIMITED",
                    "company_status": "Active",
                    "company_class": "Public",
                    "registered_state": "Maharashtra",
                    "date_of_registration": "19/01/1995"
                }
            ]
        }
        client = DataGovMCAClient(api_key="mock_key_12345")
        parsed, total = client.parse_records(mock_api_response)

        self.assertEqual(total, 1250000)
        self.assertEqual(len(parsed), 2)

        # Check record 1
        r1 = parsed[0]
        self.assertEqual(r1["cin"], "U72900MH2001PTC132450")
        self.assertEqual(r1["company_name"], "ACCENTURE SOLUTIONS PRIVATE LIMITED")
        self.assertEqual(r1["company_status"], "Active")
        self.assertEqual(r1["registered_state"], "MH")

        # Check record 2
        r2 = parsed[1]
        self.assertEqual(r2["cin"], "L22210MH1995PLC084781")
        self.assertEqual(r2["company_name"], "TATA CONSULTANCY SERVICES LIMITED")


if __name__ == "__main__":
    unittest.main()
