from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class TenderAISearchRequest(BaseModel):
    query: str
    variables: Optional[Dict[str, Any]] = Field(default_factory=dict)

class TenderSearchPayload(BaseModel):
    tab_id: int = 2
    tender_id: int = 0
    tender_number: str = ""
    search_text: str = ""
    refine_search_text: str = ""
    boq: bool = False
    city_ids: str = ""
    closing_date_from: str = ""
    closing_date_to: str = ""
    exact_search: bool = False
    exact_search_text: bool = False
    gem: int = 0
    guest_user_id: int = 0
    is_ai_summary: bool = False
    is_tender_doc_uploaded: bool = False
    keyword_id: int = 0
    mfa: str = ""
    msme: int = 0
    nameof_website: str = ""
    organization_ids: int = 0
    organization_name: str = ""
    organization_type_id: int = 0
    organization_type_fallback: str = ""
    page_no: int = 1
    product_id: int = 0
    publication_date_from: str = ""
    publication_date_to: str = ""
    quantity: str = ""
    quantityOperator: int = 0
    record_per_page: int = 20
    search_by: int = 0
    search_by_location: bool = False
    search_by_split_word: bool = False
    sort_by: int = 1
    sort_type: int = 2
    startup: int = 0
    state_ids: str = ""
    statezone_ids: str = ""
    sub_industry_id: int = 0
    tender_typeid: int = 0
    tender_value_from: float = 0
    tender_value_operator: int = 0
    tender_value_to: float = 0

class TenderItem(BaseModel):
    tender_id: int
    requirement_workbrief: Optional[str] = ""
    estimatedcost: Optional[float] = 0
    tender_endsubmission_datetime: Optional[str] = ""
    site_location: Optional[str] = ""
    organization_name: Optional[str] = ""
    doc_uploaded: Optional[bool] = False
    security_code: Optional[str] = ""
    earnest_money_deposite: Optional[float] = 0
    is_favourite: Optional[Any] = None
    ai_summary: Optional[bool] = False
    show_tender_endsubmission: Optional[bool] = True
    boq_line_item: Optional[str] = ""
    is_boq_line_item: Optional[int] = 0
    submission_enddate: Optional[str] = ""

class ExploreSearchResponse(BaseModel):
    success: bool
    message: str = "Success"
    total_record: int = 0
    data: List[Dict[str, Any]] = []
    status_code: int = 200
    used_search_by: Optional[int] = 0

class ExploreCountResponse(BaseModel):
    success: bool
    count: int = 0

class ImportTenderRequest(BaseModel):
    tender: Dict[str, Any]

