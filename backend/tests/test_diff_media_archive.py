import json

from app.models.document_file import DocumentFile
from app.models.file_analysis_record import FileAnalysisRecord
from app.models.file_version import FileVersion
from app.models.project import Project
from app.services.archive_analysis_service import build_archive_manifest
from app.services.diff_service import compute_diff


def _create_project(db_session, test_user):
    project = Project(
        name="Media Archive Diff Project",
        description="desc",
        owner_id=test_user.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def _create_document_file(
    db_session,
    project,
    *,
    filename: str,
    file_type: str,
    file_category: str,
    mime_type: str,
):
    doc_file = DocumentFile(
        project_id=project.id,
        filename=filename,
        file_type=file_type,
        file_category=file_category,
        mime_type=mime_type,
        current_version=2,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)
    return doc_file


def _create_version(
    db_session,
    doc_file,
    *,
    version_number: int,
    storage_path: str,
    file_hash: str,
    file_size: int,
):
    version = FileVersion(
        file_id=doc_file.id,
        version=version_number,
        sort_order=float(version_number),
        storage_path=storage_path,
        file_hash=file_hash,
        file_size=file_size,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)
    return version


def test_compute_diff_archive_uses_analysis_manifest_to_build_structure_payload(
    db_session,
    test_user,
    tmp_path,
):
    project = _create_project(db_session, test_user)
    doc_file = _create_document_file(
        db_session,
        project,
        filename="bundle.zip",
        file_type="zip",
        file_category="archive",
        mime_type="application/zip",
    )

    old_path = tmp_path / "bundle-v1.zip"
    old_path.write_bytes(b"archive-v1")
    new_path = tmp_path / "bundle-v2.zip"
    new_path.write_bytes(b"archive-v2")

    old_version = _create_version(
        db_session,
        doc_file,
        version_number=1,
        storage_path=str(old_path),
        file_hash="a" * 64,
        file_size=128,
    )
    new_version = _create_version(
        db_session,
        doc_file,
        version_number=2,
        storage_path=str(new_path),
        file_hash="b" * 64,
        file_size=256,
    )

    old_manifest = build_archive_manifest(
        [
            {"path": "docs/guide.md", "size": 12},
            {"path": "assets/logo.png", "size": 20},
        ]
    )
    new_manifest = build_archive_manifest(
        [
            {"path": "docs/guide.md", "size": 12},
            {"path": "videos/demo.mp4", "size": 40},
        ]
    )
    db_session.add_all(
        [
            FileAnalysisRecord(
                file_id=doc_file.id,
                version_id=old_version.id,
                analysis_type="archive_manifest",
                payload_json=json.dumps(old_manifest),
                status="ready",
            ),
            FileAnalysisRecord(
                file_id=doc_file.id,
                version_id=new_version.id,
                analysis_type="archive_manifest",
                payload_json=json.dumps(new_manifest),
                status="ready",
            ),
        ]
    )
    db_session.commit()

    result = compute_diff(old_version.id, new_version.id, db_session)
    payload = json.loads(result.diff_data)

    assert result.diff_type == "structure"
    assert payload["payload"]["added_paths"] == ["videos/demo.mp4"]
    assert payload["payload"]["removed_paths"] == ["assets/logo.png"]
    assert payload["summary"] == {"files_added": 1, "files_removed": 1}
    assert payload["metadata"]["file_category"] == "archive"
    assert "1" in result.summary


def test_compute_diff_media_uses_metadata_to_build_media_payload(
    db_session,
    test_user,
    tmp_path,
):
    project = _create_project(db_session, test_user)
    doc_file = _create_document_file(
        db_session,
        project,
        filename="demo.mp4",
        file_type="mp4",
        file_category="video",
        mime_type="video/mp4",
    )

    old_path = tmp_path / "demo-v1.mp4"
    old_path.write_bytes(b"video-v1")
    new_path = tmp_path / "demo-v2.mp4"
    new_path.write_bytes(b"video-v2-more-content")

    old_version = _create_version(
        db_session,
        doc_file,
        version_number=1,
        storage_path=str(old_path),
        file_hash="c" * 64,
        file_size=100,
    )
    new_version = _create_version(
        db_session,
        doc_file,
        version_number=2,
        storage_path=str(new_path),
        file_hash="d" * 64,
        file_size=164,
    )

    db_session.add_all(
        [
            FileAnalysisRecord(
                file_id=doc_file.id,
                version_id=old_version.id,
                analysis_type="media_metadata",
                payload_json=json.dumps(
                    {
                        "duration": 30,
                        "width": 1280,
                        "height": 720,
                        "codec": "h264",
                        "bit_rate": 64000,
                    }
                ),
                status="ready",
            ),
            FileAnalysisRecord(
                file_id=doc_file.id,
                version_id=new_version.id,
                analysis_type="media_metadata",
                payload_json=json.dumps(
                    {
                        "duration": 36,
                        "width": 1920,
                        "height": 1080,
                        "codec": "h265",
                        "bit_rate": 128000,
                    }
                ),
                status="ready",
            ),
        ]
    )
    db_session.commit()

    result = compute_diff(old_version.id, new_version.id, db_session)
    payload = json.loads(result.diff_data)

    assert result.diff_type == "media"
    assert payload["payload"]["left"]["preview_url"].endswith(
        f"/files/{doc_file.id}/versions/{old_version.id}/download"
    )
    assert payload["payload"]["right"]["preview_url"].endswith(
        f"/files/{doc_file.id}/versions/{new_version.id}/download"
    )
    assert payload["payload"]["left"]["analysis"]["duration_seconds"] == 30
    assert payload["payload"]["right"]["analysis"]["duration_seconds"] == 36
    assert payload["summary"]["duration_delta_seconds"] == 6
    assert payload["summary"]["size_delta_bytes"] == 64
    assert payload["summary"]["codec_changed"] is True


def test_list_diffs_returns_computed_archive_structure_diff(
    client,
    auth_headers,
    db_session,
    test_user,
    tmp_path,
):
    project = _create_project(db_session, test_user)
    doc_file = _create_document_file(
        db_session,
        project,
        filename="release.zip",
        file_type="zip",
        file_category="archive",
        mime_type="application/zip",
    )

    old_path = tmp_path / "release-v1.zip"
    old_path.write_bytes(b"release-v1")
    new_path = tmp_path / "release-v2.zip"
    new_path.write_bytes(b"release-v2")

    old_version = _create_version(
        db_session,
        doc_file,
        version_number=1,
        storage_path=str(old_path),
        file_hash="e" * 64,
        file_size=111,
    )
    new_version = _create_version(
        db_session,
        doc_file,
        version_number=2,
        storage_path=str(new_path),
        file_hash="f" * 64,
        file_size=222,
    )

    db_session.add_all(
        [
            FileAnalysisRecord(
                file_id=doc_file.id,
                version_id=old_version.id,
                analysis_type="archive_manifest",
                payload_json=json.dumps(
                    build_archive_manifest(
                        [{"path": "docs/intro.md", "size": 8}]
                    )
                ),
                status="ready",
            ),
            FileAnalysisRecord(
                file_id=doc_file.id,
                version_id=new_version.id,
                analysis_type="archive_manifest",
                payload_json=json.dumps(
                    build_archive_manifest(
                        [{"path": "docs/intro.md", "size": 8}, {"path": "docs/changelog.md", "size": 18}]
                    )
                ),
                status="ready",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}/diffs",
        headers=auth_headers,
        params={"old_version": old_version.id, "new_version": new_version.id},
    )

    assert response.status_code == 200
    diff = response.json()["data"]["diffs"][0]
    parsed = json.loads(diff["diff_data"])

    assert diff["diff_type"] == "structure"
    assert parsed["payload"]["added_paths"] == ["docs/changelog.md"]
    assert parsed["summary"] == {"files_added": 1, "files_removed": 0}
