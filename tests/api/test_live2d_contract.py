from __future__ import annotations

from tests.helpers.api_contract import (
    assert_json_response,
    assert_live2d_payload_contract,
    assert_ok_response,
)


def test_live2d_stats_contract(api_client):
    response = api_client.get("/live2d/stats")
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "stats" in data
    assert isinstance(data["stats"], dict)


def test_live2d_preview_contract(api_client):
    response = api_client.post(
        "/live2d/preview",
        json={
            "character_id": "yzl",
            "emotion": "calm",
            "expression": "gentle",
            "motion": "soft_idle",
            "background_id": "room_default",
            "audio_url": "",
            "metadata": {
                "test": "contract",
            },
        },
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "payload" in data
    assert_live2d_payload_contract(data["payload"])
    payload = data["payload"]
    assert payload["version"] == "1.0"
    assert payload["metadata"]["test"] == "contract"
    assert payload["character"]["emotion"] == "calm"
    assert payload["character"]["motion_group"]
    assert "expression_file" in payload["character"]
    assert "motion_file" in payload["character"]
    assert "background_file" in payload["scene"]


def test_live2d_runtime_status_contract(api_client):
    response = api_client.get("/live2d/runtime/status")
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "runtime" in data
    assert isinstance(data["runtime"], dict)