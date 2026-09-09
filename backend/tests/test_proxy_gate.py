"""Tests for the shared-secret gate in api/proxy_guard.py.

These pin the behaviour that the gate exists for: this service is deployed as
its own public web service, so before the gate, anyone on the internet could
call it with a chosen X-User-Id and read another user's data, or with a chosen
X-User-Email and get free generation.
"""
import httpx
import pytest
import respx
from fastapi.testclient import TestClient

FAKE_MODELS = {
    "models": [
        {"name": "models/gemini-2.5-flash"},
        {"name": "models/imagen-4.0-generate-001"},
        {"name": "models/veo-3.1-generate-preview"},
    ]
}

SECRET = "test-proxy-secret"


@pytest.fixture(scope="module")
def raw_client():
    """A client that sends no proxy secret unless a test supplies one."""
    with respx.mock(assert_all_called=False):
        respx.get("https://generativelanguage.googleapis.com/v1beta/models").mock(
            return_value=httpx.Response(200, json=FAKE_MODELS)
        )
        from main import app

        with TestClient(app) as c:
            yield c


def test_health_is_reachable_without_the_secret(raw_client):
    """Render's health check has no way to send the secret."""
    assert raw_client.get("/health").status_code == 200


def test_user_data_is_refused_without_the_secret(raw_client):
    """The pre-fix exploit: read another user's profile by asserting their id."""
    r = raw_client.get("/users/victim/profile", headers={"X-User-Id": "victim"})
    assert r.status_code == 403


def test_free_checkout_is_refused_without_the_secret(raw_client):
    """The pre-fix exploit: free generation by asserting a staff email."""
    r = raw_client.post(
        "/stripe/free-checkout",
        json={
            "duration": "10s",
            "brand_name": "x",
            "brand_color": "#000000",
            "document_text": "x",
        },
        headers={"X-User-Id": "attacker", "X-User-Email": "any@servicevision.net"},
    )
    assert r.status_code == 403


def test_wrong_secret_is_refused(raw_client):
    r = raw_client.get(
        "/users/u1/profile",
        headers={"X-User-Id": "u1", "X-Proxy-Secret": "not-the-secret"},
    )
    assert r.status_code == 403


def test_correct_secret_is_admitted(raw_client):
    r = raw_client.get(
        "/users/u1/profile",
        headers={"X-User-Id": "u1", "X-Proxy-Secret": SECRET},
    )
    assert r.status_code == 200


def test_ownership_check_still_applies_behind_the_gate(raw_client):
    """The gate makes X-User-Id trustworthy; it does not replace authorisation."""
    r = raw_client.get(
        "/users/victim/profile",
        headers={"X-User-Id": "intruder", "X-Proxy-Secret": SECRET},
    )
    assert r.status_code == 403


def test_fails_closed_when_the_secret_is_unset(raw_client, monkeypatch):
    """An unset variable must not mean an open door."""
    monkeypatch.delenv("BACKEND_PROXY_SECRET", raising=False)
    r = raw_client.get("/users/u1/profile", headers={"X-User-Id": "u1"})
    assert r.status_code == 503
