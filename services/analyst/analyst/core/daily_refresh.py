import logging
from datetime import datetime, timezone
from typing import List, Optional

from ..db import Database
from .expert_recommendation_engine import ExpertRecommendationEngine
from .insight_generator import InsightGenerator

logger = logging.getLogger(__name__)

DAILY_REFRESH_LOCK_ID = 918273645


async def _get_latest_timestamp(
    db: Database,
    table: str,
    zone_ids: List[str],
    restrict_to_expert: bool = False
) -> Optional[datetime]:
    if not zone_ids:
        return None

    if restrict_to_expert:
        query = (
            f"SELECT MAX(created_at) FROM {table} "
            "WHERE zone_id = ANY($1::text[]) AND proposal ? 'expert_framework'"
        )
    else:
        query = f"SELECT MAX(created_at) FROM {table} WHERE zone_id = ANY($1::text[])"

    return await db.fetchval(query, zone_ids)


async def ensure_daily_refresh(
    db: Database,
    zone_ids: List[str],
    force_refresh: bool
):
    """Ensure insights and recommendations refresh at most once per day."""

    if not zone_ids:
        return

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    refresh_insights = force_refresh
    refresh_recommendations = force_refresh

    if not force_refresh:
        latest_insight = await _get_latest_timestamp(db, 'insights', zone_ids)
        latest_recommendation = await _get_latest_timestamp(
            db,
            'recommendations',
            zone_ids,
            restrict_to_expert=True
        )

        refresh_insights = latest_insight is None or latest_insight < today
        refresh_recommendations = (
            latest_recommendation is None or latest_recommendation < today
        )

        if not (refresh_insights or refresh_recommendations):
            logger.info("Daily refresh skipped – existing data is current")
            return

    async with db.transaction() as conn:
        await conn.execute(
            "SELECT pg_advisory_lock($1)", DAILY_REFRESH_LOCK_ID
        )

        try:
            if not force_refresh:
                latest_insight = await _get_latest_timestamp(db, 'insights', zone_ids)
                latest_recommendation = await _get_latest_timestamp(
                    db,
                    'recommendations',
                    zone_ids,
                    restrict_to_expert=True
                )

                refresh_insights = latest_insight is None or latest_insight < today
                refresh_recommendations = (
                    latest_recommendation is None or latest_recommendation < today
                )

                if not (refresh_insights or refresh_recommendations):
                    logger.info("Data became fresh while waiting for lock; skipping refresh")
                    return

            if refresh_insights:
                logger.info("Starting insight regeneration job")
                insight_generator = InsightGenerator(db)
                try:
                    fresh_insights = await insight_generator.generate_insights_for_all_zones(zone_ids)
                    if fresh_insights:
                        await insight_generator.save_insights(fresh_insights)
                    else:
                        logger.warning("Insight regeneration produced no results")
                except Exception as exc:
                    logger.error("Insight regeneration failed: %s", exc, exc_info=True)
                    if force_refresh:
                        raise

            if refresh_recommendations:
                logger.info("Starting expert recommendation regeneration job")
                expert_engine = ExpertRecommendationEngine(db)
                try:
                    await expert_engine.generate_recommendations_for_all_zones(zone_ids)
                except Exception as exc:
                    logger.error("Expert recommendation regeneration failed: %s", exc, exc_info=True)
                    if force_refresh:
                        raise

        finally:
            await conn.fetchval("SELECT pg_advisory_unlock($1)", DAILY_REFRESH_LOCK_ID)
