import pytest

from aiagent.knowledge.evaluation.answer import evaluate_answer, evaluate_answer_batch


@pytest.mark.parametrize(("answer", "passed", "failures"), [
    ("设定：代表色为星蓝。", True, []),
    ("设定：代表色未知。", False, ["required_term_missing:0"]),
    ("星蓝，也可能是暗红。", False, ["forbidden_term_present:0"]),
    ("", False, ["answer_empty", "required_term_missing:0"]),
])
def test_answer_contrast(answer, passed, failures):
    result = evaluate_answer(
        answer, required_terms=("星蓝",), forbidden_terms=("暗红",),
    )
    assert result.passed is passed
    assert result.failures == failures
    assert result.details["required_term_recall"] == int("星蓝" in answer)


def test_normalization_and_report_serialization():
    result = evaluate_answer("ＡＧＥＮＴ", required_terms=("agent",))
    assert result.model_dump()["passed"] is True


@pytest.mark.parametrize(("required", "forbidden"), [
    ((), ()), ((" ",), ()), (("Agent",), ("ＡＧＥＮＴ",)),
])
def test_invalid_rules(required, forbidden):
    with pytest.raises(ValueError):
        evaluate_answer("答案", required_terms=required, forbidden_terms=forbidden)

CASES = {"color": {"required_terms": ("星蓝",), "forbidden_terms": ("暗红",)}}


@pytest.mark.parametrize(("answer", "passed"), [("星蓝", True), ("暗红", False), ("", False)])
def test_batch_contrast(answer, passed):
    report = evaluate_answer_batch(CASES, {"color": answer})
    assert report["ok"] is passed
    assert report["passed"] == int(passed)
    assert report["failed"] == int(not passed)
    assert report["pass_rate"] == float(passed)


@pytest.mark.parametrize("answers", [{}, {"unknown": "星蓝"}, {"color": "星蓝", "extra": ""}])
def test_batch_rejects_missing_or_unexpected_answers(answers):
    with pytest.raises(ValueError):
        evaluate_answer_batch(CASES, answers)


def test_batch_validation_and_reproducibility():
    with pytest.raises(ValueError):
        evaluate_answer_batch({}, {})
    with pytest.raises(TypeError):
        evaluate_answer_batch(CASES, {"color": None})
    first = evaluate_answer_batch(CASES, {"color": "星蓝"})
    second = evaluate_answer_batch(CASES, {"color": "暗红"})
    assert first["dataset_sha256"] == second["dataset_sha256"]
    assert first["results"]["color"]["passed"] is True
    assert second["results"]["color"]["passed"] is False
