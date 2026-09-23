from __future__ import annotations

from apps.api.middleware import normalize_request_id


def test_normalize_request_id_accepts_valid_value():
    request_id = normalize_request_id(
        "client-request_001:test"
    )

    assert request_id == "client-request_001:test"


def test_normalize_request_id_rejects_newline():
    request_id = normalize_request_id(
        "valid\nforged-log-entry"
    )

    assert request_id != "valid\nforged-log-entry"
    assert "\n" not in request_id
    assert len(request_id) == 32


def test_normalize_request_id_rejects_overlong_value():
    request_id = normalize_request_id("x" * 129)

    assert request_id != "x" * 129
    assert len(request_id) == 32


def test_normalize_request_id_generates_value_when_missing():
    request_id = normalize_request_id(None)

    assert isinstance(request_id, str)
    assert len(request_id) == 32