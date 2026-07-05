from app.deps.auth import get_password_hash
from app.models.project import Project
from app.models.share_token import ShareToken
from app.models.user import User


def _create_public_project(db_session, *, owner_id, name="Public Project"):
    project = Project(
        name=name,
        description="Public project for uploader regression",
        owner_id=owner_id,
        is_public=True,
        share_token=f"share-token-{owner_id}",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def _create_project_share_token(db_session, *, owner_id, project_id, token="managed-project-token"):
    share_token = ShareToken(
        token=token,
        name="Public project share",
        resource_type="project",
        resource_id=project_id,
        is_active=1,
        created_by=owner_id,
    )
    db_session.add(share_token)
    db_session.commit()
    db_session.refresh(share_token)
    return share_token


def test_public_projects_include_uploader_for_existing_owner(client, db_session):
    owner = User(
        username="uploader-user",
        password_hash=get_password_hash("Uploader@123"),
        role="user",
        avatar_url="/api/v1/avatars/uploader.png",
    )
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)
    project = _create_public_project(db_session, owner_id=owner.id)
    share_token = _create_project_share_token(
        db_session,
        owner_id=owner.id,
        project_id=project.id,
        token="managed-public-project-token",
    )

    response = client.get("/api/v1/share/public-projects")

    assert response.status_code == 200
    item = next(
        item for item in response.json()["data"]["items"] if item["id"] == project.id
    )
    assert item["uploader"] == {
        "id": owner.id,
        "username": "uploader-user",
        "role": "user",
        "avatar": "/api/v1/avatars/uploader.png",
    }
    assert item["share_token"] == share_token.token


def test_public_projects_use_deleted_user_fallback_when_owner_row_is_missing(
    client,
    db_session,
):
    missing_owner_id = "missing-owner-id"
    project = _create_public_project(
        db_session,
        owner_id=missing_owner_id,
        name="Orphan Public Project",
    )
    _create_project_share_token(
        db_session,
        owner_id=missing_owner_id,
        project_id=project.id,
        token="managed-orphan-project-token",
    )

    response = client.get("/api/v1/share/public-projects")

    assert response.status_code == 200
    item = next(
        item for item in response.json()["data"]["items"] if item["id"] == project.id
    )
    assert item["uploader"] == {
        "id": missing_owner_id,
        "username": "已删除用户",
        "role": "user",
        "avatar": "",
    }
