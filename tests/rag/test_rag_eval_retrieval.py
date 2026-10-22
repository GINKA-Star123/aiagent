from __future__ import annotations

import os
from pathlib import Path

from aiagent.knowledge.evaluation.dataset import load_query_cases
from aiagent.knowledge.evaluation.runner import evaluate_query_cases

CASES = Path("tests/fixtures/rag_eval/cases.jsonl")


def test_smoke_retrieval_and_rerank(rag_eval_pipeline) -> None:
    cases = load_query_cases(CASES, suite="smoke")
    summary, results = evaluate_query_cases(
        rag_eval_pipeline,
        cases,
        suite="smoke",
    )

    retrieval_min = float(os.getenv("RAG_EVAL_MIN_RETRIEVAL_RECALL", "0.0"))
    rerank_min = float(os.getenv("RAG_EVAL_MIN_RERANK_RECALL", "0.0"))
    top1_min = float(os.getenv("RAG_EVAL_MIN_RERANK_TOP1", "0.0"))

    assert summary.metrics["retrieval_recall"] >= retrieval_min, summary.metrics
    assert summary.metrics["rerank_recall"] >= rerank_min, summary.metrics
    assert summary.metrics["rerank_top1_accuracy"] >= top1_min, summary.metrics
    assert len(results) == len(cases)

    for result in results:
        assert "retrieval" in result.stages
        if result.stages.get("rerank") and not result.stages["rerank"].details.get(
            "skipped"
        ):
            assert result.stages["rerank"].details["top1_source"], (
                result.case_id,
                result.query,
                result.stages["rerank"].failures,
            )
