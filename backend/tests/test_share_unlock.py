from app.config import settings
from app.deps.auth import get_password_hash
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.project import Project
from app.models.share_token import ShareToken
from app.models.user import User


def _make_user(db_session, username: str) -> User:
    user = User(username=username, password_hash=get_password_hash("test123"), role="user")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_password_protected_share(db_session, tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    owner = _make_user(db_session, "protected-share-owner")
    project = Project(name="Protected Share Project", description="private", owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="protected.pdf",
        file_type="pdf",
        current_version=1,
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    stored_file = upload_dir / "protected.pdf"
    stored_file.write_bytes(b"%PDF-1.4 protected share")

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1,
        storage_path=str(stored_file),
        file_hash="protected-share-hash",
        file_size=stored_file.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    share_token = ShareToken(
        token="protected-share-token",
        name="protected share",
        resource_type="file",
        resource_id=doc_file.id,
        created_by=owner.id,
        password_hash=get_password_hash("OpenSesame!1"),
        allow_preview=1,
    )
    db_session.add(share_token)
    db_session.commit()
    db_session.refresh(share_token)

    return share_token, doc_file


def test_unlock_returns_tab_grant_contract(client, db_session, tmp_path, monkeypatch):
    share_token, _doc_file = _make_password_protected_share(db_session, tmp_path, monkeypatch)

    response = client.post(
        f"/api/v1/share/{share_token.token}/unlock",
        headers={"X-Share-Tab-Id": "tab-a"},
        json={"password": "OpenSesame!1"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["unlocked"] is True
    assert isinstance(payload["grant_token"], str) and payload["grant_token"]
    assert payload["heartbeat_interval_seconds"] == 30
    assert payload["expires_at"]


def test_locked_share_preview_denies_without_cookie(client, db_session, tmp_path, monkeypatch):
    share_token, doc_file = _make_password_protected_share(db_session, tmp_path, monkeypatch)

    response = client.get(f"/api/v1/share/{share_token.token}/files/{doc_file.id}/preview")

    assert response.status_code == 403
    assert response.json()["detail"] == "share_password_required"


def test_locked_share_preview_allows_after_unlock(client, db_session, tmp_path, monkeypatch):
    share_token, doc_file = _make_password_protected_share(db_session, tmp_path, monkeypatch)

    unlock_response = client.post(
        f"/api/v1/share/{share_token.token}/unlock",
        headers={"X-Share-Tab-Id": "tab-a"},
        json={"password": "OpenSesame!1"},
    )
    assert unlock_response.status_code == 200
    grant_token = unlock_response.json()["data"]["grant_token"]

    preview_response = client.get(
        f"/api/v1/share/{share_token.token}/files/{doc_file.id}/preview",
        headers={
            "X-Share-Tab-Id": "tab-a",
            "X-Share-Grant": grant_token,
        },
    )

    assert preview_response.status_code == 200
    assert "<iframe" in preview_response.text


def test_release_invalidates_same_tab_grant(client, db_session, tmp_path, monkeypatch):
    share_token, doc_file = _make_password_protected_share(db_session, tmp_path, monkeypatch)

    unlock_response = client.post(
        f"/api/v1/share/{share_token.token}/unlock",
        headers={"X-Share-Tab-Id": "tab-a"},
        json={"password": "OpenSesame!1"},
    )
    assert unlock_response.status_code == 200
    grant_token = unlock_response.json()["data"]["grant_token"]

    release_response = client.post(
        f"/api/v1/share/{share_token.token}/grant/release",
        headers={
            "X-Share-Tab-Id": "tab-a",
            "X-Share-Grant": grant_token,
        },
    )

    assert release_response.status_code == 200
    assert release_response.json()["data"]["released"] is True

    preview_response = client.get(
        f"/api/v1/share/{share_token.token}/files/{doc_file.id}/preview",
        headers={
            "X-Share-Tab-Id": "tab-a",
            "X-Share-Grant": grant_token,
        },
    )

    assert preview_response.status_code == 403
    assert preview_response.json()["detail"] == "share_password_required"


def test_issue_resource_ticket_after_unlock_and_use_it_for_preview(client, db_session, tmp_path, monkeypatch):
    share_token, doc_file = _make_password_protected_share(db_session, tmp_path, monkeypatch)

    unlock_response = client.post(
        f"/api/v1/share/{share_token.token}/unlock",
        headers={"X-Share-Tab-Id": "tab-a"},
        json={"password": "OpenSesame!1"},
    )
    assert unlock_response.status_code == 200
    grant_token = unlock_response.json()["data"]["grant_token"]

    ticket_response = client.post(
        f"/api/v1/share/{share_token.token}/resource-ticket",
        headers={
            "X-Share-Tab-Id": "tab-a",
            "X-Share-Grant": grant_token,
        },
        json={
            "kind": "preview",
            "file_id": doc_file.id,
        },
    )

    assert ticket_response.status_code == 200
    ticket = ticket_response.json()["data"]["ticket"]
    assert isinstance(ticket, str) and ticket

    preview_response = client.get(
        f"/api/v1/share/{share_token.token}/files/{doc_file.id}/preview",
        params={"ticket": ticket},
    )

    assert preview_response.status_code == 200
    assert "<iframe" in preview_response.text


def test_issue_resource_ticket_after_unlock_and_use_it_for_download(client, db_session, tmp_path, monkeypatch):
    share_token, doc_file = _make_password_protected_share(db_session, tmp_path, monkeypatch)
    version = db_session.query(FileVersion).filter(FileVersion.file_id == doc_file.id).first()
    assert version is not None

    unlock_response = client.post(
        f"/api/v1/share/{share_token.token}/unlock",
        headers={"X-Share-Tab-Id": "tab-a"},
        json={"password": "OpenSesame!1"},
    )
    assert unlock_response.status_code == 200
    grant_token = unlock_response.json()["data"]["grant_token"]

    ticket_response = client.post(
        f"/api/v1/share/{share_token.token}/resource-ticket",
        headers={
            "X-Share-Tab-Id": "tab-a",
            "X-Share-Grant": grant_token,
        },
        json={
            "kind": "download_original",
            "file_id": doc_file.id,
            "version_id": version.id,
        },
    )

    assert ticket_response.status_code == 200
    ticket = ticket_response.json()["data"]["ticket"]
    assert isinstance(ticket, str) and ticket

    download_response = client.get(
        f"/api/v1/share/{share_token.token}/files/{doc_file.id}/versions/{version.id}/download",
        params={"ticket": ticket},
    )

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
