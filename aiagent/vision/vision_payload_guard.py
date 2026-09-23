from __future__ import annotations

from typing import Any

from aiagent.graphs.graph_model import (
    DailySceneResult,
    VisionChannels,
    VisionImageType,
    VisionLive2DSuggestion,
    VisionMemoryCandidate,
    VisionModelCharacter,
    VisionModelPayload,
    VisionSafetyResult,
    VisionSchemaViolation,
    VisionSectionReport,
    VisionSectionStatus,
)

MAX_TEXT_CHARS = 2000
MAX_LIST_ITEMS = 40
MAX_ITEM_CHARS = 200
MAX_CHARACTER_ITEMS = 10

IMAGE_TYPES = {item.value for item in VisionImageType}
DAILY_SCENE_TYPES = {
    "travel", "food", "desk", "street", "home", "landscape",
    "screenshot", "document", "object", "unknown",
}
RISK_LEVELS = {"none", "low", "medium", "high"}
LIVE2D_EMOTIONS = {"neutral", "happy", "calm", "excited", "angry", "sad", "surprised"}
LIVE2D_EXPRESSIONS = {"neutral", "gentle", "happy_smile", "bright_smile", "serious", "shy"}
LIVE2D_MOTIONS = {"idle", "soft_idle", "smile_nod", "excited_wave", "serious_still"}
LIVE2D_BACKGROUNDS = {
    "room_default", "room_night", "desk_work", "travel_day",
    "cafe_table", "stage_default", "street_day", "landscape_view",
}


def normalize_payload(raw: Any) -> tuple[VisionModelPayload, list[VisionSchemaViolation]]:
    """把视觉模型的原始输出校验并修复成 VisionModelPayload。

    契约：**任何情况下都不抛异常**。非法字段一律回落到安全默认值，
    并把问题记录成 VisionSchemaViolation 供上层观测。
    """
    violations: list[VisionSchemaViolation] = []

    if not isinstance(raw, dict):
        violations.append(
            _violation("$", "root_not_object", f"模型输出根节点是 {type(raw).__name__}，按空结果处理")
        )
        return VisionModelPayload(), violations

    image_type, image_type_code = _image_type(raw.get("image_type"))
    if image_type_code:
        violations.append(_violation("image_type", image_type_code, f"未知图片类型：{raw.get('image_type')!r}"))

    confidence, confidence_code = _ratio(raw.get("confidence"))
    if confidence_code:
        violations.append(_violation("confidence", confidence_code, f"confidence 非法：{raw.get('confidence')!r}"))

    objects, object_violations = _string_list(raw.get("objects"), "objects")
    ocr_text, ocr_violations = _string_list(raw.get("ocr_text"), "ocr_text")
    violations.extend(object_violations)
    violations.extend(ocr_violations)

    daily_scene, daily_violations = _daily_scene(raw.get("daily_scene"))
    violations.extend(daily_violations)

    characters, character_violations = _characters(raw.get("recognized_characters"))
    violations.extend(character_violations)

    safety, safety_violations = _safety(raw.get("safety"))
    violations.extend(safety_violations)

    memory, memory_violations = _memory(raw.get("memory"))
    violations.extend(memory_violations)

    live2d, live2d_violations = _live2d(raw.get("live2d"))
    violations.extend(live2d_violations)

    summary, summary_violation = _text(raw.get("summary"), "summary")
    scene, scene_violation = _text(raw.get("scene"), "scene")
    mood, mood_violation = _text(raw.get("mood"), "mood")
    confidence_reason, reason_violation = _text(raw.get("confidence_reason"), "confidence_reason")
    for item in (summary_violation, scene_violation, mood_violation, reason_violation):
        if item is not None:
            violations.append(item)

    payload = VisionModelPayload(
        image_type=image_type,
        user_intent=_short_text(raw.get("user_intent"), "unknown"),
        confidence=confidence,
        confidence_reason=confidence_reason,
        summary=summary,
        objects=objects,
        scene=scene,
        daily_scene=daily_scene,
        ocr_text=ocr_text,
        mood=mood,
        characters=characters,
        safety=safety,
        memory=memory,
        live2d=live2d,
        raw_output=str(raw.get("_raw_model_output") or "")[:MAX_TEXT_CHARS],
    )
    return payload, violations


