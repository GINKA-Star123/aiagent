# tests/unit/test_rag_eval_report.py
from __future__ import annotations

import json

from aiagent.knowledge.rag_eval_models import (
    RAGEvalCase,
    RAGEvalCaseResult,
    RAGEvalHit,
    RAGEvalSummary,
    RAGEvalThresholds,
)
from aiagent.knowledge.rag_eval_report import (
    build_category_summaries,
    build_eval_report,
    render_failures_jsonl,
    render_markdown_report,
    threshold_failures,
)


def test_build_category_summaries_groups_metrics():
    results = [
        RAGEvalCaseResult(
            case_id="c1",
            category="character",
            query="乐正绫是谁",
            passed=True,
            reason="expected_hit_matched",
            best_rank=1,
        ),
        RAGEvalCaseResult(
            case_id="c2",
            category="character",
            query="阿绫代表色",
            passed=False,
            reason="no_expected_hit",
        ),
        RAGEvalCaseResult(
            case_id="c3",
            category="workflow",
            query="直播开场",
            passed=True,
            reason="expected_hit_matched",
            best_rank=2,
        ),
        RAGEvalCaseResult(
            case_id="c4",
            category="negative",
            query="星尘Zero是谁",
            passed=False,
            reason="forbidden_source_matched",
        ),
        RAGEvalCaseResult(
            case_id="c5",
            category="mixed",
            query="墨清弦和苍穹是什么关系",
            passed=True,
            reason="expected_hit_matched",
            best_rank=2,
        ),
    ]

    summaries = build_category_summaries(results)

    by_category = {item.category: item for item in summaries}

    assert by_category["character"].total == 2
    assert by_category["character"].passed == 1
    assert by_category["character"].failed == 1
    assert by_category["character"].pass_rate == 0.5
    assert by_category["character"].recall_at_1 == 0.5
    assert by_category["character"].failure_reasons == {"no_expected_hit": 1}

    assert by_category["workflow"].total == 1
    assert by_category["workflow"].passed == 1
    assert by_category["workflow"].mrr == 0.5
    assert by_category["negative"].total == 1
    assert by_category["negative"].failed == 1
    assert by_category["negative"].failure_reasons == {"forbidden_source_matched": 1}

    assert by_category["mixed"].total == 1
    assert by_category["mixed"].passed == 1


def test_threshold_failures_reports_failed_metrics():
    summary = RAGEvalSummary(
        total=10,
        passed=6,
        failed=4,
        pass_rate=0.6,
        recall_at_1=0.3,
        recall_at_3=0.7,
        mrr=0.4,
    )
    thresholds = RAGEvalThresholds(
        min_pass_rate=0.75,
        min_recall_at_1=0.4,
        min_recall_at_3=0.8,
        min_mrr=0.55,
    )

    failures = threshold_failures(summary, thresholds)

    assert len(failures) == 4
    assert any("pass_rate" in item for item in failures)
    assert any("recall_at_1" in item for item in failures)
    assert any("recall_at_3" in item for item in failures)
    assert any("mrr" in item for item in failures)


def test_build_eval_report_and_markdown_contains_failures():
    cases = [
        RAGEvalCase(
            case_id="yzl_identity",
            category="character",
            query="乐正绫是谁",
            expected_source_paths=["YueZhengling.md"],
        ),
        RAGEvalCase(
            case_id="streaming_basics",
            category="workflow",
            query="直播开场应该怎么做",
            expected_source_paths=["streaming_basics.md"],
        ),
    ]

    results = [
        RAGEvalCaseResult(
            case_id="yzl_identity",
            category="character",
            query="乐正绫是谁",
            passed=True,
            reason="expected_hit_matched",
            best_rank=1,
            matched_source_path="YueZhengling.md",
        ),
        RAGEvalCaseResult(
            case_id="streaming_basics",
            category="workflow",
            query="直播开场应该怎么做",
            passed=False,
            reason="no_expected_hit",
            top_hits=[
                RAGEvalHit(
                    title="producer",
                    source_path="producer.md",
                    preview="producer intro",
                )
            ],
        ),
    ]

    summary = RAGEvalSummary(
        total=2,
        passed=1,
        failed=1,
        pass_rate=0.5,
        recall_at_1=0.5,
        recall_at_3=0.5,
        mrr=0.5,
    )
    thresholds = RAGEvalThresholds()

    report = build_eval_report(
        cases=cases,
        summary=summary,
        results=results,
        thresholds=thresholds,
        cases_path="tests/fixtures/rag_eval/cases.jsonl",
        knowledge_dir="data/knowledge/public",
    )

    markdown = render_markdown_report(report)
    failures_jsonl = render_failures_jsonl(report.results)

    assert report.ok is False
    assert report.threshold_failures
    assert "streaming_basics" in markdown
    assert "no_expected_hit" in markdown

    failure_lines = [line for line in failures_jsonl.splitlines() if line.strip()]
    assert len(failure_lines) == 1

    payload = json.loads(failure_lines[0])
    assert payload["case_id"] == "streaming_basics"
    assert payload["passed"] is False
    assert report.metadata["case_count"] == 2
    assert report.metadata["category_count"] == 2

