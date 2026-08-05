import pytest
from fastapi import HTTPException

from cloud.admin_auth import require_cloud_admin


@pytest.mark.anyio
async def test_cloud_admin_auth_accepts_cloud_header(monkeypatch):
    monkeypatch.setenv("CLOUD_ADMIN_TOKEN", "unit-token")

    await require_cloud_admin(x_cloud_admin_token="unit-token")


@pytest.mark.anyio
async def test_cloud_admin_auth_accepts_legacy_header(monkeypatch):
    monkeypatch.setenv("CLOUD_ADMIN_TOKEN", "unit-token")

    await require_cloud_admin(x_admin_token="unit-token")


@pytest.mark.anyio
async def test_cloud_admin_auth_rejects_invalid_token(monkeypatch):
    monkeypatch.setenv("CLOUD_ADMIN_TOKEN", "unit-token")

    with pytest.raises(HTTPException) as exc_info:
        await require_cloud_admin(x_cloud_admin_token="wrong-token")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["stage"] == "cloud_admin_auth"


@pytest.mark.anyio
async def test_cloud_admin_auth_requires_configured_token(monkeypatch):
    monkeypatch.delenv("CLOUD_ADMIN_TOKEN", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        await require_cloud_admin(x_cloud_admin_token="unit-token")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["stage"] == "cloud_admin_auth"