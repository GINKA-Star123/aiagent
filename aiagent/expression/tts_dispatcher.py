"""Dispatch text to TTS service."""
from __future__ import annotations

import logging
from datetime import datetime

from aiagent.schemas.outputs import ResponsePacket
from aiagent.state.speaking_state import SpeakingState
from integrations.tts.gpt_sovits_client import GPTSoVITSClient
from integrations.tts.mock_tts_client import MockTTSClient


class TTSDispatcher:
    def __init__(
        self,
        mock_tts_client: MockTTSClient,
        speaking_state: SpeakingState,
        tts_provider: str = "mock",
        enable_mock_tts: bool = True,
        gpt_sovits_client: GPTSoVITSClient | None = None,
    ) -> None:
        self.mock_tts_client = mock_tts_client
        self.speaking_state = speaking_state
        self.tts_provider = tts_provider
        self.enable_mock_tts = enable_mock_tts
        self.gpt_sovits_client = gpt_sovits_client
        self.logger = logging.getLogger(self.__class__.__name__)

    def dispatch(self, packet: ResponsePacket) -> ResponsePacket:
        if not packet.should_speak:
            packet.metadata["tts"] = "skipped_should_speak_false"
            return packet

        self.speaking_state.last_tts_text = packet.reply_text
        self.speaking_state.last_updated_at = datetime.now().isoformat(timespec="seconds")

        try:
            audio_path = self._synthesize(packet.reply_text)
        except Exception as exc:
            self.logger.exception("TTS dispatch failed: %s", exc)
            audio_path = self.mock_tts_client.synthesize(packet.reply_text)
            packet.metadata["tts"] = "mock-fallback"
            packet.metadata["tts_error"] = str(exc)
            self.speaking_state.current_provider = "mock-fallback"
        else:
            packet.metadata["tts"] = self.tts_provider
            self.speaking_state.current_provider = self.tts_provider

        self.speaking_state.last_audio_path = audio_path
        self.speaking_state.last_updated_at = datetime.now().isoformat(timespec="seconds")
        packet.audio_path = audio_path
        return packet

    def _synthesize(self, text: str) -> str:
        if self.enable_mock_tts or self.tts_provider == "mock":
            self.logger.info("using mock tts provider")
            return self.mock_tts_client.synthesize(text)

        if self.tts_provider == "gpt_sovits":
            if self.gpt_sovits_client is None:
                raise RuntimeError("GPT-SOVITS client is not initialized")
            self.logger.info("using GPT-SOVITS TTS provider")
            return self.gpt_sovits_client.synthesize(text)

        raise RuntimeError(f"Unsupported TTS provider: {self.tts_provider}")
