"""SQLite models — projects and jobs tables."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATABASE_PATH = Path("./video_magic.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def create_tables() -> None:
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id          TEXT PRIMARY KEY,
            status      TEXT NOT NULL DEFAULT 'pending',
            spec        TEXT NOT NULL DEFAULT '{}',
            video_url   TEXT,
            error       TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id          TEXT PRIMARY KEY,
            project_id  TEXT NOT NULL REFERENCES projects(id),
            stage       TEXT NOT NULL,
            pct         INTEGER NOT NULL DEFAULT 0,
            status      TEXT NOT NULL DEFAULT 'pending',
            detail      TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_project_id ON jobs(project_id);
    """)
    conn.commit()
    conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Project CRUD ─────────────────────────────────────────────────────────────

def create_project(spec: dict) -> dict:
    pid = str(uuid.uuid4())
    now = _now()
    conn = _connect()
    conn.execute(
        "INSERT INTO projects (id, status, spec, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (pid, "pending", json.dumps(spec), now, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    conn.close()
    return _project_row(row)


def get_project(pid: str) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    conn.close()
    return _project_row(row) if row else None


def update_project(pid: str, **kwargs: Any) -> dict | None:
    if not kwargs:
        return get_project(pid)
    kwargs["updated_at"] = _now()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [pid]
    conn = _connect()
    conn.execute(f"UPDATE projects SET {sets} WHERE id = ?", vals)
    conn.commit()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    conn.close()
    return _project_row(row) if row else None


def patch_project_spec(pid: str, spec: dict) -> dict | None:
    return update_project(pid, spec=json.dumps(spec))


def _project_row(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["spec"] = json.loads(d["spec"])
    return d


# ── Job CRUD ─────────────────────────────────────────────────────────────────

def upsert_job(project_id: str, stage: str, pct: int, status: str = "running", detail: str = "") -> dict:
    now = _now()
    conn = _connect()
    existing = conn.execute(
        "SELECT id FROM jobs WHERE project_id = ? AND stage = ?", (project_id, stage)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE jobs SET pct = ?, status = ?, detail = ?, updated_at = ? WHERE project_id = ? AND stage = ?",
            (pct, status, detail, now, project_id, stage),
        )
    else:
        jid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO jobs (id, project_id, stage, pct, status, detail, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (jid, project_id, stage, pct, status, detail, now, now),
        )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM jobs WHERE project_id = ? AND stage = ?", (project_id, stage)
    ).fetchone()
    conn.close()
    return dict(row)


def get_jobs(project_id: str) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at", (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
