from fastapi import APIRouter, Depends, Query, status
from typing import List, Dict, Any
from app.schemas.content import ContentResponse
from app.services.content_service import ContentService

router = APIRouter()

def get_content_service():
    return ContentService()

@router.post("/collect/{source_id}", status_code=status.HTTP_200_OK)
async def collect_content(source_id: str, service: ContentService = Depends(get_content_service)):
    """Manually triggers collection for one source."""
    return await service.collect_source(source_id)

@router.get("", response_model=List[ContentResponse])
async def read_contents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    service: ContentService = Depends(get_content_service)
):
    """Retrieve collected contents."""
    return await service.get_all_content(skip=skip, limit=limit)

@router.get("/{content_id}", response_model=ContentResponse)
async def read_content(content_id: str, service: ContentService = Depends(get_content_service)):
    """Retrieve a specific content by ID."""
    return await service.get_content(content_id)

