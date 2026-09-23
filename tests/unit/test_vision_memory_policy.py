from __future__ import annotations

from aiagent.graphs.graph_model import (
    VisionConfidenceLevel,
    VisionImageType,
    VisionMemoryCandidate,
    VisionSafetyResult,
)
from aiagent.vision.vision_memory_policy import decide_memory


def _decide(**overrides):
    kwargs = {
        "image_type": VisionImageType.DAILY,
        "identity_confirmed": False,
        "identity_candidate_exists": False,
        "confidence_level": VisionConfidenceLevel.HIGH,
        "confidence_score": 0.8,
        "safety": VisionSafetyResult(),
        "model_memory": VisionMemoryCandidate(should_consider=True, reason="用户常发食物照片"),
        "has_ocr_text": False,
        "people_count": None,
    }
    kwargs.update(overrides)
    return decide_memory(**kwargs)


def test_sensitive_image_is_never_remembered():
    decision = _decide(safety=VisionSafetyResult(has_sensitive_content=True, risk_level="high"))
    assert decision.allow is False
    assert decision.reason_code == "sensitive_content"


def test_unconfirmed_character_identity_is_not_remembered():
    decision = _decide(image_type=VisionImageType.CHARACTER, identity_candidate_exists=True)
    assert decision.allow is False
    assert decision.reason_code == "unconfirmed_character_identity"


def test_confirmed_character_becomes_topic_memory():
    decision = _decide(image_type=VisionImageType.CHARACTER, identity_confirmed=True)
    assert decision.allow is True
    assert decision.reason_code == "confirmed_character_identity"
    assert decision.categories == ["topic"]


def test_document_and_screenshot_are_transient():
    document = _decide(image_type=VisionImageType.DOCUMENT, has_ocr_text=True)
    assert document.allow is False
    assert document.reason_code == "transient_document_image"
    assert "OCR" in document.reason

    screenshot = _decide(image_type=VisionImageType.SCREENSHOT)
    assert screenshot.allow is False
    assert screenshot.reason_code == "transient_document_image"


def test_daily_scene_requires_model_opinion_and_confidence():
    assert _decide().allow is True

    no_opinion = _decide(model_memory=VisionMemoryCandidate(should_consider=False))
    assert no_opinion.allow is False
    assert no_opinion.reason_code == "model_not_considering"

    low = _decide(confidence_level=VisionConfidenceLevel.LOW, confidence_score=0.4)
    assert low.allow is False
    assert low.reason_code == "low_confidence_scene"


def test_people_in_photo_block_identity_speculation():
    decision = _decide(people_count=2, identity_candidate_exists=True)
    assert decision.allow is False
    assert decision.reason_code == "possible_real_person_identity"


def test_unknown_image_type_is_not_remembered():
    decision = _decide(image_type="unknown")
    assert decision.allow is False
    assert decision.reason_code == "unknown_image_type"