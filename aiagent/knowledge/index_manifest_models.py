from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IndexFreshnessStatus(StrEnum):
    UNKNOWN = "unknown"
    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"


class IndexStaleReason(StrEnum):
    """索引过期的机器可读原因码，供日志/接口/前端判断。"""

    MANIFEST_MISSING = "manifest_missing"
    MANIFEST_SCHEMA_CHANGED = "manifest_schema_changed"
    KNOWLEDGE_FILES_ADDED = "knowledge_files_added"
    KNOWLEDGE_FILES_MODIFIED = "knowledge_files_modified"
    KNOWLEDGE_FILES_REMOVED = "knowledge_files_removed"
    EMBEDDING_PROVIDER_CHANGED = "embedding_provider_changed"
    EMBEDDING_MODEL_CHANGED = "embedding_model_changed"
    EMBEDDING_DIMENSION_CHANGED = "embedding_dimension_changed"
    CHUNK_POLICY_CHANGED = "chunk_policy_changed"
    TOKENIZER_VERSION_CHANGED = "tokenizer_version_changed"


class KnowledgeFileFingerprint(BaseModel):
    """单个知识文件的指纹。path 相对 knowledge_dir，保证换机器可比对。"""

    path: str = ""
    size: int = 0
    mtime: float = 0.0
    sha1: str = ""


class IndexBuildManifest(BaseModel):
    """一次索引构建完成时的"出生证明"。"""

    schema_version: int = 1
    built_at: str = ""
    knowledge_dir: str = ""
    docs_index_path: str = ""
    faiss_dir: str = ""
    embedding_provider: str = ""
    embedding_model: str = ""
    embedding_model_path: str = ""
    embedding_dimensions: int | None = None
    faiss_dimension: int | None = None
    chunk_size: int = 0
    chunk_overlap: int = 0
    tokenizer_version: str = ""
    chunk_count: int = 0
    vector_count: int = 0
    files: list[KnowledgeFileFingerprint] = Field(default_factory=list)


class IndexFreshnessReport(BaseModel):
    """当前索引 vs 当前知识库/当前 embedding 配置的比对结论。"""

    ok: bool = True
    status: IndexFreshnessStatus = IndexFreshnessStatus.UNKNOWN
    stale: bool = False
    reasons: list[str] = Field(default_factory=list)
    hint: str = ""
    manifest_path: str = ""
    checked_at: str = ""
    built_at: str = ""
    knowledge_dir: str = ""
    current_embedding: dict[str, Any] = Field(default_factory=dict)
    manifest_embedding: dict[str, Any] = Field(default_factory=dict)
    added_files: list[str] = Field(default_factory=list)
    modified_files: list[str] = Field(default_factory=list)
    removed_files: list[str] = Field(default_factory=list)
    file_count: int = 0
    chunk_count: int = 0
    vector_count: int = 0