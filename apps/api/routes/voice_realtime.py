from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel,Field

from aiagent.graphs.metadata_utils import now_perf
from aiagent.live2d.payload_contract import normalize_live2d_payload
from aiagent.perception.voice_call_store import VoiceRealtimeCallStore
from aiagent.perception.voice_realtime_observability import (
    attach_voice_live2d_status,
    attach_voice_model_latency,
    attach_voice_tts_status,
    mark_voice_stage_done,
    mark_voice_stage_failed,
    mark_voice_stage_skipped,
    merge_voice_metadata,
    voice_base_metadata,
    voice_response_payload,
)
from aiagent.perception.voice_state_machine import (
    can_interrupt,
    can_start_turn,
    normalize_interrupt_reason,
    state_conflict_extra,
)
from aiagent.schemas.outputs import ResponsePacket
from aiagent.schemas.voice import VoiceTurnPhase
from apps.api.shared_state_errors import shared_state_error_response
from apps.api.response_utils import (
    error_message_response,
    error_response,
    ok_response,
)
from apps.core.runtime_registry import get_runtime, get_runtime_error

from cloud.config import cloud_settings

router = APIRouter()
logger = logging.getLogger("aiagent.api.voice_realtime")

_CALL_STORE = VoiceRealtimeCallStore(
    prefix=cloud_settings.redis_prefix,
    provider=cloud_settings.voice_call_store_provider,
    ttl_seconds=cloud_settings.voice_call_ttl_seconds,
    ended_ttl_seconds=cloud_settings.voice_call_ended_ttl_seconds,
    lock_ttl_seconds=cloud_settings.voice_call_lock_ttl_seconds,
    lock_wait_seconds=cloud_settings.voice_call_lock_wait_seconds,
    fail_open=cloud_settings.voice_call_store_fail_open,
)

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
    started_at = now_perf()

    call = await _CALL_STORE.start(
        user_id=req.user_id,
        username=req.username,
    )

    metadata = mark_voice_stage_done(
        voice_base_metadata(call),
        "call_start",
        started_at,
        voice_call_started=True,
    )
    call.update_metadata(**metadata)
    await _CALL_STORE.save(call)

    payload = voice_response_payload(call)
    payload["turn_seconds"] = 2.8

    return ok_response(**payload)


@router.post("/voice/realtime/end")
async def voice_realtime_end(req: VoiceRealtimeEndRequest):
    started_at = now_perf()

    call = await _CALL_STORE.end(req.call_id)
    if call is None:
        return _call_not_found_response(
            "voice_realtime_end",
            req.call_id,
        )

    metadata = mark_voice_stage_done(
        dict(call.metadata),
        "call_end",
        started_at,
        voice_call_ended=True,
    )
    call.update_metadata(**metadata)
    await _CALL_STORE.save(call)

    payload = voice_response_payload(call)
    payload["metadata"] = dict(call.metadata)

    return ok_response(**payload)


@router.get("/voice/realtime/state/{call_id}")
async def voice_realtime_state(call_id: str):
    call = await _CALL_STORE.get(call_id)
    if call is None:
        return _call_not_found_response("voice_realtime_state", call_id)

    return ok_response(**voice_response_payload(call))


