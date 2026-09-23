from __future__ import annotations


def test_allowed_origin_receives_cors_header(
    api_client,
):
    origin = "http://localhost:3000"

    response = api_client.options(
        "/health",
        headers={
            "origin": origin,
            "access-control-request-method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers[
            "access-control-allow-origin"
        ]
        == origin
    )
    assert (
        response.headers[
            "access-control-allow-credentials"
        ]
        == "true"
    )


def test_unknown_origin_is_not_authorized(
    api_client,
):
    response = api_client.options(
        "/health",
        headers={
            "origin": "https://evil.example.com",
            "access-control-request-method": "GET",
        },
    )

    assert response.status_code == 400
    assert (
        "access-control-allow-origin"
        not in response.headers
    )


def test_request_id_header_is_exposed(
    api_client,
):
    response = api_client.get(
        "/health",
        headers={
            "origin": "http://localhost:3000",
            "x-request-id": "cors-contract-001",
        },
    )

    exposed = response.headers.get(
        "access-control-expose-headers",
        "",
    ).lower()

    assert "x-request-id" in exposed
    assert (
        response.headers["x-request-id"]
        == "cors-contract-001"
    )