from pydantic import BaseModel, Field
from typing import Optional, List

class CategoryBase(BaseModel):
    name: str
    parent_id: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: str = Field(alias="_id")

    model_config = {
        "populate_by_name": True,
        "serialize_by_alias": True,
    }

