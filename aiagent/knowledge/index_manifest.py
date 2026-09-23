from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiagent.knowledge.document_loader import DocumentLoader
from aiagent.knowledge.index_manifest_models import (
    IndexBuildManifest,
    IndexFreshnessReport,
    IndexFreshnessStatus,
    IndexStaleReason,
    KnowledgeFileFingerprint,
)

logger = logging.getLogger(__name__)

INDEX_MANIFEST_SCHEMA_VERSION = 1
# 与 HybridRetriever._searchable_text / _tokenize 的实现绑定：
# 只要分词或"可检索文本"的构造方式变了（例如上一批次把文件名词干注入 header），
# 就必须把这个版本号 +1，否则旧索引不会被判定为过期。
TOKENIZER_VERSION = "bm25-zh-ngram-v2"

# 超过 4MB 的文件不计算 sha1（省启动时间），退化为 size+mtime 判定。
_HASH_READ_LIMIT = 4 * 1024 * 1024
_HASH_CHUNK_SIZE = 1024 * 1024
_MTIME_TOLERANCE = 1e-6


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint_knowledge_files(knowledge_dir: str | Path) -> list[KnowledgeFileFingerprint]:
    """扫描知识目录，只统计 DocumentLoader 支持的后缀，保证与加载器口径一致。"""
    root = Path(knowledge_dir)
    if not root.exists():
        return []

    fingerprints: list[KnowledgeFileFingerprint] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in DocumentLoader.SUPPORTED_SUFFIXES:
            continue
        fingerprints.append(fingerprint_file(path, root=root))
    return fingerprints


def fingerprint_file(path: str | Path, *, root: str | Path | None = None) -> KnowledgeFileFingerprint:
    file_path = Path(path)
    try:
        stat = file_path.stat()
    except OSError:
        return KnowledgeFileFingerprint(path=_relative_path(file_path, root))

    return KnowledgeFileFingerprint(
        path=_relative_path(file_path, root),
        size=int(stat.st_size),
        mtime=float(stat.st_mtime),
        sha1=_sha1_of_file(file_path),
    )


def build_index_manifest(
    *,
    knowledge_dir: str | Path,
    docs_index_path: str | Path,
    faiss_dir: str | Path,
    embedding: dict[str, Any] | None = None,
    chunk_size: int,
    chunk_overlap: int,
    chunk_count: int,
    vector_count: int,
    tokenizer_version: str = TOKENIZER_VERSION,
    files: list[KnowledgeFileFingerprint] | None = None,
) -> IndexBuildManifest:
    identity = dict(embedding or {})

    return IndexBuildManifest(
        schema_version=INDEX_MANIFEST_SCHEMA_VERSION,
        built_at=utc_now(),
        knowledge_dir=str(knowledge_dir),
        docs_index_path=str(docs_index_path),
        faiss_dir=str(faiss_dir),
        embedding_provider=str(identity.get("provider") or ""),
        embedding_model=str(identity.get("model") or ""),
        embedding_model_path=str(identity.get("model_path") or ""),
        embedding_dimensions=_optional_int(identity.get("dimensions")),
        faiss_dimension=_optional_int(identity.get("faiss_dimension")),
        chunk_size=int(chunk_size),
        chunk_overlap=int(chunk_overlap),
        tokenizer_version=str(tokenizer_version or ""),
        chunk_count=int(chunk_count),
        vector_count=int(vector_count),
        files=list(files if files is not None else fingerprint_knowledge_files(knowledge_dir)),
    )


def save_index_manifest(path: str | Path, manifest: IndexBuildManifest) -> bool:
    """原子写：先写 .tmp 再 replace，避免进程被杀时留下半截 JSON。"""
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target.with_name(target.name + ".tmp")
        temp_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(target)
        return True
    except Exception as exc:
        logger.warning("Failed to save knowledge index manifest: %s", exc)
        return False


def load_index_manifest(path: str | Path) -> IndexBuildManifest | None:
    """容错读取：文件不存在/坏 JSON/字段不合法一律返回 None，绝不抛。"""
    target = Path(path)
    if not target.exists():
        return None

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read knowledge index manifest: %s", exc)
        return None

    if not isinstance(payload, dict):
        return None

    try:
        return IndexBuildManifest(**payload)
    except Exception as exc:
        logger.warning("Invalid knowledge index manifest: %s", exc)
        return None


