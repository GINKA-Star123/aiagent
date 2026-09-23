from __future__ import annotations

from aiagent.graphs.graph_model import (
    VisionConfidenceLevel,
    VisionImageType,
    VisionMemoryCandidate,
    VisionMemoryDecision,
    VisionSafetyResult,
)

SCENE_IMAGE_TYPES = {
    VisionImageType.DAILY,
    VisionImageType.FOOD,
    VisionImageType.TRAVEL,
    VisionImageType.LANDSCAPE,
    VisionImageType.OBJECT,
}

TRANSIENT_IMAGE_TYPES = {
    VisionImageType.DOCUMENT,
    VisionImageType.SCREENSHOT,
}

CONFIDENT_LEVELS = {
    VisionConfidenceLevel.HIGH,
    VisionConfidenceLevel.MEDIUM,
}


def decide_memory(
    *,
    image_type: VisionImageType | str,
    identity_confirmed: bool,
    identity_candidate_exists: bool,
    confidence_level: VisionConfidenceLevel | str,
    confidence_score: float,
    safety: VisionSafetyResult | None = None,
    model_memory: VisionMemoryCandidate | None = None,
    has_ocr_text: bool = False,
    people_count: int | None = None,
) -> VisionMemoryDecision:
    """视觉结果进入长期记忆前的策略闸门。

    设计原则（对应 roadmap 6.4）：
    1. 高敏/高风险内容一律不记；
    2. 未确认的角色身份绝不写成长期记忆——"可能像洛天依"不是事实；
    3. 文档/截图属于一次性内容，不构成长期偏好；
    4. 日常图片必须同时满足"模型认为值得记"和"场景置信度足够"；
    5. 画中有人且只有角色候选时拒绝写入，避免推断真实人物身份。
    """
    normalized_type = _image_type(image_type)
    level = _level(confidence_level)
    model_wants = bool(model_memory.should_consider) if model_memory is not None else False

    if safety is not None and (safety.has_sensitive_content or safety.risk_level == "high"):
        return _deny("sensitive_content", "图片包含敏感内容或高风险内容，不写入长期记忆")

    if normalized_type == VisionImageType.UNKNOWN:
        return _deny("unknown_image_type", "图片类型未识别，缺少可长期记忆的稳定信息")

    if normalized_type == VisionImageType.CHARACTER:
        if identity_confirmed:
            return VisionMemoryDecision(
                allow=True,
                reason_code="confirmed_character_identity",
                reason="角色身份已确认，可作为稳定的兴趣/话题记忆",
                categories=["topic"],
            )
        return _deny(
            "unconfirmed_character_identity",
            "角色身份未确认，只有候选，不能把推测写成长期记忆",
        )

    if normalized_type in TRANSIENT_IMAGE_TYPES:
        suffix = "（即使包含 OCR 文本也不写入）" if has_ocr_text else ""
        return _deny("transient_document_image", f"文档/截图属于一次性内容，不构成长期记忆{suffix}")

    if normalized_type in SCENE_IMAGE_TYPES:
        if people_count and identity_candidate_exists and not identity_confirmed:
            return _deny(
                "possible_real_person_identity",
                "画面中有人物且只有角色候选，禁止推断真实人物身份并写入记忆",
            )
        if not model_wants:
            return _deny("model_not_considering", "模型认为该图片不值得作为长期记忆")
        if level not in CONFIDENT_LEVELS:
            return _deny(
                "low_confidence_scene",
                f"场景理解置信度不足（{confidence_score:.3f}），不写入长期记忆",
            )
        return VisionMemoryDecision(
            allow=True,
            reason_code="scene_preference_signal",
            reason="场景理解可信，可作为偏好类记忆候选",
            categories=["preference"],
        )

    return _deny("unsupported_image_type", f"不支持的图片类型：{normalized_type.value}")


def _deny(reason_code: str, reason: str) -> VisionMemoryDecision:
    return VisionMemoryDecision(allow=False, reason_code=reason_code, reason=reason, categories=[])


def _image_type(value: VisionImageType | str) -> VisionImageType:
    if isinstance(value, VisionImageType):
        return value
    try:
        return VisionImageType(str(value).strip().lower())
    except Exception:
        return VisionImageType.UNKNOWN


def _level(value: VisionConfidenceLevel | str) -> VisionConfidenceLevel:
    if isinstance(value, VisionConfidenceLevel):
        return value
    try:
        return VisionConfidenceLevel(str(value).strip().lower())
    except Exception:
        return VisionConfidenceLevel.UNCERTAIN