from pathlib import Path


RUNTIME_SOURCE_FILES = [
    Path("app/routers/files.py"),
    Path("app/routers/share.py"),
    Path("app/services/conversion_service.py"),
    Path("app/services/document_store.py"),
    Path("app/routers/share_tokens.py"),
    Path("app/services/file_service.py"),
]

PUBLISHED_TEXT_FILES = [
    Path("../README.md"),
    Path("../docs/ui-ux-audit-2026-06-11.md"),
    Path("../scripts/reset_admin_password.py"),
    Path("app/routers/files.py"),
    Path("load_tests/locustfile.py"),
    Path("scripts/migrate_add_card_fields.py"),
    Path("scripts/migrate_add_exam_tables.py"),
]

MOJIBAKE_MARKERS = [
    "????",
    "[??]",
    "锛",
    "涓",
    "鍙",
    "鐨",
    "鈥",
    "�",
]


def test_runtime_source_does_not_contain_mojibake_placeholders():
    offenders = []
    for path in RUNTIME_SOURCE_FILES:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "????" in line or "[??]" in line:
                offenders.append(f"{path}:{line_no}: {stripped}")

    assert offenders == []


def test_published_text_does_not_contain_mojibake_markers():
    offenders = []
    for path in PUBLISHED_TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for marker in MOJIBAKE_MARKERS:
                if marker in line:
                    offenders.append(f"{path}:{line_no}: contains {marker!r}: {line.strip()}")
                    break

    assert offenders == []
