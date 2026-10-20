from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aiagent.knowledge.evaluation.models import (
    ChunkCaseResult,
    RAGEvalCaseResult,
    RAGEvalReport,
    RAGEvalStageSummary,
    RAGEvalSummary,
    StageCheck,
)


def threshold_failures(
    summary: RAGEvalSummary,
    chunk_summary: RAGEvalStageSummary,
    thresholds: dict[str, float],
) -> list[str]:
    checks: list[tuple[str, float, float]] = [
        ("pass_rate", summary.pass_rate, thresholds.get("min_pass_rate", -1.0)),
        (
            "retrieval_recall",
            summary.metrics.get("retrieval_recall", 0.0),
            thresholds.get("min_retrieval_recall", -1.0),
        ),
        (
            "rerank_recall",
            summary.metrics.get("rerank_recall", 0.0),
            thresholds.get("min_rerank_recall", -1.0),
        ),
        (
            "rerank_top1_accuracy",
            summary.metrics.get("rerank_top1_accuracy", 0.0),
            thresholds.get("min_rerank_top1", -1.0),
        ),
        (
            "injection_accuracy",
            summary.metrics.get("injection_accuracy", 0.0),
            thresholds.get("min_injection_accuracy", -1.0),
        ),
        (
            "prompt_pass_rate",
            summary.metrics.get("prompt_pass_rate", 0.0),
            thresholds.get("min_prompt_pass_rate", -1.0),
        ),
        (
            "chunk_pass_rate",
            chunk_summary.pass_rate,
            thresholds.get("min_chunk_pass_rate", -1.0),
        ),
    ]

    failures: list[str] = []
    for name, actual, minimum in checks:
        if minimum >= 0 and actual < minimum:
            failures.append(f"{name} {actual:.6f} < {minimum:.6f}")
    return failures


def build_report(
    *,
    suite: str,
    summary: RAGEvalSummary,
    results: list[RAGEvalCaseResult],
    chunk_summary: RAGEvalStageSummary,
    chunk_results: list[ChunkCaseResult],
    index_audit: StageCheck,
    thresholds: dict[str, float],
    cases_path: str,
    chunk_cases_path: str,
    knowledge_dir: str,
    corpus: dict[str, Any],
) -> RAGEvalReport:
    failures = threshold_failures(summary, chunk_summary, thresholds)
    category_summaries = _category_summaries(results)

    return RAGEvalReport(
        ok=not failures,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        suite=suite,
        cases_path=cases_path,
        chunk_cases_path=chunk_cases_path,
        knowledge_dir=knowledge_dir,
        corpus=corpus,
        summary=summary,
        chunk_summary=chunk_summary,
        chunk_results=chunk_results,
        index_audit=index_audit,
        results=results,
        thresholds=thresholds,
        threshold_failures=failures,
        metadata={
            "query_cases": len(results),
            "chunk_cases": len(chunk_results),
            "category_summaries": category_summaries,
            "stage_failures": {
                item.stage: item.failures for item in summary.stage_summaries
            },
        },
    )


def _category_summaries(results: list[RAGEvalCaseResult]) -> list[dict[str, Any]]:
    grouped: dict[str, list[RAGEvalCaseResult]] = defaultdict(list)
    for result in results:
        grouped[result.category or "general"].append(result)

    summaries: list[dict[str, Any]] = []
    for category, items in sorted(grouped.items()):
        passed = sum(1 for item in items if item.passed)
        summaries.append(
            {
                "category": category,
                "total": len(items),
                "passed": passed,
                "failed": len(items) - passed,
                "pass_rate": round(passed / len(items), 6) if items else 0.0,
            }
        )
    return summaries


