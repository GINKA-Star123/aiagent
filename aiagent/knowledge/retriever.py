from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from pydantic import BaseModel, Field

from aiagent.knowledge.vector_store import LangChainVectorStore


class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    source_path: str
    content: str
    score: float
    bm25_rank: int | None = None
    vector_rank: int | None = None
    cosine_score: float | None = None
    retrieval_sources: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class _Candidate:
    doc: Document
    source: str
    rank: int
    cosine_score: float | None = None


class HybridRetriever:
    def __init__(self, bm25_top_k: int = 8, vector_top_k: int = 8, rrf_k: int = 60) -> None:
        self.bm25_top_k = bm25_top_k
        self.vector_top_k = vector_top_k
        self.rrf_k = rrf_k
        self.bm25_retriever: BM25Retriever | None = None
        self.documents: list[Document] = []

    def build(self, documents: list[Document]) -> None:
        self.documents = documents
        self.bm25_retriever = BM25Retriever.from_documents(
            documents,
            preprocess_func=self._tokenize,
        )
        self.bm25_retriever.k = self.bm25_top_k

    def retrieve(self, query: str, vector_store: LangChainVectorStore, top_k: int = 10) -> list[RetrievedChunk]:
        query = query.strip()
        if not query:
            return []

        candidates: list[_Candidate] = []

        if self.bm25_retriever is not None:
            for rank, doc in enumerate(self.bm25_retriever.invoke(query), start=1):
                candidates.append(_Candidate(doc=doc, source="bm25", rank=rank))

        for rank, (doc, cosine_score) in enumerate(
            vector_store.similarity_search_with_score(query, k=self.vector_top_k),
            start=1,
        ):
            candidates.append(
                _Candidate(doc=doc, source="vector", rank=rank, cosine_score=cosine_score)
            )

        return self._fuse(candidates, top_k=top_k)

    def _fuse(self, candidates: list[_Candidate], top_k: int) -> list[RetrievedChunk]:
        scores: dict[str, float] = defaultdict(float)
        doc_by_id: dict[str, Document] = {}
        sources_by_id: dict[str, set[str]] = defaultdict(set)
        bm25_rank_by_id: dict[str, int] = {}
        vector_rank_by_id: dict[str, int] = {}
        cosine_by_id: dict[str, float] = {}

        for candidate in candidates:
            chunk_id = self._chunk_id(candidate.doc)
            doc_by_id[chunk_id] = candidate.doc
            sources_by_id[chunk_id].add(candidate.source)
            scores[chunk_id] += 1.0 / (self.rrf_k + candidate.rank)

            if candidate.source == "bm25":
                bm25_rank_by_id[chunk_id] = min(candidate.rank, bm25_rank_by_id.get(chunk_id, candidate.rank))

            if candidate.source == "vector":
                vector_rank_by_id[chunk_id] = min(candidate.rank, vector_rank_by_id.get(chunk_id, candidate.rank))
                if candidate.cosine_score is not None:
                    cosine_by_id[chunk_id] = max(candidate.cosine_score, cosine_by_id.get(chunk_id, 0.0))

        chunks: list[RetrievedChunk] = []
        for chunk_id, score in scores.items():
            doc = doc_by_id[chunk_id]
            metadata = doc.metadata
            cosine_score = cosine_by_id.get(chunk_id)
            if cosine_score is not None:
                score += cosine_score * 0.03

            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    doc_id=str(metadata.get("doc_id", "unknown-doc")),
                    title=str(metadata.get("title", "untitled")),
                    source_path=str(metadata.get("source_path", "")),
                    content=doc.page_content.strip(),
                    score=score,
                    bm25_rank=bm25_rank_by_id.get(chunk_id),
                    vector_rank=vector_rank_by_id.get(chunk_id),
                    cosine_score=cosine_score,
                    retrieval_sources=sorted(sources_by_id[chunk_id]),
                )
            )

        chunks.sort(key=lambda item: item.score, reverse=True)
        return chunks[:top_k]

    def _chunk_id(self, doc: Document) -> str:
        return str(doc.metadata.get("chunk_id", "unknown-chunk"))

    def _tokenize(self, text: str) -> list[str]:
        lowered = text.lower()
        english_terms = re.findall(r"[a-z0-9_./:-]{2,}", lowered)
        chinese_blocks = re.findall(r"[\u4e00-\u9fff]+", lowered)

        chinese_terms: list[str] = []
        for block in chinese_blocks:
            if len(block) <= 4:
                chinese_terms.append(block)
                continue
            chinese_terms.extend(block[i : i + 2] for i in range(len(block) - 1))
            chinese_terms.extend(block[i : i + 3] for i in range(len(block) - 2))

        seen: set[str] = set()
        output: list[str] = []
        for term in english_terms + chinese_terms:
            if term not in seen:
                seen.add(term)
                output.append(term)
        return output