def build_channels(
    *,
    payload: VisionModelPayload,
    retrieval_candidate_count: int = 0,
    identity_confirmed: bool = False,
) -> VisionChannels:
    """把三条链路的状态拆开。

    OCR 命中不等于场景理解成功，场景理解成功也不等于角色身份确认。
    上层据此决定"这一段能不能注入 prompt"。
    """
    ocr_items = len(payload.ocr_text)
    ocr = VisionSectionReport(
        status=VisionSectionStatus.OK if ocr_items else VisionSectionStatus.MISSING,
        confidence=payload.confidence if ocr_items else 0.0,
        item_count=ocr_items,
        reason="使用模型整体置信度，非独立 OCR 置信度" if ocr_items else "模型未返回 OCR 文本",
    )

    scene_items = (
        (1 if payload.summary else 0)
        + (1 if payload.scene else 0)
        + len(payload.objects)
        + len(payload.daily_scene.notable_details)
    )
    has_scene = scene_items > 0 or payload.daily_scene.scene_type not in {"", "unknown"}
    scene = VisionSectionReport(
        status=VisionSectionStatus.OK if has_scene else VisionSectionStatus.MISSING,
        confidence=payload.confidence if has_scene else 0.0,
        item_count=scene_items,
        reason="场景与物体描述可用" if has_scene else "模型未返回可用场景描述",
    )

    if identity_confirmed:
        character_status = VisionSectionStatus.OK
        character_reason = "模型确认了角色身份"
    elif payload.characters or retrieval_candidate_count:
        character_status = VisionSectionStatus.PARTIAL
        character_reason = (
            f"仅有候选（模型声明 {len(payload.characters)} 个，图库候选 {retrieval_candidate_count} 个），"
            "不能当作身份确认"
        )
    else:
        character_status = VisionSectionStatus.MISSING
        character_reason = "没有角色线索"

    character = VisionSectionReport(
        status=character_status,
        confidence=payload.characters[0].confidence if payload.characters else 0.0,
        item_count=len(payload.characters),
        reason=character_reason,
    )

    return VisionChannels(ocr=ocr, scene=scene, character=character)


def describe_violations(violations: list[VisionSchemaViolation]) -> str:
    if not violations:
        return ""
    return ",".join(dict.fromkeys(item.code for item in violations if item.code))


def _violation(path: str, code: str, detail: str) -> VisionSchemaViolation:
    return VisionSchemaViolation(path=path, code=code, detail=str(detail)[:200])


def _image_type(value: Any) -> tuple[VisionImageType, str]:
    if value is None:
        return VisionImageType.UNKNOWN, ""
    normalized = str(value).strip().lower()
    if normalized in IMAGE_TYPES:
        return VisionImageType(normalized), ""
    return VisionImageType.UNKNOWN, "invalid_image_type"


def _ratio(value: Any) -> tuple[float, str]:
    if value is None:
        return 0.0, ""
    if isinstance(value, bool):
        return 0.0, "invalid_confidence"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0, "invalid_confidence"
    if number != number:          # NaN
        return 0.0, "invalid_confidence"
    if number < 0.0 or number > 1.0:
        return min(max(number, 0.0), 1.0), "confidence_out_of_range"
    return number, ""


def _text(value: Any, path: str) -> tuple[str, VisionSchemaViolation | None]:
    if value is None:
        return "", None
    if isinstance(value, (dict, list)):
        return "", _violation(path, "invalid_text", f"{path} 期望字符串，收到 {type(value).__name__}")
    text = " ".join(str(value).split())
    if len(text) > MAX_TEXT_CHARS:
        return text[:MAX_TEXT_CHARS], _violation(path, "text_truncated", f"{path} 超长，已截断")
    return text, None


def _short_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return fallback
    text = " ".join(str(value).split())
    return text[:MAX_ITEM_CHARS] if text else fallback


def _clip(text: Any) -> str:
    return " ".join(str(text).split())[:MAX_ITEM_CHARS]


