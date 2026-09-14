from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from enum import Enum

class CrawlStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class CrawlResult(str, Enum):
    CREATED = "CREATED"
    UNCHANGED = "UNCHANGED"
    UPDATED = "UPDATED"

class CrawlLogBase(BaseModel):
    source_id: str
    url: HttpUrl
    status: CrawlStatus
    result: Optional[CrawlResult] = None
    http_status: Optional[int] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: datetime

class CrawlLogCreate(CrawlLogBase):
    pass

class CrawlLogResponse(CrawlLogBase):
    id: str = Field(alias="_id")
    url: str

    model_config = {
        "populate_by_name": True,
    }

