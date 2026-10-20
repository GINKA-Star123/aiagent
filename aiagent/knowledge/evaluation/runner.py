from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from aiagent.knowledge.evaluation.dataset import path_matches
from aiagent.knowledge.evaluation.models import (
    ChunkCase,
    ChunkCaseResult,
    RAGEvalCase,
    RAGEvalCaseResult,
    RAGEvalStageSummary,
    RAGEvalSummary,
    StageCheck,
)
from aiagent.knowledge.query_normalizer import normalize_rag_query
from aiagent.knowledge.rag_pipeline import RAGPipeline

_REQUIRED_CHUNK_METADATA = (
    "chunk_id",
    "chunk_index",
    "doc_id",
    "title",
    "source_path",
    "character",
    "aliases",
    "topic",
    "trust_level",
    "doc_kind",
    "chunk_policy",
)


def _chunk_text(chunk: dict[str, Any]) -> str:
    return "\n".join(
        [
            str(chunk.get("title", "")),
            str(chunk.get("source_path", "")),
            str(chunk.get("content", "")),
        ]
    )


def _all_terms_present(terms: list[str], chunks: list[dict[str, Any]]) -> list[str]:
    haystack = "\n".join(_chunk_text(chunk) for chunk in chunks).lower()
    return [term for term in terms if term.lower() not in haystack]


def _find_rank(chunks: list[dict[str, Any]], expected_paths: list[str]) -> int | None:
    if not expected_paths:
        return None
    for rank, chunk in enumerate(chunks, start=1):
        source = str(chunk.get("source_path", ""))
        if any(path_matches(source, expected) for expected in expected_paths):
            return rank
    return None


def _find_forbidden(
    chunks: list[dict[str, Any]], forbidden_paths: list[str]
) -> str:
    for chunk in chunks:
        source = str(chunk.get("source_path", ""))
        for forbidden in forbidden_paths:
            if path_matches(source, forbidden):
                return source
    return ""


def _missing_required(
    chunks: list[dict[str, Any]], required_paths: list[str]
) -> list[str]:
    if not required_paths:
        return []
    sources = [str(chunk.get("source_path", "")) for chunk in chunks]
    missing: list[str] = []
    for required in required_paths:
        if not any(path_matches(source, required) for source in sources):
            missing.append(required)
    return missing


def _citation_has_source(citations: list[dict[str, Any]], expected: str) -> bool:
    return any(
        path_matches(str(citation.get("source_path", "")), expected)
        for citation in citations
    )


def _retrieval_stage(
    case: RAGEvalCase,
    *,
    coarse_chunks: list[dict[str, Any]],
    final_chunks: list[dict[str, Any]],
) -> StageCheck:
    expected = case.retrieval.expected_source_paths
    required = case.retrieval.required_source_paths
    forbidden = case.retrieval.forbidden_source_paths

    failures: list[str] = []
    coarse_rank = _find_rank(coarse_chunks, expected)
    forbidden_hit = _find_forbidden(final_chunks, forbidden)
    missing_required = _missing_required(coarse_chunks, required)

    if forbidden_hit:
        failures.append(f"forbidden_source_matched:{forbidden_hit}")
    if missing_required:
        failures.append("missing_required_source_paths:" + ",".join(missing_required))
    if expected and coarse_rank is None:
        failures.append("no_expected_hit_in_coarse")

    return StageCheck(
        passed=not failures,
        failures=failures,
        details={
            "coarse_best_rank": coarse_rank,
            "forbidden_hit": forbidden_hit,
            "missing_required_source_paths": missing_required,
            "coarse_top_sources": [
                str(chunk.get("source_path", "")) for chunk in coarse_chunks
            ],
            "final_top_sources": [
                str(chunk.get("source_path", "")) for chunk in final_chunks
            ],
        },
    )


