from datetime import datetime, timezone

from fastapi import HTTPException, status

from sqlalchemy.orm import Session

from app.utils.time import utc_now, utc_now_iso
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.project import Project
from app.models.share_token import SharePolicy, ShareToken


def _expired(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    try:
        expires = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        now = utc_now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc) > expires.astimezone(timezone.utc)
    except ValueError:
        return False


def assert_share_token_allowed(token: ShareToken | None, action: str = "view") -> None:
    if not token or token.is_active != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share token not found")
    if _expired(token.expires_at):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="share token expired")

    if action == "download":
        if token.allow_download != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="download disabled")
        if token.max_downloads and token.download_count >= token.max_downloads:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="download limit exceeded")
        return

    if token.max_views and token.view_count >= token.max_views:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="view limit exceeded")


def _is_share_token_allowed(token: ShareToken | None, action: str = "view") -> bool:
    try:
        assert_share_token_allowed(token, action=action)
    except HTTPException:
        return False
    return True


def consume_share_token(token: ShareToken, action: str = "view") -> None:
    if action == "download":
        token.download_count = int(token.download_count or 0) + 1
    else:
        token.view_count = int(token.view_count or 0) + 1
    token.updated_at = utc_now_iso()


VALID_RESOURCE_TYPES = {"project", "file", "version"}


def get_or_create_share_policy(db: Session) -> SharePolicy:
    policy = db.query(SharePolicy).filter(SharePolicy.id == "default").first()
    if policy:
        return policy
    policy = SharePolicy(id="default")
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def _resource_project(resource_type: str, resource_id: str, db: Session) -> tuple[Project, DocumentFile | None, FileVersion | None]:
    if resource_type == "project":
        project = db.query(Project).filter(Project.id == resource_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project, None, None

    if resource_type == "file":
        doc = db.query(DocumentFile).filter(DocumentFile.id == resource_id).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        project = db.query(Project).filter(Project.id == doc.project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project, doc, None

    if resource_type == "version":
        version = db.query(FileVersion).filter(FileVersion.id == resource_id).first()
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
        doc = db.query(DocumentFile).filter(DocumentFile.id == version.file_id).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        project = db.query(Project).filter(Project.id == doc.project_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project, doc, version

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid resource_type")


def assert_resource_owner(resource_type: str, resource_id: str, db: Session, user) -> tuple[Project, DocumentFile | None, FileVersion | None]:
    project, doc, version = _resource_project(resource_type, resource_id, db)
    if getattr(user, "role", None) != "admin" and project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to share this resource")
    return project, doc, version


def assert_policy_allows_creation(policy: SharePolicy, resource_type: str, user) -> None:
    if not policy.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="sharing disabled")
    if resource_type not in policy.allowed_types_list():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="resource type cannot be shared")
    if user is None and not policy.allow_anonymous_creation:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="anonymous sharing disabled")
    if user is not None and getattr(user, "role", None) != "admin" and not policy.allow_user_creation:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user sharing disabled")


def get_resource_share_token_map(
    resource_type: str,
    resource_ids: list[str],
    db: Session,
    action: str = "view",
) -> dict[str, ShareToken]:
    normalized_ids = [str(resource_id) for resource_id in resource_ids if resource_id]
    if not normalized_ids:
        return {}

    tokens = (
        db.query(ShareToken)
        .filter(
            ShareToken.resource_type == resource_type,
            ShareToken.resource_id.in_(normalized_ids),
        )
        .order_by(ShareToken.resource_id.asc(), ShareToken.created_at.desc())
        .all()
    )

    mapping: dict[str, ShareToken] = {}
    for token in tokens:
        if token.resource_id in mapping:
            continue
        if not _is_share_token_allowed(token, action=action):
            continue
        mapping[token.resource_id] = token
    return mapping


def get_resource_share_token(
    resource_type: str,
    resource_id: str,
    db: Session,
    action: str = "view",
) -> ShareToken | None:
    return get_resource_share_token_map(resource_type, [resource_id], db, action=action).get(str(resource_id))


def ensure_project_share_token(project: Project, db: Session, created_by: str | None = None) -> ShareToken:
    token = get_resource_share_token("project", project.id, db, action="view")
    if token:
        return token

    token = ShareToken(
        token=ShareToken.generate(),
        name=f"分享项目：{str(project.name or '项目')}"[:120],
        resource_type="project",
        resource_id=project.id,
        is_active=1,
        created_by=str(created_by or project.owner_id or "system"),
    )
    db.add(token)
    return token


def resolve_share_token(raw_token: str, db: Session, action: str = "view") -> dict:
    share_token = db.query(ShareToken).filter(ShareToken.token == raw_token).first()
    if share_token:
        assert_share_token_allowed(share_token, action=action)
        project, doc, version = _resource_project(share_token.resource_type, share_token.resource_id, db)
        return {"share_token": share_token, "project": project, "file": doc, "version": version, "legacy": False}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")


def share_scope_file_filter(resolved: dict, db: Session, file_id: str) -> DocumentFile:
    share_token = resolved.get("share_token")
    scoped_file = resolved.get("file")
    scoped_version = resolved.get("version")
    project = resolved["project"]
    if scoped_version and scoped_version.file_id != file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if scoped_file and scoped_file.id != file_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    doc = db.query(DocumentFile).filter(DocumentFile.id == file_id, DocumentFile.project_id == project.id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return doc


def share_scope_versions_query(resolved: dict, db: Session, file_id: str):
    query = db.query(FileVersion).filter(FileVersion.file_id == file_id)
    scoped_version = resolved.get("version")
    if scoped_version:
        query = query.filter(FileVersion.id == scoped_version.id)
    return query


def assert_version_in_share_scope(resolved: dict, version: FileVersion) -> None:
    scoped_version = resolved.get("version")
    if scoped_version and version.id != scoped_version.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
