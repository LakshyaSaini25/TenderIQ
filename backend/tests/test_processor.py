import unittest
from datetime import datetime, timezone
from app.processors.classifier import Classifier
from app.processors.extractor import Extractor
from app.processors.opportunity_processor import OpportunityProcessor

class TestOpportunityProcessor(unittest.TestCase):

    def test_tender_classification(self):
        title = "Notice Inviting Tender for Road Construction"
        text = "Sealed bids are invited for road construction work. Tender No. NIT-12345."
        is_opp, opp_type, reason = Classifier.classify(title, text)

        self.assertTrue(is_opp)
        self.assertEqual(opp_type, "TENDER")
        self.assertIn("tender", reason.lower())

    def test_project_classification(self):
        title = "Smart City Infrastructure Project Phase 2"
        text = "Building construction and civil works expansion project in Noida."
        is_opp, opp_type, reason = Classifier.classify(title, text)

        self.assertTrue(is_opp)
        self.assertEqual(opp_type, "PROJECT")
        self.assertIn("project", reason.lower())

    def test_non_opportunity_classification(self):
        title = "About Our Company"
        text = "We are a leading software company. Contact us for privacy policy and terms of service."
        is_opp, opp_type, reason = Classifier.classify(title, text)

        self.assertFalse(is_opp)

    def test_reference_extraction(self):
        sample_text = "Construction of 200-bed hospital — Tender No. ABC/2026/123 — closing date 25/10/2026"
        ref_num, raw_ref = Extractor.extract_reference_number(sample_text)

        self.assertEqual(ref_num, "ABC/2026/123")
        self.assertIn("Tender No.", raw_ref)

    def test_date_extraction(self):
        sample_text = "Tender Notice: closing date 25/10/2026 for building construction."
        deadline = Extractor.extract_deadline(sample_text)

        self.assertIsNotNone(deadline)
        self.assertEqual(deadline.year, 2026)
        self.assertEqual(deadline.month, 10)
        self.assertEqual(deadline.day, 25)

    def test_value_extraction(self):
        sample_text = "Construction of 200-bed hospital — estimated value ₹5 crore — submission deadline 2026"
        val, currency, val_text = Extractor.extract_value(sample_text)

        self.assertEqual(val, 50000000.0)  # 5 Crore = 5 * 10,000,000
        self.assertEqual(currency, "INR")
        self.assertTrue("₹5 crore" in val_text.lower() or "5 crore" in val_text.lower())

    def test_lakh_value_extraction(self):
        sample_text = "Supply of office furniture. Estimated Cost: INR 50 Lakh."
        val, currency, val_text = Extractor.extract_value(sample_text)

        self.assertEqual(val, 5000000.0)  # 50 Lakh = 50 * 100,000
        self.assertEqual(currency, "INR")

    def test_contact_extraction(self):
        sample_text = "For queries email us at tender.dept@gov.in or contact +91 9876543210."
        contacts = Extractor.extract_contacts(sample_text)

        self.assertIn("tender.dept@gov.in", contacts["emails"])
        self.assertTrue(len(contacts["phones"]) > 0)

    def test_full_opportunity_processor(self):
        content_doc = {
            "_id": "60d5ec49f1b2c8b1f8c8d8f1",
            "source_id": "src_123",
            "title": "Construction of 200-bed hospital",
            "content": "Construction of 200-bed hospital — Tender No. ABC/2026/123 — closing date 25/10/2026 — estimated value ₹5 crore. Email: tender@hospital.org",
            "url": "https://eprocure.gov.in/tender/123"
        }

        is_opp, status_reason, opp_data = OpportunityProcessor.process(content_doc)

        self.assertTrue(is_opp)
        self.assertEqual(status_reason, "SUCCESS")
        self.assertEqual(opp_data["type"], "TENDER")
        self.assertEqual(opp_data["reference_number"], "ABC/2026/123")
        self.assertEqual(opp_data["value"], 50000000.0)
        self.assertEqual(opp_data["currency"], "INR")
        self.assertEqual(opp_data["deadline"].year, 2026)
        self.assertIn("tender@hospital.org", opp_data["contacts"]["emails"])

if __name__ == '__main__':
    unittest.main()

