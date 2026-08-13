from __future__ import annotations

from typing import Any

from aiagent.graphs.metadata_utils import elapsed_ms
from aiagent.schemas.outputs import ResponsePacket
from aiagent.schemas.voice import VoiceRealtimeCall


def _enum_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return "" if raw is None else str(raw)


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None

    raw = getattr(value, "value", None)
    if raw is not None:
        return raw

    return value


def merge_voice_metadata(*sources: dict[str, Any] | None, **extra: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    for source in sources:
        for key, value in dict(source or {}).items():
            normalized = _normalize_value(value)
            if normalized is None:
                continue
            metadata[str(key)] = normalized

    for key, value in extra.items():
        normalized = _normalize_value(value)
        if normalized is None:
            continue
        metadata[str(key)] = normalized

    return metadata


def voice_base_metadata(call: VoiceRealtimeCall) -> dict[str, Any]:
    return {
        "voice_realtime": True,
        "voice_realtime_call_id": call.call_id,
        "voice_realtime_turn_id": call.last_turn_id,
        "voice_realtime_turn_count": call.turn_count,
        "voice_realtime_status": _enum_value(call.status),
        "voice_realtime_phase": _enum_value(call.phase),
    }


def mark_voice_stage_done(
    metadata: dict[str, Any] | None,
    stage: str,
    started_at: float,
    **extra: Any,
) -> dict[str, Any]:
    return merge_voice_metadata(
        metadata,
        {
            f"voice_{stage}_status": "done",
            f"voice_{stage}_latency_ms": elapsed_ms(started_at),
        },
        **extra,
    )


def mark_voice_stage_skipped(
    metadata: dict[str, Any] | None,
    stage: str,
    reason: str,
    **extra: Any,
) -> dict[str, Any]:
    return merge_voice_metadata(
        metadata,
        {
            f"voice_{stage}_status": "skipped",
            f"voice_{stage}_skip_reason": reason,
        },
        **extra,
    )


def mark_voice_stage_failed(
    metadata: dict[str, Any] | None,
    stage: str,
    started_at: float,
    error: Exception | str,
    **extra: Any,
) -> dict[str, Any]:
    return merge_voice_metadata(
        metadata,
        {
            f"voice_{stage}_status": "failed",
            f"voice_{stage}_latency_ms": elapsed_ms(started_at),
            f"voice_{stage}_error": str(error),
        },
        **extra,
    )


def attach_voice_tts_status(
    metadata: dict[str, Any],
    *,
    packet: ResponsePacket,
) -> dict[str, Any]:
    packet_metadata = dict(packet.metadata or {})
    has_audio = bool(
        packet.audio_path
        or packet.audio_url
        or packet.audio_segments
        or packet.audio_segment_urls
    )

    tts_status = str(packet_metadata.get("tts_status", "") or "")
    update: dict[str, Any] = {}

    if tts_status == "failed":
        update["voice_tts_status"] = "failed"
        if packet_metadata.get("tts_error"):
            update["voice_tts_error"] = packet_metadata["tts_error"]
    elif tts_status == "skipped":
        update["voice_tts_status"] = "skipped"
        update["voice_tts_skip_reason"] = str(
            packet_metadata.get("tts_skip_reason") or "no_audio_output"
        )
    elif has_audio:
        update["voice_tts_status"] = "done"
    else:
        update["voice_tts_status"] = "skipped"
        update["voice_tts_skip_reason"] = "no_audio_output"

    for key in ("tts_latency_ms", "tts_graph_latency_ms"):
        if packet_metadata.get(key) is not None:
            update["voice_tts_latency_ms"] = packet_metadata[key]
            break

    return merge_voice_metadata(metadata, update)


def voice_response_payload(call: VoiceRealtimeCall) -> dict[str, Any]:
    return {
        "call_id": call.call_id,
        "status": _enum_value(call.status),
        "phase": _enum_value(call.phase),
        "turn_id": call.last_turn_id,
        "turn_count": call.turn_count,
        "last_seen_at": call.last_seen_at,
        "phase_changed_at": call.phase_changed_at,
        "metadata": dict(call.metadata),
        "call": call.model_dump(mode="json"),
    }