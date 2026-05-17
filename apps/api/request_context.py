from __future__ import annotations

from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="")
_request_path: ContextVar[str] = ContextVar("request_path", default="")
_request_method: ContextVar[str] = ContextVar("request_method", default="")


def set_request_context(
    *,
    request_id: str,
    method: str,
    path: str,
) -> None:
    _request_id.set(request_id)
    _request_method.set(method)
    _request_path.set(path)


def clear_request_context() -> None:
    _request_id.set("")
    _request_method.set("")
    _request_path.set("")


def get_request_id() -> str:
    return _request_id.get()


def get_request_method() -> str:
    return _request_method.get()


def get_request_path() -> str:
    return _request_path.get()
