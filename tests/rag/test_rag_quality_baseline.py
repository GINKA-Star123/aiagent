from __future__ import annotations

from pathlib import Path

import pytest

from aiagent.knowledge.query_normalizer import normalize_rag_query
from aiagent.knowledge.rag_eval import (
    build_bm25_baseline_pipeline,
    evaluate_cases,
    load_cases,
)


@pytest.mark.skipif(
    not Path("data/knowledge/public").exists(),
    reason="knowledge directory is missing",
)
def test_rag_quality_baseline_passes(tmp_path):
    cases = load_cases("tests/fixtures/rag_eval/cases.jsonl")
    pipeline = build_bm25_baseline_pipeline(
        knowledge_dir="data/knowledge/public",
        docs_index_path=tmp_path / "split_docs.json",
        faiss_dir=tmp_path / "faiss",
    )

    summary, results = evaluate_cases(
        cases,
        retrieve_fn=lambda case: pipeline.debug_retrieve(
            query=normalize_rag_query(case.query),
            top_k=case.top_k,
        ),
    )

    assert summary.total == len(cases)
    assert summary.pass_rate >= 0.75
    assert summary.recall_at_1 >= 0.40
    assert summary.recall_at_3 >= 0.80
    assert summary.mrr >= 0.55
    assert {"character", "workflow", "mixed"} <= {case.category for case in cases}
    assert {"source", "any"} <= {case.match_mode for case in cases}
    assert summary.total == len(cases)
    assert summary.pass_rate >= 0.75
    assert summary.recall_at_1 >= 0.40
    assert summary.recall_at_3 >= 0.80
    assert summary.mrr >= 0.55

    for result in results:
        assert result.case_id
        assert result.query
