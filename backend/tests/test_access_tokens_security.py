import pytest

from app.models.access_token import AccessToken
from app.routers import access_tokens


def _create_access_token(db_session, test_user, token: str = "secret-access-token") -> AccessToken:
    access_token = AccessToken(
        token=token,
        name="security-test",
        is_active=1,
        created_by=test_user.id,
    )
    db_session.add(access_token)
    db_session.commit()
    db_session.refresh(access_token)
    return access_token


def test_validate_token_prefers_post_body(client, db_session, test_user):
    """访问令牌校验应支持 POST body，避免令牌进入 URL。"""
    _create_access_token(db_session, test_user)

    response = client.post(
        "/api/v1/access-tokens/validate",
        json={"token": "secret-access-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"] == {"valid": True}


def test_validate_token_post_validation_error_uses_standard_error_handler(client):
    """RequestValidationError 应使用统一 400/40001 响应，而不是 FastAPI 默认 422。"""
    response = client.post("/api/v1/access-tokens/validate", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == 40001
    assert payload["message"] == "请求参数校验失败"
    assert payload["errors"][0]["field"] == "body.token"


def test_admin_token_list_includes_full_token_for_copyable_access_links(
    client,
    db_session,
    test_user,
    auth_headers,
):
    """??????????? token ??????????"""
    _create_access_token(db_session, test_user, token="copyable-access-token")

    response = client.get("/api/v1/access-tokens", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    item = payload["data"]["items"][0]
    assert item["token"] == "copyable-access-token"
    assert item["token_preview"] != item["token"]



def test_admin_can_fetch_single_full_token_for_access_link_copy(
    client,
    db_session,
    test_user,
    auth_headers,
):
    """??????????????? id ???? token?"""
    token = _create_access_token(db_session, test_user, token="single-copy-token")

    response = client.get(f"/api/v1/access-tokens/{token.id}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["id"] == token.id
    assert payload["data"]["token"] == "single-copy-token"
    assert payload["data"]["token_preview"] != payload["data"]["token"]


def test_validate_token_legacy_get_is_deprecated_and_rate_limited(
    client,
    db_session,
    test_user,
    monkeypatch,
):
    """兼容 GET query 时必须明确弃用并做本地限流。"""
    _create_access_token(db_session, test_user)
    monkeypatch.setattr(access_tokens, "_LEGACY_VALIDATE_MAX_ATTEMPTS", 1, raising=False)
    monkeypatch.setattr(access_tokens, "_LEGACY_VALIDATE_WINDOW_SECONDS", 60, raising=False)
    if hasattr(access_tokens, "_legacy_validate_attempts"):
        access_tokens._legacy_validate_attempts.clear()

    first = client.get("/api/v1/access-tokens/validate?token=secret-access-token")
    second = client.get("/api/v1/access-tokens/validate?token=secret-access-token")

    assert first.status_code == 200
    assert first.headers.get("Deprecation") == "true"
    assert "POST" in first.headers.get("Warning", "")
    assert second.status_code == 429


def test_announcements_router_has_no_optional_auth_stub():
    """移除始终返回 None 的 get_optional_user stub，避免误用造成权限绕过。"""
    from app.routers import announcements

    assert not hasattr(announcements, "get_optional_user")
