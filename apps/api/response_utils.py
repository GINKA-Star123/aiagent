from __future__ import annotations

import json
import traceback
from typing import Any

from fastapi import Response

from apps.api.request_context import get_request_id


def json_response(body: dict[str, Any], status_code: int = 200) -> Response:
    payload = dict(body)

    request_id = get_request_id()
    if request_id and "request_id" not in payload:
        payload["request_id"] = request_id

    return Response(
        content=json.dumps(payload, ensure_ascii=False, default=str),
        media_type="application/json; charset=utf-8",
        status_code=status_code,
    )


def ok_response(
    *,
    status_code: int = 200,
    **body: Any,
) -> Response:
    payload = {
        "ok": True,
        **body,
    }
    return json_response(payload, status_code=status_code)


def error_response(
    *,
    stage: str,
    exc: Exception,
    status_code: int = 500,
    runtime_error: str | None = None,
    include_traceback: bool = True,
    extra: dict[str, Any] | None = None,
) -> Response:
    payload: dict[str, Any] = {
        "ok": False,
        "stage": stage,
        "error": str(exc),
    }

    if runtime_error:
        payload["runtime_error"] = runtime_error

    if include_traceback:
        payload["traceback"] = traceback.format_exc()

    if extra:
        payload.update(extra)

    return json_response(payload, status_code=status_code)