def _string_list(value: Any, path: str) -> tuple[list[str], list[VisionSchemaViolation]]:
    """把"可能是字符串/对象/数组"的字段统一收敛成字符串数组。

    这一步专门防模型把 "objects": "猫，沙发" 写成字符串——
    原实现会逐字符迭代成 ["猫","，","沙","发"]。
    """
    violations: list[VisionSchemaViolation] = []

    if value is None:
        return [], violations

    if isinstance(value, str):
        parts = (
            value.replace("，", "\n")
            .replace("、", "\n")
            .replace(",", "\n")
            .splitlines()
        )
        items = [_clip(item) for item in parts if item.strip()][:MAX_LIST_ITEMS]
        violations.append(_violation(path, "list_from_string", f"{path} 收到字符串，已按分隔符拆分"))
        return items, violations

    if isinstance(value, dict):
        items = [_clip(item) for item in value.values() if str(item).strip()][:MAX_LIST_ITEMS]
        violations.append(_violation(path, "list_from_object", f"{path} 收到对象，已取字段值"))
        return items, violations

    if not isinstance(value, list):
        violations.append(_violation(path, "invalid_list", f"{path} 期望数组，收到 {type(value).__name__}"))
        return [], violations

    output: list[str] = []
    for index, item in enumerate(value[:MAX_LIST_ITEMS]):
        if isinstance(item, (dict, list)):
            violations.append(_violation(f"{path}[{index}]", "invalid_list_item", "数组元素不是字符串，已丢弃"))
            continue
        text = _clip(item)
        if text:
            output.append(text)

    if len(value) > MAX_LIST_ITEMS:
        violations.append(_violation(path, "list_truncated", f"{path} 超过 {MAX_LIST_ITEMS} 项，已截断"))

    return output, violations


def _optional_int(value: Any) -> tuple[int | None, str]:
    if value is None or value == "":
        return None, ""
    if isinstance(value, bool):
        return None, "invalid_people_count"
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, "invalid_people_count"
    if number < 0 or number > 100:
        return max(min(number, 100), 0), "people_count_out_of_range"
    return number, ""


def _daily_scene(value: Any) -> tuple[DailySceneResult, list[VisionSchemaViolation]]:
    violations: list[VisionSchemaViolation] = []

    if value is None:
        return DailySceneResult(), violations
    if not isinstance(value, dict):
        violations.append(_violation("daily_scene", "invalid_object", f"期望对象，收到 {type(value).__name__}"))
        return DailySceneResult(), violations

    scene_type = str(value.get("scene_type") or "unknown").strip().lower()
    if scene_type not in DAILY_SCENE_TYPES:
        violations.append(_violation("daily_scene.scene_type", "invalid_scene_type", f"未知场景类型：{scene_type}"))
        scene_type = "unknown"

    food, food_violations = _string_list(value.get("food"), "daily_scene.food")
    landmarks, landmark_violations = _string_list(value.get("landmarks"), "daily_scene.landmarks")
    objects, object_violations = _string_list(value.get("objects"), "daily_scene.objects")
    details, detail_violations = _string_list(value.get("notable_details"), "daily_scene.notable_details")
    violations.extend(food_violations)
    violations.extend(landmark_violations)
    violations.extend(object_violations)
    violations.extend(detail_violations)

    people_count, people_code = _optional_int(value.get("people_count"))
    if people_code:
        violations.append(_violation("daily_scene.people_count", people_code, "people_count 非法，已修正"))

    return (
        DailySceneResult(
            scene_type=scene_type,
            location_hint=_short_text(value.get("location_hint")),
            activity=_short_text(value.get("activity")),
            food=food,
            landmarks=landmarks,
            objects=objects,
            people_count=people_count,
            time_hint=_short_text(value.get("time_hint")),
            weather_hint=_short_text(value.get("weather_hint")),
            notable_details=details,
        ),
        violations,
    )


