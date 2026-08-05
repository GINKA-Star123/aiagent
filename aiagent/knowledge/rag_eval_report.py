# aiagent/knowledge/rag_eval_report.py
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from aiagent.knowledge.rag_eval_models import (
    RAGEvalCase,
    RAGEvalCaseResult,
    RAGEvalCategorySummary,
    RAGEvalReport,
    RAGEvalSummary,
    RAGEvalThresholds,
)


def build_eval_report(
    *,
    cases: list[RAGEvalCase],
    summary: RAGEvalSummary,
    results: list[RAGEvalCaseResult],
    thresholds: RAGEvalThresholds,
    cases_path: str,
    knowledge_dir: str,
    retriever_name: str = "bm25_baseline",
) -> RAGEvalReport:
    failures = threshold_failures(summary, thresholds)

    return RAGEvalReport(
        ok=not failures,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        retriever_name=retriever_name,
        cases_path=cases_path,
        knowledge_dir=knowledge_dir,
        thresholds=thresholds,
        summary=summary,
        category_summaries=build_category_summaries(results),
        results=results,
        threshold_failures=failures,
        metadata={
            "case_count": len(cases),
            "category_count": len({case.category for case in cases}),
        },
    )


def threshold_failures(
    summary: RAGEvalSummary,
    thresholds: RAGEvalThresholds,
) -> list[str]:
    failures: list[str] = []

    if summary.pass_rate < thresholds.min_pass_rate:
        failures.append(
            f"pass_rate {summary.pass_rate:.6f} < {thresholds.min_pass_rate:.6f}"
        )

    if summary.recall_at_1 < thresholds.min_recall_at_1:
        failures.append(
            f"recall_at_1 {summary.recall_at_1:.6f} < {thresholds.min_recall_at_1:.6f}"
        )

    if summary.recall_at_3 < thresholds.min_recall_at_3:
        failures.append(
            f"recall_at_3 {summary.recall_at_3:.6f} < {thresholds.min_recall_at_3:.6f}"
        )

    if summary.mrr < thresholds.min_mrr:
        failures.append(
            f"mrr {summary.mrr:.6f} < {thresholds.min_mrr:.6f}"
        )

    return failures


def build_category_summaries(
    results: list[RAGEvalCaseResult],
) -> list[RAGEvalCategorySummary]:
    grouped: dict[str, list[RAGEvalCaseResult]] = defaultdict(list)

    for result in results:
        grouped[result.category or "general"].append(result)

    summaries = [
        _category_summary(category, category_results)
        for category, category_results in sorted(grouped.items())
    ]
    return summaries


def render_markdown_report(report: RAGEvalReport) -> str:
    lines: list[str] = [
        "# RAG Quality Report",
        "",
        f"- generated_at: `{report.generated_at}`",
        f"- retriever_name: `{report.retriever_name}`",
        f"- cases_path: `{report.cases_path}`",
        f"- knowledge_dir: `{report.knowledge_dir}`",
        f"- ok: `{str(report.ok).lower()}`",
        "",
        "## Summary",
        "",
        "| metric | value | threshold |",
        "| --- | ---: | ---: |",
        f"| total | {report.summary.total} | - |",
        f"| passed | {report.summary.passed} | - |",
        f"| failed | {report.summary.failed} | - |",
        f"| pass_rate | {report.summary.pass_rate:.6f} | {report.thresholds.min_pass_rate:.6f} |",
        f"| recall_at_1 | {report.summary.recall_at_1:.6f} | {report.thresholds.min_recall_at_1:.6f} |",
        f"| recall_at_3 | {report.summary.recall_at_3:.6f} | {report.thresholds.min_recall_at_3:.6f} |",
        f"| mrr | {report.summary.mrr:.6f} | {report.thresholds.min_mrr:.6f} |",
        f"| avg_best_rank | {report.summary.avg_best_rank:.6f} | - |",
        "",
        "## Category Summary",
        "",
        "| category | total | passed | failed | pass_rate | recall_at_1 | recall_at_3 | mrr |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for item in report.category_summaries:
        lines.append(
            "| "
            f"{item.category} | "
            f"{item.total} | "
            f"{item.passed} | "
            f"{item.failed} | "
            f"{item.pass_rate:.6f} | "
            f"{item.recall_at_1:.6f} | "
            f"{item.recall_at_3:.6f} | "
            f"{item.mrr:.6f} |"
        )

    lines.extend(["", "## Threshold Failures", ""])

    if report.threshold_failures:
        lines.extend(f"- {item}" for item in report.threshold_failures)
    else:
        lines.append("- none")

    lines.extend(["", "## Failed Cases", ""])

    failed_results = [result for result in report.results if not result.passed]
    if not failed_results:
        lines.append("- none")
    else:
        lines.extend(
            [
                "| case_id | category | reason | query | top_hit |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for result in failed_results:
            top_hit = result.top_hits[0] if result.top_hits else None
            top_hit_text = ""
            if top_hit is not None:
                top_hit_text = f"{top_hit.title} / {top_hit.source_path}"

            lines.append(
                "| "
                f"{_escape_md(result.case_id)} | "
                f"{_escape_md(result.category)} | "
                f"{_escape_md(result.reason)} | "
                f"{_escape_md(result.query)} | "
                f"{_escape_md(top_hit_text)} |"
            )

    lines.append("")
    return "\n".join(lines)


def render_failures_jsonl(results: list[RAGEvalCaseResult]) -> str:
    lines = [
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
        for result in results
        if not result.passed
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def write_eval_report(
    report: RAGEvalReport,
    output_dir: str | Path,
    *,
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

    markdown_path.write_text(
        render_markdown_report(report),
        encoding="utf-8",
    )

    failures_path.write_text(
        render_failures_jsonl(report.results),
        encoding="utf-8",
    )

    return {
        "json": str(json_path),
        "markdown": str(markdown_path),
        "failures_jsonl": str(failures_path),
    }


def _category_summary(
    category: str,
    results: list[RAGEvalCaseResult],
) -> RAGEvalCategorySummary:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    failed = total - passed

    ranked_passes = [
        result for result in results
        if result.passed and result.best_rank is not None
    ]

    failure_reasons = Counter(
        result.reason for result in results if not result.passed
    )

    return RAGEvalCategorySummary(
        category=category,
        total=total,
        passed=passed,
        failed=failed,
        pass_rate=_ratio(passed, total),
        recall_at_1=_ratio(
            sum(1 for result in ranked_passes if result.best_rank == 1),
            total,
        ),
        recall_at_3=_ratio(
            sum(1 for result in ranked_passes if result.best_rank is not None and result.best_rank <= 3),
            total,
        ),
        mrr=_ratio(
            sum(1.0 / float(result.best_rank) for result in ranked_passes if result.best_rank),
            total,
        ),
        avg_best_rank=_ratio(
            sum(float(result.best_rank) for result in ranked_passes if result.best_rank),
            len(ranked_passes),
        ),
        failure_reasons=dict(sorted(failure_reasons.items())),
    )


def _ratio(numerator: float, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _escape_md(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")