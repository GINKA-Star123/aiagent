"""TTS 派发元数据与分段清理单测（roadmap 5.1 / 7.1）。"""

from __future__ import annotations

from aiagent.expression.tts_dispatcher import MAX_TTS_SEGMENT_CHARS, TTSDispatcher
from aiagent.schemas.outputs import ResponsePacket
from aiagent.state.speaking_state import SpeakingState
from integrations.tts.mock_tts_client import MockTTSClient


def _dispatcher(tmp_path, *, provider: str = "mock", enable_mock: bool = True) -> TTSDispatcher:
    return TTSDispatcher(
        mock_tts_client=MockTTSClient(output_dir=tmp_path),
        speaking_state=SpeakingState(),
        tts_provider=provider,
        enable_mock_tts=enable_mock,
    )


def test_tts_success_writes_status_and_latency(tmp_path):
    dispatcher = _dispatcher(tmp_path)
    packet = ResponsePacket(reply_text="你好呀", should_speak=True)

    result = dispatcher.dispatch(packet)

    assert result.metadata["tts_status"] == "ok"
    assert float(result.metadata["tts_latency_ms"]) >= 0
    assert result.metadata["tts_segments"] == "1"
    assert result.metadata["tts_empty_segments_dropped"] == "0"
    assert result.metadata["tts_segment_overlong_count"] == "0"
    assert result.audio_url.startswith("/audio/")
    assert result.audio_segments == [result.audio_path]


def test_tts_skipped_when_should_speak_false(tmp_path):
    dispatcher = _dispatcher(tmp_path)
    packet = ResponsePacket(reply_text="", should_speak=False)

    result = dispatcher.dispatch(packet)

    assert result.metadata["tts_status"] == "skipped"
    assert result.metadata["tts_skip_reason"] == "should_speak_false"
    assert float(result.metadata["tts_latency_ms"]) >= 0
    assert result.audio_url is None


def test_tts_failed_when_provider_unsupported(tmp_path):
    dispatcher = _dispatcher(tmp_path, provider="not-a-provider", enable_mock=False)
    packet = ResponsePacket(reply_text="你好", should_speak=True)

    result = dispatcher.dispatch(packet)

    assert result.metadata["tts_status"] == "failed"
    assert result.metadata["tts_error"]
    assert float(result.metadata["tts_latency_ms"]) >= 0
    assert result.audio_path is None


def test_tts_drops_empty_segments(tmp_path, monkeypatch):
    dispatcher = _dispatcher(tmp_path)
    monkeypatch.setattr(
        dispatcher,
        "_synthesize",
        lambda text: ("a.wav", ["a.wav", "", "b.wav"], ["片段一", "", "片段二"]),
    )
    packet = ResponsePacket(reply_text="两段", should_speak=True)

    result = dispatcher.dispatch(packet)

    assert result.metadata["tts_status"] == "ok"
    assert result.metadata["tts_segments"] == "2"
    assert result.metadata["tts_empty_segments_dropped"] == "1"
    assert result.audio_segments == ["a.wav", "b.wav"]
    assert result.audio_segment_texts == ["片段一", "片段二"]


def test_tts_marks_overlong_segment(tmp_path, monkeypatch):
    dispatcher = _dispatcher(tmp_path)
    long_text = "长" * (MAX_TTS_SEGMENT_CHARS + 1)
    monkeypatch.setattr(
        dispatcher,
        "_synthesize",
        lambda text: ("a.wav", ["a.wav"], [long_text]),
    )
    packet = ResponsePacket(reply_text="长文本", should_speak=True)

    result = dispatcher.dispatch(packet)

    assert result.metadata["tts_segment_overlong_count"] == "1"
    assert result.metadata["tts_max_segment_chars"] == str(MAX_TTS_SEGMENT_CHARS)


def test_tts_fails_when_all_segments_empty(tmp_path, monkeypatch):
    dispatcher = _dispatcher(tmp_path)
    monkeypatch.setattr(
        dispatcher,
        "_synthesize",
        lambda text: ("", ["", ""], ["", ""]),
    )
    packet = ResponsePacket(reply_text="空段", should_speak=True)

    result = dispatcher.dispatch(packet)

    assert result.metadata["tts_status"] == "failed"
    assert "no usable segments" in result.metadata["tts_error"]