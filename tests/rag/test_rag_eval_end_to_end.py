from __future__ import annotations

import os
from pathlib import Path

from aiagent.knowledge.evaluation.dataset import load_query_cases
from aiagent.knowledge.evaluation.runner import evaluate_query_cases

CASES = Path("tests/fixtures/rag_eval/cases.jsonl")


def test_smoke_end_to_end(rag_eval_pipeline) -> None:
    cases = load_query_cases(CASES, suite="smoke")
    summary, results = evaluate_query_cases(
        rag_eval_pipeline,
        cases,
        suite="smoke",
    )

    minimum = float(os.getenv("RAG_EVAL_MIN_PASS_RATE", "0.0"))
    assert summary.pass_rate >= minimum, summary.metrics
    assert len(results) == len(cases)
    assert all("end_to_end" in result.stages for result in results)
    assert all(result.passed == result.stages["end_to_end"].passed for result in results)
