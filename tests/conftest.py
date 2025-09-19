
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from services.analyst.analyst.db import Database
from services.analyst.analyst.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.supabase_db_url = "postgresql://test:test@localhost:5432/test"
    settings.jwt_issuer = "test.lvlparking.com"
    settings.dev_jwt_hs256_secret = "test-secret"
    settings.dev_zone_ids_list = ["z-110", "z-221"]
    settings.org_id = "org-test"
    settings.openai_api_key = None  # Disable OpenAI calls in tests
    settings.analyst_require_approval = True
    settings.analyst_auto_apply = False
    return settings


@pytest_asyncio.fixture
async def mock_db():
    """Mock database for testing."""
    connection = MagicMock()
    connection.execute = AsyncMock(return_value="")
    connection.fetch = AsyncMock(return_value=[])
    connection.fetchrow = AsyncMock(return_value=None)
    connection.fetchval = AsyncMock(return_value=None)

    transaction_mock = MagicMock()

    class _TransactionContext:
        async def __aenter__(self_inner):
            return connection

        async def __aexit__(self_inner, exc_type, exc, tb):
            return False

    transaction_mock.return_value = _TransactionContext()

    db = MagicMock(spec=Database)
    db.fetch = AsyncMock(return_value=[])
    db.fetchrow = AsyncMock(return_value=None)
    db.fetchval = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value="")
    db.transaction = transaction_mock
    db.set_jwt_claims = AsyncMock()
    db.connection = connection

    return db


@pytest.fixture
def mock_user_context():
    """Mock user context for testing."""
    return {
        "sub": "test-user",
        "org_id": "org-test",
        "roles": ["viewer", "approver"],
        "zone_ids": ["z-110", "z-221"],
        "iss": "test.lvlparking.com",
        "exp": 9999999999
    }


@pytest.fixture
def sample_insight():
    """Sample insight data for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "location_id": "550e8400-e29b-41d4-a716-446655440001",
        "zone_id": "z-110",
        "kind": "performance",
        "window": "7d",
        "narrative_text": "Occupancy increased 15% over the last week",
        "confidence": 0.82,
        "metrics_json": {"occupancy_change": 0.15, "revenue_change": 0.08},
        "created_at": "2024-01-15T10:00:00Z",
        "created_by": None
    }


@pytest.fixture
def sample_recommendation():
    """Sample recommendation data for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "location_id": "550e8400-e29b-41d4-a716-446655440001",
        "zone_id": "z-110",
        "type": "price_adjustment",
        "proposal": {
            "target_daypart": "morning",
            "price_changes": [
                {
                    "tier_description": "First hour",
                    "current_rate": 5.00,
                    "proposed_rate": 5.50,
                    "change_pct": 0.10
                }
            ]
        },
        "rationale_text": "High occupancy indicates room for price optimization",
        "expected_lift_json": {"revenue_lift_pct": 0.08, "occupancy_impact_pct": -0.02},
        "confidence": 0.75,
        "requires_approval": True,
        "memory_ids_used": [],
        "prompt_version_id": None,
        "thread_id": None,
        "status": "draft",
        "created_at": "2024-01-15T10:00:00Z"
    }


@pytest.fixture
def sample_price_change():
    """Sample price change data for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "location_id": "550e8400-e29b-41d4-a716-446655440001",
        "zone_id": "z-110",
        "prev_price": 5.00,
        "new_price": 5.50,
        "change_pct": 0.10,
        "policy_version": "v1.0",
        "recommendation_id": "550e8400-e29b-41d4-a716-446655440002",
        "applied_by": None,
        "applied_at": None,
        "revert_to": 5.00,
        "revert_if": None,
        "expires_at": None,
        "status": "pending",
        "created_at": "2024-01-15T10:00:00Z"
    }
