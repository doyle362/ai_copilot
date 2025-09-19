import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.analyst.analyst.core.policy_guardrails import PolicyGuardrails, GuardrailViolation
from services.analyst.analyst.models.changes import PriceChangeCreate


class TestGuardrails:
    """Test policy guardrails functionality."""

    @pytest.fixture
    def mock_guardrails_data(self):
        """Mock guardrails data for testing."""
        return [
            {
                "name": "default-guardrails",
                "json_schema": {
                    "max_change_pct": 0.15,
                    "min_price": 2.0,
                    "blackout_weekday_hours": {"fri": [16, 17, 18, 19]},
                    "require_approval_if_confidence_lt": 0.7
                }
            }
        ]

    @pytest.mark.asyncio
    async def test_validate_price_change_valid(self, mock_db, mock_guardrails_data):
        """Test price change validation with valid change."""
        mock_db.fetch.side_effect = [mock_guardrails_data, []]

        guardrails = PolicyGuardrails(mock_db)

        change = PriceChangeCreate(
            zone_id="z-110",
            prev_price=5.00,
            new_price=5.50,
            change_pct=0.10  # 10% increase, within 15% limit
        )

        result = await guardrails.validate_price_change(change)

        assert result.is_valid
        assert result.reason is None
        assert len(result.violated_rules) == 0

    @pytest.mark.asyncio
    async def test_validate_price_change_exceeds_max_change(self, mock_db, mock_guardrails_data):
        """Test price change validation with excessive change percentage."""
        mock_db.fetch.side_effect = [mock_guardrails_data, []]

        guardrails = PolicyGuardrails(mock_db)

        change = PriceChangeCreate(
            zone_id="z-110",
            prev_price=5.00,
            new_price=6.00,
            change_pct=0.20  # 20% increase, exceeds 15% limit
        )

        result = await guardrails.validate_price_change(change)

        assert not result.is_valid
        assert "Change percentage 20.0% exceeds maximum 15.0%" in result.reason
        assert any("exceeds maximum" in rule for rule in result.violated_rules)

    @pytest.mark.asyncio
    async def test_validate_price_change_below_min_price(self, mock_db, mock_guardrails_data):
        """Test price change validation with price below minimum."""
        mock_db.fetch.side_effect = [mock_guardrails_data, []]

        guardrails = PolicyGuardrails(mock_db)

        change = PriceChangeCreate(
            zone_id="z-110",
            prev_price=3.00,
            new_price=1.50,  # Below $2.00 minimum
            change_pct=-0.50
        )

        result = await guardrails.validate_price_change(change)

        assert not result.is_valid
        assert "New price $1.50 below minimum $2.00" in result.reason
        assert len(result.violated_rules) >= 1

    @pytest.mark.asyncio
    async def test_validate_price_change_multiple_violations(self, mock_db, mock_guardrails_data):
        """Test price change validation with multiple violations."""
        mock_db.fetch.side_effect = [mock_guardrails_data, []]

        guardrails = PolicyGuardrails(mock_db)

        change = PriceChangeCreate(
            zone_id="z-110",
            prev_price=3.00,
            new_price=1.00,  # Below minimum AND large change
            change_pct=-0.67  # -67% change, exceeds 15% limit
        )

        result = await guardrails.validate_price_change(change)

        assert not result.is_valid
        assert len(result.violated_rules) == 2
        assert "New price $1.00 below minimum $2.00" in result.reason
        assert "Change percentage -67.0% exceeds maximum 15.0%" in result.reason

    @pytest.mark.asyncio
    async def test_validate_price_change_no_guardrails(self, mock_db):
        """Test price change validation with no active guardrails."""
        mock_db.fetch.side_effect = [[], []]

        guardrails = PolicyGuardrails(mock_db)

        change = PriceChangeCreate(
            zone_id="z-110",
            prev_price=5.00,
            new_price=10.00,  # 100% increase
            change_pct=1.0
        )

        result = await guardrails.validate_price_change(change)

        assert result.is_valid  # Should allow when no guardrails
        assert result.reason is None

    @pytest.mark.asyncio
    @patch('services.analyst.analyst.core.policy_guardrails.datetime')
    async def test_check_blackout_hours(self, mock_datetime, mock_db, mock_guardrails_data):
        """Test blackout hour restrictions."""
        from datetime import datetime
        import pytz

        # Mock current time to Friday 5 PM CST (blackout hour)
        mock_now = datetime(2024, 1, 19, 17, 0, 0)  # Friday 5 PM
        mock_datetime.now.return_value = mock_now.replace(tzinfo=pytz.timezone('America/Chicago'))

        mock_db.fetch.side_effect = [mock_guardrails_data, []]

        guardrails = PolicyGuardrails(mock_db)

        change = PriceChangeCreate(
            zone_id="z-110",
            prev_price=5.00,
            new_price=5.50,
            change_pct=0.10
        )

        result = await guardrails.validate_price_change(change)

        assert not result.is_valid
        assert "price changes not allowed on fri at hour 17" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_check_rate_consistency(self, mock_db, mock_guardrails_data):
        """Test rate consistency check."""
        recent_changes = [
            {"new_price": 5.00},
            {"new_price": 5.10},
            {"new_price": 4.90}
        ]
        mock_db.fetch.side_effect = [mock_guardrails_data, recent_changes]

        guardrails = PolicyGuardrails(mock_db)

        # Price change that's very different from recent average (~5.00)
        change = PriceChangeCreate(
            zone_id="z-110",
            prev_price=5.00,
            new_price=8.00,  # 60% increase from recent average
            change_pct=0.60
        )

        # This should trigger rate consistency warning
        result = await guardrails.validate_price_change(change)

        # Should still be valid but have warning
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_get_guardrail_summary(self, mock_db, mock_guardrails_data):
        """Test guardrail summary generation."""
        mock_db.fetch.side_effect = [mock_guardrails_data, []]

        guardrails = PolicyGuardrails(mock_db)
        summary = await guardrails.get_guardrail_summary()

        assert summary["active_count"] == 1
        assert "default-guardrails" in summary["rules"]
        assert summary["rules"]["default-guardrails"]["max_change_pct"] == 0.15
        assert summary["rules"]["default-guardrails"]["min_price"] == 2.0

    @pytest.mark.asyncio
    async def test_validate_recommendation_constraints(self, mock_db):
        """Test recommendation constraint validation."""
        mock_db.fetch.side_effect = [[], []]

        guardrails = PolicyGuardrails(mock_db)

        recommendation_data = {
            "confidence": 0.4,  # Low confidence
            "proposal": {
                "price_changes": [
                    {
                        "zone_id": "z-110",
                        "prev_price": 5.0,
                        "new_price": 5.5,
                        "change_pct": 0.1
                    }
                ]
            }
        }

        result = await guardrails.validate_recommendation_constraints(recommendation_data)

        assert result.is_valid  # Should be valid
        assert "Low confidence recommendation (40.0%)" in str(result.warnings)

    def test_guardrail_violation_model(self):
        """Test GuardrailViolation model."""
        violation = GuardrailViolation(
            is_valid=False,
            reason="Test violation",
            violated_rules=["rule1", "rule2"],
            warnings=["warning1"]
        )

        assert not violation.is_valid
        assert violation.reason == "Test violation"
        assert len(violation.violated_rules) == 2
        assert len(violation.warnings) == 1

        # Test valid violation
        valid = GuardrailViolation(is_valid=True)
        assert valid.is_valid
        assert valid.reason is None
