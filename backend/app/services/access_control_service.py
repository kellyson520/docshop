from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.resource_access_policy import ResourceAccessGroup, ResourceAccessPolicy
from app.models.user import User
from app.models.user_group import UserGroup, UserGroupMember


ACCESS_ACTIONS = {
    "view_metadata",
    "view_preview",
    "view_page_asset",
    "view_diff",
    "view_versions",
    "download_original",
    "download_converted",
    "manage_share",
    "manage_policy",
}


@dataclass(frozen=True)
class AccessSubject:
    user_id: str | None
    role: str | None
    group_codes: set[str] = field(default_factory=set)
    authenticated: bool = False
    share_unlocked: bool = False

    @classmethod
    def anonymous(cls) -> "AccessSubject":
        return cls(
            user_id=None,
            role=None,
            group_codes=set(),
            authenticated=False,
            share_unlocked=False,
        )


@dataclass(frozen=True)
class AccessResource:
    resource_type: str
    resource_id: str
    owner_id: str | None = None


@dataclass(frozen=True)
class AccessPolicy:
    visibility: str = "inherit"
    allow_preview: bool = True
    allow_download_original: bool = True
    allow_download_converted: bool = True
    allow_diff: bool = True
    allow_versions: bool = True
    required_group_codes: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str


def _as_bool(value) -> bool:
    return bool(int(value)) if isinstance(value, int) else bool(value)


def _action_flag_allowed(action: str, policy: AccessPolicy) -> bool:
    if action in {"view_preview", "view_metadata", "view_page_asset"}:
        return policy.allow_preview
    if action == "view_diff":
        return policy.allow_diff
    if action == "view_versions":
        return policy.allow_versions
    if action == "download_original":
        return policy.allow_download_original
    if action == "download_converted":
        return policy.allow_download_converted
    return True


def load_user_group_codes(db: Session, user_id: str | None) -> set[str]:
    if not user_id:
        return set()
    rows = (
        db.query(UserGroup.code)
        .join(UserGroupMember, UserGroupMember.group_id == UserGroup.id)
        .filter(
            UserGroupMember.user_id == user_id,
            UserGroup.is_active == 1,
        )
        .all()
    )
    return {str(code).strip() for (code,) in rows if str(code).strip()}


def build_access_subject(
    db: Session,
    user: User | None = None,
    *,
    share_unlocked: bool = False,
) -> AccessSubject:
    if user is None:
        return AccessSubject(
            user_id=None,
            role=None,
            group_codes=set(),
            authenticated=False,
            share_unlocked=share_unlocked,
        )
    return AccessSubject(
        user_id=user.id,
        role=user.role,
        group_codes=load_user_group_codes(db, user.id),
        authenticated=True,
        share_unlocked=share_unlocked,
    )


def _policy_required_group_codes(db: Session, policy_id: str) -> set[str]:
    rows = (
        db.query(UserGroup.code)
        .join(ResourceAccessGroup, ResourceAccessGroup.group_id == UserGroup.id)
        .filter(
            ResourceAccessGroup.policy_id == policy_id,
            UserGroup.is_active == 1,
        )
        .all()
    )
    return {str(code).strip() for (code,) in rows if str(code).strip()}


def _to_access_policy(db: Session, model: ResourceAccessPolicy) -> AccessPolicy:
    return AccessPolicy(
        visibility=str(model.visibility or "inherit"),
        allow_preview=_as_bool(model.allow_preview),
        allow_download_original=_as_bool(model.allow_download_original),
        allow_download_converted=_as_bool(model.allow_download_converted),
        allow_diff=_as_bool(model.allow_diff),
        allow_versions=_as_bool(model.allow_versions),
        required_group_codes=_policy_required_group_codes(db, model.id),
    )


def _get_resource_policy(db: Session, resource_type: str, resource_id: str) -> ResourceAccessPolicy | None:
    policy = (
        db.query(ResourceAccessPolicy)
        .filter(
            ResourceAccessPolicy.resource_type == resource_type,
            ResourceAccessPolicy.resource_id == resource_id,
        )
        .first()
    )
    if not isinstance(policy, ResourceAccessPolicy):
        return None
    return policy


def resolve_resource_policy(
    db: Session,
    *,
    resource_type: str,
    resource_id: str,
    project_id: str | None = None,
    default_visibility: str = "private",
) -> AccessPolicy:
    specific = _get_resource_policy(db, resource_type, resource_id)
    if specific and str(specific.visibility or "inherit") != "inherit":
        return _to_access_policy(db, specific)

    if resource_type != "project" and project_id:
        project_policy = _get_resource_policy(db, "project", project_id)
        if project_policy and str(project_policy.visibility or "inherit") != "inherit":
            return _to_access_policy(db, project_policy)

    return AccessPolicy(visibility=default_visibility)


def authorize_resource_action(
    *,
    subject: AccessSubject,
    resource: AccessResource,
    action: str,
    policy: AccessPolicy,
) -> AccessDecision:
    if action not in ACCESS_ACTIONS:
        return AccessDecision(False, "invalid_action")

    if subject.role == "admin":
        return AccessDecision(True, "admin_allowed")

    if resource.owner_id and subject.user_id and resource.owner_id == subject.user_id:
        return AccessDecision(True, "owner_allowed")

    if not _action_flag_allowed(action, policy):
        return AccessDecision(False, "action_forbidden")

    visibility = policy.visibility or "inherit"
    if visibility in {"public", "inherit"}:
        return AccessDecision(True, "allowed")

    if visibility == "login_required":
        if not subject.authenticated:
            return AccessDecision(False, "login_required")
        return AccessDecision(True, "allowed")

    if visibility == "password_required":
        if not subject.share_unlocked:
            return AccessDecision(False, "password_required")
        return AccessDecision(True, "allowed")

    if visibility == "groups_required":
        if not subject.authenticated:
            return AccessDecision(False, "login_required")
        if policy.required_group_codes and not (policy.required_group_codes & subject.group_codes):
            return AccessDecision(False, "group_required")
        return AccessDecision(True, "allowed")

    if visibility == "private":
        return AccessDecision(False, "private_resource")

    return AccessDecision(False, "unsupported_visibility")


def require_resource_action(
    *,
    db: Session,
    action: str,
    resource_type: str,
    resource_id: str,
    owner_id: str | None = None,
    project_id: str | None = None,
    user: User | None = None,
    subject: AccessSubject | None = None,
    policy: AccessPolicy | None = None,
) -> AccessDecision:
    resolved_subject = subject or build_access_subject(db, user)
    resolved_policy = policy or resolve_resource_policy(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
    )
    decision = authorize_resource_action(
        subject=resolved_subject,
        resource=AccessResource(
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=owner_id,
        ),
        action=action,
        policy=resolved_policy,
    )
    if decision.allowed:
        return decision
    if decision.reason == "login_required":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)
