import asyncio
from datetime import datetime
from app.collectors.adapters.eprocure_adapter import EprocureAdapter

SAMPLE_CPPP_TABLE_HTML = """
<html>
<body>
  <div>Some header text</div>
  <table class="table">
    <thead>
      <tr>
        <th>Sl.No</th>
        <th>e-Published Date</th>
        <th>Bid Submission Closing Date</th>
        <th>Tender Opening Date</th>
        <th>Title/Ref.No./Tender Id</th>
        <th>Organisation Name</th>
        <th>Corrigendum</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>1.</td>
        <td>14-Sep-2026 12:30 PM</td>
        <td>05-Oct-2026 06:00 PM</td>
        <td>08-Oct-2026 10:00 AM</td>
        <td><a href="/cppp/tendersfullview/abc123xyz" title="External Url">WORK SERVICES OF RUNWAY REHABILITATION SCHEME (RSS) EXERCISE</a>/8924/BKT/E8/2026_MES_789292_1</td>
        <td>E-IN-C BRANCH - MILITARY ENGINEER SERVICES</td>
        <td>--</td>
      </tr>
      <tr>
        <td>2.</td>
        <td>14-Sep-2026 12:05 PM</td>
        <td>17-Sep-2026 04:00 PM</td>
        <td>17-Sep-2026 04:30 PM</td>
        <td><a href="https://eprocure.gov.in/cppp/tendersfullview/ntpc456">PROPOSAL FOR VISIT OF BHEL SERVICE ENGINEER</a>/NTPC/USSC-CPG3/9900333431/2026_NTPC_111878_1</td>
        <td>NTPC Limited</td>
        <td>--</td>
      </tr>
    </tbody>
  </table>
  <footer>Footer with FAQ, Terms, Feedback</footer>
</body>
</html>
"""

def test_eprocure_adapter_supports():
    adapter = EprocureAdapter()
    assert adapter.supports({"url": "https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata"}) is True
    assert adapter.supports({"url": "https://example.com", "name": "CPPP Tender Portal"}) is True
    assert adapter.supports({"url": "https://unknownportal.org", "name": "Random Site"}) is False

def test_eprocure_adapter_extracts_clean_tenders():
    adapter = EprocureAdapter()
    url = "https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata"
    source_id = "test_source_123"

    results = asyncio.run(adapter.extract_opportunity(url, SAMPLE_CPPP_TABLE_HTML, source_id, fetch_details=False))
    assert results is not None
    assert len(results) == 2

    # Verify Tender 1
    t1 = results[0]
    assert t1["title"] == "WORK SERVICES OF RUNWAY REHABILITATION SCHEME (RSS) EXERCISE"
    assert t1["reference_number"] == "8924/BKT/E8"
    assert t1["organization"] == "E-IN-C BRANCH - MILITARY ENGINEER SERVICES"
    assert t1["source_url"] == "https://eprocure.gov.in/cppp/tendersfullview/abc123xyz"
    assert t1["type"] == "TENDER"
    assert t1["status"] == "OPEN"
    assert isinstance(t1["published_at"], datetime)
    assert isinstance(t1["deadline"], datetime)
    assert "Footer with FAQ" not in t1["description"]

    # Verify Tender 2
    t2 = results[1]
    assert t2["title"] == "PROPOSAL FOR VISIT OF BHEL SERVICE ENGINEER"
    assert t2["reference_number"] == "NTPC/USSC-CPG3/9900333431"
    assert t2["organization"] == "NTPC Limited"
    assert t2["source_url"] == "https://eprocure.gov.in/cppp/tendersfullview/ntpc456"
    assert t2["status"] == "OPEN"

def test_eprocure_adapter_empty_html():
    adapter = EprocureAdapter()
    res = asyncio.run(adapter.extract_opportunity("http://url", "<html><body>No tables here</body></html>", "src_1", fetch_details=False))
    assert res is None

def test_captcha_solver_parse_cppp_detail_html():
    from app.collectors.captcha_solver import CaptchaSolver
    sample_detail_html = """
    <html>
    <body>
      <table>
        <tr>
          <td>Organisation Name</td><td>:</td><td>Central Public Works Department (CPWD)</td>
        </tr>
        <tr>
          <td>Tender Category</td><td>:</td><td>Works</td>
          <td>Product Category</td><td>:</td><td>Civil Works - Others</td>
        </tr>
        <tr>
          <td>Tender Fee *</td><td>:</td><td>500</td>
          <td>EMD *</td><td>:</td><td>453942</td>
        </tr>
        <tr>
          <td>Work Description</td><td>:</td><td>Augmentation of existing STP with 170 KLD STP at IIIT, Pala, Kottayam</td>
        </tr>
        <tr>
          <td>Tender Document</td><td>:</td><td><a href="https://etender.cpwd.gov.in/doc123.pdf">Download Tender Notice</a></td>
        </tr>
        <tr>
          <td>Name</td><td>:</td><td>IIT Pala Pro Division</td>
          <td>Address</td><td>:</td><td>OFFICE OF THE EXECUTIVE ENGINEER</td>
        </tr>
      </table>
    </body>
    </html>
    """
    fields, docs = CaptchaSolver.parse_cppp_detail_html(sample_detail_html)
    assert fields["organization"] == "Central Public Works Department (CPWD)"
    assert fields["tender_category"] == "Works"
    assert fields["product_category"] == "Civil Works - Others"
    assert fields["tender_fee"] == "500"
    assert fields["emd_amount"] == "453942"
    assert "Augmentation of existing STP" in fields["work_description"]
    assert fields["inviting_authority_name"] == "IIT Pala Pro Division"
    assert fields["inviting_authority_address"] == "OFFICE OF THE EXECUTIVE ENGINEER"
    assert len(docs) == 1
    assert docs[0]["url"] == "https://etender.cpwd.gov.in/doc123.pdf"
    assert docs[0]["title"] == "Download Tender Notice"


