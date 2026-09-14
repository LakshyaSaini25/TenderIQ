from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class ContentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

class ContentResponse(BaseModel):
    id: str = Field(alias="_id")
    source_id: str
    url: str
    title: str
    content: str
    content_hash: str
    published_at: Optional[datetime] = None
    last_seen_at: datetime
    first_seen_at: datetime
    status: ContentStatus
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "serialize_by_alias": True,
    }
