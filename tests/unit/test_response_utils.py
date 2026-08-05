import json

from apps.api.request_context import clear_request_context, set_request_context
from apps.api.response_utils import error_message_response, ok_response


def _json_body(response):
    return json.loads(response.body.decode("utf-8"))


def test_ok_response_injects_request_id():
    set_request_context(
        request_id="unit-request-001",
        method="GET",
        path="/unit",
    )

    try:
        response = ok_response(message="你好")
        body = _json_body(response)

        assert response.status_code == 200
        assert body["ok"] is True
        assert body["message"] == "你好"
        assert body["request_id"] == "unit-request-001"

    finally:
        clear_request_context()


def test_error_message_response_shape():
    set_request_context(
        request_id="unit-request-002",
        method="POST",
        path="/unit/error",
    )

    try:
        response = error_message_response(
            stage="unit_stage",
            error="单元测试错误",
            status_code=404,
            extra={
                "resource_id": "missing",
            },
        )
        body = _json_body(response)

        assert response.status_code == 404
        assert body["ok"] is False
        assert body["stage"] == "unit_stage"
        assert body["error"] == "单元测试错误"
        assert body["resource_id"] == "missing"
        assert body["request_id"] == "unit-request-002"

    finally:
        clear_request_context()