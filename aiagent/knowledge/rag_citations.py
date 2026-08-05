from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

class RAGCitation(BaseModel):
    citation_id: str
    rank: int
    chunk_id: str = ""
    doc_id: str = ""
    title: str = ""
    source_path: str = ""
    source_name: str = ""
    score: float = 0.0
    cosine_score: float | None = None
    bm25_rank: int | None = None
    vector_rank: int | None = None
    retrieval_sources: list[str] = Field(default_factory=list)
    preview: str = ""

def build_rag_citations(
        chunks: list[dict[str,Any]],
        *,
        max_citations: int = 4,
        preview_chars: int = 160,
) -> list[RAGCitation]:
    citations: list[RAGCitation] = []

    for rank, chunk in enumerate(chunks[:max_citations], start=1):
        source_path = _safe_source_path(str(chunk.get("source_path", "")))
        source_name = Path(source_path).name if source_path else ""

        citation = RAGCitation(
            citation_id=f"rag-{rank}",
            rank=rank,
            chunk_id=str(chunk.get("chunk_id", "")),
            doc_id=str(chunk.get("doc_id", "")),
            title=str(chunk.get("title", "")),
            source_path=source_path,
            source_name=source_name,
            score=_float(chunk.get("score")),
            cosine_score=_optional_float(chunk.get("cosine_score")),
            bm25_rank=_optional_int(chunk.get("bm25_rank")),
            vector_rank=_optional_int(chunk.get("vector_rank")),
            retrieval_sources=_string_list(chunk.get("retrieval_sources")),
            preview=_preview(
                str(chunk.get("preview") or chunk.get("content") or ""),
                preview_chars=preview_chars,
            ),
        )
        citations.append(citation)

    return citations

def citations_to_metadata(citations: list[RAGCitation], prefix: str = "rag") -> dict[str, str]:
    return {
        f"{prefix}_citation_count": str(len(citations)),
        f"{prefix}_citation_sources": ",".join(
            citation.source_name or citation.source_path
            for citation in citations
            if citation.source_name or citation.source_path
        ),
        f"{prefix}_citation_titles": ",".join(
            citation.title for citation in citations if citation.title
        ),
    }

def _safe_source_path(source_path: str) -> str:
    value = source_path.strip().replace("\\", "/")
    if not value:
        return ""

    marker = "data/knowledge/public/"
    if marker in value:
        return value.split(marker,1)[1]

    if ":" in value or value.startswith("/"):
        return Path(value).name

    return value

def _preview(text:str,*,preview_chars:int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= preview_chars:
        return compact
    return compact[:preview_chars].rstrip() + "..."

def _float(value:Any) -> float:
    if isinstance(value, (int,float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item) for item in value if str(item).strip()})