def _characters(value: Any) -> tuple[list[VisionModelCharacter], list[VisionSchemaViolation]]:
    violations: list[VisionSchemaViolation] = []

    if value is None:
        return [], violations
    if not isinstance(value, list):
        violations.append(
            _violation("recognized_characters", "invalid_list", f"期望数组，收到 {type(value).__name__}")
        )
        return [], violations

    output: list[VisionModelCharacter] = []
    for index, item in enumerate(value[:MAX_CHARACTER_ITEMS]):
        if not isinstance(item, dict):
            violations.append(
                _violation(f"recognized_characters[{index}]", "invalid_list_item", "元素不是对象，已丢弃")
            )
            continue

        character_id = _short_text(item.get("character_id"))
        if not character_id:
            violations.append(
                _violation(
                    f"recognized_characters[{index}].character_id",
                    "missing_character_id",
                    "缺少 character_id，已丢弃",
                )
            )
            continue

        confidence, confidence_code = _ratio(item.get("confidence"))
        if confidence_code:
            violations.append(
                _violation(f"recognized_characters[{index}].confidence", confidence_code, "角色置信度非法，已归零")
            )

        evidence, evidence_violations = _string_list(
            item.get("evidence"),
            f"recognized_characters[{index}].evidence",
        )
        violations.extend(evidence_violations)

        output.append(
            VisionModelCharacter(
                character_id=character_id,
                name=_short_text(item.get("name")) or character_id,
                confidence=confidence,
                evidence=evidence,
            )
        )

    return output, violations


def _safety(value: Any) -> tuple[VisionSafetyResult, list[VisionSchemaViolation]]:
    violations: list[VisionSchemaViolation] = []

    if value is None:
        return VisionSafetyResult(), violations
    if not isinstance(value, dict):
        violations.append(_violation("safety", "invalid_object", f"期望对象，收到 {type(value).__name__}"))
        return VisionSafetyResult(), violations

    risk_level = str(value.get("risk_level") or "none").strip().lower()
    if risk_level not in RISK_LEVELS:
        violations.append(_violation("safety.risk_level", "invalid_risk_level", f"未知风险等级：{risk_level}"))
        # 未知风险按 medium 保守处理，既不放过也不误杀。
        risk_level = "medium"

    return (
        VisionSafetyResult(
            has_sensitive_content=bool(
                value.get("has_sensitive_content") or value.get("has_sentitive_content")
            ),
            risk_level=risk_level,
            reason=_short_text(value.get("reason")),
        ),
        violations,
    )


def _memory(value: Any) -> tuple[VisionMemoryCandidate, list[VisionSchemaViolation]]:
    violations: list[VisionSchemaViolation] = []

    if value is None:
        return VisionMemoryCandidate(), violations
    if not isinstance(value, dict):
        violations.append(_violation("memory", "invalid_object", f"期望对象，收到 {type(value).__name__}"))
        return VisionMemoryCandidate(), violations

    return (
        VisionMemoryCandidate(
            should_consider=bool(value.get("should_consider")),
            reason=_short_text(value.get("reason")),
        ),
        violations,
    )


def _live2d(value: Any) -> tuple[VisionLive2DSuggestion, list[VisionSchemaViolation]]:
    violations: list[VisionSchemaViolation] = []
    default = VisionLive2DSuggestion()

    if value is None:
        return default, violations
    if not isinstance(value, dict):
        violations.append(_violation("live2d", "invalid_object", f"期望对象，收到 {type(value).__name__}"))
        return default, violations

    return (
        VisionLive2DSuggestion(
            suggested_emotion=_choice(
                value.get("suggested_emotion"), LIVE2D_EMOTIONS, default.suggested_emotion,
                "live2d.suggested_emotion", violations,
            ),
            suggested_expression=_choice(
                value.get("suggested_expression"), LIVE2D_EXPRESSIONS, default.suggested_expression,
                "live2d.suggested_expression", violations,
            ),
            suggested_motion=_choice(
                value.get("suggested_motion"), LIVE2D_MOTIONS, default.suggested_motion,
                "live2d.suggested_motion", violations,
            ),
            suggested_background=_choice(
                value.get("suggested_background"), LIVE2D_BACKGROUNDS, default.suggested_background,
                "live2d.suggested_background", violations,
            ),
        ),
        violations,
    )


def _choice(
    value: Any,
    allowed: set[str],
    fallback: str,
    path: str,
    violations: list[VisionSchemaViolation],
) -> str:
    """枚举白名单：未知表情/动作一律回落默认值并记录违规（客户端不会收到未知值）。"""
    if value is None:
        return fallback
    normalized = str(value).strip().lower()
    if normalized in allowed:
        return normalized
    violations.append(_violation(path, "invalid_enum_value", f"{path} 不在白名单：{normalized!r}"))
    return fallback