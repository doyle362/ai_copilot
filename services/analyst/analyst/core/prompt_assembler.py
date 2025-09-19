import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from ..db import Database

logger = logging.getLogger(__name__)


class PromptAssembler:
    def __init__(self, db: Database):
        self.db = db

    async def build_system_prompt(
        self,
        zone_id: str,
        location_id: Optional[str] = None,
        context_data: Optional[Dict] = None,
        relevant_memories: Optional[List[Dict]] = None
    ) -> str:
        """Build a comprehensive system prompt for the AI analyst"""

        try:
            # Get active prompt version
            base_prompt = await self._get_active_prompt('zone', zone_id)

            if not base_prompt:
                base_prompt = await self._get_active_prompt('global')

            if not base_prompt:
                base_prompt = "You are Level Analyst, an AI optimization copilot for Level Parking."

            # Get guardrails context
            guardrails = await self._get_guardrails_context()

            # Build comprehensive prompt
            prompt_sections = [
                base_prompt,
                "",
                "## CONTEXT",
                f"Zone: {zone_id}",
                f"Location: {location_id or 'N/A'}",
                f"Analysis Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                ""
            ]

            # Add performance context
            if context_data and context_data.get('recent_metrics'):
                metrics_summary = self._summarize_metrics(context_data['recent_metrics'])
                prompt_sections.extend([
                    "## RECENT PERFORMANCE",
                    metrics_summary,
                    ""
                ])

            # Add current pricing context
            if context_data and context_data.get('current_rates'):
                rates_summary = self._summarize_rates(context_data['current_rates'])
                prompt_sections.extend([
                    "## CURRENT PRICING",
                    rates_summary,
                    ""
                ])

            # Add guardrails
            if guardrails:
                prompt_sections.extend([
                    "## GUARDRAILS (MUST COMPLY)",
                    guardrails,
                    ""
                ])

            # Add relevant memories
            if relevant_memories:
                memories_context = self._format_memories(relevant_memories)
                prompt_sections.extend([
                    "## PRIOR FEEDBACK & INSIGHTS",
                    memories_context,
                    ""
                ])

            # Add output format requirements
            prompt_sections.extend([
                "## OUTPUT REQUIREMENTS",
                "- Provide recommendations as valid JSON",
                "- Include clear rationale for each recommendation",
                "- Specify confidence levels (0.0-1.0)",
                "- Respect all guardrails and constraints",
                "- If confidence < 0.6, ask clarifying questions",
                ""
            ])

            return "\n".join(prompt_sections)

        except Exception as e:
            logger.error(f"Error building system prompt: {str(e)}")
            return "You are Level Analyst, an AI optimization copilot for Level Parking. Provide safe, data-driven recommendations."

    async def _get_active_prompt(
        self,
        scope: str,
        scope_ref: Optional[str] = None
    ) -> Optional[str]:
        """Get the active prompt for a given scope"""

        query = """
            SELECT system_prompt
            FROM agent_prompt_versions
            WHERE scope = $1
                AND ($2::text IS NULL OR scope_ref::text = $2)
                AND is_active = true
            ORDER BY created_at DESC
            LIMIT 1
        """

        try:
            result = await self.db.fetchrow(query, scope, scope_ref)
            return result['system_prompt'] if result else None
        except Exception as e:
            logger.error(f"Error fetching active prompt: {str(e)}")
            return None

    async def _get_guardrails_context(self) -> str:
        """Format guardrails for prompt context"""

        query = """
            SELECT name, json_schema
            FROM agent_guardrails
            WHERE is_active = true
            ORDER BY name
        """

        try:
            results = await self.db.fetch(query)

            if not results:
                return "No specific guardrails configured."

            guardrail_lines = []
            for row in results:
                schema = row['json_schema']

                if isinstance(schema, dict):
                    rules = []

                    if 'max_change_pct' in schema:
                        rules.append(f"Maximum price change: {schema['max_change_pct']:.1%}")

                    if 'min_price' in schema:
                        rules.append(f"Minimum price: ${schema['min_price']:.2f}")

                    if 'blackout_weekday_hours' in schema:
                        blackout_info = []
                        for day, hours in schema['blackout_weekday_hours'].items():
                            blackout_info.append(f"{day}: hours {hours}")
                        rules.append(f"Blackout hours: {', '.join(blackout_info)}")

                    if 'require_approval_if_confidence_lt' in schema:
                        rules.append(f"Require approval if confidence < {schema['require_approval_if_confidence_lt']}")

                    if rules:
                        guardrail_lines.append(f"- {row['name']}: {'; '.join(rules)}")

            return "\n".join(guardrail_lines) if guardrail_lines else "Standard safety guardrails apply."

        except Exception as e:
            logger.error(f"Error formatting guardrails: {str(e)}")
            return "Error loading guardrails - proceed with caution."

    def _summarize_metrics(self, metrics: List[Dict]) -> str:
        """Summarize recent performance metrics"""

        if not metrics:
            return "No recent performance data available."

        try:
            # Get recent trend
            recent_7d = metrics[:7] if len(metrics) >= 7 else metrics

            avg_rev = sum(m.get('rev', 0) for m in recent_7d) / len(recent_7d)
            avg_occ = sum(m.get('occupancy_pct', 0) for m in recent_7d) / len(recent_7d)
            avg_ticket = sum(m.get('avg_ticket', 0) for m in recent_7d) / len(recent_7d)

            # Compare to older period if available
            comparison = ""
            if len(metrics) >= 14:
                older_7d = metrics[7:14]
                old_avg_rev = sum(m.get('rev', 0) for m in older_7d) / len(older_7d)
                old_avg_occ = sum(m.get('occupancy_pct', 0) for m in older_7d) / len(older_7d)

                if old_avg_rev > 0:
                    rev_change = (avg_rev - old_avg_rev) / old_avg_rev
                    occ_change = avg_occ - old_avg_occ

                    comparison = f" (Revenue {rev_change:+.1%}, Occupancy {occ_change:+.1%} vs prior week)"

            return f"7-day average: Revenue ${avg_rev:.0f}, Occupancy {avg_occ:.1%}, Avg Ticket ${avg_ticket:.2f}{comparison}"

        except Exception as e:
            logger.error(f"Error summarizing metrics: {str(e)}")
            return "Recent performance metrics available but analysis failed."

    def _summarize_rates(self, rates: List[Dict]) -> str:
        """Summarize current rate structure"""

        if not rates:
            return "No current rate structure available."

        try:
            summary_lines = []

            # Group by daypart
            morning_rates = [r for r in rates if r.get('daypart') == 'morning']
            evening_rates = [r for r in rates if r.get('daypart') == 'evening']

            if morning_rates:
                morning_example = morning_rates[0]
                tiers = morning_example.get('tiers', [])
                if tiers:
                    first_tier = tiers[0]
                    summary_lines.append(f"Morning rates: Starting at ${first_tier.get('rate_per_hour', 0):.2f}/hour")

            if evening_rates:
                evening_example = evening_rates[0]
                tiers = evening_example.get('tiers', [])
                if tiers:
                    first_tier = tiers[0]
                    summary_lines.append(f"Evening rates: Starting at ${first_tier.get('rate_per_hour', 0):.2f}/hour")

            return "\n".join(summary_lines) if summary_lines else "Rate structure configured but details unavailable."

        except Exception as e:
            logger.error(f"Error summarizing rates: {str(e)}")
            return "Current rate structure available but analysis failed."

    def _format_memories(self, memories: List[Dict]) -> str:
        """Format relevant memories for prompt context"""

        if not memories:
            return "No prior insights or feedback available."

        try:
            formatted_memories = []

            for memory in memories:
                kind = memory.get('kind', 'context')
                content = memory.get('content', '')
                topic = memory.get('topic', 'general')

                # Truncate very long memories
                if len(content) > 200:
                    content = content[:197] + "..."

                formatted_memories.append(f"[{kind.upper()}/{topic}] {content}")

            return "\n".join(formatted_memories)

        except Exception as e:
            logger.error(f"Error formatting memories: {str(e)}")
            return "Prior insights available but formatting failed."