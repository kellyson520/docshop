from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path


EXCLUDED_DIR_NAMES = {
    ".git",
    ".codegraph",
    ".pytest_cache",
    "__tests__",
    "node_modules",
    "logs",
    "playwright-report",
    "test-results",
}

EXCLUDED_DIR_PATHS = {
    "test",
    "backend/tests",
    "frontend/e2e",
    "frontend/src/test",
    "frontend/dist",
    "artifacts/coverage",
    "docs",
}

EXCLUDED_FILE_NAMES = {
    "pytest.ini",
    ".coverage",
    "vitest.config.js",
    "playwright.config.js",
    "requirements-dev.txt",
    "requirements-loadtest.txt",
}

EXCLUDED_FILE_PATTERNS = [
    "*.spec.*",
    "*.test.*",
    "*.log",
    "*.pid",
    "*.zip",
    "*_test*.db",
    "_tmp*.db",
]

EXCLUDED_FILE_PATHS = {
    "backend/.coverage",
    "backend/pytest.ini",
    "probe_counter.db",
    "debug_preconvert.db",
    "test.db",
}


def to_posix_relative(root: Path, target: Path) -> str:
    return target.relative_to(root).as_posix()


def should_exclude_dir(relative_dir: str) -> bool:
    parts = [part for part in relative_dir.split("/") if part]
    if not parts:
        return False
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return True
    return relative_dir in EXCLUDED_DIR_PATHS


def should_exclude_file(relative_file: str) -> bool:
    path = Path(relative_file)
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    if relative_file in EXCLUDED_FILE_PATHS:
        return True
    return any(fnmatch(path.name, pattern) for pattern in EXCLUDED_FILE_PATTERNS)
