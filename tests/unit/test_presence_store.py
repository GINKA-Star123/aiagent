import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import aiagent.presence.store as store_module


@pytest.mark.parametrize("redis_enabled", [False, True])
def test_get_snapshot_awaits_client_and_handles_empty_storage(monkeypatch, redis_enabled):
    client = SimpleNamespace(get=AsyncMock(return_value=None)) if redis_enabled else None
    getter = AsyncMock(return_value=client)
    monkeypatch.setattr(store_module, "get_redis_client", getter)

    snapshot = asyncio.run(store_module.PresenceStore().get_snapshot("u1", "测试用户"))

    getter.assert_awaited_once_with()
    assert snapshot.user_id == "u1"
    assert snapshot.username == "测试用户"
    if client is not None:
        client.get.assert_awaited_once_with(store_module.PresenceStore()._key("u1"))
