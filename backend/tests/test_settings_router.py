import io
from types import SimpleNamespace
from pathlib import Path

import pytest

from app.exceptions import ValidationError
from app.models.category import Category, Tag
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.project import Project
from app.routers import settings as settings_router
from app.routers import files as files_router


class DummyBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))


def test_update_user_settings_applies_changes_without_background_reload(monkeypatch):
    touched = {"called": False}
    applied = {"called": False}

    monkeypatch.setattr(settings_router, "_write_env", lambda body: None)
    monkeypatch.setattr(
        settings_router,
        "apply_runtime_settings",
        lambda *args, **kwargs: applied.__setitem__("called", True),
        raising=False,
    )
    monkeypatch.setattr(settings_router, "_touch_reload", lambda: touched.__setitem__("called", True))

    background_tasks = DummyBackgroundTasks()
    response = settings_router.update_user_settings(
        body={"token_expire": 60},
        background_tasks=background_tasks,
        db=SimpleNamespace(commit=lambda: None),
        current_user=SimpleNamespace(username="admin"),
    )

    assert response["code"] == 0
    assert applied["called"] is True
    assert touched["called"] is False
    assert background_tasks.tasks == []


def test_write_env_allows_backend_env_file_with_relative_upload_dir(monkeypatch, tmp_path):
    env_file = tmp_path / "backend" / ".env"
    env_file.parent.mkdir()
    env_file.write_text(
        "\n".join([
            "UPLOAD_DIR=./data/uploads",
            "LOG_LEVEL=INFO",
            "RATE_LIMIT_REQUESTS=100",
            "RATE_LIMIT_WINDOW=60",
            "",
        ]),
        encoding="utf-8",
    )

    monkeypatch.delenv("DOCSHOP_ENV_FILE", raising=False)
    monkeypatch.setattr(settings_router.app_settings, "UPLOAD_DIR", "./data/uploads")
    monkeypatch.setattr(settings_router, "__file__", str(env_file.parent / "app" / "routers" / "settings.py"))

    settings_router._write_env({
        "log_level": "debug",
        "rate_upload": 50,
        "rate_api": 800,
    })

    saved = env_file.read_text(encoding="utf-8")
    assert "LOG_LEVEL=DEBUG" in saved
    assert "RATE_LIMIT_REQUESTS=50" in saved
    assert "RATE_LIMIT_WINDOW=60" in saved
    assert "RATE_API=800" not in saved


