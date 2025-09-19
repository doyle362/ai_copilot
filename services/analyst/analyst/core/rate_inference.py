import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pytz
import logging
from ..db import Database
from ..config import settings

logger = logging.getLogger(__name__)


class RateInference:
    def __init__(self, db: Database):
        self.db = db
        self.tz = pytz.timezone(settings.tz)

    async def infer_current_rates(self, zone_id: str, location_id: Optional[str] = None) -> Dict:
        """Infer current rate tiers from transaction data and store in inferred_rate_plans"""

        try:
            # Get recent transaction data
            transaction_data = await self._get_transaction_data(zone_id, location_id, days=30)

            if not transaction_data:
                logger.warning(f"No transaction data found for zone {zone_id}")
                return {"status": "no_data", "zone_id": zone_id}

            # Convert to DataFrame for analysis
            df = pd.DataFrame(transaction_data)
            df['created_at'] = pd.to_datetime(df['created_at'])

            # Add daypart and day of week
            df = self._add_time_features(df)

            # Infer rate tiers for each daypart/dow combination
            inferred_plans = []

            for dow in range(7):  # 0=Monday, 6=Sunday
                for daypart in ['morning', 'evening']:
                    mask = (df['dow'] == dow) & (df['daypart'] == daypart)
                    daypart_data = df[mask]

                    if len(daypart_data) < 10:  # Need minimum data
                        continue

                    tiers = self._infer_tiers_from_durations(daypart_data)

                    if tiers:
                        inferred_plans.append({
                            'location_id': location_id,
                            'zone_id': zone_id,
                            'daypart': daypart,
                            'dow': dow,
                            'tiers': tiers,
                            'source': 'transaction_analysis'
                        })

            # Store inferred plans
            await self._store_inferred_plans(inferred_plans)

            return {
                "status": "success",
                "zone_id": zone_id,
                "plans_generated": len(inferred_plans),
                "plans": inferred_plans
            }

        except Exception as e:
            logger.error(f"Error inferring rates for zone {zone_id}: {str(e)}")
            return {"status": "error", "zone_id": zone_id, "error": str(e)}

    async def _get_transaction_data(self, zone_id: str, location_id: Optional[str], days: int) -> List[Dict]:
        """Get recent transaction/stay data for analysis"""

        # This would query your actual transaction/stay tables
        # For now, simulate with mart data + synthetic stay durations
        query = """
            SELECT
                date::timestamp as created_at,
                zone_id,
                location_id,
                rev as total_amount,
                occupancy_pct,
                -- Simulate stay durations based on occupancy patterns
                CASE
                    WHEN occupancy_pct > 0.8 THEN 45 + (random() * 60)  -- 45-105 min high demand
                    WHEN occupancy_pct > 0.5 THEN 60 + (random() * 120) -- 60-180 min medium
                    ELSE 90 + (random() * 180)  -- 90-270 min low demand
                END as duration_minutes,
                -- Simulate hourly pricing based on revenue patterns
                CASE
                    WHEN occupancy_pct > 0.8 THEN 8.0 + (random() * 4)   -- $8-12/hr
                    WHEN occupancy_pct > 0.5 THEN 5.0 + (random() * 3)   -- $5-8/hr
                    ELSE 3.0 + (random() * 2)   -- $3-5/hr
                END as rate_per_hour
            FROM mart_metrics_daily
            WHERE zone_id = $1
                AND ($2::uuid IS NULL OR location_id = $2::uuid)
                AND date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY date DESC
            LIMIT 1000
        """ % days

        try:
            results = await self.db.fetch(query, zone_id, location_id)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error fetching transaction data: {str(e)}")
            return []

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add daypart and day of week features to transaction data"""

        # Convert to local timezone
        df['local_time'] = df['created_at'].dt.tz_localize('UTC').dt.tz_convert(self.tz)
        df['hour'] = df['local_time'].dt.hour
        df['dow'] = df['local_time'].dt.dayofweek  # 0=Monday

        # Define dayparts based on requirements
        # morning: open-16:00 CST, evening: 16:00-23:59 CST
        df['daypart'] = df['hour'].apply(lambda h: 'morning' if h < 16 else 'evening')

        return df

    def _infer_tiers_from_durations(self, data: pd.DataFrame) -> Optional[List[Dict]]:
        """Infer pricing tiers from stay duration patterns"""

        if len(data) < 10:
            return None

        durations = data['duration_minutes'].values
        rates = data['rate_per_hour'].values

        # Define tier boundaries based on duration quantiles
        quantiles = np.percentile(durations, [25, 50, 75, 90])

        tiers = []

        # First hour tier
        first_hour_rate = np.median(rates[durations <= 60])
        tiers.append({
            "duration_max_minutes": 60,
            "rate_per_hour": round(first_hour_rate, 2),
            "description": "First hour"
        })

        # 2-3 hour tier
        mid_duration_mask = (durations > 60) & (durations <= 180)
        if np.sum(mid_duration_mask) > 3:
            mid_rate = np.median(rates[mid_duration_mask])
            tiers.append({
                "duration_max_minutes": 180,
                "rate_per_hour": round(mid_rate, 2),
                "description": "2-3 hours"
            })

        # Long stay tier
        long_duration_mask = durations > 180
        if np.sum(long_duration_mask) > 3:
            long_rate = np.median(rates[long_duration_mask])
            tiers.append({
                "duration_max_minutes": None,  # No limit
                "rate_per_hour": round(long_rate, 2),
                "description": "Extended stay"
            })

        return tiers

    async def _store_inferred_plans(self, plans: List[Dict]):
        """Store inferred rate plans in database"""

        if not plans:
            return

        try:
            async with self.db.transaction() as conn:
                for plan in plans:
                    # Delete existing inferred plan for this zone/dow/daypart
                    await conn.execute("""
                        DELETE FROM inferred_rate_plans
                        WHERE zone_id = $1 AND dow = $2 AND daypart = $3
                            AND ($4::uuid IS NULL OR location_id = $4::uuid)
                    """, plan['zone_id'], plan['dow'], plan['daypart'], plan.get('location_id'))

                    # Insert new inferred plan
                    await conn.execute("""
                        INSERT INTO inferred_rate_plans
                        (location_id, zone_id, daypart, dow, tiers, source)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    plan.get('location_id'),
                    plan['zone_id'],
                    plan['daypart'],
                    plan['dow'],
                    plan['tiers'],
                    plan['source'])

        except Exception as e:
            logger.error(f"Error storing inferred plans: {str(e)}")

    async def get_current_inferred_rates(self, zone_id: str, location_id: Optional[str] = None) -> List[Dict]:
        """Get current inferred rate plans for a zone"""

        query = """
            SELECT location_id, zone_id, daypart, dow, tiers, source, created_at
            FROM inferred_rate_plans
            WHERE zone_id = $1
                AND ($2::uuid IS NULL OR location_id = $2::uuid)
            ORDER BY dow, daypart
        """

        try:
            results = await self.db.fetch(query, zone_id, location_id)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error fetching inferred rates: {str(e)}")
            return []