from apps.core.bootstrap import build_runtime
from apps.core.runtime import CoreRuntime

_runtime: CoreRuntime | None = None
_runtime_error: str | None = None


def get_runtime() -> CoreRuntime:
    global _runtime
    global _runtime_error

    if _runtime is not None:
        return _runtime

    try:
        _runtime = build_runtime()
        _runtime_error = None
        return _runtime
    except Exception as exc:
        _runtime_error = repr(exc)
        raise


def get_runtime_error() -> str | None:
    return _runtime_error


def reset_runtime() -> None:
    global _runtime
    global _runtime_error
    _runtime = None
    _runtime_error = None
