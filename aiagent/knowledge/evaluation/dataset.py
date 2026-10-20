from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from aiagent.knowledge.evaluation.models import ChunkCase, RAGEvalCase

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".json", ".jsonl", ".pdf"}


def _iter_lines(path: str | Path) -> Iterable[tuple[int, str]]:
    file_path = Path(path)
    for line_number, line in enumerate(
        file_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.strip()
        if stripped:
            yield line_number, stripped


def load_query_cases(path: str | Path, suite: str = "all") -> list[RAGEvalCase]:
    cases: list[RAGEvalCase] = []
    seen: dict[str, int] = {}

    for line_number, line in _iter_lines(path):
        case = RAGEvalCase.model_validate_json(line)

        if case.case_id in seen:
            raise ValueError(
                f"duplicate case_id '{case.case_id}' at line {line_number} "
                f"(first seen at line {seen[case.case_id]})"
            )
        seen[case.case_id] = line_number

        if suite != "all" and case.suite != suite:
            continue

        cases.append(case)

    if not cases:
        raise ValueError(f"no RAG evaluation cases loaded from {path} (suite={suite})")

    return cases


def load_chunk_cases(path: str | Path) -> list[ChunkCase]:
    cases: list[ChunkCase] = []
    seen: dict[str, int] = {}

    for line_number, line in _iter_lines(path):
        case = ChunkCase.model_validate_json(line)

        if case.case_id in seen:
            raise ValueError(
                f"duplicate chunk case_id '{case.case_id}' at line {line_number} "
                f"(first seen at line {seen[case.case_id]})"
            )
        seen[case.case_id] = line_number
        cases.append(case)

    return cases


def normalize_path(value: str) -> str:
    return str(value).replace("\\", "/").strip().lower()


def path_matches(source: str, expected: str) -> bool:
    source_norm = normalize_path(source)
    expected_norm = normalize_path(expected)
    if not source_norm or not expected_norm:
        return False
    return source_norm == expected_norm or source_norm.endswith("/" + expected_norm)


def _doc_path(knowledge_dir: str | Path, source_path: str) -> Path:
    return Path(knowledge_dir) / str(source_path)


def _read_doc_text(knowledge_dir: str | Path, source_path: str) -> str:
    path = _doc_path(knowledge_dir, source_path)
    if not path.is_file():
        raise FileNotFoundError(f"knowledge file not found: {path}")
    if path.suffix.lower() in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def validate_query_cases(
    cases: list[RAGEvalCase],
    knowledge_dir: str | Path,
) -> None:
    seen_queries: dict[str, str] = {}

    for case in cases:
        if case.query in seen_queries:
            raise ValueError(
                f"duplicate query '{case.query}' in {case.case_id} and "
                f"{seen_queries[case.query]}"
            )
        seen_queries[case.query] = case.case_id

        if case.suite not in {"smoke", "core", "hard"}:
            raise ValueError(f"{case.case_id}: unsupported suite {case.suite}")

        if not case.stages:
            raise ValueError(f"{case.case_id}: stages must not be empty")

        expected = list(case.retrieval.expected_source_paths)
        required = list(case.retrieval.required_source_paths)
        forbidden = list(case.retrieval.forbidden_source_paths)

        for source_path in [*expected, *required, *forbidden]:
            if not _doc_path(knowledge_dir, source_path).is_file():
                raise FileNotFoundError(
                    f"{case.case_id}: knowledge file not found: {source_path}"
                )

        texts: list[str] = []
        for source_path in [*expected, *required]:
            texts.append(_read_doc_text(knowledge_dir, source_path))

        haystack = "\n".join(texts).lower()
        for term in case.retrieval.expected_content_terms:
            if term.lower() not in haystack:
                raise ValueError(
                    f"{case.case_id}: expected_content_term not found in expected docs: {term}"
                )


def validate_chunk_cases(
    cases: list[ChunkCase],
    knowledge_dir: str | Path,
) -> None:
    for case in cases:
        text = _read_doc_text(knowledge_dir, case.source_path)

        if case.required_section and case.required_section not in text:
            raise ValueError(
                f"{case.case_id}: required_section not found: {case.required_section}"
            )

        for group in case.must_keep_together:
            for term in group:
                if term not in text:
                    raise ValueError(
                        f"{case.case_id}: must_keep_together term not found: {term}"
                    )

        for term in case.forbidden_terms:
            if term and term not in text:
                raise ValueError(
                    f"{case.case_id}: forbidden term not present in source: {term}"
                )


def corpus_snapshot(knowledge_dir: str | Path) -> dict[str, object]:
    root = Path(knowledge_dir)
    if not root.exists():
        raise FileNotFoundError(f"knowledge directory not found: {root}")

    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    digest = hashlib.sha256()
    total_bytes = 0

    for file_path in files:
        data = file_path.read_bytes()
        total_bytes += len(data)
        relative = file_path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)

    return {
        "file_count": len(files),
        "total_bytes": total_bytes,
        "sha256": digest.hexdigest(),
        "root": str(root),
    }


def load_manifest(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
