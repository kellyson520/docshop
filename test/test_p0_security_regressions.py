import inspect
import os
from pathlib import Path

import pytest


def test_access_token_public_dict_does_not_expose_raw_secret():
    # Import relationship targets so SQLAlchemy mapper configuration is stable
    # when this focused regression test is run outside the full app bootstrap.
    import app.models.category  # noqa: F401
    from app.models.access_token import AccessToken

    token = AccessToken(token="raw-secret-token", name="门禁令牌", created_by="admin-id")

    public_data = token.to_dict()

    assert "token" not in public_data
    assert public_data["token_preview"].startswith("raw-")
    assert public_data["token_preview"].endswith("oken")


def test_jwt_contains_revocation_identifier_jti():
    from jose import jwt

    from app.config import settings
    from app.deps.auth import create_access_token

    encoded = create_access_token({"sub": "admin", "role": "admin"})
    payload = jwt.decode(encoded, settings.SECRET_KEY, algorithms=["HS256"])

    assert payload.get("jti")


def test_settings_update_endpoint_requires_admin_dependency():
    from app.deps.auth import get_current_admin
    from app.routers import settings as settings_router

    signature = inspect.signature(settings_router.update_user_settings)
    dependency = signature.parameters["current_user"].default.dependency

    assert dependency is get_current_admin


def test_config_path_helpers_reject_traversal(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "TEMP_DIR", str(tmp_path / "temp"))

    with pytest.raises(ValueError):
        settings.get_upload_path("..", "escaped.txt")

    with pytest.raises(ValueError):
        settings.get_temp_path("../escaped.tmp")


def test_tracking_header_sanitizer_redacts_sensitive_values():
    from app.middlewares.tracking import sanitize_headers_for_tracking

    sanitized = sanitize_headers_for_tracking({
        "Authorization": "Bearer secret",
        "Cookie": "session_id=secret",
        "X-Api-Key": "secret",
        "User-Agent": "pytest",
    })

    assert sanitized["Authorization"] == "***"
    assert sanitized["Cookie"] == "***"
    assert sanitized["X-Api-Key"] == "***"
    assert sanitized["User-Agent"] == "pytest"


def test_logging_request_id_sanitizer_rejects_header_injection():
    from app.middlewares.logging import sanitize_request_id

    assert sanitize_request_id("abc-123_456") == "abc-123_456"
    assert sanitize_request_id("abc\r\nInjected: yes") != "abc\r\nInjected: yes"
    assert "\n" not in sanitize_request_id("abc\r\nInjected: yes")


def test_frontend_router_keeps_public_routes_public_and_rejects_url_jwt_injection():
    router_source = Path("frontend/src/router/index.js").read_text(encoding="utf-8")

    assert "isPublicRoute(to)" in router_source
    assert "acceptUrlAccessToken" in router_source
    assert "localStorage.setItem('access_token', urlToken)" not in router_source


def test_docker_compose_secret_key_expansion_is_valid_and_env_writable():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "${SECRET_KEY:???? SECRET_KEY ????}" not in compose
    assert "${SECRET_KEY:?SECRET_KEY is required}" in compose
    assert "./.env:/app/.env:ro" not in compose


def test_rate_limiter_ignores_spoofed_forwarded_headers_by_default():
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from app.middlewares.rate_limit import RateLimitMiddleware

    middleware = RateLimitMiddleware(app=MagicMock())
    request = SimpleNamespace(
        headers={
            "X-Forwarded-For": "198.51.100.250",
            "X-Real-IP": "198.51.100.251",
        },
        client=SimpleNamespace(host="203.0.113.10"),
    )

    assert middleware._get_client_ip(request) == "203.0.113.10"


def test_sliding_window_counter_bounds_unique_key_memory():
    from app.middlewares.rate_limit import SlidingWindowCounter

    counter = SlidingWindowCounter(max_requests=10, window_seconds=60, max_keys=2)

    assert counter.is_allowed("ip:203.0.113.1")[0] is True
    assert counter.is_allowed("ip:203.0.113.2")[0] is True
    assert counter.is_allowed("ip:203.0.113.3")[0] is True

    assert len(counter.get_stats()) <= 2


def test_change_password_uses_registration_strength_rules():
    from types import SimpleNamespace

    from app.deps.auth import get_password_hash
    from app.exceptions import ValidationError
    from app.routers.settings import change_password

    user = SimpleNamespace(password_hash=get_password_hash("OldPassword1"))
    db = SimpleNamespace(commit=lambda: None)

    with pytest.raises(ValidationError):
        change_password(
            {"old_password": "OldPassword1", "new_password": "abcdef"},
            db=db,
            current_user=user,
        )
