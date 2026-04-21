"""Broadcast output events to external consumers."""

import logging

from aiagent.expression.audio_playback_dispatcher import AudioPlaybackDispatcher
from aiagent.expression.live2d_dispatcher import Live2DDispatcher
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
    ) -> None:
        self.tts_dispatcher = tts_dispatcher
        self.live2d_dispatcher = live2d_dispatcher
        self.motion_policy = motion_policy
        self.audio_playback_dispatcher = audio_playback_dispatcher
        self.logger = logging.getLogger(self.__class__.__name__)

    def broadcast(self, output_event: OutputEvent) -> OutputEvent:
        packet = output_event.packet

        try:
            packet = self.motion_policy.refine(packet)
        except Exception as exc:
            self.logger.exception("Motion policy failed: %s", exc)
            packet.metadata["motion_policy"] = f"failed:{exc}"

        try:
            packet = self.tts_dispatcher.dispatch(packet)
        except Exception as exc:
            self.logger.exception("TTS dispatch failed: %s", exc)
            packet.metadata["tts"] = f"failed:{exc}"

        try:
            packet = self.live2d_dispatcher.dispatch(packet)
        except Exception as exc:
            self.logger.exception("Live2D dispatch failed: %s", exc)
            packet.metadata["live2d"] = f"failed:{exc}"

        try:
            packet = self.audio_playback_dispatcher.dispatch(packet)
        except Exception as exc:
            self.logger.exception("Audio playback dispatch failed: %s", exc)
            packet.metadata["audio_playback"] = f"failed:{exc}"

        output_event.packet = packet
        return output_event