@router.post("/voice/realtime/turn")
async def voice_realtime_turn(
    call_id: str = Form(...),
    user_id: str = Form(default="guest"),
    username: str = Form(default="guest"),
    file: UploadFile = File(...),
):
    existing_call = await _CALL_STORE.get(call_id)
    if existing_call is None:
        return _call_not_found_response("voice_realtime_turn", call_id)

    turn_decision = can_start_turn(existing_call)

    if not turn_decision.allowed:
        # 已结束的通话对 turn 接口等价于"不存在"：返回 404，
        # 与 GET /state 仍可查询已结束通话（200）区分开；
        # 其余不可开始新 turn 的阶段统一返回 409 状态冲突。
        if turn_decision.reason == "call_ended":
            return _call_not_found_response("voice_realtime_turn", call_id)

        return error_message_response(
            stage="voice_realtime_state_conflict",
            error=turn_decision.message,
            status_code=409,
            extra={
                "call_id": call_id,
                **state_conflict_extra(turn_decision)
            },
        )
    call = await _CALL_STORE.next_turn(call_id)
    if call is None:
        return _call_not_found_response("voice_realtime_turn", call_id)

    turn_started_at = now_perf()
    metadata = dict(call.metadata)

    call = await _CALL_STORE.mark_phase(
        call_id,
        VoiceTurnPhase.LISTENING,
        **metadata,
    ) or call

    metadata = dict(call.metadata)

    try:
        runtime = get_runtime()

        upload_started_at = now_perf()
        upload_dir = Path("data/cache/voice_realtime")
        upload_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "turn.m4a").suffix or ".m4a"
        file_path = upload_dir / f"{call_id}_{call.turn_count}{suffix}"

        content = await file.read()
        if not content:
            failed_metadata = mark_voice_stage_failed(
                metadata,
                "upload",
                upload_started_at,
                "audio file is empty",
            )
            call = await _CALL_STORE.mark_phase(
                call_id,
                VoiceTurnPhase.FAILED,
                **failed_metadata
            ) or call

            return error_message_response(
                stage="voice_upload_validation",
                error="audio file is empty",
                status_code=400,
                extra={
                    "call_id": call_id,
                    "turn_id": call.last_turn_id,
                    "metadata": dict(call.metadata),
                },
            )

        max_voice_upload_bytes = 25 * 1024 * 1024
        if len(content) > max_voice_upload_bytes:
            failed_metadata = mark_voice_stage_failed(
                metadata,
                "upload",
                upload_started_at,
                "voice upload is too large",
                voice_upload_bytes=len(content),
            )
            call = await _CALL_STORE.mark_phase(
                call_id,
                VoiceTurnPhase.FAILED,
                **failed_metadata,
            ) or call

            return error_message_response(
                stage="voice_upload_size_limit",
                error="voice upload is too large",
                status_code=413,
                extra={
                    "call_id": call_id,
                    "turn_id": call.last_turn_id,
                    "max_bytes": max_voice_upload_bytes,
                    "actual_bytes": len(content),
                    "metadata": dict(call.metadata),
                },
            )
        await asyncio.to_thread(file_path.write_bytes, content)

        metadata = mark_voice_stage_done(
            metadata,
            "upload",
            upload_started_at,
            voice_upload_filename=file.filename or "",
            voice_upload_path=str(file_path),
            voice_upload_bytes=len(content),
        )
        call = await _CALL_STORE.mark_phase(
            call_id,
            VoiceTurnPhase.TRANSCRIBING,
            **metadata,
        ) or call
        metadata = dict(call.metadata)

        asr_started_at = now_perf()
        transcript = await asyncio.to_thread(
            runtime.transcribe_audio_file,
            str(file_path),
        )
        transcript = (transcript or "").strip()

        metadata = mark_voice_stage_done(
            metadata,
            "asr",
            asr_started_at,
            voice_asr_text_chars=len(transcript),
            voice_asr_empty=not bool(transcript),
        )
        call = await _CALL_STORE.mark_transcript(
            call_id,
            transcript,
            **metadata,
        ) or call
        metadata = dict(call.metadata)

        if not transcript:
            metadata = mark_voice_stage_skipped(
                metadata,
                "chat",
                "empty_transcript",
            )
            metadata = mark_voice_stage_skipped(
                metadata,
                "tts",
                "empty_transcript",
            )
            metadata = mark_voice_stage_done(
                metadata,
                "turn",
                turn_started_at,
                voice_turn_empty=True,
            )
            call.update_metadata(**metadata)
            await _CALL_STORE.save(call)

            payload = voice_response_payload(call)
            payload.update(_empty_chat_fields())
            payload.update(
                {
                    "transcript": "",
                    "session_id": call_id,
                    "metadata": dict(call.metadata),
                }
            )
            return ok_response(**payload)

        chat_started_at = now_perf()
        output = await asyncio.to_thread(
            runtime.handle_chat_full,
            text=transcript,
            user_id=user_id,
            username=username,
            session_id=call_id,
            turn_id=call.last_turn_id,
        )

        packet = output.packet
        packet_metadata = dict(packet.metadata or {})

        metadata = merge_voice_metadata(packet_metadata, metadata)
        metadata = mark_voice_stage_done(
            metadata,
            "chat",
            chat_started_at,
            voice_output_id=output.output_id,
        )
        metadata = attach_voice_tts_status(metadata, packet=packet)
        metadata = attach_voice_tts_status(metadata, packet=packet)
        metadata = attach_voice_model_latency(metadata, packet=packet)
        metadata = attach_voice_live2d_status(metadata, packet=packet)

        live2d = packet.live2d or _build_live2d_payload(packet)

        call = await _CALL_STORE.mark_output(
            call_id,
            output_id=output.output_id,
            audio_path=packet.audio_path or "",
            audio_url=packet.audio_url or "",
            has_audio=bool(
                packet.audio_path
                or packet.audio_url
                or packet.audio_segments
                or packet.audio_segment_urls
            ),
            **metadata,
        ) or call

        metadata = dict(call.metadata)
        metadata = mark_voice_stage_done(
            metadata,
            "turn",
            turn_started_at,
            voice_turn_empty=False,
        )
        call.update_metadata(**metadata)
        await _CALL_STORE.save(call)

        payload = voice_response_payload(call)
        payload.update(
            {
                "transcript": transcript,
                "output_id": output.output_id,
                "reply": packet.reply_text or "",
                "base_reply_text": packet.base_reply_text or packet.reply_text or "",
                "emotion": str(packet.emotion or "neutral"),
                "motion": packet.motion or "idle",
                "expression": packet.expression or "neutral",
                "audio_path": packet.audio_path or "",
                "audio_url": packet.audio_url or "",
                "audio_segments": packet.audio_segments or [],
                "audio_segment_urls": packet.audio_segment_urls or [],
                "audio_segment_texts": packet.audio_segment_texts or [],
                "live2d_command_path": packet.live2d_command_path or "",
                "live2d": live2d,
                "session_id": call_id,
                "metadata": dict(call.metadata),
            }
        )

        return ok_response(**payload)

    except Exception as exc:
        shared_error = shared_state_error_response(exc)
        if shared_error is not None:
            return shared_error

        failed_metadata = mark_voice_stage_failed(
            metadata,
            "turn",
            turn_started_at,
            exc,
        )
        call = await _CALL_STORE.fail(call_id, exc, **failed_metadata) or call
        failed_metadata = dict(call.metadata)

        logger.exception("/voice/realtime/turn failed: %s", exc)
        return error_response(
            stage="voice_realtime_turn",
            exc=exc,
            status_code=500,
            runtime_error=get_runtime_error(),
            extra={
                "call_id": call_id,
                "metadata": failed_metadata,
                "call": call.model_dump(mode="json"),
            },
        )


