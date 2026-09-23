from __future__ import annotations

from aiagent.graphs.graph_model import VisionImageType, VisionSectionStatus
from aiagent.vision.vision_payload_guard import (
    build_channels,
    describe_violations,
    normalize_payload,
)


def test_valid_payload_passes_without_violations():
    payload, violations = normalize_payload(
        {
            "image_type": "character",
            "user_intent": "识别角色",
            "confidence": 0.91,
            "confidence_reason": "特征明显",
            "summary": "一位蓝发少女在舞台上",
            "objects": ["麦克风", "舞台灯"],
            "scene": "舞台",
            "daily_scene": {"scene_type": "unknown"},
            "ocr_text": [],
            "mood": "明亮",
            "recognized_characters": [
                {
                    "character_id": "luotianyi",
                    "name": "洛天依",
                    "confidence": 0.91,
                    "evidence": ["蓝发"],
                }
            ],
            "safety": {"has_sensitive_content": False, "risk_level": "none"},
            "memory": {"should_consider": False, "reason": ""},
            "live2d": {"suggested_emotion": "happy", "suggested_motion": "smile_nod"},
            "_raw_model_output": "{}",
        }
    )

    assert violations == []
    assert payload.image_type == VisionImageType.CHARACTER
    assert payload.confidence == 0.91
    assert payload.characters[0].character_id == "luotianyi"
    assert payload.objects == ["麦克风", "舞台灯"]


def test_non_object_root_is_repaired_not_raised():
    payload, violations = normalize_payload("这不是 JSON 对象")

    assert payload.image_type == VisionImageType.UNKNOWN
    assert payload.confidence == 0.0
    assert describe_violations(violations) == "root_not_object"


def test_invalid_fields_are_repaired_and_recorded():
    payload, violations = normalize_payload(
        {
            "image_type": "cat_photo",
            "confidence": "很高",
            "objects": "猫，沙发、窗台",
            "ocr_text": {"a": "第一行", "b": "第二行"},
            "summary": {"nested": "不该是对象"},
            "daily_scene": "不是对象",
            "recognized_characters": [
                "洛天依",
                {"name": "缺少 id"},
                {"character_id": "yue", "confidence": 3.5},
            ],
            "safety": {"risk_level": "catastrophic"},
            "live2d": {"suggested_emotion": "ecstatic", "suggested_motion": "smile_nod"},
        }
    )

    codes = describe_violations(violations).split(",")
    assert "invalid_image_type" in codes
    assert "invalid_confidence" in codes
    assert "list_from_string" in codes
    assert "list_from_object" in codes
    assert "invalid_text" in codes
    assert "invalid_object" in codes
    assert "invalid_list_item" in codes
    assert "missing_character_id" in codes
    assert "confidence_out_of_range" in codes
    assert "invalid_risk_level" in codes
    assert "invalid_enum_value" in codes

    assert payload.image_type == VisionImageType.UNKNOWN
    assert payload.confidence == 0.0
    assert payload.objects == ["猫", "沙发", "窗台"]
    assert payload.ocr_text == ["第一行", "第二行"]
    assert payload.summary == ""
    assert payload.daily_scene.scene_type == "unknown"
    assert [item.character_id for item in payload.characters] == ["yue"]
    assert payload.characters[0].confidence == 1.0
    assert payload.safety.risk_level == "medium"
    assert payload.live2d.suggested_emotion == "neutral"
    assert payload.live2d.suggested_motion == "smile_nod"


def test_channels_keep_ocr_scene_and_character_separate():
    payload, _ = normalize_payload(
        {
            "image_type": "document",
            "confidence": 0.8,
            "summary": "一张发票",
            "ocr_text": ["金额 128 元"],
            "recognized_characters": [],
            "daily_scene": {"scene_type": "document"},
        }
    )

    channels = build_channels(payload=payload, retrieval_candidate_count=2)
    assert channels.ocr.status == VisionSectionStatus.OK
    assert channels.ocr.item_count == 1
    assert channels.scene.status == VisionSectionStatus.OK
    assert channels.character.status == VisionSectionStatus.PARTIAL
    assert "不能当作身份确认" in channels.character.reason


def test_channels_report_missing_when_all_empty():
    payload, _ = normalize_payload({"image_type": "unknown"})
    channels = build_channels(payload=payload)

    assert channels.ocr.status == VisionSectionStatus.MISSING
    assert channels.scene.status == VisionSectionStatus.MISSING
    assert channels.character.status == VisionSectionStatus.MISSING