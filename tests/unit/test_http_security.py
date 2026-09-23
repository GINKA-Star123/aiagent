from __future__ import annotations

import pytest

from apps.api.http_security import (
    HttpSecurityConfigError,
    build_cors_policy,
    build_trusted_proxy_policy,
    normalize_origin,
    parse_forwarded_for,
    resolve_client_ip,
)


def test_normalize_origin_removes_default_https_port():
    assert (
        normalize_origin(
            "https://app.example.com:443/"
        )
        == "https://app.example.com"
    )


def test_normalize_origin_preserves_custom_port():
    assert (
        normalize_origin(
            "http://localhost:3000"
        )
        == "http://localhost:3000"
    )


def test_normalize_origin_rejects_path():
    with pytest.raises(HttpSecurityConfigError):
        normalize_origin(
            "https://app.example.com/private"
        )


def test_production_rejects_empty_cors_origins():
    with pytest.raises(HttpSecurityConfigError):
        build_cors_policy(
            "",
            app_env="production",
            cloud_mode=True,
            allow_credentials=True,
        )


def test_production_rejects_wildcard_origin():
    with pytest.raises(HttpSecurityConfigError):
        build_cors_policy(
            "*",
            app_env="production",
            cloud_mode=True,
            allow_credentials=False,
        )


def test_wildcard_rejects_credentials_in_development():
    with pytest.raises(HttpSecurityConfigError):
        build_cors_policy(
            "*",
            app_env="development",
            cloud_mode=False,
            allow_credentials=True,
        )


def test_production_rejects_localhost_origin():
    with pytest.raises(HttpSecurityConfigError):
        build_cors_policy(
            "https://app.example.com,http://localhost:3000",
            app_env="production",
            cloud_mode=True,
            allow_credentials=True,
        )


def test_production_accepts_explicit_https_origin():
    policy = build_cors_policy(
        "https://app.example.com",
        app_env="production",
        cloud_mode=True,
        allow_credentials=True,
    )

    assert policy.origins == (
        "https://app.example.com",
    )
    assert policy.allow_credentials is True
    assert "POST" in policy.allow_methods
    assert "Authorization" in policy.allow_headers
    assert "X-Request-ID" in policy.expose_headers


def test_trusted_proxy_uses_forwarded_client():
    policy = build_trusted_proxy_policy(
        "127.0.0.1,172.18.0.0/16"
    )

    client_ip = resolve_client_ip(
        peer_address="172.18.0.2",
        forwarded_for="203.0.113.10",
        trusted_proxies=policy,
    )

    assert client_ip == "203.0.113.10"


def test_untrusted_peer_cannot_spoof_forwarded_for():
    policy = build_trusted_proxy_policy(
        "127.0.0.1,172.18.0.0/16"
    )

    client_ip = resolve_client_ip(
        peer_address="198.51.100.99",
        forwarded_for="127.0.0.1",
        trusted_proxies=policy,
    )

    assert client_ip == "198.51.100.99"


def test_multiple_trusted_proxies_are_skipped():
    policy = build_trusted_proxy_policy(
        "172.18.0.0/16,198.51.100.20"
    )

    client_ip = resolve_client_ip(
        peer_address="172.18.0.2",
        forwarded_for=(
            "203.0.113.10,198.51.100.20"
        ),
        trusted_proxies=policy,
    )

    assert client_ip == "203.0.113.10"


def test_invalid_forwarded_for_is_discarded():
    assert parse_forwarded_for(
        "203.0.113.10,not-an-ip"
    ) == []


def test_invalid_trusted_proxy_config_fails():
    with pytest.raises(HttpSecurityConfigError):
        build_trusted_proxy_policy(
            "not-a-network"
        )