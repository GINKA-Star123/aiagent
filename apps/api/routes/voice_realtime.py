from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from apps.api.response_utils import (
    error_message_response,
    error_response,
    ok_response,
)

from aiagent.live2d.payload_contract import normalize_live2d_payload
from aiagent.perception.voice_call_store import VoiceRealtimeCallStore
from aiagent.schemas.voice import VoiceTurnPhase
from apps.core.runtime_registry import get_runtime, get_runtime_error

router = APIRouter()
logger = logging.getLogger("aiagent.api.voice_realtime")

_CALL_STORE = VoiceRealtimeCallStore(ttl_seconds=1800.0)


class VoiceRealtimeInterruptRequest(BaseModel):
    call_id: str
    reason: str = "voice_realtime_interrupt"


class VoiceRealtimeStartRequest(BaseModel):
    user_id: str = "guest"
    username: str = "guest"


class VoiceRealtimeEndRequest(BaseModel):
    call_id: str


@router.post("/voice/realtime/start")
async def voice_realtime_start(req: VoiceRealtimeStartRequest):
    call = _CALL_STORE.start(
        user_id=req.user_id,
        username=req.username,
    )

    return ok_response(
        call_id=call.call_id,
        status=call.status,
        phase=call.phase,
        turn_seconds=2.8,
        call=call.model_dump(mode="json"),
    )


@router.post("/voice/realtime/end")
async def voice_realtime_end(req: VoiceRealtimeEndRequest):
    call = _CALL_STORE.end(req.call_id)

    return ok_response(
        call_id=call.call_id,
        status=call.status,
        phase=call.phase,
        call=call.model_dump(mode="json"),
    )


@router.get("/voice/realtime/state/{call_id}")
async def voice_realtime_state(call_id: str):
    call = _CALL_STORE.get(call_id)
    if call is None:
        return error_message_response(
            stage="voice_realtime_state",
            error="call not found",
            status_code=404,
            extra={
                "call_id": call_id,
            },
        )

    return ok_response(
        call=call.model_dump(mode="json"),
    )


@router.post("/voice/realtime/turn")
async def voice_realtime_turn(
    call_id: str = Form(...),
    user_id: str = Form(default="guest"),
    username: str = Form(default="guest"),
    file: UploadFile = File(...),
):
    call = _CALL_STORE.get(call_id)
    if call is None:
        return error_message_response(
            stage="voice_realtime_turn",
            error="call not found or expired",
            status_code=404,
            extra={
                "call_id": call_id,
            },
        )

    call = _CALL_STORE.next_turn(call_id)
    if call is None:
        return error_message_response(
            stage="voice_realtime_turn",
            error="call not found or expired",
            status_code=404,
            extra={
                "call_id": call_id,
            },
        )
    try:
        runtime = get_runtime()

        upload_dir = Path("data/cache/voice_realtime")
        upload_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "turn.m4a").suffix or ".m4a"
        file_path = upload_dir / f"{call_id}_{call.turn_count}{suffix}"

        content = await file.read()
        file_path.write_bytes(content)
        _CALL_STORE.mark_phase(
            call_id,
            VoiceTurnPhase.TRANSCRIBING,
            upload_path=str(file_path),
            upload_bytes=len(content),
        )

        transcript = await asyncio.to_thread(
            runtime.transcribe_audio_file,
            str(file_path),
        )

        transcript = transcript.strip()
        call = _CALL_STORE.mark_transcript(call_id, transcript) or call
        if not transcript:
            return ok_response(
                call_id=call_id,
                turn_count=call.turn_count,
                phase=call.phase,
                call=call.model_dump(mode="json"),
                transcript="",
                reply="",
                base_reply_text="",
                emotion="neutral",
                motion="idle",
                expression="neutral",
                audio_path="",
                audio_url="",
                audio_segments=[],
                audio_segment_urls=[],
                audio_segment_texts=[],
                live2d_command_path="",
                live2d=None,
                metadata={
                    "voice_realtime_empty_turn": True,
                    "voice_realtime_call_id": call_id,
                    "voice_realtime_turn_count": call.turn_count,
                    "voice_realtime_phase": call.phase,
                    "voice_realtime_turn_id": call.last_turn_id,
                },
            )
        _CALL_STORE.mark_phase(call_id, VoiceTurnPhase.THINKING)
        output = await asyncio.to_thread(
            runtime.handle_chat_full,
            text=transcript,
            user_id=user_id,
            username=username,
        )

        packet = output.packet
        live2d = packet.live2d or _build_live2d_payload(packet)
        call = _CALL_STORE.mark_output(
            call_id,
            output_id=output.output_id,
            audio_path=packet.audio_path,
            audio_url=packet.audio_url,
        ) or call

        return ok_response(
            call_id=call_id,
            turn_count=call.turn_count,
            phase=call.phase,
            call=call.model_dump(mode="json"),
            transcript=transcript,
            output_id=output.output_id,
            reply=packet.reply_text,
            base_reply_text=packet.base_reply_text,
            emotion=packet.emotion,
            motion=packet.motion,
            expression=packet.expression,
            audio_path=packet.audio_path,
            audio_url=packet.audio_url,
            audio_segments=packet.audio_segments,
            audio_segment_urls=packet.audio_segment_urls,
            audio_segment_texts=packet.audio_segment_texts,
            live2d_command_path=packet.live2d_command_path,
            live2d=live2d,
            metadata={
                **dict(packet.metadata),
                "voice_realtime": True,
                "voice_realtime_call_id": call_id,
                "voice_realtime_turn_count": call.turn_count,
                "voice_realtime_phase": call.phase,
                "voice_realtime_turn_id": call.last_turn_id,
            },
        )

    except Exception as exc:
        _CALL_STORE.fail(call_id, exc)
        logger.exception("/voice/realtime/turn failed: %s", exc)
        return error_response(
            stage="voice_realtime_turn",
            exc=exc,
            status_code=500,
            runtime_error=get_runtime_error(),
            extra={
                "call_id": call_id,
            },
        )


@router.post("/voice/realtime/interrupt")
async def voice_realtime_interrupt(req: VoiceRealtimeInterruptRequest):
    call = _CALL_STORE.interrupt(req.call_id, req.reason)
    if call is None:
        return error_message_response(
            stage="voice_realtime_interrupt",
            error="call not found or expired",
            status_code=404,
            extra={
                "call_id": req.call_id,
            },
        )

    try:
        runtime = get_runtime()
        result = await asyncio.to_thread(
            runtime.interrupt_speaking,
            req.reason,
        )
    except Exception as exc:
        _CALL_STORE.fail(req.call_id, exc)
        logger.exception("/voice/realtime/interrupt failed: %s", exc)
        return error_response(
            stage="voice_realtime_interrupt",
            exc=exc,
            status_code=500,
            runtime_error=get_runtime_error(),
            extra={
                "call_id": req.call_id,
            },
        )

    call = _CALL_STORE.get(req.call_id) or call

    return ok_response(
        call_id=req.call_id,
        status=call.status,
        phase=call.phase,
        result=result,
        call=call.model_dump(mode="json"),
    )


def _build_live2d_payload(packet) -> dict[str, Any]:
    return normalize_live2d_payload(
        {},
        emotion=str(packet.emotion or "neutral"),
        expression=packet.expression or "neutral",
        motion=packet.motion or "idle",
        audio_url=packet.audio_url or "",
        background_id="room_default",
        metadata={
            "source": "voice_realtime_fallback",
        },
    )