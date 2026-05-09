from __future__ import annotations

from aiagent.schemas.outputs import ResponsePacket


class NoopLive2DDispatcher:
    def dispatch(self, packet: ResponsePacket) -> ResponsePacket:
        packet.live2d_command_path = None
        packet.metadata["live2d"] = "mock_disabled"

        if not isinstance(packet.live2d, dict):
            packet.live2d = {}

        packet.live2d.setdefault(
            "character",
            {
                "character_id": "yzl",
                "model_id": "yzl_v1",
                "emotion": packet.emotion or "neutral",
                "expression": packet.expression or "neutral",
                "motion": packet.motion or "idle",
                "motion_priority": 1,
                "mouth": {
                    "mode": "idle",
                    "audio_url": "",
                },
                "eye": {
                    "blink": True,
                    "look_at": "user",
                },
            },
        )

        packet.live2d.setdefault(
            "scene",
            {
                "background_id": "room_default",
                "lighting": "normal",
                "effect": "none",
            },
        )

        return packet
