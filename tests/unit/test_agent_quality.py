from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from aiagent.knowledge.evaluation import agent_quality as quality
from aiagent.knowledge.evaluation.answer import evaluate_answer
from aiagent.persona.persona_loader import PersonaLoader

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "tests/fixtures/agent_eval/v1.json"
PERSONA = ROOT / "tests/fixtures/runtime/persona/yzl/persona.yaml"


@pytest.fixture
def dataset():
    return quality.load_dataset(DATASET)


def test_fixture_covers_five_domains_and_oracles(dataset):
    assert {case.domain for case in dataset.answer_cases} == quality.DOMAINS
    assert len(dataset.retrieval_cases) == 5
    assert len(dataset.answer_cases) == 12
    for case in dataset.answer_cases:
        assert evaluate_answer(case.reference_answer, **case.rules()).passed
        assert not evaluate_answer(case.contrast_answer, **case.rules()).passed


def test_answer_context_defaults_to_empty_when_omitted():
    payload = quality.read_json(DATASET)["answer_cases"][0]
    payload.pop("context", None)

    case = quality.AnswerCase.model_validate(payload)

    assert case.context == ""


@pytest.mark.parametrize("context", ["", "合成场景补充。", "x" * 5000])
def test_answer_context_preserves_valid_text(context):
    payload = quality.read_json(DATASET)["answer_cases"][0]
    payload["context"] = context

    case = quality.AnswerCase.model_validate(payload)

    assert case.context == context


@pytest.mark.parametrize("context", [None, 123, [], {}, "x" * 5001])
def test_answer_context_rejects_invalid_type_or_length(context):
    payload = quality.read_json(DATASET)["answer_cases"][0]
    payload["context"] = context

    with pytest.raises(ValidationError) as exc_info:
        quality.AnswerCase.model_validate(payload)

    assert any(error["loc"] == ("context",) for error in exc_info.value.errors())


