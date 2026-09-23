from __future__ import annotations

from pathlib import Path

from aiagent.knowledge.index_manifest import (
    build_index_manifest,
    evaluate_index_freshness,
    fingerprint_knowledge_files,
    load_index_manifest,
    save_index_manifest,
)
from aiagent.knowledge.index_manifest_models import IndexFreshnessStatus


def _identity(dimensions: int = 512) -> dict:
    return {
        "provider": "huggingface",
        "model": "test-embedding",
        "model_path": "",
        "dimensions": dimensions,
        "faiss_dimension": dimensions,
    }


def _build(knowledge_dir: Path, manifest_path: Path):
    files = fingerprint_knowledge_files(knowledge_dir)
    manifest = build_index_manifest(
        knowledge_dir=knowledge_dir,
        docs_index_path=manifest_path.parent / "split_docs.json",
        faiss_dir=manifest_path.parent / "faiss",
        embedding=_identity(),
        chunk_size=520,
        chunk_overlap=80,
        chunk_count=len(files),
        vector_count=len(files),
        files=files,
    )
    assert save_index_manifest(manifest_path, manifest) is True
    return load_index_manifest(manifest_path)


def _check(manifest, manifest_path: Path, knowledge_dir: Path, **overrides):
    kwargs = {"embedding": _identity(), "chunk_size": 520, "chunk_overlap": 80}
    kwargs.update(overrides)
    return evaluate_index_freshness(
        manifest=manifest,
        manifest_path=manifest_path,
        knowledge_dir=knowledge_dir,
        **kwargs,
    )


def test_manifest_roundtrip_reports_fresh(tmp_path):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "a.md").write_text("乐正绫", encoding="utf-8")
    manifest_path = tmp_path / "index_manifest.json"

    manifest = _build(knowledge, manifest_path)
    assert manifest is not None
    assert manifest.chunk_count == 1

    report = _check(manifest, manifest_path, knowledge)
    assert report.status == IndexFreshnessStatus.FRESH
    assert report.stale is False
    assert report.reasons == []


def test_manifest_flags_embedding_dimension_change(tmp_path):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "a.md").write_text("乐正绫", encoding="utf-8")
    manifest_path = tmp_path / "index_manifest.json"

    manifest = _build(knowledge, manifest_path)
    report = _check(manifest, manifest_path, knowledge, embedding=_identity(768))

    assert report.stale is True
    assert "embedding_dimension_changed" in report.reasons
    assert "维度" in report.hint


def test_manifest_flags_chunk_policy_change(tmp_path):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "a.md").write_text("乐正绫", encoding="utf-8")
    manifest_path = tmp_path / "index_manifest.json"

    manifest = _build(knowledge, manifest_path)
    report = _check(manifest, manifest_path, knowledge, chunk_size=720, chunk_overlap=120)

    assert report.stale is True
    assert "chunk_policy_changed" in report.reasons


def test_manifest_flags_knowledge_file_changes(tmp_path):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "a.md").write_text("乐正绫", encoding="utf-8")
    manifest_path = tmp_path / "index_manifest.json"

    manifest = _build(knowledge, manifest_path)
    (knowledge / "a.md").write_text("乐正绫 代表色是红色", encoding="utf-8")
    (knowledge / "b.md").write_text("洛天依", encoding="utf-8")

    report = _check(manifest, manifest_path, knowledge)
    assert report.stale is True
    assert report.added_files == ["b.md"]
    assert report.modified_files == ["a.md"]
    assert "knowledge_files_added" in report.reasons
    assert "knowledge_files_modified" in report.reasons


def test_manifest_missing_marks_stale(tmp_path):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "a.md").write_text("乐正绫", encoding="utf-8")
    manifest_path = tmp_path / "index_manifest.json"

    report = _check(None, manifest_path, knowledge)
    assert report.status == IndexFreshnessStatus.MISSING
    assert report.stale is True
    assert report.reasons == ["manifest_missing"]