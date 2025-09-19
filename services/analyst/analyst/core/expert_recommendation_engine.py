import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from ..db import Database
from .parking_expert_ai import ParkingExpertAI

logger = logging.getLogger(__name__)


class ExpertRecommendationEngine:
    """
    Expert-driven recommendation engine that uses parking industry knowledge
    to generate precise, actionable recommendations with revenue estimates.
    """

    def __init__(self, db: Database):
        self.db = db
        self.expert_ai = ParkingExpertAI(db)

    async def generate_recommendations_for_all_zones(self, user_zone_ids: List[str]) -> List[Dict[str, Any]]:
        """Generate expert recommendations for all user zones"""

        logger.info(f"🎯 EXPERT RECOMMENDATIONS: Generating for {len(user_zone_ids)} zones")

        await self._clear_existing_recommendations(user_zone_ids)
        all_recommendations = []

        for zone_id in user_zone_ids:
            try:
                zone_recommendations = await self._generate_zone_recommendations(zone_id)
                all_recommendations.extend(zone_recommendations)
                logger.info(f"🎯 EXPERT RECOMMENDATIONS: Zone {zone_id} generated {len(zone_recommendations)} recommendations")
            except Exception as e:
                logger.error(f"🎯 EXPERT RECOMMENDATIONS: Error for zone {zone_id}: {e}")
                continue

        # Store recommendations in database
        stored_recommendations = []
        for rec in all_recommendations:
            try:
                stored_rec = await self._store_recommendation(rec)
                if stored_rec:
                    stored_recommendations.append(stored_rec)
            except Exception as e:
                logger.error(f"Error storing recommendation: {e}")
                continue

        logger.info(f"🎯 EXPERT RECOMMENDATIONS: Generated {len(stored_recommendations)} total recommendations")
        return stored_recommendations

    async def _clear_existing_recommendations(self, zone_ids: List[str]):
        if not zone_ids:
            return

        try:
            await self.db.execute(
                """
                DELETE FROM recommendations
                WHERE zone_id = ANY($1::text[])
                  AND status IN ('pending', 'draft')
                  AND proposal ? 'expert_framework'
                """,
                zone_ids
            )
            logger.info(
                "🎯 EXPERT RECOMMENDATIONS: Cleared existing pending expert recommendations for zones %s",
                zone_ids
            )
        except Exception as exc:
            logger.warning(
                "🎯 EXPERT RECOMMENDATIONS: Unable to clear previous recommendations: %s",
                exc
            )

    async def _generate_zone_recommendations(self, zone_id: str) -> List[Dict[str, Any]]:
        """Generate expert recommendations for a specific zone"""

        # Get zone analytics data
        zone_stats = await self._get_zone_analytics(zone_id)
        if not zone_stats:
            return []

        # Get expert analysis
        expert_analysis = await self.expert_ai.analyze_with_expert_knowledge(zone_stats)

        # Generate recommendations based on expert analysis
        recommendations = []

        # Occupancy-based recommendations
        occupancy_recs = await self._generate_occupancy_recommendations(zone_id, zone_stats, expert_analysis)
        recommendations.extend(occupancy_recs)

        # Revenue optimization recommendations
        revenue_recs = await self._generate_revenue_recommendations(zone_id, zone_stats, expert_analysis)
        recommendations.extend(revenue_recs)

        # Operational recommendations
        operational_recs = await self._generate_operational_recommendations(zone_id, zone_stats, expert_analysis)
        recommendations.extend(operational_recs)

        return recommendations

    async def _generate_occupancy_recommendations(self, zone_id: str, zone_stats: Dict, expert_analysis: Dict) -> List[Dict[str, Any]]:
        """Generate occupancy-based recommendations using expert knowledge"""

        recommendations = []
        occupancy_assessment = expert_analysis.get('occupancy_assessment', {})
        status = occupancy_assessment.get('status', 'unknown')
        current_occupancy = occupancy_assessment.get('current_occupancy', 0.0)

        if status == 'overcapacity':
            # Zone exceeds 85% rule - recommend price increase
            current_rate = zone_stats.get('revenue_per_space_hour', 2.0)
            proposed_increase = 0.25  # $0.25 increment per expert knowledge
            new_rate = current_rate + proposed_increase
            revenue_increase_pct = proposed_increase / current_rate

            # Apply demand elasticity (-0.3 for price increases)
            expected_occupancy_decrease = revenue_increase_pct * 0.3
            new_occupancy = current_occupancy - expected_occupancy_decrease

            # Calculate revenue impact
            current_revenue = zone_stats.get('total_revenue', 0)
            revenue_lift_pct = revenue_increase_pct * (1 - expected_occupancy_decrease)
            expected_revenue_increase = current_revenue * revenue_lift_pct

            recommendations.append({
                'zone_id': zone_id,
                'type': 'pricing_optimization',
                'title': 'Reduce Overcrowding with Strategic Price Increase',
                'action': f'Increase hourly rates by ${proposed_increase:.2f}',
                'rationale_text': f'Zone operates at {current_occupancy:.1%} occupancy, exceeding the industry-standard 85% optimal level. This indicates capacity constraints and degraded customer experience. Based on demand elasticity research showing -0.3 elasticity for price increases, a ${proposed_increase:.2f} rate increase should reduce occupancy to the target 85% range while increasing revenue.',
                'proposal': {
                    'current_rate': current_rate,
                    'proposed_rate': new_rate,
                    'rate_increase': proposed_increase,
                    'target_occupancy': 0.85,
                    'implementation': 'Apply during peak hours (identified through demand pattern analysis)'
                },
                'expected_outcomes': {
                    'revenue_increase_dollars': expected_revenue_increase,
                    'revenue_increase_pct': revenue_lift_pct,
                    'occupancy_reduction': expected_occupancy_decrease,
                    'new_occupancy_pct': new_occupancy,
                    'customer_experience': 'Improved availability and reduced search times'
                },
                'confidence': 0.85,
                'priority': 'high',
                'expert_framework': '85% Occupancy Rule + Demand Elasticity Analysis',
                'monitoring_period': '2-3 weeks',
                'success_metrics': ['Occupancy reduction to 80-85%', 'Revenue increase', 'Reduced customer complaints']
            })

        elif status == 'underutilized':
            # Zone below optimal - comprehensive analysis needed
            current_revenue_per_hour = zone_stats.get('revenue_per_space_hour', 1.0)

            if current_revenue_per_hour < 1.50:  # Below concerning threshold
                recommendations.append({
                    'zone_id': zone_id,
                    'type': 'comprehensive_optimization',
                    'title': 'Comprehensive Revenue Optimization Strategy',
                    'action': 'Implement multi-faceted optimization approach',
                    'rationale_text': f'Zone shows {current_occupancy:.1%} occupancy with ${current_revenue_per_hour:.2f}/hour RevPASH, both below optimal levels. Expert analysis indicates comprehensive strategy needed rather than simple price adjustments. Focus on rate optimization while maintaining volume.',
                    'proposal': {
                        'phase_1': 'Market analysis and competitor pricing review',
                        'phase_2': 'Modest rate increase ($0.25) with demand monitoring',
                        'phase_3': 'Marketing and accessibility improvements',
                        'target_revpash': '$1.80-2.80 per hour (downtown standard)'
                    },
                    'expected_outcomes': {
                        'revenue_increase_dollars': current_revenue_per_hour * 0.15 * zone_stats.get('total_spaces', 100) * 8,  # 15% increase over 8-hour day
                        'revenue_increase_pct': 0.15,
                        'occupancy_target': 0.80,
                        'timeline': '6-8 weeks for full implementation'
                    },
                    'confidence': 0.75,
                    'priority': 'medium',
                    'expert_framework': 'Revenue Optimization Matrix + Industry Benchmarking',
                    'monitoring_period': '4 weeks',
                    'success_metrics': ['RevPASH increase to $1.80+', 'Occupancy improvement', 'Customer satisfaction maintenance']
                })

        return recommendations

    async def _generate_revenue_recommendations(self, zone_id: str, zone_stats: Dict, expert_analysis: Dict) -> List[Dict[str, Any]]:
        """Generate revenue optimization recommendations"""

        recommendations = []
        revenue_analysis = expert_analysis.get('revenue_analysis', {})
        current_revpash = revenue_analysis.get('revpash')

        if current_revpash and current_revpash < 2.50:  # Below excellent threshold
            # Calculate potential improvement
            target_revpash = 2.50
            improvement_potential = target_revpash - current_revpash
            improvement_pct = improvement_potential / current_revpash

            total_spaces = zone_stats.get('total_spaces', 100)
            operating_hours = 12  # Assume 12-hour operation
            current_daily_revenue = current_revpash * total_spaces * operating_hours
            potential_daily_increase = improvement_potential * total_spaces * operating_hours
            annual_potential = potential_daily_increase * 365

            recommendations.append({
                'zone_id': zone_id,
                'type': 'revenue_optimization',
                'title': 'RevPASH Optimization to Industry Excellence',
                'action': f'Optimize pricing to reach ${target_revpash:.2f}/hour RevPASH',
                'rationale_text': f'Current RevPASH of ${current_revpash:.2f}/hour is below the excellence threshold of $2.50. Industry benchmarking shows potential for ${improvement_potential:.2f}/hour improvement through strategic pricing optimization and operational efficiency gains.',
                'proposal': {
                    'current_revpash': current_revpash,
                    'target_revpash': target_revpash,
                    'optimization_strategies': [
                        'Peak hour premium pricing',
                        'Dynamic rate adjustments based on demand',
                        'Operational efficiency improvements',
                        'Payment convenience enhancements'
                    ]
                },
                'expected_outcomes': {
                    'revenue_increase_dollars': potential_daily_increase,
                    'annual_revenue_potential': annual_potential,
                    'revenue_increase_pct': improvement_pct,
                    'daily_revenue_current': current_daily_revenue,
                    'daily_revenue_target': current_daily_revenue + potential_daily_increase
                },
                'confidence': 0.80,
                'priority': 'high',
                'expert_framework': 'RevPASH Optimization + Industry Benchmarking',
                'implementation_timeline': '4-6 weeks',
                'success_metrics': [f'Achieve ${target_revpash:.2f}/hour RevPASH', 'Maintain 80-85% occupancy', 'Customer satisfaction scores']
            })

        return recommendations

    async def _generate_operational_recommendations(self, zone_id: str, zone_stats: Dict, expert_analysis: Dict) -> List[Dict[str, Any]]:
        """Generate operational efficiency recommendations"""

        recommendations = []
        strategic_recommendations = expert_analysis.get('strategic_recommendations', [])

        # Look for specific tactical recommendations from expert AI
        for expert_rec in strategic_recommendations:
            if expert_rec.get('tactic') == 'Off-Peak Activation Strategy':
                turnover_rate = zone_stats.get('sessions_per_space', 2.0)
                if turnover_rate < 3.0:  # Below good threshold

                    total_spaces = zone_stats.get('total_spaces', 100)
                    current_utilization = zone_stats.get('occupancy_ratio', 0.6)
                    potential_increase = (3.0 - turnover_rate) / turnover_rate
                    revenue_impact = zone_stats.get('total_revenue', 1000) * potential_increase * 0.3  # Conservative estimate

                    recommendations.append({
                        'zone_id': zone_id,
                        'type': 'operational_optimization',
                        'title': 'Off-Peak Period Activation Strategy',
                        'action': 'Implement targeted promotions for underutilized periods',
                        'rationale_text': f'Current turnover rate of {turnover_rate:.1f} sessions/space/day is below the industry benchmark of 3-5 sessions. Off-peak activation can improve space utilization without cannibalizing peak revenue.',
                        'proposal': {
                            'strategies': [
                                'Early bird discounts (6-9 AM)',
                                'Flat-rate evening parking (6-10 PM)',
                                'Business partnership programs',
                                'Extended validation periods'
                            ],
                            'target_periods': 'Mornings, evenings, and weekends',
                            'pricing_adjustments': 'Promotional rates 15-25% below standard'
                        },
                        'expected_outcomes': {
                            'revenue_increase_dollars': revenue_impact,
                            'revenue_increase_pct': potential_increase * 0.3,
                            'utilization_improvement': potential_increase,
                            'target_turnover_rate': 3.5
                        },
                        'confidence': 0.70,
                        'priority': 'medium',
                        'expert_framework': 'Operational Tactics + Turnover Optimization',
                        'implementation_timeline': '2-3 weeks',
                        'success_metrics': ['Increased sessions per space', 'Off-peak utilization improvement', 'Overall revenue growth']
                    })

        return recommendations

    async def _get_zone_analytics(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive analytics data for a zone"""

        try:
            # First get the real zone capacity from locations table
            capacity_query = """
                SELECT capacity
                FROM locations
                WHERE zone_id = $1
                LIMIT 1
            """

            capacity_result = await self.db.fetchrow(capacity_query, zone_id)
            real_capacity = float(capacity_result['capacity']) if capacity_result and capacity_result['capacity'] else 100

            # Get zone statistics from historical_transactions (using same structure as insight_generator)
            stats_query = """
                SELECT
                    zone as zone_id,
                    COUNT(*) as total_sessions,
                    COUNT(DISTINCT start_park_date) as active_days,
                    AVG(paid_minutes) as avg_session_duration_minutes,
                    SUM(
                        CASE
                            WHEN parking_amount IS NOT NULL
                                 AND parking_amount != ''
                                 AND parking_amount != '-'
                                 AND parking_amount != 'null'
                                 AND parking_amount ~ '^[0-9]+\\.?[0-9]*$'
                            THEN parking_amount::NUMERIC
                            ELSE 0
                        END
                    ) as total_revenue,
                    AVG(
                        CASE
                            WHEN parking_amount IS NOT NULL
                                 AND parking_amount != ''
                                 AND parking_amount != '-'
                                 AND parking_amount != 'null'
                                 AND parking_amount ~ '^[0-9]+\\.?[0-9]*$'
                            THEN parking_amount::NUMERIC
                            ELSE NULL
                        END
                    ) as avg_transaction_value
                FROM historical_transactions
                WHERE zone = $1
                AND paid_minutes IS NOT NULL
                GROUP BY zone
            """

            result = await self.db.fetchrow(stats_query, zone_id)
            if not result:
                return None

            stats = dict(result)

            # Convert Decimal to float for JSON serialization
            for key, value in stats.items():
                if isinstance(value, Decimal):
                    stats[key] = float(value)

            # Calculate additional metrics using real capacity
            if stats['total_sessions'] > 0 and stats['active_days'] > 0:
                stats['sessions_per_day'] = stats['total_sessions'] / stats['active_days']
                stats['sessions_per_space'] = stats['sessions_per_day'] / real_capacity  # Use real capacity

                # Calculate occupancy ratio using real capacity and operating hours
                avg_duration_hours = (stats.get('avg_session_duration_minutes', 0) or 0) / 60
                operating_hours = 12  # Assume 12-hour operation per day

                if avg_duration_hours > 0:
                    # Total vehicle-hours per day
                    total_vehicle_hours = stats['sessions_per_day'] * avg_duration_hours
                    # Total available space-hours per day
                    total_available_hours = real_capacity * operating_hours
                    # Real occupancy ratio
                    stats['occupancy_ratio'] = min(1.0, total_vehicle_hours / total_available_hours)
                else:
                    stats['occupancy_ratio'] = 0.1  # Conservative default for low-usage zones

                # Calculate revenue per space hour using real capacity
                daily_revenue = stats['total_revenue'] / stats['active_days'] if stats['active_days'] > 0 else 0
                stats['revenue_per_space_hour'] = daily_revenue / (real_capacity * operating_hours)

                # Use real capacity data
                stats['total_spaces'] = real_capacity
                stats['peak_occupancy'] = min(1.0, stats['occupancy_ratio'] * 1.2)  # Estimated peak

            return stats

        except Exception as e:
            logger.error(f"Error getting zone analytics for {zone_id}: {e}")
            return None

    async def _store_recommendation(self, rec_data: Dict) -> Optional[Dict]:
        """Store a recommendation in the database"""

        try:
            query = """
                INSERT INTO recommendations
                (zone_id, type, proposal, rationale_text, expected_lift_json, confidence, requires_approval, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, zone_id, type, proposal, rationale_text, expected_lift_json,
                          confidence, requires_approval, status, created_at
            """

            # Prepare data for storage
            proposal = {
                'title': rec_data.get('title'),
                'action': rec_data.get('action'),
                'details': rec_data.get('proposal', {}),
                'priority': rec_data.get('priority'),
                'expert_framework': rec_data.get('expert_framework'),
                'implementation_timeline': rec_data.get('implementation_timeline'),
                'monitoring_period': rec_data.get('monitoring_period'),
                'success_metrics': rec_data.get('success_metrics', [])
            }

            expected_lift = rec_data.get('expected_outcomes', {})

            import json

            result = await self.db.fetchrow(
                query,
                rec_data['zone_id'],
                rec_data['type'],
                json.dumps(proposal),  # Convert dict to JSON string
                rec_data['rationale_text'],
                json.dumps(expected_lift),  # Convert dict to JSON string
                rec_data['confidence'],
                True,  # Require approval for expert recommendations
                'pending'
            )

            return dict(result) if result else None

        except Exception as e:
            logger.error(f"Error storing recommendation: {str(e)}")
            return None
