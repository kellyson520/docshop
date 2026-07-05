from app.routers import announcements as announcements_router


def test_create_announcement_accepts_rich_blocks(client, auth_headers):
    response = client.post(
        "/api/v1/announcements",
        headers=auth_headers,
        json={
            "title": "Upgrade",
            "summary": "Night deploy",
            "content": "Deploy at 22:00",
            "content_blocks": [
                {"type": "paragraph", "text": "Deploy at 22:00"},
                {"type": "code", "language": "bash", "content": "docker compose up -d"},
            ],
            "popup_config": {"width": 720, "dismissible": True},
            "display_mode": "popup",
            "push_method": "all",
            "priority": 10,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["summary"] == "Night deploy"
    assert payload["data"]["content_blocks"][1]["type"] == "code"
    assert payload["data"]["popup_config"]["width"] == 720


def test_create_announcement_schedules_created_event(client, auth_headers, monkeypatch):
    recorded = []

    monkeypatch.setattr(
        announcements_router,
        "_notify_announcement_event",
        lambda event_type, payload: recorded.append((event_type, payload)),
    )

    response = client.post(
        "/api/v1/announcements",
        headers=auth_headers,
        json={
            "title": "Upgrade",
            "summary": "Night deploy",
            "content": "Deploy at 22:00",
        },
    )

    assert response.status_code == 201
    created_id = response.json()["data"]["id"]
    assert recorded == [("announcement.created", {"announcement_id": created_id})]


def test_active_announcements_return_rich_blocks(client, auth_headers):
    create_response = client.post(
        "/api/v1/announcements",
        headers=auth_headers,
        json={
            "title": "Popup",
            "summary": "Show rich popup",
            "content": "Fallback text",
            "content_blocks": [
                {"type": "paragraph", "text": "Rich popup body"},
                {"type": "button", "label": "View", "url": "/docs/deploy"},
            ],
            "display_mode": "popup",
            "push_method": "all",
            "priority": 5,
        },
    )
    assert create_response.status_code == 201

    response = client.get("/api/v1/announcements/active")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]
    target = next(item for item in payload["data"] if item["title"] == "Popup")
    assert target["summary"] == "Show rich popup"
    assert target["content_blocks"][0]["text"] == "Rich popup body"


def test_update_announcement_visibility_change_schedules_event(client, auth_headers, monkeypatch):
    create_response = client.post(
        "/api/v1/announcements",
        headers=auth_headers,
        json={
            "title": "Popup",
            "summary": "Show rich popup",
            "content": "Fallback text",
        },
    )
    announcement_id = create_response.json()["data"]["id"]
    recorded = []

    monkeypatch.setattr(
        announcements_router,
        "_notify_announcement_event",
        lambda event_type, payload: recorded.append((event_type, payload)),
    )

    response = client.put(
        f"/api/v1/announcements/{announcement_id}",
        headers=auth_headers,
        json={"is_active": 0},
    )

    assert response.status_code == 200
    assert recorded == [("announcement.visibility.changed", {"announcement_id": announcement_id})]


def test_delete_announcement_schedules_deleted_event(client, auth_headers, monkeypatch):
    create_response = client.post(
        "/api/v1/announcements",
        headers=auth_headers,
        json={
            "title": "Popup",
            "summary": "Show rich popup",
            "content": "Fallback text",
        },
    )
    announcement_id = create_response.json()["data"]["id"]
    recorded = []

    monkeypatch.setattr(
        announcements_router,
        "_notify_announcement_event",
        lambda event_type, payload: recorded.append((event_type, payload)),
    )

    response = client.delete(
        f"/api/v1/announcements/{announcement_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204
    assert recorded == [("announcement.deleted", {"announcement_id": announcement_id})]
