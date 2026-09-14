import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from app.repositories.source_repository import SourceRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.opportunity_repository import OpportunityRepository
from app.repositories.crawl_log_repository import CrawlLogRepository
from app.repositories.ai_log_repository import AILogRepository
from app.collectors.adapters.registry import AdapterRegistry
from app.collectors.fetcher import Fetcher
from app.collectors.normalizer import Normalizer
from app.processors.opportunity_processor import OpportunityProcessor
from app.ai.opportunity_extractor import OpportunityAIExtractor
from app.schemas.crawl_log import CrawlStatus

logger = logging.getLogger(__name__)

class OpportunityService:
    def __init__(self):
        self.source_repo = SourceRepository()
        self.content_repo = ContentRepository()
        self.opportunity_repo = OpportunityRepository()
        self.crawl_log_repo = CrawlLogRepository()
        self.ai_log_repo = AILogRepository()
        self.ai_extractor = OpportunityAIExtractor()

    async def collect_opportunities(self, source_id: str) -> Dict[str, Any]:
        """
        Runs scraper adapter to discover & extract opportunities from source URL.
        """
        started_at = datetime.now(timezone.utc)
        
        # 1. Load source
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
            
        if not source.get("is_active"):
            raise HTTPException(status_code=400, detail="Source is not active")

        source_url = source["url"]

        # 2. Select Adapter
        adapter = AdapterRegistry.get_adapter_for_source(source)
        logger.info(f"Using adapter {adapter.__class__.__name__} for source: {source.get('name')}")

        stats = {
            "source_id": source_id,
            "discovered": 0,
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "failed": 0
        }

        # Track opportunity IDs for auto captcha enrichment
        created_opp_ids: List[str] = []

        try:
            # 3. Discover URLs
            discovered_urls = await adapter.discover_listing_urls(source_url)
            stats["discovered"] = len(discovered_urls)
            logger.info(f"Discovered {len(discovered_urls)} tender URLs from {source_url}")

            # 4. Fetch & Extract each opportunity
            is_ollama_online = False
            try:
                is_ollama_online = await self.ai_extractor.ollama_client.check_health()
            except Exception:
                is_ollama_online = False

            total_discovered = 0

            for url in discovered_urls:
                try:
                    status_code, html, fetch_err = await Fetcher.fetch_html(url)
                    if fetch_err or not html:
                        logger.error(f"Fetch error on {url}: {fetch_err}")
                        stats["failed"] += 1
                        continue

                    raw_extract = await adapter.extract_opportunity(url, html, source_id)
                    if not raw_extract:
                        stats["failed"] += 1
                        continue

                    # Support adapters returning either a single dict or a list of tender dicts
                    opp_items = raw_extract if isinstance(raw_extract, list) else [raw_extract]
                    total_discovered += len(opp_items)

                    for opp_item in opp_items:
                        try:
                            # 5. Automatically create/update a content document for audit/verification and AI linking
                            item_url = opp_item.get("source_url") or url
                            raw_content = opp_item.pop("raw_content", None) or (
                                f"Title: {opp_item.get('title')}\n"
                                f"Reference Number: {opp_item.get('reference_number')}\n"
                                f"Organization: {opp_item.get('organization')}\n"
                                f"Published Date: {opp_item.get('published_at')}\n"
                                f"Closing Date: {opp_item.get('deadline')}\n"
                                f"Description: {opp_item.get('description')}"
                            )
                            raw_html = opp_item.pop("raw_html", None) or html

                            content_hash = Normalizer.generate_hash(raw_content)

                            existing_content = await self.content_repo.get_by_source_and_url(source_id, item_url)
                            if existing_content:
                                content_doc = await self.content_repo.update(existing_content["_id"], {
                                    "title": opp_item.get("title", ""),
                                    "content": raw_content,
                                    "raw_html": raw_html,
                                    "content_hash": content_hash,
                                    "last_seen_at": datetime.now(timezone.utc),
                                    "is_opportunity": True,
                                    "opportunity_type": opp_item.get("type", "TENDER"),
                                })
                            else:
                                content_doc = await self.content_repo.create({
                                    "source_id": source_id,
                                    "url": item_url,
                                    "title": opp_item.get("title", ""),
                                    "content": raw_content,
                                    "raw_html": raw_html,
                                    "content_hash": content_hash,
                                    "first_seen_at": datetime.now(timezone.utc),
                                    "last_seen_at": datetime.now(timezone.utc),
                                    "is_opportunity": True,
                                    "opportunity_type": opp_item.get("type", "TENDER"),
                                })

                            if content_doc and "_id" in content_doc:
                                opp_item["content_id"] = str(content_doc["_id"])

                            # 6. Upsert / Deduplicate Opportunity
                            result_status, opp_doc = await self.opportunity_repo.upsert_opportunity(opp_item)
                            if result_status == "CREATED":
                                stats["created"] += 1
                            elif result_status == "UPDATED":
                                stats["updated"] += 1
                            elif result_status == "UNCHANGED":
                                stats["unchanged"] += 1

                            # Track for auto captcha enrichment (only unenriched CPPP opps)
                            if opp_doc and opp_doc.get("_id") and not opp_doc.get("detail_solved"):
                                created_opp_ids.append(str(opp_doc["_id"]))

                            # 7. If Ollama is running and available, automatically enrich with AI
                            if is_ollama_online and opp_doc and content_doc:
                                try:
                                    ai_result = await self.ai_extractor.extract(content_doc, opp_doc)
                                    if ai_result.get("status") == "SUCCESS":
                                        enriched = ai_result.get("enriched_fields", {})
                                        if enriched:
                                            await self.opportunity_repo.update(opp_doc["_id"], enriched)
                                except Exception as ai_e:
                                    logger.warning(f"Auto AI enrichment skipped for {item_url}: {ai_e}")

                        except Exception as item_err:
                            logger.error(f"Error saving tender item: {item_err}")
                            stats["failed"] += 1

                except Exception as page_err:
                    logger.error(f"Error processing page {url}: {page_err}")
                    stats["failed"] += 1

            stats["discovered"] = total_discovered or len(discovered_urls)

            # 6. Update source last_checked_at
            now = datetime.now(timezone.utc)
            await self.source_repo.update(source_id, {"last_checked_at": now})

            # 7. Log crawl attempt
            await self._log_crawl(
                source_id=source_id,
                url=source_url,
                status=CrawlStatus.SUCCESS,
                started_at=started_at,
                stats=stats
            )

            # 8. Auto-enrich collected opportunities with CAPTCHA solver in background queue
            # (Queue batch size: 3, Jitter: 2-3s between batches)
            if created_opp_ids:
                logger.info(f"Auto-enriching {len(created_opp_ids)} opportunities with CAPTCHA solver in background queue")
                for opp_id in created_opp_ids:
                    try:
                        await self.opportunity_repo.update(opp_id, {"detail_enriching": True})
                    except Exception:
                        pass
                asyncio.create_task(self.batch_refresh_opportunities(created_opp_ids))

            return stats

        except Exception as e:
            logger.error(f"Collection error for source {source_id}: {e}")
            await self._log_crawl(
                source_id=source_id,
                url=source_url,
                status=CrawlStatus.FAILED,
                started_at=started_at,
                error=str(e),
                stats=stats
            )
            raise HTTPException(status_code=500, detail=f"Collection failed: {str(e)}")

    async def process_single_content(self, content_id: str) -> Dict[str, Any]:
        """
        Processes a single content item into an opportunity using OpportunityProcessor.
        """
        content_doc = await self.content_repo.get_by_id(content_id)
        if not content_doc:
            raise HTTPException(status_code=404, detail="Content not found")

        is_opp, status_reason, opp_data = OpportunityProcessor.process(content_doc)

        if not is_opp or not opp_data:
            return {
                "status": "NOT_AN_OPPORTUNITY",
                "is_opportunity": False,
                "type": None,
                "opportunity_id": None
            }

        result_status, opp_doc = await self.opportunity_repo.upsert_opportunity(opp_data)
        return {
            "status": result_status,
            "is_opportunity": True,
            "type": opp_data.get("type"),
            "opportunity_id": opp_doc.get("_id")
        }

    async def process_source_content(self, source_id: str) -> Dict[str, Any]:
        """
        Processes all collected content items belonging to a source into opportunities.
        """
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        contents = await self.content_repo.get_by_source(source_id)

        stats = {
            "source_id": source_id,
            "processed": len(contents),
            "opportunities_created": 0,
            "opportunities_updated": 0,
            "not_opportunities": 0,
            "failed": 0
        }

        for content_doc in contents:
            try:
                is_opp, status_reason, opp_data = OpportunityProcessor.process(content_doc)
                if not is_opp or not opp_data:
                    stats["not_opportunities"] += 1
                    continue

                res_status, _opp_doc = await self.opportunity_repo.upsert_opportunity(opp_data)
                if res_status == "CREATED":
                    stats["opportunities_created"] += 1
                elif res_status == "UPDATED":
                    stats["opportunities_updated"] += 1
                else:
                    # Unchanged counts towards processed opportunity
                    pass

            except Exception as e:
                logger.error(f"Error processing content {content_doc.get('_id')}: {e}")
                stats["failed"] += 1

        return stats

    async def ai_process_single_content(self, content_id: str) -> Dict[str, Any]:
        """
        Runs AI extraction on a content item to enrich an existing opportunity.
        First ensures an opportunity exists (via rules), then enriches it with Ollama AI.
        """
        started_at = datetime.now(timezone.utc)

        # 1. Load content
        content_doc = await self.content_repo.get_by_id(content_id)
        if not content_doc:
            raise HTTPException(status_code=404, detail="Content not found")

        # 2. Check if opportunity already exists for this content, or generate via rules
        opp_doc = await self.opportunity_repo.get_by_content_id(content_id)
        if not opp_doc:
            is_opp, status_reason, opp_data = OpportunityProcessor.process(content_doc)
            if not is_opp or not opp_data:
                return {
                    "content_id": content_id,
                    "opportunity_id": None,
                    "ai_status": "SKIPPED",
                    "ai_model": None,
                    "processing_duration": 0.0,
                    "enriched_fields": [],
                    "message": "Content does not qualify as an opportunity"
                }
            _res_status, opp_doc = await self.opportunity_repo.upsert_opportunity(opp_data)

        opportunity_id = opp_doc.get("_id") if opp_doc else None

        # 3. Run AI extraction
        ai_result = await self.ai_extractor.extract(content_doc, opp_doc or opp_data)

        duration = (datetime.now(timezone.utc) - started_at).total_seconds()

        # 4. Log AI processing attempt
        await self.ai_log_repo.log_process({
            "content_id": content_id,
            "opportunity_id": opportunity_id,
            "model": ai_result.get("model"),
            "processing_status": ai_result.get("status"),
            "processing_duration": duration,
            "prompt_version": ai_result.get("prompt_version"),
            "error": ai_result.get("error"),
            "timestamp": started_at
        })

        # 5. If AI succeeded, update opportunity with enriched fields
        if ai_result.get("status") == "SUCCESS" and opportunity_id:
            enriched = ai_result.get("enriched_fields", {})
            if enriched:
                await self.opportunity_repo.update(opportunity_id, enriched)

        return {
            "content_id": content_id,
            "opportunity_id": opportunity_id,
            "ai_status": ai_result.get("status"),
            "ai_model": ai_result.get("model"),
            "processing_duration": duration,
            "enriched_fields": list(ai_result.get("enriched_fields", {}).keys()),
            "message": ai_result.get("error") or "AI processing complete"
        }

    async def _log_crawl(
        self,
        source_id: str,
        url: str,
        status: CrawlStatus,
        started_at: datetime,
        stats: Dict[str, Any],
        error: Optional[str] = None
    ):
        completed_at = datetime.now(timezone.utc)
        log_data = {
            "source_id": source_id,
            "url": url,
            "status": status.value,
            "discovered": stats.get("discovered", 0),
            "created": stats.get("created", 0),
            "updated": stats.get("updated", 0),
            "unchanged": stats.get("unchanged", 0),
            "failed": stats.get("failed", 0),
            "error": error,
            "started_at": started_at,
            "completed_at": completed_at
        }
        await self.crawl_log_repo.create(log_data)

    async def get_all_opportunities(
        self,
        source_id: Optional[str] = None,
        type_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        category_id_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        return await self.opportunity_repo.get_all(
            source_id=source_id,
            type_filter=type_filter,
            status_filter=status_filter,
            category_id_filter=category_id_filter,
            skip=skip,
            limit=limit
        )

    async def count_opportunities(
        self,
        source_id: Optional[str] = None,
        type_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        category_id_filter: Optional[str] = None
    ) -> int:
        return await self.opportunity_repo.count(
            source_id=source_id,
            type_filter=type_filter,
            status_filter=status_filter,
            category_id_filter=category_id_filter
        )

    async def get_opportunity(self, opportunity_id: str) -> Dict[str, Any]:
        opp = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        return opp

    async def batch_refresh_opportunities(self, opportunity_ids: List[str]) -> Dict[str, Any]:
        """
        Refresh a batch of opportunities using a semaphore to limit concurrency to 3.
        Sleeps 2 to 3 seconds (jitter) between batches of 3 requests to avoid portal rate limits.
        Returns a summary dict with counts of processed, succeeded, failed.
        """
        if not opportunity_ids:
            return {"processed": 0, "succeeded": 0, "failed": 0}

        semaphore = asyncio.Semaphore(3)
        processed = 0
        succeeded = 0
        failed = 0

        async def _refresh_one(opp_id: str):
            async with semaphore:
                try:
                    await self.refresh_opportunity_detail(opp_id)
                    return True
                except Exception as e:
                    logger.error(f"Batch refresh failed for {opp_id}: {e}")
                    try:
                        await self.opportunity_repo.update(opp_id, {"detail_enriching": False})
                    except Exception:
                        pass
                    return False

        # Process in batches of 3
        for i in range(0, len(opportunity_ids), 3):
            batch = opportunity_ids[i:i+3]
            logger.info(f"Processing batch of {len(batch)} opportunities for captcha solve & enrichment ({i+1}-{i+len(batch)} of {len(opportunity_ids)})")
            results = await asyncio.gather(*[_refresh_one(oid) for oid in batch])
            processed += len(batch)
            succeeded += sum(1 for r in results if r)
            failed += sum(1 for r in results if not r)
            if i + 3 < len(opportunity_ids):
                jitter = random.uniform(2.0, 3.0)
                logger.info(f"Waiting {jitter:.2f}s jitter before next batch...")
                await asyncio.sleep(jitter)

        logger.info(f"Batch refresh finished: {processed} processed, {succeeded} succeeded, {failed} failed")
        return {"processed": processed, "succeeded": succeeded, "failed": failed}

    async def refresh_opportunity_detail(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Re-fetches fresh detail data for an opportunity by resolving its portal link
        and solving any captcha on-demand. Gracefully handles portals with no structured
        fields or failed captchas by leaving the record as is.
        """
        opp = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        # Mark as enriching so UI can display shimmer/loading indicators
        await self.opportunity_repo.update(opportunity_id, {"detail_enriching": True})

        source = await self.source_repo.get_by_id(opp["source_id"])
        source_url = source["url"] if source else "https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata"

        # Check if CPPP source
        is_cppp = "eprocure.gov.in" in source_url or "cppp" in source_url or "cppp" in opp.get("source_url", "")

        if not is_cppp:
            await self.opportunity_repo.update(opportunity_id, {"detail_enriching": False})
            return opp

        from app.collectors.captcha_solver import CaptchaSolver
        import httpx
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        transport = httpx.AsyncHTTPTransport(retries=3, verify=False)

        try:
            async with httpx.AsyncClient(transport=transport, headers=headers, timeout=35.0, follow_redirects=True) as client:
                # 1. Start fresh session by hitting listing page
                try:
                    list_resp = await client.get(source_url)
                    if list_resp.status_code != 200:
                        logger.warning(f"Could not reach tender portal {source_url} (HTTP {list_resp.status_code})")
                        await self.opportunity_repo.update(opportunity_id, {"detail_enriching": False})
                        return opp
                    soup = BeautifulSoup(list_resp.text, "html.parser")
                except Exception as net_err:
                    logger.warning(f"Connection error to portal {source_url}: {net_err}")
                    await self.opportunity_repo.update(opportunity_id, {"detail_enriching": False})
                    return opp

                # 2. Locate fresh detail URL for this tender by reference_number, tender_id, or title
                target_ref = (opp.get("reference_number") or "").strip().lower()
                target_title = (opp.get("title") or "").strip().lower()
                fresh_detail_url = None

                for tr in soup.find_all("tr"):
                    tr_text = tr.get_text().lower()
                    if (target_ref and target_ref in tr_text) or (target_title and target_title[:40] in tr_text):
                        a_tag = tr.find("a", href=True)
                        if a_tag and "/cppp/tendersfullview/" in a_tag["href"]:
                            href = a_tag["href"].strip()
                            fresh_detail_url = f"https://eprocure.gov.in{href}" if href.startswith("/") else href
                            break

                # Fallback to stored source_url if not found in current 1st page
                if not fresh_detail_url:
                    fresh_detail_url = opp.get("source_url")

                if not fresh_detail_url:
                    logger.warning(f"No detail URL found for tender {opportunity_id}. Leaving record as is.")
                    await self.opportunity_repo.update(opportunity_id, {"detail_enriching": False})
                    return opp

                # 3. Solve captcha and retrieve detail page
                detail_html, err = await CaptchaSolver.solve_and_fetch_detail(client, fresh_detail_url, list_url=source_url)
                if not detail_html:
                    logger.warning(f"Could not bypass captcha for opp {opportunity_id}: {err}. Leaving record as is.")
                    await self.opportunity_repo.update(opportunity_id, {"detail_enriching": False})
                    return opp

                fields, docs = CaptchaSolver.parse_cppp_detail_html(detail_html, base_url=fresh_detail_url)
                if not fields and not docs:
                    # Gracefully handle: leave the record as it is without failing
                    logger.warning(f"No structured detail fields found on page for opp {opportunity_id}. Leaving record as is without update.")
                    await self.opportunity_repo.update(opportunity_id, {"detail_enriching": False})
                    return opp

                # 4. Prepare update fields
                patch_data: Dict[str, Any] = {
                    "source_url": fresh_detail_url,
                    "detail_solved": True,
                    "detail_enriching": False,
                }
                if fields.get("work_description"):
                    patch_data["description"] = fields["work_description"][:2000]
                if fields.get("organization"):
                    patch_data["organization"] = fields["organization"]
                if fields.get("location"):
                    patch_data["location"] = fields["location"]
                if fields.get("pincode"):
                    patch_data["pincode"] = fields["pincode"]
                if fields.get("tender_fee"):
                    patch_data["tender_fee"] = fields["tender_fee"]
                if fields.get("emd_amount"):
                    patch_data["emd_amount"] = fields["emd_amount"]
                if fields.get("tender_category"):
                    patch_data["tender_category"] = fields["tender_category"]
                    patch_data["category_name"] = fields["tender_category"]
                if fields.get("product_category"):
                    patch_data["product_category"] = fields["product_category"]
                if fields.get("inviting_authority_name"):
                    patch_data["inviting_authority_name"] = fields["inviting_authority_name"]
                if fields.get("inviting_authority_address"):
                    patch_data["inviting_authority_address"] = fields["inviting_authority_address"]
                if docs:
                    patch_data["documents"] = docs

                updated_opp = await self.opportunity_repo.update(opportunity_id, patch_data)

                # Also update linked content document if present
                content_id = opp.get("content_id")
                if content_id:
                    try:
                        await self.content_repo.update(content_id, {
                            "content": (
                                f"Title: {updated_opp.get('title')}\n"
                                f"Reference Number: {updated_opp.get('reference_number')}\n"
                                f"Organization: {updated_opp.get('organization')}\n"
                                f"Work Description: {patch_data.get('description', '')}\n"
                                f"Tender Fee: {patch_data.get('tender_fee', 'N/A')}\n"
                                f"EMD Amount: {patch_data.get('emd_amount', 'N/A')}\n"
                                f"Location: {patch_data.get('location', '')}\n"
                                f"Inviting Authority: {patch_data.get('inviting_authority_name', '')}\n"
                                f"Address: {patch_data.get('inviting_authority_address', '')}\n"
                                f"Documents: {', '.join([d.get('url', '') for d in docs])}"
                            ),
                            "raw_html": detail_html,
                        })
                    except Exception:
                        pass

                return updated_opp or opp

        except Exception as e:
            logger.error(f"Error during refresh for opportunity {opportunity_id}: {e}. Leaving record as is.")
            await self.opportunity_repo.update(opportunity_id, {"detail_enriching": False})
            return opp

    async def download_document(self, opportunity_id: str, doc_index: int):
        """
        Proxies tender document downloads with proper portal session and referer headers
        to bypass portal 'Unauthorized Page' restrictions.
        """
        opp = await self.opportunity_repo.get_by_id(opportunity_id)
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        docs = opp.get("documents") or []
        if doc_index < 0 or doc_index >= len(docs):
            raise HTTPException(status_code=404, detail="Document index out of range")

        doc = docs[doc_index]
        doc_url = doc.get("url")
        doc_title = doc.get("title", f"tender_document_{doc_index+1}")
        if not doc_url:
            raise HTTPException(status_code=400, detail="Document has no URL")

        source_url = opp.get("source_url") or "https://eprocure.gov.in"
        from urllib.parse import urlparse
        parsed = urlparse(doc_url)
        portal_origin = f"{parsed.scheme}://{parsed.netloc}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": source_url,
            "Origin": portal_origin,
        }
        import httpx
        from fastapi.responses import Response, RedirectResponse
        transport = httpx.AsyncHTTPTransport(retries=3, verify=False)

        try:
            async with httpx.AsyncClient(transport=transport, headers=headers, timeout=35.0, follow_redirects=True) as client:
                # Prime session on target portal if needed
                try:
                    await client.get(source_url)
                except Exception:
                    pass

                doc_resp = await client.get(doc_url, headers={"Referer": source_url})
                content_type = doc_resp.headers.get("content-type", "application/octet-stream").split(";")[0].strip()

                # If server returned an HTML error or restart/unauthorized page
                if "unauthorized area" in doc_resp.text.lower() or "service=restart" in doc_resp.text.lower():
                    # Fallback: Redirect user to the portal page where they can access it directly
                    return RedirectResponse(url=source_url)

                # Generate clean filename
                safe_filename = "".join(c for c in doc_title if c.isalnum() or c in (" ", ".", "_", "-")).strip()
                if not any(safe_filename.lower().endswith(ext) for ext in [".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx", ".rar"]):
                    if "pdf" in content_type:
                        safe_filename += ".pdf"
                    elif "zip" in content_type:
                        safe_filename += ".zip"
                    else:
                        safe_filename += ".pdf"

                return Response(
                    content=doc_resp.content,
                    media_type=content_type,
                    headers={
                        "Content-Disposition": f'attachment; filename="{safe_filename}"'
                    }
                )
        except Exception as e:
            logger.error(f"Error proxying document download {doc_url}: {e}")
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=source_url)

