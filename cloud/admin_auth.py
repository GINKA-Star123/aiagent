from __future__ import annotations

import os
from hmac import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException


def _admin_token() -> str:
    return os.getenv("CLOUD_ADMIN_TOKEN", "").strip()

async def require_cloud_admin(
    x_cloud_admin_token: Annotated[str | None, Header(alias="x-cloud-admin-token")] = None,
    x_admin_token: Annotated[str | None, Header(alias="x-admin-token")] = None,
) -> None:
    expected = _admin_token()
    provided = (x_cloud_admin_token or x_admin_token or "").strip()

    if not expected:
        raise HTTPException(
            status_code=503,
            detail={
                "stage":"cloud_admin_auth",
                "error":"CLOUD_ADMIN_TOKEN is not configured",
            },
        ) 

    if not provided or not compare_digest(provided,expected):
        raise HTTPException(
            status_code=403,
            detail={
                "stage":"cloud_admin_auth",
                "error":"Invalid admin token",
            },
        )