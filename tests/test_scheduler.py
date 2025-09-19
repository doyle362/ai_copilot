import pytest

from analyst import scheduler
from analyst.config import settings


@pytest.mark.asyncio
async def test_scheduler_resolves_configured_zone_ids(monkeypatch):
    manager = scheduler.SchedulerManager()

    original = settings.scheduler_zone_ids
    settings.scheduler_zone_ids = "z-1, z-2"
    try:
        async def _fail_fetch(_query):  # pragma: no cover - should not run
            raise AssertionError("DB fetch should not be called when zone IDs are configured")

        monkeypatch.setattr(scheduler.db, "fetch", _fail_fetch)

        zone_ids = await manager._resolve_zone_ids()
        assert zone_ids == ["z-1", "z-2"]
    finally:
        settings.scheduler_zone_ids = original


@pytest.mark.asyncio
async def test_scheduler_falls_back_to_dev_zones(monkeypatch):
    manager = scheduler.SchedulerManager()

    original_config = settings.scheduler_zone_ids
    original_dev = settings.dev_zone_ids
    settings.scheduler_zone_ids = None
    settings.dev_zone_ids = "dev-1,dev-2"

    async def _fake_fetch(_query):
        return []

    monkeypatch.setattr(scheduler.db, "fetch", _fake_fetch)

    try:
        zone_ids = await manager._resolve_zone_ids()
        assert zone_ids == ["dev-1", "dev-2"]
    finally:
        settings.scheduler_zone_ids = original_config
        settings.dev_zone_ids = original_dev


@pytest.mark.asyncio
async def test_scheduler_prefers_database_results(monkeypatch):
    manager = scheduler.SchedulerManager()

    original_config = settings.scheduler_zone_ids
    settings.scheduler_zone_ids = None

    async def _fake_fetch(_query):
        return [{"zone_id": "123"}, {"zone_id": "456"}, {"zone_id": None}]

    monkeypatch.setattr(scheduler.db, "fetch", _fake_fetch)

    try:
        zone_ids = await manager._resolve_zone_ids()
        assert zone_ids == ["123", "456"]
    finally:
        settings.scheduler_zone_ids = original_config
