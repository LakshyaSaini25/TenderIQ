from datetime import datetime, timezone
from fastapi import HTTPException
from app.repositories.source_repository import SourceRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.crawl_log_repository import CrawlLogRepository
from app.collectors.fetcher import Fetcher
from app.collectors.parser import Parser
from app.collectors.normalizer import Normalizer
from app.schemas.content import ContentStatus
from app.schemas.crawl_log import CrawlStatus, CrawlResult
import logging

logger = logging.getLogger(__name__)

class ContentService:
    def __init__(self):
        self.source_repo = SourceRepository()
        self.content_repo = ContentRepository()
        self.crawl_log_repo = CrawlLogRepository()

    async def collect_source(self, source_id: str):
        started_at = datetime.now(timezone.utc)
        
        # 1. Load source
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        if not source.get("is_active"):
            raise HTTPException(status_code=400, detail="Source is not active")
            
        url = source["url"]
        
        # 2. Fetch URL
        status_code, html, error = await Fetcher.fetch_html(url)
        
        if error or not html:
            # Log failure
            await self._log_crawl(
                source_id=source_id, url=url, status=CrawlStatus.FAILED,
                http_status=status_code, error=error, started_at=started_at
            )
            # Update source last_checked_at
            await self.source_repo.update(source_id, {"last_checked_at": datetime.now(timezone.utc)})
            
            return {
                "status": "FAILED",
                "source_id": source_id,
                "url": url,
                "error": error
            }

        # 3. Parse HTML
        parsed_data = Parser.parse_html(html)
        title = parsed_data.get("title", "")
        raw_text = parsed_data.get("raw_text", "")
        
        # 4. Normalize & Hash
        normalized_text = Normalizer.normalize_text(raw_text)
        content_hash = Normalizer.generate_hash(normalized_text)
        
        # 5. Check existing content
        existing_content = await self.content_repo.get_by_source_and_url(source_id, url)
        now = datetime.now(timezone.utc)
        
        result_status = None
        content_id = None
        
        if not existing_content:
            # Create new content
            new_content = {
                "source_id": source_id,
                "url": url,
                "title": title,
                "content": normalized_text,
                "content_hash": content_hash,
                "first_seen_at": now,
                "last_seen_at": now,
                "status": ContentStatus.ACTIVE
            }
            created = await self.content_repo.create(new_content)
            content_id = created["_id"]
            result_status = CrawlResult.CREATED
            
        else:
            content_id = existing_content["_id"]
            if existing_content.get("content_hash") == content_hash:
                # Unchanged
                await self.content_repo.update(content_id, {"last_seen_at": now})
                result_status = CrawlResult.UNCHANGED
            else:
                # Updated
                await self.content_repo.update(content_id, {
                    "title": title,
                    "content": normalized_text,
                    "content_hash": content_hash,
                    "last_seen_at": now
                })
                result_status = CrawlResult.UPDATED

        # 6. Update source
        await self.source_repo.update(source_id, {"last_checked_at": now})
        
        # 7. Log success
        await self._log_crawl(
            source_id=source_id, url=url, status=CrawlStatus.SUCCESS,
            result=result_status, http_status=status_code, started_at=started_at
        )

        response = {
            "status": result_status.value,
            "source_id": source_id,
            "url": url
        }
        if result_status != CrawlResult.UNCHANGED:
            response["content_id"] = content_id
            
        return response

    async def _log_crawl(self, source_id, url, status, started_at, result=None, http_status=None, error=None):
        completed_at = datetime.now(timezone.utc)
        log_data = {
            "source_id": source_id,
            "url": url,
            "status": status.value,
            "result": result.value if result else None,
            "http_status": http_status,
            "error": error,
            "started_at": started_at,
            "completed_at": completed_at
        }
        await self.crawl_log_repo.create(log_data)

    async def get_all_content(self, skip: int = 0, limit: int = 100):
        return await self.content_repo.get_all(skip=skip, limit=limit)

    async def get_content(self, content_id: str):
        content = await self.content_repo.get_by_id(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        return content

