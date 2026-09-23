from __future__ import annotations

import asyncio

import pytest

import aiagent.perception.voice_call_store as store_module
from aiagent.perception.voice_call_store import (
    VoiceCallStoreUnavailableError,
    VoiceRealtimeCallStore,
)


async def _missing_redis():
    return None


def test_redis_store_fail_closed_when_redis_is_missing(
    monkeypatch,
):
    monkeypatch.setattr(
        store_module,
        "get_redis_client",
        _missing_redis,
    )

    async def run():
        store = VoiceRealtimeCallStore(
            prefix="unit:aiagent",
            provider="redis",
            fail_open=False,
        )

        with pytest.raises(
            VoiceCallStoreUnavailableError
        ):
            await store.start(
                user_id="u1",
                username="tester",
            )

    asyncio.run(run())


def test_redis_store_fail_open_uses_memory(
    monkeypatch,
):
    monkeypatch.setattr(
        store_module,
        "get_redis_client",
        _missing_redis,
    )

    async def run():
        store = VoiceRealtimeCallStore(
            prefix="unit:aiagent",
            provider="redis",
            fail_open=True,
        )

        call = await store.start(
            user_id="u1",
            username="tester",
        )
        loaded = await store.get(call.call_id)
        status = await store.backend_status()

        assert loaded is not None
        assert loaded.call_id == call.call_id
        assert status["ok"] is True
        assert status["effective_provider"] == "memory_fallback"

    asyncio.run(run())