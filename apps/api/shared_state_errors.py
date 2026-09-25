from __future__ import annotations

from starlette.responses import JSONResponse

from aiagent.state.shared_state import (
    SharedStateConflictError,
    SharedStateOwnershipError,
    SharedStateUnavailableError,
)


def shared_state_error_response(exc: Exception) -> JSONResponse | None:
    if isinstance(exc, SharedStateConflictError):
        return JSONResponse(
            status_code=409,
            content={
                "ok": False,
                "stage": exc.stage,
                "error": str(exc),
                "retryable": True,
            },
        )

    if isinstance(exc, SharedStateUnavailableError):
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "stage": exc.stage,
                "error": "共享执行状态暂时不可用",
                "retryable": True,
            },
        )

    if isinstance(exc, SharedStateOwnershipError):
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "stage": exc.stage,
                "error": "无权访问该会话状态",
                "retryable": False,
            },
        )

    return None
