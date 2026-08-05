from __future__ import annotations

from typing import Any

from pydantic import BaseModel,Field

LIVE2D_PAYLOAD_VERSION = "1.0"

class Live2DExpressionAsset(BaseModel):
    expression_id:str
    file:str
    aliases:list[str] = Field(default_factory=list)

class Live2DMotionAsset(BaseModel):
    motion_id:str
    group:str = "default"
    file:str
    priority:int  = 1
    aliases: list[str] = Field(default_factory=list)

class Live2DCharacterProfile(BaseModel):
    character_id :str
    model_id:str
    display_name :str 
    model3_json:str

    default_expression:str = "neutral"
    default_motion:str = "idle"

    expressions:list[Live2DExpressionAsset] = Field(default_factory=list)
    motions: list[Live2DMotionAsset] = Field(default_factory=list)

    emotion_expression_map:dict[str,str] = Field(default_factory=dict)
    emotion_motion_map:dict[str,str] = Field(default_factory=dict)

    metadata:dict[str,Any] = Field(default_factory=dict)

class Live2DBackgroundProfile(BaseModel):
    background_id:str
    display_name : str
    file:str = ""
    kind:str = "image"
    metadata:dict[str,Any] = Field(default_factory=dict)

class Live2DCharacterCommand(BaseModel):
    character_id: str = "yzl"
    model_id: str = "yzl_v1"
    display_name: str = ""
    model3_json: str = ""

    emotion: str = "neutral"
    expression: str = "neutral"
    expression_file: str = ""

    motion: str = "idle"
    motion_group: str = "default"
    motion_file: str = ""
    motion_priority: int = 1

    mouth: dict[str, Any] = Field(
        default_factory=lambda: {
            "mode": "idle",
            "audio_url": "",
        }
    )

    eye: dict[str, Any] = Field(
        default_factory=lambda: {
            "blink": True,
            "look_at": "user",
        }
    )

    metadata: dict[str, Any] = Field(default_factory=dict)


class Live2DSceneCommand(BaseModel):
    background_id: str = "room_default"
    background_file: str = ""
    lighting: str = "normal"
    effect: str = "none"
    metadata: dict[str, Any] = Field(default_factory=dict)


class Live2DPayload(BaseModel):
    version: str = LIVE2D_PAYLOAD_VERSION
    character: Live2DCharacterCommand = Field(default_factory=Live2DCharacterCommand)
    scene: Live2DSceneCommand = Field(default_factory=Live2DSceneCommand)
    metadata: dict[str, Any] = Field(default_factory=dict)