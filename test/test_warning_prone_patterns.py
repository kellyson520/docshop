from pathlib import Path


SCHEMA_ROOT = Path("backend/app/schemas")
ROUTER_ROOT = Path("backend/app/routers")


def test_pydantic_models_do_not_use_class_config():
    offenders: list[str] = []

    for path in SCHEMA_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "class Config:" in text:
            offenders.append(path.as_posix())

    assert offenders == []


def test_fastapi_query_does_not_use_deprecated_regex_keyword():
    offenders: list[str] = []

    for path in ROUTER_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "regex=" in text:
            offenders.append(path.as_posix())

    assert offenders == []
