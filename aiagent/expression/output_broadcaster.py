"""Broadcast output events to external consumers."""

from __future__ import annotations

import logging

from aiagent.expression.audio_playback_dispatcher import AudioPlaybackDispatcher
from aiagent.expression.live2d_payload_dispatcher import Live2DDispatcher
from aiagent.expression.motion_policy import MotionPolicy
from aiagent.expression.tts_dispatcher import TTSDispatcher
from aiagent.schemas.outputs import OutputEvent


class OutputBroadcaster:
    def __init__(
        self,
        tts_dispatcher: TTSDispatcher,
        live2d_dispatcher: Live2DDispatcher,
        motion_policy: MotionPolicy,
        audio_playback_dispatcher: AudioPlaybackDispatcher,
        enable_local_audio_playback: bool = False,
    ) -> None:
        self.tts_dispatcher = tts_dispatcher
        self.live2d_dispatcher = live2d_dispatcher
        self.motion_policy = motion_policy
        self.audio_playback_dispatcher = audio_playback_dispatcher
        self.enable_local_audio_playback = enable_local_audio_playback
        self.logger = logging.getLogger(self.__class__.__name__)

    def broadcast(self, output_event: OutputEvent) -> OutputEvent:
        packet = output_event.packet

        try:
            packet = self.motion_policy.refine(packet)
        except Exception as exc:
            self.logger.exception("Motion policy failed: %s", exc)
            packet.metadata["motion_policy"] = f"failed:{exc}"

        if packet.should_speak:
            packet = self._run_tts(packet)
        else:
            packet.metadata["tts"] = "skipped_should_speak_false"

        try:
            packet = self.live2d_dispatcher.dispatch(packet)
        except Exception as exc:
            self.logger.exception("Live2D dispatch failed: %s", exc)
            packet.metadata["live2d"] = f"failed:{exc}"

        if self.enable_local_audio_playback:
            packet = self._run_local_playback(packet)
        else:
            packet.metadata["audio_playback"] = "skipped_client_playback_mode"

        output_event.packet = packet
        return output_event

    def _run_tts(self, packet):
        try:
            return self.tts_dispatcher.dispatch(packet)
        except Exception as exc:
            self.logger.exception("TTS dispatch failed: %s", exc)
            packet.metadata["tts"] = f"failed:{exc}"
            return packet

    def _run_local_playback(self, packet):
        try:
            return self.audio_playback_dispatcher.dispatch(packet)
        except Exception as exc:
            self.logger.exception("Audio playback dispatch failed in background: %s", exc)
            packet.metadata["audio_playback"] = f"failed:{exc}"
            return packet
