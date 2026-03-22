"""Unit tests for models.py — SQLite CRUD layer."""
import pytest

import models


# ── Projects ──────────────────────────────────────────────────────────────────

def test_create_project_defaults():
    spec = {"duration": 30, "brand_name": "Acme"}
    p = models.create_project(spec)
    assert p["status"] == "pending"
    assert p["spec"] == spec
    assert p["user_id"] is None
    assert p["video_url"] is None


def test_create_project_with_user():
    p = models.create_project({"duration": 10}, user_id="user_abc")
    assert p["user_id"] == "user_abc"


def test_get_project_roundtrip():
    p = models.create_project({"k": "v"})
    fetched = models.get_project(p["id"])
    assert fetched["id"] == p["id"]
    assert fetched["spec"] == {"k": "v"}


def test_get_project_missing():
    assert models.get_project("nonexistent-id") is None


def test_update_project_status():
    p = models.create_project({})
    updated = models.update_project(p["id"], status="running")
    assert updated["status"] == "running"


def test_update_project_dict_spec():
    """The bug: update_project(spec=dict) must not raise 'type dict not supported'."""
    p = models.create_project({"duration": 30})
    new_spec = {"duration": 30, "doc_spec": {"title": "Test", "scenes": []}}
    updated = models.update_project(p["id"], spec=new_spec)
    assert updated["spec"]["doc_spec"]["title"] == "Test"


def test_update_project_nested_dict_and_list():
    p = models.create_project({})
    models.update_project(p["id"], spec={"scenes": [1, 2, 3], "meta": {"x": 1}})
    fetched = models.get_project(p["id"])
    assert fetched["spec"]["scenes"] == [1, 2, 3]
    assert fetched["spec"]["meta"] == {"x": 1}


def test_update_project_noop():
    p = models.create_project({"a": 1})
    result = models.update_project(p["id"])  # no kwargs
    assert result["spec"] == {"a": 1}


def test_patch_project_spec():
    p = models.create_project({"duration": 10})
    patched = models.patch_project_spec(p["id"], {"duration": 10, "extra": "yes"})
    assert patched["spec"]["extra"] == "yes"


def test_list_projects_by_user():
    models.create_project({}, user_id="u1")
    models.create_project({}, user_id="u1")
    models.create_project({}, user_id="u2")
    results = models.list_projects_by_user("u1")
    assert len(results) == 2
    assert all(r["user_id"] == "u1" for r in results)


def test_list_projects_empty():
    assert models.list_projects_by_user("nobody") == []


# ── Jobs ──────────────────────────────────────────────────────────────────────

def test_upsert_job_creates_and_updates():
    p = models.create_project({})
    j = models.upsert_job(p["id"], "parse", 10, "running")
    assert j["pct"] == 10

    j2 = models.upsert_job(p["id"], "parse", 50, "running")
    assert j2["pct"] == 50
    assert j2["id"] == j["id"]  # same row updated


def test_get_jobs():
    p = models.create_project({})
    models.upsert_job(p["id"], "parse", 5, "running")
    models.upsert_job(p["id"], "character", 25, "running")
    jobs = models.get_jobs(p["id"])
    assert len(jobs) == 2
    stages = {j["stage"] for j in jobs}
    assert stages == {"parse", "character"}


# ── User Profiles ─────────────────────────────────────────────────────────────

def test_upsert_and_get_profile():
    models.upsert_user_profile("u1", "My Brand", "#ff0000")
    p = models.get_user_profile("u1")
    assert p["brand_name"] == "My Brand"
    assert p["brand_color"] == "#ff0000"


def test_upsert_profile_updates():
    models.upsert_user_profile("u1", "Old", "#000")
    models.upsert_user_profile("u1", "New", "#fff")
    p = models.get_user_profile("u1")
    assert p["brand_name"] == "New"


def test_get_profile_missing_returns_defaults():
    p = models.get_user_profile("nobody")
    assert p["brand_name"] == ""
    assert p["brand_color"] == "#1A56DB"


# ── Referral Codes ────────────────────────────────────────────────────────────

