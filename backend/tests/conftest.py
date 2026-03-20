"""Shared fixtures for all test modules."""
import os
import tempfile
from pathlib import Path

import pytest

import models


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point every test at a fresh in-memory-style SQLite file."""
    db = tmp_path / "test.db"
    monkeypatch.setattr(models, "DATABASE_PATH", db)
    models.create_tables()
    yield db


@pytest.fixture(autouse=True)
def gemini_env(monkeypatch):
    """Provide a dummy GEMINI_API_KEY so model_config doesn't crash."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("APP_URL", "http://localhost:3000")
