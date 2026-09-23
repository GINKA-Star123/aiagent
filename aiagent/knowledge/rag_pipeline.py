from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any
from datetime import datetime


from langchain_core.documents import Document

from aiagent.knowledge.document_loader import DocumentLoader
from aiagent.knowledge.index_manifest import (
    TOKENIZER_VERSION,
    build_index_manifest,
    evaluate_index_freshness,
    fingerprint_knowledge_files,
    load_index_manifest,
    save_index_manifest,
)
from aiagent.knowledge.index_manifest_models import IndexFreshnessReport
from aiagent.knowledge.reranker import SimpleReranker
from aiagent.knowledge.retriever import HybridRetriever, RetrievedChunk
from aiagent.knowledge.vector_store import LangChainVectorStore
from aiagent.knowledge.rag_citations import build_rag_citations
from aiagent.knowledge.rag_confidence import evaluate_rag_confidence
from config.paths import KNOWLEDGE_CACHE_DIR, KNOWLEDGE_INDEX_MANIFEST_NAME, KNOWLEDGE_PUBLIC_DIR

logger = logging.getLogger(__name__)


class RAGPipeline:
    """构建、缓存并查询项目知识索引。

    所有知识文件会合并进同一个逻辑索引。split_docs 缓存和 FAISS 目录让
    正常启动可以复用上一次构建结果。
    """

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
        manifest_path: str | Path | None = None,
        auto_rebuild_on_stale: bool = False,
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

        self.manifest_path = (Path(manifest_path) if manifest_path else self.docs_index_path.parent / KNOWLEDGE_INDEX_MANIFEST_NAME)
        self.auto_rebuild_on_stale = bool(auto_rebuild_on_stale)
        self._freshness_report: IndexFreshnessReport | None = None

        self._build_lock = threading.RLock()
        self._build_status:dict[str,Any] = {
            "running":False,
            "status":"idle",
            "started_at":None,
            "finished_at":None,
            "error":"",
            "stats":{},
        }

    def build_index(self, force_rebuild: bool = False) -> dict[str, Any]:
        """同步构建或加载 RAG 索引。"""
        with self._build_lock:
            self._build_status.update(
                {
                    "running":True,
                    "status":"running",
                    "started_at":datetime.now().isoformat(timespec="seconds"),
                    "finished_at":None,
                    "error":"",
                }
            )
        
        try:
            stats = self._build_index_inner(force_rebuild=force_rebuild)
        except Exception as exc:
            with self._build_lock:
                self._build_status.update(
                    {
                        "running":False,
                        "status":"failed",
                        "finished_at":datetime.now().isoformat(timespec="seconds"),
                        "error":str(exc),
                    }
                )
            raise 

        with self._build_lock:
            self._build_status.update(
                {
                    "running":False,
                    "status":"done",
                    "finished_at":datetime.now().isoformat(timespec="seconds"),
                    "stats":stats,
                }
            )
        return stats

    def rebuild_async(self,force_rebuild:bool = True) -> dict[str,Any]:
        """启动后台重建任务，供 /knowledge/rebuild 接口使用。"""
        with self._build_lock:
            if self._build_status.get("running"):
                return self.build_status()
            
            self._build_status.update(
                {
                    "running":True,
                    "status":"queued",
                    "started_at":datetime.now().isoformat(timespec="seconds"),
                    "finished_at":None,
                    "error":"",
                }
            )

        thread = threading.Thread(
            target=self._rebuild_worker,
            kwargs={"force_rebuild":force_rebuild},
            daemon=True
        )
        thread.start()

        return self.build_status()
    
    def build_status(self) -> dict[str,Any]:
        with self._build_lock:
            return dict(self._build_status)
        
    def _rebuild_worker(self,force_rebuild:bool) ->None:
        try:
            self.build_index(force_rebuild=force_rebuild)

        except Exception:
            pass
    
    def _build_index_inner(self, force_rebuild: bool = False) -> dict[str, Any]:
        # 快速路径：直接加载已缓存的 split docs 和 FAISS 向量，
        # 避免每次启动都重新 embedding 全部知识文件。
        # 但加载完必须比对清单，标记"索引是否已过期"。
        if not force_rebuild and self.docs_index_path.exists() and self.faiss_dir.exists():
            self._load_documents()
            self.vector_store.load(self.faiss_dir)
            self.retriever.build(self.documents)
            self._refresh_freshness()
            self._warn_if_stale()
            return self.stats()

        raw_docs = self.loader.load_directory(self.knowledge_dir)
        split_docs = self.loader.split_documents(
            raw_docs,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        if not split_docs:
            raise RuntimeError(f"No knowledge documents were loaded from {self.knowledge_dir}")

        self.documents = split_docs
        self._save_documents(split_docs)
        self.vector_store.build(split_docs)
        self.vector_store.save(self.faiss_dir)
        self.retriever.build(split_docs)
        # 构建成功后立刻写清单：记录本次构建时的 embedding 身份、
        # chunk 策略、分词版本和每个知识文件的指纹。
        self._write_manifest()
        self._freshness_report = None

        return self.stats()


    def ensure_ready(self) -> None:
        if self.documents:
            return

        if self.docs_index_path.exists() and self.faiss_dir.exists():
            self._load_documents()
            self.vector_store.load(self.faiss_dir)
            self.retriever.build(self.documents)
            self._refresh_freshness()
            self._warn_if_stale()
            return

        self.build_index(force_rebuild=True)

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        self.ensure_ready()

        final_top_k = top_k or self.final_top_k

        # 先召回更宽的候选集合，再重排到最终 prompt 预算内；
        # 这样能兼顾 BM25 精确匹配和向量召回。
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
            return "无相关知识"
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
                "content": chunk.content,
            }
            for chunk in self.retrieve(query=query, top_k=top_k)
        ]
    
    def inspect(
                self,
                query: str,
                top_k: int = 4,
                min_cosine_score: float = 0.38,
        ) -> dict[str,Any]:
            chunks = self.debug_retrieve(query=query, top_k=top_k)
            confidence = evaluate_rag_confidence(
                chunks,
                min_cosine_score=min_cosine_score,
                allow_bm25_only=True,
            )

            usable_chunks = chunks if confidence.should_inject else []
            citations = build_rag_citations(usable_chunks, max_citations=top_k)

            return {
                "ok": True,
                "query": query,
                "top_k": top_k,
                "should_inject": confidence.should_inject,
                "confidence": confidence.model_dump(mode="json"),
                "citations": [citation.model_dump(mode="json") for citation in citations],
                "chunks": chunks,
                "prompt_context": self._format_debug_chunks(usable_chunks),
            }
    def stats(self) -> dict[str, Any]:
        freshness = self.index_freshness()

        return {
            "knowledge_dir": str(self.knowledge_dir),
            "docs_index_path": str(self.docs_index_path),
            "faiss_dir": str(self.faiss_dir),
            "chunk_count": len(self.documents),
            "vector_count": self.vector_store.count(),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "final_top_k": self.final_top_k,
            "index_manifest_path": str(self.manifest_path),
            "index_tokenizer_version": TOKENIZER_VERSION,
            "index_freshness": freshness,
            "index_stale": bool(freshness.get("stale")),
            "build_status": self.build_status(),
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
    def _format_debug_chunks(self, chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return "无相关知识"

        return "\n\n".join(
            self._format_debug_chunk(chunk, index)
            for index, chunk in enumerate(chunks, start=1)
        )


    def _format_debug_chunk(self, chunk: dict[str, Any], index: int) -> str:
        source_path = str(chunk.get("source_path", ""))
        source_name = Path(source_path).name if source_path else "unknown"
        sources = chunk.get("retrieval_sources") or []
        source_text = ", ".join(str(item) for item in sources) if sources else "unknown"

        cosine_score = chunk.get("cosine_score")
        cosine_text = f"{cosine_score:.4f}" if isinstance(cosine_score, (int, float)) else "无"

        return (
            f"[知识片段 {index}]\n"
            f"标题: {chunk.get('title', '')}\n"
            f"来源: {source_name}\n"
            f"召回方式: {source_text}\n"
            f"BM25排名: {chunk.get('bm25_rank') if chunk.get('bm25_rank') is not None else '无'}\n"
            f"向量排名: {chunk.get('vector_rank') if chunk.get('vector_rank') is not None else '无'}\n"
            f"余弦相似度: {cosine_text}\n"
            f"内容:\n{str(chunk.get('content', '')).strip()}"
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

    def index_freshness(self, force_refresh: bool = False) -> dict[str, Any]:
        """索引新鲜度报告（带缓存）。任何异常都降级成 unknown，绝不抛出。"""
        if self._freshness_report is None or force_refresh:
            self._freshness_report = self._evaluate_freshness()
        return self._freshness_report.model_dump(mode="json")

    def _evaluate_freshness(self) -> IndexFreshnessReport:
        try:
            manifest = load_index_manifest(self.manifest_path)
            return evaluate_index_freshness(
                manifest=manifest,
                manifest_path=self.manifest_path,
                knowledge_dir=self.knowledge_dir,
                embedding=self._embedding_identity(),
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
        except Exception as exc:
            logger.warning("Failed to evaluate knowledge index freshness: %s", exc)
            return IndexFreshnessReport(
                ok=False,
                status="unknown", # type:ignore
                stale=False,
                reasons=["freshness_check_failed"],
                hint=f"索引新鲜度检查失败：{exc}",
                manifest_path=str(self.manifest_path),
            )

    def _refresh_freshness(self) -> None:
        self._freshness_report = self._evaluate_freshness()

    def _warn_if_stale(self) -> None:
        report = self._freshness_report
        if report is None or not report.stale:
            return

        logger.warning("Knowledge index is stale: %s", report.hint)
        if self.auto_rebuild_on_stale:
            # 只排队，不阻塞启动；rebuild_async 内部有 running 去重。
            self.rebuild_async(force_rebuild=True)

    def _write_manifest(self) -> None:
        try:
            manifest = build_index_manifest(
                knowledge_dir=self.knowledge_dir,
                docs_index_path=self.docs_index_path,
                faiss_dir=self.faiss_dir,
                embedding=self._embedding_identity(),
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                chunk_count=len(self.documents),
                vector_count=self.vector_store.count(),
                tokenizer_version=TOKENIZER_VERSION,
                files=fingerprint_knowledge_files(self.knowledge_dir),
            )
            save_index_manifest(self.manifest_path, manifest)
        except Exception as exc:
            logger.warning("Failed to write knowledge index manifest: %s", exc)

    def _embedding_identity(self) -> dict[str, Any]:
        identity_fn = getattr(self.vector_store, "identity", None)
        if callable(identity_fn):
            try:
                return dict(identity_fn()) # type:ignore
            except Exception:
                return {}
        return {}