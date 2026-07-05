import asyncio

import pytest

from app.services.config_watch import ConfigFileWatcher, fingerprint_file


def test_fingerprint_file_missing_path_is_stable(tmp_path):
    missing = tmp_path / "missing.env"

    assert fingerprint_file(missing) == "missing"


def test_fingerprint_file_changes_with_content(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("LOG_LEVEL=INFO\n", encoding="utf-8")
    first = fingerprint_file(env_file)

    env_file.write_text("LOG_LEVEL=DEBUG\n", encoding="utf-8")
    second = fingerprint_file(env_file)

    assert first != second


@pytest.mark.asyncio
async def test_check_once_publishes_after_baseline_change(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("LOG_LEVEL=INFO\n", encoding="utf-8")
    applied = []
    published = []

    monkeypatch.setattr("app.services.config_watch.apply_runtime_settings", lambda path: applied.append(path))

    async def fake_publish(changed_keys, source):
        published.append((changed_keys, source))

    monkeypatch.setattr("app.services.config_watch.publish_config_updated", fake_publish)

    watcher = ConfigFileWatcher(lambda: str(env_file), debounce_seconds=0)
    assert await watcher.check_once() is False

    await asyncio.sleep(0.01)
    env_file.write_text("LOG_LEVEL=ERROR\n", encoding="utf-8")

    assert await watcher.check_once() is True
    assert applied == [str(env_file)]
    assert published == [([], "env-file")]
