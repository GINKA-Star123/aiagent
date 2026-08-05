from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aiagent.knowledge.document_loader import DocumentLoader
from aiagent.knowledge.query_normalizer import normalize_rag_query
from aiagent.knowledge.rag_eval_models import (
    RAGEvalCase,
    RAGEvalCaseResult,
    RAGEvalHit,
    RAGEvalSummary,
    RAGEvalThresholds,
)
from aiagent.knowledge.rag_pipeline import RAGPipeline
from aiagent.knowledge.reranker import SimpleReranker
from aiagent.knowledge.retriever import HybridRetriever
from aiagent.knowledge.rag_eval_report import (
    build_eval_report,
    render_markdown_report,
    threshold_failures,
    write_eval_report,
)

class NullVectorStore:
    """BM25-only eval vector-store stand-in.

    RAG quality baselines should not require embedding models, FAISS state, or
    network access. HybridRetriever still expects a vector store object, so this
    no-op implementation keeps the pipeline shape identical while returning no
    vector candidates.
    """

    def build(self, documents) -> None:
        return None

    def save(self, directory) -> None:
        return None

    def load(self, directory) -> None:
        return None

    def count(self) -> int:
        return 0

    def similarity_search_with_score(self, query: str, k: int = 6):
        return []

    def similarity_search(self, query: str, k: int = 6):
        return []


def load_cases(path: str | Path) -> list[RAGEvalCase]:
    file_path = Path(path)
    cases: list[RAGEvalCase] = []

    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        cases.append(RAGEvalCase.model_validate_json(line))

    return cases


def build_bm25_baseline_pipeline(
    knowledge_dir: str | Path,
    docs_index_path: str | Path,
    faiss_dir: str | Path,
) -> RAGPipeline:
    pipeline = RAGPipeline(
        loader=DocumentLoader(),
        retriever=HybridRetriever(bm25_top_k=8, vector_top_k=0),
        vector_store=NullVectorStore(),  # type: ignore[arg-type]
        reranker=SimpleReranker(),
        knowledge_dir=knowledge_dir,
        docs_index_path=docs_index_path,
        faiss_dir=faiss_dir,
        chunk_size=520,
        chunk_overlap=80,
        final_top_k=4,
    )
    pipeline.build_index(force_rebuild=True)
    return pipeline


def evaluate_case(case: RAGEvalCase, hits: list[dict[str, Any]]) -> RAGEvalCaseResult:
    top_hits = [RAGEvalHit(**hit) for hit in hits[: case.top_k]]
    forbidden = _find_forbidden_hit(case, top_hits)
    if forbidden is not None:
        return RAGEvalCaseResult(
            case_id=case.case_id,
            category=case.category,
            query=case.query,
            passed=False,
            reason="forbidden_source_matched",
            matched_source_path=forbidden.source_path,
            matched_title=forbidden.title,
            top_hits=top_hits,
        )

    best_rank: int | None = None
    best_hit: RAGEvalHit | None = None
    best_terms: list[str] = []
    best_priority = -1

    for index, hit in enumerate(top_hits, start=1):
        source_matched = _source_matches(case, hit)
        title_matched = _title_matches(case, hit)
        matched_terms = _matched_terms(case, hit)

        if not (source_matched or title_matched or matched_terms):
            continue

        priority = 0
        if source_matched:
            priority += 1
        if title_matched:
            priority += 1
        if matched_terms:
            priority += 1

        if priority > best_priority:
            best_priority = priority
            best_rank = index
            best_hit = hit
            best_terms = matched_terms

    if best_hit is None or best_rank is None:
        return RAGEvalCaseResult(
            case_id=case.case_id,
            category=case.category,
            query=case.query,
            passed=False,
            reason="no_expected_hit",
            top_hits=top_hits,
        )

    if best_rank > case.max_rank:
        return RAGEvalCaseResult(
            case_id=case.case_id,
            category=case.category,
            query=case.query,
            passed=False,
            reason="expected_hit_rank_too_low",
            best_rank=best_rank,
            best_score=best_hit.score,
            matched_source_path=best_hit.source_path,
            matched_title=best_hit.title,
            matched_terms=best_terms,
            top_hits=top_hits,
        )

    if case.expected_terms and not best_terms:
        return RAGEvalCaseResult(
            case_id=case.case_id,
            category=case.category,
            query=case.query,
            passed=False,
            reason="expected_source_matched_but_terms_missing",
            best_rank=best_rank,
            best_score=best_hit.score,
            matched_source_path=best_hit.source_path,
            matched_title=best_hit.title,
            top_hits=top_hits,
        )

    return RAGEvalCaseResult(
        case_id=case.case_id,
        category=case.category,
        query=case.query,
        passed=True,
        reason="expected_hit_matched",
        best_rank=best_rank,
        best_score=best_hit.score,
        matched_source_path=best_hit.source_path,
        matched_title=best_hit.title,
        matched_terms=best_terms,
        top_hits=top_hits,
    )


