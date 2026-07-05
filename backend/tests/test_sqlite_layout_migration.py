from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migrate_sqlite_layout import migrate_sqlite_layout, resolve_sqlite_database_path


def _create_marker_db(path: Path, marker: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS marker (value TEXT NOT NULL)")
        conn.execute("DELETE FROM marker")
        conn.execute("INSERT INTO marker (value) VALUES (?)", (marker,))
        conn.commit()
    finally:
        conn.close()


def _read_marker(path: Path) -> str:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT value FROM marker").fetchone()[0]
    finally:
        conn.close()


def test_resolve_sqlite_database_path_supports_relative_project_paths(tmp_path):
    root = tmp_path / "repo"

    assert resolve_sqlite_database_path("sqlite:///./data/docshop.db", root) == root / "data" / "docshop.db"


def test_migrate_sqlite_layout_copies_legacy_backend_database_without_overwriting(tmp_path):
    root = tmp_path / "repo"
    target = root / "data" / "docshop.db"
    legacy = root / "backend" / "data" / "docshop.db"
    _create_marker_db(legacy, "legacy")

    result = migrate_sqlite_layout(root=root, database_url="sqlite:///./data/docshop.db")

    assert result["action"] == "copied"
    assert result["target"] == str(target)
    assert result["source"] == str(legacy)
    assert _read_marker(target) == "legacy"

    _create_marker_db(target, "current")
    second = migrate_sqlite_layout(root=root, database_url="sqlite:///./data/docshop.db")

    assert second["action"] == "exists"
    assert second["source"] is None
    assert _read_marker(target) == "current"


def test_migrate_sqlite_layout_supports_docdist_rename_in_data_dir(tmp_path):
    root = tmp_path / "repo"
    target = root / "data" / "docshop.db"
    legacy = root / "data" / "docdist.db"
    _create_marker_db(legacy, "docdist")

    result = migrate_sqlite_layout(root=root, database_url="sqlite:///./data/docshop.db")

    assert result["action"] == "copied"
    assert result["source"] == str(legacy)
    assert _read_marker(target) == "docdist"