def _rerank_stage(
    case: RAGEvalCase,
    *,
    final_chunks: list[dict[str, Any]],
    best_rank: int | None,
) -> StageCheck:
    if not case.rerank.expected_top1_source_paths and not case.rerank.expected_sections:
        return StageCheck(passed=True, details={"skipped": True})

    failures: list[str] = []
    top_source = str(final_chunks[0].get("source_path", "")) if final_chunks else ""
    expected_top1 = case.rerank.expected_top1_source_paths

    top1_ok = True
    if expected_top1:
        top1_ok = any(path_matches(top_source, expected) for expected in expected_top1)
        if not top1_ok:
            failures.append(f"top1_source_mismatch:{top_source}")

    section_hits = 0
    if case.rerank.expected_sections:
        for chunk in final_chunks:
            text = str(chunk.get("content", ""))
            if any(section in text for section in case.rerank.expected_sections):
                section_hits += 1
        if section_hits < case.rerank.min_section_hits:
            failures.append(
                f"section_hits_below_min:{section_hits}<{case.rerank.min_section_hits}"
            )

    missing_terms = _all_terms_present(
        case.retrieval.expected_content_terms,
        final_chunks,
    )
    if missing_terms:
        failures.append("content_terms_missing:" + ",".join(missing_terms))

    forbidden_hit = _find_forbidden(
        final_chunks, case.retrieval.forbidden_source_paths
    )
    if forbidden_hit:
        failures.append(f"forbidden_source_matched:{forbidden_hit}")

    if (
        case.rerank.expected_top1_source_paths
        and best_rank is not None
        and best_rank > case.retrieval.max_rank
    ):
        failures.append(
            f"final_rank_too_low:{best_rank}>{case.retrieval.max_rank}"
        )

    return StageCheck(
        passed=not failures,
        failures=failures,
        details={
            "top1_source": top_source,
            "top1_ok": top1_ok,
            "section_hits": section_hits,
            "missing_content_terms": missing_terms,
            "best_rank": best_rank,
            "top_sources": [str(chunk.get("source_path", "")) for chunk in final_chunks],
        },
    )


def _injection_stage(
    case: RAGEvalCase,
    inspection: dict[str, Any],
    *,
    normalized_query: str,
) -> StageCheck:
    expectation = case.injection
    if expectation is None:
        return StageCheck(passed=True, details={"skipped": True})

    confidence = inspection.get("confidence") or {}
    citations = inspection.get("citations") or []
    should_inject = bool(inspection.get("should_inject"))
    level = str(confidence.get("level", ""))
    status = str(confidence.get("status", ""))
    reason = str(confidence.get("reason", ""))

    failures: list[str] = []
    if should_inject != expectation.should_inject:
        failures.append(f"should_inject_mismatch:{should_inject}")
    if level not in expectation.allowed_levels:
        failures.append(f"confidence_level_not_allowed:{level}")
    if status not in expectation.allowed_statuses:
        failures.append(f"confidence_status_not_allowed:{status}")

    count = len(citations)
    if count < expectation.min_citations:
        failures.append(f"citation_count_too_low:{count}<{expectation.min_citations}")
    if count > expectation.max_citations:
        failures.append(f"citation_count_too_high:{count}>{expectation.max_citations}")

    missing_sources = [
        source
        for source in expectation.required_citation_sources
        if not _citation_has_source(citations, source)
    ]
    if missing_sources:
        failures.append("required_citation_sources_missing:" + ",".join(missing_sources))

    forbidden_sources = [
        source
        for source in expectation.forbidden_citation_sources
        if _citation_has_source(citations, source)
    ]
    if forbidden_sources:
        failures.append("forbidden_citation_sources_present:" + ",".join(forbidden_sources))

    return StageCheck(
        passed=not failures,
        failures=failures,
        details={
            "query": normalized_query,
            "should_inject": should_inject,
            "confidence_level": level,
            "confidence_status": status,
            "confidence_reason": reason,
            "citation_count": count,
            "citation_sources": [
                str(citation.get("source_path", "")) for citation in citations
            ],
        },
    )


