from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from app.schemas.explore import (
    TenderAISearchRequest,
    ImportTenderRequest
)
from app.services.explore_service import ExploreService

router = APIRouter()

def get_explore_service():
    return ExploreService()

@router.get("/states")
async def get_states(
    service: ExploreService = Depends(get_explore_service)
):
    """
    Returns list of Indian states with IDs from the portal.
    """
    return await service.get_states()

@router.get("/cities")
async def get_cities(
    state_id: str,
    service: ExploreService = Depends(get_explore_service)
):
    """
    Returns list of cities with IDs for a specific state.
    """
    return await service.get_cities(state_id)

@router.post("/ai-search")
async def ai_search_tenders(
    request: TenderAISearchRequest,
    service: ExploreService = Depends(get_explore_service)
):
    """
    Parses a natural language query (e.g. 'Construction Tenders') using Tender247's AI Search API.
    Returns the parsed query metadata and payload.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return await service.ai_search(request.query, request.variables)

@router.post("/search")
async def search_tenders(
    payload: Dict[str, Any],
    service: ExploreService = Depends(get_explore_service)
):
    """
    Searches tenders on Tender247 using filter payload.
    Handles fallback: if search_by = 2 fails or yields no results, automatically retries with search_by = 0.
    """
    return await service.search_tenders(payload)

@router.post("/count")
async def count_tenders(
    payload: Dict[str, Any],
    service: ExploreService = Depends(get_explore_service)
):
    """
    Retrieves the total count of matching tenders from Tender247.
    """
    return await service.count_tenders(payload)

@router.post("/ai-search-with-results")
async def ai_search_with_results(
    request: TenderAISearchRequest,
    service: ExploreService = Depends(get_explore_service)
):
    """
    Executes AI search query and immediately fetches the first page of results + count
    for seamless fast UI rendering.
    """
    ai_res = await service.ai_search(request.query, request.variables)
    if not ai_res or ai_res.get("status") != "success" or not ai_res.get("data"):
        return {
            "status": "error",
            "message": ai_res.get("message") or "AI search failed",
            "ai_data": ai_res,
            "search_result": None,
            "count_result": None
        }

    payload = ai_res["data"].get("payload") or {}
    # Fetch results
    search_res = await service.search_tenders(payload)
    # Fetch count
    count_res = await service.count_tenders(payload)

    return {
        "status": "success",
        "ai_data": ai_res,
        "search_result": search_res,
        "count_result": count_res,
        "payload": payload
    }

@router.post("/import")
async def import_tender(
    request: ImportTenderRequest,
    service: ExploreService = Depends(get_explore_service)
):
    """
    Imports an explored tender into TenderMate's local Opportunities.
    """
    return await service.import_tender_to_opportunities(request.tender)

