import logging

from app.config import settings


def test_apply_runtime_settings_updates_global_settings(monkeypatch, tmp_path):
    from app.services.runtime_config import apply_runtime_settings

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join([
            "SECRET_KEY=test-secret-key-for-ci-env-12345678",
            "LOG_LEVEL=ERROR",
            "MAX_FILE_SIZE=1048576",
            "",
        ]),
        encoding="utf-8",
    )

    original_log_level = settings.LOG_LEVEL
    original_max_file_size = settings.MAX_FILE_SIZE

    apply_runtime_settings(env_file=env_file)

    assert settings.LOG_LEVEL == "ERROR"
    assert settings.MAX_FILE_SIZE == 1048576

    monkeypatch.setattr(settings, "LOG_LEVEL", original_log_level, raising=False)
    monkeypatch.setattr(settings, "MAX_FILE_SIZE", original_max_file_size, raising=False)


def test_reconfigure_logging_uses_new_log_level(monkeypatch):
    from app.utils import logger as logger_module

    monkeypatch.setattr(settings, "LOG_LEVEL", "ERROR")

    logger_module.reconfigure_logging()

    assert logger_module._global_log_level == logging.ERROR
    assert any(handler.level == logging.ERROR for handler in logger_module.logger.handlers)