def render_markdown(report: RAGEvalReport) -> str:
    lines: list[str] = [
        "# RAG Evaluation Report",
        "",
        f"- generated_at: {report.generated_at}",
        f"- suite: {report.suite}",
        f"- cases: {report.cases_path}",
        f"- chunk_cases: {report.chunk_cases_path}",
        f"- knowledge_dir: {report.knowledge_dir}",
        f"- ok: {str(report.ok).lower()}",
        "",
        "## Corpus",
        "",
        f"- files: {report.corpus.get('file_count', '?')}",
        f"- bytes: {report.corpus.get('total_bytes', '?')}",
        f"- sha256: {report.corpus.get('sha256', '?')}",
        "",
        "## Overall",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| total | {report.summary.total} |",
        f"| passed | {report.summary.passed} |",
        f"| failed | {report.summary.failed} |",
        f"| pass_rate | {report.summary.pass_rate:.6f} |",
    ]

    for name, value in sorted(report.summary.metrics.items()):
        lines.append(f"| {name} | {value:.6f} |")

    lines.extend(
        [
            "",
            "## Stage Summary",
            "",
            "| stage | total | passed | failed | pass_rate | failure codes |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for item in report.summary.stage_summaries:
        failures = ", ".join(
            f"{key}={value}" for key, value in item.failures.items()
        )
        lines.append(
            f"| {item.stage} | {item.total} | {item.passed} | {item.failed} | "
            f"{item.pass_rate:.6f} | {failures or '-'} |"
        )

    lines.extend(
        [
            "",
            "## Chunking / Index",
            "",
            f"- index_audit: {'pass' if report.index_audit.passed else 'fail'}",
            f"- index_failures: {', '.join(report.index_audit.failures) or '-'}",
            f"- chunk_pass_rate: {report.chunk_summary.pass_rate:.6f} "
            f"({report.chunk_summary.passed}/{report.chunk_summary.total})",
            "",
            "| chunk_case | source | passed | failures |",
            "| --- | --- | --- | --- |",
        ]
    )
    for result in report.chunk_results:
        lines.append(
            f"| {result.case_id} | {result.source_path} | "
            f"{str(result.passed).lower()} | {'; '.join(result.failures) or '-'} |"
        )

    category_summaries = report.metadata.get("category_summaries", [])
    lines.extend(
        [
            "",
            "## Category Summary",
            "",
            "| category | total | passed | failed | pass_rate |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in category_summaries:
        lines.append(
            f"| {item['category']} | {item['total']} | {item['passed']} | "
            f"{item['failed']} | {item['pass_rate']:.6f} |"
        )

    lines.extend(["", "## Threshold Failures", ""])
    if report.threshold_failures:
        lines.extend(f"- {failure}" for failure in report.threshold_failures)
    else:
        lines.append("- none")

    lines.extend(["", "## Failed Query Cases", ""])
    failed_results = [result for result in report.results if not result.passed]
    if not failed_results:
        lines.append("- none")
    else:
        lines.extend(
            [
                "| case_id | category | stage failures |",
                "| --- | --- | --- |",
            ]
        )
        for result in failed_results:
            stage_failures = "; ".join(
                f"{stage}: {', '.join(check.failures)}"
                for stage, check in result.stages.items()
                if check.failures
            )
            if result.error:
                stage_failures = f"error: {result.error}; {stage_failures}"
            lines.append(
                f"| {result.case_id} | {result.category} | "
                f"{_escape_md(stage_failures)} |"
            )

    lines.append("")
    return "\n".join(lines)


def render_failures_jsonl(report: RAGEvalReport) -> str:
    records: list[dict[str, Any]] = []
    for result in report.results:
        if result.passed:
            continue
        records.append({"kind": "query", **result.model_dump(mode="json")})
    for result in report.chunk_results:
        if result.passed:
            continue
        records.append({"kind": "chunk", **result.model_dump(mode="json")})
    if not records:
        return ""
    return "\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n"


def write_report(
    report: RAGEvalReport,
    *,
    output_dir: str | Path,
    prefix: str = "rag_eval",
) -> dict[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    json_path = target / f"{prefix}_report.json"
    markdown_path = target / f"{prefix}_report.md"
    failures_path = target / f"{prefix}_failures.jsonl"

    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    failures_path.write_text(render_failures_jsonl(report), encoding="utf-8")

    return {
        "json": str(json_path),
        "markdown": str(markdown_path),
        "failures_jsonl": str(failures_path),
    }


def _escape_md(value: str) -> str:
    return str(value).replace("|", "&#124;").replace(chr(10), " ")
