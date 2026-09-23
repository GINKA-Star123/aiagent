from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


REDACTED = "[redacted]"
TRUNCATED = "[truncated]"

DEFAULT_MAX_LOG_TEXT_LENGTH = 8192
DEFAULT_SUMMARY_PREVIEW_LENGTH = 80

SENSITIVE_KEY_PARTS = {
    "authorization",
    "api_key",
    "apikey",
    "access_key",
    "secret",
    "password",
    "passwd",
    "token",
    "credential",
    "private_key",
    "cookie",
    "session_key",
}

CONTENT_KEY_PARTS = {
    "base64",
    "image_data",
    "audio_data",
    "file_data",
    "binary",
    "blob",
}

_AUTHORIZATION_PATTERN = re.compile(
    # 注意：这里不能用 \b。"_" 也属于 \w，
    # 所以 X_AUTHORIZATION: Bearer xxx 这类下划线前缀在下划线处没有单词边界，
    # 会被整体漏掉。改用"前一个字符不是字母/数字"的负向后顾。
    r"(?i)(?<![A-Za-z0-9])(authorization\s*[:=]\s*)"
    r"(?:bearer\s+)?[^\s,;]+"
)

_BEARER_PATTERN = re.compile(
    r"(?i)\bbearer\s+[a-z0-9._~+/=-]+"
)

_KEY_VALUE_SECRET_PATTERN = re.compile(
    # 同样不能用 \b：OPENAI_API_KEY / DB_PASSWORD / JWT_SECRET / MY_TOKEN
    # 这类"前缀_关键词"的写法在下划线处没有单词边界，会整体漏脱敏。
    # 负向后顾只排除"紧跟在字母/数字之后"的情况，
    # 既保留 \b 的防误伤效果，又能命中下划线前缀的字段名。
    r"(?i)(?<![A-Za-z0-9])("
    r"api[_-]?key|"
    r"access[_-]?key(?:[_-]?id)?|"
    r"secret(?:[_-]?access[_-]?key)?|"
    r"password|passwd|token|credential"
    r")(\s*[:=]\s*)"
    r"([^\s,;}\]]+)"
)

_JSON_SECRET_PATTERN = re.compile(
    # 引号必须用非捕获组把整个候选集合包起来：
    # 否则开引号只作用于第一个候选、尾部 "\s*:\s*" 只作用于最后一个候选，
    # 中间的 token/password 会退化成"裸关键字"匹配，再被末尾的 "[^"]*" 吞掉冒号，
    # 结果就变成：冒号被替换成 [redacted]，真正的密钥值反而留在日志里。
    r'(?i)("'
    r'(?:authorization|api[_-]?key|access[_-]?key(?:[_-]?id)?|'
    r'secret(?:[_-]?access[_-]?key)?|password|passwd|token|credential)'
    r'"\s*:\s*)'
    r'"[^"]*"'
)

_DATA_URL_PATTERN = re.compile(
    r"(?i)data:"
    r"(?:image|audio|video|application)"
    r"/[a-z0-9.+-]+;"
    r"base64,"
    r"[a-z0-9+/=\r\n]+"
)

_LONG_BASE64_PATTERN = re.compile(
    r"(?<![a-zA-Z0-9+/=])"
    r"[a-zA-Z0-9+/]{256,}={0,2}"
    r"(?![a-zA-Z0-9+/=])"
)


def is_sensitive_key(key: str) -> bool:
    """
    判断字段名是否表示密钥、令牌、密码或认证信息。
    """

    normalized = key.strip().lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def is_large_content_key(key: str) -> bool:
    """
    判断字段是否可能包含大段二进制或 Base64 内容。
    """

    normalized = key.strip().lower()
    return any(part in normalized for part in CONTENT_KEY_PARTS)


