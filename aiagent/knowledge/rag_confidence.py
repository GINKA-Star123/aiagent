from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel,Field

RAGConfidenceLevel = Literal["high","medium","low","none"]
RAGConfidenceStatus = Literal["passed","low_relevance","empty"]

class RAGConfidenceDecision(BaseModel):
    status: RAGConfidenceStatus = "empty"
    level: RAGConfidenceLevel = "none"
    should_inject: bool = False
    reason: str = "no_chunks"

    best_rank: int | None = None
    best_chunk_id: str = ""
    best_title: str = ""
    best_source_path: str = ""
    best_score: float = 0.0
    best_cosine: float = 0.0
    best_bm25_rank: int | None = None
    best_vector_rank: int | None = None
    best_sources: list[str] = Field(default_factory=list)

    candidate_count: int = 0
    signals: list[str] = Field(default_factory=list)

    def to_metadata(self, prefix: str = "rag") -> dict[str, str]:
        return {
            f"{prefix}_confidence_status": self.status,
            f"{prefix}_confidence_level": self.level,
            f"{prefix}_should_inject": str(self.should_inject).lower(),
            f"{prefix}_confidence_reason": self.reason,
            f"{prefix}_candidate_count": str(self.candidate_count),
            f"{prefix}_best_rank": "" if self.best_rank is None else str(self.best_rank),
            f"{prefix}_best_chunk_id": self.best_chunk_id,
            f"{prefix}_best_title": self.best_title,
            f"{prefix}_best_source_path": self.best_source_path,
            f"{prefix}_best_score": f"{self.best_score:.6f}",
            f"{prefix}_best_cosine": f"{self.best_cosine:.6f}",
            f"{prefix}_best_sources": ",".join(self.best_sources),
            f"{prefix}_confidence_signals": ",".join(self.signals),
        }

def evaluate_rag_confidence(
    chunks: list[dict[str, Any]],
    *,
    min_cosine_score: float = 0.38,
    min_score: float = 0.045,
    max_strong_rank: int = 3,
    allow_bm25_only: bool = True,
) -> RAGConfidenceDecision:
    if not chunks:
        return RAGConfidenceDecision(
            status="empty",
            level="none",
            should_inject=False,
            reason="no_chunks",
            candidate_count=0,
        )

    best = _best_chunk(chunks)
    rank = best["rank"]
    chunk = best["chunk"]

    sources = _string_list(chunk.get("retrieval_sources"))
    score = _float(chunk.get("score"))
    cosine = _float(chunk.get("cosine_score"))
    bm25_rank = _optional_int(chunk.get("bm25_rank"))
    vector_rank = _optional_int(chunk.get("vector_rank"))

    signals: list[str] = []

    has_bm25 = "bm25" in sources
    has_vector = "vector" in sources
    is_strong_rank = rank <= max_strong_rank

    if has_bm25 and has_vector and is_strong_rank:
        signals.append("hybrid_top_rank")
        return _decision(
            chunk=chunk,
            rank=rank,
            status="passed",
            level="high",
            should_inject=True,
            reason="hybrid_match",
            candidate_count=len(chunks),
            signals=signals,
        )

    if cosine >= min_cosine_score and is_strong_rank:
        signals.append("vector_cosine_threshold")
        return _decision(
            chunk=chunk,
            rank=rank,
            status="passed",
            level="high",
            should_inject=True,
            reason="vector_score",
            candidate_count=len(chunks),
            signals=signals,
        )

    if allow_bm25_only and bm25_rank is not None and bm25_rank <= 2 and score >= min_score:
        signals.append("bm25_top_score")
        return _decision(
            chunk=chunk,
            rank=rank,
            status="passed",
            level="medium",
            should_inject=True,
            reason="bm25_top_score",
            candidate_count=len(chunks),
            signals=signals,
        )

    if score >= min_score and is_strong_rank:
        signals.append("rerank_score_threshold")
        return _decision(
            chunk=chunk,
            rank=rank,
            status="passed",
            level="medium",
            should_inject=True,
            reason="rerank_score",
            candidate_count=len(chunks),
            signals=signals,
        )

    signals.append("no_reliable_candidate")
    return _decision(
        chunk=chunk,
        rank=rank,
        status="low_relevance",
        level="low",
        should_inject=False,
        reason="no_reliable_candidate",
        candidate_count=len(chunks),
        signals=signals,
    )

def _best_chunk(chunks:list[dict[str,Any]]) -> dict[str,Any]:
    best_rank = 1
    best_chunk = chunks[0]
    best_score = _float(best_chunk.get("score"))

    for rank, chunk in enumerate(chunks, start=1):
        score = _float(chunk.get("score"))
        if score > best_score:
            best_rank = rank
            best_chunk = chunk
            best_score = score

    return {
        "rank": best_rank,
        "chunk": best_chunk,
    }

def _decision(
        *,
        chunk:dict[str,Any],
        rank:int,
        status:RAGConfidenceStatus,
        level:RAGConfidenceLevel,
        should_inject:bool,
        reason:str,
        candidate_count:int,
        signals:list[str],
) -> RAGConfidenceDecision:
    sources = _string_list(chunk.get("retrieval_sources"))

    return RAGConfidenceDecision(
        status=status,
        level=level,
        should_inject=should_inject,
        reason=reason,
        best_rank=rank,
        best_chunk_id=str(chunk.get("chunk_id", "")),
        best_title=str(chunk.get("title", "")),
        best_source_path=str(chunk.get("source_path", "")),
        best_score=_float(chunk.get("score")),
        best_cosine=_float(chunk.get("cosine_score")),
        best_bm25_rank=_optional_int(chunk.get("bm25_rank")),
        best_vector_rank=_optional_int(chunk.get("vector_rank")),
        best_sources=sources,
        candidate_count=candidate_count,
        signals=signals,
    )
def _float(value:Any) -> float:
    if isinstance(value, (int,float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def _optional_int(value:Any) -> int | None:
    if isinstance(value,int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _string_list(value:Any) ->list[str]:
    if not isinstance(value,list):
        return []
    return sorted({str(item) for item in value if str(item).strip()})