def test_get_or_create_referral_code_idempotent():
    code1 = models.get_or_create_referral_code("u1")
    code2 = models.get_or_create_referral_code("u1")
    assert code1 == code2
    assert len(code1) == 8


def test_referral_codes_unique_per_user():
    c1 = models.get_or_create_referral_code("u1")
    c2 = models.get_or_create_referral_code("u2")
    assert c1 != c2


def test_register_referral_valid():
    models.get_or_create_referral_code("referrer")
    code = models.get_or_create_referral_code("referrer")
    result = models.register_referral("new_user", code)
    assert result is True


def test_register_referral_self_rejected():
    code = models.get_or_create_referral_code("u1")
    assert models.register_referral("u1", code) is False


def test_register_referral_bad_code():
    assert models.register_referral("u1", "BADCODE") is False


# ── Credits ───────────────────────────────────────────────────────────────────

def test_credits_zero_for_new_user():
    assert models.get_user_credits("new_user") == 0


def test_apply_referral_credit():
    code = models.get_or_create_referral_code("referrer")
    models.register_referral("referred", code)
    referrer_id = models.apply_referral_credit("referred")
    assert referrer_id == "referrer"
    assert models.get_user_credits("referrer") == 500


def test_apply_referral_credit_only_once():
    code = models.get_or_create_referral_code("referrer")
    models.register_referral("referred", code)
    models.apply_referral_credit("referred")
    second = models.apply_referral_credit("referred")
    assert second is None
    assert models.get_user_credits("referrer") == 500  # not doubled


def test_deduct_credits():
    code = models.get_or_create_referral_code("r")
    models.register_referral("u", code)
    models.apply_referral_credit("u")  # give r 500 cents
    new_bal = models.deduct_user_credits("r", 200)
    assert new_bal == 300


def test_deduct_credits_insufficient():
    with pytest.raises(ValueError, match="Insufficient"):
        models.deduct_user_credits("broke_user", 100)


# ── API Costs ──────────────────────────────────────────────────────────────────

def test_log_and_get_api_costs():
    p = models.create_project({})
    models.log_api_cost(p["id"], "gemini", "gemini-2.5-flash", "parse_document", 500, "tokens", 0.000075)
    models.log_api_cost(p["id"], "imagen", "imagen-4.0-generate-001", "character_gen", 1, "images", 0.04)
    costs = models.get_project_costs(p["id"])
    assert len(costs) == 2
    services = {c["service"] for c in costs}
    assert services == {"gemini", "imagen"}


def test_api_costs_sum():
    p = models.create_project({})
    models.log_api_cost(p["id"], "veo", "veo-3.1-generate-preview", "scene_0", 8.0, "seconds", 2.80)
    models.log_api_cost(p["id"], "elevenlabs", "eleven_turbo_v2_5", "voiceover", 200, "characters", 0.06)
    costs = models.get_project_costs(p["id"])
    total = sum(c["cost_usd"] for c in costs)
    assert abs(total - 2.86) < 0.001


def test_api_costs_isolated_per_project():
    p1 = models.create_project({})
    p2 = models.create_project({})
    models.log_api_cost(p1["id"], "gemini", "m", "op", 1, "tokens", 0.001)
    assert models.get_project_costs(p2["id"]) == []


def test_api_costs_empty_for_new_project():
    p = models.create_project({})
    assert models.get_project_costs(p["id"]) == []


# ── Orphan Recovery ───────────────────────────────────────────────────────────

def test_reset_orphaned_projects_marks_running_as_error():
    p1 = models.create_project({})
    p2 = models.create_project({})
    models.update_project(p1["id"], status="running")
    models.update_project(p2["id"], status="done")

    count = models.reset_orphaned_projects()

    assert count == 1
    assert models.get_project(p1["id"])["status"] == "error"
    assert "interrupted" in models.get_project(p1["id"])["error"].lower()
    assert models.get_project(p2["id"])["status"] == "done"


def test_reset_orphaned_projects_none_running():
    p = models.create_project({})
    models.update_project(p["id"], status="pending")
    count = models.reset_orphaned_projects()
    assert count == 0
