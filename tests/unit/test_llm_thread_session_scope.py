from __future__ import annotations

from aiagent.graphs.llm_graph import LLMRunner


class _StubSettings:
    enable_mock_llm = True
    llm_provider = "mock"


class _StubLLMService:
    settings = _StubSettings()


def test_clear_user_threads_only_touches_that_user(monkeypatch):
    runner = LLMRunner(llm_service=_StubLLMService())

    cleared: list[str] = []
    monkeypatch.setattr(runner, "clear_thread", lambda thread_id: cleared.append(thread_id))

    runner._thread_users.update(
        {
            "chat:u1:aaaa": "u1",
            "chat:u1:bbbb": "u1",
            "chat:u2:cccc": "u2",
        }
    )

    targets = runner.clear_user_threads("u1")

    assert sorted(targets) == ["chat:u1:aaaa", "chat:u1:bbbb"]
    assert sorted(cleared) == ["chat:u1:aaaa", "chat:u1:bbbb"]
    assert "chat:u2:cccc" in runner._thread_users


def test_clear_user_threads_returns_empty_for_unknown_user():
    runner = LLMRunner(llm_service=_StubLLMService())
    runner._thread_users.update({"chat:u1:aaaa": "u1"})

    assert runner.clear_user_threads("nobody") == []
    assert "chat:u1:aaaa" in runner._thread_users


def test_clear_all_threads_resets_ownership_map():
    runner = LLMRunner(llm_service=_StubLLMService())
    runner._thread_users.update({"chat:u1:aaaa": "u1"})

    runner.clear_all_threads()

    assert runner._thread_users == {}