from pathlib import Path

from app.utils.time import utc_now, utc_now_iso


SCAN_ROOTS = (
    Path("backend/app"),
    Path("backend/tests"),
    Path("test"),
)


def test_utc_helpers_return_expected_shapes():
    now = utc_now()
    iso = utc_now_iso()

    assert now.tzinfo is None
    assert iso.endswith("Z")
    assert "T" in iso


def test_project_python_files_do_not_use_datetime_utcnow():
    patterns = (
        ".utc" + "now(",
        ".utc" + "now",
    )
    offenders: list[str] = []

    for root in SCAN_ROOTS:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if any(pattern in text for pattern in patterns):
                offenders.append(path.as_posix())

    assert offenders == []
