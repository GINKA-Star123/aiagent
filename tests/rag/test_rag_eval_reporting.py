from __future__ import annotations

import json

from aiagent.knowledge.evaluation.models import (
    RAGEvalCaseResult,
    RAGEvalStageSummary,
    RAGEvalSummary,
    StageCheck,
)
from aiagent.knowledge.evaluation.report import build_report, render_markdown, write_report


def test_report_writes_json_markdown_and_failures(tmp_path) -> None:
    summary = RAGEvalSummary(
        suite="smoke",
        total=1,
        passed=1,
        failed=0,
        pass_rate=1.0,
        stage_summaries=[
            RAGEvalStageSummary(
                stage="end_to_end",
                total=1,
                passed=1,
                failed=0,
                pass_rate=1.0,
            )
        ],
        metrics={"retrieval_recall": 1.0, "rerank_recall": 1.0},
    )
    results = [
        RAGEvalCaseResult(
            case_id="demo_case",
            suite="smoke",
            category="character",
            query="demo",
            passed=True,
            stages={"retrieval": StageCheck(passed=True)},
        )
    ]
    chunk_summary = RAGEvalStageSummary(
        stage="chunking",
        total=1,
        passed=1,
        failed=0,
        pass_rate=1.0,
    )

    report = build_report(
        suite="smoke",
        summary=summary,
        results=results,
        chunk_summary=chunk_summary,
        chunk_results=[],
        index_audit=StageCheck(passed=True),
        thresholds={"min_pass_rate": -1.0},
        cases_path="cases.jsonl",
        chunk_cases_path="chunk_cases.jsonl",
        knowledge_dir="data/knowledge/public",
        corpus={"file_count": 1, "total_bytes": 1, "sha256": "x"},
    )

    markdown = render_markdown(report)
    assert "# RAG Evaluation Report" in markdown
    assert "end_to_end" in markdown

    paths = write_report(report, output_dir=tmp_path, prefix="demo")
    assert set(paths) == {"json", "markdown", "failures_jsonl"}

    payload = json.loads((tmp_path / "demo_report.json").read_text(encoding="utf-8"))
    assert payload["summary"]["suite"] == "smoke"
    assert payload["ok"] is True
