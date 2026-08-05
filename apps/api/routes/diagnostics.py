from __future__ import annotations

from fastapi import APIRouter

from aiagent.diagnostics.runtime_diagnostics import RuntimeDiagnostics
from apps.core.runtime_registry import get_runtime,get_runtime_error
from apps.api.response_utils import error_response, json_response,ok_response

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

@router.get("/runtime/capabilities")
def runtime_capabilities():
    try:
        runtime = get_runtime()
        return ok_response(
            capabilities=runtime.get_capability_snapshot(),
        )
    except Exception as exc:
        return error_response(
            stage="runtime_capabilities",
            exc=exc,
            status_code=500,
            runtime_error=get_runtime_error(),
        )