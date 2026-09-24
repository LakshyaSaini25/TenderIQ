import os
import pytest
from datetime import datetime, timezone

from app.scrapers.cppp_scraper import CPPPScraper
from app.scrapers.schema import TenderSchema

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(filename: str) -> str:
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def cppp_scraper():
    return CPPPScraper(repository=None)


def test_extract_tenders_from_listing(cppp_scraper):
    html = read_fixture("cppp_page.html")
    soup = cppp_scraper.parse(html)
    tenders = cppp_scraper.extract_tenders(soup)

    assert len(tenders) == 2

    # Verify first tender fields
    t1 = tenders[0]
    assert t1["sl_no"] == "1."
    assert "UPGRADATION OF FURNITURE" in t1["title"]
    assert t1["reference_no"] == "1000465402"
    assert t1["tender_id"] == "2026_BPCL_26768"
    assert t1["source_id"] == "2026_BPCL_26768"
    assert t1["organisation"] == "Bharat Petroleum Corporation Limited"
    assert t1["pub_date_str"] == "23-Sep-2026 10:41 PM"
    assert t1["close_date_str"] == "30-Sep-2026 09:00 AM"
    assert t1["open_date_str"] == "30-Sep-2026 09:15 AM"
    assert "tendersfullview" in t1["detail_url"]

    # Verify second tender fields
    t2 = tenders[1]
    assert t2["sl_no"] == "2."
    assert "CONSTRUCTION OF RESIDENTIAL QUARTERS" in t2["title"]
    assert t2["organisation"] == "Central Public Works Department (CPWD)"
    assert t2["tender_id"] == "170018"


def test_parse_detail_html(cppp_scraper):
    html = read_fixture("cppp_detail.html")
    raw_item = {
        "title": "UPGRADATION OF FURNITURE",
        "detail_url": "https://eprocure.gov.in/cppp/tendersfullview/123",
        "documents": [],
    }

    cppp_scraper._parse_detail_html(html, raw_item)

    assert "Retail Business Unit" in raw_item["department"]
    assert raw_item["category"] == "Works"
    assert raw_item["location"] == "Hyderabad"
    assert raw_item["pincode"] == "500001"
    assert raw_item["tender_fee"] == 1180.0
    assert raw_item["emd_amount"] == 50000.0
    assert raw_item["tender_value"] == 2500000.0
    assert "Chief Manager" in raw_item["inviting_authority_name"]
    assert "Begumpet" in raw_item["inviting_authority_address"]

    # Check documents
    docs = raw_item["documents"]
    assert len(docs) == 3
    doc_urls = [d["url"] for d in docs]
    assert any("Notice_Inviting_Tender.pdf" in u for u in doc_urls)
    assert any("BOQ_Furniture.xlsx" in u for u in doc_urls)


def test_normalization_to_schema(cppp_scraper):
    raw_item = {
        "source_id": "2026_BPCL_26768",
        "title": "UPGRADATION OF FURNITURE AT HYDERABAD",
        "reference_no": "1000465402",
        "organisation": "Bharat Petroleum Corporation Limited",
        "department": "Retail BU",
        "category": "Works",
        "location": "Hyderabad",
        "pincode": "500001",
        "pub_date_str": "23-Sep-2026 10:41 PM",
        "close_date_str": "30-Sep-2026 09:00 AM",
        "open_date_str": "30-Sep-2026 09:15 AM",
        "tender_value": 2500000.0,
        "emd_amount": 50000.0,
        "tender_fee": 1180.0,
        "detail_url": "https://eprocure.gov.in/cppp/tendersfullview/123",
        "description": "Upgradation of office furniture",
        "documents": [
            {"name": "NIT.pdf", "url": "https://eprocure.gov.in/cppp/doc/nit.pdf", "type": "tender_document"}
        ],
        "detail_solved": True
    }

    normalized = cppp_scraper.normalize(raw_item)

    assert isinstance(normalized, TenderSchema)
    assert normalized.source == "CPPP"
    assert normalized.source_id == "2026_BPCL_26768"
    assert normalized.title == "UPGRADATION OF FURNITURE AT HYDERABAD"
    assert normalized.tender_value == 2500000.0
    assert normalized.emd_amount == 50000.0
    assert normalized.publication_date is not None
    assert normalized.publication_date.tzinfo == timezone.utc
    assert len(normalized.documents) == 1
    assert normalized.documents[0].name == "NIT.pdf"
    assert normalized.detail_solved is True


def test_numeric_parsing(cppp_scraper):
    assert cppp_scraper._parse_numeric_amount("₹ 25,00,000") == 2500000.0
    assert cppp_scraper._parse_numeric_amount("1,180.50") == 1180.50
    assert cppp_scraper._parse_numeric_amount("--") is None
    assert cppp_scraper._parse_numeric_amount("N/A") is None


def test_location_heuristic(cppp_scraper):
    loc1 = cppp_scraper._extract_location("CONSTRUCTION WORK AT LUCKNOW CAMPUS", "CPWD")
    assert loc1 == "Lucknow"

    loc2 = cppp_scraper._extract_location("SOLAR POWER INSTALLATION IN MUMBAI DOCKS", "PORT TRUST")
    assert loc2 == "Mumbai"
