from __future__ import annotations

from tests.helpers.api_contract import (
    assert_json_response,
    assert_ok_response,
)


def test_session_open_contract(api_client, test_user):
    response = api_client.post(
        "/session/open",
        json={
            "user_id": test_user["user_id"],
            "username": test_user["username"],
            "entry": "chat_page",
            "recent_topic": "",
        },
    )
    data = assert_json_response(response)

    assert_ok_response(data)

    assert "opening" in data
    assert "presence" in data
    assert "live2d" in data
    assert "memory" in data

    opening = data["opening"]
    presence = data["presence"]
    live2d = data["live2d"]
    memory = data["memory"]

    assert isinstance(opening, dict)
    assert isinstance(presence, dict)
    assert isinstance(live2d, dict)
    assert isinstance(memory, dict)

    assert "kind" in opening
    assert "text" in opening
    assert "should_speak" in opening

    assert "state" in presence
    assert "mood" in presence
    assert "energy" in presence
    assert "fatigue" in presence
    assert "curiosity" in presence

    assert "expression" in live2d
    assert "motion" in live2d