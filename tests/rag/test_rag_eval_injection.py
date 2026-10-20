from __future__ import annotations

import os
from pathlib import Path

from aiagent.knowledge.evaluation.dataset import load_query_cases
from aiagent.knowledge.evaluation.runner import evaluate_query_cases

CASES = Path("tests/fixtures/rag_eval/cases.jsonl")


def test_smoke_injection_and_prompt_contract(rag_eval_pipeline) -> None:
    cases = load_query_cases(CASES, suite="smoke")
    summary, results = evaluate_query_cases(
        rag_eval_pipeline,
        cases,
        suite="smoke",
    )

    injection_min = float(os.getenv("RAG_EVAL_MIN_INJECTION_ACCURACY", "0.0"))
    prompt_min = float(os.getenv("RAG_EVAL_MIN_PROMPT_PASS_RATE", "0.0"))

    assert summary.metrics["injection_accuracy"] >= injection_min, summary.metrics
    assert summary.metrics["prompt_pass_rate"] >= prompt_min, summary.metrics

    for result in results:
        assert "injection" in result.stages
        assert "prompt" in result.stages
        injection = result.stages["injection"].details
        assert "should_inject" in injection
        assert "citation_count" in injection
