from aiagent.memory.memory_safety import MemorySafetyFilter


def test_memory_safety_blocks_api_key():
    result = MemorySafetyFilter().evaluate("记住我的 key 是 sk-abcdefghijklmnop")

    assert result.allowed is False
    assert result.sensitivity == "blocked"
    assert "secret" in result.flags


def test_memory_safety_redacts_phone():
    result = MemorySafetyFilter().evaluate("记住我的手机号是 13812345678")

    assert result.allowed is True
    assert result.sensitivity == "high"
    assert "contact" in result.flags
    assert "13812345678" not in result.redacted_text


def test_memory_safety_allows_preference():
    result = MemorySafetyFilter().evaluate("用户喜欢川菜，不喜欢甜口。")

    assert result.allowed is True
    assert result.sensitivity == "none"
    assert result.redacted_text == "用户喜欢川菜，不喜欢甜口。"