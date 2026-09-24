from abc import ABC, abstractmethod
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from .schema import TenderSchema, ScraperRunStats
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.repositories.scraped_tender_repository import ScrapedTenderRepository

logger = logging.getLogger(__name__)


class BaseTenderScraper(ABC):
    """
    Abstract Base Class for all website-specific tender scrapers.
    Defines the standard lifecycle:
        fetch() -> parse() -> extract_tenders() -> normalize() -> save()
    """

    def __init__(self, source_name: str, repository: Optional['ScrapedTenderRepository'] = None):
        self.source_name = source_name
        if repository is None:
            from app.repositories.scraped_tender_repository import ScrapedTenderRepository
            self.repository = ScrapedTenderRepository()
        else:
            self.repository = repository
        self.logger = logging.getLogger(f"scraper.{source_name.lower()}")

    @abstractmethod
    async def fetch(self, page: int = 1, **kwargs) -> Any:
        """
        Fetch the raw listing content (HTML or JSON) for a specific page.
        """
        pass

    @abstractmethod
    def parse(self, raw_content: Any) -> Any:
        """
        Parse raw content into an intermediary structure (e.g. BeautifulSoup or Dict).
        """
        pass

    @abstractmethod
    def extract_tenders(self, parsed_data: Any) -> List[Dict[str, Any]]:
        """
        Extract individual tender dictionary records from the parsed listing.
        """
        pass

    @abstractmethod
    def normalize(self, raw_tender: Dict[str, Any]) -> TenderSchema:
        """
        Convert website-specific raw tender data into the universal TenderSchema.
        """
        pass

    async def save(self, tenders: List[TenderSchema]) -> Dict[str, int]:
        """
        Saves a list of normalized tenders into the database with deduplication / upsert.
        Returns counts: {'new': int, 'updated': int, 'failed': int}.
        """
        new_count = 0
        updated_count = 0
        failed_count = 0

        for tender in tenders:
            try:
                is_new, _ = await self.repository.upsert_tender(tender)
                if is_new:
                    new_count += 1
                else:
                    updated_count += 1
            except Exception as e:
                failed_count += 1
                self.logger.error(
                    f"[{self.source_name}] Failed to save tender {tender.reference_no or tender.source_id}: {e}"
                )

        return {"new": new_count, "updated": updated_count, "failed": failed_count}

    async def run(self, max_pages: int = 1, enrich_details: bool = True) -> ScraperRunStats:
        """
        Orchestrates the entire scraping execution with structured logging and metric tracking.
        """
        start_time = datetime.now(timezone.utc)
        stats = ScraperRunStats(
            source=self.source_name,
            started_at=start_time,
            status="RUNNING"
        )

        self.logger.info(f"[{self.source_name}] Scraper started (max_pages={max_pages}, enrich_details={enrich_details})")

        try:
            for page in range(1, max_pages + 1):
                self.logger.info(f"[{self.source_name}] Requesting page {page}...")
                stats.pages_requested += 1

                raw_content = await self.fetch(page=page)
                if not raw_content:
                    self.logger.info(f"[{self.source_name}] No content received for page {page}. Stopping.")
                    break

                parsed_data = self.parse(raw_content)
                raw_tenders = self.extract_tenders(parsed_data)

                if not raw_tenders:
                    self.logger.info(f"[{self.source_name}] No tenders found on page {page}. Ending pagination.")
                    break

                self.logger.info(f"[{self.source_name}] Page {page} -> Found {len(raw_tenders)} tenders")
                stats.tenders_found += len(raw_tenders)

                # Optionally enrich detail pages (if scraper supports it)
                if enrich_details and hasattr(self, "enrich_details"):
                    await self.enrich_details(raw_tenders)

                # Normalize all tenders
                normalized_batch: List[TenderSchema] = []
                for raw_item in raw_tenders:
                    try:
                        normalized = self.normalize(raw_item)
                        normalized_batch.append(normalized)
                    except Exception as err:
                        stats.failed_tenders += 1
                        self.logger.warning(f"[{self.source_name}] Normalization failed for tender: {err}")

                # Save batch to DB
                save_results = await self.save(normalized_batch)
                stats.new_tenders += save_results["new"]
                stats.updated_tenders += save_results["updated"]
                stats.failed_tenders += save_results["failed"]

            stats.status = "COMPLETED"

        except Exception as e:
            stats.status = "FAILED"
            stats.error_message = str(e)
            self.logger.exception(f"[{self.source_name}] Scraper execution failed: {e}")

        finally:
            end_time = datetime.now(timezone.utc)
            stats.completed_at = end_time
            stats.duration_seconds = (end_time - start_time).total_seconds()

            self.logger.info(
                f"[{self.source_name}] Completed in {stats.duration_seconds:.2f}s | "
                f"Pages: {stats.pages_requested} | Found: {stats.tenders_found} | "
                f"New: {stats.new_tenders} | Updated: {stats.updated_tenders} | Failed: {stats.failed_tenders}"
            )

        return stats
