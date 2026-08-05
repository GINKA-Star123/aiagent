# tests/unit/test_rag_quality_policy.py
from __future__ import annotations

from aiagent.knowledge.rag_citations import build_rag_citations
from aiagent.knowledge.rag_confidence import evaluate_rag_confidence


def _chunk(
    *,
    chunk_id: str = "chunk-1",
    title: str = "乐正绫",
    source_path: str = "data/knowledge/public/YueZhengling.md",
    score: float = 0.12,
    cosine_score: float | None = 0.52,
    bm25_rank: int | None = 1,
    vector_rank: int | None = 1,
    sources: list[str] | None = None,
    content: str = "乐正绫是 VSinger 旗下虚拟歌手，代表色是阿绫红。",
) -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": "doc-1",
        "title": title,
        "source_path": source_path,
        "content": content,
        "score": score,
        "bm25_rank": bm25_rank,
        "vector_rank": vector_rank,
        "cosine_score": cosine_score,
        "retrieval_sources": sources if sources is not None else ["bm25", "vector"],
        "preview": content[:80],
    }


def test_rag_confidence_accepts_hybrid_top_match():
    decision = evaluate_rag_confidence([_chunk()])

    assert decision.should_inject is True
    assert decision.status == "passed"
    assert decision.level == "high"
    assert decision.reason == "hybrid_match"
    assert decision.best_chunk_id == "chunk-1"


def test_rag_confidence_accepts_bm25_only_when_score_is_strong():
    decision = evaluate_rag_confidence(
        [
            _chunk(
                score=0.09,
                cosine_score=None,
                vector_rank=None,
                sources=["bm25"],
            )
        ]
    )

    assert decision.should_inject is True
    assert decision.status == "passed"
    assert decision.level == "medium"
    assert decision.reason == "bm25_top_score"


def test_rag_confidence_rejects_low_relevance_chunks():
    decision = evaluate_rag_confidence(
        [
            _chunk(
                score=0.01,
                cosine_score=0.08,
                bm25_rank=8,
                vector_rank=8,
                sources=["bm25"],
                content="这是一段和用户问题没有明显关系的内容。",
            )
        ]
    )

    assert decision.should_inject is False
    assert decision.status == "low_relevance"
    assert decision.level == "low"
    assert decision.reason == "no_reliable_candidate"


def test_rag_confidence_handles_empty_chunks():
    decision = evaluate_rag_confidence([])

    assert decision.should_inject is False
    assert decision.status == "empty"
    assert decision.level == "none"
    assert decision.reason == "no_chunks"


def test_rag_citations_are_stable_and_safe():
    citations = build_rag_citations(
        [
            _chunk(
                source_path="F:\\aiagent\\data\\knowledge\\public\\YueZhengling.md",
                content="乐正绫是 VSinger 旗下虚拟歌手，代表色是阿绫红。" * 20,
            )
        ],
        max_citations=1,
        preview_chars=40,
    )

    assert len(citations) == 1

    citation = citations[0]
    assert citation.citation_id == "rag-1"
    assert citation.rank == 1
    assert citation.source_path == "YueZhengling.md"
    assert citation.source_name == "YueZhengling.md"
    assert citation.title == "乐正绫"
    assert citation.preview.endswith("...")