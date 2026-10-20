from __future__ import annotations

from pathlib import Path
from typing import Any

from aiagent.knowledge.document_loader import DocumentLoader
from aiagent.knowledge.rag_pipeline import RAGPipeline
from aiagent.knowledge.reranker import SimpleReranker
from aiagent.knowledge.retriever import HybridRetriever


class NullVectorStore:
    """BM25-only evaluation stand-in.

    The chunking / retrieval / injection evaluation must stay offline and
    deterministic. RAGPipeline still expects a vector store object, so this
    implementation keeps the pipeline shape identical without embeddings.
    """

    def build(self, documents: list[Any]) -> None:
        return None

    def save(self, directory: str | Path) -> None:
        return None

    def load(self, directory: str | Path) -> None:
        return None

    def count(self) -> int:
        return 0

    def similarity_search_with_score(self, query: str, k: int = 6) -> list[Any]:
        return []

    def similarity_search(self, query: str, k: int = 6) -> list[Any]:
        return []


def build_eval_pipeline(
    *,
    knowledge_dir: str | Path,
    docs_index_path: str | Path,
    faiss_dir: str | Path,
    chunk_size: int = 520,
    chunk_overlap: int = 80,
    final_top_k: int = 4,
) -> RAGPipeline:
    pipeline = RAGPipeline(
        loader=DocumentLoader(),
        retriever=HybridRetriever(bm25_top_k=12, vector_top_k=0),
        vector_store=NullVectorStore(),  # type: ignore[arg-type]
        reranker=SimpleReranker(),
        knowledge_dir=knowledge_dir,
        docs_index_path=docs_index_path,
        faiss_dir=faiss_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        final_top_k=final_top_k,
    )
    pipeline.build_index(force_rebuild=True)
    return pipeline
