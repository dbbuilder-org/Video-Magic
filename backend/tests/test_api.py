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


# ── Cost breakdown ────────────────────────────────────────────────────────────

def test_cost_breakdown_empty(client):
    p = models.create_project({}, user_id="u_cost")
    r = client.get(f"/projects/{p['id']}/cost-breakdown", headers={"X-User-Id": "u_cost"})
    assert r.status_code == 200
    body = r.json()
    assert body["total_usd"] == 0
    assert body["breakdown"] == []


def test_cost_breakdown_with_records(client):
    p = models.create_project({}, user_id="u_cost2")
    models.log_api_cost(p["id"], "gemini", "gemini-2.5-flash", "parse_document", 100, "tokens", 0.01)
    models.log_api_cost(p["id"], "veo", "veo-3.1", "scene_0", 8.0, "seconds", 2.80)
    r = client.get(f"/projects/{p['id']}/cost-breakdown", headers={"X-User-Id": "u_cost2"})
    assert r.status_code == 200
    body = r.json()
    assert abs(body["total_usd"] - 2.81) < 0.001
    assert len(body["breakdown"]) == 2


def test_cost_breakdown_forbidden(client):
    p = models.create_project({}, user_id="owner")
    r = client.get(f"/projects/{p['id']}/cost-breakdown", headers={"X-User-Id": "other"})
    assert r.status_code == 403


# ── Reprocess ─────────────────────────────────────────────────────────────────

@patch("api.projects.run_pipeline")
def test_reprocess_starts_pipeline(mock_pipeline, client):
    p = models.create_project({"duration": 10}, user_id="u_reprocess")
    r = client.post(f"/projects/{p['id']}/reprocess", headers={"X-User-Id": "u_reprocess"})
    assert r.status_code == 200
    assert r.json()["status"] == "reprocessing"
    assert mock_pipeline.called


@patch("api.projects.run_pipeline")
def test_reprocess_sets_status_running(mock_pipeline, client):
    p = models.create_project({"duration": 10}, user_id="u_rep2")
    models.update_project(p["id"], status="done", video_url="/storage/x/final.mp4")
    client.post(f"/projects/{p['id']}/reprocess", headers={"X-User-Id": "u_rep2"})
    updated = models.get_project(p["id"])
    assert updated["status"] == "running"
    assert updated["video_url"] is None


def test_reprocess_forbidden(client):
    p = models.create_project({}, user_id="owner")
    r = client.post(f"/projects/{p['id']}/reprocess", headers={"X-User-Id": "intruder"})
    assert r.status_code == 403


def test_reprocess_not_found(client):
    r = client.post("/projects/nonexistent/reprocess", headers={"X-User-Id": "u"})
    assert r.status_code == 404


# ── SSE progress endpoint is open ─────────────────────────────────────────────

async def _one_shot_subscribe(project_id: str):
    """Test double: yields a single done event so the stream closes immediately."""
    yield 'data: {"stage": "done", "pct": 100}\n\n'


def test_progress_endpoint_exists(client):
    p = models.create_project({})
    # Patch subscribe so the stream closes immediately instead of blocking forever
    with patch("api.projects.subscribe", _one_shot_subscribe):
        with client.stream("GET", f"/projects/{p['id']}/progress") as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers.get("content-type", "")
