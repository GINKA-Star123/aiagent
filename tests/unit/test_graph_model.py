from aiagent.graphs.graph_model import VisionSafetyResult


def test_vision_safety_accepts_canonical_sensitive_field():
    result = VisionSafetyResult(has_sensitive_content=True, risk_level="low")

    assert result.has_sensitive_content is True
    assert result.model_dump()["has_sensitive_content"] is True
    assert result.risk_level == "low"


def test_vision_safety_accepts_legacy_sentitive_field():
    result = VisionSafetyResult(has_sentitive_content=True)

    assert result.has_sensitive_content is True