def _prompt_stage(
    case: RAGEvalCase,
    *,
    prompt_context: str,
) -> StageCheck:
    expectation = case.prompt
    if expectation is None:
        return StageCheck(passed=True, details={"skipped": True})

    failures: list[str] = []

    if expectation.expect_empty:
        if prompt_context.strip() != "无相关知识":
            failures.append("prompt_not_empty")
    else:
        for needle in expectation.must_contain:
            if needle not in prompt_context:
                failures.append(f"prompt_missing:{needle}")
        for needle in expectation.must_not_contain:
            if needle in prompt_context:
                failures.append(f"prompt_contains_forbidden:{needle}")
        lower_prompt = prompt_context.lower()
        for term in expectation.required_terms:
            if term.lower() not in lower_prompt:
                failures.append(f"prompt_term_missing:{term}")
        for term in expectation.forbidden_terms:
            if term.lower() in lower_prompt:
                failures.append(f"prompt_term_forbidden:{term}")
        if len(prompt_context) > expectation.max_chars:
            failures.append(
                f"prompt_too_long:{len(prompt_context)}>{expectation.max_chars}"
            )

    return StageCheck(
        passed=not failures,
        failures=failures,
        details={
            "chars": len(prompt_context),
            "empty": prompt_context.strip() == "无相关知识",
        },
    )


def _end_to_end_stage(
    case: RAGEvalCase,
    stages: dict[str, StageCheck],
) -> StageCheck:
    failures: list[str] = []
    for stage_name in case.stages:
        stage = stages.get(stage_name)
        if stage is None:
            failures.append(f"stage_missing:{stage_name}")
            continue
        failures.extend(f"{stage_name}:{failure}" for failure in stage.failures)

    return StageCheck(passed=not failures, failures=failures)


def evaluate_query_case(
    pipeline: RAGPipeline,
    case: RAGEvalCase,
) -> RAGEvalCaseResult:
    normalized_query = normalize_rag_query(case.query)
    coarse_k = max(case.retrieval.top_k * 3, 10)

    try:
        coarse_chunks = pipeline.retriever.retrieve(
            query=normalized_query,
            vector_store=pipeline.vector_store,
            top_k=coarse_k,
        )
        final_chunks = pipeline.reranker.rerank(
            query=normalized_query,
            chunks=coarse_chunks,
            top_k=case.retrieval.top_k,
        )
        final_dicts = [
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "source_path": chunk.source_path,
                "content": chunk.content,
                "score": chunk.score,
                "bm25_rank": chunk.bm25_rank,
                "vector_rank": chunk.vector_rank,
                "cosine_score": chunk.cosine_score,
                "retrieval_sources": chunk.retrieval_sources,
                "preview": chunk.content[:260],
            }
            for chunk in final_chunks
        ]
        coarse_dicts = [
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "source_path": chunk.source_path,
                "content": chunk.content,
                "score": chunk.score,
                "bm25_rank": chunk.bm25_rank,
                "vector_rank": chunk.vector_rank,
                "cosine_score": chunk.cosine_score,
                "retrieval_sources": chunk.retrieval_sources,
                "preview": chunk.content[:260],
            }
            for chunk in coarse_chunks
        ]
        coarse_best_rank = _find_rank(
            coarse_dicts, case.retrieval.expected_source_paths
        )
        best_rank = _find_rank(
            final_dicts, case.retrieval.expected_source_paths
        )

        stages: dict[str, StageCheck] = {}
        if "retrieval" in case.stages:
            stages["retrieval"] = _retrieval_stage(
                case,
                coarse_chunks=coarse_dicts,
                final_chunks=final_dicts,
            )
        if "rerank" in case.stages:
            stages["rerank"] = _rerank_stage(
                case,
                final_chunks=final_dicts,
                best_rank=best_rank,
            )

        inspection = pipeline.inspect(
            query=normalized_query,
            top_k=case.retrieval.top_k,
        )
        if "injection" in case.stages:
            stages["injection"] = _injection_stage(
                case,
                inspection,
                normalized_query=normalized_query,
            )
        if "prompt" in case.stages:
            stages["prompt"] = _prompt_stage(
                case,
                prompt_context=str(inspection.get("prompt_context", "")),
            )

        stages["end_to_end"] = _end_to_end_stage(case, stages)

        citations = inspection.get("citations") or []
        metrics = {
            "coarse_best_rank": float(coarse_best_rank or 0),
            "final_best_rank": float(best_rank or 0),
            "citation_count": float(len(citations)),
        }
        return RAGEvalCaseResult(
            case_id=case.case_id,
            suite=case.suite,
            category=case.category,
            query=case.query,
            passed=stages["end_to_end"].passed,
            stages=stages,
            metrics=metrics,
            top_sources=[
                str(chunk.get("source_path", "")) for chunk in final_dicts
            ],
        )
    except Exception as exc:  # noqa: BLE001 - evaluation must report, not crash
        stage_names = list(dict.fromkeys([*case.stages, "end_to_end"]))
        failed = {
            name: StageCheck(passed=False, failures=[f"exception:{type(exc).__name__}"])
            for name in stage_names
        }
        return RAGEvalCaseResult(
            case_id=case.case_id,
            suite=case.suite,
            category=case.category,
            query=case.query,
            passed=False,
            stages=failed,
            error=f"{type(exc).__name__}: {exc}",
        )


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _stage_summary(
    stage: str,
    results: list[RAGEvalCaseResult],
) -> RAGEvalStageSummary:
    applicable = [result for result in results if stage in result.stages]
    passed = sum(1 for result in applicable if result.stages[stage].passed)
    failure_counts: Counter[str] = Counter()
    for result in applicable:
        for failure in result.stages[stage].failures:
            failure_counts[failure.split(":", 1)[0]] += 1

    return RAGEvalStageSummary(
        stage=stage,
        total=len(applicable),
        passed=passed,
        failed=len(applicable) - passed,
        pass_rate=_ratio(passed, len(applicable)),
        failures=dict(sorted(failure_counts.items())),
    )


