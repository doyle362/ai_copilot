import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import pytz
from pydantic import BaseModel
from ..db import Database
from ..models.changes import PriceChangeCreate
from ..config import settings
import logging

logger = logging.getLogger(__name__)


class GuardrailViolation(BaseModel):
    is_valid: bool
    reason: Optional[str] = None
    violated_rules: List[str] = []
    warnings: List[str] = []


class PolicyGuardrails:
    def __init__(self, db: Database):
        self.db = db
        self.tz = pytz.timezone(settings.tz)

    async def validate_price_change(self, change: PriceChangeCreate) -> GuardrailViolation:
        """Validate a price change against active guardrails"""

        try:
            # Get active guardrails
            guardrails = await self._get_active_guardrails()

            if not guardrails:
                logger.warning("No active guardrails found, allowing all changes")
                return GuardrailViolation(is_valid=True)

            violations = []
            warnings = []

            for guardrail in guardrails:
                rules = guardrail.get('json_schema', {})

                # Check maximum change percentage
                if 'max_change_pct' in rules and change.change_pct:
                    max_change = rules['max_change_pct']
                    if abs(change.change_pct) > max_change:
                        violations.append(f"Change percentage {change.change_pct:.1%} exceeds maximum {max_change:.1%}")

                # Check minimum price
                if 'min_price' in rules:
                    min_price = rules['min_price']
                    if change.new_price < min_price:
                        violations.append(f"New price ${change.new_price:.2f} below minimum ${min_price:.2f}")

                # Check blackout hours
                if 'blackout_weekday_hours' in rules:
                    violation = self._check_blackout_hours(change, rules['blackout_weekday_hours'])
                    if violation:
                        violations.append(violation)

                # Check confidence-based approval requirements
                if 'require_approval_if_confidence_lt' in rules:
                    min_confidence = rules['require_approval_if_confidence_lt']
                    # This would be checked if we had confidence in the change request
                    # For now, we'll assume it requires approval
                    if not change.recommendation_id:  # Direct changes need approval
                        warnings.append(f"Manual price change requires approval")

            # Check for rate consistency (no dramatic swings)
            consistency_warning = await self._check_rate_consistency(change)
            if consistency_warning:
                warnings.append(consistency_warning)

            is_valid = len(violations) == 0

            return GuardrailViolation(
                is_valid=is_valid,
                reason="; ".join(violations) if violations else None,
                violated_rules=violations,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Error validating price change: {str(e)}")
            return GuardrailViolation(
                is_valid=False,
                reason=f"Validation error: {str(e)}"
            )

    async def _get_active_guardrails(self) -> List[Dict[str, Any]]:
        """Get active guardrails from database"""

        query = """
            SELECT name, json_schema
            FROM agent_guardrails
            WHERE is_active = true
            ORDER BY name
        """

        try:
            results = await self.db.fetch(query)
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error fetching guardrails: {str(e)}")
            return []

    def _check_blackout_hours(self, change: PriceChangeCreate, blackout_rules: Dict) -> Optional[str]:
        """Check if change violates blackout hour restrictions"""

        now = datetime.now(self.tz)
        current_dow = now.strftime('%a').lower()  # mon, tue, wed, etc.
        current_hour = now.hour

        if current_dow in blackout_rules:
            blackout_hours = blackout_rules[current_dow]
            if current_hour in blackout_hours:
                return f"Price changes not allowed on {current_dow.capitalize()} at hour {current_hour}"

        return None

    async def _check_rate_consistency(self, change: PriceChangeCreate) -> Optional[str]:
        """Check for dramatic rate changes that might indicate errors"""

        if not change.prev_price or not change.change_pct:
            return None

        # Get recent price changes for this zone
        query = """
            SELECT new_price, created_at
            FROM price_changes
            WHERE zone_id = $1 AND status = 'applied'
                AND created_at > NOW() - INTERVAL '7 days'
            ORDER BY created_at DESC
            LIMIT 5
        """

        try:
            recent_changes = await self.db.fetch(query, change.zone_id)

            if recent_changes:
                recent_prices = [row['new_price'] for row in recent_changes]
                avg_recent_price = sum(recent_prices) / len(recent_prices)

                # Check if new price is dramatically different from recent average
                price_diff_pct = abs(change.new_price - avg_recent_price) / avg_recent_price

                if price_diff_pct > 0.3:  # 30% different from recent average
                    return f"New price ${change.new_price:.2f} differs {price_diff_pct:.1%} from recent average ${avg_recent_price:.2f}"

        except Exception as e:
            logger.error(f"Error checking rate consistency: {str(e)}")

        return None

    async def validate_recommendation_constraints(self, recommendation_data: Dict) -> GuardrailViolation:
        """Validate recommendation constraints beyond price changes"""

        violations = []
        warnings = []

        try:
            # Check confidence thresholds
            confidence = recommendation_data.get('confidence', 0)
            if confidence < 0.6:
                warnings.append(f"Low confidence recommendation ({confidence:.1%})")

            # Check if recommendation follows memory constraints
            if 'proposal' in recommendation_data:
                proposal = recommendation_data['proposal']

                # Validate proposal structure
                if isinstance(proposal, dict) and 'price_changes' in proposal:
                    for price_change in proposal['price_changes']:
                        change_obj = PriceChangeCreate(**price_change)
                        change_validation = await self.validate_price_change(change_obj)

                        if not change_validation.is_valid:
                            violations.extend(change_validation.violated_rules)

            return GuardrailViolation(
                is_valid=len(violations) == 0,
                reason="; ".join(violations) if violations else None,
                violated_rules=violations,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Error validating recommendation constraints: {str(e)}")
            return GuardrailViolation(
                is_valid=False,
                reason=f"Recommendation validation error: {str(e)}"
            )

    async def get_guardrail_summary(self) -> Dict[str, Any]:
        """Get summary of active guardrails for display"""

        guardrails = await self._get_active_guardrails()

        summary = {
            "active_count": len(guardrails),
            "rules": {}
        }

        for guardrail in guardrails:
            rules = guardrail.get('json_schema', {})
            summary["rules"][guardrail['name']] = rules

        return summary