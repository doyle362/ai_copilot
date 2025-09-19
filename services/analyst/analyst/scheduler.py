import asyncio
import logging
from time import perf_counter
from typing import List, Optional

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .core.daily_refresh import ensure_daily_refresh
from .db import db
from .observability import record_refresh

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Coordinates background jobs for the Analyst service."""

    def __init__(self) -> None:
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._startup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if not settings.scheduler_enabled:
            logger.info("Scheduler disabled via configuration")
            return

        if getattr(db, "_pool", None) is None:
            logger.warning("Database not initialized – skipping scheduler startup")
            return

        # Create the scheduler bound to UTC so cron expressions map cleanly to CONFIG times
        self._scheduler = AsyncIOScheduler(timezone=pytz.utc)

        trigger = CronTrigger(
            hour=settings.scheduler_daily_refresh_hour_utc,
            minute=settings.scheduler_daily_refresh_minute_utc,
            timezone=pytz.utc,
        )

        self._scheduler.add_job(
            self._run_daily_refresh,
            trigger=trigger,
            name="daily_insight_refresh",
            misfire_grace_time=3600,  # allow one hour delay if the service was down
            coalesce=True,
        )

        self._scheduler.start()
        logger.info(
            "Scheduler started – daily refresh set for %02d:%02d UTC",
            settings.scheduler_daily_refresh_hour_utc,
            settings.scheduler_daily_refresh_minute_utc,
        )

        # Kick off an immediate refresh on startup without blocking the event loop
        self._startup_task = asyncio.create_task(self._run_startup_refresh())

    async def stop(self) -> None:
        if self._startup_task:
            await asyncio.shield(self._startup_task)
            self._startup_task = None

        if self._scheduler:
            await self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
            self._scheduler = None

    async def _run_startup_refresh(self) -> None:
        try:
            zone_ids = await self._resolve_zone_ids()
            start = perf_counter()
            await ensure_daily_refresh(db, zone_ids, force_refresh=False)
            record_refresh("startup_success", perf_counter() - start)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Startup refresh failed: %s", exc)
            record_refresh("startup_failure")

    async def _run_daily_refresh(self) -> None:
        logger.info("Daily refresh job triggered")
        zone_ids = await self._resolve_zone_ids()
        start = perf_counter()
        try:
            await ensure_daily_refresh(db, zone_ids, force_refresh=True)
            duration = perf_counter() - start
            record_refresh("success", duration)
            logger.info("Daily refresh completed for %d zones", len(zone_ids))
        except Exception as exc:  # pragma: no cover - defensive logging
            record_refresh("failure")
            logger.exception("Daily refresh job failed: %s", exc)

    async def _resolve_zone_ids(self) -> List[str]:
        configured = settings.scheduler_zone_ids_list
        if configured:
            return configured

        query = """
            SELECT DISTINCT zone::text AS zone_id
            FROM historical_transactions
            WHERE zone IS NOT NULL
        """
        results = await db.fetch(query)
        zone_ids = [row["zone_id"] for row in results if row.get("zone_id")]

        if not zone_ids:
            logger.warning(
                "No zone IDs found for scheduler, reverting to developer defaults"
            )
            return settings.dev_zone_ids_list

        return zone_ids


scheduler_manager = SchedulerManager()
