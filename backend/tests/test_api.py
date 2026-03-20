"""Integration tests for FastAPI routes using TestClient."""
import json
from unittest.mock import MagicMock, patch

import pytest
import respx
import httpx
from fastapi.testclient import TestClient

import models
import model_config

# Patch model resolution before importing the app
FAKE_MODELS = {"models": [
    {"name": "models/gemini-2.5-flash"},
    {"name": "models/imagen-4.0-generate-001"},
    {"name": "models/veo-3.1-generate-preview"},
]}


@pytest.fixture(scope="module")
def client():
    with respx.mock(assert_all_called=False):
        respx.get("https://generativelanguage.googleapis.com/v1beta/models").mock(
            return_value=httpx.Response(200, json=FAKE_MODELS)
        )
        from main import app
        with TestClient(app) as c:
            yield c


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "models" in body


# ── Prices ────────────────────────────────────────────────────────────────────

def test_get_prices(client):
    r = client.get("/stripe/prices")
    assert r.status_code == 200
    body = r.json()
    assert "10s" in body and "30s" in body and "60s" in body


# ── Projects — auth required ──────────────────────────────────────────────────

def test_list_projects_requires_user(client):
    r = client.get("/projects")
    assert r.status_code == 401


def test_list_projects_returns_empty(client):
    r = client.get("/projects", headers={"X-User-Id": "user_test"})
    assert r.status_code == 200
    assert r.json() == []


def test_get_project_not_found(client):
    r = client.get("/projects/nonexistent", headers={"X-User-Id": "u1"})
    assert r.status_code == 404


def test_get_project_ownership_check(client):
    p = models.create_project({"duration": 10}, user_id="owner")
    # Different user cannot access
    r = client.get(f"/projects/{p['id']}", headers={"X-User-Id": "intruder"})
    assert r.status_code == 403


def test_get_project_owner_can_access(client):
    p = models.create_project({"duration": 10}, user_id="owner2")
    r = client.get(f"/projects/{p['id']}", headers={"X-User-Id": "owner2"})
    assert r.status_code == 200
    assert r.json()["id"] == p["id"]


def test_get_project_no_owner_is_public(client):
    p = models.create_project({"duration": 10}, user_id=None)
    r = client.get(f"/projects/{p['id']}", headers={"X-User-Id": "anyone"})
    assert r.status_code == 200


# ── Free checkout ─────────────────────────────────────────────────────────────

def test_free_checkout_rejected_for_unknown_email(client):
    r = client.post(
        "/stripe/free-checkout",
        json={"duration": 30, "brand_name": "Test", "document_text": "x"},
        headers={"X-User-Id": "u1", "X-User-Email": "random@gmail.com"},
    )
    assert r.status_code == 403


@patch("api.stripe_routes.run_pipeline")
def test_free_checkout_allowed_for_servicevision(mock_pipeline, client):
    r = client.post(
        "/stripe/free-checkout",
        json={"duration": 30, "brand_name": "Test", "document_text": "x"},
        headers={"X-User-Id": "u1", "X-User-Email": "chris@servicevision.net"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["free"] is True
    assert "/project/" in body["checkout_url"]
    assert "project_id" in body


@patch("api.stripe_routes.run_pipeline")
def test_free_checkout_allowed_for_dbbuilderio(mock_pipeline, client):
    r = client.post(
        "/stripe/free-checkout",
        json={"duration": 10, "brand_name": "Brand", "document_text": "y"},
        headers={"X-User-Id": "u2", "X-User-Email": "dbbuilderio@gmail.com"},
    )
    assert r.status_code == 200
    assert r.json()["free"] is True


@patch("api.stripe_routes.run_pipeline")
def test_free_checkout_case_insensitive_email(mock_pipeline, client):
    r = client.post(
        "/stripe/free-checkout",
        json={"duration": 10, "brand_name": "B", "document_text": "z"},
        headers={"X-User-Id": "u3", "X-User-Email": "Chris@ServiceVision.NET"},
    )
    assert r.status_code == 200


@patch("api.stripe_routes.run_pipeline")
def test_free_checkout_creates_project_in_db(mock_pipeline, client):
    r = client.post(
        "/stripe/free-checkout",
        json={"duration": 30, "brand_name": "SV", "document_text": "doc"},
        headers={"X-User-Id": "sv_user", "X-User-Email": "test@servicevision.net"},
    )
    pid = r.json()["project_id"]
    p = models.get_project(pid)
    assert p is not None
    assert p["spec"]["brand_name"] == "SV"


# ── SSE progress endpoint is open ─────────────────────────────────────────────

def test_progress_endpoint_exists(client):
    p = models.create_project({})
    # Just verify the endpoint accepts the request (stream will be empty)
    with client.stream("GET", f"/projects/{p['id']}/progress") as r:
        assert r.status_code == 200
