from __future__ import annotations

from unittest.mock import Mock

import pytest
from langchain_core.documents import Document

from aiagent.knowledge.retriever import HybridRetriever


@pytest.mark.parametrize(("file_name", "stem"), [
    ("producer.md", "producer"),
    ("starlight_alt.txt", "starlight_alt"),
    ("starlight-alt.txt", "starlight-alt"),
    ("starlight.alt.txt", "starlight.alt"),
])
def test_filename_stem_uses_the_same_token_boundaries_as_body(file_name, stem):
    retriever = HybridRetriever()
    doc = Document(page_content="Reference body", metadata={"file_name": file_name})

    terms = retriever._tokenize(retriever._searchable_text(doc))

    assert stem in terms
    assert "md" not in terms
    assert "txt" not in terms
    if stem != "producer":
        assert "starlight" not in terms


@pytest.mark.parametrize(("query", "expected_id"), [
    ("starlight", "main"),
    ("STARLIGHT", "main"),
    ("starlight_alt", "alternate"),
    ("starlightalt", "alternate"),
    ("zzqvnotindataset", None),
])
def test_similar_filename_does_not_add_an_unrequested_alias(query, expected_id):
    docs = [
        Document(
            page_content="Main reference body.",
            metadata={"chunk_id": "main", "file_name": "starlight.txt"},
        ),
        Document(
            page_content="Alternate reference body. starlightalt",
            metadata={"chunk_id": "alternate", "file_name": "starlight_alt.txt"},
        ),
    ]
    retriever = HybridRetriever(bm25_top_k=8, vector_top_k=0)
    retriever.build(docs)
    vector_store = Mock()
    vector_store.similarity_search_with_score.return_value = []

    chunks = retriever.retrieve(query, vector_store, top_k=10)

    assert [chunk.chunk_id for chunk in chunks] == ([] if expected_id is None else [expected_id])
    for chunk in chunks:
        source = next(doc for doc in docs if doc.metadata["chunk_id"] == chunk.chunk_id)
        assert chunk.content == source.page_content


def test_explicit_metadata_alias_is_still_searchable():
    doc = Document(
        page_content="Alternate reference body.",
        metadata={
            "chunk_id": "alternate",
            "file_name": "starlight_alt.txt",
            "search_aliases": ["starlight"],
        },
    )
    retriever = HybridRetriever(vector_top_k=0)
    retriever.build([doc])
    vector_store = Mock()
    vector_store.similarity_search_with_score.return_value = []

    chunks = retriever.retrieve("starlight", vector_store)

    assert [chunk.chunk_id for chunk in chunks] == ["alternate"]
