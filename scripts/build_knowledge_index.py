"""Build knowledge index for the RAG pipeline."""
from aiagent.knowledge.document_loader import DocumentLoader
from aiagent.knowledge.rag_pipeline import RAGPipeline
from aiagent.knowledge.retriever import HybridRetriever
from aiagent.knowledge.reranker import SimpleReranker
from aiagent.knowledge.vector_store import LangChainVectorStore
from config.settings import settings


def main() -> None:
    pipeline = RAGPipeline(
        loader=DocumentLoader(),
        retriever=HybridRetriever(
            bm25_top_k=settings.rag_bm25_top_k,
            vector_top_k=settings.rag_vector_top_k,
        ),
        vector_store=LangChainVectorStore(
            embedding_model_name=settings.rag_embedding_model_name,
            embedding_model_path=settings.rag_embedding_model_path,
        ),
        reranker=SimpleReranker(),
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        final_top_k=settings.rag_final_top_k,
    )

    stats = pipeline.build_index(force_rebuild=True)
    print("=== KNOWLEDGE INDEX BUILT ===")
    print(stats)

    query = "如果观众说自己考试紧张，我应该怎么安慰？"
    print("=== RAG DEBUG ===")
    for item in pipeline.debug_retrieve(query=query, top_k=4):
        print(item)

    print("=== PROMPT CONTEXT ===")
    print(pipeline.format_for_prompt(query=query, top_k=4))


if __name__ == "__main__":
    main()
