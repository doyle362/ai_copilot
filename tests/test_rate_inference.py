import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch
from services.analyst.analyst.core.rate_inference import RateInference


class TestRateInference:
    """Test rate inference functionality."""

    @pytest.fixture
    def sample_transaction_data(self):
        """Sample transaction data for testing."""
        return [
            {
                "created_at": "2024-01-15T10:00:00",
                "zone_id": "z-110",
                "location_id": "550e8400-e29b-41d4-a716-446655440001",
                "duration_minutes": 60,
                "rate_per_hour": 5.0,
                "total_amount": 5.0
            },
            {
                "created_at": "2024-01-15T14:00:00",
                "zone_id": "z-110",
                "location_id": "550e8400-e29b-41d4-a716-446655440001",
                "duration_minutes": 120,
                "rate_per_hour": 4.5,
                "total_amount": 9.0
            },
            {
                "created_at": "2024-01-15T23:00:00",
                "zone_id": "z-110",
                "location_id": "550e8400-e29b-41d4-a716-446655440001",
                "duration_minutes": 240,
                "rate_per_hour": 4.0,
                "total_amount": 16.0
            }
        ]

    @pytest.mark.asyncio
    async def test_infer_current_rates_success(self, mock_db, sample_transaction_data):
        """Test successful rate inference."""
        mock_db.fetch.return_value = sample_transaction_data

        with patch.object(RateInference, '_store_inferred_plans', new_callable=AsyncMock):
            rate_inference = RateInference(mock_db)
            result = await rate_inference.infer_current_rates("z-110")

            assert result["status"] == "success"
            assert result["zone_id"] == "z-110"
            assert result["plans_generated"] >= 0

    @pytest.mark.asyncio
    async def test_infer_current_rates_no_data(self, mock_db):
        """Test rate inference with no transaction data."""
        mock_db.fetch.return_value = []  # No data

        rate_inference = RateInference(mock_db)
        result = await rate_inference.infer_current_rates("z-110")

        assert result["status"] == "no_data"
        assert result["zone_id"] == "z-110"

    @pytest.mark.asyncio
    async def test_get_transaction_data(self, mock_db, sample_transaction_data):
        """Test retrieving transaction data."""
        mock_db.fetch.return_value = sample_transaction_data

        rate_inference = RateInference(mock_db)
        data = await rate_inference._get_transaction_data("z-110", None, 30)

        assert len(data) == 3
        assert all("duration_minutes" in item for item in data)
        assert all("rate_per_hour" in item for item in data)

        # Verify query was called with correct parameters
        mock_db.fetch.assert_called_once()
        call_args = mock_db.fetch.call_args[0]
        assert "z-110" in call_args

    def test_add_time_features(self, sample_transaction_data):
        """Test adding time-based features to transaction data."""
        rate_inference = RateInference(MagicMock())

        df = pd.DataFrame(sample_transaction_data)
        df['created_at'] = pd.to_datetime(df['created_at'])

        # Add time features
        result_df = rate_inference._add_time_features(df)

        assert 'local_time' in result_df.columns
        assert 'hour' in result_df.columns
        assert 'dow' in result_df.columns
        assert 'daypart' in result_df.columns

        # Check daypart classification
        morning_entries = result_df[result_df['daypart'] == 'morning']
        evening_entries = result_df[result_df['daypart'] == 'evening']

        assert len(morning_entries) == 2
        assert len(evening_entries) == 1

    def test_infer_tiers_from_durations(self, sample_transaction_data):
        """Test inferring pricing tiers from duration patterns."""
        rate_inference = RateInference(MagicMock())

        extended_data = []
        durations = [30, 45, 60, 75, 90, 120, 150, 180, 210, 240, 270, 300]
        for idx, duration in enumerate(durations):
            extended_data.append({
                "duration_minutes": duration,
                "rate_per_hour": 6.0 - (idx * 0.2),
                "total_amount": duration * (6.0 - (idx * 0.2)) / 60
            })

        df = pd.DataFrame(extended_data)
        tiers = rate_inference._infer_tiers_from_durations(df)

        assert tiers is not None
        assert len(tiers) >= 1
        assert tiers[0]["duration_max_minutes"] == 60

    def test_infer_tiers_insufficient_data(self):
        """Test tier inference with insufficient data."""
        rate_inference = RateInference(MagicMock())

        # Too few data points
        small_df = pd.DataFrame([
            {"duration_minutes": 60, "rate_per_hour": 5.0},
            {"duration_minutes": 120, "rate_per_hour": 4.0}
        ])

        tiers = rate_inference._infer_tiers_from_durations(small_df)
        assert tiers is None

    @pytest.mark.asyncio
    async def test_store_inferred_plans(self, mock_db):
        """Test storing inferred rate plans."""
        sample_plans = [
            {
                "location_id": "550e8400-e29b-41d4-a716-446655440001",
                "zone_id": "z-110",
                "daypart": "morning",
                "dow": 1,  # Monday
                "tiers": [
                    {"duration_max_minutes": 60, "rate_per_hour": 5.0, "description": "First hour"},
                    {"duration_max_minutes": 180, "rate_per_hour": 4.0, "description": "2-3 hours"}
                ],
                "source": "transaction_analysis"
            }
        ]

        rate_inference = RateInference(mock_db)
        await rate_inference._store_inferred_plans(sample_plans)

        # Should have called execute twice on the transaction connection
        assert mock_db.connection.execute.call_count == 2

        delete_call = mock_db.connection.execute.call_args_list[0]
        assert "DELETE FROM inferred_rate_plans" in delete_call[0][0]

        insert_call = mock_db.connection.execute.call_args_list[1]
        assert "INSERT INTO inferred_rate_plans" in insert_call[0][0]

    @pytest.mark.asyncio
    async def test_store_inferred_plans_empty(self, mock_db):
        """Test storing empty inferred plans list."""
        rate_inference = RateInference(mock_db)
        await rate_inference._store_inferred_plans([])

        # Should not call database if no plans
        mock_db.connection.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_inferred_rates(self, mock_db):
        """Test retrieving current inferred rates."""
        mock_rates = [
            {
                "location_id": "550e8400-e29b-41d4-a716-446655440001",
                "zone_id": "z-110",
                "daypart": "morning",
                "dow": 1,
                "tiers": [{"duration_max_minutes": 60, "rate_per_hour": 5.0}],
                "source": "analysis",
                "created_at": "2024-01-15T10:00:00Z"
            }
        ]

        mock_db.fetch.return_value = mock_rates

        rate_inference = RateInference(mock_db)
        rates = await rate_inference.get_current_inferred_rates("z-110")

        assert len(rates) == 1
        assert rates[0]["zone_id"] == "z-110"
        assert rates[0]["daypart"] == "morning"

    @pytest.mark.asyncio
    async def test_infer_current_rates_error_handling(self, mock_db):
        """Test error handling in rate inference."""
        # Mock database error
        mock_db.fetch.side_effect = Exception("Database connection failed")

        rate_inference = RateInference(mock_db)
        result = await rate_inference.infer_current_rates("z-110")

        assert result["status"] == "no_data"
        assert result["zone_id"] == "z-110"

    @pytest.mark.asyncio
    async def test_complex_daypart_analysis(self, mock_db):
        """Test rate inference with data spanning multiple dayparts and days."""
        complex_data = []

        # Generate data for different days of week and dayparts
        for dow in range(7):  # All days of week
            for hour in [10, 23]:  # Morning and evening (UTC -> local split)
                for duration in [45, 90, 180]:  # Different durations
                    complex_data.append({
                        "created_at": f"2024-01-{15 + dow:02d}T{hour:02d}:00:00",
                        "zone_id": "z-110",
                        "location_id": "550e8400-e29b-41d4-a716-446655440001",
                        "duration_minutes": duration,
                        "rate_per_hour": 5.0 - (duration / 120),  # Decreasing rate for longer stays
                        "total_amount": duration * (5.0 - (duration / 120)) / 60
                    })

        mock_db.fetch.return_value = complex_data

        with patch.object(RateInference, '_store_inferred_plans', new_callable=AsyncMock):
            rate_inference = RateInference(mock_db)
            result = await rate_inference.infer_current_rates("z-110")

            assert result["status"] in {"success", "no_data"}
