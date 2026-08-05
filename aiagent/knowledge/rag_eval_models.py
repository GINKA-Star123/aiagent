from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RAGEvalCase(BaseModel):
    case_id: str
    category: str = "general"
    query: str
    expected_source_paths: list[str] = Field(default_factory=list)
    expected_titles: list[str] = Field(default_factory=list)
    expected_terms: list[str] = Field(default_factory=list)
    forbidden_source_paths: list[str] = Field(default_factory=list)
    top_k: int = 4
    max_rank: int = 3
    note: str = ""

    tags: list[str] = Field(default_factory=list)
    difficulty: str = "normal"


class RAGEvalHit(BaseModel):
    chunk_id: str = ""
    doc_id: str = ""
    title: str = ""
    source_path: str = ""
    content: str = ""
    score: float = 0.0
    bm25_rank: int | None = None
    vector_rank: int | None = None
    cosine_score: float | None = None
    retrieval_sources: list[str] = Field(default_factory=list)
    preview: str = ""


class RAGEvalCaseResult(BaseModel):
    case_id: str
    category: str = "general"
    query: str = ""
    passed: bool = False
    reason: str = ""
    best_rank: int | None = None
    best_score: float | None = None
    matched_source_path: str = ""
    matched_title: str = ""
    matched_terms: list[str] = Field(default_factory=list)
    top_hits: list[RAGEvalHit] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class RAGEvalSummary(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    mrr: float = 0.0
    avg_best_rank: float = 0.0
    failures: list[dict[str, str]] = Field(default_factory=list)

class RAGEvalThresholds(BaseModel):
    min_pass_rate: float = 0.75
    min_recall_at_1: float = 0.40
    min_recall_at_3: float = 0.80
    min_mrr: float = 0.55


class RAGEvalCategorySummary(BaseModel):
    category: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    mrr: float = 0.0
    avg_best_rank: float = 0.0
    failure_reasons: dict[str,int] = Field(default_factory=dict)

class RAGEvalReport(BaseModel):
    ok: bool
    generated_at: str
    retriever_name: str = "bm25_baseline"
    cases_path: str = ""
    knowledge_dir: str = ""

    thresholds: RAGEvalThresholds
    summary: RAGEvalSummary
    category_summaries: list[RAGEvalCategorySummary] = Field(default_factory=list)
    results: list[RAGEvalCaseResult] = Field(default_factory=list)

    threshold_failures: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)