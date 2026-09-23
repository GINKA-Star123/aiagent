from __future__ import annotations

from typing import Any

from pydantic import BaseModel,Field

LIVE2D_PAYLOAD_VERSION = "1.0"

# 语义情绪词表：仅用于"未知情绪"告警，不做强制改写。
# expression / motion 是 profile 里的资产 id（例如 smile / wave），必须保持自由字符串，
# 因此这里不提供它们的白名单。
LIVE2D_EMOTION_VOCABULARY = (
    "neutral", "happy", "calm", "excited", "angry", "sad", "shy", "surprised",
)

# 单个字段的字符上限，超长一律截断并记录告警。
LIVE2D_MAX_TEXT_CHARS = 64

# audio_url 只允许空值、站内相对路径或 http(s) 绝对地址。
LIVE2D_ALLOWED_AUDIO_PREFIXES = ("/", "", "http://", "https://")

class Live2DPayloadWarning(BaseModel):
    """Live2D payload 在归一化过程中被修正或降级的一条记录。"""

    path: str = ""
    code: str = ""
    detail: str = ""


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
    # 归一化过程中被修正/降级的项；客户端可忽略，排查时很有用。
    warnings: list[Live2DPayloadWarning] = Field(default_factory=list)