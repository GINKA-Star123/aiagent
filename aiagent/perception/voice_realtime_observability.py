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
        "voice_realtime_session_id": call.call_id,
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
            update["voice_tts_latency_source"] = key
            break

    segment_count = packet_metadata.get("tts_segments")
    if segment_count is None:
        segment_count = len(packet.audio_segments or [])
    update["voice_tts_segment_count"] = str(segment_count)

    for key in (
        "tts_empty_segments_dropped",
        "tts_segment_overlong_count",
        "tts_max_segment_chars",
    ):
        if packet_metadata.get(key) is not None:
            update[f"voice_{key.removeprefix('tts_')}"] = packet_metadata[key]

    return merge_voice_metadata(metadata, update)

def attach_voice_model_latency(
    metadata: dict[str, Any],
    *,
    packet: ResponsePacket,
) -> dict[str, Any]:
    """把 LLM 侧耗时带进语音元数据。

    优先级：llm_graph_latency_ms（主图 LLM 节点）> llm_latency_ms > chat_latency_ms。
    找不到时不写字段，消费方需容忍缺失。
    """

    packet_metadata = dict(packet.metadata or {})

    for key in ("llm_graph_latency_ms", "llm_latency_ms", "chat_latency_ms"):
        value = packet_metadata.get(key)
        if value is None:
            continue
        return merge_voice_metadata(
            metadata,
            {
                "voice_llm_latency_ms": value,
                "voice_llm_latency_source": key,
            },
        )

    return dict(metadata or {})


def attach_voice_live2d_status(
    metadata: dict[str, Any],
    *,
    packet: ResponsePacket,
) -> dict[str, Any]:
    """把 Live2D 表达层状态与耗时带进语音元数据。"""

    packet_metadata = dict(packet.metadata or {})
    update: dict[str, Any] = {}

    status = packet_metadata.get("live2d_status")
    if status is not None:
        update["voice_live2d_status"] = status

    if packet_metadata.get("live2d_skip_reason") is not None:
        update["voice_live2d_skip_reason"] = packet_metadata["live2d_skip_reason"]

    if packet_metadata.get("live2d_latency_ms") is not None:
        update["voice_live2d_latency_ms"] = packet_metadata["live2d_latency_ms"]

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