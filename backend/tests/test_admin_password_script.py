import sqlite3
import sys
from pathlib import Path

import bcrypt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.reset_admin_password import _default_db_path, reset_admin_password


def _create_users_table(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                avatar_url TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _create_current_users_table(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                avatar_url TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _get_user(db_path, username):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    finally:
        conn.close()


def test_reset_admin_password_creates_missing_admin(tmp_path):
    db_path = tmp_path / "docshop.db"
    _create_users_table(db_path)

    result = reset_admin_password(str(db_path), "admin", "NewPass123", "admin")

    row = _get_user(db_path, "admin")
    assert result["created"] is True
    assert row["role"] == "admin"
    assert bcrypt.checkpw(b"NewPass123", row["password_hash"].encode("utf-8"))


def test_reset_admin_password_updates_existing_user(tmp_path):
    db_path = tmp_path / "docshop.db"
    _create_users_table(db_path)
    reset_admin_password(str(db_path), "admin", "OldPass123", "viewer")

    result = reset_admin_password(str(db_path), "admin", "NewPass123", "admin")

    row = _get_user(db_path, "admin")
    assert result["created"] is False
    assert row["role"] == "admin"
    assert bcrypt.checkpw(b"NewPass123", row["password_hash"].encode("utf-8"))


def test_reset_admin_password_creates_user_with_current_not_null_schema(tmp_path):
    db_path = tmp_path / "docshop.db"
    _create_current_users_table(db_path)

    result = reset_admin_password(str(db_path), "admin", "NewPass123", "admin")

    row = _get_user(db_path, "admin")
    assert result["created"] is True
    assert row["is_active"] == 1
    assert row["email"] is None
    assert bcrypt.checkpw(b"NewPass123", row["password_hash"].encode("utf-8"))


def test_default_db_path_uses_unified_project_data_directory(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert _default_db_path() == PROJECT_ROOT / "data" / "docshop.db"


def test_default_db_path_respects_sqlite_database_url(monkeypatch, tmp_path):
    db_path = tmp_path / "custom.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    assert _default_db_path() == db_path
