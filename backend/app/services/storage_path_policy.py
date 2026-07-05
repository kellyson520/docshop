from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from app.config import settings
from app.services import document_store


def _normalize_root(path: str | Path | None) -> Path | None:
    if not path:
        return None
    try:
        return Path(os.path.realpath(os.fspath(path)))
    except (OSError, TypeError, ValueError):
        return None


def _is_testing_env() -> bool:
    return os.environ.get("APP_ENV") == "testing" or "pytest" in sys.modules


def _append_root(roots: list[Path], candidate: str | Path | None) -> None:
    resolved = _normalize_root(candidate)
    if resolved and resolved not in roots:
        roots.append(resolved)


def _path_within_roots(path: str | Path, roots: list[Path]) -> bool:
    target = _normalize_root(path)
    if target is None:
        return False
    for root in roots:
        if target == root or root in target.parents:
            return True
    return False


def allowed_storage_roots() -> list[Path]:
    roots: list[Path] = []
    for candidate in (settings.UPLOAD_DIR, document_store.ROOT):
        _append_root(roots, candidate)

    if _is_testing_env():
        _append_root(roots, tempfile.gettempdir())

    return roots


def allowed_response_roots() -> list[Path]:
    roots = allowed_storage_roots()
    _append_root(roots, settings.TEMP_DIR)

    return roots


def is_allowed_storage_path(path: str | Path) -> bool:
    return _path_within_roots(path, allowed_storage_roots())


def is_allowed_response_path(path: str | Path) -> bool:
    return _path_within_roots(path, allowed_response_roots())
