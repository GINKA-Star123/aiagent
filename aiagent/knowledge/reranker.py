from __future__ import annotations

from aiagent.knowledge.retriever import RetrievedChunk


class SimpleReranker:
    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 4,
    ) -> list[RetrievedChunk]:
        query_lower = query.lower()
        reranked: list[RetrievedChunk] = []

        for chunk in chunks:
            score = chunk.score

            if "bm25" in chunk.retrieval_sources and "vector" in chunk.retrieval_sources:
                score += 0.08

            if chunk.cosine_score is not None:
                score += chunk.cosine_score * 0.04

            if chunk.bm25_rank is not None:
                score += max(0.0, 0.04 - chunk.bm25_rank * 0.003)

            if chunk.vector_rank is not None:
                score += max(0.0, 0.04 - chunk.vector_rank * 0.003)

            if chunk.title and chunk.title.lower() in query_lower:
                score += 0.03

            if self._has_exact_term_overlap(query_lower, chunk):
                score += 0.03

            content_len = len(chunk.content)
            if 120 <= content_len <= 1200:
                score += 0.02

            reranked.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    source_path=chunk.source_path,
                    content=chunk.content,
                    score=score,
                    bm25_rank=chunk.bm25_rank,
                    vector_rank=chunk.vector_rank,
                    cosine_score=chunk.cosine_score,
                    retrieval_sources=chunk.retrieval_sources,
                )
            )

        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[:top_k]

    def _has_exact_term_overlap(self, query_lower: str, chunk: RetrievedChunk) -> bool:
        important_terms = [
            "洛天依",
            "天依",
            "乐正绫",
            "阿绫",
            "应援词",
            "应援口号",
            "口号",
            "华风夏韵",
            "洛水天依",
            "歌曲",
            "专辑",
            "生日",
            "代表色",
            "声源",
        ]

        content = f"{chunk.title}\n{chunk.content}".lower()
        return any(term.lower() in query_lower and term.lower() in content for term in important_terms)
