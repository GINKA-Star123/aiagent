from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import BaseModel

from apps.core.runtime_registry import get_runtime

router = APIRouter()
logger = logging.getLogger("aiagent.api.voice_realtime")

_ACTIVE_CALLS: dict[str, dict[str, Any]] = {}


class VoiceRealtimeStartRequest(BaseModel):
    user_id: str = "guest"
    username: str = "guest"


class VoiceRealtimeEndRequest(BaseModel):
    call_id: str


@router.post("/voice/realtime/start")
async def voice_realtime_start(req: VoiceRealtimeStartRequest):
    call_id = uuid.uuid4().hex
    now = time.time()

    _ACTIVE_CALLS[call_id] = {
        "call_id": call_id,
        "user_id": req.user_id,
        "username": req.username,
        "started_at": now,
        "last_seen_at": now,
        "turn_count": 0,
        "status": "active",
    }

    return {
        "ok": True,
        "call_id": call_id,
        "status": "active",
        "turn_seconds": 2.8,
    }


@router.post("/voice/realtime/end")
async def voice_realtime_end(req: VoiceRealtimeEndRequest):
    call = _ACTIVE_CALLS.get(req.call_id)
    if call is not None:
        call["status"] = "ended"
        call["ended_at"] = time.time()
        _ACTIVE_CALLS.pop(req.call_id, None)

    return {
        "ok": True,
        "call_id": req.call_id,
        "status": "ended",
    }


@router.get("/voice/realtime/state/{call_id}")
async def voice_realtime_state(call_id: str):
    call = _ACTIVE_CALLS.get(call_id)
    if call is None:
        return {
            "ok": False,
            "stage": "voice_realtime_state",
            "error": "call not found",
            "call_id": call_id,
        }

    return {
        "ok": True,
        "call": call,
    }


@router.post("/voice/realtime/turn")
async def voice_realtime_turn(
    call_id: str = Form(...),
    user_id: str = Form(default="guest"),
    username: str = Form(default="guest"),
    file: UploadFile = File(...),
):
    call = _ACTIVE_CALLS.get(call_id)
    if call is None:
        return _json_response(
            {
                "ok": False,
                "stage": "voice_realtime_turn",
                "error": "call not found or expired",
                "call_id": call_id,
            },
            status_code=404,
        )

    call["last_seen_at"] = time.time()
    call["turn_count"] = int(call.get("turn_count", 0)) + 1

    try:
        runtime = get_runtime()

        upload_dir = Path("data/cache/voice_realtime")
        upload_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "turn.m4a").suffix or ".m4a"
        file_path = upload_dir / f"{call_id}_{call['turn_count']}{suffix}"

        content = await file.read()
        file_path.write_bytes(content)

        transcript = await asyncio.to_thread(
            runtime.transcribe_audio_file,
            str(file_path),
        )

        transcript = transcript.strip()
        if not transcript:
            return _json_response(
                {
                    "ok": True,
                    "call_id": call_id,
                    "transcript": "",
                    "reply": "",
                    "base_reply_text": "",
                    "emotion": "neutral",
                    "motion": "idle",
                    "expression": "neutral",
                    "audio_path": "",
                    "audio_url": "",
                    "live2d": None,
                    "metadata": {
                        "voice_realtime_empty_turn": True,
                    },
                }
            )

        output = await asyncio.to_thread(
            runtime.handle_chat_full,
            text=transcript,
            user_id=user_id,
            username=username,
        )

        packet = output.packet
        live2d = packet.live2d or _build_live2d_payload(packet)

        return _json_response(
            {
                "ok": True,
                "call_id": call_id,
                "turn_count": call["turn_count"],
                "transcript": transcript,
                "output_id": output.output_id,
                "reply": packet.reply_text,
                "base_reply_text": packet.base_reply_text,
                "emotion": packet.emotion,
                "motion": packet.motion,
                "expression": packet.expression,
                "audio_path": packet.audio_path,
                "audio_url": packet.audio_url,
                "audio_segments": packet.audio_segments,
                "audio_segment_urls": packet.audio_segment_urls,
                "audio_segment_texts": packet.audio_segment_texts,
                "live2d_command_path": packet.live2d_command_path,
                "live2d": live2d,
                "metadata": {
                    **dict(packet.metadata),
                    "voice_realtime": True,
                    "voice_realtime_call_id": call_id,
                    "voice_realtime_turn_count": call["turn_count"],
                },
            }
        )

    except Exception as exc:
        logger.exception("/voice/realtime/turn failed: %s", exc)
        return _json_response(
            {
                "ok": False,
                "stage": "voice_realtime_turn",
                "error": str(exc),
                "call_id": call_id,
            },
            status_code=500,
        )


def _build_live2d_payload(packet) -> dict[str, Any]:
    audio_url = packet.audio_url or ""

    return {
        "character": {
            "character_id": "yzl",
            "model_id": "yzl_v1",
            "emotion": str(packet.emotion),
            "expression": packet.expression or "neutral",
            "motion": packet.motion or "idle",
            "motion_priority": 1,
            "mouth": {
                "mode": "audio" if audio_url else "idle",
                "audio_url": audio_url,
            },
            "eye": {
                "blink": True,
                "look_at": "user",
            },
        },
        "scene": {
            "background_id": "room_default",
            "lighting": "normal",
            "effect": "none",
        },
    }


def _json_response(body: dict[str, Any], status_code: int = 200) -> Response:
    return Response(
        content=json.dumps(body, ensure_ascii=False, default=str),
        media_type="application/json; charset=utf-8",
        status_code=status_code,
    )