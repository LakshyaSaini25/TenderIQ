from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


class TenderDocument(BaseModel):
    name: str
    url: str
    type: Optional[str] = "tender_document"


class TenderSchema(BaseModel):
    """
    Universal normalized schema that EVERY scraper must produce.
    """
    source: str = Field(..., description="Source portal identifier, e.g. CPPP, GeM")
    source_id: str = Field(..., description="Unique portal tender ID or reference number")

    title: str = Field(..., description="Normalized tender title")
    reference_no: Optional[str] = Field(None, description="Tender notice/reference number")

    organisation: Optional[str] = Field(None, description="Issuing organisation or company")
    department: Optional[str] = Field(None, description="Sub-department or division")

    category: Optional[str] = Field(None, description="Works, Goods, Services, etc.")
    tender_type: Optional[str] = Field(None, description="Open, Limited, EOI, etc.")

    location: Optional[str] = Field(None, description="City, District, or State")
    pincode: Optional[str] = Field(None, description="Postal code if available")

    tender_value: Optional[float] = Field(None, description="Estimated tender value in INR")
    emd_amount: Optional[float] = Field(None, description="Earnest Money Deposit in INR")
    tender_fee: Optional[float] = Field(None, description="Tender document processing fee in INR")

    publication_date: Optional[datetime] = Field(None, description="Date when published")
    closing_date: Optional[datetime] = Field(None, description="Bid submission deadline")
    opening_date: Optional[datetime] = Field(None, description="Technical bid opening date")

    status: Optional[str] = Field("OPEN", description="OPEN, CLOSED, CANCELLED")
    description: Optional[str] = Field(None, description="Work description or summary")

    source_url: str = Field(..., description="Direct URL to the tender or detail page")
    documents: List[TenderDocument] = Field(default_factory=list, description="Associated tender documents")

    inviting_authority_name: Optional[str] = None
    inviting_authority_address: Optional[str] = None

    detail_solved: bool = Field(False, description="True if detail page & CAPTCHA was bypassed")
    raw_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Raw portal-specific payload")

    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TenderFilterParams(BaseModel):
    """
    Query parameters for filtering scraped tenders in the database.
    """
    keyword: Optional[str] = None
    source: Optional[str] = None
    state: Optional[str] = None
    category: Optional[str] = None
    organisation: Optional[str] = None
    status: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    sort_by: str = Field("closing_date", description="closing_date, publication_date, tender_value, scraped_at")
    sort_order: int = Field(1, description="1 for ASC (e.g. earliest closing first), -1 for DESC")


class ScraperRunStats(BaseModel):
    source: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    pages_requested: int = 0
    tenders_found: int = 0
    new_tenders: int = 0
    updated_tenders: int = 0
    failed_tenders: int = 0
    duration_seconds: float = 0.0
    status: str = "RUNNING"  # RUNNING, COMPLETED, FAILED
    error_message: Optional[str] = None