def evaluate_index_freshness(
    *,
    manifest: IndexBuildManifest | None,
    manifest_path: str | Path,
    knowledge_dir: str | Path,
    embedding: dict[str, Any] | None = None,
    chunk_size: int,
    chunk_overlap: int,
    tokenizer_version: str = TOKENIZER_VERSION,
) -> IndexFreshnessReport:
    """把"当前配置+当前文件"和清单逐项比对，产出过期原因。"""
    identity = dict(embedding or {})
    report = IndexFreshnessReport(
        manifest_path=str(manifest_path),
        checked_at=utc_now(),
        knowledge_dir=str(knowledge_dir),
        current_embedding=identity,
    )

    if manifest is None:
        report.status = IndexFreshnessStatus.MISSING
        report.stale = True
        report.reasons = [IndexStaleReason.MANIFEST_MISSING.value]
        report.hint = describe_freshness(report)
        return report

    report.built_at = manifest.built_at
    report.chunk_count = manifest.chunk_count
    report.vector_count = manifest.vector_count
    report.manifest_embedding = {
        "provider": manifest.embedding_provider,
        "model": manifest.embedding_model,
        "model_path": manifest.embedding_model_path,
        "dimensions": manifest.embedding_dimensions,
        "faiss_dimension": manifest.faiss_dimension,
    }

    reasons: list[str] = []
    if manifest.schema_version != INDEX_MANIFEST_SCHEMA_VERSION:
        reasons.append(IndexStaleReason.MANIFEST_SCHEMA_CHANGED.value)

    current_provider = str(identity.get("provider") or "")
    current_model = str(identity.get("model") or "")

    if manifest.embedding_provider and current_provider and manifest.embedding_provider != current_provider:
        reasons.append(IndexStaleReason.EMBEDDING_PROVIDER_CHANGED.value)
    if manifest.embedding_model and current_model and manifest.embedding_model != current_model:
        reasons.append(IndexStaleReason.EMBEDDING_MODEL_CHANGED.value)

    # 维度取 embedding_dimensions 与 faiss_dimension 的并集优先值：
    # 前者是"配置声明"，后者是"索引实际"。任一不一致都意味着维度变了。
    manifest_dimension = _optional_int(manifest.embedding_dimensions) or _optional_int(manifest.faiss_dimension)
    current_dimension = _optional_int(identity.get("dimensions")) or _optional_int(identity.get("faiss_dimension"))
    if manifest_dimension and current_dimension and int(manifest_dimension) != int(current_dimension):
        reasons.append(IndexStaleReason.EMBEDDING_DIMENSION_CHANGED.value)

    if tokenizer_version and manifest.tokenizer_version and manifest.tokenizer_version != tokenizer_version:
        reasons.append(IndexStaleReason.TOKENIZER_VERSION_CHANGED.value)

    if int(manifest.chunk_size) != int(chunk_size) or int(manifest.chunk_overlap) != int(chunk_overlap):
        reasons.append(IndexStaleReason.CHUNK_POLICY_CHANGED.value)

    current_files = fingerprint_knowledge_files(knowledge_dir)
    added, modified, removed = _diff_files(manifest.files, current_files)
    if added:
        reasons.append(IndexStaleReason.KNOWLEDGE_FILES_ADDED.value)
    if modified:
        reasons.append(IndexStaleReason.KNOWLEDGE_FILES_MODIFIED.value)
    if removed:
        reasons.append(IndexStaleReason.KNOWLEDGE_FILES_REMOVED.value)

    report.added_files = added
    report.modified_files = modified
    report.removed_files = removed
    report.file_count = len(current_files)
    report.reasons = reasons
    report.stale = bool(reasons)
    report.status = IndexFreshnessStatus.STALE if reasons else IndexFreshnessStatus.FRESH
    report.hint = describe_freshness(report)
    return report


def describe_freshness(report: IndexFreshnessReport) -> str:
    """把原因码翻译成给人看的一句话，优先级从"必须重建"到"建议重建"。"""
    if report.status == IndexFreshnessStatus.FRESH:
        return "索引与知识库一致。"
    if IndexStaleReason.MANIFEST_MISSING.value in report.reasons:
        return "未找到索引清单，无法确认索引是否与知识库一致；建议执行一次索引重建。"
    if IndexStaleReason.EMBEDDING_DIMENSION_CHANGED.value in report.reasons:
        return "embedding 维度与索引不一致，必须重建索引后才能检索。"
    if (
        IndexStaleReason.EMBEDDING_MODEL_CHANGED.value in report.reasons
        or IndexStaleReason.EMBEDDING_PROVIDER_CHANGED.value in report.reasons
    ):
        return "embedding 模型或提供方已变化，建议重建索引。"
    if IndexStaleReason.TOKENIZER_VERSION_CHANGED.value in report.reasons:
        return "检索分词实现已升级，建议重建索引。"
    if IndexStaleReason.CHUNK_POLICY_CHANGED.value in report.reasons:
        return "chunk 策略已变化，建议重建索引。"
    if IndexStaleReason.MANIFEST_SCHEMA_CHANGED.value in report.reasons:
        return "索引清单结构已升级，建议重建索引。"

    changed = len(report.added_files) + len(report.modified_files) + len(report.removed_files)
    if changed:
        return f"知识库有 {changed} 个文件发生变化，索引已过期。"
    return "索引已过期，建议重建。"


def _diff_files(
    manifest_files: list[KnowledgeFileFingerprint],
    current_files: list[KnowledgeFileFingerprint],
) -> tuple[list[str], list[str], list[str]]:
    expected = {item.path: item for item in manifest_files}
    actual = {item.path: item for item in current_files}

    added = sorted(path for path in actual if path not in expected)
    removed = sorted(path for path in expected if path not in actual)
    modified = sorted(
        path
        for path, item in actual.items()
        if path in expected and _file_changed(expected[path], item)
    )
    return added, modified, removed


def _file_changed(before: KnowledgeFileFingerprint, after: KnowledgeFileFingerprint) -> bool:
    """先比 size（最快），size 不同直接判变；size 相同再比 mtime，最后才用 sha1 定论。"""
    if before.size != after.size:
        return True
    if abs(before.mtime - after.mtime) > _MTIME_TOLERANCE:
        if before.sha1 and after.sha1:
            return before.sha1 != after.sha1
        return True
    return False


def _relative_path(path: Path, root: str | Path | None) -> str:
    if root is not None:
        try:
            path = path.relative_to(Path(root))
        except ValueError:
            pass
    return str(path).replace("\\", "/")


def _sha1_of_file(path: Path) -> str:
    try:
        if path.stat().st_size > _HASH_READ_LIMIT:
            return ""
        digest = hashlib.sha1()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(_HASH_CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()[:16]
    except OSError:
        return ""


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
