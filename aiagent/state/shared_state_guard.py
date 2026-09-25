from __future__ import annotations

from aiagent.state.shared_state import (
    SharedStateConflictError,
    SharedStateOwnershipError,
    SharedStateUnavailableError,
)


_SHARED_STATE_ERRORS = (
    SharedStateUnavailableError,
    SharedStateConflictError,
    SharedStateOwnershipError,
)


def raise_if_shared_state_error(exc: BaseException) -> None:
    if isinstance(exc, _SHARED_STATE_ERRORS):
        raise exc