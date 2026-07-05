from app.models.category import Category, Tag
from app.models.document_file import DocumentFile
from app.models.project import Project
from app.utils.time import utc_now_iso


def test_project_file_list_keyword_filters_and_ranks_by_relevance(client, auth_headers, db_session, test_user):
    project = Project(name="算法搜索项目", owner_id=test_user.id)
    category = Category(name="预算分类", color="#2563eb")
    urgent_tag = Tag(name="预算", color="#f97316")
    db_session.add_all([project, category, urgent_tag])
    db_session.commit()
    db_session.refresh(project)

    exact = DocumentFile(
        project_id=project.id,
        filename="budget.pdf",
        display_name="budget",
        file_type="pdf",
        current_version=1,
        updated_at="2026-06-19T10:00:00Z",
        visit_count=1,
        download_count=1,
    )
    contains = DocumentFile(
        project_id=project.id,
        filename="june-budget.pdf",
        display_name="六月预算",
        file_type="pdf",
        current_version=1,
        updated_at="2026-06-19T09:00:00Z",
    )
    tag_hit = DocumentFile(
        project_id=project.id,
        filename="meeting-notes.pdf",
        display_name="会议纪要",
        file_type="pdf",
        current_version=1,
        category=category,
        tags=[urgent_tag],
        updated_at="2026-06-19T08:00:00Z",
    )
    miss = DocumentFile(
        project_id=project.id,
        filename="travel.pdf",
        display_name="差旅制度",
        file_type="pdf",
        current_version=1,
        updated_at=utc_now_iso(),
    )
    db_session.add_all([contains, miss, tag_hit, exact])
    db_session.commit()

    response = client.get(
        f"/api/v1/projects/{project.id}/files?keyword=budget",
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]["files"]
    assert [item["id"] for item in payload] == [exact.id, contains.id]
    assert payload[0]["display_name"] == "budget"

    tag_response = client.get(
        f"/api/v1/projects/{project.id}/files?keyword=预算",
        headers=auth_headers,
    )
    assert tag_response.status_code == 200, tag_response.text
    tag_payload = tag_response.json()["data"]["files"]
    assert tag_payload[0]["id"] == tag_hit.id
    assert {item["id"] for item in tag_payload} == {tag_hit.id, contains.id}
