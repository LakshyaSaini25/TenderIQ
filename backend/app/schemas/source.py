from pydantic import BaseModel, HttpUrl, Field, field_serializer
from typing import Optional
from typing import Optional, List
from datetime import datetime, timezone
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

    @field_serializer("last_checked_at", "created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime]) -> Optional[str]:
        """Always emit datetimes as UTC ISO 8601 with Z suffix so the browser parses them correctly."""
        if dt is None:
            return None
        # If the datetime is naive (no tzinfo), assume it is UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ─── Source Discovery Schemas ─────────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    """Request body for POST /sources/discover"""
    state: str
    city: Optional[str] = None


class RecommendedSource(BaseModel):
    """A portal recommended by the discovery engine for a given location."""
    name: str
    url: str
    type: str
    description: str
    tags: List[str] = []
    relevance_score: int
    is_curated: bool = True