def test_get_file_detail_returns_display_name_and_metadata(client, auth_headers, db_session, test_user):
    category = Category(name="测试分类", color="#123456")
    tag = Tag(name="测试标签", color="#abcdef")
    project = Project(name="测试项目", owner_id=test_user.id)
    db_session.add_all([category, tag, project])
    db_session.commit()

    document = DocumentFile(
        project_id=project.id,
        filename="original.docx",
        file_type="docx",
        display_name="显示名称",
        description="文档描述",
        category_id=category.id,
        cover_image="/covers/demo.png",
    )
    document.tags = [tag]
    db_session.add(document)
    db_session.commit()

    response = client.get(f"/api/v1/files/{document.id}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["id"] == document.id
    assert payload["data"]["display_name"] == "显示名称"
    assert payload["data"]["description"] == "文档描述"
    assert payload["data"]["category_id"] == category.id
    assert payload["data"]["tags"] == [{"id": tag.id, "name": tag.name, "color": tag.color}]


def test_plural_category_tags_endpoint_alias_updates_document(client, auth_headers, db_session, test_user):
    category = Category(name="分类A", color="#123456")
    tag = Tag(name="标签A", color="#abcdef")
    project = Project(name="项目A", owner_id=test_user.id)
    db_session.add_all([category, tag, project])
    db_session.commit()

    document = DocumentFile(
        project_id=project.id,
        filename="demo.pdf",
        file_type="pdf",
        current_version=1,
    )
    db_session.add(document)
    db_session.commit()

    version = FileVersion(
        file_id=document.id,
        version=1,
        sort_order=1,
        storage_path="/tmp/demo.pdf",
        file_hash="a" * 64,
        file_size=128,
    )
    db_session.add(version)
    db_session.commit()

    response = client.put(
        f"/api/v1/files/{document.id}/versions/{version.id}/category-tags",
        headers=auth_headers,
        json={"category_id": category.id, "tag_ids": [tag.id]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0

    db_session.refresh(document)
    assert document.category_id == category.id
    assert [item.id for item in document.tags] == [tag.id]


def test_update_file_types_refreshes_runtime_settings_for_upload_validators(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join([
            "SECRET_KEY=test-secret-key-for-ci-env-12345678",
            "ALLOWED_FILE_TYPES=.pdf,.docx",
            "MAX_FILE_SIZE=52428800",
            "",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setenv("DOCSHOP_ENV_FILE", str(env_file))
    monkeypatch.setattr(settings_router.app_settings, "ALLOWED_FILE_TYPES", {".pdf", ".docx"})
    monkeypatch.setattr(settings_router.app_settings, "MAX_FILE_SIZE", 50 * 1024 * 1024)
    monkeypatch.setattr(settings_router, "_delayed_touch_reload", lambda *args, **kwargs: None)

    background_tasks = DummyBackgroundTasks()
    response = settings_router.update_user_settings(
        body={"file_types": [".pdf", ".docx", ".mp4"]},
        background_tasks=background_tasks,
        db=SimpleNamespace(commit=lambda: None),
        current_user=SimpleNamespace(username="admin"),
    )

    assert response["code"] == 0
    assert "ALLOWED_FILE_TYPES=.pdf,.docx,.mp4" in env_file.read_text(encoding="utf-8")
    assert ".mp4" in settings_router.app_settings.ALLOWED_FILE_TYPES
    assert ".mp4" in files_router.settings.ALLOWED_FILE_TYPES


def test_update_file_types_creates_missing_env_file_for_vps_deployments(monkeypatch, tmp_path):
    env_file = tmp_path / "deploy" / ".env"

    monkeypatch.setenv("DOCSHOP_ENV_FILE", str(env_file))
    monkeypatch.setattr(settings_router.app_settings, "ALLOWED_FILE_TYPES", {".pdf", ".docx"})
    monkeypatch.setattr(settings_router.app_settings, "MAX_FILE_SIZE", 50 * 1024 * 1024)
    monkeypatch.setattr(settings_router, "_delayed_touch_reload", lambda *args, **kwargs: None)

    background_tasks = DummyBackgroundTasks()
    response = settings_router.update_user_settings(
        body={"file_types": [".doc", ".docx", ".pdf", ".xls", ".xlsx", ".html"]},
        background_tasks=background_tasks,
        db=SimpleNamespace(commit=lambda: None),
        current_user=SimpleNamespace(username="admin"),
    )

    assert response["code"] == 0
    assert env_file.exists() is True
    saved = env_file.read_text(encoding="utf-8")
    assert "ALLOWED_FILE_TYPES=.doc,.docx,.pdf,.xls,.xlsx,.html" in saved
    assert ".html" in settings_router.app_settings.ALLOWED_FILE_TYPES
    assert ".html" in files_router.settings.ALLOWED_FILE_TYPES


def test_update_user_settings_persists_force_https_to_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("FORCE_HTTPS=false\n", encoding="utf-8")

    monkeypatch.setenv("DOCSHOP_ENV_FILE", str(env_file))
    monkeypatch.setattr(settings_router, "_delayed_touch_reload", lambda *args, **kwargs: None)

    background_tasks = DummyBackgroundTasks()
    response = settings_router.update_user_settings(
        body={"force_https": True},
        background_tasks=background_tasks,
        db=SimpleNamespace(commit=lambda: None),
        current_user=SimpleNamespace(username="admin"),
    )

    assert response["code"] == 0
    assert "FORCE_HTTPS=true" in env_file.read_text(encoding="utf-8")


def test_update_user_settings_rejects_restart_required_settings():
    background_tasks = DummyBackgroundTasks()

    with pytest.raises(ValidationError) as exc_info:
        settings_router.update_user_settings(
            body={"storage_root": "./backend/data"},
            background_tasks=background_tasks,
            db=SimpleNamespace(commit=lambda: None),
            current_user=SimpleNamespace(username="admin"),
        )

    assert "重启" in exc_info.value.message
    assert background_tasks.tasks == []


def test_update_user_settings_applies_runtime_settings_without_reload_task(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join([
            "SECRET_KEY=test-secret-key-for-ci-env-12345678",
            "LOG_LEVEL=INFO",
            "",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setenv("DOCSHOP_ENV_FILE", str(env_file))
    monkeypatch.setattr(settings_router.app_settings, "LOG_LEVEL", "INFO")
    monkeypatch.setattr(settings_router, "_delayed_touch_reload", lambda *args, **kwargs: None)

    background_tasks = DummyBackgroundTasks()
    response = settings_router.update_user_settings(
        body={"log_level": "error"},
        background_tasks=background_tasks,
        db=SimpleNamespace(commit=lambda: None),
        current_user=SimpleNamespace(username="admin"),
    )

    assert response["code"] == 0
    assert response["message"] == "运行期配置已写入 .env 并立即生效"
    assert settings_router.app_settings.LOG_LEVEL == "ERROR"
    assert background_tasks.tasks == []


def test_get_user_settings_reads_latest_env_file_not_stale_runtime_settings(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join([
            "SECRET_KEY=test-secret-key-for-ci-env-12345678",
            "FORCE_HTTPS=true",
            'CORS_ORIGINS=["https://admin.example.com"]',
            "RATE_LIMIT_REQUESTS=88",
            "ACCESS_TOKEN_EXPIRE_MINUTES=30",
            "MAX_FILE_SIZE=10485760",
            "LOG_LEVEL=ERROR",
            "ALLOWED_FILE_TYPES=.pdf,.xlsx",
            "",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setenv("DOCSHOP_ENV_FILE", str(env_file))
    monkeypatch.setattr(settings_router.app_settings, "CORS_ORIGINS", ["http://stale.local"])
    monkeypatch.setattr(settings_router.app_settings, "RATE_LIMIT_REQUESTS", 999)
    monkeypatch.setattr(settings_router.app_settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 999)
    monkeypatch.setattr(settings_router.app_settings, "MAX_FILE_SIZE", 999 * 1024 * 1024)
    monkeypatch.setattr(settings_router.app_settings, "LOG_LEVEL", "DEBUG")
    monkeypatch.setattr(settings_router.app_settings, "ALLOWED_FILE_TYPES", {".doc"})

    response = settings_router.get_user_settings(
        db=SimpleNamespace(),
        current_user=SimpleNamespace(username="admin", avatar_url=""),
    )

    assert response["code"] == 0
    data = response["data"]
    assert data["force_https"] is True
    assert data["cors_origins"] == ["https://admin.example.com"]
    assert data["rate_upload"] == 88
    assert data["token_expire"] == 30
    assert data["max_file_mb"] == 10
    assert data["log_level"] == "ERROR"
    assert data["file_types"] == [".pdf", ".xlsx"]


def test_upload_avatar_does_not_delete_outside_allowed_root(
    monkeypatch, tmp_path, client, auth_headers, db_session, test_user
):
    from app.config import settings as app_settings

    monkeypatch.setattr(app_settings, "STORAGE_ROOT", str(tmp_path / "storage"), raising=False)

    outside_file = tmp_path / "outside" / "keep.png"
    outside_file.parent.mkdir(parents=True, exist_ok=True)
    outside_file.write_bytes(b"\x89PNG\r\n\x1a\nfakepng")

    malicious_avatar = f"/api/v1/avatars/{test_user.id}/../../outside/keep.png"
    test_user.avatar_url = malicious_avatar
    db_session.commit()

    response = client.post(
        "/api/v1/settings/avatar",
        headers=auth_headers,
        files={"avatar": ("new.png", io.BytesIO(b"\x89PNG\r\n\x1a\nnewavatar"), "image/png")},
    )

    assert response.status_code == 200
    assert outside_file.exists() is True
