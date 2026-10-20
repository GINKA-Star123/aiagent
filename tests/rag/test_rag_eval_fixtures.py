from __future__ import annotations

from pathlib import Path

import pytest

from aiagent.knowledge.evaluation.dataset import (
    corpus_snapshot,
    load_chunk_cases,
    load_manifest,
    load_query_cases,
    validate_chunk_cases,
    validate_query_cases,
)

FIXTURE_DIR = Path("tests/fixtures/rag_eval")
CASES = FIXTURE_DIR / "cases.jsonl"
CHUNK_CASES = FIXTURE_DIR / "chunk_cases.jsonl"
KNOWLEDGE_DIR = Path("data/knowledge/public")


@pytest.mark.skipif(not KNOWLEDGE_DIR.exists(), reason="knowledge directory is missing")
def test_query_fixture_is_valid() -> None:
    cases = load_query_cases(CASES)
    validate_query_cases(cases, KNOWLEDGE_DIR)

    assert len(cases) == 120
    assert {case.suite for case in cases} == {"smoke", "core", "hard"}
    assert len({case.case_id for case in cases}) == len(cases)
    assert all(case.stages for case in cases)
    assert all(case.retrieval.top_k >= 1 for case in cases)


@pytest.mark.skipif(not KNOWLEDGE_DIR.exists(), reason="knowledge directory is missing")
def test_chunk_fixture_is_valid() -> None:
    cases = load_chunk_cases(CHUNK_CASES)
    validate_chunk_cases(cases, KNOWLEDGE_DIR)

    assert len(cases) == 12
    assert len({case.case_id for case in cases}) == len(cases)
    assert all(case.required_metadata for case in cases)
    assert all(case.required_section.startswith("### ") for case in cases)


@pytest.mark.skipif(not KNOWLEDGE_DIR.exists(), reason="knowledge directory is missing")
def test_manifest_matches_corpus() -> None:
    manifest = load_manifest(FIXTURE_DIR / "manifest.json")
    snapshot = corpus_snapshot(KNOWLEDGE_DIR)

    assert manifest["corpus"]["file_count"] == snapshot["file_count"]
    assert manifest["corpus"]["sha256"] == snapshot["sha256"]
    assert manifest["query_cases"]["total"] == 120
    assert manifest["chunk_cases"]["total"] == 12
