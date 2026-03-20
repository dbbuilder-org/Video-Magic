"""Unit tests for model_config.py — startup model resolution."""
from unittest.mock import patch

import pytest

import model_config

ALL_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "imagen-4.0-generate-001",
    "veo-3.1-generate-preview",
    "veo-3.0-generate-001",
}


def test_resolves_preferred_when_available():
    with patch("model_config._fetch_available", return_value=ALL_MODELS):
        result = model_config.resolve_models()
    assert result["FLASH"] == "gemini-2.5-flash"
    assert result["IMAGEN"] == "imagen-4.0-generate-001"
    assert result["VEO"] == "veo-3.1-generate-preview"


def test_falls_back_when_preferred_unavailable():
    limited = {"gemini-2.0-flash", "imagen-4.0-generate-001", "veo-3.0-generate-001"}
    with patch("model_config._fetch_available", return_value=limited):
        result = model_config.resolve_models()
    assert result["FLASH"] == "gemini-2.0-flash"   # 2.5 not available → 2.0
    assert result["VEO"] == "veo-3.0-generate-001" # 3.1 not available → 3.0


def test_env_override_skips_chain(monkeypatch):
    monkeypatch.setenv("GEMINI_FLASH_MODEL", "gemini-2.5-pro")
    with patch("model_config._fetch_available", return_value=ALL_MODELS) as mock_fetch:
        result = model_config.resolve_models()
    assert result["FLASH"] == "gemini-2.5-pro"


def test_auto_value_is_ignored(monkeypatch):
    for val in ("AUTO", "auto", "Auto", "  AUTO  "):
        monkeypatch.setenv("GEMINI_FLASH_MODEL", val)
        with patch("model_config._fetch_available", return_value=ALL_MODELS):
            result = model_config.resolve_models()
        assert result["FLASH"] == "gemini-2.5-flash", f"'{val}' should be treated as AUTO"


def test_blank_env_is_ignored(monkeypatch):
    monkeypatch.setenv("GEMINI_FLASH_MODEL", "")
    with patch("model_config._fetch_available", return_value=ALL_MODELS):
        result = model_config.resolve_models()
    assert result["FLASH"] == "gemini-2.5-flash"


def test_api_unreachable_uses_defaults():
    with patch("model_config._fetch_available", return_value=set()):
        result = model_config.resolve_models()
    # Empty set → no candidate found → falls to chain[0]
    assert result["FLASH"] == model_config._CHAINS["FLASH"][0]
    assert result["IMAGEN"] == model_config._CHAINS["IMAGEN"][0]
    assert result["VEO"] == model_config._CHAINS["VEO"][0]


def test_no_api_key_uses_defaults(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = model_config.resolve_models()
    assert result["FLASH"] == model_config._CHAINS["FLASH"][0]
