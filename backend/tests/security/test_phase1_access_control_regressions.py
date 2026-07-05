from app.config import settings
from app.deps.auth import get_password_hash
from app.models.diff_record import DiffRecord
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.project import Project
from app.models.resource_access_policy import ResourceAccessGroup, ResourceAccessPolicy
from app.models.share_token import ShareToken
from app.models.user import User
from app.models.user_group import UserGroup, UserGroupMember


def _make_user(db_session, username: str, role: str = "user") -> User:
    user = User(username=username, password_hash=get_password_hash("test123"), role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_file_with_pdf_version(db_session, owner: User, tmp_path, monkeypatch, filename: str = "secured.pdf"):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    project = Project(name=f"Project-{filename}", description="secured", owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename=filename,
        file_type="pdf",
        current_version=1,
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    storage_path = upload_dir / filename
    storage_path.write_bytes(b"%PDF-1.4 secured")

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1,
        storage_path=str(storage_path),
        file_hash=f"hash-{filename}",
        file_size=storage_path.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)
    return project, doc_file, version


def test_group_member_can_access_group_protected_file_preview(
    client,
    db_session,
    test_user_viewer,
    viewer_headers,
    tmp_path,
    monkeypatch,
):
    owner = _make_user(db_session, "phase1-owner-group-preview")
    _project, doc_file, _version = _make_file_with_pdf_version(
        db_session,
        owner,
        tmp_path,
        monkeypatch,
        filename="group-preview.pdf",
    )

    group = UserGroup(name="Legal Review", code="legal-review", description="legal", is_active=1)
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    db_session.add(UserGroupMember(group_id=group.id, user_id=test_user_viewer.id))
    db_session.commit()

    policy = ResourceAccessPolicy(
        resource_type="file",
        resource_id=doc_file.id,
        visibility="groups_required",
        allow_preview=1,
        allow_download_original=1,
        allow_download_converted=1,
        allow_diff=1,
        allow_versions=1,
        created_by=owner.id,
        updated_by=owner.id,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    db_session.add(ResourceAccessGroup(policy_id=policy.id, group_id=group.id))
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}/preview",
        headers=viewer_headers,
    )

    assert response.status_code == 200


def test_shared_file_token_ignores_group_policy_and_allows_anonymous(client, db_session, tmp_path, monkeypatch):
    owner = _make_user(db_session, "phase1-share-owner")
    _project, doc_file, _version = _make_file_with_pdf_version(
        db_session,
        owner,
        tmp_path,
        monkeypatch,
        filename="shared-policy.pdf",
    )

    group = UserGroup(name="Share Legal", code="share-legal", description="share legal", is_active=1)
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    policy = ResourceAccessPolicy(
        resource_type="file",
        resource_id=doc_file.id,
        visibility="groups_required",
        allow_preview=1,
        allow_download_original=1,
        allow_download_converted=1,
        allow_diff=1,
        allow_versions=1,
        created_by=owner.id,
        updated_by=owner.id,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)

    db_session.add(ResourceAccessGroup(policy_id=policy.id, group_id=group.id))
    db_session.commit()

    share_token = ShareToken(
        token="phase1-inherit-group-share-token",
        name="inherit group policy share",
        resource_type="file",
        resource_id=doc_file.id,
        allow_download=1,
        allow_preview=1,
        allow_diff=1,
        allow_versions=1,
        policy_mode="inherit_resource_policy",
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()
    db_session.refresh(share_token)

    response = client.get(f"/api/v1/share/{share_token.token}/files/{doc_file.id}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == doc_file.id


def test_file_diffs_route_denies_outsider_for_private_file(
    client,
    db_session,
    viewer_headers,
    tmp_path,
    monkeypatch,
):
    owner = _make_user(db_session, "phase1-diff-owner")
    _project, doc_file, version1 = _make_file_with_pdf_version(
        db_session,
        owner,
        tmp_path,
        monkeypatch,
        filename="private-diff.pdf",
    )

    version2_path = tmp_path / "uploads" / "private-diff-v2.pdf"
    version2_path.write_bytes(b"%PDF-1.4 secured v2")
    version2 = FileVersion(
        file_id=doc_file.id,
        version=2,
        sort_order=2,
        storage_path=str(version2_path),
        file_hash="hash-private-diff-v2",
        file_size=version2_path.stat().st_size,
    )
    db_session.add(version2)
    db_session.commit()
    db_session.refresh(version2)

    diff = DiffRecord(
        old_version_id=version1.id,
        new_version_id=version2.id,
        diff_type="text",
        diff_data="{}",
        summary="changed",
    )
    db_session.add(diff)
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}/diffs",
        headers=viewer_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "private_resource"
