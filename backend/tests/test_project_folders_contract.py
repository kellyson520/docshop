from pathlib import Path

from app.models.project import Project
from app.models.user import User
from app.utils.security import get_password_hash


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_project_folder_model_and_schema_migration_contract():
    model_source = read("app/models/project_folder.py")
    document_source = read("app/models/document_file.py")
    init_source = read("app/models/__init__.py")
    database_source = read("app/database.py")

    assert "class ProjectFolder(Base)" in model_source
    assert '__tablename__ = "project_folders"' in model_source
    assert 'ForeignKey("projects.id"' in model_source
    assert "folder_id" in document_source
    assert 'ForeignKey("project_folders.id"' in document_source
    assert "ProjectFolder" in init_source
    assert "project_folders" in database_source
    assert "ALTER TABLE document_files ADD COLUMN folder_id" in database_source


def test_project_folder_routes_and_file_move_contract():
    projects_source = read("app/routers/projects.py")
    files_source = read("app/routers/files.py")

    assert '@router.get("/{project_id}/folders"' in projects_source
    assert '@router.post("/{project_id}/folders"' in projects_source
    assert '@router.put("/{project_id}/folders/{folder_id}"' in projects_source
    assert '@router.delete("/{project_id}/folders/{folder_id}"' in projects_source
    assert "ProjectFolderCreate" in projects_source
    assert "ProjectFolderUpdate" in projects_source
    assert '"folder_id": f.folder_id' in projects_source
    assert '@router.put("/files/{file_id}/folder"' in files_source
    assert "MoveFileFolderRequest" in files_source


def test_admin_can_create_folder_for_project_owned_by_another_user(client, auth_headers, db_session):
    owner = User(
        username="folder-owner",
        password_hash=get_password_hash("test123"),
        role="user",
    )
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    project = Project(name="非管理员创建的项目", description="folder test", owner_id=owner.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    response = client.post(
        f"/api/v1/projects/{project.id}/folders",
        headers=auth_headers,
        json={"name": "资料归档"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["name"] == "资料归档"
