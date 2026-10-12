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


@router.get("/tenders/{tender_id}/documents/{doc_index}/download", summary="Proxy and download official scraped tender document")
async def download_scraped_tender_document(tender_id: str, doc_index: int):
    """
    Proxies tender document access with proper portal session and referer headers.
    - If the URL is a direct file (PDF/ZIP/BOQ excel etc.), streams it as a download.
    - If the stored URL is a NIC/GePNIC portal detail page, serves the portal HTML with base tag and viewer banner.
    Bypasses 'Unauthorized Page' errors caused by missing portal session/referer headers.
    """
    tender = await repository.get_by_id(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    docs = tender.get("documents") or []
    if doc_index < 0 or doc_index >= len(docs):
        raise HTTPException(status_code=404, detail="Document index out of range")

    doc = docs[doc_index]
    doc_url = doc.get("url")
    doc_title = doc.get("name", f"tender_document_{doc_index+1}")
    if not doc_url:
        raise HTTPException(status_code=400, detail="Document has no URL")

    from urllib.parse import urlparse
    import httpx
    from fastapi.responses import HTMLResponse, Response

    parsed = urlparse(doc_url)
    portal_origin = f"{parsed.scheme}://{parsed.netloc}"

    is_nic_portal = any(host in parsed.netloc for host in [
        "eprocure.gov.in", "coalindiatenders.nic.in", "eprocurebhel.co.in",
        "eprocurentpc.nic.in", "etenders.gov.in", "eprocurebpcl.in",
        "bpcltenders.eproc.in", "nic.in"
    ])
    referer = "https://eprocure.gov.in/" if is_nic_portal else portal_origin

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
    }

    try:
        transport = httpx.AsyncHTTPTransport(retries=2, verify=False)
        async with httpx.AsyncClient(transport=transport, headers=headers, timeout=30.0, follow_redirects=True) as client:
            # Prime session on eprocure portal if NIC portal
            if is_nic_portal:
                try:
                    await client.get("https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata", headers={"Referer": "https://eprocure.gov.in/"})
                except Exception:
                    pass

            doc_resp = await client.get(doc_url, headers={"Referer": referer})
            content_type = doc_resp.headers.get("content-type", "").split(";")[0].strip().lower()

            # Case 1: Binary file
            binary_types = [
                "application/pdf", "application/zip", "application/octet-stream",
                "application/msword", "application/vnd.openxmlformats",
                "application/vnd.ms-excel"
            ]
            is_binary = any(bt in content_type for bt in binary_types)

            if is_binary and len(doc_resp.content) > 1024:
                safe_name = "".join(c for c in doc_title if c.isalnum() or c in " ._-").strip()
                if not any(safe_name.lower().endswith(e) for e in [".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx"]):
                    ext_map = {"pdf": ".pdf", "zip": ".zip", "msword": ".doc", "excel": ".xls"}
                    for k, v in ext_map.items():
                        if k in content_type:
                            safe_name += v
                            break
                    else:
                        safe_name += ".pdf"
                return Response(
                    content=doc_resp.content,
                    media_type=content_type or "application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{safe_name}"'}
                )

            # Case 2: HTML portal page (e.g. GePNIC detail view)
            html = doc_resp.text

            # Check for unauthorized page
            if any(phrase in html.lower() for phrase in [
                "unauthorized area", "service=restart", "you are attempting to access"
            ]):
                # Retry once with referer https://eprocure.gov.in/
                try:
                    doc_resp2 = await client.get(doc_url, headers={"Referer": "https://eprocure.gov.in/"})
                    if "unauthorized area" not in doc_resp2.text.lower():
                        html = doc_resp2.text
                except Exception:
                    pass

            banner_html = f"""
<div style="position:sticky;top:0;z-index:9999;background:#1e3a5f;color:#fff;padding:10px 16px;font-family:sans-serif;font-size:13px;display:flex;align-items:center;justify-content:space-between;gap:12px;box-shadow:0 2px 8px rgba(0,0,0,0.3)">
  <span>📋 <strong>TenderMate Portal Document Viewer</strong> — Viewing official portal page for: <em>{doc_title}</em></span>
  <div style="display:flex;gap:8px">
    <a href="{doc_url}" target="_blank" style="color:#7dd3fc;text-decoration:none;font-size:12px;">↗ Open Direct URL</a>
    <button onclick="window.close()" style="background:#ef4444;border:none;color:white;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:12px;">✕ Close</button>
  </div>
</div>
"""
            base_tag = f'<base href="{portal_origin}/">'
            if "<head>" in html:
                html = html.replace("<head>", f"<head>\n{base_tag}", 1)
            else:
                html = base_tag + html

            if "<body" in html:
                body_end = html.index("<body") + html[html.index("<body"):].index(">") + 1
                html = html[:body_end] + "\n" + banner_html + html[body_end:]
            else:
                html = banner_html + html

            return HTMLResponse(content=html, status_code=200)

    except Exception as e:
        logger.error(f"Error proxying scraped tender document {doc_url}: {e}")
        fallback_html = f"""<!DOCTYPE html>
<html>
<head><title>TenderMate — Document Access</title></head>
<body style="font-family:sans-serif;padding:40px;max-width:600px;margin:auto">
  <h2>📋 Tender Document Access</h2>
  <p>TenderMate could not automatically load the document stream. Portal session may have expired.</p>
  <p><strong>Document:</strong> {doc_title}</p>
  <a href="{doc_url}" target="_blank"
     style="display:inline-block;background:#2563eb;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;margin-top:12px">
    ↗ Open Official Government Link
  </a>
  <br><br>
  <a href="https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata" target="_blank"
     style="display:inline-block;background:#64748b;color:white;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:13px">
    🏛️ Go to CPPP Portal Homepage
  </a>
</body>
</html>"""
        return HTMLResponse(content=fallback_html, status_code=200)

