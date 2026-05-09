from __future__ import annotations

import json
import traceback

from fastapi import APIRouter, Response

from aiagent.diagnostics.runtime_diagnostics import RuntimeDiagnostics

router = APIRouter()


@router.get("/runtime/diagnostics")
def runtime_diagnostics() -> Response:
    try:
        report = RuntimeDiagnostics().run()
        return _json_response(report.model_dump())
    except Exception as exc:
        return _json_response(
            {
                "ok": False,
                "status": "failed",
                "stage": "runtime_diagnostics",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            status_code=500,
        )


def _json_response(body: dict, status_code: int = 200) -> Response:
    return Response(
        content=json.dumps(body, ensure_ascii=False, default=str),
        media_type="application/json; charset=utf-8",
        status_code=status_code,
    )
