from __future__ import annotations

from fastapi import APIRouter

from aiagent.diagnostics.runtime_diagnostics import RuntimeDiagnostics
from apps.api.response_utils import error_response, json_response

router = APIRouter()


@router.get("/runtime/diagnostics")
def runtime_diagnostics():
    try:
        report = RuntimeDiagnostics().run()
        return json_response(report.model_dump())
    except Exception as exc:
        return error_response(
            stage="runtime_diagnostics",
            exc=exc,
            status_code=500,
        )
