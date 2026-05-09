"""Dispatch motion and expression commands to Live2D."""
from __future__ import annotations

from aiagent.schemas.outputs import ResponsePacket
from integrations.live2d.file_live2d_client import FileLive2DClient
from integrations.live2d.mock_live2d_client import MockLive2DClient

class Live2DPayloadDispatcher:
    def __init__(self,client:FileLive2DClient) -> None:
        self.client = client

    def dispatch(self, packet: ResponsePacket) -> ResponsePacket:
        metadata = packet.metadata or {}

        image_type = metadata.get("vision_image_type", "")
        daily_scene_type = metadata.get("vision_daily_scene_type", "")
        topic = metadata.get("rag_query", "") or metadata.get("state_topic", "")

        live2d = packet.live2d if isinstance(packet.live2d, dict) else {}
        character = live2d.get("character", {}) if isinstance(live2d.get("character"), dict) else {}
        scene = live2d.get("scene", {}) if isinstance(live2d.get("scene"), dict) else {}

        character_id = str(character.get("character_id") or "yzl")
        background_id = str(scene.get("background_id") or "")
        if self.client is isinstance(self.client,FileLive2DClient):
            command_path = self.client.dispatch(
                character_id=character_id,
                emotion=str(packet.emotion or "neutral"),
                expression=packet.expression,
                motion=packet.motion,
                background_id=background_id or None,
                image_type=image_type or None,
                daily_scene_type=daily_scene_type or None,
                topic=topic or None,
                audio_url=packet.audio_url,
                metadata={
                    "reply_text": packet.reply_text,
                    "source": "response_packet",
                },
            )

        packet.live2d_command_path = command_path
        packet.metadata["live2d"] = "file_payload"
        return packet


# Backward-compatible name for existing bootstrap/output broadcaster wiring.
Live2DDispatcher = Live2DPayloadDispatcher
