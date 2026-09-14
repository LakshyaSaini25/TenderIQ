from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

class OpportunityType(str, Enum):
    TENDER = "TENDER"
    PROJECT = "PROJECT"
    PROCUREMENT = "PROCUREMENT"
    NEWS = "NEWS"
    BUSINESS_OPPORTUNITY = "BUSINESS_OPPORTUNITY"
    OTHER = "OTHER"

class OpportunityStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"

class OpportunityContacts(BaseModel):
    emails: List[str] = []
    phones: List[str] = []

class AIMetadata(BaseModel):
    processed: bool = False
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    processed_at: Optional[datetime] = None
    confidence: Optional[float] = None
    error: Optional[str] = None

class TenderDocument(BaseModel):
    title: str
    url: str

class OpportunityBase(BaseModel):
    source_id: str
    content_id: Optional[str] = None
    type: OpportunityType = OpportunityType.TENDER
    title: str
    reference_number: Optional[str] = None
    reference_number_raw: Optional[str] = None
    description: Optional[str] = None
    organization: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    value: Optional[Union[float, str]] = None
    currency: Optional[str] = None
    value_text: Optional[str] = None
    published_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    contacts: OpportunityContacts = Field(default_factory=OpportunityContacts)
    source_url: str
    status: OpportunityStatus = OpportunityStatus.OPEN
    is_opportunity: bool = True
    detection_reason: Optional[str] = None

    # Enriched Tender Detail fields (from CPPP detail page & captcha solve)
    tender_fee: Optional[str] = None
    emd_amount: Optional[str] = None
    tender_category: Optional[str] = None
    product_category: Optional[str] = None
    pincode: Optional[str] = None
    inviting_authority_name: Optional[str] = None
    inviting_authority_address: Optional[str] = None
    documents: List[TenderDocument] = Field(default_factory=list)
    detail_solved: bool = False
    detail_enriching: bool = False

    # Phase 6 AI-enhanced fields
    eligibility: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    scope: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    experience_requirements: List[str] = Field(default_factory=list)
    equipment_requirements: List[str] = Field(default_factory=list)
    ai: Optional[AIMetadata] = None

class OpportunityCreate(OpportunityBase):
    pass

class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    reference_number: Optional[str] = None
    reference_number_raw: Optional[str] = None
    description: Optional[str] = None
    organization: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    value: Optional[Union[float, str]] = None
    currency: Optional[str] = None
    value_text: Optional[str] = None
    published_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    contacts: Optional[OpportunityContacts] = None
    source_url: Optional[str] = None
    status: Optional[OpportunityStatus] = None
    is_opportunity: Optional[bool] = None
    detection_reason: Optional[str] = None

    # Enriched fields
    tender_fee: Optional[str] = None
    emd_amount: Optional[str] = None
    tender_category: Optional[str] = None
    product_category: Optional[str] = None
    pincode: Optional[str] = None
    inviting_authority_name: Optional[str] = None
    inviting_authority_address: Optional[str] = None
    documents: Optional[List[TenderDocument]] = None
    detail_solved: Optional[bool] = None
    detail_enriching: Optional[bool] = None

    # Phase 6 fields
    eligibility: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    scope: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    experience_requirements: Optional[List[str]] = None
    equipment_requirements: Optional[List[str]] = None
    ai: Optional[AIMetadata] = None

class OpportunityResponse(OpportunityBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "serialize_by_alias": True,
    }

class CollectionSummary(BaseModel):
    source_id: str
    discovered: int
    created: int
    updated: int
    unchanged: int
    failed: int

class ProcessSingleResponse(BaseModel):
    status: str  # "CREATED", "UPDATED", "UNCHANGED", "NOT_AN_OPPORTUNITY", "FAILED"
    is_opportunity: bool
    type: Optional[str] = None
    opportunity_id: Optional[str] = None

class ProcessSourceSummary(BaseModel):
    source_id: str
    processed: int
    opportunities_created: int
    opportunities_updated: int
    not_opportunities: int
    failed: int

class AIProcessResponse(BaseModel):
    content_id: str
    opportunity_id: Optional[str] = None
    ai_status: str  # "SUCCESS", "UNAVAILABLE", "SKIPPED", "FAILED"
    ai_model: Optional[str] = None
    processing_duration: float = 0.0
    enriched_fields: List[str] = []
    message: Optional[str] = None

class AIHealthResponse(BaseModel):
    available: bool
    model: Optional[str] = None
    models_loaded: List[str] = []
    error: Optional[str] = None
