import json

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from apps.api.shared_state_errors import shared_state_error_response
from apps.core.runtime_registry import get_runtime

router = APIRouter()


def _get_runtime_or_error():
    try:
        return get_runtime()
    except Exception as exc:
        shared_error = shared_state_error_response(exc)
        if shared_error is not None:
            return shared_error
        raise


def _is_error_response(value: object) -> bool:
    return isinstance(value, JSONResponse)


class ControlInputRequest(BaseModel):
    source: str = "chat"
    user_id: str = "guest"
    username: str = "guest"
    text: str
    priority: str = "normal"
    room_id: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)


class PauseRequest(BaseModel):
    paused: bool = True


class InterruptRequest(BaseModel):
    reason: str = "control_interrupt"


@router.post("/control/input")
def control_input(req: ControlInputRequest):
    runtime = _get_runtime_or_error()
    if _is_error_response(runtime):
        return runtime

    payload = {
        "user_id": req.user_id,
        "username": req.username,
        "text": req.text,
        "priority": req.priority,
        "room_id": req.room_id,
        "metadata": req.metadata,
    }

    try:
        output = runtime.handle_source_payload(
            source=req.source,
            payload=payload,
        )
    except Exception as exc:
        shared_error = shared_state_error_response(exc)
        if shared_error is not None:
            return shared_error
        raise

    body = json.dumps(
        {
            "ok": True,
            "source": req.source,
            "reply": output.packet.reply_text,
            "base_reply_text": output.packet.base_reply_text,
            "emotion": output.packet.emotion,
            "motion": output.packet.motion,
            "expression": output.packet.expression,
            "metadata": output.packet.metadata,
        },
        ensure_ascii=False,
    )

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
    )


@router.get("/control/status")
def control_status():
    runtime = _get_runtime_or_error()
    if _is_error_response(runtime):
        return runtime

    body = json.dumps(
        {
            "ok": True,
            "snapshot": runtime.get_control_snapshot(),
        },
        ensure_ascii=False,
    )

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
    )


@router.post("/control/pause")
def pause_control(req: PauseRequest):
    runtime = _get_runtime_or_error()
    if _is_error_response(runtime):
        return runtime
    result = runtime.pause_dialogue() if req.paused else runtime.resume_dialogue()

    body = json.dumps(
        {
            "ok": True,
            "result": result,
            "snapshot": runtime.get_control_snapshot(),
        },
        ensure_ascii=False,
    )

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
    )


@router.post("/control/resume")
def resume_control():
    runtime = _get_runtime_or_error()
    if _is_error_response(runtime):
        return runtime
    result = runtime.resume_dialogue()

    body = json.dumps(
        {
            "ok": True,
            "result": result,
            "snapshot": runtime.get_control_snapshot(),
        },
        ensure_ascii=False,
    )

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
    )


@router.post("/control/reset-context")
def reset_context():
    runtime = _get_runtime_or_error()
    if _is_error_response(runtime):
        return runtime
    try:
        result = runtime.reset_dialogue_context()
    except Exception as exc:
        shared_error = shared_state_error_response(exc)
        if shared_error is not None:
            return shared_error
        raise

    body = json.dumps(
        {
            "ok": True,
            "result": result,
            "snapshot": runtime.get_control_snapshot(),
        },
        ensure_ascii=False,
    )

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
    )


@router.post("/control/interrupt")
def interrupt_control(req: InterruptRequest):
    runtime = _get_runtime_or_error()
    if _is_error_response(runtime):
        return runtime
    result = runtime.interrupt_speaking(reason=req.reason)

    body = json.dumps(
        {
            "ok": True,
            "result": result,
            "snapshot": runtime.get_control_snapshot(),
        },
        ensure_ascii=False,
    )

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
    )
