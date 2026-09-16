import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from app.repositories.source_repository import SourceRepository
from app.services.opportunity_service import OpportunityService

logger = logging.getLogger(__name__)

CRAWL_INTERVAL_SECONDS: Dict[str, int] = {
    "HOURLY": 3600,               # 1 hour
    "EVERY_6_HOURS": 6 * 3600,    # 6 hours
    "DAILY": 24 * 3600,           # 24 hours
    "WEEKLY": 7 * 24 * 3600,      # 7 days
}

DEFAULT_INTERVAL_SECONDS = 24 * 3600  # Default to 24h if unknown frequency


class CrawlScheduler:
    """
    Automated background scheduler that continuously checks active sources
    and executes crawls according to their defined crawl_frequency.
    """

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval_seconds = check_interval_seconds
        self.source_repo = SourceRepository()
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._currently_crawling: Set[str] = set()
        self.last_check_at: Optional[datetime] = None
        self.last_crawls_history: List[Dict[str, Any]] = []

    def is_due(self, source: Dict[str, Any]) -> tuple[bool, str, int]:
        """
        Determines whether a source is due for a crawl.
        Returns (is_due, reason, seconds_remaining_or_overdue).
        """
        if not source.get("is_active", False):
            return False, "Source is inactive", 0

        freq_str = str(source.get("crawl_frequency", "DAILY")).upper()
        interval = CRAWL_INTERVAL_SECONDS.get(freq_str, DEFAULT_INTERVAL_SECONDS)

        last_checked = source.get("last_checked_at")
        if not last_checked:
            return True, "Never crawled before", interval

        # Ensure last_checked is UTC aware
        if isinstance(last_checked, str):
            try:
                last_checked = datetime.fromisoformat(last_checked.replace("Z", "+00:00"))
            except Exception:
                return True, "Invalid last_checked date format", interval

        if last_checked.tzinfo is None:
            last_checked = last_checked.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        elapsed = (now - last_checked).total_seconds()

        if elapsed >= interval:
            overdue_by = int(elapsed - interval)
            return True, f"Overdue by {overdue_by}s (frequency: {freq_str})", -overdue_by

        remaining = int(interval - elapsed)
        return False, f"Next crawl in {remaining}s", remaining

    async def _execute_crawl(self, source_id: str, source_name: str):
        """
        Executes a crawl for a given source and logs result.
        """
        self._currently_crawling.add(source_id)
        start_time = datetime.now(timezone.utc)
        logger.info(f"⏰ [Scheduler] Starting automated crawl for source: {source_name} ({source_id})")
        
        result_entry: Dict[str, Any] = {
            "source_id": source_id,
            "source_name": source_name,
            "started_at": start_time.isoformat(),
            "status": "RUNNING",
            "stats": None,
            "error": None
        }

        try:
            opp_service = OpportunityService()
            stats = await opp_service.collect_opportunities(source_id)
            result_entry["status"] = "SUCCESS"
            result_entry["stats"] = stats
            logger.info(
                f"✅ [Scheduler] Completed crawl for {source_name}: "
                f"discovered={stats.get('discovered')}, created={stats.get('created')}, updated={stats.get('updated')}"
            )
        except Exception as e:
            result_entry["status"] = "FAILED"
            result_entry["error"] = str(e)
            logger.error(f"❌ [Scheduler] Automated crawl failed for {source_name}: {e}")
        finally:
            self._currently_crawling.discard(source_id)
            result_entry["completed_at"] = datetime.now(timezone.utc).isoformat()
            self.last_crawls_history.append(result_entry)
            # Keep history to last 50 runs
            if len(self.last_crawls_history) > 50:
                self.last_crawls_history = self.last_crawls_history[-50:]

    async def check_and_run_due_crawls(self) -> List[Dict[str, Any]]:
        """
        Checks all active sources and triggers crawls for any that are due.
        Returns list of sources triggered.
        """
        self.last_check_at = datetime.now(timezone.utc)
        sources = await self.source_repo.get_all()
        triggered = []

        for src in sources:
            source_id = str(src.get("_id") or src.get("id"))
            source_name = src.get("name", "Unnamed Source")

            if source_id in self._currently_crawling:
                logger.debug(f"[Scheduler] Source {source_name} is already being crawled. Skipping.")
                continue

            due, reason, _ = self.is_due(src)
            if due:
                logger.info(f"🔔 [Scheduler] Source due for crawl: '{source_name}' - Reason: {reason}")
                triggered.append({
                    "source_id": source_id,
                    "source_name": source_name,
                    "frequency": src.get("crawl_frequency"),
                    "reason": reason
                })
                # Spawn background task
                asyncio.create_task(self._execute_crawl(source_id, source_name))

        return triggered

    async def start(self):
        """
        Starts the background scheduling loop.
        """
        if self._running:
            logger.warning("[Scheduler] Scheduler is already running.")
            return

        self._running = True
        logger.info(f"🚀 [Scheduler] Automated Crawl Scheduler started (check interval: {self.check_interval_seconds}s)")

        # Initial check immediately on startup
        try:
            await self.check_and_run_due_crawls()
        except Exception as e:
            logger.error(f"[Scheduler] Error during startup check: {e}")

        while self._running:
            try:
                await asyncio.sleep(self.check_interval_seconds)
                if self._running:
                    await self.check_and_run_due_crawls()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Scheduler] Error in scheduler loop: {e}")
                await asyncio.sleep(5)

        logger.info("🛑 [Scheduler] Automated Crawl Scheduler stopped.")

    async def stop(self):
        """
        Stops the background scheduling loop.
        """
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def get_status(self) -> Dict[str, Any]:
        """
        Returns full diagnostic status of the scheduler and all tracked sources.
        """
        sources = await self.source_repo.get_all()
        now = datetime.now(timezone.utc)

        sources_diag = []
        for src in sources:
            source_id = str(src.get("_id") or src.get("id"))
            due, reason, rem = self.is_due(src)
            sources_diag.append({
                "source_id": source_id,
                "name": src.get("name"),
                "url": src.get("url"),
                "is_active": src.get("is_active", False),
                "frequency": src.get("crawl_frequency"),
                "last_checked_at": src.get("last_checked_at"),
                "is_due": due,
                "status_reason": reason,
                "seconds_remaining": rem,
                "is_currently_crawling": source_id in self._currently_crawling
            })

        return {
            "scheduler_running": self._running,
            "check_interval_seconds": self.check_interval_seconds,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None,
            "currently_crawling_count": len(self._currently_crawling),
            "sources": sources_diag,
            "recent_crawls": self.last_crawls_history[-10:]
        }


# Global singleton instance
_scheduler_instance: Optional[CrawlScheduler] = None

def get_crawl_scheduler() -> CrawlScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = CrawlScheduler(check_interval_seconds=60)
    return _scheduler_instance