@router.post("/voice/realtime/interrupt")
async def voice_realtime_interrupt(req: VoiceRealtimeInterruptRequest):
    started_at = now_perf()

    existing_call = await _CALL_STORE.get(req.call_id)

    if existing_call is None:
        return _call_not_found_response(
            "voice_realtime_interrupt",
            req.call_id,
        )

    interrupt_reason = normalize_interrupt_reason(req.reason)
    interrupt_decision = can_interrupt(existing_call)

    if not interrupt_decision.allowed:
        return error_message_response(
            stage="voice_realtime_state_conflict",
            error=interrupt_decision.message,
            status_code=409,
            extra={
                "call_id": req.call_id,
                **state_conflict_extra(interrupt_decision),
            },
        )

    call = await _CALL_STORE.interrupt(
        req.call_id,
        interrupt_reason,
    )

    if call is None:
        return _call_not_found_response(
            "voice_realtime_interrupt",
            req.call_id,
        )

    try:
        runtime = get_runtime()
        result = await asyncio.to_thread(
            runtime.interrupt_speaking,
            interrupt_reason,
        )
    except Exception as exc:
        shared_error = shared_state_error_response(exc)
        if shared_error is not None:
            return shared_error

        failed_metadata = mark_voice_stage_failed(
            dict(call.metadata),
            "interrupt",
            started_at,
            exc,
            voice_interrupt_reason=interrupt_reason,
        )
        call = await _CALL_STORE.fail(req.call_id, exc, **failed_metadata) or call
        failed_metadata = dict(call.metadata)

        logger.exception("/voice/realtime/interrupt failed: %s", exc)
        return error_response(
            stage="voice_realtime_interrupt",
            exc=exc,
            status_code=500,
            runtime_error=get_runtime_error(),
            extra={
                "call_id": req.call_id,
                "metadata": failed_metadata,
                "call": call.model_dump(mode="json"),
            },
        )

    metadata = mark_voice_stage_done(
        dict(call.metadata),
        "interrupt",
        started_at,
        voice_interrupt_reason=interrupt_reason,
    )
    call.update_metadata(**metadata)
    await _CALL_STORE.save(call)

    payload = voice_response_payload(call)
    payload.update(
        {
            "result": result,
            "metadata": dict(call.metadata),
        }
    )

    return ok_response(**payload)


def _call_not_found_response(stage: str, call_id: str):
    return error_message_response(
        stage=stage,
        error="call not found or expired",
        status_code=404,
        extra={
            "call_id": call_id,
        },
    )


def _empty_chat_fields() -> dict[str, Any]:
    return {
        "output_id": "",
        "reply": "",
        "base_reply_text": "",
        "emotion": "neutral",
        "motion": "idle",
        "expression": "neutral",
        "audio_path": "",
        "audio_url": "",
        "audio_segments": [],
        "audio_segment_urls": [],
        "audio_segment_texts": [],
        "live2d_command_path": "",
        "live2d": _empty_live2d_payload(),
    }


def _empty_live2d_payload() -> dict[str, Any]:
    return normalize_live2d_payload(
        {},
        emotion="neutral",
        expression="neutral",
        motion="idle",
        audio_url="",
        background_id="room_default",
        metadata={
            "source": "voice_realtime_empty_turn",
        },
    )


def _build_live2d_payload(packet: ResponsePacket) -> dict[str, Any]:
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



