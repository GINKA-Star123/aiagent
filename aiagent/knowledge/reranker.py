"""Reranker placeholder."""

from __future__ import annotations

from aiagent.knowledge.retriever import RetrievedChunk


class SimpleReranker:
    def rerank(
            self,
            query:str,
            chunks: list[RetrievedChunk],
            top_k : int = 4,
    ) -> list[RetrievedChunk]:
        query_lower = query.lower()
        reranked: list[RetrievedChunk] = []

        for chunk in chunks:
            bonus = 0.0

            if len(chunk.retrieval_sources) >=2:
                bonus +=0.25
            
            if any(term in chunk.title.lower() for term in chunk.matched_terms):
                bonus +=0.15
            
            if "规则" in chunk.title or "示例" in chunk.title or "设定" in chunk.title:
                bonus += 0.08

            if chunk.title.lower() in query_lower:
                bonus += 0.2

            reranked.append(
                RetrievedChunk(
                    chunk_id = chunk.chunk_id,
                    doc_id = chunk.doc_id,
                    title = chunk.title,
                    source_path= chunk.source_path,
                    content = chunk.content,
                    score = chunk.score+bonus,
                    matched_terms= chunk.matched_terms,
                    retrieval_sources= chunk.retrieval_sources,
                )
            )
        reranked.sort(key = lambda item:item.score,reverse=True)
        return reranked[:top_k]