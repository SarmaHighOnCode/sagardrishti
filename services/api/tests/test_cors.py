"""CORS is load-bearing, not cosmetic.

The console is served from :5173 and talks to the API on :8000. Without
the right headers the browser discards the response before lib/api.ts can
read it, so the operator gets "Failed to fetch" instead of the server's
problem+json `detail`. These tests pin the behaviour that makes the two
halves of the system able to talk at all.
"""

from __future__ import annotations

from app.main import DEFAULT_CORS_ORIGINS, cors_origins

CONSOLE_ORIGIN = "http://localhost:5173"


def test_allowed_origin_gets_the_header(client):
    res = client.get("/api/v1/detections", headers={"Origin": CONSOLE_ORIGIN})

    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == CONSOLE_ORIGIN


def test_preflight_is_answered(client):
    """The browser sends OPTIONS before the real GET. If this 405s, the
    GET is never attempted."""
    res = client.options(
        "/api/v1/detections",
        headers={
            "Origin": CONSOLE_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "accept",
        },
    )

    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == CONSOLE_ORIGIN
    assert "GET" in res.headers["access-control-allow-methods"]


def test_unknown_origin_is_not_granted_access(client):
    """Not a wildcard. An origin we did not configure gets no grant —
    the request still executes (CORS is enforced in the browser, not the
    server), but the browser will refuse to hand the body to script."""
    res = client.get("/api/v1/detections", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in res.headers


def test_error_responses_are_also_readable_by_the_console(client):
    """The 501s are the whole point of NotImplementedError in lib/api.ts.
    If the CORS header is missing on a non-2xx, the console cannot tell a
    deliberate 501 from a network failure."""
    res = client.get(
        "/api/v1/detections/det_synthetic_001/hindcast",
        headers={"Origin": CONSOLE_ORIGIN},
    )

    assert res.status_code == 501
    assert res.headers["access-control-allow-origin"] == CONSOLE_ORIGIN


def test_blank_env_falls_back_to_defaults_rather_than_locking_everyone_out():
    assert cors_origins("") == list(DEFAULT_CORS_ORIGINS)
    assert cors_origins("   ") == list(DEFAULT_CORS_ORIGINS)
    assert cors_origins(" , ,, ") == list(DEFAULT_CORS_ORIGINS)


def test_configured_origins_are_split_and_trimmed():
    assert cors_origins("https://a.example, https://b.example") == [
        "https://a.example",
        "https://b.example",
    ]
