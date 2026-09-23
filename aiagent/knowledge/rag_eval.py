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
    seen_case_ids: dict[str, int] = {}

    for line_number, line in enumerate(
        file_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = line.strip()
        if not line:
            continue

        case = RAGEvalCase.model_validate_json(line)

        # pass_rate / recall / mrr 被同一条用例重复计入，直接 fail fast。
        if case.case_id in seen_case_ids:
            raise ValueError(
                "duplicate eval case_id "
                f"'{case.case_id}' at line {line_number} "
                f"(first seen at line {seen_case_ids[case.case_id]})"
            )

        seen_case_ids[case.case_id] = line_number
        cases.append(case)

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
    """对单条用例做判定，返回结构化结果。

    判定顺序（不要调换，语义有依赖）：
    1. 负例（match_mode == "negative"）：只关心"有没有踩 forbidden"，期望列表为空是正常的；
    2. 普通用例的 forbidden 检查：踩了直接失败；
    3. required_source_paths 检查：这是"必须进榜"的硬约束，语义与 expected 不同；
    4. 逐条 hit 找第一个满足 match_mode 的命中，其 rank 即召回位置（recall@k 的分子依据）；
    5. rank > max_rank 判失败；
    6. expected_terms 只作为诊断信息（terms_missing），不再判失败。
    """
    top_hits = [RAGEvalHit(**hit) for hit in hits[: case.top_k]]

    forbidden = _find_forbidden_hit(case, top_hits)

    if case.match_mode == "negative":
        if forbidden is None:
            return RAGEvalCaseResult(
                case_id=case.case_id,
                category=case.category,
                query=case.query,
                passed=True,
                reason="no_forbidden_hit",
                top_hits=top_hits,
                extra={"match_mode": "negative"},
            )
        return RAGEvalCaseResult(
            case_id=case.case_id,
            category=case.category,
            query=case.query,
            passed=False,
            reason="forbidden_source_matched",
            matched_source_path=forbidden.source_path,
            matched_title=forbidden.title,
            top_hits=top_hits,
            extra={"match_mode": "negative"},
        )

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
            extra={"match_mode":case.match_mode},
        )

    missing_required = _missing_required_source_paths(case, top_hits)
    if missing_required:
        return RAGEvalCaseResult(
            case_id=case.case_id,
            category=case.category,
            query=case.query,
            passed=False,
            reason="missing_required_source_paths",
            top_hits=top_hits,
            extra={"match_mode":case.match_mode,
                   "missing_required_source_paths":missing_required},
        )

    best_rank: int | None = None
    best_hit: RAGEvalHit | None = None
    best_terms: list[str] = []

    for index, hit in enumerate(top_hits, start=1):
        source_matched = _source_matches(case, hit)
        title_matched = _title_matches(case, hit)
        matched_terms = _matched_terms(case, hit)

        if not _hit_matches_mode(
            case.match_mode,
            source_matched=source_matched,
            title_matched=title_matched,
            term_matched=bool(matched_terms),
        ):
            continue

        best_rank = index
        best_hit = hit
        best_terms = matched_terms
        break

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


    extra: dict[str, Any] = {"match_mode": case.match_mode}
    if case.expected_terms and not best_terms:
        extra["terms_missing"] = list(case.expected_terms)

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
        extra=extra,
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

def _hit_matches_mode(
        match_mode: str,
        *,
        source_matched: bool,
        title_matched: bool,
        term_matched: bool,
) -> bool:
    """判断单个命中是否满足用例声明的匹配模式。

    "term" 与 "terms" 都接受：模型字面量历史上写的是 "term"，
    而旧实现只判 "terms"，会让 "term" 悄悄退化成 "any"。
    "negative" 不走这里（在 evaluate_case 里单独处理）。
    """
    if match_mode == "source":
        return source_matched
    if match_mode == "title":
        return title_matched
    if match_mode in ("term", "terms"):
        return term_matched
    return source_matched or title_matched or term_matched

def _missing_required_source_paths(
        case: RAGEvalCase,
        hits: list[RAGEvalHit],
) -> list[str]:
    if not case.required_source_paths:
        return []

    normalized_hit_paths = [_normalize_path(hit.source_path) for hit in hits]
    missing: list[str] = []

    for expected in case.required_source_paths:
        normalized_expected = _normalize_path(expected)
        if not any(
            hit_path == normalized_expected or hit_path.endswith(normalized_expected)
            for hit_path in normalized_hit_paths
        ):
            missing.append(expected)

    return missing
    

if __name__ == "__main__":
    raise SystemExit(main())
