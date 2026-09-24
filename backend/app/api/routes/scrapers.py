from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import logging

from app.scrapers.schema import TenderFilterParams, ScraperRunStats
from app.repositories.scraped_tender_repository import ScrapedTenderRepository
from app.scrapers.cppp_scraper import CPPPScraper

logger = logging.getLogger(__name__)

router = APIRouter()
repository = ScrapedTenderRepository()

# In-memory store for recent scraper runs
recent_runs: Dict[str, ScraperRunStats] = {}
scraper_lock = asyncio.Lock()


@router.get("/tenders", summary="Search and filter scraped tenders from local DB")
async def get_scraped_tenders(
    keyword: Optional[str] = Query(None, description="Search term for title, description, or ref number"),
    source: Optional[str] = Query(None, description="Filter by portal source, e.g. CPPP, GeM"),
    state: Optional[str] = Query(None, description="Filter by location / state"),
    category: Optional[str] = Query(None, description="Filter by category (Works, Goods, etc.)"),
    organisation: Optional[str] = Query(None, description="Filter by issuing organisation"),
    status: Optional[str] = Query(None, description="Filter by OPEN or CLOSED"),
    min_value: Optional[float] = Query(None, description="Minimum estimated tender value"),
    max_value: Optional[float] = Query(None, description="Maximum estimated tender value"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("closing_date", description="Field to sort by"),
    sort_order: int = Query(1, description="1 for Ascending, -1 for Descending"),
):
    """
    Directly queries our internal database of scraped tenders with high-performance multi-criteria filters.
    """
    params = TenderFilterParams(
        keyword=keyword,
        source=source,
        state=state,
        category=category,
        organisation=organisation,
        status=status,
        min_value=min_value,
        max_value=max_value,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    result = await repository.search_and_filter(params)
    return result


@router.get("/tenders/{tender_id}", summary="Get full details for a scraped tender")
async def get_scraped_tender(tender_id: str):
    tender = await repository.get_by_id(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


@router.get("/stats", summary="Get aggregated scraper statistics")
async def get_scraper_stats():
    stats = await repository.get_stats()
    stats["recent_runs"] = list(recent_runs.values())[-5:]
    return stats


async def _run_scraper_task(source: str, max_pages: int, enrich_details: bool):
    async with scraper_lock:
        if source.upper() == "CPPP":
            scraper = CPPPScraper(repository=repository)
        else:
            logger.error(f"Unknown scraper source: {source}")
            return

        run_result = await scraper.run(max_pages=max_pages, enrich_details=enrich_details)
        recent_runs[source.upper()] = run_result


@router.post("/run/{source}", summary="Trigger a scraper run on demand")
async def trigger_scraper(
    source: str,
    background_tasks: BackgroundTasks,
    max_pages: int = Query(1, ge=1, le=10, description="Number of pages to scrape"),
    enrich_details: bool = Query(True, description="Unlock full details and solve captchas"),
    async_mode: bool = Query(True, description="Run in background or wait for completion"),
):
    src_upper = source.upper()
    if src_upper not in ["CPPP"]:
        raise HTTPException(status_code=400, detail=f"Scraper for '{source}' is not registered yet. Available: CPPP")

    if async_mode:
        background_tasks.add_task(_run_scraper_task, src_upper, max_pages, enrich_details)
        return {
            "message": f"{src_upper} scraper launched in background.",
            "source": src_upper,
            "max_pages": max_pages,
            "enrich_details": enrich_details,
            "status": "RUNNING"
        }
    else:
        # Run synchronously and return result directly
        if src_upper == "CPPP":
            scraper = CPPPScraper(repository=repository)
        stats = await scraper.run(max_pages=max_pages, enrich_details=enrich_details)
        recent_runs[src_upper] = stats
        return stats
