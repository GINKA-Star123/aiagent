from __future__ import annotations

import json
import logging

from aiagent.common.logger import (
    RequestContextFilter,
    SafeJsonFormatter,
    SafeTextFormatter,
)
from apps.api.request_context import (
    get_request_id,
    reset_request_context,
    set_request_context,
)


def _record(
    message: str,
    *args,
    exc_info=None,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="aiagent.unit",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=args,
        exc_info=exc_info,
    )

    RequestContextFilter().filter(record)
    return record


def test_text_formatter_contains_request_context():
    tokens = set_request_context(
        request_id="unit-request-001",
        method="POST",
        path="/chat",
    )

    try:
        output = SafeTextFormatter().format(
            _record("request completed")
        )
    finally:
        reset_request_context(tokens)

    assert "request_id=unit-request-001" in output
    assert "method=POST" in output
    assert "path=/chat" in output
    assert "request completed" in output


def test_json_formatter_returns_structured_log():
    tokens = set_request_context(
        request_id="unit-request-002",
        method="GET",
        path="/health",
    )

    try:
        output = SafeJsonFormatter().format(
            _record("health checked")
        )
    finally:
        reset_request_context(tokens)

    data = json.loads(output)

    assert data["level"] == "INFO"
    assert data["logger"] == "aiagent.unit"
    assert data["message"] == "health checked"
    assert data["request_id"] == "unit-request-002"
    assert data["method"] == "GET"
    assert data["path"] == "/health"


def test_formatter_redacts_secret_in_message():
    output = SafeTextFormatter().format(
        _record(
            "request failed api_key=%s",
            "sk-unit-secret",
        )
    )

    assert "sk-unit-secret" not in output
    assert "[redacted]" in output


def test_formatter_redacts_secret_in_exception():
    try:
        raise RuntimeError(
            "provider failed token=unit-secret-token"
        )
    except RuntimeError:
        import sys

        exc_info = sys.exc_info()

    output = SafeTextFormatter().format(
        _record(
            "provider request failed",
            exc_info=exc_info,
        )
    )

    assert "unit-secret-token" not in output
    assert "[redacted]" in output


def test_request_context_reset_restores_previous_context():
    outer = set_request_context(
        request_id="outer-request",
        method="GET",
        path="/outer",
    )

    try:
        inner = set_request_context(
            request_id="inner-request",
            method="POST",
            path="/inner",
        )

        assert get_request_id() == "inner-request"

        reset_request_context(inner)

        assert get_request_id() == "outer-request"
    finally:
        reset_request_context(outer)