def evaluate_query_cases(
    pipeline: RAGPipeline,
    cases: list[RAGEvalCase],
    *,
    suite: str,
) -> tuple[RAGEvalSummary, list[RAGEvalCaseResult]]:
    results = [evaluate_query_case(pipeline, case) for case in cases]
    total = len(results)
    passed = sum(1 for result in results if result.passed)

    positive_ids = {
        case.case_id
        for case in cases
        if case.retrieval.expected_source_paths or case.retrieval.required_source_paths
    }
    positive_results = [result for result in results if result.case_id in positive_ids]

    coarse_hits = [
        result
        for result in positive_results
        if result.metrics.get("coarse_best_rank", 0.0) > 0
    ]
    retrieval_recall = _ratio(len(coarse_hits), len(positive_results))
    retrieval_mrr = _ratio(
        sum(
            1.0 / result.metrics["coarse_best_rank"]
            for result in coarse_hits
            if result.metrics.get("coarse_best_rank", 0.0) > 0
        ),
        len(positive_results),
    )

    final_hits = [
        result
        for result in positive_results
        if result.metrics.get("final_best_rank", 0.0) > 0
    ]
    rerank_recall = _ratio(len(final_hits), len(positive_results))
    rerank_mrr = _ratio(
        sum(
            1.0 / result.metrics["final_best_rank"]
            for result in final_hits
            if result.metrics.get("final_best_rank", 0.0) > 0
        ),
        len(positive_results),
    )

    top1_cases = [
        result
        for result in positive_results
        if result.stages.get("rerank")
        and result.stages["rerank"].details.get("top1_ok") is not None
    ]
    top1_hits = [
        result
        for result in top1_cases
        if result.stages["rerank"].details.get("top1_ok") is True
    ]

    injection_cases = [
        result for result in results if "injection" in result.stages
    ]
    injection_passed = [
        result
        for result in injection_cases
        if result.stages["injection"].passed
    ]
    prompt_cases = [result for result in results if "prompt" in result.stages]
    prompt_passed = [
        result for result in prompt_cases if result.stages["prompt"].passed
    ]

    stage_summaries = [
        _stage_summary(stage, results)
        for stage in ("retrieval", "rerank", "injection", "prompt", "end_to_end")
    ]

    summary = RAGEvalSummary(
        suite=suite,
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=_ratio(passed, total),
        stage_summaries=stage_summaries,
        metrics={
            "retrieval_recall": retrieval_recall,
            "retrieval_mrr": retrieval_mrr,
            "rerank_recall": rerank_recall,
            "rerank_top1_accuracy": _ratio(len(top1_hits), len(top1_cases)),
            "rerank_mrr": rerank_mrr,
            "injection_accuracy": _ratio(
                len(injection_passed), len(injection_cases)
            ),
            "prompt_pass_rate": _ratio(len(prompt_passed), len(prompt_cases)),
            "end_to_end_pass_rate": _ratio(passed, total),
            "positive_cases": float(len(positive_results)),
            "negative_cases": float(total - len(positive_results)),
        },
    )
    return summary, results


