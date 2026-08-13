from aiagent.graphs.graph_model import CharacterCandidate, VisionConfidenceLevel
from aiagent.vision.confidence_policy import VisionConfidencePolicy


def _candidate(confidence: float, score: float | None = None) -> CharacterCandidate:
    return CharacterCandidate(
        character_id="char_a",
        name="测试角色",
        confidence=confidence,
        score=confidence if score is None else score,
        evidence=["unit evidence"],
    )


def test_character_high_confidence_confirms_candidate():
    image_type, confirmed, report, policy = VisionConfidencePolicy(
        character_confident_score=0.78,
    ).evaluate(
        image_type="character",
        model_confidence=0.8,
        model_reason="unit",
        character_candidates=[_candidate(0.88)],
    )

    assert image_type == "character"
    assert len(confirmed) == 1
    assert report.level in {VisionConfidenceLevel.MEDIUM, VisionConfidenceLevel.HIGH}
    assert policy.active is False
    assert policy.avoid_identity_assertion is False


def test_character_low_confidence_keeps_candidate_unconfirmed():
    image_type, confirmed, report, policy = VisionConfidencePolicy(
        character_confident_score=0.78,
        low_margin=0.12,
    ).evaluate(
        image_type="character",
        model_confidence=0.7,
        model_reason="unit",
        character_candidates=[_candidate(0.70)],
    )

    assert image_type == "character"
    assert confirmed == []
    assert report.level == VisionConfidenceLevel.LOW
    assert policy.active is True
    assert policy.avoid_identity_assertion is True
    assert policy.expose_candidates is True
    assert policy.defer_memory_hint is True


def test_daily_image_uses_model_confidence_not_character_score():
    image_type, confirmed, report, policy = VisionConfidencePolicy(
        scene_confident_score=0.55,
    ).evaluate(
        image_type="daily",
        model_confidence=0.72,
        model_reason="scene is clear",
        character_candidates=[],
    )

    assert image_type == "daily"
    assert confirmed == []
    assert report.score == 0.72
    assert report.source == "scene_understanding"
    assert policy.active is False
    assert policy.avoid_identity_assertion is False


def test_unknown_image_with_no_confidence_is_uncertain():
    image_type, confirmed, report, policy = VisionConfidencePolicy().evaluate(
        image_type="unknown",
        model_confidence=0.1,
        model_reason="unclear",
        character_candidates=[],
    )

    assert image_type == "unknown"
    assert confirmed == []
    assert report.level == VisionConfidenceLevel.UNCERTAIN
    assert policy.active is True

def test_character_low_confidence_suppresses_live2d_override_and_uses_conservative_reply():
    image_type, confirmed, report, policy = VisionConfidencePolicy(
        character_confident_score=0.78,
        low_margin=0.12,
    ).evaluate(
        image_type="character",
        model_confidence=0.69,
        model_reason="unit",
        character_candidates=[_candidate(0.69)],
    )

    assert image_type == "character"
    assert confirmed == []
    assert report.level == VisionConfidenceLevel.LOW
    assert policy.active is True
    assert policy.avoid_identity_assertion is True
    assert policy.expose_candidates is True
    assert policy.defer_memory_hint is True
    assert policy.suppress_live2d_override is True
    assert policy.use_conservative_wording is True
    assert policy.reply_instruction
    assert "保守" in policy.reply_instruction or "候选" in policy.reply_instruction