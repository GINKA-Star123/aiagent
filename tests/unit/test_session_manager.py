"""session_id / turn_id 解析优先级单测（roadmap 5.3）。"""

from __future__ import annotations

from aiagent.orchestrator.session_manager import SessionManager
from aiagent.schemas.inputs import InputEvent, InputSource


def _event(**overrides):
    payload = {
        "source": InputSource.CHAT,
        "user_id": "u1",
        "text": "hi",
    }
    payload.update(overrides)
    return InputEvent(**payload)


def test_resolve_session_id_prefers_explicit_value():
    manager = SessionManager()

    assert manager.resolve_session_id(_event(session_id="s-explicit")) == "s-explicit"


def test_resolve_session_id_supports_legacy_metadata_channel():
    manager = SessionManager()

    event = _event(metadata={"session_id": "s-legacy"})

    assert manager.resolve_session_id(event) == "s-legacy"


def test_resolve_session_id_falls_back_to_source_and_user_id():
    manager = SessionManager()

    assert manager.resolve_session_id(_event()) == "chat:u1"


def test_resolve_session_id_ignores_blank_values():
    manager = SessionManager()

    event = _event(session_id="   ", metadata={"session_id": "   "})

    assert manager.resolve_session_id(event) == "chat:u1"


def test_resolve_turn_id_prefers_explicit_value():
    manager = SessionManager()

    event = _event(turn_id="call-1:3")

    assert manager.resolve_turn_id(event, session_id="call-1") == "call-1:3"


def test_resolve_turn_id_is_unique_and_prefixed_by_session():
    manager = SessionManager()

    first = manager.resolve_turn_id(_event(), session_id="s1")
    second = manager.resolve_turn_id(_event(), session_id="s1")

    assert first.startswith("s1:")
    assert second.startswith("s1:")
    assert first != second
    assert len(first.split(":")[-1]) == 8