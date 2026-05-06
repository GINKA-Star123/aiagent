from __future__ import annotations

from typing import Any

from aiagent.live2d.models import (
    Live2DCharacterCommand,
    Live2DPayload,
    Live2DSceneCommand,
)
from aiagent.live2d.motion_mapper import Live2DMotionMapper
from aiagent.live2d.registry import Live2DRegistry
from aiagent.live2d.scene_mapper import Live2DSceneMapper


class Live2DPayloadBuilder:
    def __init__(
        self,
        registry: Live2DRegistry,
        motion_mapper: Live2DMotionMapper | None = None,
        scene_mapper: Live2DSceneMapper | None = None,
    ) -> None:
        self.registry = registry
        self.motion_mapper = motion_mapper or Live2DMotionMapper()
        self.scene_mapper = scene_mapper or Live2DSceneMapper()

    def build(
        self,
        *,
        character_id: str = "yzl",
        emotion: str = "neutral",
        expression: str | None = None,
        motion: str | None = None,
        background_id: str | None = None,
        image_type: str | None = None,
        daily_scene_type: str | None = None,
        topic: str | None = None,
        audio_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        character_profile = self.registry.get_character(character_id)

        expression_asset = self.motion_mapper.resolve_expression(
            profile=character_profile,
            emotion=emotion,
            expression=expression,
        )
        motion_asset = self.motion_mapper.resolve_motion(
            profile=character_profile,
            emotion=emotion,
            motion=motion,
        )

        resolved_background_id = self.scene_mapper.scene_from_context(
            background_id=background_id,
            image_type=image_type,
            daily_scene_type=daily_scene_type,
            topic=topic,
            emotion=emotion,
        )
        background_profile = self.registry.get_background(resolved_background_id)

        expression_id = (
            expression_asset.expression_id
            if expression_asset is not None
            else character_profile.default_expression
        )
        expression_file = expression_asset.file if expression_asset is not None else ""

        motion_id = (
            motion_asset.motion_id
            if motion_asset is not None
            else character_profile.default_motion
        )
        motion_group = motion_asset.group if motion_asset is not None else "default"
        motion_file = motion_asset.file if motion_asset is not None else ""
        motion_priority = motion_asset.priority if motion_asset is not None else 1

        payload = Live2DPayload(
            character=Live2DCharacterCommand(
                character_id=character_profile.character_id,
                model_id=character_profile.model_id,
                emotion=emotion or "neutral",
                expression=expression_id,
                expression_file=expression_file,
                motion=motion_id,
                motion_group=motion_group,
                motion_file=motion_file,
                motion_priority=motion_priority,
                mouth={
                    "mode": "audio" if audio_url else "idle",
                    "audio_url": audio_url or "",
                },
                eye={
                    "blink": True,
                    "look_at": "user",
                },
            ),
            scene=Live2DSceneCommand(
                background_id=background_profile.background_id,
                background_file=background_profile.file,
                lighting="normal",
                effect="none",
                metadata=background_profile.metadata,
            ),
            metadata={
                "source": "live2d_payload_builder",
                **(metadata or {}),
            },
        )

        return payload.model_dump(mode="json")
