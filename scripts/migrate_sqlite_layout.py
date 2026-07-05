"""Safely migrate legacy SQLite database files into the unified data layout.

The migration is intentionally conservative:
- only SQLite file URLs are handled;
- the target database is never overwritten;
- legacy files are copied, not moved.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_sqlite_database_path(database_url: str | None = None, root: str | Path | None = None) -> Path | None:
    """Return the filesystem path for a sqlite DATABASE_URL, or None for non-file DBs."""
    raw = (database_url or os.environ.get("DATABASE_URL") or "sqlite:///./data/docshop.db").strip()
    if not raw.lower().startswith("sqlite:///"):
        return None
    if raw == "sqlite:///:memory:":
        return None

    location = raw[len("sqlite:///"):]
    location = unquote(location)
    if location.startswith("./"):
        location = location[2:]

    path = Path(location)
    if not path.is_absolute():
        base = Path(root) if root is not None else project_root()
        path = base / path
    return path.resolve(strict=False)


def legacy_sqlite_candidates(target: Path, root: str | Path | None = None) -> list[Path]:
    """Known legacy database locations ordered from safest/same-layout to older layouts."""
    base = Path(root) if root is not None else project_root()
    candidates = [
        target.with_name("docdist.db"),
        base / "backend" / "data" / "docshop.db",
        base / "backend" / "data" / "docdist.db",
        Path("/app/backend/data/docshop.db"),
        Path("/app/backend/data/docdist.db"),
    ]

    seen: set[str] = set()
    unique: list[Path] = []
    target_resolved = target.resolve(strict=False)
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        key = str(resolved)
        if key == str(target_resolved) or key in seen:
            continue
        seen.add(key)
        unique.append(resolved)
    return unique


def _first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def migrate_sqlite_layout(
    *,
    root: str | Path | None = None,
    database_url: str | None = None,
) -> dict[str, str | None]:
    """Copy a legacy SQLite database to the configured target when target is missing."""
    target = resolve_sqlite_database_path(database_url, root)
    if target is None:
        return {"action": "skipped", "reason": "non_sqlite_database_url", "target": None, "source": None}

    if target.exists():
        return {"action": "exists", "reason": "target_exists_not_overwritten", "target": str(target), "source": None}

    source = _first_existing(legacy_sqlite_candidates(target, root))
    if source is None:
        target.parent.mkdir(parents=True, exist_ok=True)
        return {"action": "missing", "reason": "no_legacy_database_found", "target": str(target), "source": None}

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {"action": "copied", "reason": "legacy_database_copied_without_overwrite", "target": str(target), "source": str(source)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy DocShop SQLite database files into the unified data layout.")
    parser.add_argument("--root", default=str(project_root()), help="Project/application root")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"), help="SQLite DATABASE_URL")
    args = parser.parse_args()

    result = migrate_sqlite_layout(root=args.root, database_url=args.database_url)
    print(
        "[sqlite-layout] "
        f"action={result['action']} reason={result.get('reason')} "
        f"source={result.get('source')} target={result.get('target')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
