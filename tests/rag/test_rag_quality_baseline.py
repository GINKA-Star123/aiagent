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
    """BM25 基线检索质量门禁。

    阈值取自 2026 实测值（32 条用例：pass_rate 1.0 / recall@1 0.84375 /
    recall@3 0.96875 / mrr 0.90625），统一留 5%~8% 余量：
    pass_rate 允许 1 条失败，recall@1 允许 2 条未命中，recall@3 允许 3 条，mrr 允许轻微下滑。
    注意：这里用 normalize_rag_query 是刻意为之——评测必须走"线上同款查询归一化"，
    裸 query 只用于 tokenizer 单测。
    """
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
    assert summary.pass_rate >= 0.95
    assert summary.recall_at_1 >= 0.78
    assert summary.recall_at_3 >= 0.90
    assert summary.mrr >= 0.85

    # 用例集必须覆盖三类问题与三种匹配模式（含负例）
    assert {"character", "workflow", "mixed", "group", "negative"} <= {
        case.category for case in cases
    }
    assert {"source", "any", "negative"} <= {case.match_mode for case in cases}

    for result in results:
        assert result.case_id
        assert result.query