def _disk_sources(knowledge_dir: str | Path) -> list[str]:
    root = Path(knowledge_dir)
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".markdown", ".txt"}
    )


def _chunk_source_path(chunk: Any) -> str:
    return str(chunk.metadata.get("source_path", ""))


def _chunk_content(chunk: Any) -> str:
    return str(getattr(chunk, "page_content", ""))


def evaluate_chunking(
    chunks: list[Any],
    cases: list[ChunkCase],
    *,
    knowledge_dir: str | Path,
    pipeline: RAGPipeline | None = None,
) -> tuple[RAGEvalStageSummary, list[ChunkCaseResult], StageCheck]:
    results: list[ChunkCaseResult] = []
    global_failures: list[str] = []

    disk_sources = _disk_sources(knowledge_dir)
    chunk_sources = sorted({_chunk_source_path(chunk) for chunk in chunks})
    missing_sources = [
        source
        for source in disk_sources
        if not any(path_matches(chunk_source, source) for chunk_source in chunk_sources)
    ]
    if missing_sources:
        global_failures.append("sources_missing_from_index:" + ",".join(missing_sources))

    duplicate_ids: dict[str, int] = {}
    for chunk in chunks:
        chunk_id = str(chunk.metadata.get("chunk_id", ""))
        duplicate_ids[chunk_id] = duplicate_ids.get(chunk_id, 0) + 1
    duplicated = [chunk_id for chunk_id, count in duplicate_ids.items() if count > 1]
    if duplicated:
        global_failures.append("duplicate_chunk_ids:" + ",".join(duplicated[:10]))

    empty_chunks = sum(1 for chunk in chunks if not _chunk_content(chunk).strip())
    if empty_chunks:
        global_failures.append(f"empty_chunks:{empty_chunks}")

    missing_metadata = Counter()
    for chunk in chunks:
        for key in _REQUIRED_CHUNK_METADATA:
            if key not in chunk.metadata:
                missing_metadata[key] += 1
    if missing_metadata:
        global_failures.append(
            "missing_metadata:" + ",".join(sorted(missing_metadata))
        )

    oversized = [
        chunk
        for chunk in chunks
        if len(_chunk_content(chunk)) > 1200
    ]
    if oversized:
        global_failures.append(f"oversized_chunks:{len(oversized)}")

    invalid_indexes = 0
    for chunk in chunks:
        value = chunk.metadata.get("chunk_index")
        if not isinstance(value, int) or value < 0:
            invalid_indexes += 1
    if invalid_indexes:
        global_failures.append(f"invalid_chunk_index:{invalid_indexes}")

    absolute_sources = [
        source
        for source in chunk_sources
        if source.startswith("/") or ":" in source
    ]
    if absolute_sources:
        global_failures.append(
            "absolute_source_paths:" + ",".join(absolute_sources[:5])
        )

    results.append(
        ChunkCaseResult(
            case_id="chunk_global",
            source_path="*",
            passed=not global_failures,
            failures=global_failures,
            details={
                "disk_sources": len(disk_sources),
                "indexed_sources": len(chunk_sources),
                "chunks": len(chunks),
            },
        )
    )

    for case in cases:
        source_chunks = [
            chunk
            for chunk in chunks
            if path_matches(_chunk_source_path(chunk), case.source_path)
        ]
        failures: list[str] = []
        if not source_chunks:
            failures.append("no_chunks_for_source")
        else:
            count = len(source_chunks)
            if count < case.min_chunks:
                failures.append(f"chunk_count_too_low:{count}<{case.min_chunks}")
            if count > case.max_chunks:
                failures.append(f"chunk_count_too_high:{count}>{case.max_chunks}")

            for key in case.required_metadata:
                if any(key not in chunk.metadata for chunk in source_chunks):
                    failures.append(f"metadata_missing:{key}")

            if case.expected_character:
                actual = str(source_chunks[0].metadata.get("character", ""))
                if actual != case.expected_character:
                    failures.append(
                        f"character_mismatch:{actual}!={case.expected_character}"
                    )
            if case.expected_topic:
                actual = str(source_chunks[0].metadata.get("topic", ""))
                if actual != case.expected_topic:
                    failures.append(f"topic_mismatch:{actual}!={case.expected_topic}")
            if case.expected_doc_kind:
                actual = str(source_chunks[0].metadata.get("doc_kind", ""))
                if actual != case.expected_doc_kind:
                    failures.append(
                        f"doc_kind_mismatch:{actual}!={case.expected_doc_kind}"
                    )

            aliases = source_chunks[0].metadata.get("aliases") or []
            search_aliases = source_chunks[0].metadata.get("search_aliases") or []
            if case.required_alias and case.required_alias not in aliases:
                failures.append(f"alias_missing:{case.required_alias}")
            if (
                case.required_search_alias
                and case.required_search_alias not in search_aliases
            ):
                failures.append(
                    f"search_alias_missing:{case.required_search_alias}"
                )

            if case.required_section and not any(
                case.required_section in _chunk_content(chunk)
                for chunk in source_chunks
            ):
                failures.append(f"section_missing:{case.required_section}")

            for group in case.must_keep_together:
                if not any(
                    all(term in _chunk_content(chunk) for term in group)
                    for chunk in source_chunks
                ):
                    failures.append("terms_split:" + "|".join(group))

            too_small = [
                len(_chunk_content(chunk))
                for chunk in source_chunks
                if len(_chunk_content(chunk)) < case.min_chunk_chars
            ]
            if too_small:
                failures.append(f"chunk_too_small:{len(too_small)}")
            too_large = [
                len(_chunk_content(chunk))
                for chunk in source_chunks
                if len(_chunk_content(chunk)) > case.max_chunk_chars
            ]
            if too_large:
                failures.append(f"chunk_too_large:{len(too_large)}")

            for term in case.forbidden_terms:
                if any(term in _chunk_content(chunk) for chunk in source_chunks):
                    failures.append(f"forbidden_term_present:{term}")

        results.append(
            ChunkCaseResult(
                case_id=case.case_id,
                source_path=case.source_path,
                passed=not failures,
                failures=failures,
                details={
                    "chunks": len(source_chunks),
                    "sizes": [len(_chunk_content(chunk)) for chunk in source_chunks][:20],
                },
            )
        )

    passed = sum(1 for result in results if result.passed)
    failure_counts: Counter[str] = Counter()
    for result in results:
        for failure in result.failures:
            failure_counts[failure.split(":", 1)[0]] += 1

    summary = RAGEvalStageSummary(
        stage="chunking",
        total=len(results),
        passed=passed,
        failed=len(results) - passed,
        pass_rate=_ratio(passed, len(results)),
        failures=dict(sorted(failure_counts.items())),
    )

    index_audit = collect_index_audit(pipeline, chunks=chunks)
    return summary, results, index_audit


