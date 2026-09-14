from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class SourceType(str, Enum):
    GOVERNMENT = "GOVERNMENT"
    TENDER_PORTAL = "TENDER_PORTAL"
    COMPANY_WEBSITE = "COMPANY_WEBSITE"
    NEWS = "NEWS"
    PROJECT_PORTAL = "PROJECT_PORTAL"
    OTHER = "OTHER"

class CrawlFrequency(str, Enum):
    HOURLY = "HOURLY"
    EVERY_6_HOURS = "EVERY_6_HOURS"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"

class SourceBase(BaseModel):
    name: str
    url: HttpUrl
    type: SourceType
    crawl_frequency: CrawlFrequency
    is_active: bool = True

class SourceCreate(SourceBase):
    pass

class SourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    type: Optional[SourceType] = None
    crawl_frequency: Optional[CrawlFrequency] = None
    is_active: Optional[bool] = None

class SourceResponse(BaseModel):
    id: str = Field(alias="_id")
    name: str
    url: str
    type: SourceType
    crawl_frequency: CrawlFrequency
    is_active: bool
    last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        # Serialize using aliases so JSON key is "_id"
        "serialize_by_alias": True,
    }
