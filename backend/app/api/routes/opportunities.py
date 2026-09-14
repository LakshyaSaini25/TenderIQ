import asyncio
from fastapi import APIRouter, Depends, Query, status
from typing import List, Optional, Dict, Any
from app.schemas.opportunity import (
    OpportunityResponse,
    CollectionSummary,
    ProcessSingleResponse,
    ProcessSourceSummary,
    AIProcessResponse
)
from app.services.opportunity_service import OpportunityService

router = APIRouter()

def get_opportunity_service():
    return OpportunityService()

@router.post("/collect/{source_id}", response_model=CollectionSummary, status_code=status.HTTP_200_OK)
async def collect_opportunities(
    source_id: str,
    service: OpportunityService = Depends(get_opportunity_service)
):
    """Triggers scraper adapter collection for a specific tender source."""
    return await service.collect_opportunities(source_id)

@router.post("/process/{content_id}", response_model=ProcessSingleResponse, status_code=status.HTTP_200_OK)
async def process_opportunity_content(
    content_id: str,
    service: OpportunityService = Depends(get_opportunity_service)
):
    """Manually processes a single content item into a structured opportunity."""
    return await service.process_single_content(content_id)

@router.post("/process-source/{source_id}", response_model=ProcessSourceSummary, status_code=status.HTTP_200_OK)
async def process_source_opportunities(
    source_id: str,
    service: OpportunityService = Depends(get_opportunity_service)
):
    """Processes all collected content items belonging to a source into opportunities."""
    return await service.process_source_content(source_id)

@router.post("/ai-process/{content_id}", response_model=AIProcessResponse, status_code=status.HTTP_200_OK)
async def ai_process_opportunity(
    content_id: str,
    service: OpportunityService = Depends(get_opportunity_service)
):
    """Runs Ollama AI extraction on a content item to enrich an existing opportunity."""
    return await service.ai_process_single_content(content_id)

@router.get("", response_model=List[OpportunityResponse])

async def read_opportunities(
    source_id: Optional[str] = Query(None, description="Filter by source_id"),
    type: Optional[str] = Query(None, description="Filter by type (e.g. TENDER, PROJECT)"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. OPEN, CLOSED)"),
    category_id: Optional[str] = Query(None, description="Filter by category_id"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    service: OpportunityService = Depends(get_opportunity_service)
):
    """Retrieve list of extracted opportunities with filtering and pagination."""
    return await service.get_all_opportunities(
        source_id=source_id,
        type_filter=type,
        status_filter=status,
        category_id_filter=category_id,
        skip=skip,
        limit=limit
    )

@router.get("/count", response_model=int)
async def count_opportunities(
    source_id: Optional[str] = Query(None, description="Filter by source_id"),
    type: Optional[str] = Query(None, description="Filter by type (e.g. TENDER, PROJECT)"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. OPEN, CLOSED)"),
    category_id: Optional[str] = Query(None, description="Filter by category_id"),
    service: OpportunityService = Depends(get_opportunity_service)
):
    """Retrieve total count of opportunities matching filters for pagination."""
    return await service.count_opportunities(
        source_id=source_id,
        type_filter=type,
        status_filter=status,
        category_id_filter=category_id
    )

@router.post("/batch-refresh")
async def batch_refresh_all_pending(
    service: OpportunityService = Depends(get_opportunity_service)
):
    """
    Enriches all pending unenriched opportunities in background using
    batch queue (batches of 3, 2-3s jitter).
    """
    all_opps = await service.get_all_opportunities(limit=100)
    pending_ids = [
        str(o["_id"]) for o in all_opps
        if not o.get("detail_solved")
    ]
    if pending_ids:
        for pid in pending_ids:
            try:
                await service.opportunity_repo.update(pid, {"detail_enriching": True})
            except Exception:
                pass
        asyncio.create_task(service.batch_refresh_opportunities(pending_ids))

    return {
        "status": "QUEUED",
        "queued": len(pending_ids),
        "message": f"Queued {len(pending_ids)} opportunities for background CAPTCHA solving & enrichment"
    }

@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def read_opportunity(
    opportunity_id: str,
    service: OpportunityService = Depends(get_opportunity_service)
):
    """Retrieve details of a single opportunity by ID."""
    return await service.get_opportunity(opportunity_id)

@router.post("/{opportunity_id}/refresh-detail", response_model=OpportunityResponse)
async def refresh_opportunity_detail(
    opportunity_id: str,
    service: OpportunityService = Depends(get_opportunity_service)
):
    """Re-fetches fresh detail specifications & documents via captcha solver for an opportunity."""
    return await service.refresh_opportunity_detail(opportunity_id)

@router.get("/{opportunity_id}/documents/{doc_index}/download")
async def download_opportunity_document(
    opportunity_id: str,
    doc_index: int,
    service: OpportunityService = Depends(get_opportunity_service)
):
    """Proxies and downloads the official tender document with proper session and referer headers."""
    return await service.download_document(opportunity_id, doc_index)