def collect_index_audit(
    pipeline: RAGPipeline | None,
    *,
    chunks: list[Any] | None = None,
) -> StageCheck:
    if pipeline is None:
        return StageCheck(
            passed=True,
            details={"skipped": True, "chunks": len(chunks or [])},
        )

    stats = pipeline.stats()
    failures: list[str] = []

    if int(stats.get("chunk_count", 0)) != len(chunks or pipeline.documents):
        failures.append("chunk_count_mismatch")
    if int(stats.get("chunk_count", 0)) <= 0:
        failures.append("no_chunks")
    if int(stats.get("vector_count", 0)) != 0:
        failures.append("unexpected_vector_count")
    if int(stats.get("chunk_size", 0)) != 520:
        failures.append("unexpected_chunk_size")
    if int(stats.get("chunk_overlap", 0)) != 80:
        failures.append("unexpected_chunk_overlap")
    if stats.get("index_stale") is not False:
        failures.append("index_stale")
    build_status = stats.get("build_status") or {}
    if str(build_status.get("status", "")) != "done":
        failures.append("index_build_not_done")
    manifest_path = Path(str(stats.get("index_manifest_path", "")))
    if not manifest_path.is_file():
        failures.append("index_manifest_missing")

    return StageCheck(
        passed=not failures,
        failures=failures,
        details={
            "chunk_count": stats.get("chunk_count"),
            "vector_count": stats.get("vector_count"),
            "chunk_size": stats.get("chunk_size"),
            "chunk_overlap": stats.get("chunk_overlap"),
            "index_stale": stats.get("index_stale"),
            "build_status": build_status.get("status"),
        },
    )
