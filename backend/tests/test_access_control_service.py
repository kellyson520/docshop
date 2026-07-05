from app.services.access_control_service import (
    AccessPolicy,
    AccessResource,
    AccessSubject,
    authorize_resource_action,
    load_user_group_codes,
    resolve_resource_policy,
)
from app.models.document_file import DocumentFile
from app.models.project import Project
from app.models.resource_access_policy import ResourceAccessGroup, ResourceAccessPolicy
from app.models.user import User
from app.models.user_group import UserGroup, UserGroupMember
from app.deps.auth import get_password_hash


def test_public_policy_allows_preview_for_anonymous():
    decision = authorize_resource_action(
        subject=AccessSubject.anonymous(),
        resource=AccessResource(resource_type="file", resource_id="f1", owner_id="u1"),
        action="view_preview",
        policy=AccessPolicy(visibility="public", allow_preview=True),
    )
    assert decision.allowed is True
    assert decision.reason == "allowed"


def test_group_policy_denies_non_member():
    decision = authorize_resource_action(
        subject=AccessSubject(
            user_id="u2",
            role="user",
            group_codes={"sales"},
            authenticated=True,
        ),
        resource=AccessResource(resource_type="file", resource_id="f1", owner_id="u1"),
        action="view_preview",
        policy=AccessPolicy(
            visibility="groups_required",
            allow_preview=True,
            required_group_codes={"legal"},
        ),
    )
    assert decision.allowed is False
    assert decision.reason == "group_required"


def test_password_policy_allows_unlocked_share_subject():
    decision = authorize_resource_action(
        subject=AccessSubject(
            user_id=None,
            role=None,
            group_codes=set(),
            authenticated=False,
            share_unlocked=True,
        ),
        resource=AccessResource(resource_type="file", resource_id="f1", owner_id="u1"),
        action="view_preview",
        policy=AccessPolicy(visibility="password_required", allow_preview=True),
    )
    assert decision.allowed is True
    assert decision.reason == "allowed"


def test_login_required_download_denies_anonymous():
    decision = authorize_resource_action(
        subject=AccessSubject.anonymous(),
        resource=AccessResource(resource_type="file", resource_id="f1", owner_id="u1"),
        action="download_original",
        policy=AccessPolicy(
            visibility="login_required",
            allow_download_original=True,
        ),
    )
    assert decision.allowed is False
    assert decision.reason == "login_required"


def test_owner_short_circuit_allows_private_resource():
    decision = authorize_resource_action(
        subject=AccessSubject(
            user_id="u1",
            role="user",
            group_codes=set(),
            authenticated=True,
        ),
        resource=AccessResource(resource_type="file", resource_id="f1", owner_id="u1"),
        action="download_original",
        policy=AccessPolicy(visibility="private", allow_download_original=True),
    )
    assert decision.allowed is True
    assert decision.reason == "owner_allowed"


def test_load_user_group_codes_returns_active_group_codes_for_user(db_session):
    user = User(username="policy-user", password_hash=get_password_hash("test123"), role="user")
    active_group = UserGroup(name="Legal", code="legal", is_active=1)
    inactive_group = UserGroup(name="Dormant", code="dormant", is_active=0)
    db_session.add_all([user, active_group, inactive_group])
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(active_group)
    db_session.refresh(inactive_group)

    db_session.add_all(
        [
            UserGroupMember(group_id=active_group.id, user_id=user.id),
            UserGroupMember(group_id=inactive_group.id, user_id=user.id),
        ]
    )
    db_session.commit()

    assert load_user_group_codes(db_session, user.id) == {"legal"}


def test_resolve_resource_policy_inherits_project_policy_for_file(db_session):
    owner = User(username="policy-owner", password_hash=get_password_hash("test123"), role="user")
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    project = Project(name="Policy Project", description="demo", owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="contract.pdf",
        file_type="pdf",
        current_version=1,
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    group = UserGroup(name="Reviewers", code="reviewers", is_active=1)
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    project_policy = ResourceAccessPolicy(
        resource_type="project",
        resource_id=project.id,
        visibility="groups_required",
        allow_preview=1,
        allow_download_original=0,
        allow_download_converted=1,
        allow_diff=1,
        allow_versions=1,
    )
    db_session.add(project_policy)
    db_session.commit()
    db_session.refresh(project_policy)

    db_session.add(ResourceAccessGroup(policy_id=project_policy.id, group_id=group.id))
    db_session.commit()

    resolved = resolve_resource_policy(
        db_session,
        resource_type="file",
        resource_id=doc_file.id,
        project_id=project.id,
    )

    assert resolved.visibility == "groups_required"
    assert resolved.required_group_codes == {"reviewers"}
    assert resolved.allow_download_original is False


def test_resolve_resource_policy_defaults_to_private_when_missing(db_session):
    resolved = resolve_resource_policy(
        db_session,
        resource_type="file",
        resource_id="missing-file",
        project_id="missing-project",
    )

    assert resolved.visibility == "private"
    assert resolved.required_group_codes == set()
