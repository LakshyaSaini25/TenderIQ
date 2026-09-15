from fastapi import APIRouter, Depends, status
from typing import List
from app.schemas.source import SourceResponse, SourceCreate, SourceUpdate, DiscoverRequest, RecommendedSource
from app.services.source_service import SourceService
from app.services.source_discovery_service import discover_sources

router = APIRouter()

def get_source_service():
    return SourceService()

@router.get("", response_model=List[SourceResponse])
async def read_sources(service: SourceService = Depends(get_source_service)):
    """Retrieve all tracked sources."""
    return await service.get_all_sources()

@router.get("/{source_id}", response_model=SourceResponse)
async def read_source(source_id: str, service: SourceService = Depends(get_source_service)):
    """Retrieve a specific source by ID."""
    return await service.get_source(source_id)

@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(source_in: SourceCreate, service: SourceService = Depends(get_source_service)):
    """Add a new source to track."""
    return await service.create_source(source_in)

@router.post("/discover", response_model=List[RecommendedSource])
async def discover_tender_sources(body: DiscoverRequest):
    """
    Discover relevant tender portal sources for the given Indian state and optional city.
    Returns a scored, ranked list of recommended sources drawn from a curated database
    of 80+ known Indian tender portals plus live DuckDuckGo search results.
    """
    results = await discover_sources(state=body.state, city=body.city)
    return results

@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(source_id: str, source_in: SourceUpdate, service: SourceService = Depends(get_source_service)):
    """Update an existing source."""
    return await service.update_source(source_id, source_in)

@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str, service: SourceService = Depends(get_source_service)):
    """Delete a source."""
    await service.delete_source(source_id)

