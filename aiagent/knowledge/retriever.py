"""Hybrid retriever with BM25 + FAISS."""
from __future__ import annotations

import re

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
    matched_terms: list[str] = Field(default_factory=list)
    retrieval_sources: list[str] = Field(default_factory=list)


class HybridRetriever:
    def __init__(
        self,
        bm25_top_k: int = 6,
        vector_top_k: int = 6,
    ) -> None:
        self.bm25_top_k = bm25_top_k
        self.vector_top_k = vector_top_k
        self.bm25_retriever: BM25Retriever | None = None
        self.documents: list[Document] = []

    def build(self, documents: list[Document]) -> None:
        self.documents = documents
        self.bm25_retriever = BM25Retriever.from_documents(documents)
        self.bm25_retriever.k = self.bm25_top_k

    def retrieve(
        self,
        query: str,
        vector_store: LangChainVectorStore,
        top_k: int = 8,
    ) -> list[RetrievedChunk]:
        query_terms = self._tokenize(query)
        merged: dict[str, RetrievedChunk] = {}

        if self.bm25_retriever is not None:
            bm25_docs = self.bm25_retriever.invoke(query)
            self._merge_docs(
                merged=merged,
                docs=bm25_docs,
                query_terms=query_terms,
                source_name="bm25",
                base_score=1.0,
            )

        vector_docs = vector_store.similarity_search(query, k=self.vector_top_k)
        self._merge_docs(
            merged=merged,
            docs=vector_docs,
            query_terms=query_terms,
            source_name="vector",
            base_score=0.9,
        )

        items = list(merged.values())
        items.sort(key=lambda item: item.score, reverse=True)
        return items[:top_k]

    def _merge_docs(
        self,
        merged: dict[str, RetrievedChunk],
        docs: list[Document],
        query_terms: list[str],
        source_name: str,
        base_score: float,
    ) -> None:
        for rank, doc in enumerate(docs):
            metadata = doc.metadata
            chunk_id = str(metadata.get("chunk_id", "unknown-chunk"))
            title = str(metadata.get("title", "untitled"))
            content = doc.page_content.strip()
            matched_terms = self._match_terms(query_terms, title, content)
            score = base_score - rank * 0.03 + len(matched_terms) * 0.08

            if chunk_id in merged:
                existing = merged[chunk_id]
                existing.score = max(existing.score, score)
                existing.matched_terms = sorted(set(existing.matched_terms + matched_terms))
                existing.retrieval_sources = sorted(set(existing.retrieval_sources + [source_name]))
                merged[chunk_id] = existing
                continue

            merged[chunk_id] = RetrievedChunk(
                chunk_id=chunk_id,
                doc_id=str(metadata.get("doc_id", "unknown-doc")),
                title=title,
                source_path=str(metadata.get("source_path", "")),
                content=content,
                score=score,
                matched_terms=matched_terms,
                retrieval_sources=[source_name],
            )

    def _tokenize(self, text: str) -> list[str]:
        lowered = text.lower()
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_]{2,}", lowered)

        unique: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            if token not in seen:
                seen.add(token)
                unique.append(token)
        return unique

    def _match_terms(self, query_terms: list[str], title: str, content: str) -> list[str]:
        title_lower = title.lower()
        content_lower = content.lower()

        matched: list[str] = []
        for term in query_terms:
            if term in title_lower or term in content_lower:
                matched.append(term)

        return matched


