from app.deps.auth import verify_password


def test_admin_can_change_own_password_and_login_with_new_password(
    client,
    auth_headers,
    db_session,
    test_user,
):
    response = client.post(
        "/api/v1/settings/change-password",
        headers=auth_headers,
        json={
            "old_password": "test123",
            "new_password": "NewAdmin@123",
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 0

    db_session.refresh(test_user)
    assert verify_password("NewAdmin@123", test_user.password_hash)

    old_login = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "test123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "NewAdmin@123"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["data"]["access_token"]


def test_admin_change_password_rejects_wrong_old_password(
    client,
    auth_headers,
    db_session,
    test_user,
):
    response = client.post(
        "/api/v1/settings/change-password",
        headers=auth_headers,
        json={
            "old_password": "wrong-old-password",
            "new_password": "NewAdmin@123",
        },
    )

    assert response.status_code == 401
    db_session.refresh(test_user)
    assert verify_password("test123", test_user.password_hash)
