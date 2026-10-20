from __future__ import annotations

import argparse
import json
import sys

from aiagent.knowledge.evaluation.dataset import (
    corpus_snapshot,
    load_chunk_cases,
    load_query_cases,
    validate_chunk_cases,
    validate_query_cases,
)
from aiagent.knowledge.evaluation.models import RAGEvalStageSummary
from aiagent.knowledge.evaluation.pipeline import build_eval_pipeline
from aiagent.knowledge.evaluation.report import build_report, render_markdown, write_report
from aiagent.knowledge.evaluation.runner import evaluate_chunking, evaluate_query_cases


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the complete RAG evaluation: chunking -> index -> retrieval -> rerank -> injection -> prompt."
    )
    parser.add_argument(
        "--cases",
        default="tests/fixtures/rag_eval/cases.jsonl",
        help="Query-level evaluation cases (JSONL).",
    )
    parser.add_argument(
        "--chunk-cases",
        default="tests/fixtures/rag_eval/chunk_cases.jsonl",
        help="Chunk-level evaluation cases (JSONL).",
    )
    parser.add_argument(
        "--suite",
        default="all",
        choices=["smoke", "core", "hard", "all"],
        help="Which query suite to evaluate.",
    )
    parser.add_argument(
        "--knowledge-dir",
        default="data/knowledge/public",
        help="Knowledge directory.",
    )
    parser.add_argument(
        "--docs-index-path",
        default="data/cache/knowledge/rag_eval_v2_split_docs.json",
        help="Split-docs cache path for this evaluation run.",
    )
    parser.add_argument(
        "--faiss-dir",
        default="data/cache/knowledge/rag_eval_v2_faiss",
        help="FAISS cache path (unused by the BM25-only eval).",
    )
    parser.add_argument(
        "--report-dir",
        default="data/cache/knowledge/reports/rag_eval_v2",
        help="Directory for JSON / Markdown / failures reports.",
    )
    parser.add_argument(
        "--report-prefix",
        default="rag_eval",
        help="Report filename prefix.",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write JSON, Markdown and failures JSONL reports.",
    )
    parser.add_argument(
        "--print-markdown",
        action="store_true",
        help="Print the Markdown report.",
    )
    parser.add_argument(
        "--show-results",
        action="store_true",
        help="Print per-case results as JSON.",
    )
    parser.add_argument(
        "--show-category-summary",
        action="store_true",
        help="Print per-category pass rates.",
    )
    parser.add_argument(
        "--no-chunk-audit",
        action="store_true",
        help="Skip chunk-level and index-level checks.",
    )
    parser.add_argument(
        "--min-pass-rate", type=float, default=-1.0, help="Minimum end-to-end pass rate."
    )
    parser.add_argument(
        "--min-retrieval-recall",
        type=float,
        default=-1.0,
        help="Minimum retrieval recall on positive cases.",
    )
    parser.add_argument(
        "--min-rerank-recall",
        type=float,
        default=-1.0,
        help="Minimum rerank recall (expected doc in final top-k).",
    )
    parser.add_argument(
        "--min-rerank-top1",
        type=float,
        default=-1.0,
        help="Minimum rerank top-1 accuracy.",
    )
    parser.add_argument(
        "--min-injection-accuracy",
        type=float,
        default=-1.0,
        help="Minimum injection-decision accuracy.",
    )
    parser.add_argument(
        "--min-prompt-pass-rate",
        type=float,
        default=-1.0,
        help="Minimum prompt/citation contract pass rate.",
    )
    parser.add_argument(
        "--min-chunk-pass-rate",
        type=float,
        default=-1.0,
        help="Minimum chunking/index pass rate.",
    )
    return parser


def _empty_chunk_summary() -> RAGEvalStageSummary:
    return RAGEvalStageSummary(
        stage="chunking",
        total=0,
        passed=0,
        failed=0,
        pass_rate=0.0,
        failures={},
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = _build_parser().parse_args(argv)

    cases = load_query_cases(args.cases, suite=args.suite)
    validate_query_cases(cases, args.knowledge_dir)

    chunk_cases = []
    if not args.no_chunk_audit:
        chunk_cases = load_chunk_cases(args.chunk_cases)
        validate_chunk_cases(chunk_cases, args.knowledge_dir)

    corpus = corpus_snapshot(args.knowledge_dir)

    pipeline = build_eval_pipeline(
        knowledge_dir=args.knowledge_dir,
        docs_index_path=args.docs_index_path,
        faiss_dir=args.faiss_dir,
    )

    if args.no_chunk_audit:
        chunk_summary = _empty_chunk_summary()
        chunk_results = []
        from aiagent.knowledge.evaluation.models import StageCheck

        index_audit = StageCheck(passed=True, details={"skipped": True})
    else:
        chunk_summary, chunk_results, index_audit = evaluate_chunking(
            pipeline.documents,
            chunk_cases,
            knowledge_dir=args.knowledge_dir,
            pipeline=pipeline,
        )

    summary, results = evaluate_query_cases(
        pipeline,
        cases,
        suite=args.suite,
    )

    thresholds = {
        "min_pass_rate": args.min_pass_rate,
        "min_retrieval_recall": args.min_retrieval_recall,
        "min_rerank_recall": args.min_rerank_recall,
        "min_rerank_top1": args.min_rerank_top1,
        "min_injection_accuracy": args.min_injection_accuracy,
        "min_prompt_pass_rate": args.min_prompt_pass_rate,
        "min_chunk_pass_rate": args.min_chunk_pass_rate,
    }

    report = build_report(
        suite=args.suite,
        summary=summary,
        results=results,
        chunk_summary=chunk_summary,
        chunk_results=chunk_results,
        index_audit=index_audit,
        thresholds=thresholds,
        cases_path=args.cases,
        chunk_cases_path=args.chunk_cases if not args.no_chunk_audit else "",
        knowledge_dir=args.knowledge_dir,
        corpus=corpus,
    )

    print(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2))

    if args.show_category_summary:
        print(
            json.dumps(
                report.metadata.get("category_summaries", []),
                ensure_ascii=False,
                indent=2,
            )
        )

    if args.show_results:
        print(
            json.dumps(
                [result.model_dump(mode="json") for result in results],
                ensure_ascii=False,
                indent=2,
            )
        )

    if args.print_markdown:
        print(render_markdown(report))

    if args.write_report:
        paths = write_report(
            report,
            output_dir=args.report_dir,
            prefix=args.report_prefix,
        )
        print(
            json.dumps(
                {"ok": True, "report_paths": paths},
                ensure_ascii=False,
                indent=2,
            )
        )

    if report.threshold_failures:
        for failure in report.threshold_failures:
            print(f"THRESHOLD FAILURE: {failure}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
