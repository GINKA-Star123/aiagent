# tests/api/test_knowledge_contract.py
from __future__ import annotations

from tests.helpers.api_contract import assert_json_response, assert_ok_response


def test_knowledge_search_contract(api_client):
    response = api_client.post(
        "/knowledge/search",
        json={
            "query": "乐正绫是谁",
            "top_k": 2,
            "include_prompt_context": True,
            "include_citations": True,
            "include_confidence": True,
        },
    )
    data = assert_json_response(response)

    assert_ok_response(data)
    assert data["query"] == "乐正绫是谁"
    assert "normalized_query" in data
    assert "top_k" in data
    assert "should_inject" in data
    assert "chunks" in data
    assert "prompt_context" in data
    assert "citations" in data
    assert "confidence" in data

    assert isinstance(data["chunks"], list)
    assert isinstance(data["citations"], list)
    assert isinstance(data["confidence"], dict)