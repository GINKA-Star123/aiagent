from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from aiagent.knowledge.document_loader import DocumentLoader
from aiagent.knowledge.reranker import SimpleReranker
from aiagent.knowledge.retriever import HybridRetriever, RetrievedChunk
from aiagent.knowledge.vector_store import LangChainVectorStore
from config.paths import KNOWLEDGE_CACHE_DIR, KNOWLEDGE_PUBLIC_DIR


class RAGPipeline:
    def __init__(
        self,
        loader: DocumentLoader,
        retriever: HybridRetriever,
        vector_store: LangChainVectorStore,
        reranker: SimpleReranker,
        knowledge_dir: str | Path | None = None,
        docs_index_path: str | Path | None = None,
        faiss_dir: str | Path | None = None,
        chunk_size: int = 520,
        chunk_overlap: int = 80,
        final_top_k: int = 4,
    ) -> None:
        self.loader = loader
        self.retriever = retriever
        self.vector_store = vector_store
        self.reranker = reranker
        self.knowledge_dir = Path(knowledge_dir) if knowledge_dir else KNOWLEDGE_PUBLIC_DIR
        self.docs_index_path = Path(docs_index_path) if docs_index_path else KNOWLEDGE_CACHE_DIR / "split_docs.json"
        self.faiss_dir = Path(faiss_dir) if faiss_dir else KNOWLEDGE_CACHE_DIR / "faiss_index"
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.final_top_k = final_top_k
        self.documents: list[Document] = []

    def build_index(self, force_rebuild: bool = False) -> dict[str, Any]:
        if not force_rebuild and self.docs_index_path.exists() and self.faiss_dir.exists():
            self._load_documents()
            self.vector_store.load(self.faiss_dir)
            self.retriever.build(self.documents)
            return self.stats()

        raw_docs = self.loader.load_directory(self.knowledge_dir)
        split_docs = self.loader.split_documents(
            raw_docs,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        if not split_docs:
            raise RuntimeError(f"No knowledge documents were loaded from {self.knowledge_dir}")

        self.documents = split_docs
        self._save_documents(split_docs)
        self.vector_store.build(split_docs)
        self.vector_store.save(self.faiss_dir)
        self.retriever.build(split_docs)
        return self.stats()

    def ensure_ready(self) -> None:
        if self.documents:
            return

        if self.docs_index_path.exists() and self.faiss_dir.exists():
            self._load_documents()
            self.vector_store.load(self.faiss_dir)
            self.retriever.build(self.documents)
            return

        self.build_index(force_rebuild=True)

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        self.ensure_ready()
        final_top_k = top_k or self.final_top_k
        coarse = self.retriever.retrieve(
            query=query,
            vector_store=self.vector_store,
            top_k=max(final_top_k * 3, 10),
        )
        return self.reranker.rerank(query=query, chunks=coarse, top_k=final_top_k)

    def search(self, query: str, top_k: int = 4) -> list[str]:
        return [
            self._format_chunk(chunk, index)
            for index, chunk in enumerate(self.retrieve(query=query, top_k=top_k), start=1)
        ]

    def format_for_prompt(self, query: str, top_k: int = 4) -> str:
        chunks = self.search(query=query, top_k=top_k)
        if not chunks:
            return "无"
        return "\n\n".join(chunks)

    def debug_retrieve(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        return [
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "source_path": chunk.source_path,
                "score": round(chunk.score, 6),
                "bm25_rank": chunk.bm25_rank,
                "vector_rank": chunk.vector_rank,
                "cosine_score": round(chunk.cosine_score, 6) if chunk.cosine_score is not None else None,
                "retrieval_sources": chunk.retrieval_sources,
                "preview": chunk.content[:260],
            }
            for chunk in self.retrieve(query=query, top_k=top_k)
        ]

    def stats(self) -> dict[str, Any]:
        return {
            "knowledge_dir": str(self.knowledge_dir),
            "docs_index_path": str(self.docs_index_path),
            "faiss_dir": str(self.faiss_dir),
            "chunk_count": len(self.documents),
            "vector_count": self.vector_store.count(),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "final_top_k": self.final_top_k,
        }

    def _format_chunk(self, chunk: RetrievedChunk, index: int) -> str:
        source_name = Path(chunk.source_path).name if chunk.source_path else "unknown"
        cosine_score = f"{chunk.cosine_score:.4f}" if chunk.cosine_score is not None else "无"
        sources = ", ".join(chunk.retrieval_sources) if chunk.retrieval_sources else "unknown"

        return (
            f"[知识片段 {index}]\n"
            f"标题: {chunk.title}\n"
            f"来源: {source_name}\n"
            f"召回方式: {sources}\n"
            f"BM25排名: {chunk.bm25_rank if chunk.bm25_rank is not None else '无'}\n"
            f"向量排名: {chunk.vector_rank if chunk.vector_rank is not None else '无'}\n"
            f"余弦相似度: {cosine_score}\n"
            f"内容:\n{chunk.content.strip()}"
        )

    def _save_documents(self, documents: list[Document]) -> None:
        self.docs_index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [{"page_content": doc.page_content, "metadata": doc.metadata} for doc in documents]
        self.docs_index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_documents(self) -> None:
        data = json.loads(self.docs_index_path.read_text(encoding="utf-8"))
        self.documents = [
            Document(page_content=item["page_content"], metadata=item["metadata"])
            for item in data
        ]
