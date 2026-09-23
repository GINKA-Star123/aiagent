from __future__ import annotations

import asyncio

from aiagent.perception.voice_call_store import VoiceRealtimeCallStore
from aiagent.schemas.voice import (
    VoiceCallStatus,
    VoiceTurnPhase,
)


def _store() -> VoiceRealtimeCallStore:
    return VoiceRealtimeCallStore(
        prefix="unit:aiagent",
        provider="memory",
        ttl_seconds=1800,
        ended_ttl_seconds=300,
    )


def test_voice_call_store_start_and_get():
    async def run():
        store = _store()

        call = await store.start(
            user_id="u1",
            username="tester",
        )
        loaded = await store.get(call.call_id)

        assert loaded is not None
        assert loaded.call_id == call.call_id
        assert loaded.user_id == "u1"
        assert loaded.username == "tester"
        assert loaded.status == VoiceCallStatus.ACTIVE
        assert loaded.phase == VoiceTurnPhase.IDLE

    asyncio.run(run())


def test_voice_call_store_turn_flow():
    async def run():
        store = _store()
        call = await store.start(
            user_id="u1",
            username="tester",
        )

        call = await store.next_turn(call.call_id)
        assert call is not None
        assert call.turn_count == 1
        assert call.last_turn_id.endswith(":1")
        assert call.phase == VoiceTurnPhase.UPLOADED

        call = await store.mark_phase(
            call.call_id,
            VoiceTurnPhase.TRANSCRIBING,
        )
        assert call is not None
        assert call.phase == VoiceTurnPhase.TRANSCRIBING

        call = await store.mark_transcript(
            call.call_id,
            "你好",
        )
        assert call is not None
        assert call.last_transcript == "你好"
        assert call.phase == VoiceTurnPhase.THINKING

        call = await store.mark_output(
            call.call_id,
            output_id="out-1",
            audio_path="data/audio/out.wav",
            audio_url="/audio/out.wav",
        )
        assert call is not None
        assert call.last_output_id == "out-1"
        assert call.phase == VoiceTurnPhase.SPEAKING

    asyncio.run(run())


def test_voice_call_store_save_persists_metadata():
    async def run():
        store = _store()
        call = await store.start(
            user_id="u1",
            username="tester",
        )

        call.update_metadata(unit_value="saved")
        await store.save(call)

        loaded = await store.get(
            call.call_id,
            touch=False,
        )

        assert loaded is not None
        assert loaded.metadata["unit_value"] == "saved"

    asyncio.run(run())


def test_voice_call_store_returns_deep_copy():
    async def run():
        store = _store()
        call = await store.start(
            user_id="u1",
            username="tester",
        )

        loaded = await store.get(
            call.call_id,
            touch=False,
        )
        assert loaded is not None

        loaded.metadata["local_only"] = True

        reloaded = await store.get(
            call.call_id,
            touch=False,
        )
        assert reloaded is not None
        assert "local_only" not in reloaded.metadata

    asyncio.run(run())


def test_voice_call_store_empty_turn():
    async def run():
        store = _store()
        call = await store.start(
            user_id="u1",
            username="tester",
        )

        await store.next_turn(call.call_id)
        call = await store.mark_transcript(
            call.call_id,
            "",
        )

        assert call is not None
        assert call.phase == VoiceTurnPhase.EMPTY_TURN
        assert call.metadata["voice_asr_empty"] is True

    asyncio.run(run())


def test_voice_call_store_interrupt():
    async def run():
        store = _store()
        call = await store.start(
            user_id="u1",
            username="tester",
        )

        call = await store.interrupt(
            call.call_id,
            "unit_interrupt",
        )

        assert call is not None
        assert call.phase == VoiceTurnPhase.INTERRUPTED
        assert call.interrupt_count == 1
        assert call.last_interrupt_reason == "unit_interrupt"

    asyncio.run(run())


def test_voice_call_store_end_is_idempotent_and_queryable():
    async def run():
        store = _store()
        call = await store.start(
            user_id="u1",
            username="tester",
        )

        first = await store.end(call.call_id)
        second = await store.end(call.call_id)
        loaded = await store.get(
            call.call_id,
            touch=False,
        )

        assert first is not None
        assert second is not None
        assert loaded is not None
        assert first.status == VoiceCallStatus.ENDED
        assert second.status == VoiceCallStatus.ENDED
        assert loaded.status == VoiceCallStatus.ENDED
        assert loaded.phase == VoiceTurnPhase.COMPLETED
        assert loaded.ended_at

    asyncio.run(run())


def test_voice_call_store_end_missing_returns_none():
    async def run():
        store = _store()

        call = await store.end("missing-call")

        assert call is None

    asyncio.run(run())


def test_voice_call_store_fail_marks_error_state():
    async def run():
        store = _store()
        call = await store.start(
            user_id="u1",
            username="tester",
        )

        call = await store.fail(
            call.call_id,
            RuntimeError("boom"),
        )

        assert call is not None
        assert call.status == VoiceCallStatus.ERROR
        assert call.phase == VoiceTurnPhase.FAILED
        assert call.last_error == "boom"

    asyncio.run(run())


def test_voice_call_store_memory_backend_status():
    async def run():
        store = _store()

        status = await store.backend_status()

        assert status["ok"] is True
        assert status["configured_provider"] == "memory"
        assert status["effective_provider"] == "memory"

    asyncio.run(run())