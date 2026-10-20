from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RAGSuite = Literal["smoke", "core", "hard"]
RAGStageName = Literal[
    "chunking",
    "index",
    "retrieval",
    "rerank",
    "injection",
    "prompt",
    "end_to_end",
]


class RetrievalExpectation(BaseModel):
    """Candidate-stage expectations: before and after reranking."""

    expected_source_paths: list[str] = Field(default_factory=list)
    required_source_paths: list[str] = Field(default_factory=list)
    forbidden_source_paths: list[str] = Field(default_factory=list)
    expected_content_terms: list[str] = Field(default_factory=list)
    top_k: int = 4
    max_rank: int = 3


class RerankExpectation(BaseModel):
    """Final top-k ordering and section expectations."""

    expected_top1_source_paths: list[str] = Field(default_factory=list)
    expected_sections: list[str] = Field(default_factory=list)
    max_top1_rank: int = 1
    min_section_hits: int = 0


class InjectionExpectation(BaseModel):
    """Confidence / should_inject / citations expectations."""

    should_inject: bool = True
    allowed_levels: list[str] = Field(default_factory=lambda: ["high", "medium"])
    allowed_statuses: list[str] = Field(default_factory=lambda: ["passed"])
    min_citations: int = 1
    max_citations: int = 4
    required_citation_sources: list[str] = Field(default_factory=list)
    forbidden_citation_sources: list[str] = Field(default_factory=list)


class PromptExpectation(BaseModel):
    """Final injected prompt-context expectations."""

    must_contain: list[str] = Field(default_factory=list)
    must_not_contain: list[str] = Field(default_factory=list)
    required_terms: list[str] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)
    max_chars: int = 6000
    expect_empty: bool = False


class RAGEvalCase(BaseModel):
    case_id: str
    suite: RAGSuite
    category: str
    query: str
    difficulty: str = "normal"
    tags: list[str] = Field(default_factory=list)
    stages: list[str] = Field(
        default_factory=lambda: ["retrieval", "rerank", "injection", "prompt"]
    )
    retrieval: RetrievalExpectation = Field(default_factory=RetrievalExpectation)
    rerank: RerankExpectation = Field(default_factory=RerankExpectation)
    injection: InjectionExpectation | None = None
    prompt: PromptExpectation | None = None
    note: str = ""


class ChunkCase(BaseModel):
    case_id: str
    source_path: str
    expected_character: str = ""
    expected_topic: str = ""
    expected_doc_kind: str = ""
    required_metadata: list[str] = Field(default_factory=list)
    required_alias: str = ""
    required_search_alias: str = ""
    required_section: str = ""
    must_keep_together: list[list[str]] = Field(default_factory=list)
    min_chunks: int = 1
    max_chunks: int = 1000
    min_chunk_chars: int = 20
    max_chunk_chars: int = 1200
    forbidden_terms: list[str] = Field(default_factory=list)
    note: str = ""


class StageCheck(BaseModel):
    passed: bool = True
    failures: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ChunkCaseResult(BaseModel):
    case_id: str
    source_path: str
    passed: bool
    failures: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class RAGEvalCaseResult(BaseModel):
    case_id: str
    suite: str
    category: str
    query: str
    passed: bool
    stages: dict[str, StageCheck] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    top_sources: list[str] = Field(default_factory=list)
    error: str = ""


class RAGEvalStageSummary(BaseModel):
    stage: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    failures: dict[str, int] = Field(default_factory=dict)


class RAGEvalSummary(BaseModel):
    suite: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    stage_summaries: list[RAGEvalStageSummary] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class RAGEvalReport(BaseModel):
    ok: bool
    generated_at: str
    suite: str
    cases_path: str
    chunk_cases_path: str
    knowledge_dir: str
    corpus: dict[str, Any] = Field(default_factory=dict)
    summary: RAGEvalSummary
    chunk_summary: RAGEvalStageSummary
    chunk_results: list[ChunkCaseResult] = Field(default_factory=list)
    index_audit: StageCheck = Field(default_factory=StageCheck)
    results: list[RAGEvalCaseResult] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)
    threshold_failures: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
