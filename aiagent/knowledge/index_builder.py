"""Knowledge index builder placeholder."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from aiagent.knowledge.document_loader import DocumentLoader
from aiagent.knowledge.rag_pipeline import RAGPipeline
from aiagent.knowledge.reranker import SimpleReranker
from aiagent.knowledge.retriever import HybridRetriever
from aiagent.knowledge.vector_store import LangChainVectorStore


class KnowledgeIndexBuilder:
    def __init__(
        self,
        embedding_model_name: str,
        embedding_model_path: str = "",
        knowledge_dir: str | Path | None = None,
        bm25_top_k: int = 8,
        vector_top_k: int = 8,
        chunk_size: int = 520,
        chunk_overlap: int = 80,
        final_top_k: int = 4,
    ) -> None:
        self.pipeline = RAGPipeline(
            loader=DocumentLoader(),
            retriever=HybridRetriever(
                bm25_top_k=bm25_top_k,
                vector_top_k=vector_top_k,
            ),
            vector_store=LangChainVectorStore(
                embedding_model_name=embedding_model_name,
                embedding_model_path=embedding_model_path,
            ),
            reranker=SimpleReranker(),
            knowledge_dir=knowledge_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            final_top_k=final_top_k,
        )

    def build(self, force_rebuild: bool = True) -> dict[str, Any]:
        return self.pipeline.build_index(force_rebuild=force_rebuild)

    def test_query(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        self.pipeline.ensure_ready()
        return self.pipeline.debug_retrieve(query=query, top_k=top_k)
