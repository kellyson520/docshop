from app.services.preview_manifest_service import (
    build_preview_manifest,
    build_preview_manifest_payload,
)


def test_build_preview_manifest_for_pptx_prefers_pdf_and_thumbnails():
    manifest = build_preview_manifest(
        file_profile={"category": "office", "preview_mode": "converted"},
        preview_assets=[
            {"asset_type": "pdf", "url": "/api/v1/files/f1/assets/main.pdf"},
            {"asset_type": "thumbnail", "page_number": 1, "url": "/api/v1/files/f1/assets/thumb-1.png"},
        ],
        analysis_summary={"page_count": 12},
    )

    assert manifest["type"] == "office_pdf"
    assert manifest["status"] == "ready"
    assert manifest["primary_asset"]["asset_type"] == "pdf"
    assert manifest["thumbnails"][0]["page"] == 1


def test_build_preview_manifest_for_archive_uses_structure_mode():
    manifest = build_preview_manifest(
        file_profile={"category": "archive", "preview_mode": "structure"},
        preview_assets=[],
        analysis_summary={"entry_count": 42, "root_nodes": ["docs", "video"]},
    )

    assert manifest["type"] == "archive_structure"
    assert manifest["status"] == "ready"
    assert manifest["summary"]["entry_count"] == 42


def test_build_preview_manifest_for_html_uses_runtime_mode():
    manifest = build_preview_manifest(
        file_profile={"category": "html", "preview_mode": "native", "preview_status": "ready"},
        preview_assets=[
            {"asset_type": "html_runtime_entry", "url": "/api/v1/files/f1/preview?version=1"},
        ],
        analysis_summary={"title": "MATLAB 模拟测试"},
    )

    assert manifest["type"] == "html_runtime"
    assert manifest["status"] == "ready"
    assert manifest["primary_asset"]["asset_type"] == "html_runtime_entry"
    assert manifest["summary"]["title"] == "MATLAB 模拟测试"


def test_build_preview_manifest_payload_for_video_uses_preview_route():
    manifest = build_preview_manifest_payload(
        {"category": "video", "preview_mode": "native", "preview_status": "ready"},
        file_id="f1",
        version_id="v1",
        version_number=3,
        preview_assets=[
            {"id": "asset-video", "asset_type": "video", "status": "ready"},
            {"id": "asset-poster", "asset_type": "poster", "status": "ready"},
        ],
        analysis_summary={"codec": "aac"},
    )

    assert manifest["type"] == "video_native"
    assert manifest["primary_asset"]["asset_type"] == "video"
    assert manifest["primary_asset"]["url"] == "/api/v1/files/f1/preview?version=3"
    assert manifest["poster_asset"]["url"] == "/api/v1/files/f1/preview-assets/asset-poster"


def test_build_preview_manifest_payload_for_video_adds_missing_video_asset_when_only_poster_exists():
    manifest = build_preview_manifest_payload(
        {"category": "video", "preview_mode": "native", "preview_status": "ready"},
        file_id="f1",
        version_id="v1",
        version_number=3,
        preview_assets=[
            {"id": "asset-poster", "asset_type": "poster", "status": "ready"},
        ],
        analysis_summary={"codec": "aac"},
    )

    assert manifest["type"] == "video_native"
    assert manifest["primary_asset"]["asset_type"] == "video"
    assert manifest["primary_asset"]["url"] == "/api/v1/files/f1/preview?version=3"
    assert manifest["poster_asset"]["url"] == "/api/v1/files/f1/preview-assets/asset-poster"


def test_build_preview_manifest_payload_for_video_prefers_preview_video_asset_when_available():
    manifest = build_preview_manifest_payload(
        {"category": "video", "preview_mode": "native", "preview_status": "ready"},
        file_id="f1",
        version_id="v1",
        version_number=3,
        preview_assets=[
            {"id": "asset-poster", "asset_type": "poster", "status": "ready"},
            {"id": "asset-preview", "asset_type": "preview_video", "status": "ready"},
            {"id": "asset-video", "asset_type": "video", "status": "ready"},
        ],
        analysis_summary={"codec": "aac"},
    )

    assert manifest["type"] == "video_native"
    assert manifest["primary_asset"]["asset_type"] == "preview_video"
    assert manifest["primary_asset"]["url"] == "/api/v1/files/f1/preview-assets/asset-preview"
    assert manifest["poster_asset"]["url"] == "/api/v1/files/f1/preview-assets/asset-poster"
    assert manifest["original_asset"]["asset_type"] == "video"
    assert manifest["original_asset"]["url"] == "/api/v1/files/f1/preview?version=3"
