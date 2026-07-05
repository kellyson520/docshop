import json
from pathlib import Path

from app.models.document_file import DocumentFile
from app.models.file_preview_asset import FilePreviewAsset
from app.models.file_version import FileVersion
from app.models.project import Project


def test_get_file_analysis_returns_archive_manifest(client, auth_headers, db_session, test_user):
    from app.models.file_analysis_record import FileAnalysisRecord

    project = Project(name="Preview Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    archive_file = DocumentFile(
        project_id=project.id,
        filename="bundle.zip",
        file_type="zip",
        file_category="archive",
        mime_type="application/zip",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(archive_file)
    db_session.commit()
    db_session.refresh(archive_file)

    version = FileVersion(
        file_id=archive_file.id,
        version=1,
        sort_order=1.0,
        storage_path="C:/tmp/bundle.zip",
        file_hash="0" * 64,
        file_size=123,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    analysis = FileAnalysisRecord(
        file_id=archive_file.id,
        version_id=version.id,
        analysis_type="archive_manifest",
        payload_json=json.dumps({"entry_count": 2, "root_nodes": ["docs"]}),
        status="ready",
    )
    db_session.add(analysis)
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{archive_file.id}/analysis",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["analysis_type"] == "archive_manifest"
    assert response.json()["data"]["payload"]["entry_count"] == 2


def test_get_preview_status_returns_file_preview_and_analysis_state(
    client,
    auth_headers,
    db_session,
    test_user,
):
    project = Project(name="Preview Status Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="guide.pdf",
        file_type="pdf",
        file_category="pdf",
        mime_type="application/pdf",
        current_version=1,
        preview_status="pending",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    response = client.get(
        f"/api/v1/files/{doc_file.id}/preview-status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["preview_status"] == "pending"
    assert payload["analysis_status"] == "ready"


def test_get_file_detail_includes_preview_manifest_and_analysis_summary(
    client,
    auth_headers,
    db_session,
    test_user,
):
    from app.models.file_analysis_record import FileAnalysisRecord

    project = Project(name="Rich Detail Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="slides.pptx",
        file_type="pptx",
        file_category="office",
        mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path="C:/tmp/slides.pptx",
        file_hash="1" * 64,
        file_size=4096,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    db_session.add_all(
        [
            FilePreviewAsset(
                file_id=doc_file.id,
                version_id=version.id,
                asset_type="pdf",
                storage_path="C:/tmp/slides.pdf",
                sort_order=0,
                status="ready",
            ),
            FilePreviewAsset(
                file_id=doc_file.id,
                version_id=version.id,
                asset_type="thumbnail",
                storage_path="C:/tmp/slides-thumb-1.png",
                page_number=1,
                sort_order=1,
                status="ready",
            ),
            FileAnalysisRecord(
                file_id=doc_file.id,
                version_id=version.id,
                analysis_type="office_summary",
                payload_json=json.dumps({"page_count": 12}),
                status="ready",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["file_category"] == "office"
    assert payload["capabilities"]["can_preview"] is True
    assert payload["preview_manifest"]["type"] == "office_pdf"
    assert payload["preview_manifest"]["primary_asset"]["asset_type"] == "pdf"
    assert payload["preview_manifest"]["thumbnails"][0]["page"] == 1
    assert payload["analysis_summary"]["page_count"] == 12


def test_get_version_preview_status_and_analysis_return_version_specific_payload(
    client,
    auth_headers,
    db_session,
    test_user,
):
    from app.models.file_analysis_record import FileAnalysisRecord

    project = Project(name="Version Analysis Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    archive_file = DocumentFile(
        project_id=project.id,
        filename="bundle.zip",
        file_type="zip",
        file_category="archive",
        mime_type="application/zip",
        current_version=1,
        preview_status="processing",
        analysis_status="ready",
    )
    db_session.add(archive_file)
    db_session.commit()
    db_session.refresh(archive_file)

    version = FileVersion(
        file_id=archive_file.id,
        version=1,
        sort_order=1.0,
        storage_path="C:/tmp/bundle.zip",
        file_hash="2" * 64,
        file_size=2048,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    analysis = FileAnalysisRecord(
        file_id=archive_file.id,
        version_id=version.id,
        analysis_type="archive_manifest",
        payload_json=json.dumps({"entry_count": 3, "root_nodes": ["docs", "src"]}),
        status="ready",
    )
    db_session.add(analysis)
    db_session.commit()

    preview_status_response = client.get(
        f"/api/v1/files/{archive_file.id}/versions/{version.id}/preview-status",
        headers=auth_headers,
    )
    analysis_response = client.get(
        f"/api/v1/files/{archive_file.id}/versions/{version.id}/analysis",
        headers=auth_headers,
    )

    assert preview_status_response.status_code == 200
    assert analysis_response.status_code == 200
    assert preview_status_response.json()["data"]["preview_status"] == "ready"
    assert preview_status_response.json()["data"]["analysis_status"] == "ready"
    assert analysis_response.json()["data"]["analysis_type"] == "archive_manifest"
    assert analysis_response.json()["data"]["payload"]["root_nodes"] == ["docs", "src"]


def test_get_image_file_detail_includes_enriched_analysis_summary(
    client,
    auth_headers,
    db_session,
    test_user,
):
    from app.models.file_analysis_record import FileAnalysisRecord

    project = Project(name="Image Detail Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="poster.jpg",
        file_type="jpg",
        file_category="image",
        mime_type="image/jpeg",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path="C:/tmp/poster.jpg",
        file_hash="9" * 64,
        file_size=5120,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    db_session.add(
        FileAnalysisRecord(
            file_id=doc_file.id,
            version_id=version.id,
            analysis_type="media_metadata",
            payload_json=json.dumps(
                {
                    "dimensions": {"width": 3024, "height": 4032},
                    "format": "JPEG",
                    "color_mode": "RGB",
                    "has_alpha": False,
                    "orientation": 1,
                    "aspect_ratio": "3:4",
                }
            ),
            status="ready",
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["preview_manifest"]["type"] == "image_native"
    assert payload["preview_manifest"]["primary_asset"]["asset_type"] == "image"
    assert payload["analysis_summary"]["format"] == "JPEG"
    assert payload["analysis_summary"]["color_mode"] == "RGB"
    assert payload["analysis_summary"]["has_alpha"] is False
    assert payload["analysis_summary"]["aspect_ratio"] == "3:4"


def test_get_video_file_detail_includes_poster_asset_in_preview_manifest(
    client,
    auth_headers,
    db_session,
    test_user,
):
    from app.models.file_analysis_record import FileAnalysisRecord

    project = Project(name="Video Detail Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="demo.mp4",
        file_type="mp4",
        file_category="video",
        mime_type="video/mp4",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path="C:/tmp/demo.mp4",
        file_hash="6" * 64,
        file_size=8192,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    db_session.add_all(
        [
            FilePreviewAsset(
                file_id=doc_file.id,
                version_id=version.id,
                asset_type="poster",
                storage_path="C:/tmp/demo-poster.jpg",
                sort_order=0,
                status="ready",
            ),
            FilePreviewAsset(
                file_id=doc_file.id,
                version_id=version.id,
                asset_type="video",
                storage_path="C:/tmp/demo.mp4",
                sort_order=1,
                status="ready",
            ),
            FileAnalysisRecord(
                file_id=doc_file.id,
                version_id=version.id,
                analysis_type="media_metadata",
                payload_json=json.dumps({"duration_seconds": 42, "codec": "h264"}),
                status="ready",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["preview_manifest"]["type"] == "video_native"
    assert payload["preview_manifest"]["primary_asset"]["asset_type"] == "video"
    assert payload["preview_manifest"]["poster_asset"]["asset_type"] == "poster"
    assert "/preview-assets/" in payload["preview_manifest"]["poster_asset"]["url"]


def test_get_video_file_detail_prefers_preview_video_asset_in_preview_manifest(
    client,
    auth_headers,
    db_session,
    test_user,
):
    from app.models.file_analysis_record import FileAnalysisRecord

    project = Project(name="Compatible Video Detail Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="compatible-demo.mp4",
        file_type="mp4",
        file_category="video",
        mime_type="video/mp4",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path="C:/tmp/compatible-demo.mp4",
        file_hash="6" * 64,
        file_size=8192,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    db_session.add_all(
        [
            FilePreviewAsset(
                file_id=doc_file.id,
                version_id=version.id,
                asset_type="poster",
                storage_path="C:/tmp/compatible-demo-poster.jpg",
                sort_order=0,
                status="ready",
            ),
            FilePreviewAsset(
                file_id=doc_file.id,
                version_id=version.id,
                asset_type="preview_video",
                storage_path="C:/tmp/compatible-preview.mp4",
                sort_order=1,
                status="ready",
            ),
            FilePreviewAsset(
                file_id=doc_file.id,
                version_id=version.id,
                asset_type="video",
                storage_path="C:/tmp/compatible-demo.mp4",
                sort_order=2,
                status="ready",
            ),
            FileAnalysisRecord(
                file_id=doc_file.id,
                version_id=version.id,
                analysis_type="media_metadata",
                payload_json=json.dumps({"duration_seconds": 42, "codec": "h264"}),
                status="ready",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["preview_manifest"]["type"] == "video_native"
    assert payload["preview_manifest"]["primary_asset"]["asset_type"] == "preview_video"
    assert "/preview-assets/" in payload["preview_manifest"]["primary_asset"]["url"]
    assert payload["preview_manifest"]["original_asset"]["asset_type"] == "video"


def test_get_file_preview_asset_streams_poster_image(
    client,
    auth_headers,
    db_session,
    test_user,
    tmp_path,
    monkeypatch,
):
    from app.services import document_store

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))

    project = Project(name="Poster Asset Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="demo.mp4",
        file_type="mp4",
        file_category="video",
        mime_type="video/mp4",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path="C:/tmp/demo.mp4",
        file_hash="7" * 64,
        file_size=8192,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    poster_path = Path(document_store.dir_images(doc_file.id)) / "video-poster.jpg"
    poster_path.parent.mkdir(parents=True, exist_ok=True)
    poster_path.write_bytes(b"poster-image")

    asset = FilePreviewAsset(
        file_id=doc_file.id,
        version_id=version.id,
        asset_type="poster",
        storage_path=str(poster_path),
        sort_order=0,
        status="ready",
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    response = client.get(
        f"/api/v1/files/{doc_file.id}/preview-assets/{asset.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.content == b"poster-image"
    assert response.headers["content-type"].startswith("image/jpeg")


def test_preview_file_streams_mp4_inline_for_video_files(
    client,
    auth_headers,
    db_session,
    test_user,
    tmp_path,
    monkeypatch,
):
    from app.config import settings

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    video_path = upload_dir / "demo.mp4"
    video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 32
    video_path.write_bytes(video_bytes)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    project = Project(name="Inline Video Preview Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="demo.mp4",
        file_type="mp4",
        file_category="video",
        mime_type="video/mp4",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path=str(video_path),
        file_hash="preview-video",
        file_size=len(video_bytes),
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}/preview",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.content == video_bytes
    assert response.headers["content-type"].startswith("video/mp4")
    assert "inline;" in response.headers["content-disposition"]


def test_preview_file_prefers_compatible_preview_video_asset_when_present(
    client,
    auth_headers,
    db_session,
    test_user,
    tmp_path,
    monkeypatch,
):
    from app.config import settings
    from app.services import document_store

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    video_path = upload_dir / "demo.mp4"
    video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 32
    video_path.write_bytes(video_bytes)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))

    compatible_path = Path(document_store.dir_original("preview-video-file")) / "preview-video.mp4"
    compatible_path.parent.mkdir(parents=True, exist_ok=True)
    compatible_bytes = b"compatible-video"
    compatible_path.write_bytes(compatible_bytes)

    project = Project(name="Compatible Inline Video Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="demo.mp4",
        file_type="mp4",
        file_category="video",
        mime_type="video/mp4",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path=str(video_path),
        file_hash="preview-video-compatible",
        file_size=len(video_bytes),
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    db_session.add(
        FilePreviewAsset(
            file_id=doc_file.id,
            version_id=version.id,
            asset_type="preview_video",
            storage_path=str(compatible_path),
            sort_order=1,
            status="ready",
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}/preview",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.content == compatible_bytes
    assert response.headers["content-type"].startswith("video/mp4")


def test_preview_file_streams_png_inline_for_image_files(
    client,
    auth_headers,
    db_session,
    test_user,
    tmp_path,
    monkeypatch,
):
    from app.config import settings

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = upload_dir / "poster.png"
    image_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
        b"\xe2!\xbc3"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    image_path.write_bytes(image_bytes)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    project = Project(name="Inline Image Preview Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="poster.png",
        file_type="png",
        file_category="image",
        mime_type="image/png",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path=str(image_path),
        file_hash="preview-image",
        file_size=len(image_bytes),
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}/preview",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.content == image_bytes
    assert response.headers["content-type"].startswith("image/png")
    assert "inline;" in response.headers["content-disposition"]


def test_preview_file_returns_direct_html_document_for_html_files(
    client,
    auth_headers,
    auth_token,
    db_session,
    test_user,
    tmp_path,
    monkeypatch,
):
    from app.config import settings

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    html_path = upload_dir / "report.html"
    styles_dir = upload_dir / "styles"
    styles_dir.mkdir(parents=True, exist_ok=True)
    css_path = styles_dir / "app.css"
    css_content = "body { color: rgb(1, 2, 3); }"
    css_path.write_text(css_content, encoding="utf-8")
    html_content = (
        """<!DOCTYPE html><html><head><title>MATLAB模拟测试</title>"""
        """<link rel="stylesheet" href="styles/app.css"></head>"""
        """<body><h1>Preview</h1></body></html>"""
    )
    html_path.write_text(html_content, encoding="utf-8")
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    project = Project(name="Inline HTML Preview Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="report.html",
        file_type="html",
        file_category="html",
        mime_type="text/html",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path=str(html_path),
        file_hash="preview-html",
        file_size=len(html_content.encode("utf-8")),
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}/preview?auth_token={auth_token}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert f'href="/api/v1/files/{doc_file.id}/html-assets/styles/app.css?version=1&auth_token={auth_token}"' in response.text
    assert '<h1>Preview</h1>' in response.text
    assert "location.replace(" not in response.text
    assert response.headers["content-type"].startswith("text/html")

    asset_response = client.get(
        f"/api/v1/files/{doc_file.id}/html-assets/styles/app.css?version=1&auth_token={auth_token}",
    )

    assert asset_response.status_code == 200
    assert asset_response.text == css_content
    assert asset_response.headers["content-type"].startswith("text/css")


def test_get_tar_gz_file_detail_uses_archive_capabilities_from_compound_extension(
    client,
    auth_headers,
    db_session,
    test_user,
):
    from app.models.file_analysis_record import FileAnalysisRecord

    project = Project(name="Tar Preview Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="bundle.tar.gz",
        file_type="gz",
        file_category="archive",
        mime_type="application/gzip",
        current_version=1,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path="C:/tmp/bundle.tar.gz",
        file_hash="8" * 64,
        file_size=2048,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    db_session.add(
        FileAnalysisRecord(
            file_id=doc_file.id,
            version_id=version.id,
            analysis_type="archive_manifest",
            payload_json=json.dumps({"entry_count": 2, "root_nodes": ["assets", "docs"]}),
            status="ready",
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["file_category"] == "archive"
    assert payload["capabilities"]["can_preview"] is True
    assert payload["capabilities"]["can_diff_structural"] is True
    assert payload["preview_manifest"]["type"] == "archive_structure"


def test_get_versions_include_preview_refresh_token_and_derived_asset_version(
    client,
    auth_headers,
    db_session,
    test_user,
):
    project = Project(name="Version Token Project", description="desc", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="diagram.png",
        file_type="png",
        file_category="image",
        mime_type="image/png",
        current_version=2,
        preview_status="ready",
        analysis_status="ready",
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    old_version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path="C:/tmp/diagram-v1.png",
        file_hash="3" * 64,
        file_size=1024,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
        preview_refresh_token="token-v1",
        derived_asset_version=2,
    )
    latest_version = FileVersion(
        file_id=doc_file.id,
        version=2,
        sort_order=2.0,
        storage_path="C:/tmp/diagram-v2.png",
        file_hash="4" * 64,
        file_size=2048,
        storage_mode="full",
        preview_status="ready",
        analysis_status="ready",
        preview_refresh_token="token-v2",
        derived_asset_version=5,
    )
    db_session.add_all([old_version, latest_version])
    db_session.commit()

    response = client.get(
        f"/api/v1/files/{doc_file.id}/versions",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]["versions"]
    assert payload[0]["version"] == 2
    assert payload[0]["preview_refresh_token"] == "token-v2"
    assert payload[0]["derived_asset_version"] == 5
    assert payload[1]["preview_refresh_token"] == "token-v1"
    assert payload[1]["derived_asset_version"] == 2
