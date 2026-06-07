"""重置或创建管理员账号密码。

用法：
    python scripts/reset_admin_password.py --username admin --password NewPass123
    python scripts/reset_admin_password.py --db backend/data/docdist.db --username admin --password NewPass123
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import bcrypt


VALID_ROLES = {"admin", "user", "viewer"}
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _ensure_users_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
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


def reset_admin_password(db_path: str, username: str, password: str, role: str = "admin") -> Dict[str, object]:
    """创建或更新用户密码，返回安全摘要（不返回密码和 hash）。"""
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of: {', '.join(sorted(VALID_ROLES))}")
    if not PASSWORD_PATTERN.match(password):
        raise ValueError("password must be at least 8 characters and include letters and numbers")

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    password_hash = _hash_password(password)
    now = _utc_now()

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        _ensure_users_table(conn)
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE users
                SET password_hash = ?, role = ?, updated_at = ?
                WHERE username = ?
                """,
                (password_hash, role, now, username),
            )
            created = False
            user_id = existing["id"]
        else:
            user_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO users (id, username, password_hash, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, password_hash, role, now, now),
            )
            created = True
        conn.commit()
    finally:
        conn.close()

    return {
        "db_path": str(path),
        "id": user_id,
        "username": username,
        "role": role,
        "created": created,
        "updated_at": now,
    }


def _default_db_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "backend" / "data" / "docdist.db"


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset or create a DocDist admin account.")
    parser.add_argument("--db", default=str(_default_db_path()), help="SQLite database path")
    parser.add_argument("--username", default="admin", help="Username to reset/create")
    parser.add_argument("--password", required=True, help="New password")
    parser.add_argument("--role", default="admin", choices=sorted(VALID_ROLES), help="User role")
    args = parser.parse_args()

    result = reset_admin_password(args.db, args.username, args.password, args.role)
    action = "created" if result["created"] else "updated"
    print(
        f"{action}: username={result['username']} role={result['role']} "
        f"db={result['db_path']} updated_at={result['updated_at']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
