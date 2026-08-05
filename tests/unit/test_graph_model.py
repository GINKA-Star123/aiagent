from aiagent.graphs.graph_model import VisionSafetyResult
from aiagent.graphs.graph_model import (
    VisionAnalyzeResult,
    VisionConfidenceLevel,
)

def test_vision_safety_accepts_canonical_sensitive_field():
    result = VisionSafetyResult(has_sensitive_content=True, risk_level="low")

    assert result.has_sensitive_content is True
    assert result.model_dump()["has_sensitive_content"] is True
    assert result.risk_level == "low"


def test_vision_safety_accepts_legacy_sentitive_field():
    result = VisionSafetyResult(has_sensitive_content=True)

    assert result.has_sensitive_content is True

def test_vision_result_includes_confidence_schema_defaults():
    result = VisionAnalyzeResult(
        image_id="img_unit",
        image_path="unit.png",
    )

    assert result.confidence_report.level == VisionConfidenceLevel.UNCERTAIN
    assert result.low_confidence_policy.active is True
    assert result.character_candidates == []
    assert result.recognized_characters == []

    dumped = result.model_dump(mode="json")
    assert dumped["image_type"] == "unknown"
    assert dumped["confidence_report"]["level"] == "uncertain"
    assert dumped["low_confidence_policy"]["use_conservative_wording"] is True
