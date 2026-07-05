from app.deps.auth import get_password_hash, verify_password
from app.models.document_file import DocumentFile
from app.models.project import Project
from app.models.resource_access_policy import ResourceAccessPolicy
from app.models.user import User
from app.models.user_group import UserGroup


def _make_user(db_session, username: str, role: str = "user") -> User:
    user = User(username=username, password_hash=get_password_hash("test123"), role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_file(db_session, owner: User) -> DocumentFile:
    project = Project(name="Policy Project", description="demo", owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="legal-contract.pdf",
        file_type="pdf",
        current_version=1,
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)
    return doc_file


def test_admin_can_create_group(client, auth_headers):
    response = client.post(
        "/api/v1/access-control/groups",
        headers=auth_headers,
        json={
            "name": "Legal",
            "code": "legal",
            "description": "legal reviewers",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == "legal"
    assert data["name"] == "Legal"
    assert data["description"] == "legal reviewers"


def test_admin_can_replace_group_members(client, auth_headers, db_session):
    group = UserGroup(name="Reviewers", code="reviewers", description="reviewers")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    member = _make_user(db_session, "group-member")

    response = client.put(
        f"/api/v1/access-control/groups/{group.id}/members",
        headers=auth_headers,
        json={"user_ids": [member.id]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == group.id
    assert data["member_user_ids"] == [member.id]


def test_admin_can_list_access_groups(client, auth_headers, db_session):
    db_session.add_all(
        [
            UserGroup(name="Legal Team", code="legal", description="legal", is_active=1),
            UserGroup(name="Finance Team", code="finance", description="finance", is_active=0),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/access-control/groups", headers=auth_headers)

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["code"] for item in items] == ["finance", "legal"]
    assert items[0]["is_active"] is False
    assert items[1]["is_active"] is True


def test_admin_can_set_and_get_file_policy(client, auth_headers, db_session, test_user):
    doc_file = _make_file(db_session, test_user)
    group = UserGroup(name="Legal Team", code="legal", description="legal")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    put_response = client.put(
        f"/api/v1/access-control/policies/file/{doc_file.id}",
        headers=auth_headers,
        json={
            "visibility": "groups_required",
            "group_codes": ["legal"],
            "allow_preview": True,
            "allow_download_original": False,
        },
    )

    assert put_response.status_code == 200
    put_data = put_response.json()["data"]
    assert put_data["visibility"] == "groups_required"
    assert put_data["group_codes"] == ["legal"]
    assert put_data["allow_download_original"] is False

    get_response = client.get(
        f"/api/v1/access-control/policies/file/{doc_file.id}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    get_data = get_response.json()["data"]
    assert get_data["resource_type"] == "file"
    assert get_data["resource_id"] == doc_file.id
    assert get_data["visibility"] == "groups_required"
    assert get_data["group_codes"] == ["legal"]


def test_policy_put_accepts_password_clear_and_merged_allow_download(client, auth_headers, db_session, test_user):
    doc_file = _make_file(db_session, test_user)

    put_response = client.put(
        f"/api/v1/access-control/policies/file/{doc_file.id}",
        headers=auth_headers,
        json={
            "visibility": "password_required",
            "password": "OpenSesame!1",
            "password_hint": "project code",
            "allow_download": False,
            "allow_preview": True,
            "allow_diff": False,
            "allow_versions": True,
        },
    )

    assert put_response.status_code == 200
    put_data = put_response.json()["data"]
    assert put_data["visibility"] == "password_required"
    assert put_data["password_hint"] == "project code"
    assert put_data["allow_download"] is False
    assert put_data["allow_download_original"] is False
    assert put_data["allow_download_converted"] is False
    assert put_data["has_password"] is True

    policy = (
        db_session.query(ResourceAccessPolicy)
        .filter(
            ResourceAccessPolicy.resource_type == "file",
            ResourceAccessPolicy.resource_id == doc_file.id,
        )
        .first()
    )
    assert policy is not None
    assert verify_password("OpenSesame!1", policy.password_hash)

    clear_response = client.put(
        f"/api/v1/access-control/policies/file/{doc_file.id}",
        headers=auth_headers,
        json={
            "visibility": "public",
            "clear_password": True,
            "allow_download": True,
        },
    )

    assert clear_response.status_code == 200
    clear_data = clear_response.json()["data"]
    assert clear_data["visibility"] == "public"
    assert clear_data["allow_download"] is True
    assert clear_data["allow_download_original"] is True
    assert clear_data["allow_download_converted"] is True
    assert clear_data["has_password"] is False

    db_session.refresh(policy)
    assert policy.password_hash is None
