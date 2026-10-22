from __future__ import annotations

import hashlib

import pytest

from aiagent.knowledge.evaluation.dataset import corpus_snapshot


def test_snapshot_sorts_case_sensitive_posix_paths_and_preserves_bytes(tmp_path):
    # 顺序显式指定，避免测试重复使用待测函数的 Path 排序逻辑。
    entries = [
        ("Beta.md", b"upper\n"),
        ("alpha.MD", b"lower\r\n"),
        ("nested/Gamma.pdf", b"%PDF-1.4\r\n"),
        ("nested/delta.txt", b"nested\n"),
    ]
    expected = hashlib.sha256()
    for relative, data in reversed(entries):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (tmp_path / "ignored.png").write_bytes(b"not part of the corpus")

    for relative, data in entries:
        expected.update(relative.encode("utf-8"))
        expected.update(b"\0")
        expected.update(str(len(data)).encode("ascii"))
        expected.update(b"\0")
        expected.update(data)

    snapshot = corpus_snapshot(tmp_path)

    assert snapshot["file_count"] == len(entries)
    assert snapshot["total_bytes"] == sum(len(data) for _, data in entries)
    assert snapshot["sha256"] == expected.hexdigest()


@pytest.mark.parametrize("change", ["content", "path"])
def test_snapshot_detects_corpus_changes(tmp_path, change):
    path = tmp_path / "document.md"
    path.write_bytes(b"original\n")
    before = corpus_snapshot(tmp_path)

    if change == "content":
        path.write_bytes(b"modified\n")
    else:
        path.rename(tmp_path / "renamed.md")

    after = corpus_snapshot(tmp_path)

    assert after["file_count"] == before["file_count"]
    assert after["sha256"] != before["sha256"]


def test_snapshot_rejects_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError, match="knowledge directory not found"):
        corpus_snapshot(tmp_path / "missing")
