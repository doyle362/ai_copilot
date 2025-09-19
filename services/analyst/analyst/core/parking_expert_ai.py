"""
Parking Expert AI System
Integrates comprehensive parking industry knowledge for expert-level analysis
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from ..db import Database

logger = logging.getLogger(__name__)


class ParkingExpertAI:
    """
    Advanced parking analytics system that thinks like a parking expert.
    Integrates comprehensive industry knowledge, best practices, and decision frameworks.
    """

    def __init__(self, db: Database):
        self.db = db

    async def analyze_with_expert_knowledge(self, zone_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform expert-level analysis of zone performance using comprehensive knowledge base.
        Returns insights, recommendations, and reasoning that mirrors parking industry expertise.
        """

        # Extract key metrics
        occupancy_ratio = float(zone_stats.get('avg_daily_occupancy_ratio', 0))
        capacity = zone_stats.get('capacity', 0)
        location_name = zone_stats.get('location_name', f"Zone {zone_stats.get('zone_id', 'Unknown')}")

        # Calculate RevPASH if possible
        revpash = await self._calculate_revpash(zone_stats)

        # Get expert analysis
        expert_analysis = {
            'occupancy_assessment': await self._assess_occupancy_with_85_rule(occupancy_ratio),
            'revenue_analysis': await self._analyze_revenue_performance(revpash, zone_stats),
            'strategic_recommendations': await self._generate_strategic_recommendations(zone_stats),
            'market_context': await self._provide_market_context(zone_stats),
            'decision_framework': await self._apply_decision_frameworks(zone_stats),
            'expert_reasoning': await self._generate_expert_reasoning(zone_stats)
        }

        return expert_analysis

    async def _assess_occupancy_with_85_rule(self, occupancy_ratio: float) -> Dict[str, Any]:
        """Apply the industry-standard 85% rule with expert interpretation"""

        # Get the 85% rule principle from knowledge base
        principle_query = """
            SELECT detailed_explanation, threshold_values, context_triggers
            FROM parking_principles
            WHERE principle_name = '85% Occupancy Rule' AND is_foundational = true
        """
        principle = await self.db.fetchrow(principle_query)

        if not principle:
            # Fallback to hardcoded knowledge if DB not populated yet
            thresholds = {
                "target": 85,
                "acceptable_range": {"min": 80, "max": 90},
                "action_thresholds": {
                    "price_increase": 90,
                    "price_decrease_consideration": 50,
                    "capacity_constraint": 95
                }
            }
        else:
            thresholds = json.loads(principle['threshold_values']) if isinstance(principle['threshold_values'], str) else principle['threshold_values']

        # Expert assessment based on 85% rule
        assessment = {
            'current_occupancy': occupancy_ratio,
            'target_occupancy': thresholds['target'],
            'status': self._classify_occupancy_status(occupancy_ratio, thresholds),
            'distance_from_optimal': abs(occupancy_ratio - thresholds['target']),
            'recommended_action': self._determine_occupancy_action(occupancy_ratio, thresholds),
            'expert_interpretation': self._get_occupancy_interpretation(occupancy_ratio, thresholds)
        }

        return assessment

    def _classify_occupancy_status(self, occupancy: float, thresholds: Dict) -> str:
        """Classify occupancy status using expert thresholds"""
        if occupancy >= 95:
            return "capacity_constraint"
        elif occupancy >= 90:
            return "overcapacity_risk"
        elif occupancy >= thresholds['acceptable_range']['min']:
            return "optimal"
        elif occupancy >= 50:
            return "underutilized"
        else:
            return "severely_underutilized"

    def _determine_occupancy_action(self, occupancy: float, thresholds: Dict) -> str:
        """Expert recommendation based on occupancy level"""
        if occupancy >= 95:
            return "emergency_rate_increase"
        elif occupancy >= 90:
            return "implement_rate_increase"
        elif occupancy >= thresholds['acceptable_range']['max']:
            return "consider_modest_rate_increase"
        elif occupancy >= thresholds['acceptable_range']['min']:
            return "maintain_current_strategy"
        elif occupancy >= 50:
            return "comprehensive_analysis_needed"
        else:
            return "urgent_strategy_review"

    def _get_occupancy_interpretation(self, occupancy: float, thresholds: Dict) -> str:
        """Provide expert interpretation of occupancy level"""
        if occupancy >= 95:
            return f"Critical overcapacity at {occupancy:.1f}%. Customer experience severely impacted. Immediate rate increase required to reduce demand to sustainable levels."
        elif occupancy >= 90:
            return f"Above optimal at {occupancy:.1f}%. Approaching capacity constraints. Rate increase recommended to maintain {thresholds['target']}% target."
        elif occupancy >= thresholds['acceptable_range']['min']:
            return f"Within optimal range at {occupancy:.1f}%. Good balance of utilization and availability consistent with industry best practices."
        elif occupancy >= 50:
            return f"Below optimal at {occupancy:.1f}%. Revenue opportunity exists. Analyze pricing, marketing, and accessibility before considering rate reductions."
        else:
            return f"Significantly underutilized at {occupancy:.1f}%. Comprehensive strategy review needed. Price reduction alone unlikely to solve utilization issues."

    async def _calculate_revpash(self, zone_stats: Dict[str, Any]) -> Optional[float]:
        """Calculate Revenue per Available Space Hour (RevPASH)"""
        try:
            total_revenue = float(zone_stats.get('total_revenue', 0))
            capacity = float(zone_stats.get('capacity', 0))
            active_days = float(zone_stats.get('active_days', 30))  # Default to 30 days
            hours_per_day = 12  # Typical enforcement hours - could be made configurable

            if capacity > 0 and active_days > 0:
                total_space_hours = capacity * active_days * hours_per_day
                revpash = total_revenue / total_space_hours
                return round(revpash, 2)
        except (ValueError, ZeroDivisionError):
            pass
        return None

    async def _analyze_revenue_performance(self, revpash: Optional[float], zone_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Expert-level revenue analysis using RevPASH and industry benchmarks"""

        # Get revenue benchmarks from knowledge base
        benchmark_query = """
            SELECT quantitative_benchmarks, content
            FROM industry_knowledge
            WHERE category = 'revenue' AND knowledge_type = 'benchmark'
            ORDER BY confidence_level DESC
            LIMIT 1
        """
        benchmark = await self.db.fetchrow(benchmark_query)

        analysis = {
            'revpash': revpash,
            'performance_assessment': 'insufficient_data' if not revpash else self._assess_revpash_performance(revpash, benchmark),
            'revenue_opportunity': await self._identify_revenue_opportunities(zone_stats),
            'benchmarking': await self._benchmark_against_industry(revpash, zone_stats)
        }

        return analysis

    def _assess_revpash_performance(self, revpash: float, benchmark: Optional[Dict]) -> Dict[str, Any]:
        """Assess RevPASH performance against industry standards"""

        # Default benchmarks if not in database
        default_benchmarks = {
            "excellent": 2.50,
            "good": 1.50,
            "concerning": 0.75,
            "target_range": "1.80-2.80"
        }

        if benchmark and benchmark.get('quantitative_benchmarks'):
            benchmarks = benchmark['quantitative_benchmarks']
        else:
            benchmarks = default_benchmarks

        if revpash >= benchmarks.get('excellent', 2.50):
            status = "excellent"
            interpretation = f"Strong revenue performance at ${revpash:.2f}/space-hour. Well above industry benchmark."
        elif revpash >= benchmarks.get('good', 1.50):
            status = "good"
            interpretation = f"Solid revenue generation at ${revpash:.2f}/space-hour. Room for optimization to reach ${benchmarks.get('excellent', 2.50):.2f}+ range."
        elif revpash >= benchmarks.get('concerning', 0.75):
            status = "concerning"
            interpretation = f"Below-target performance at ${revpash:.2f}/space-hour. Significant optimization opportunity exists."
        else:
            status = "critical"
            interpretation = f"Poor revenue performance at ${revpash:.2f}/space-hour. Immediate intervention required."

        return {
            'status': status,
            'interpretation': interpretation,
            'benchmark_comparison': benchmarks,
            'improvement_potential': max(0, benchmarks.get('excellent', 2.50) - revpash)
        }

    async def _generate_strategic_recommendations(self, zone_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate expert strategic recommendations using decision frameworks"""

        recommendations = []
        occupancy = float(zone_stats.get('avg_daily_occupancy_ratio', 0))

        # Get decision frameworks from knowledge base
        frameworks_query = """
            SELECT framework_name, decision_matrix, expected_outcomes, context_triggers
            FROM decision_frameworks
            WHERE decision_type = 'pricing' OR decision_type = 'comprehensive'
            ORDER BY framework_name
        """
        frameworks = await self.db.fetch(frameworks_query)

        for framework in frameworks:
            try:
                decision_matrix = json.loads(framework['decision_matrix']) if isinstance(framework['decision_matrix'], str) else framework['decision_matrix']
                expected_outcomes = json.loads(framework['expected_outcomes']) if isinstance(framework['expected_outcomes'], str) else framework['expected_outcomes']

                # Apply framework logic
                if occupancy > 90 and 'above_90' in decision_matrix:
                    rec = decision_matrix['above_90']
                    recommendations.append({
                        'framework': framework['framework_name'],
                        'recommendation': rec['action'],
                        'details': rec.get('increment', 'See framework'),
                        'expected_outcome': expected_outcomes,
                        'priority': 'high',
                        'reasoning': f"Occupancy at {occupancy:.1f}% exceeds 90% threshold"
                    })
                elif occupancy < 50 and 'below_50' in decision_matrix:
                    rec = decision_matrix['below_50']
                    recommendations.append({
                        'framework': framework['framework_name'],
                        'recommendation': rec['action'],
                        'details': rec.get('consider', 'Comprehensive analysis'),
                        'expected_outcome': expected_outcomes,
                        'priority': 'medium',
                        'reasoning': f"Occupancy at {occupancy:.1f}% below 50% threshold"
                    })
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error processing framework {framework['framework_name']}: {e}")
                continue

        # Add expert tactical recommendations
        tactical_recs = await self._get_tactical_recommendations(zone_stats)
        recommendations.extend(tactical_recs)

        return recommendations

    async def _get_tactical_recommendations(self, zone_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get specific tactical recommendations from operational tactics knowledge"""

        recommendations = []
        occupancy = float(zone_stats.get('avg_daily_occupancy_ratio', 0))

        # Query operational tactics
        tactics_query = """
            SELECT tactic_name, implementation_details, expected_impact, tactic_category
            FROM operational_tactics
            WHERE
                (tactic_category = 'pricing' AND $1 > 85) OR
                (tactic_category = 'marketing' AND $1 < 60) OR
                tactic_category = 'operations'
            ORDER BY tactic_category, tactic_name
        """
        tactics = await self.db.fetch(tactics_query, occupancy)

        for tactic in tactics:
            try:
                expected_impact = json.loads(tactic['expected_impact']) if isinstance(tactic['expected_impact'], str) else tactic['expected_impact']

                recommendations.append({
                    'tactic': tactic['tactic_name'],
                    'category': tactic['tactic_category'],
                    'implementation': tactic['implementation_details'],
                    'expected_impact': expected_impact,
                    'applicability': self._assess_tactic_applicability(tactic, zone_stats)
                })
            except (json.JSONDecodeError) as e:
                logger.warning(f"Error processing tactic {tactic['tactic_name']}: {e}")
                continue

        return recommendations

    def _assess_tactic_applicability(self, tactic: Dict, zone_stats: Dict[str, Any]) -> str:
        """Assess how applicable a tactic is to the current situation"""
        occupancy = float(zone_stats.get('avg_daily_occupancy_ratio', 0))

        if 'peak' in tactic['tactic_name'].lower() and occupancy > 85:
            return "highly_applicable"
        elif 'off-peak' in tactic['tactic_name'].lower() and occupancy < 60:
            return "highly_applicable"
        else:
            return "potentially_applicable"

    async def _provide_market_context(self, zone_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Provide market context and benchmarking information"""

        # Get market behavior patterns
        patterns_query = """
            SELECT behavior_type, behavior_description, quantitative_data
            FROM market_behavior
            WHERE behavior_type IN ('elasticity', 'benchmark', 'seasonality')
            ORDER BY behavior_type
        """
        patterns = await self.db.fetch(patterns_query)

        context = {
            'elasticity_guidance': None,
            'seasonal_considerations': None,
            'benchmarking_data': None
        }

        for pattern in patterns:
            try:
                data = json.loads(pattern['quantitative_data']) if isinstance(pattern['quantitative_data'], str) else pattern['quantitative_data']

                if pattern['behavior_type'] == 'elasticity':
                    context['elasticity_guidance'] = {
                        'description': pattern['behavior_description'],
                        'price_increase_response': data.get('price_increase_response'),
                        'price_decrease_response': data.get('price_decrease_response')
                    }
                elif pattern['behavior_type'] == 'seasonality':
                    context['seasonal_considerations'] = {
                        'description': pattern['behavior_description'],
                        'seasonal_data': data
                    }
            except (json.JSONDecodeError) as e:
                logger.warning(f"Error processing market pattern: {e}")
                continue

        return context

    async def _apply_decision_frameworks(self, zone_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Apply comprehensive decision frameworks for expert-level analysis"""

        frameworks = {}
        occupancy = float(zone_stats.get('avg_daily_occupancy_ratio', 0))

        # 85% Rule Framework
        frameworks['occupancy_rule'] = {
            'framework': '85% Occupancy Rule',
            'current_status': f"{occupancy:.1f}%",
            'target': '85%',
            'variance': f"{occupancy - 85:+.1f}%",
            'action_required': occupancy < 80 or occupancy > 90,
            'severity': 'high' if abs(occupancy - 85) > 15 else 'medium' if abs(occupancy - 85) > 5 else 'low'
        }

        # Revenue Optimization Framework
        revpash = await self._calculate_revpash(zone_stats)
        if revpash:
            frameworks['revenue_optimization'] = {
                'framework': 'Revenue Optimization',
                'current_revpash': f"${revpash:.2f}",
                'target_range': "$1.80-2.80",
                'optimization_opportunity': max(0, 2.00 - revpash),
                'action_priority': 'high' if revpash < 1.50 else 'medium' if revpash < 2.00 else 'low'
            }

        return frameworks

    async def _generate_expert_reasoning(self, zone_stats: Dict[str, Any]) -> str:
        """Generate expert-level reasoning that explains the analysis"""

        occupancy = float(zone_stats.get('avg_daily_occupancy_ratio', 0))
        capacity = zone_stats.get('capacity', 0)
        location = zone_stats.get('location_name', 'this location')
        revpash = await self._calculate_revpash(zone_stats)

        reasoning_parts = []

        # Occupancy analysis
        if occupancy > 90:
            reasoning_parts.append(f"At {occupancy:.1f}% occupancy, {location} is operating above the industry-standard 85% optimal level, indicating potential capacity constraints and customer experience issues.")
        elif occupancy >= 80:
            reasoning_parts.append(f"With {occupancy:.1f}% occupancy, {location} is performing within the optimal range near the industry-recommended 85% target.")
        else:
            reasoning_parts.append(f"Current occupancy of {occupancy:.1f}% is below the 85% industry benchmark, suggesting revenue optimization opportunities.")

        # Revenue analysis
        if revpash:
            if revpash >= 2.50:
                reasoning_parts.append(f"Revenue performance is strong at ${revpash:.2f} per space-hour, exceeding industry benchmarks.")
            elif revpash >= 1.50:
                reasoning_parts.append(f"Revenue generation of ${revpash:.2f} per space-hour is solid but has room for improvement toward the $2.50+ excellence threshold.")
            else:
                reasoning_parts.append(f"Revenue performance of ${revpash:.2f} per space-hour is below industry standards, indicating significant optimization potential.")

        # Strategic context
        reasoning_parts.append("Recommendations are based on industry best practices including the 85% occupancy rule, demand elasticity research showing price increases are more effective than decreases, and revenue optimization frameworks used by leading parking operators.")

        return " ".join(reasoning_parts)

    async def _identify_revenue_opportunities(self, zone_stats: Dict[str, Any]) -> List[str]:
        """Identify specific revenue optimization opportunities"""

        opportunities = []
        occupancy = float(zone_stats.get('avg_daily_occupancy_ratio', 0))

        if occupancy > 90:
            opportunities.append("Peak period rate increase to manage demand and capture premium pricing")
            opportunities.append("Implement dynamic pricing to automatically adjust rates based on real-time occupancy")
        elif occupancy < 60:
            opportunities.append("Analyze off-peak periods for promotional pricing opportunities")
            opportunities.append("Review marketing and accessibility to increase demand")
            opportunities.append("Consider partnership opportunities to drive traffic")

        # Always consider these
        opportunities.append("Extend operating hours if demand exists beyond current enforcement periods")
        opportunities.append("Optimize permit vs transient parking allocation based on yield analysis")

        return opportunities

    async def _benchmark_against_industry(self, revpash: Optional[float], zone_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark performance against industry standards"""

        benchmarking = {
            'occupancy_benchmark': '85% (industry standard)',
            'revenue_benchmark': '$1.80-2.80 per space-hour (downtown)',
            'current_performance': {},
            'improvement_potential': {}
        }

        occupancy = float(zone_stats.get('avg_daily_occupancy_ratio', 0))

        benchmarking['current_performance']['occupancy'] = f"{occupancy:.1f}%"
        benchmarking['improvement_potential']['occupancy'] = f"{85 - occupancy:+.1f}% to optimal"

        if revpash:
            benchmarking['current_performance']['revenue'] = f"${revpash:.2f}/space-hour"
            benchmarking['improvement_potential']['revenue'] = f"${max(0, 2.00 - revpash):.2f}/space-hour opportunity"

        return benchmarking