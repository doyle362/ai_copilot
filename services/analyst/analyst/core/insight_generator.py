import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
# OpenAI import moved to function level for new API
from ..db import Database
from ..config import settings
from .parking_expert_ai import ParkingExpertAI

logger = logging.getLogger(__name__)


class InsightGenerator:
    def __init__(self, db: Database):
        self.db = db
        self.expert_ai = ParkingExpertAI(db)

        # OpenAI client initialized in _generate_ai_narrative method

    async def generate_insights_for_all_zones(self, user_zone_ids: List[str]) -> List[Dict[str, Any]]:
        """Generate fresh insights by analyzing historical_transactions data for all user zones"""

        try:
            logger.info(f"🔥 INSIGHT GENERATOR: Starting analysis for zones: {user_zone_ids}")
            logger.info(f"🔥 INSIGHT GENERATOR: Total zones to process: {len(user_zone_ids)}")

            # Clear existing insights for these zones
            await self._clear_existing_insights(user_zone_ids)

            # Analyze each zone and generate insights
            all_insights = []
            for zone_id in user_zone_ids:
                logger.info(f"🔥 INSIGHT GENERATOR: Analyzing zone {zone_id}")
                try:
                    zone_insights = await self._analyze_zone(zone_id)
                    logger.info(f"🔥 INSIGHT GENERATOR: Zone {zone_id} generated {len(zone_insights)} insights")
                    all_insights.extend(zone_insights)
                except Exception as zone_error:
                    logger.error(f"🔥 INSIGHT GENERATOR: Error analyzing zone {zone_id}: {str(zone_error)}")
                    continue  # Continue with other zones

            # Also generate cross-zone insights
            logger.info(f"🔥 INSIGHT GENERATOR: Generating cross-zone insights")
            try:
                cross_zone_insights = await self._analyze_cross_zone_patterns(user_zone_ids)
                logger.info(f"🔥 INSIGHT GENERATOR: Generated {len(cross_zone_insights)} cross-zone insights")
                all_insights.extend(cross_zone_insights)
            except Exception as cross_error:
                logger.error(f"🔥 INSIGHT GENERATOR: Error in cross-zone analysis: {str(cross_error)}")

            zones_with_insights = list(set([insight['zone_id'] for insight in all_insights]))
            logger.info(f"🔥 INSIGHT GENERATOR: Generated {len(all_insights)} total insights across {len(zones_with_insights)} zones")
            logger.info(f"🔥 INSIGHT GENERATOR: Zones with insights: {sorted(zones_with_insights)}")
            return all_insights

        except Exception as e:
            logger.error(f"🔥 INSIGHT GENERATOR ERROR: {str(e)}")
            import traceback
            logger.error(f"🔥 INSIGHT GENERATOR TRACEBACK: {traceback.format_exc()}")
            raise

    async def _clear_existing_insights(self, zone_ids: List[str]):
        """Clear existing insights for the given zones, handling foreign key constraints"""
        if not zone_ids:
            return

        try:
            # First, delete any dependent records in feedback_memories table
            placeholders = ','.join([f"${i+1}" for i in range(len(zone_ids))])

            # Delete feedback_memories that reference insight_threads for these zones
            delete_feedback_query = f"""
            DELETE FROM feedback_memories
            WHERE source_thread_id IN (
                SELECT id FROM insight_threads
                WHERE insight_id IN (
                    SELECT id FROM insights WHERE zone_id IN ({placeholders})
                )
            )
            """
            await self.db.execute(delete_feedback_query, *zone_ids)

            # Delete insight_threads for these zones
            delete_threads_query = f"""
            DELETE FROM insight_threads
            WHERE insight_id IN (
                SELECT id FROM insights WHERE zone_id IN ({placeholders})
            )
            """
            await self.db.execute(delete_threads_query, *zone_ids)

            # Finally, delete the insights themselves
            delete_insights_query = f"DELETE FROM insights WHERE zone_id IN ({placeholders})"
            await self.db.execute(delete_insights_query, *zone_ids)

            logger.info(f"Cleared existing insights and related data for zones: {zone_ids}")

        except Exception as e:
            # If there are still foreign key issues, just log and continue
            # The new insights will still be generated
            logger.warning(f"Could not clear all existing insights: {str(e)}, continuing with generation")

    async def _analyze_zone(self, zone_id: str) -> List[Dict[str, Any]]:
        """Analyze a single zone's transaction data and generate insights"""

        # Get zone statistics from historical_transactions
        zone_stats = await self._get_zone_statistics(zone_id)

        if not zone_stats:
            return []

        insights = []

        # Generate different types of insights based on the data
        insights.extend(await self._generate_volume_insights(zone_id, zone_stats))
        insights.extend(await self._generate_duration_insights(zone_id, zone_stats))
        insights.extend(await self._generate_revenue_insights(zone_id, zone_stats))
        insights.extend(await self._generate_pattern_insights(zone_id, zone_stats))
        insights.extend(await self._generate_occupancy_insights(zone_id, zone_stats))

        # Always generate a basic zone summary insight if we have any data
        if zone_stats['total_transactions'] > 0:
            insights.extend(await self._generate_basic_zone_insight(zone_id, zone_stats))

        return insights

    async def _get_zone_statistics(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive statistics for a zone from historical_transactions"""

        # Remove 'z-' prefix if present to match database format
        db_zone = zone_id.replace('z-', '')

        query = """
        SELECT
            COUNT(*) as total_transactions,
            AVG(ht.paid_minutes) as avg_duration_minutes,
            MIN(ht.paid_minutes) as min_duration_minutes,
            MAX(ht.paid_minutes) as max_duration_minutes,
            AVG(
                CASE
                    WHEN ht.parking_amount IS NOT NULL
                         AND ht.parking_amount != ''
                         AND ht.parking_amount != '-'
                         AND ht.parking_amount != 'null'
                         AND ht.parking_amount ~ '^[0-9]+\.?[0-9]*$'
                    THEN ht.parking_amount::NUMERIC
                    WHEN ht.parking_amount IS NOT NULL
                         AND ht.parking_amount != ''
                         AND ht.parking_amount != '-'
                         AND ht.parking_amount != 'null'
                         AND ht.parking_amount ~ '^\$[0-9]+\.?[0-9]*$'
                    THEN REPLACE(ht.parking_amount, '$', '')::NUMERIC
                    ELSE NULL
                END
            ) as avg_amount,
            SUM(
                CASE
                    WHEN ht.parking_amount IS NOT NULL
                         AND ht.parking_amount != ''
                         AND ht.parking_amount != '-'
                         AND ht.parking_amount != 'null'
                         AND ht.parking_amount ~ '^[0-9]+\.?[0-9]*$'
                    THEN ht.parking_amount::NUMERIC
                    WHEN ht.parking_amount IS NOT NULL
                         AND ht.parking_amount != ''
                         AND ht.parking_amount != '-'
                         AND ht.parking_amount != 'null'
                         AND ht.parking_amount ~ '^\$[0-9]+\.?[0-9]*$'
                    THEN REPLACE(ht.parking_amount, '$', '')::NUMERIC
                    ELSE NULL
                END
            ) as total_revenue,
            COUNT(DISTINCT ht.start_park_date) as active_days,
            COUNT(DISTINCT EXTRACT(DOW FROM ht.start_park_date)) as active_weekdays,
            MIN(ht.start_park_date) as first_transaction,
            MAX(ht.start_park_date) as last_transaction,
            l.capacity,
            l.name as location_name,
            CASE
                WHEN l.capacity > 0 THEN
                    ROUND((COUNT(*)::NUMERIC / COUNT(DISTINCT ht.start_park_date)::NUMERIC / l.capacity::NUMERIC) * 100, 2)
                ELSE NULL
            END as avg_daily_occupancy_ratio,
            CASE
                WHEN l.capacity > 0 THEN
                    ROUND((SUM(ht.paid_minutes)::NUMERIC / (COUNT(DISTINCT ht.start_park_date)::NUMERIC * 1440.0 * l.capacity::NUMERIC)) * 100, 2)
                ELSE NULL
            END as avg_utilization_ratio
        FROM historical_transactions ht
        LEFT JOIN locations l ON ht.zone::text = l.zone_id
        WHERE ht.zone::text = $1
        AND ht.paid_minutes IS NOT NULL
        GROUP BY l.capacity, l.name
        """

        result = await self.db.fetchrow(query, db_zone)

        if not result or result['total_transactions'] == 0:
            return None

        # Convert result to dict and handle Decimal objects
        stats_dict = dict(result)
        return self._convert_decimals_to_float(stats_dict)

    async def _generate_volume_insights(self, zone_id: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights about transaction volume"""
        insights = []

        total_txns = stats['total_transactions']
        active_days = stats['active_days']
        avg_per_day = total_txns / active_days if active_days > 0 else 0

        # Volume insight - lowered threshold to include more zones
        if total_txns > 100:
            narrative = await self._generate_ai_narrative(
                "volume_analysis",
                f"Zone {zone_id} shows high activity with {total_txns} transactions over {active_days} days "
                f"(avg {avg_per_day:.1f} per day). Analyze what this suggests for demand and capacity."
            )

            insights.append({
                'zone_id': zone_id,
                'kind': 'demand_pattern',
                'window': f"{active_days}d",
                'narrative_text': narrative,
                'confidence': 0.85,
                'metrics_json': {
                    'total_transactions': total_txns,
                    'active_days': active_days,
                    'avg_transactions_per_day': round(avg_per_day, 1)
                }
            })

        return insights

    async def _generate_duration_insights(self, zone_id: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights about parking duration patterns"""
        insights = []

        avg_duration = stats['avg_duration_minutes']
        max_duration = stats['max_duration_minutes']

        # Anomaly detection for very long durations
        if avg_duration > 480:  # More than 8 hours average
            narrative = await self._generate_ai_narrative(
                "duration_anomaly",
                f"Zone {zone_id} has unusually long average session duration of {avg_duration:.0f} minutes "
                f"({avg_duration/60:.1f} hours). Maximum session was {max_duration:.0f} minutes. "
                f"This may indicate meter issues, policy violations, or unique usage patterns."
            )

            insights.append({
                'zone_id': zone_id,
                'kind': 'anomaly_detection',
                'window': '30d',
                'narrative_text': narrative,
                'confidence': 0.95,
                'metrics_json': {
                    'avg_duration_minutes': round(avg_duration, 1),
                    'max_duration_minutes': max_duration,
                    'avg_duration_hours': round(avg_duration/60, 1)
                }
            })

        # Normal duration insight
        elif 60 <= avg_duration <= 180:  # 1-3 hours is typical
            narrative = await self._generate_ai_narrative(
                "duration_optimal",
                f"Zone {zone_id} shows healthy parking patterns with {avg_duration:.0f}-minute average sessions. "
                f"This suggests well-calibrated pricing and appropriate usage for the area."
            )

            insights.append({
                'zone_id': zone_id,
                'kind': 'pricing_efficiency',
                'window': '7d',
                'narrative_text': narrative,
                'confidence': 0.82,
                'metrics_json': {
                    'avg_duration_minutes': round(avg_duration, 1),
                    'status': 'optimal'
                }
            })

        return insights

    async def _generate_revenue_insights(self, zone_id: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights about revenue patterns"""
        insights = []

        total_revenue = stats['total_revenue']
        avg_amount = stats['avg_amount']
        total_txns = stats['total_transactions']

        if total_revenue and avg_amount:
            narrative = await self._generate_ai_narrative(
                "revenue_analysis",
                f"Zone {zone_id} generated ${total_revenue:.2f} total revenue from {total_txns} transactions "
                f"(${avg_amount:.2f} average). Analyze optimization opportunities for pricing strategy."
            )

            insights.append({
                'zone_id': zone_id,
                'kind': 'revenue_optimization',
                'window': '7d',
                'narrative_text': narrative,
                'confidence': 0.78,
                'metrics_json': {
                    'total_revenue': round(total_revenue, 2),
                    'avg_amount': round(avg_amount, 2),
                    'total_transactions': total_txns
                }
            })

        return insights

    async def _generate_pattern_insights(self, zone_id: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights about usage patterns"""
        insights = []

        active_days = stats['active_days']
        active_weekdays = stats['active_weekdays']
        total_txns = stats['total_transactions']

        # Consistent usage pattern - lowered threshold to include more zones
        if active_weekdays >= 3 and active_days >= 10:  # Active multiple days
            narrative = await self._generate_ai_narrative(
                "utilization_consistency",
                f"Zone {zone_id} demonstrates reliable utilization with activity across {active_weekdays} different weekdays "
                f"and {active_days} total days. {total_txns} transactions suggest steady demand that could support "
                f"strategic rate adjustments during peak periods."
            )

            insights.append({
                'zone_id': zone_id,
                'kind': 'utilization_trend',
                'window': '14d',
                'narrative_text': narrative,
                'confidence': 0.88,
                'metrics_json': {
                    'active_days': active_days,
                    'active_weekdays': active_weekdays,
                    'consistency_score': round(active_weekdays / 7 * 100, 1)
                }
            })

        return insights

    async def _generate_basic_zone_insight(self, zone_id: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a basic summary insight for any zone with transaction data"""
        insights = []

        total_txns = stats['total_transactions']
        active_days = stats['active_days']
        avg_duration = stats['avg_duration_minutes']
        avg_per_day = total_txns / active_days if active_days > 0 else 0

        # Generate a basic summary insight for all zones
        narrative = await self._generate_ai_narrative(
            "zone_summary",
            f"Zone {zone_id} recorded {total_txns} parking transactions across {active_days} active days "
            f"({avg_per_day:.1f} avg per day). Average parking duration is {avg_duration:.0f} minutes "
            f"({avg_duration/60:.1f} hours). Analyze utilization patterns and suggest optimizations."
        )

        insights.append({
            'zone_id': zone_id,
            'kind': 'zone_summary',
            'window': f"{active_days}d",
            'narrative_text': narrative,
            'confidence': 0.70,
            'metrics_json': {
                'total_transactions': total_txns,
                'active_days': active_days,
                'avg_transactions_per_day': round(avg_per_day, 1),
                'avg_duration_minutes': round(avg_duration, 1),
                'avg_duration_hours': round(avg_duration/60, 1)
            }
        })

        return insights

    async def _generate_occupancy_insights(self, zone_id: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights about occupancy and capacity utilization using expert AI analysis"""
        insights = []

        capacity = stats.get('capacity')
        location_name = stats.get('location_name')
        occupancy_ratio = stats.get('avg_daily_occupancy_ratio')
        utilization_ratio = stats.get('avg_utilization_ratio')

        if not capacity or capacity <= 0:
            return insights

        # EXPERT AI ANALYSIS - Use parking industry expertise
        try:
            expert_analysis = await self.expert_ai.analyze_with_expert_knowledge(stats)

            # Generate expert-level occupancy insight based on 85% rule and industry standards
            occupancy_assessment = expert_analysis.get('occupancy_assessment', {})
            revenue_analysis = expert_analysis.get('revenue_analysis', {})
            recommendations = expert_analysis.get('strategic_recommendations', [])
            expert_reasoning = expert_analysis.get('expert_reasoning', '')

            if occupancy_assessment and occupancy_assessment.get('status'):
                status = occupancy_assessment['status']
                current_occupancy = occupancy_assessment.get('current_occupancy', occupancy_ratio)
                interpretation = occupancy_assessment.get('expert_interpretation', '')

                # Create expert insight based on assessment
                if status in ['capacity_constraint', 'overcapacity_risk']:
                    insight_kind = 'capacity_optimization'
                    confidence = 0.95
                elif status == 'optimal':
                    insight_kind = 'optimal_utilization'
                    confidence = 0.85
                else:
                    insight_kind = 'underutilization'
                    confidence = 0.90

                # Enhanced narrative with expert reasoning
                narrative = f"Expert Analysis: {interpretation}"
                if expert_reasoning:
                    narrative += f" {expert_reasoning[:200]}..."  # Truncate for insight display

                # Add strategic recommendations to narrative
                if recommendations:
                    top_rec = recommendations[0]
                    narrative += f" Recommended action: {top_rec.get('recommendation', 'strategic review')}."

                insights.append({
                    'zone_id': zone_id,
                    'kind': insight_kind,
                    'window': '7d',
                    'narrative_text': narrative,
                    'confidence': confidence,
                    'metrics_json': {
                        'capacity': capacity,
                        'occupancy_ratio': round(current_occupancy, 1),
                        'utilization_ratio': round(utilization_ratio, 1) if utilization_ratio else None,
                        'location_name': location_name,
                        'status': status,
                        'expert_assessment': occupancy_assessment,
                        'revenue_analysis': revenue_analysis,
                        'strategic_recommendations': recommendations[:3],  # Top 3 recommendations
                        'expert_reasoning': expert_reasoning
                    }
                })

                # Return expert insight - don't generate fallback insights
                return insights

        except Exception as e:
            logger.warning(f"Expert AI analysis failed for zone {zone_id}: {str(e)}")
            # Continue to fallback logic below

        # High occupancy insight
        if occupancy_ratio and occupancy_ratio > 80:
            narrative = await self._generate_ai_narrative(
                "high_occupancy",
                f"Zone {zone_id} ({location_name}) shows high demand with {occupancy_ratio}% daily occupancy "
                f"against {capacity} total spaces. Time-based utilization at {utilization_ratio}% suggests "
                f"strong revenue potential but possible capacity constraints during peak times.",
                stats
            )

            insights.append({
                'zone_id': zone_id,
                'kind': 'capacity_optimization',
                'window': '7d',
                'narrative_text': narrative,
                'confidence': 0.90,
                'metrics_json': {
                    'capacity': capacity,
                    'occupancy_ratio': round(occupancy_ratio, 1),
                    'utilization_ratio': round(utilization_ratio, 1) if utilization_ratio else None,
                    'location_name': location_name,
                    'status': 'high_demand'
                }
            })

        # Low occupancy insight
        elif occupancy_ratio and occupancy_ratio < 30:
            narrative = await self._generate_ai_narrative(
                "underutilized_capacity",
                f"Zone {zone_id} ({location_name}) shows underutilization with only {occupancy_ratio}% daily "
                f"occupancy from {capacity} available spaces. Consider pricing adjustments, marketing initiatives, "
                f"or policy changes to improve utilization efficiency.",
                stats
            )

            insights.append({
                'zone_id': zone_id,
                'kind': 'underutilization',
                'window': '7d',
                'narrative_text': narrative,
                'confidence': 0.85,
                'metrics_json': {
                    'capacity': capacity,
                    'occupancy_ratio': round(occupancy_ratio, 1),
                    'utilization_ratio': round(utilization_ratio, 1) if utilization_ratio else None,
                    'location_name': location_name,
                    'status': 'underutilized'
                }
            })

        # Optimal occupancy insight
        elif occupancy_ratio and 50 <= occupancy_ratio <= 80:
            narrative = await self._generate_ai_narrative(
                "optimal_occupancy",
                f"Zone {zone_id} ({location_name}) demonstrates excellent capacity management with {occupancy_ratio}% "
                f"occupancy across {capacity} spaces. This balanced utilization suggests effective pricing and "
                f"healthy demand without oversaturation.",
                stats
            )

            insights.append({
                'zone_id': zone_id,
                'kind': 'optimal_utilization',
                'window': '7d',
                'narrative_text': narrative,
                'confidence': 0.80,
                'metrics_json': {
                    'capacity': capacity,
                    'occupancy_ratio': round(occupancy_ratio, 1),
                    'utilization_ratio': round(utilization_ratio, 1) if utilization_ratio else None,
                    'location_name': location_name,
                    'status': 'optimal'
                }
            })

        return insights

    async def _analyze_cross_zone_patterns(self, zone_ids: List[str]) -> List[Dict[str, Any]]:
        """Analyze patterns across multiple zones"""
        insights = []

        # Get cross-zone statistics (focusing on data that's reliably available)
        db_zones = [z.replace('z-', '') for z in zone_ids]
        placeholders = ','.join([f"${i+1}" for i in range(len(db_zones))])

        query = f"""
        SELECT
            COUNT(*) as total_transactions,
            COUNT(DISTINCT zone) as zones_with_data,
            AVG(paid_minutes) as avg_duration,
            COUNT(DISTINCT start_park_date) as total_active_days
        FROM historical_transactions
        WHERE zone IN ({placeholders})
        AND paid_minutes IS NOT NULL
        """

        result = await self.db.fetchrow(query, *db_zones)

        if result and result['total_transactions'] > 0:
            narrative = await self._generate_ai_narrative(
                "cross_zone_analysis",
                f"Across {result['zones_with_data']} zones, {result['total_transactions']} total transactions "
                f"with {result['avg_duration']:.0f}-minute average sessions over {result['total_active_days']} "
                f"active days. Strong utilization patterns suggest opportunities for coordinated pricing strategies."
            )

            insights.append({
                'zone_id': zone_ids[0],  # Use first zone as representative
                'kind': 'cross_zone_analysis',
                'window': '30d',
                'narrative_text': narrative,
                'confidence': 0.75,
                'metrics_json': {
                    'zones_analyzed': result['zones_with_data'],
                    'total_transactions': result['total_transactions'],
                    'avg_duration_minutes': round(result['avg_duration'], 1),
                    'total_active_days': result['total_active_days']
                }
            })

        return insights

    async def _get_relevant_kpi_knowledge(self, context_keywords: List[str]) -> List[Dict[str, Any]]:
        """Get relevant KPI knowledge based on context keywords"""
        if not context_keywords:
            return []

        try:
            # Build query to find KPIs matching any of the context keywords
            base_query = """
                SELECT
                    kpi_name,
                    kpi_category,
                    calculation_formula,
                    interpretation_rules,
                    industry_benchmarks,
                    recommended_actions,
                    related_kpis
                FROM parking_kpis
                WHERE is_active = true
            """

            # Add context filtering - match any keyword against triggers or name
            for i, keyword in enumerate(context_keywords):
                if i == 0:
                    base_query += " AND ("
                else:
                    base_query += " OR "
                base_query += f"(${i+1} = ANY(context_triggers) OR kpi_name ILIKE '%' || ${i+1} || '%')"

            if context_keywords:
                base_query += ")"

            base_query += " ORDER BY kpi_category, kpi_name"

            results = await self.db.fetch(base_query, *context_keywords)
            return [dict(row) for row in results]

        except Exception as e:
            logger.warning(f"Could not retrieve KPI knowledge: {str(e)}")
            return []

    async def _get_relevant_analytical_patterns(self, context_keywords: List[str]) -> List[Dict[str, Any]]:
        """Get relevant analytical patterns based on context keywords"""
        if not context_keywords:
            return []

        try:
            # Build query to find patterns matching any of the context keywords
            base_query = """
                SELECT
                    pattern_name,
                    pattern_type,
                    description,
                    detection_criteria,
                    significance_level,
                    typical_causes,
                    recommended_analysis,
                    example_insights
                FROM analytical_patterns
                WHERE is_active = true
            """

            # Add context filtering
            for i, keyword in enumerate(context_keywords):
                if i == 0:
                    base_query += " AND ("
                else:
                    base_query += " OR "
                base_query += f"(${i+1} = ANY(context_triggers) OR pattern_name ILIKE '%' || ${i+1} || '%' OR description ILIKE '%' || ${i+1} || '%')"

            if context_keywords:
                base_query += ")"

            base_query += " ORDER BY significance_level DESC, pattern_type, pattern_name"

            results = await self.db.fetch(base_query, *context_keywords)
            return [dict(row) for row in results]

        except Exception as e:
            logger.warning(f"Could not retrieve analytical patterns: {str(e)}")
            return []

    async def _get_industry_knowledge(self, context_keywords: List[str]) -> List[Dict[str, Any]]:
        """Get relevant industry knowledge based on context keywords"""
        if not context_keywords:
            return []

        try:
            base_query = """
                SELECT
                    knowledge_type,
                    category,
                    industry_vertical,
                    title,
                    content,
                    confidence_level
                FROM industry_knowledge
                WHERE is_active = true
            """

            # Add context filtering
            for i, keyword in enumerate(context_keywords):
                if i == 0:
                    base_query += " AND ("
                else:
                    base_query += " OR "
                base_query += f"(${i+1} = ANY(context_triggers) OR title ILIKE '%' || ${i+1} || '%' OR content ILIKE '%' || ${i+1} || '%')"

            if context_keywords:
                base_query += ")"

            base_query += " ORDER BY confidence_level DESC NULLS LAST, knowledge_type, category"

            results = await self.db.fetch(base_query, *context_keywords)
            return [dict(row) for row in results]

        except Exception as e:
            logger.warning(f"Could not retrieve industry knowledge: {str(e)}")
            return []

    async def _generate_ai_narrative(self, insight_type: str, context: str, zone_stats: Optional[Dict[str, Any]] = None) -> str:
        """Generate enhanced narrative text for insights using KPI knowledge"""

        # Extract context keywords from insight type and context
        context_keywords = []

        # Add insight type as context
        if insight_type:
            context_keywords.append(insight_type.lower())

        # Extract keywords from metrics if zone_stats provided
        if zone_stats:
            if zone_stats.get('avg_daily_occupancy_ratio'):
                occupancy = float(zone_stats['avg_daily_occupancy_ratio'] or 0)
                context_keywords.extend(['occupancy', 'efficiency'])
                if occupancy > 80:
                    context_keywords.extend(['high_demand', 'capacity'])
                elif occupancy < 50:
                    context_keywords.extend(['underutilized', 'pricing'])

            if zone_stats.get('total_revenue'):
                context_keywords.extend(['revenue', 'performance'])

            if zone_stats.get('avg_duration_minutes'):
                duration = float(zone_stats['avg_duration_minutes'] or 0)
                context_keywords.extend(['duration', 'utilization'])
                if duration < 60:
                    context_keywords.append('turnover')
                elif duration > 240:
                    context_keywords.append('premium')

        # Get relevant knowledge
        kpi_knowledge = await self._get_relevant_kpi_knowledge(context_keywords)
        analytical_patterns = await self._get_relevant_analytical_patterns(context_keywords)
        industry_knowledge = await self._get_industry_knowledge(context_keywords)

        # Build enhanced narrative
        narrative = f"Analytics insight: {context}"

        # Add KPI context if available
        if kpi_knowledge:
            kpi_names = [kpi['kpi_name'] for kpi in kpi_knowledge[:2]]  # Limit to 2 most relevant
            narrative += f" This analysis relates to key performance indicators: {', '.join(kpi_names)}."

            # Add interpretation if we have zone stats and matching KPI rules
            for kpi in kpi_knowledge[:1]:  # Just use the most relevant KPI
                if kpi.get('interpretation_rules') and zone_stats:
                    try:
                        import json
                        rules = json.loads(kpi['interpretation_rules']) if isinstance(kpi['interpretation_rules'], str) else kpi['interpretation_rules']

                        # Try to match occupancy rules if available
                        if 'occupancy' in kpi['kpi_name'].lower() and zone_stats.get('avg_daily_occupancy_ratio'):
                            occupancy = float(zone_stats['avg_daily_occupancy_ratio'])
                            for level, rule in rules.items():
                                if isinstance(rule, dict) and 'min' in rule and 'max' in rule:
                                    if rule['min'] <= occupancy <= rule['max']:
                                        narrative += f" Based on industry standards, this {rule.get('meaning', 'performance level')}."
                                        break
                                elif isinstance(rule, dict) and 'max' in rule and occupancy <= rule['max']:
                                    narrative += f" Based on industry standards, this {rule.get('meaning', 'performance level')}."
                                    break
                                elif isinstance(rule, dict) and 'min' in rule and occupancy >= rule['min']:
                                    narrative += f" Based on industry standards, this {rule.get('meaning', 'performance level')}."
                                    break
                    except (json.JSONDecodeError, TypeError, KeyError):
                        pass

        # Add analytical pattern insights
        if analytical_patterns:
            pattern = analytical_patterns[0]  # Use most relevant pattern
            if pattern.get('example_insights'):
                try:
                    examples = pattern['example_insights']
                    if examples and len(examples) > 0:
                        # Pick a relevant example
                        narrative += f" {examples[0]}"
                except (TypeError, IndexError):
                    pass

        # Add recommended actions if available from KPI knowledge
        if kpi_knowledge:
            for kpi in kpi_knowledge[:1]:
                if kpi.get('recommended_actions') and zone_stats:
                    try:
                        import json
                        actions = json.loads(kpi['recommended_actions']) if isinstance(kpi['recommended_actions'], str) else kpi['recommended_actions']

                        # Try to find relevant actions based on occupancy
                        if zone_stats.get('avg_daily_occupancy_ratio'):
                            occupancy = float(zone_stats['avg_daily_occupancy_ratio'])
                            if occupancy < 50 and 'below_50' in actions:
                                action_list = actions['below_50']
                                if action_list and len(action_list) > 0:
                                    narrative += f" Recommended action: {action_list[0]}."
                            elif 50 <= occupancy <= 70 and '50_to_70' in actions:
                                action_list = actions['50_to_70']
                                if action_list and len(action_list) > 0:
                                    narrative += f" Recommended action: {action_list[0]}."
                            elif occupancy > 95 and 'above_95' in actions:
                                action_list = actions['above_95']
                                if action_list and len(action_list) > 0:
                                    narrative += f" Recommended action: {action_list[0]}."
                    except (json.JSONDecodeError, TypeError, KeyError):
                        pass

        return narrative

    def _convert_decimals_to_float(self, obj):
        """Convert Decimal objects to float for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self._convert_decimals_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals_to_float(v) for v in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            return obj

    async def _save_insight(self, insight: Dict[str, Any]) -> str:
        """Save a single insight to the database"""

        query = """
        INSERT INTO insights (zone_id, kind, "window", narrative_text, confidence, metrics_json)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """

        # Convert any Decimal values to float for JSON serialization
        metrics_json = self._convert_decimals_to_float(insight.get('metrics_json', {}))

        result = await self.db.fetchval(
            query,
            insight['zone_id'],
            insight['kind'],
            insight['window'],
            insight['narrative_text'],
            insight['confidence'],
            json.dumps(metrics_json)
        )

        return str(result)

    async def save_insights(self, insights: List[Dict[str, Any]]) -> List[str]:
        """Save multiple insights to the database"""

        saved_ids = []
        for insight in insights:
            insight_id = await self._save_insight(insight)
            saved_ids.append(insight_id)

        logger.info(f"Saved {len(saved_ids)} insights to database")
        return saved_ids