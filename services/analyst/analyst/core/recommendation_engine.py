import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import openai
from ..db import Database
from ..config import settings
from .rate_inference import RateInference
from .policy_guardrails import PolicyGuardrails
from .memory_distiller import MemoryDistiller
from .prompt_assembler import PromptAssembler

logger = logging.getLogger(__name__)


class RecommendationEngine:
    def __init__(self, db: Database):
        self.db = db
        self.rate_inference = RateInference(db)
        self.guardrails = PolicyGuardrails(db)
        self.memory_distiller = MemoryDistiller(db)
        self.prompt_assembler = PromptAssembler(db)

        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key

    async def generate_recommendations_for_zone(
        self,
        zone_id: str,
        location_id: Optional[str] = None,
        context: Optional[str] = None,
        use_reason_model: bool = False,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate AI-powered recommendations for a zone"""

        try:
            logger.info(f"Generating recommendations for zone {zone_id}")

            # Step 1: Gather context data
            context_data = await self._gather_context_data(zone_id, location_id)

            # Step 2: Get relevant memories
            relevant_memories = await self.memory_distiller.get_relevant_memories(
                zone_id, context or "pricing optimization"
            )

            # Step 3: Build prompt
            system_prompt = await self.prompt_assembler.build_system_prompt(
                zone_id, location_id, context_data, relevant_memories
            )

            # Step 4: Generate recommendations using LLM
            model = settings.openai_model_reason if use_reason_model else settings.openai_model_fast

            recommendations = await self._call_llm_for_recommendations(
                system_prompt, context_data, model
            )

            # Step 5: Validate against guardrails
            validated_recommendations = []
            for rec in recommendations:
                validation = await self.guardrails.validate_recommendation_constraints(rec)
                if validation.is_valid:
                    validated_recommendations.append(rec)
                else:
                    logger.warning(f"Recommendation failed validation: {validation.reason}")
                    rec['validation_warnings'] = validation.warnings
                    rec['confidence'] = max(0, rec.get('confidence', 0.5) - 0.2)  # Reduce confidence

            # Step 6: Store recommendations
            stored_recs = []
            for rec in validated_recommendations:
                stored_rec = await self._store_recommendation(rec, zone_id, location_id, user_id)
                if stored_rec:
                    stored_recs.append(stored_rec)

            return {
                "status": "success",
                "zone_id": zone_id,
                "recommendations_generated": len(stored_recs),
                "recommendations": stored_recs
            }

        except Exception as e:
            logger.error(f"Error generating recommendations for zone {zone_id}: {str(e)}")
            return {
                "status": "error",
                "zone_id": zone_id,
                "error": str(e)
            }

    async def _gather_context_data(self, zone_id: str, location_id: Optional[str]) -> Dict[str, Any]:
        """Gather all context data needed for recommendations"""

        context = {
            "zone_id": zone_id,
            "location_id": location_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Get recent metrics
            metrics_query = """
                SELECT date, rev, occupancy_pct, avg_ticket
                FROM mart_metrics_daily
                WHERE zone_id = $1
                    AND ($2::uuid IS NULL OR location_id = $2::uuid)
                    AND date >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY date DESC
                LIMIT 30
            """

            recent_metrics = await self.db.fetch(metrics_query, zone_id, location_id)
            context["recent_metrics"] = [dict(row) for row in recent_metrics]

            # Get current inferred rates
            current_rates = await self.rate_inference.get_current_inferred_rates(zone_id, location_id)
            context["current_rates"] = current_rates

            # Get recent price changes
            changes_query = """
                SELECT new_price, prev_price, change_pct, status, applied_at
                FROM price_changes
                WHERE zone_id = $1
                    AND ($2::uuid IS NULL OR location_id = $2::uuid)
                    AND created_at >= NOW() - INTERVAL '30 days'
                ORDER BY created_at DESC
                LIMIT 10
            """

            recent_changes = await self.db.fetch(changes_query, zone_id, location_id)
            context["recent_changes"] = [dict(row) for row in recent_changes]

            # Get guardrail summary
            context["guardrails"] = await self.guardrails.get_guardrail_summary()

            return context

        except Exception as e:
            logger.error(f"Error gathering context data: {str(e)}")
            return context

    async def _call_llm_for_recommendations(
        self,
        system_prompt: str,
        context_data: Dict,
        model: str
    ) -> List[Dict[str, Any]]:
        """Call OpenAI API to generate recommendations"""

        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured, returning mock recommendations")
            return await self._generate_mock_recommendations(context_data)

        try:
            # Build user message with context
            user_message = f"""
Analyze the following parking zone data and generate pricing recommendations:

Zone: {context_data['zone_id']}
Recent Performance: {json.dumps(context_data.get('recent_metrics', [])[-7:], indent=2)}
Current Rates: {json.dumps(context_data.get('current_rates', []), indent=2)}
Recent Changes: {json.dumps(context_data.get('recent_changes', []), indent=2)}

Provide 1-3 concrete recommendations with the following JSON format:
[{{
    "type": "price_adjustment",
    "rationale_text": "Clear explanation of why this change is recommended",
    "proposal": {{
        "target_daypart": "morning|evening",
        "target_dow": [0,1,2,3,4,5,6],
        "price_changes": [{{
            "tier_description": "First hour",
            "current_rate": 5.00,
            "proposed_rate": 5.50,
            "change_pct": 0.10
        }}]
    }},
    "expected_lift_json": {{
        "revenue_lift_pct": 0.08,
        "occupancy_impact_pct": -0.02
    }},
    "confidence": 0.75
}}]
"""

            response = await openai.ChatCompletion.acreate(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            content = response.choices[0].message.content

            # Parse JSON response
            try:
                recommendations = json.loads(content)
                if not isinstance(recommendations, list):
                    recommendations = [recommendations]
                return recommendations
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {content}")
                return []

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return await self._generate_mock_recommendations(context_data)

    async def _generate_mock_recommendations(self, context_data: Dict) -> List[Dict[str, Any]]:
        """Generate mock recommendations for testing when OpenAI is not available"""

        zone_id = context_data['zone_id']
        recent_metrics = context_data.get('recent_metrics', [])

        if not recent_metrics:
            return []

        # Simple logic: if occupancy is high, suggest price increase
        latest_occupancy = recent_metrics[0].get('occupancy_pct', 0.5) if recent_metrics else 0.5

        recommendations = []

        if latest_occupancy > 0.8:
            recommendations.append({
                "type": "price_adjustment",
                "rationale_text": f"High occupancy ({latest_occupancy:.1%}) indicates demand exceeds capacity. Modest price increase recommended to optimize revenue.",
                "proposal": {
                    "target_daypart": "morning",
                    "target_dow": [1, 2, 3, 4, 5],  # Weekdays
                    "price_changes": [{
                        "tier_description": "First hour",
                        "current_rate": 5.00,
                        "proposed_rate": 5.50,
                        "change_pct": 0.10
                    }]
                },
                "expected_lift_json": {
                    "revenue_lift_pct": 0.08,
                    "occupancy_impact_pct": -0.05
                },
                "confidence": 0.72
            })
        elif latest_occupancy < 0.4:
            recommendations.append({
                "type": "price_adjustment",
                "rationale_text": f"Low occupancy ({latest_occupancy:.1%}) suggests price sensitivity. Consider modest price reduction to drive utilization.",
                "proposal": {
                    "target_daypart": "evening",
                    "target_dow": [0, 6],  # Weekends
                    "price_changes": [{
                        "tier_description": "First hour",
                        "current_rate": 6.00,
                        "proposed_rate": 5.25,
                        "change_pct": -0.125
                    }]
                },
                "expected_lift_json": {
                    "revenue_lift_pct": 0.03,
                    "occupancy_impact_pct": 0.15
                },
                "confidence": 0.68
            })

        return recommendations

    async def _store_recommendation(
        self,
        rec_data: Dict,
        zone_id: str,
        location_id: Optional[str],
        user_id: Optional[str]
    ) -> Optional[Dict]:
        """Store a recommendation in the database"""

        try:
            query = """
                INSERT INTO recommendations
                (location_id, zone_id, type, proposal, rationale_text,
                 expected_lift_json, confidence, requires_approval)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, location_id, zone_id, type, proposal, rationale_text,
                          expected_lift_json, confidence, requires_approval, memory_ids_used,
                          prompt_version_id, thread_id, status, created_at
            """

            result = await self.db.fetchrow(
                query,
                location_id,
                zone_id,
                rec_data.get('type', 'price_adjustment'),
                rec_data.get('proposal'),
                rec_data.get('rationale_text'),
                rec_data.get('expected_lift_json'),
                rec_data.get('confidence'),
                settings.analyst_require_approval
            )

            return dict(result) if result else None

        except Exception as e:
            logger.error(f"Error storing recommendation: {str(e)}")
            return None