def evaluate_cases(
    cases: list[RAGEvalCase],
    retrieve_fn: Callable[[RAGEvalCase], list[dict[str, Any]]],
) -> tuple[RAGEvalSummary, list[RAGEvalCaseResult]]:
    results = [evaluate_case(case, retrieve_fn(case)) for case in cases]
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    failed = total - passed

    ranked_results = [
        result
        for result in results
        if result.best_rank is not None and result.passed
    ]
    recall_at_1 = _ratio(
        sum(1 for result in ranked_results if result.best_rank == 1),
        total,
    )
    recall_at_3 = _ratio(
        sum(1 for result in ranked_results if result.best_rank is not None and result.best_rank <= 3),
        total,
    )
    mrr = _ratio(
        sum(1.0 / float(result.best_rank) for result in ranked_results if result.best_rank),
        total,
    )
    avg_best_rank = _ratio(
        sum(float(result.best_rank) for result in ranked_results if result.best_rank),
        len(ranked_results),
    )

    summary = RAGEvalSummary(
        total=total,
        passed=passed,
        failed=failed,
        pass_rate=_ratio(passed, total),
        recall_at_1=recall_at_1,
        recall_at_3=recall_at_3,
        mrr=mrr,
        avg_best_rank=avg_best_rank,
        failures=[
            {
                "case_id": result.case_id,
                "query": result.query,
                "reason": result.reason,
            }
            for result in results
            if not result.passed
        ],
    )
    return summary, results


def render_summary(summary: RAGEvalSummary) -> str:
    return json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2)


def render_results(results: list[RAGEvalCaseResult]) -> str:
    return json.dumps(
        [result.model_dump(mode="json") for result in results],
        ensure_ascii=False,
        indent=2,
    )

def render_category_summaries(report) -> str:
    return json.dumps(
        [item.model_dump(mode="json") for item in report.category_summaries],
        ensure_ascii=False,
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run AIAgent RAG evaluation baseline.")
    parser.add_argument("--cases", required=True, help="Path to rag eval cases jsonl.")
    parser.add_argument("--knowledge-dir", default="data/knowledge/public")
    parser.add_argument("--docs-index-path", default="data/cache/knowledge/rag_eval_split_docs.json")
    parser.add_argument("--faiss-dir", default="data/cache/knowledge/rag_eval_faiss")
    parser.add_argument("--min-pass-rate", type=float, default=0.75)
    parser.add_argument("--min-recall-at-1", type=float, default=0.40)
    parser.add_argument("--min-recall-at-3", type=float, default=0.80)
    parser.add_argument("--min-mrr", type=float, default=0.55)
    parser.add_argument("--show-results", action="store_true")
    parser.add_argument("--show-category-summary", action="store_true")
    parser.add_argument("--print-markdown", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-dir", default="data/cache/knowledge/reports")
    parser.add_argument("--report-prefix", default="rag_eval")
    parser.add_argument("--retriever-name", default="bm25_baseline")

    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    pipeline = build_bm25_baseline_pipeline(
        knowledge_dir=args.knowledge_dir,
        docs_index_path=args.docs_index_path,
        faiss_dir=args.faiss_dir,
    )

    summary, results = evaluate_cases(
        cases,
        retrieve_fn=lambda case: pipeline.debug_retrieve(
            query=normalize_rag_query(case.query),
            top_k=case.top_k,
        ),
    )

    thresholds = RAGEvalThresholds(
    min_pass_rate=args.min_pass_rate,
    min_recall_at_1=args.min_recall_at_1,
    min_recall_at_3=args.min_recall_at_3,
    min_mrr=args.min_mrr,
)

    report = build_eval_report(
        cases=cases,
        summary=summary,
        results=results,
        thresholds=thresholds,
        cases_path=args.cases,
        knowledge_dir=args.knowledge_dir,
        retriever_name=args.retriever_name,
    )

    print(render_summary(summary))

    if args.show_category_summary:
        print(render_category_summaries(report))

    if args.show_results:
        print(render_results(results))

    if args.print_markdown:
        print(render_markdown_report(report))

    if args.write_report:
        paths = write_eval_report(
            report,
            output_dir=args.report_dir,
            prefix=args.report_prefix,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "report_paths": paths,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    failures = threshold_failures(summary, thresholds)
    if failures:
        return 1

    return 0

def _source_matches(case: RAGEvalCase, hit: RAGEvalHit) -> bool:
    if not case.expected_source_paths:
        return False
    return any(
        _normalize_path(expected) == _normalize_path(hit.source_path)
        or _normalize_path(hit.source_path).endswith(_normalize_path(expected))
        for expected in case.expected_source_paths
    )


def _title_matches(case: RAGEvalCase, hit: RAGEvalHit) -> bool:
    if not case.expected_titles:
        return False
    title = hit.title.lower()
    return any(expected.lower() in title for expected in case.expected_titles)


def _matched_terms(case: RAGEvalCase, hit: RAGEvalHit) -> list[str]:
    haystack = f"{hit.title}\n{hit.source_path}\n{hit.preview}\n{hit.content}".lower()
    return [
        term
        for term in case.expected_terms
        if term.lower() in haystack
    ]


def _find_forbidden_hit(
    case: RAGEvalCase,
    hits: list[RAGEvalHit],
) -> RAGEvalHit | None:
    if not case.forbidden_source_paths:
        return None

    forbidden = {_normalize_path(path) for path in case.forbidden_source_paths}
    for hit in hits:
        source_path = _normalize_path(hit.source_path)
        if any(source_path == path or source_path.endswith(path) for path in forbidden):
            return hit
    return None


def _normalize_path(path: str) -> str:
    return str(path).replace("\\", "/").strip().lower()


def _ratio(numerator: float, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


if __name__ == "__main__":
    raise SystemExit(main())
