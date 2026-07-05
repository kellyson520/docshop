from app.services.file_capability_service import resolve_file_profile
from app.models.project import Project
from tests.test_files import _create_minimal_pdf

import io


def test_resolve_file_profile_for_mp4_and_zip():
    mp4 = resolve_file_profile(filename="demo.mp4", mime_type="video/mp4")
    archive = resolve_file_profile(
        filename="bundle.7z",
        mime_type="application/x-7z-compressed",
    )

    assert mp4["category"] == "video"
    assert mp4["capabilities"]["can_play"] is True
    assert mp4["capabilities"]["can_diff_visual"] is True
    assert archive["category"] == "archive"
    assert archive["capabilities"]["can_diff_structural"] is True
    assert archive["preview_fallback"] == "structure_only"


def test_resolve_file_profile_for_pptx_uses_converted_preview():
    profile = resolve_file_profile(
        filename="roadmap.pptx",
        mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )

    assert profile["category"] == "office"
    assert profile["preview_mode"] == "converted"
    assert profile["capabilities"]["can_generate_thumbnail"] is True


def test_resolve_file_profile_for_tar_gz_uses_archive_structure_preview():
    profile = resolve_file_profile(
        filename="bundle.tar.gz",
        mime_type="application/gzip",
    )

    assert profile["ext"] == "tar.gz"
    assert profile["category"] == "archive"
    assert profile["preview_mode"] == "structure"
    assert profile["capabilities"]["can_preview"] is True
    assert profile["capabilities"]["can_diff_structural"] is True


def test_resolve_file_profile_for_html_uses_native_preview():
    profile = resolve_file_profile(
        filename="report.html",
        mime_type="text/html",
    )

    assert profile["category"] == "html"
    assert profile["preview_mode"] == "native"
    assert profile["preview_status"] == "ready"
    assert profile["capabilities"]["can_preview"] is True


def test_upload_file_response_includes_capability_metadata(
    client,
    auth_headers,
    db_session,
    test_user,
):
    project = Project(name="Capability project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    response = client.post(
        f"/api/v1/projects/{project.id}/files",
        headers=auth_headers,
        files={
            "file": (
                "guide.pdf",
                io.BytesIO(_create_minimal_pdf()),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    payload = response.json()["data"]
    assert payload["file_category"] == "pdf"
    assert payload["mime_type"] == "application/pdf"
    assert payload["preview_status"] == "pending"
    assert payload["analysis_status"] == "pending"
    assert payload["capabilities"]["can_preview"] is True
    assert payload["capabilities"]["can_generate_thumbnail"] is True