def test_duplicate_json_keys_are_rejected(tmp_path):
    source = tmp_path / "duplicate.json"
    source.write_text('{"version":"first","version":"second"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        quality.read_json(source)


@pytest.mark.parametrize("mutation", [
    "path_traversal", "duplicate_retrieval", "duplicate_answer", "missing_domain",
    "missing_link", "unknown_link", "missing_vision", "missing_stage",
    "blank_query", "blank_rule", "contradictory_rule", "bad_reference", "bad_contrast",
])
def test_invalid_dataset_is_rejected(dataset, mutation):
    payload = deepcopy(dataset.model_dump(mode="json"))
    if mutation == "path_traversal":
        payload["documents"]["../escape.txt"] = "must not be written"
    elif mutation == "duplicate_retrieval":
        payload["retrieval_cases"].append(deepcopy(payload["retrieval_cases"][0]))
    elif mutation == "duplicate_answer":
        payload["answer_cases"].append(deepcopy(payload["answer_cases"][0]))
    elif mutation == "missing_domain":
        payload["answer_cases"] = [case for case in payload["answer_cases"] if case["domain"] != "persona"]
    elif mutation == "missing_link":
        payload["answer_cases"][0]["retrieval_case_id"] = None
    elif mutation == "unknown_link":
        payload["answer_cases"][0]["retrieval_case_id"] = "not-present"
    elif mutation == "missing_vision":
        next(case for case in payload["answer_cases"] if case["domain"] == "vision")["vision"] = None
    elif mutation == "missing_stage":
        payload["retrieval_cases"][0]["stages"] = ["retrieval"]
    elif mutation == "blank_query":
        payload["answer_cases"][0]["query"] = " "
    elif mutation == "blank_rule":
        payload["answer_cases"][0]["required_terms"] = [" "]
    elif mutation == "contradictory_rule":
        payload["answer_cases"][0]["forbidden_terms"] = ["星蓝"]
    elif mutation == "bad_reference":
        payload["answer_cases"][0]["reference_answer"] = "暗红"
    elif mutation == "bad_contrast":
        payload["answer_cases"][0]["contrast_answer"] = "星蓝"
    with pytest.raises((ValueError, ValidationError)):
        quality.AgentDataset.model_validate(payload)


def test_synthetic_retrieval_baseline_and_wrong_top1_contrast(dataset, tmp_path):
    pipeline = quality.build_synthetic_pipeline(dataset, tmp_path)
    actual = quality.evaluate_retrieval(dataset, pipeline)
    assert actual["ok"], actual
    assert actual["summary"]["total"] == 5
    assert all(row["passed"] for row in actual["results"])

    wrong = dataset.model_copy(deep=True)
    wrong.retrieval_cases[0].rerank.expected_top1_source_paths = ["starlight_alt.txt"]
    contrasted = quality.evaluate_retrieval(wrong, pipeline)
    assert not contrasted["ok"]
    failed = next(row for row in contrasted["results"] if row["case_id"] == "rag-fact")
    assert not failed["stages"]["rerank"]["passed"]


def test_real_prompt_uses_retrieved_context_and_drops_disabled_memory(dataset, tmp_path):
    pipeline = quality.build_synthetic_pipeline(dataset, tmp_path)
    persona = PersonaLoader().load_from_file(PERSONA)
    rag = next(case for case in dataset.answer_cases if case.case_id == "rag_color")
    system, user = quality.build_case_prompt(rag, dataset, pipeline, persona)
    assert "星蓝" in system
    assert "暗红" not in system
    assert user == rag.query
    disabled = next(case for case in dataset.answer_cases if case.case_id == "memory_disabled")
    system, _ = quality.build_case_prompt(disabled, dataset, pipeline, persona)
    assert "榴莲" not in system
    assert "Test Assistant" in system


@pytest.mark.parametrize(("body", "code", "expected"), [
    ('<testcase classname="a" name="ok"/>', 0, True),
    ('<testcase classname="a" name="failed"><failure/></testcase>', 0, False),
    ('<testcase classname="a" name="error"><error/></testcase>', 0, False),
    ('<testcase classname="a" name="skip"><skipped/></testcase>', 0, False),
    ('<testcase classname="a" name="ok"/>', 1, False),
    ("", 0, False),
    ('<testcase name="same"/><testcase name="same"/>', 0, False),
])
def test_junit_pass_fail_skip_and_nonzero_exit(tmp_path, body, code, expected):
    path = tmp_path / "result.xml"
    path.write_text(f"<testsuite>{body}</testsuite>", encoding="utf-8")
    assert quality.parse_junit(path, code)["ok"] is expected


@pytest.mark.parametrize("value", ["1.0", "0.0", "nan", "2.0"])
def test_junit_answer_metric_must_be_finite_and_bounded(tmp_path, value):
    path = tmp_path / "answers.xml"
    path.write_text(
        '<testsuite><testcase classname="answer" name="case"><properties>'
        f'<property name="answer_rule_pass_rate" value="{value}"/>'
        '</properties></testcase></testsuite>', encoding="utf-8",
    )
    result = quality.parse_junit(path, 0)
    if value in {"nan", "2.0"}:
        assert not result["ok"]
    else:
        assert result["answer_rule_samples"] == 1
        assert result["answer_rule_pass_rate"] == float(value)


def test_missing_or_malformed_junit_is_not_success(tmp_path):
    assert not quality.parse_junit(tmp_path / "absent.xml", 0)["ok"]
    path = tmp_path / "broken.xml"
    path.write_text("<not-closed", encoding="utf-8")
    assert not quality.parse_junit(path, 0)["ok"]


def _report():
    return {
        "schema_version": quality.SCHEMA_VERSION, "mode": "offline", "ok": True,
        "dataset_sha256": "dataset", "persona_sha256": "persona", "coverage_sha256": "coverage",
        "metrics": {"rag.retrieval_recall": 1.0},
    }


def test_baseline_detects_regression_and_accepts_equal_scores():
    baseline = _report()
    current = deepcopy(baseline)
    assert quality.compare_reports(current, baseline) == []
    current["metrics"]["rag.retrieval_recall"] = 0.8
    assert quality.compare_reports(current, baseline) == ["rag.retrieval_recall"]
    assert quality.compare_reports(current, baseline, tolerance=0.21) == []


@pytest.mark.parametrize("mutation", ["mode", "dataset_sha256", "persona_sha256", "coverage_sha256", "metrics", "nan", "bool", "failed"])
def test_incompatible_baseline_is_rejected(mutation):
    baseline = _report()
    current = deepcopy(baseline)
    if mutation == "failed":
        baseline["ok"] = False
    elif mutation == "metrics":
        current["metrics"] = {}
    elif mutation == "nan":
        current["metrics"]["rag.retrieval_recall"] = float("nan")
    elif mutation == "bool":
        current["metrics"]["rag.retrieval_recall"] = True
    else:
        current[mutation] = "different"
    with pytest.raises(ValueError):
        quality.compare_reports(current, baseline)


def test_provider_baseline_rejects_model_change():
    baseline = _report()
    baseline.update(mode="provider", generation={
        "provider": "openai", "model": "model-a", "temperature": 0.0,
        "seed_enforced": False, "repeat": 1, "timeout_seconds": 60,
    })
    current = deepcopy(baseline)
    current["generation"]["model"] = "model-b"
    with pytest.raises(ValueError, match="generation settings"):
        quality.compare_reports(current, baseline)


class _StrictService:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0

    def build_messages(self, *, system_prompt, user_text):
        return [system_prompt, user_text]

    def invoke_messages_strict(self, messages):
        assert len(messages) == 2
        self.calls += 1
        value = next(self.outputs)
        if isinstance(value, Exception):
            raise value
        return value


def test_provider_strict_success_repeat_and_default_redaction(dataset, monkeypatch):
    monkeypatch.setattr(quality, "build_case_prompt", lambda *args: ("system", "user"))
    service = _StrictService([case.reference_answer for case in dataset.answer_cases for _ in range(2)])
    result = quality.evaluate_provider(dataset, None, None, service, repeat=2)
    assert result["ok"]
    assert result["total"] == 24
    assert result["logical_generation_calls"] == service.calls == 24
    assert all(key.endswith(("@1", "@2")) for key in result["results"])
    assert "raw_answers" not in result
    assert set(result["by_domain"]) == quality.DOMAINS
    assert all(value == 1.0 for value in result["by_domain"].values())


@pytest.mark.parametrize("kind", ["wrong", "empty", "timeout"])
def test_provider_wrong_empty_and_timeout_never_fall_back(dataset, monkeypatch, kind):
    monkeypatch.setattr(quality, "build_case_prompt", lambda *args: ("system", "user"))
    if kind == "wrong":
        outputs = [case.contrast_answer for case in dataset.answer_cases]
    elif kind == "empty":
        outputs = [" "] * len(dataset.answer_cases)
    else:
        outputs = [TimeoutError("secret-do-not-log")] * len(dataset.answer_cases)
    result = quality.evaluate_provider(dataset, None, None, _StrictService(outputs))
    assert not result["ok"]
    assert result["passed"] == 0
    assert "secret-do-not-log" not in json.dumps(result)
    expected_stage = "answer_rules" if kind == "wrong" else "generation"
    assert all(row["details"]["error_stage"] == expected_stage for row in result["results"].values())


def test_provider_context_error_does_not_call_generation(dataset, monkeypatch):
    def fail_context(*args):
        raise ValueError("secret-context")

    monkeypatch.setattr(quality, "build_case_prompt", fail_context)
    service = _StrictService([])
    result = quality.evaluate_provider(dataset, None, None, service)
    assert not result["ok"]
    assert service.calls == result["logical_generation_calls"] == 0
    assert all(row["details"]["error_stage"] == "context" for row in result["results"].values())
    assert "secret-context" not in json.dumps(result)


def test_raw_answers_require_explicit_opt_in(dataset, monkeypatch):
    monkeypatch.setattr(quality, "build_case_prompt", lambda *args: ("system", "user"))
    result = quality.evaluate_provider(
        dataset, None, None, _StrictService([case.reference_answer for case in dataset.answer_cases]),
        include_answers=True,
    )
    assert len(result["raw_answers"]) == 12


def test_reports_archive_failures_and_write_empty_jsonl_for_success(tmp_path):
    report = _report()
    report["ok"] = False
    report["checks"] = {"memory": {"ok": False, "results": [
        {"case_id": "write_guard", "status": "failed"},
    ]}}
    quality.write_reports(report, tmp_path)
    assert quality.read_json(tmp_path / "report.json")["ok"] is False
    failures = [json.loads(line) for line in (tmp_path / "failures.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(row.get("case_id") == "write_guard" for row in failures)
    quality.write_reports({"ok": True, "checks": {}}, tmp_path)
    assert (tmp_path / "failures.jsonl").read_text(encoding="utf-8") == ""


def test_cli_offline_writes_report_without_recursive_pytest(dataset, monkeypatch, tmp_path):
    monkeypatch.setattr(quality, "build_synthetic_pipeline", lambda *args: object())
    monkeypatch.setattr(quality, "evaluate_retrieval", lambda *args: {
        "ok": True, "summary": {"metrics": {
            name: 1.0 for name in ("retrieval_recall", "rerank_recall", "rerank_top1_accuracy", "injection_accuracy", "prompt_pass_rate")
        }}, "results": [],
    })
    monkeypatch.setattr(quality, "run_offline_groups", lambda *args: {
        name: {"ok": True, "pass_rate": 1.0, "answer_rule_pass_rate": 1.0,
               "results": [{"case_id": name, "status": "passed"}]}
        for name in quality.offline_groups()
    })
    assert quality.main(["--mode", "offline", "--dataset", str(DATASET), "--report-root", str(tmp_path)]) == 0
    reports = list(tmp_path.glob("*/report.json"))
    assert len(reports) == 1
    saved = quality.read_json(reports[0])
    assert saved["ok"]
    assert saved["metrics"]["answers.template_answer_rule_pass_rate"] == 1.0


def test_cli_provider_rejects_mock_configuration(monkeypatch, tmp_path):
    from config.settings import Settings

    monkeypatch.setattr(Settings, "model_copy", lambda self, **kwargs: self)
    monkeypatch.setenv("ENABLE_MOCK_LLM", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(quality, "build_synthetic_pipeline", lambda *args: object())
    monkeypatch.setattr(quality, "evaluate_retrieval", lambda *args: {
        "ok": True, "summary": {"metrics": {
            name: 1.0 for name in ("retrieval_recall", "rerank_recall", "rerank_top1_accuracy", "injection_accuracy", "prompt_pass_rate")
        }}, "results": [],
    })
    code = quality.main(["--mode", "provider", "--report-root", str(tmp_path)])
    assert code == 2
    saved = quality.read_json(next(tmp_path.glob("*/report.json")))
    assert saved["operational_error"]["stage"] == "provider_configuration"
    assert not saved["ok"]
