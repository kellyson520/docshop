from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCE_PATHS = [
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "README.md",
    "backend/app",
    "frontend/index.html",
    "frontend/package.json",
    "frontend/src",
    "scripts",
]

ALLOWED_LEGACY_SNIPPETS = {
    "backend/start.sh": [
        "/app/data/docdist.db",
        "docdist.db -> /app/data/docshop.db",
    ],
    "scripts/migrate_sqlite_layout.py": [
        "docdist.db",
    ],
    "README.md": [
        "/app/data/docdist.db",
        "data/docdist.db",
    ],
}


def iter_text_files():
    for relative in SOURCE_PATHS:
        path = ROOT / relative
        if path.is_file():
            yield path
            continue
        for candidate in path.rglob("*"):
            if candidate.is_file() and candidate.suffix.lower() not in {
                ".db",
                ".pyc",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".pdf",
                ".docx",
                ".xlsx",
                ".ico",
            }:
                yield candidate


def read_without_allowed_legacy(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    relative = path.relative_to(ROOT).as_posix()
    for snippet in ALLOWED_LEGACY_SNIPPETS.get(relative, []):
        text = text.replace(snippet, "")
    return text


def test_docshop_branding_replaces_docdist_in_runtime_source() -> None:
    offenders: list[str] = []
    for path in iter_text_files():
        text = read_without_allowed_legacy(path)
        if any(token in text for token in ("DocDist", "docdist", "DOCDIST")):
            offenders.append(path.relative_to(ROOT).as_posix())

    assert not offenders, "Legacy DocDist/docdist branding remains in: " + ", ".join(offenders)
