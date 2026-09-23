from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass


_request_id: ContextVar[str] = ContextVar(
    "request_id",
    default="",
)
_request_path: ContextVar[str] = ContextVar(
    "request_path",
    default="",
)
_request_method: ContextVar[str] = ContextVar(
    "request_method",
    default="",
)


@dataclass(frozen=True)
class RequestContextTokens:
    """
    保存一次 ContextVar.set() 返回的 token。

    请求结束时使用 reset，而不是直接写入空字符串，
    可以正确恢复调用前的上下文。
    """

    request_id: Token[str]
    method: Token[str]
    path: Token[str]


def set_request_context(
    *,
    request_id: str,
    method: str,
    path: str,
) -> RequestContextTokens:
    """
    设置当前异步请求的日志上下文。
    """

    return RequestContextTokens(
        request_id=_request_id.set(request_id),
        method=_request_method.set(method),
        path=_request_path.set(path),
    )


def reset_request_context(tokens: RequestContextTokens) -> None:
    """
    恢复设置请求上下文之前的 ContextVar 状态。
    """

    _request_id.reset(tokens.request_id)
    _request_method.reset(tokens.method)
    _request_path.reset(tokens.path)


def clear_request_context() -> None:
    """
    兼容已有单元测试和非 middleware 调用。

    新 middleware 应优先使用 reset_request_context。
    """

    _request_id.set("")
    _request_method.set("")
    _request_path.set("")


def get_request_id() -> str:
    return _request_id.get()


def get_request_method() -> str:
    return _request_method.get()


def get_request_path() -> str:
    return _request_path.get()


def request_context_payload() -> dict[str, str]:
    """
    返回适合写入结构化日志的请求上下文。
    """

    return {
        "request_id": get_request_id(),
        "method": get_request_method(),
        "path": get_request_path(),
    }