import asyncio
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

import pytest

from analyst.core import daily_refresh


class DummyConnection:
    def __init__(self, tracker):
        self.tracker = tracker

    async def execute(self, query, *args):
        if "pg_advisory_lock" in query:
            self.tracker["lock_calls"] += 1
            self.tracker["locked"] = True
        return "OK"

    async def fetchval(self, query, *args):
        if "pg_advisory_unlock" in query:
            self.tracker["unlock_calls"] += 1
            self.tracker["locked"] = False
        return None


class DummyDB:
    def __init__(self):
        self.tracker = {
            "lock_calls": 0,
            "unlock_calls": 0,
            "transaction_called": False,
        }

    async def fetchval(self, query, *args, **kwargs):  # pragma: no cover - patched out in tests
        raise AssertionError("fetchval should be patched by tests")

    @asynccontextmanager
    async def transaction(self):
        self.tracker["transaction_called"] = True
        conn = DummyConnection(self.tracker)
        try:
            yield conn
        finally:
            pass


@pytest.mark.asyncio
async def test_daily_refresh_skips_when_data_current(monkeypatch):
    db = DummyDB()
    zone_ids = ["z-1"]
    today = datetime.now(timezone.utc)

    async def fake_get_latest(_db, table, _zones, **kwargs):
        return today

    monkeypatch.setattr(daily_refresh, "_get_latest_timestamp", fake_get_latest)
    monkeypatch.setattr(daily_refresh, "InsightGenerator", lambda db: None)
    monkeypatch.setattr(daily_refresh, "ExpertRecommendationEngine", lambda db: None)

    await daily_refresh.ensure_daily_refresh(db, zone_ids, force_refresh=False)

    assert db.tracker["transaction_called"] is False
    assert db.tracker["lock_calls"] == 0


@pytest.mark.asyncio
async def test_daily_refresh_force_refresh_triggers_generators(monkeypatch):
    db = DummyDB()
    zone_ids = ["z-1", "z-2"]

    generated = {}

    class InsightStub:
        def __init__(self, db):
            generated["insight_init"] = True

        async def generate_insights_for_all_zones(self, zones):
            generated["insight_zones"] = zones
            return [
                {
                    "zone_id": zone,
                    "kind": "test",
                    "window": "daily",
                    "narrative_text": "narrative",
                    "confidence": 0.5,
                    "metrics_json": {},
                }
                for zone in zones
            ]

        async def save_insights(self, insights):
            generated["insights_saved"] = insights

    class ExpertStub:
        def __init__(self, db):
            generated["expert_init"] = True

        async def generate_recommendations_for_all_zones(self, zones):
            generated["expert_zones"] = zones
            return []

    monkeypatch.setattr(daily_refresh, "InsightGenerator", InsightStub)
    monkeypatch.setattr(daily_refresh, "ExpertRecommendationEngine", ExpertStub)

    await daily_refresh.ensure_daily_refresh(db, zone_ids, force_refresh=True)

    assert db.tracker["transaction_called"] is True
    assert db.tracker["lock_calls"] == 1
    assert db.tracker["unlock_calls"] == 1
    assert generated["insight_zones"] == zone_ids
    assert generated["expert_zones"] == zone_ids
    assert "insights_saved" in generated


@pytest.mark.asyncio
async def test_daily_refresh_triggers_when_data_stale(monkeypatch):
    db = DummyDB()
    zone_ids = ["z-1"]

    stale_time = datetime.now(timezone.utc) - timedelta(days=2)
    latest_values = {
        ("insights", False): stale_time,
        ("recommendations", True): stale_time,
    }

    async def fake_get_latest(_db, table, _zones, **kwargs):
        restrict = kwargs.get('restrict_to_expert', False)
        return latest_values.get((table, restrict))

    class InsightStub:
        def __init__(self, db):
            pass

        async def generate_insights_for_all_zones(self, zones):
            return [
                {
                    "zone_id": zones[0],
                    "kind": "test",
                    "window": "daily",
                    "narrative_text": "narrative",
                    "confidence": 0.5,
                    "metrics_json": {},
                }
            ]

        async def save_insights(self, insights):
            pass

    class ExpertStub:
        def __init__(self, db):
            pass

        async def generate_recommendations_for_all_zones(self, zones):
            return []

    monkeypatch.setattr(daily_refresh, "_get_latest_timestamp", fake_get_latest)
    monkeypatch.setattr(daily_refresh, "InsightGenerator", InsightStub)
    monkeypatch.setattr(daily_refresh, "ExpertRecommendationEngine", ExpertStub)

    await daily_refresh.ensure_daily_refresh(db, zone_ids, force_refresh=False)

    assert db.tracker["transaction_called"] is True
    assert db.tracker["lock_calls"] == 1
    assert db.tracker["unlock_calls"] == 1
