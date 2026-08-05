# tests/api/test_memory_control_contract.py
from __future__ import annotations

from tests.helpers.api_contract import (
    assert_error_response,
    assert_json_response,
    assert_ok_response,
)


def test_memory_snapshot_contract(api_client, test_user):
    response = api_client.get(f"/memory/user/{test_user['user_id']}/snapshot")
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "snapshot" in data

    snapshot = data["snapshot"]
    assert snapshot["user_id"] == test_user["user_id"]
    assert "total" in snapshot
    assert "layers" in snapshot
    assert isinstance(snapshot["layers"], list)


def test_memory_layer_contract(api_client, test_user):
    response = api_client.get(f"/memory/user/{test_user['user_id']}/layers/preference")
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "result" in data

    result = data["result"]
    assert result["user_id"] == test_user["user_id"]
    assert result["layer"] == "preference"
    assert "count" in result
    assert "memories" in result
    assert isinstance(result["memories"], list)


def test_memory_search_accepts_layer_filter(api_client, test_user):
    response = api_client.get(
        f"/memory/user/{test_user['user_id']}/search",
        params={
            "query": "喜欢什么",
            "limit": 5,
            "layer": "preference",
        },
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "result" in data
    assert data["result"]["query"] == "喜欢什么"
    assert data["result"]["memory_layer"] == "preference"


def test_memory_delete_layer_contract(api_client, test_user):
    response = api_client.delete(f"/memory/user/{test_user['user_id']}/layers/preference")
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "result" in data

    result = data["result"]
    assert result["layer"] == "preference"
    assert "deleted_count" in result
    assert "deleted_ids" in result


def test_memory_delete_missing_item_contract(api_client, test_user):
    response = api_client.delete(
        f"/memory/user/{test_user['user_id']}/memories/missing-memory-id"
    )
    data = assert_json_response(response, expected_status=404)

    assert_error_response(data, stage="memory_delete")
    assert data["user_id"] == test_user["user_id"]
    assert data["memory_id"] == "missing-memory-id"

def test_memory_preferences_contract(api_client, test_user):
    response = api_client.get(f"/memory/user/{test_user['user_id']}/preferences")
    data = assert_json_response(response)

    assert_ok_response(data)
    assert "preferences" in data

    preferences = data["preferences"]
    assert preferences["user_id"] == test_user["user_id"]
    assert "long_term_enabled" in preferences


def test_memory_preferences_update_contract(api_client, test_user):
    response = api_client.put(
        f"/memory/user/{test_user['user_id']}/preferences",
        json={
            "long_term_enabled": False,
            "reason": "contract_test_disable",
        },
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert data["preferences"]["long_term_enabled"] is False


def test_memory_edit_missing_item_contract(api_client, test_user):
    response = api_client.patch(
        f"/memory/user/{test_user['user_id']}/memories/missing-memory-id",
        json={
            "memory": "用户喜欢清淡口味。",
            "category": "preference",
            "importance": "medium",
        },
    )
    data = assert_json_response(response, expected_status=404)

    assert_error_response(data, stage="memory_edit")
    assert data["memory_id"] == "missing-memory-id"


def test_memory_pin_missing_item_contract(api_client, test_user):
    response = api_client.post(
        f"/memory/user/{test_user['user_id']}/memories/missing-memory-id/pin",
        json={"pinned": True, "reason": "contract_test_pin"},
    )
    data = assert_json_response(response, expected_status=404)

    assert_error_response(data, stage="memory_pin")
    assert data["memory_id"] == "missing-memory-id"


def test_memory_merge_requires_multiple_ids_contract(api_client, test_user):
    response = api_client.post(
        f"/memory/user/{test_user['user_id']}/merge",
        json={
            "memory_ids": ["only-one"],
            "merged_memory": "用户喜欢清淡口味。",
            "reason": "contract_test_merge",
        },
    )
    data = assert_json_response(response, expected_status=400)

    assert_error_response(data, stage="memory_merge")