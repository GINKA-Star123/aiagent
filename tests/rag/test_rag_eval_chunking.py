from __future__ import annotations

import os
from pathlib import Path

from aiagent.knowledge.evaluation.dataset import load_chunk_cases
from aiagent.knowledge.evaluation.runner import evaluate_chunking

FIXTURE_DIR = Path("tests/fixtures/rag_eval")
CHUNK_CASES = FIXTURE_DIR / "chunk_cases.jsonl"
KNOWLEDGE_DIR = Path("data/knowledge/public")


def test_chunking_and_index_contract(rag_eval_pipeline) -> None:
    cases = load_chunk_cases(CHUNK_CASES)
    summary, results, index_audit = evaluate_chunking(
        rag_eval_pipeline.documents,
        cases,
        knowledge_dir=KNOWLEDGE_DIR,
        pipeline=rag_eval_pipeline,
    )

    assert index_audit.passed, index_audit.failures
    assert summary.total == len(cases) + 1
    assert summary.passed >= 1
    assert all(result.case_id for result in results)

    minimum = float(os.getenv("RAG_EVAL_MIN_CHUNK_PASS_RATE", "0.0"))
    assert summary.pass_rate >= minimum, {
        "pass_rate": summary.pass_rate,
        "failures": summary.failures,
    }
