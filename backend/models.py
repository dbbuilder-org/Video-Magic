"""SQLite models — projects, jobs, user_profiles, referrals, user_credits."""
import json
import random
import sqlite3
import string
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
            user_id     TEXT,
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

        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id     TEXT PRIMARY KEY,
            brand_name  TEXT NOT NULL DEFAULT '',
            brand_color TEXT NOT NULL DEFAULT '#1A56DB',
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS referral_codes (
            code        TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL UNIQUE,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS referrals (
            id              TEXT PRIMARY KEY,
            referrer_id     TEXT NOT NULL,
            referred_id     TEXT NOT NULL UNIQUE,
            code            TEXT NOT NULL,
            first_paid_at   TEXT,
            credit_applied  INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_credits (
            user_id         TEXT PRIMARY KEY,
            balance_cents   INTEGER NOT NULL DEFAULT 0,
            updated_at      TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_project_id ON jobs(project_id);
        CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
        CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
    """)
    conn.commit()
    conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Project CRUD ─────────────────────────────────────────────────────────────

def create_project(spec: dict, user_id: str | None = None) -> dict:
    pid = str(uuid.uuid4())
    now = _now()
    conn = _connect()
    conn.execute(
        "INSERT INTO projects (id, user_id, status, spec, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (pid, user_id, "pending", json.dumps(spec), now, now),
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


def list_projects_by_user(user_id: str) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (user_id,),
    ).fetchall()
    conn.close()
    return [_project_row(r) for r in rows]


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


# ── User Profiles ─────────────────────────────────────────────────────────────

def get_user_profile(user_id: str) -> dict:
    conn = _connect()
    row = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"user_id": user_id, "brand_name": "", "brand_color": "#1A56DB", "updated_at": None}


def upsert_user_profile(user_id: str, brand_name: str, brand_color: str) -> dict:
    now = _now()
    conn = _connect()
    conn.execute(
        """INSERT INTO user_profiles (user_id, brand_name, brand_color, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             brand_name=excluded.brand_name,
             brand_color=excluded.brand_color,
             updated_at=excluded.updated_at""",
        (user_id, brand_name, brand_color, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row)


# ── Referral Codes ────────────────────────────────────────────────────────────

def _random_code(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def get_or_create_referral_code(user_id: str) -> str:
    conn = _connect()
    row = conn.execute("SELECT code FROM referral_codes WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        conn.close()
        return row["code"]
    # Generate unique code
    for _ in range(10):
        code = _random_code()
        if not conn.execute("SELECT 1 FROM referral_codes WHERE code = ?", (code,)).fetchone():
            conn.execute(
                "INSERT INTO referral_codes (code, user_id, created_at) VALUES (?, ?, ?)",
                (code, user_id, _now()),
            )
            conn.commit()
            conn.close()
            return code
    conn.close()
    raise RuntimeError("Failed to generate unique referral code")


def register_referral(referred_id: str, code: str) -> bool:
    """Call when a new user signs up with a referral code. Returns True if valid."""
    conn = _connect()
    rc = conn.execute("SELECT user_id FROM referral_codes WHERE code = ?", (code,)).fetchone()
    if not rc:
        conn.close()
        return False
    referrer_id = rc["user_id"]
    if referrer_id == referred_id:
        conn.close()
        return False
    # Idempotent: ignore if already referred
    existing = conn.execute(
        "SELECT id FROM referrals WHERE referred_id = ?", (referred_id,)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO referrals (id, referrer_id, referred_id, code, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), referrer_id, referred_id, code, _now()),
        )
        conn.commit()
    conn.close()
    return True


def apply_referral_credit(referred_id: str) -> str | None:
    """Call when a referred user makes their first payment. Credits referrer $5 (500 cents).
    Returns referrer_id if credit was applied, else None."""
    CREDIT_CENTS = 500
    conn = _connect()
    ref = conn.execute(
        "SELECT * FROM referrals WHERE referred_id = ? AND credit_applied = 0",
        (referred_id,),
    ).fetchone()
    if not ref:
        conn.close()
        return None
    referrer_id = ref["referrer_id"]
    now = _now()
    conn.execute(
        "UPDATE referrals SET credit_applied = 1, first_paid_at = ? WHERE id = ?",
        (now, ref["id"]),
    )
    # Upsert credits for referrer
    conn.execute(
        """INSERT INTO user_credits (user_id, balance_cents, updated_at) VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             balance_cents = balance_cents + ?,
             updated_at = excluded.updated_at""",
        (referrer_id, CREDIT_CENTS, now, CREDIT_CENTS),
    )
    conn.commit()
    conn.close()
    return referrer_id


# ── User Credits ──────────────────────────────────────────────────────────────

def get_user_credits(user_id: str) -> int:
    """Returns balance in cents."""
    conn = _connect()
    row = conn.execute("SELECT balance_cents FROM user_credits WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row["balance_cents"] if row else 0


def deduct_user_credits(user_id: str, amount_cents: int) -> int:
    """Deduct credits. Returns new balance. Raises if insufficient."""
    conn = _connect()
    row = conn.execute("SELECT balance_cents FROM user_credits WHERE user_id = ?", (user_id,)).fetchone()
    current = row["balance_cents"] if row else 0
    if current < amount_cents:
        conn.close()
        raise ValueError(f"Insufficient credits: {current} < {amount_cents}")
    new_balance = current - amount_cents
    conn.execute(
        "UPDATE user_credits SET balance_cents = ?, updated_at = ? WHERE user_id = ?",
        (new_balance, _now(), user_id),
    )
    conn.commit()
    conn.close()
    return new_balance
