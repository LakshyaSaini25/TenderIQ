from pydantic import BaseModel, Field
from typing import Optional, List

class LocationBase(BaseModel):
    country: str
    state: Optional[str] = None
    city: Optional[str] = None

class LocationResponse(LocationBase):
    id: str = Field(alias="_id")

    model_config = {
        "populate_by_name": True,
        "serialize_by_alias": True,
    }

