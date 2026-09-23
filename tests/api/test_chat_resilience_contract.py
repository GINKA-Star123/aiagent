"""主链路韧性契约：RAG 降级 + 会话/回合回显。"""

from __future__ import annotations

from aiagent.graphs.main_graph import RAGRunner
from tests.helpers.api_contract import assert_chat_response_contract, assert_json_response


def _chat(api_client, test_user, **extra):
    payload = {
        "user_id": test_user["user_id"],
        "username": test_user["username"],
        "text": "你好",
    }
    payload.update(extra)
    return api_client.post("/chat", json=payload)


def test_chat_degrades_when_rag_unavailable(api_client, test_user, monkeypatch):
    def _boom(self, *args, **kwargs):
        raise RuntimeError("rag unavailable (contract test)")

    monkeypatch.setattr(RAGRunner, "run", _boom)

    data = assert_json_response(_chat(api_client, test_user))

    assert_chat_response_contract(data)
    assert data["reply"]
    assert data["metadata"]["rag_graph_status"] == "failed"
    assert data["metadata"]["rag_error"]


def test_chat_echoes_explicit_session_id(api_client, test_user):
    data = assert_json_response(_chat(api_client, test_user, session_id="s-contract-1"))
    metadata = data["metadata"]

    assert metadata["session_id"] == "s-contract-1"
    assert metadata["turn_id"].startswith("s-contract-1:")


def test_chat_falls_back_to_default_session_id(api_client, test_user):
    data = assert_json_response(_chat(api_client, test_user))

    assert data["metadata"]["session_id"] == f"chat:{test_user['user_id']}"


def test_chat_turn_id_is_unique_per_request(api_client, test_user):
    first = assert_json_response(_chat(api_client, test_user, session_id="s-turn"))
    second = assert_json_response(_chat(api_client, test_user, session_id="s-turn"))

    assert first["metadata"]["turn_id"] != second["metadata"]["turn_id"]
    assert first["metadata"]["turn_id"].startswith("s-turn:")
    assert second["metadata"]["turn_id"].startswith("s-turn:")