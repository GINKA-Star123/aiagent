from __future__ import annotations

from aiagent.knowledge.query_normalizer import (
    expand_domain_terms,
    normalize_aliases,
    normalize_rag_query,
)


def test_normalize_aliases_keeps_legacy_behavior():
    normalized = normalize_aliases("墨姐是谁")

    assert "墨姐" in normalized
    assert "墨清弦" in normalized


def test_normalize_aliases_expands_english_identifier():
    normalized = normalize_aliases("乐正绫是谁")

    assert "YueZhengling" in normalized
    assert "yuezhengling" in normalized
    assert "阿绫" in normalized


def test_normalize_aliases_expands_from_english_query():
    normalized = normalize_aliases("LuoTianyi 的设定")

    assert "洛天依" in normalized
    assert "天依" in normalized


def test_normalize_aliases_keeps_unrelated_query_unchanged():
    query = "今天天气怎么样"

    assert normalize_aliases(query) == query


def test_expand_domain_terms_adds_fan_chant_terms():
    expanded = expand_domain_terms("应援词")

    assert "华风夏韵" in expanded
    assert "洛水天依" in expanded


def test_expand_domain_terms_returns_original_when_no_trigger():
    assert expand_domain_terms("随便聊聊") == "随便聊聊"


def test_normalize_rag_query_handles_blank_input():
    assert normalize_rag_query("") == ""
    assert normalize_rag_query("   ") == ""


def test_normalize_rag_query_is_idempotent():
    once = normalize_rag_query("阿绫的应援词是什么")
    twice = normalize_rag_query(once)

    assert once == twice

def test_normalize_aliases_masks_domain_terms():
    """S1 回归：领域词"洛水天依"内部的"天依"不应被当成角色命中。"""

    normalized = normalize_aliases("洛水天依是谁")

    assert "LuoTianyi" not in normalized
    assert normalized == "洛水天依是谁"


def test_expand_domain_terms_reaches_fixed_point():
    """S2 回归：term/trigger 交叉的规则必须一趟到位。"""

    expanded = expand_domain_terms("设定")

    assert "阿绫红" in expanded          # 来自 代表色 规则（被 设定 的 term 触发）
    assert expand_domain_terms(expanded) == expanded