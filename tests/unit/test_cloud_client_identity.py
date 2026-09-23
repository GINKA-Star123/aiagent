from __future__ import annotations

from starlette.requests import Request

import cloud.middleware as middleware
from apps.api.http_security import (
    build_trusted_proxy_policy,
)


def _request(
    *,
    client_ip: str,
    headers: dict[str, str] | None = None,
) -> Request:
    raw_headers = [
        (
            key.lower().encode("latin-1"),
            value.encode("latin-1"),
        )
        for key, value in (headers or {}).items()
    ]

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/chat",
            "headers": raw_headers,
            "client": (client_ip, 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )


def test_authorization_identity_is_hashed():
    request = _request(
        client_ip="203.0.113.10",
        headers={
            "authorization": "Bearer unit-secret",
        },
    )

    identity = middleware._client_identity(
        request
    )

    assert identity.startswith("auth:")
    assert "unit-secret" not in identity


def test_x_user_id_is_not_used_as_identity(
    monkeypatch,
):
    monkeypatch.setattr(
        middleware,
        "_trusted_proxy_policy",
        build_trusted_proxy_policy(
            "127.0.0.1"
        ),
    )

    request = _request(
        client_ip="203.0.113.10",
        headers={
            "x-user-id": "spoofed-user",
        },
    )

    identity = middleware._client_identity(
        request
    )

    assert identity == "ip:203.0.113.10"
    assert "spoofed-user" not in identity


def test_untrusted_client_cannot_spoof_ip(
    monkeypatch,
):
    monkeypatch.setattr(
        middleware,
        "_trusted_proxy_policy",
        build_trusted_proxy_policy(
            "127.0.0.1"
        ),
    )

    request = _request(
        client_ip="203.0.113.10",
        headers={
            "x-forwarded-for": "127.0.0.1",
        },
    )

    identity = middleware._client_identity(
        request
    )

    assert identity == "ip:203.0.113.10"


def test_trusted_proxy_can_forward_client_ip(
    monkeypatch,
):
    monkeypatch.setattr(
        middleware,
        "_trusted_proxy_policy",
        build_trusted_proxy_policy(
            "172.18.0.0/16"
        ),
    )

    request = _request(
        client_ip="172.18.0.2",
        headers={
            "x-forwarded-for": "203.0.113.10",
        },
    )

    identity = middleware._client_identity(
        request
    )

    assert identity == "ip:203.0.113.10"