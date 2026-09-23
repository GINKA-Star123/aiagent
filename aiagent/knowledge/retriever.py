from __future__ import annotations

import re
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from pydantic import BaseModel, Field

from aiagent.knowledge.vector_store import LangChainVectorStore

RAW_CONTENT_KEY = "_bm25_raw_content"
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

        bm25_texts = [self._searchable_text(doc) for doc in documents]
        bm25_metadatas = [
            {**dict(doc.metadata or {}), RAW_CONTENT_KEY: doc.page_content}
            for doc in documents
        ]

        self.bm25_retriever = BM25Retriever.from_texts(
            bm25_texts,
            metadatas=bm25_metadatas,
            preprocess_func=self._tokenize,
        )
        self.bm25_retriever.k = self.bm25_top_k

    def _searchable_text(self, doc: Document) -> str:
        """BM25 的可检索文本 = 标识头 + 正文。

        标识头来自 document_loader 推断出的 metadata，只包含名称类 token，
        不含语义描述，避免稀释相关性。

        额外补一类 token：文件名词干。原因：
        _tokenize 不会把 "producer.md" 拆成 ["producer", "md"]，
        而很多文档正文里根本不含英文名（例如 producer.md 正文 0 次 "producer"），
        导致英文查询永远命中不到它。这里把 stem 按非字母数字切分后再注入一遍。
        """
        metadata = dict(doc.metadata or {})
        parts: list[str] = []

        for key in ("title", "character", "file_name", "source_path"):
            value = str(metadata.get(key, "") or "").strip()
            if value:
                parts.append(value)

        for key in {"aliases", "search_aliases"}:
            values = metadata.get(key) or []
            if isinstance(values, (list, tuple)):
                parts.extend(str(item).strip() for item in values if str(item).strip())

        # 文件名词干（producer.md -> producer / md）
        file_stem = Path(str(metadata.get("file_name") or "")).stem
        parts.extend(
            token for token in re.split(r"[^0-9A-Za-z]+", file_stem) if token
        )

        header = " ".join(dict.fromkeys(part for part in parts if part))

        if not header:
            return doc.page_content or ""

        return f"{header}\n{doc.page_content or ''}"

    def _restore_document(self, doc: Document) -> Document:
        """
        把BM25返回结果里的可检索文本还原成原始正文
        """

        metadata = dict(doc.metadata or {})
        raw_content = metadata.pop(RAW_CONTENT_KEY, None)

        if raw_content is None:
            return doc

        return Document(page_content=str(raw_content),metadata=metadata)
        
    def retrieve(self, query: str, vector_store: LangChainVectorStore, top_k: int = 10) -> list[RetrievedChunk]:
        query = query.strip()
        if not query:
            return []

        candidates: list[_Candidate] = []

        if self.bm25_retriever is not None:
            for rank, doc in enumerate(self.bm25_retriever.invoke(query), start=1):
                candidates.append(_Candidate(doc=self._restore_document(doc), source="bm25", rank=rank))

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
            if len(block) < 2:
                chinese_terms.append(block)
                continue

            chinese_terms.append(block)

            
            if len(block) >= 5:
                chinese_terms.extend(block[i : i + 3] for i in range(len(block) - 2))

        seen: set[str] = set()
        output: list[str] = []
        for term in english_terms + chinese_terms:
            if term not in seen:
                seen.add(term)
                output.append(term)
        return output