def sanitize_text(
    value: Any,
    *,
    max_length: int = DEFAULT_MAX_LOG_TEXT_LENGTH,
) -> str:
    """
    对将要进入日志的文本执行统一脱敏。

    处理内容包括：

    - Authorization Header。
    - Bearer Token。
    - key=value 形式的密码和密钥。
    - JSON 中的敏感字段。
    - Data URL。
    - 超长 Base64。
    - 超长日志文本。
    """

    if value is None:
        return ""

    text = str(value)

    text = _AUTHORIZATION_PATTERN.sub(
        lambda match: f"{match.group(1)}{REDACTED}",
        text,
    )
    text = _BEARER_PATTERN.sub(
        f"Bearer {REDACTED}",
        text,
    )
    text = _KEY_VALUE_SECRET_PATTERN.sub(
        lambda match: (
            f"{match.group(1)}"
            f"{match.group(2)}"
            f"{REDACTED}"
        ),
        text,
    )
    text = _JSON_SECRET_PATTERN.sub(
        lambda match: f'{match.group(1)}"{REDACTED}"',
        text,
    )
    text = _DATA_URL_PATTERN.sub(
        f"data:[base64-{REDACTED}]",
        text,
    )
    text = _LONG_BASE64_PATTERN.sub(
        f"[base64-{REDACTED}]",
        text,
    )

    if max_length > 0 and len(text) > max_length:
        omitted = len(text) - max_length
        text = (
            f"{text[:max_length]}"
            f"...{TRUNCATED}"
            f"(omitted_chars={omitted})"
        )

    return text


def sanitize_log_value(
    value: Any,
    *,
    key: str = "",
    max_depth: int = 8,
    max_items: int = 100,
    max_text_length: int = DEFAULT_MAX_LOG_TEXT_LENGTH,
) -> Any:
    """
    递归清理结构化日志数据。

    可以直接用于 dict、list、Pydantic model_dump 结果等结构。
    """

    if is_sensitive_key(key):
        return REDACTED

    if is_large_content_key(key):
        if value in {None, "", b""}:
            return ""
        return "[binary-content-redacted]"

    if max_depth <= 0:
        return "[max-depth-reached]"

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, bytes):
        return f"[bytes-redacted:length={len(value)}]"

    if isinstance(value, str):
        return sanitize_text(
            value,
            max_length=max_text_length,
        )

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}

        for index, (item_key, item_value) in enumerate(value.items()):
            if index >= max_items:
                result["_truncated_items"] = len(value) - max_items
                break

            normalized_key = str(item_key)
            result[normalized_key] = sanitize_log_value(
                item_value,
                key=normalized_key,
                max_depth=max_depth - 1,
                max_items=max_items,
                max_text_length=max_text_length,
            )

        return result

    if isinstance(value, Sequence):
        result: list[Any] = []

        for index, item in enumerate(value):
            if index >= max_items:
                result.append(
                    {
                        "_truncated_items": len(value) - max_items,
                    }
                )
                break

            result.append(
                sanitize_log_value(
                    item,
                    max_depth=max_depth - 1,
                    max_items=max_items,
                    max_text_length=max_text_length,
                )
            )

        return result

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return sanitize_log_value(
                model_dump(mode="json"),
                key=key,
                max_depth=max_depth - 1,
                max_items=max_items,
                max_text_length=max_text_length,
            )
        except Exception:
            pass

    return sanitize_text(
        value,
        max_length=max_text_length,
    )


def safe_json_dumps(
    value: Any,
    *,
    ensure_ascii: bool = False,
) -> str:
    """
    对数据脱敏后再序列化为 JSON。

    日志中如需输出结构化数据，应优先使用该函数，
    不要直接 json.dumps 原始请求或配置对象。
    """

    sanitized = sanitize_log_value(value)

    return json.dumps(
        sanitized,
        ensure_ascii=ensure_ascii,
        default=str,
        separators=(",", ":"),
    )


def content_summary(
    value: str | bytes | None,
    *,
    preview_length: int = DEFAULT_SUMMARY_PREVIEW_LENGTH,
    include_preview: bool = False,
) -> dict[str, Any]:
    """
    为 Prompt、用户文本、ASR 文本等内容生成安全摘要。

    默认只返回：

    - 字符或字节长度。
    - SHA-256 短 Hash。
    - 是否为空。

    只有明确允许时才输出经过脱敏的短预览。
    """

    if value is None:
        raw = b""
        text = ""
    elif isinstance(value, bytes):
        raw = value
        text = ""
    else:
        text = str(value)
        raw = text.encode("utf-8", errors="replace")

    result: dict[str, Any] = {
        "empty": not bool(raw),
        "length": len(value) if value is not None else 0,
        "sha256": hashlib.sha256(raw).hexdigest()[:16],
    }

    if include_preview and text:
        result["preview"] = sanitize_text(
            text[:preview_length],
            max_length=preview_length,
        )

    return result