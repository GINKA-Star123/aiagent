import json
import logging
import traceback
from pathlib import Path

from fastapi import APIRouter, File, Response, UploadFile
from pydantic import BaseModel

from apps.core.runtime_registry import get_runtime, get_runtime_error

router = APIRouter()
logger = logging.getLogger("aiagent.api.voice")


class VoiceTurnRequest(BaseModel):
    user_id: str = "mic"
    username: str = "麦克风输入"
    max_seconds: float = 8.0
    silence_seconds: float = 1.2
    interrupt_playback: bool = True


class InterruptRequest(BaseModel):
    reason: str = "api_interrupt"


def _runtime_or_error(route_name: str):
    try:
        return get_runtime(), None
    except Exception as exc:
        logger.exception("Runtime init failed in %s: %s", route_name, exc)
        body = json.dumps(
            {
                "ok": False,
                "stage": "runtime_init",
                "route": route_name,
                "error": str(exc),
                "runtime_error": get_runtime_error(),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )
        return None, Response(
            content=body,
            media_type="application/json; charset=utf-8",
            status_code=500,
        )


@router.post("/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    runtime, error_response = _runtime_or_error("/voice/transcribe")
    if error_response is not None:
        return error_response

    try:
        upload_dir = Path("data/cache/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "upload.wav").suffix or ".wav"
        file_path = upload_dir / f"upload_asr{suffix}"

        content = await file.read()
        file_path.write_bytes(content)

        transcript = runtime.transcribe_audio_file(str(file_path))

        body = json.dumps(
            {
                "ok": True,
                "transcript": transcript,
                "file_path": str(file_path),
            },
            ensure_ascii=False,
        )

        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
        )
    except Exception as exc:
        logger.exception("/voice/transcribe failed: %s", exc)
        body = json.dumps(
            {
                "ok": False,
                "stage": "voice_transcribe",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            status_code=500,
        )


@router.post("/voice/turn")
def voice_turn(req: VoiceTurnRequest):
    runtime, error_response = _runtime_or_error("/voice/turn")
    if error_response is not None:
        return error_response

    try:
        output = runtime.handle_voice_turn(
            user_id=req.user_id,
            username=req.username,
            max_seconds=req.max_seconds,
            silence_seconds=req.silence_seconds,
            interrupt_playback=req.interrupt_playback,
        )

        body = json.dumps(
            {
                "ok": True,
                "reply": output.packet.reply_text,
                "base_reply_text": output.packet.base_reply_text,
                "emotion": output.packet.emotion,
                "motion": output.packet.motion,
                "expression": output.packet.expression,
                "audio_path": output.packet.audio_path,
                "live2d_command_path": output.packet.live2d_command_path,
                "metadata": output.packet.metadata,
                "stream_state": runtime.get_stream_state().model_dump(),
                "speaking_state": runtime.get_speaking_state().model_dump(),
            },
            ensure_ascii=False,
        )

        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
        )
    except Exception as exc:
        logger.exception("/voice/turn failed: %s", exc)
        body = json.dumps(
            {
                "ok": False,
                "stage": "voice_turn",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            status_code=500,
        )


@router.post("/voice/interrupt")
def interrupt_voice(req: InterruptRequest):
    runtime, error_response = _runtime_or_error("/voice/interrupt")
    if error_response is not None:
        return error_response

    try:
        result = runtime.interrupt_speaking(reason=req.reason)
        body = json.dumps(
            {
                "ok": True,
                "result": result,
                "speaking_state": runtime.get_speaking_state().model_dump(),
            },
            ensure_ascii=False,
        )
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
        )
    except Exception as exc:
        logger.exception("/voice/interrupt failed: %s", exc)
        body = json.dumps(
            {
                "ok": False,
                "stage": "voice_interrupt",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            status_code=500,
        )


@router.get("/voice/state")
def voice_state():
    runtime, error_response = _runtime_or_error("/voice/state")
    if error_response is not None:
        return error_response

    try:
        body = json.dumps(
            {
                "ok": True,
                "stream_state": runtime.get_stream_state().model_dump(),
                "speaking_state": runtime.get_speaking_state().model_dump(),
            },
            ensure_ascii=False,
        )
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
        )
    except Exception as exc:
        logger.exception("/voice/state failed: %s", exc)
        body = json.dumps(
            {
                "ok": False,
                "stage": "voice_state",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            ensure_ascii=False,
        )
        return Response(
            content=body,
            media_type="application/json; charset=utf-8",
            status_code=500,
        )
