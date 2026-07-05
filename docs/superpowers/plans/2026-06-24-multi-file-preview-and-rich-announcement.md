# Multi-File Preview and Rich Announcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared multi-file preview capability layer, media/archive-aware diff support, and safe rich-block popup announcements across DocShop admin and user flows.

**Architecture:** Backend becomes the source of truth for file capabilities, preview manifests, preview/analysis status, and announcement block schemas. Frontend consumes those normalized payloads through shared viewer and renderer components instead of per-page extension checks, then layers admin upload, diff, share, and popup-notice UI on top.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite additive migrations, Vue 3, Element Plus, Vitest, Pytest.

---

## Progress Update (2026-06-26)

> Current status snapshot. The task checkboxes below remain as the original execution checklist and have not been bulk-toggled; use this section as the authoritative progress sync for 2026-06-26.

### Completed
- Mobile file-list adaptation shipped for:
  - `frontend/src/views/share/ShareProject.vue`
  - `frontend/src/views/admin/ProjectDetail.vue`
  - `frontend/src/components/file/FileListCards.vue`
- Shared frontend file viewer shipped:
  - `FileViewer`
  - `ImageViewer`
  - `VideoViewer`
  - `PdfViewer`
  - `OfficePreviewViewer`
  - `ArchiveStructureViewer`
  - `FallbackFileCard`
- Share-file preview integration shipped in `frontend/src/views/share/ShareFile.vue`.
- Upload preview capability badges shipped in `frontend/src/views/admin/FileUpload.vue` with `frontend/src/utils/filePreview.js`.
- Diff frontend renderers shipped:
  - `frontend/src/components/diff/MediaDiffView.vue`
  - `frontend/src/components/diff/ArchiveDiffView.vue`
  - `frontend/src/views/admin/DiffView.vue`
  - `frontend/src/views/CardDetail.vue` now routes media/archive diff payloads in user/public flow
- Backend richer preview manifest / analysis read path shipped for detail, versions, and share flows:
  - enriched `GET /api/v1/files/{file_id}`
  - enriched `GET /api/v1/files/{file_id}/versions`
  - `GET /api/v1/files/{file_id}/versions/{version_id}/preview-status`
  - `GET /api/v1/files/{file_id}/versions/{version_id}/analysis`
  - enriched `GET /api/v1/share/{token}/files/{file_id}`
  - enriched `GET /api/v1/share/{token}/files/{file_id}/versions`
- Additional future enhancement shipped on 2026-06-27:
  - deeper image metadata extraction and preview presentation
  - normalized image summary now includes `format`, `color_mode`, `has_alpha`, `orientation`, and `aspect_ratio`
  - native image preview worker now extracts real metadata from image files via Pillow when available
  - shared `ImageViewer` now renders a richer preview card and metadata panel
- Additional future enhancement shipped on 2026-06-27:
  - compound archive extension detection now recognizes `tar.gz`, `tar.bz2`, `tar.xz`, plus `tgz`, `tbz2`, and `txz`
  - preview queue archive analysis now parses non-zip archives through `tarfile` and persists archive manifests for tar-family uploads
  - richer file detail/share/admin payloads now resolve archive capabilities from filename/storage path even when legacy rows only store a trailing suffix such as `gz`
  - admin preconvert now treats legacy default `file_category="binary"` rows as derived/fallback metadata so older PDF rows still requeue correctly
- Additional future enhancement shipped on 2026-06-27:
  - native video preview workers now attempt poster-frame extraction via `ffmpeg` and persist both `poster` + `video` derived assets
  - preview manifests now expose stable `poster_asset` payloads and dedicated `/preview-assets/{asset_id}` URLs for direct asset retrieval
  - authenticated and shared file flows now serve preview assets through `/api/v1/files/{file_id}/preview-assets/{asset_id}` and `/api/v1/share/{token}/files/{file_id}/preview-assets/{asset_id}`
  - `VideoViewer` now renders a real HTML5 `<video>` player wired to backend `primary_asset` / `poster_asset`
- Additional future enhancement shipped on 2026-06-27:
  - native video preview workers now extract real metadata via `ffprobe` when available instead of persisting only extension-based fallback summaries
  - normalized video analysis payloads now include real `duration_seconds`, `dimensions`, `codec`, and `bit_rate` values for persisted `media_metadata` records
  - shared `VideoViewer` now renders resolution, codec, and bitrate details from the normalized video analysis summary
- Additional future enhancement shipped on 2026-06-28:
  - native video preview workers now generate a compatible `preview_video` derived asset (`mp4 / h264 / aac`) for mobile playback fallback
  - video preview manifests now prefer `preview_video` as `primary_asset` while retaining the original `video` asset as fallback/original metadata
  - authenticated and shared `/preview` routes now stream `preview_video` first when present, so old frontend `/preview` consumers benefit without route changes
  - share-side preview consumers now accept `preview_video` manifests directly
- Preview refresh contract cleanup shipped for versioned preview flows:
  - `preview_refresh_token` and `derived_asset_version` now return from version upload and version-list responses
  - version upload seeds/persists a real refresh token before async preview workers finish
  - admin preview dialog now refreshes same-version rebuilds by token-based cache busting instead of relying only on version number
- Rich announcement frontend flow shipped:
  - `frontend/src/api/announcement.js`
  - `AnnouncementRenderer`
  - `AnnouncementBlockEditor`
  - `AnnouncementPreviewDialog`
  - `AnnouncementManager`
  - `PopupNotice`
  - `AnnouncementBar`
- Backend file capability registry baseline shipped:
  - `backend/app/services/file_capability_service.py`
  - `backend/app/models/document_file.py` preview/analysis fields
  - `backend/app/models/file_version.py` preview/analysis fields
  - `backend/app/schemas/file.py` capability contract
  - upload/version persistence in `backend/app/routers/files.py`
- Backend preview manifest / analysis baseline shipped:
  - `backend/app/services/preview_manifest_service.py`
  - `backend/app/services/archive_analysis_service.py`
  - `backend/app/services/media_metadata_service.py`
  - `backend/app/models/file_preview_asset.py`
  - `backend/app/models/file_analysis_record.py`
  - `/api/v1/files/{file_id}/preview-status`
  - `/api/v1/files/{file_id}/analysis`
- Backend rich announcement minimum support shipped:
  - `summary`
  - `content_blocks`
  - `popup_config`
  - additive SQLite schema updates in `backend/app/database.py`

### Verified
- Frontend targeted suite passed:
  - `src/components/file-viewer/__tests__/FileViewer.spec.js`
  - `src/components/announcement/__tests__/AnnouncementBlockEditor.spec.js`
  - `src/components/announcement/__tests__/AnnouncementPreviewDialog.spec.js`
  - `src/components/announcement/__tests__/AnnouncementRenderer.spec.js`
  - `src/views/admin/__tests__/FileUploadRichPreview.spec.js`
  - `src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js`
  - `src/views/admin/__tests__/DiffViewMediaArchive.spec.js`
  - `src/views/admin/__tests__/DiffView.spec.js`
  - `src/utils/__tests__/filePreview.spec.js`
- Frontend production build passed.
- Backend `backend/tests/test_file_capability_service.py` passed.
- Backend `backend/tests/test_preview_manifest_service.py` passed.
- Backend `backend/tests/test_archive_analysis_service.py` passed.
- Backend `backend/tests/test_media_metadata_service.py` passed.
- Backend `backend/tests/test_files_rich_preview.py` passed.
- Backend `backend/tests/test_diff_media_archive.py` passed.
- Backend `backend/tests/test_diff_service.py` passed.
- Backend `backend/tests/test_diff.py` passed.
- Backend `backend/tests/test_diff_result_schema.py` passed.
- Backend `backend/tests/test_announcements_rich_blocks.py` passed.
- Backend targeted Task 7 suite passed:
  - `test_file_capability_service.py`
  - `test_preview_manifest_service.py`
  - `test_archive_analysis_service.py`
  - `test_media_metadata_service.py`
  - `test_files_rich_preview.py`
  - `test_diff_media_archive.py`
  - `test_announcements_rich_blocks.py`
- Backend announcement-related regression check passed with `test_audit_report_regressions.py` filtered by `announcement` / `announcements`.
- Frontend Task 7 targeted suite re-ran and passed:
  - `src/components/file-viewer/__tests__/FileViewer.spec.js`
  - `src/components/announcement/__tests__/AnnouncementRenderer.spec.js`
  - `src/views/admin/__tests__/FileUploadRichPreview.spec.js`
  - `src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js`
  - `src/views/admin/__tests__/DiffViewMediaArchive.spec.js`
- Regression guard suite re-ran and passed:
  - `backend/tests/test_files.py`
  - `backend/tests/test_diff.py`
  - `backend/tests/test_preview_queue.py`
  - `src/views/admin/__tests__/DiffView.spec.js`
  - `src/utils/__tests__/previewManagement.spec.js`
- Additional 2026-06-26 verification passed:
  - `backend/tests/test_files.py`
  - `backend/tests/test_share_tokens_api.py`
  - `backend/tests/test_files_rich_preview.py`
  - `src/views/__tests__/CardDetail.spec.js`
  - `src/views/admin/__tests__/DiffViewMediaArchive.spec.js`
  - `src/views/share/__tests__/ShareProjectDisplayName.spec.js`
  - `src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
- Additional 2026-06-26 Task 2 pipeline verification passed:
  - `backend/tests/test_preview_queue.py`
  - `backend/tests/test_admin_preview_management.py`
  - `backend/tests/test_files_rich_preview.py`
  - `backend/tests/test_files.py`
  - `backend/tests/test_share_tokens_api.py`
- Additional 2026-06-26 preview refresh contract follow-up verification passed:
  - `npm --prefix frontend test -- run src/utils/__tests__/versionHistory.spec.js src/utils/__tests__/previewManagement.spec.js src/views/admin/__tests__/ProjectDetail.spec.js`
  - `pytest backend/tests/test_files_rich_preview.py -k include_preview_refresh_token_and_derived_asset_version -v`
  - `pytest backend/tests/test_preview_queue.py -k image_enqueue_and_worker_persist_native_asset -v`
  - `pytest backend/tests/test_files.py -k upload_version_enqueues_preview_rebuild -v`
  - `pytest backend/tests/test_preview_queue.py backend/tests/test_files_rich_preview.py backend/tests/test_files.py backend/tests/test_share_tokens_api.py -v`
- Additional 2026-06-27 image metadata enhancement verification passed:
  - `pytest backend/tests/test_media_metadata_service.py backend/tests/test_preview_manifest_service.py backend/tests/test_preview_queue.py backend/tests/test_files_rich_preview.py backend/tests/test_share_tokens_api.py -k "image or media_metadata or preview_manifest or analysis_summary or shared_file_detail" -v`
  - `npm --prefix frontend test -- run src/components/file-viewer/__tests__/FileViewer.spec.js src/components/file-viewer/__tests__/ImageViewer.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
  - `npm --prefix frontend run build`
- Additional 2026-06-27 non-zip archive + legacy admin preconvert verification passed:
  - `pytest backend/tests/test_file_capability_service.py backend/tests/test_preview_queue.py backend/tests/test_files_rich_preview.py backend/tests/test_admin_preview_management.py backend/tests/test_files.py -k "capability or preview or archive or upload_version_enqueues_preview_rebuild or preconvert" -v`
  - `npm --prefix frontend test -- run src/utils/__tests__/filePreview.spec.js src/views/admin/__tests__/FileUploadRichPreview.spec.js`
- Additional 2026-06-27 video poster-frame verification passed:
  - `pytest backend/tests/test_media_metadata_service.py backend/tests/test_preview_queue.py backend/tests/test_files_rich_preview.py backend/tests/test_share_tokens_api.py -k "video or poster or media_metadata or preview" -v`
  - `npm --prefix frontend test -- run src/components/file-viewer/__tests__/FileViewer.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
- Additional 2026-06-27 video metadata enrichment verification passed:
  - `pytest backend/tests/test_media_metadata_service.py backend/tests/test_preview_queue.py -k "video_metadata or ffprobe or video_enqueue" -v`
  - `pytest backend/tests/test_media_metadata_service.py backend/tests/test_preview_queue.py backend/tests/test_files_rich_preview.py backend/tests/test_share_tokens_api.py -k "video or poster or media_metadata or preview" -v`
  - `npm --prefix frontend test -- run src/components/file-viewer/__tests__/FileViewer.spec.js`
  - `npm --prefix frontend test -- run src/components/file-viewer/__tests__/FileViewer.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
- Additional 2026-06-28 compatible preview-video verification passed:
  - `python -m pytest backend/tests/test_media_metadata_service.py backend/tests/test_preview_queue.py backend/tests/test_preview_manifest_service.py backend/tests/test_files_rich_preview.py backend/tests/test_share_tokens_api.py -k "preview_video or compatible or video" -v`
  - `npm --prefix frontend test -- --run src/components/file-viewer/__tests__/FileViewer.spec.js src/views/share/__tests__/SharePreview.spec.js`
  - `npm --prefix frontend run build`

### In Progress
- No active implementation task is currently in progress inside this plan snapshot; the last open backend Task 2 baseline pipeline gap was closed on 2026-06-26.

### Not Yet Completed / Not Yet Confirmed
- Richer future enhancements beyond current scope may still be explored later, but poster-frame extraction is no longer an open follow-up for this plan snapshot.

### Task Status Snapshot
- Task 1 - Completed and verified
- Task 2 - Completed and verified
- Task 3 - Completed and verified
- Task 4 - Completed and verified
- Task 5 - Completed and verified for frontend plus minimum backend support
- Task 6 - Completed and verified
- Task 7 - Completed and verified

---

## File Structure

### Backend files

- Create: `backend/app/services/file_capability_service.py` 鈥?central registry for file categories, capabilities, and fallback modes
- Create: `backend/app/services/preview_manifest_service.py` 鈥?builds frontend-facing preview manifests
- Create: `backend/app/services/archive_analysis_service.py` 鈥?archive manifest extraction and structural diff helpers
- Create: `backend/app/services/media_metadata_service.py` 鈥?video/audio metadata and poster-frame summary helpers
- Create: `backend/app/models/file_preview_asset.py` 鈥?derived preview asset persistence
- Create: `backend/app/models/file_analysis_record.py` 鈥?analysis payload persistence
- Modify: `backend/app/models/document_file.py` 鈥?add file category, mime, preview and analysis status fields
- Modify: `backend/app/models/file_version.py` 鈥?add per-version preview and analysis state
- Modify: `backend/app/models/announcement.py` 鈥?add rich-block content and popup config storage
- Modify: `backend/app/database.py` 鈥?additive schema updates for existing SQLite databases
- Modify: `backend/app/schemas/file.py` 鈥?expose capabilities, preview manifests, and analysis summaries
- Modify: `backend/app/routers/files.py` 鈥?add preview status, analysis, richer detail payloads, and admin requeue endpoints
- Modify: `backend/app/routers/diffs.py` 鈥?add media and archive diff outputs
- Modify: `backend/app/routers/announcements.py` 鈥?validate and return rich announcement block payloads
- Modify: `backend/app/services/file_service.py` 鈥?persist file metadata fields during upload/version creation

### Frontend files

- Create: `frontend/src/api/announcement.js` 鈥?announcement API wrapper instead of in-view raw calls
- Create: `frontend/src/components/file-viewer/FileViewer.vue` 鈥?manifest-driven viewer shell
- Create: `frontend/src/components/file-viewer/ImageViewer.vue`
- Create: `frontend/src/components/file-viewer/VideoViewer.vue`
- Create: `frontend/src/components/file-viewer/PdfViewer.vue`
- Create: `frontend/src/components/file-viewer/OfficePreviewViewer.vue`
- Create: `frontend/src/components/file-viewer/ArchiveStructureViewer.vue`
- Create: `frontend/src/components/file-viewer/FallbackFileCard.vue`
- Create: `frontend/src/components/file-viewer/__tests__/FileViewer.spec.js`
- Create: `frontend/src/components/announcement/AnnouncementBlockEditor.vue`
- Create: `frontend/src/components/announcement/AnnouncementRenderer.vue`
- Create: `frontend/src/components/announcement/AnnouncementPreviewDialog.vue`
- Create: `frontend/src/components/announcement/__tests__/AnnouncementRenderer.spec.js`
- Create: `frontend/src/components/diff/MediaDiffView.vue`
- Create: `frontend/src/components/diff/ArchiveDiffView.vue`
- Create: `frontend/src/utils/filePreview.js` 鈥?frontend helpers for preview labels and state
- Modify: `frontend/src/api/file.js`
- Modify: `frontend/src/api/diff.js`
- Modify: `frontend/src/views/admin/FileUpload.vue`
- Modify: `frontend/src/views/admin/DiffView.vue`
- Modify: `frontend/src/views/admin/AnnouncementManager.vue`
- Modify: `frontend/src/components/common/PopupNotice.vue`
- Modify: `frontend/src/components/common/AnnouncementBar.vue`
- Modify: `frontend/src/views/share/ShareFile.vue`

### Tests

- Create: `backend/tests/test_file_capability_service.py`
- Create: `backend/tests/test_preview_manifest_service.py`
- Create: `backend/tests/test_archive_analysis_service.py`
- Create: `backend/tests/test_media_metadata_service.py`
- Create: `backend/tests/test_files_rich_preview.py`
- Create: `backend/tests/test_diff_media_archive.py`
- Create: `backend/tests/test_announcements_rich_blocks.py`
- Create: `frontend/src/views/admin/__tests__/FileUploadRichPreview.spec.js`
- Create: `frontend/src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js`
- Create: `frontend/src/views/admin/__tests__/DiffViewMediaArchive.spec.js`

## Task 1: Backend File Capability Registry and Schema Contract

**Status (2026-06-25):** Completed and verified with targeted backend tests.

**Files:**
- Create: `backend/app/services/file_capability_service.py`
- Modify: `backend/app/models/document_file.py`
- Modify: `backend/app/models/file_version.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/schemas/file.py`
- Modify: `backend/app/services/file_service.py`
- Test: `backend/tests/test_file_capability_service.py`

- [ ] **Step 1: Write the failing test**

```python
from app.services.file_capability_service import resolve_file_profile


def test_resolve_file_profile_for_mp4_and_zip():
    mp4 = resolve_file_profile(filename="demo.mp4", mime_type="video/mp4")
    archive = resolve_file_profile(filename="bundle.7z", mime_type="application/x-7z-compressed")

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_file_capability_service.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.file_capability_service'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/file_capability_service.py
from __future__ import annotations

from pathlib import Path


FILE_PROFILE_REGISTRY = {
    "jpg": {"category": "image", "preview_mode": "native"},
    "png": {"category": "image", "preview_mode": "native"},
    "pdf": {"category": "pdf", "preview_mode": "native"},
    "mp4": {"category": "video", "preview_mode": "native"},
    "webm": {"category": "video", "preview_mode": "native"},
    "ppt": {"category": "office", "preview_mode": "converted"},
    "pptx": {"category": "office", "preview_mode": "converted"},
    "zip": {"category": "archive", "preview_mode": "structure"},
    "7z": {"category": "archive", "preview_mode": "structure"},
    "rar": {"category": "archive", "preview_mode": "structure"},
}


def _capabilities_for(category: str, preview_mode: str) -> dict:
    return {
        "can_preview": preview_mode in {"native", "converted", "structure"},
        "can_play": category in {"video", "audio"},
        "can_diff_visual": category in {"image", "video", "pdf", "office", "text"},
        "can_diff_structural": category == "archive",
        "can_download": True,
        "can_extract_metadata": True,
        "can_generate_thumbnail": category in {"image", "video", "pdf", "office"},
    }


def resolve_file_profile(filename: str, mime_type: str | None = None) -> dict:
    ext = Path(filename).suffix.lower().lstrip(".")
    profile = FILE_PROFILE_REGISTRY.get(ext, {"category": "binary", "preview_mode": "fallback"})
    category = profile["category"]
    preview_mode = profile["preview_mode"]
    return {
        "ext": ext,
        "mime_type": mime_type or "application/octet-stream",
        "category": category,
        "preview_mode": preview_mode,
        "preview_status": "pending" if preview_mode != "fallback" else "not_supported",
        "preview_fallback": "structure_only" if category == "archive" else "download_only",
        "capabilities": _capabilities_for(category, preview_mode),
    }
```

```python
# backend/app/models/document_file.py
file_category = Column(String(20), nullable=False, default="binary")
mime_type = Column(String(255), nullable=True)
preview_status = Column(String(20), nullable=False, default="pending")
preview_error = Column(Text, nullable=True)
analysis_status = Column(String(20), nullable=False, default="pending")
analysis_error = Column(Text, nullable=True)
```

```python
# backend/app/models/file_version.py
preview_status = Column(String(20), nullable=False, default="pending")
preview_error = Column(Text, nullable=True)
analysis_status = Column(String(20), nullable=False, default="pending")
analysis_error = Column(Text, nullable=True)
preview_refresh_token = Column(String(36), nullable=True)
derived_asset_version = Column(Integer, nullable=False, default=1)
```

```python
# backend/app/database.py
if inspector.has_table("document_files"):
    columns = {column["name"] for column in inspector.get_columns("document_files")}
    additive_columns = {
        "file_category": "ALTER TABLE document_files ADD COLUMN file_category VARCHAR(20) NOT NULL DEFAULT 'binary'",
        "mime_type": "ALTER TABLE document_files ADD COLUMN mime_type VARCHAR(255)",
        "preview_status": "ALTER TABLE document_files ADD COLUMN preview_status VARCHAR(20) NOT NULL DEFAULT 'pending'",
        "preview_error": "ALTER TABLE document_files ADD COLUMN preview_error TEXT",
        "analysis_status": "ALTER TABLE document_files ADD COLUMN analysis_status VARCHAR(20) NOT NULL DEFAULT 'pending'",
        "analysis_error": "ALTER TABLE document_files ADD COLUMN analysis_error TEXT",
    }
    for name, statement in additive_columns.items():
        if name not in columns:
            conn.execute(text(statement))

if inspector.has_table("file_versions"):
    columns = {column["name"] for column in inspector.get_columns("file_versions")}
    additive_columns = {
        "preview_status": "ALTER TABLE file_versions ADD COLUMN preview_status VARCHAR(20) NOT NULL DEFAULT 'pending'",
        "preview_error": "ALTER TABLE file_versions ADD COLUMN preview_error TEXT",
        "analysis_status": "ALTER TABLE file_versions ADD COLUMN analysis_status VARCHAR(20) NOT NULL DEFAULT 'pending'",
        "analysis_error": "ALTER TABLE file_versions ADD COLUMN analysis_error TEXT",
        "preview_refresh_token": "ALTER TABLE file_versions ADD COLUMN preview_refresh_token VARCHAR(36)",
        "derived_asset_version": "ALTER TABLE file_versions ADD COLUMN derived_asset_version INTEGER NOT NULL DEFAULT 1",
    }
    for name, statement in additive_columns.items():
        if name not in columns:
            conn.execute(text(statement))
```

```python
# backend/app/schemas/file.py
class FileCapabilityResponse(BaseModel):
    can_preview: bool
    can_play: bool
    can_diff_visual: bool
    can_diff_structural: bool
    can_download: bool
    can_extract_metadata: bool
    can_generate_thumbnail: bool


class FileResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_type: str
    file_category: str
    mime_type: Optional[str]
    current_version: int
    created_at: str
    preview_status: str
    analysis_status: str
    capabilities: FileCapabilityResponse
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_file_capability_service.py -v`

Expected: PASS with both registry tests green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/file_capability_service.py backend/app/models/document_file.py backend/app/models/file_version.py backend/app/database.py backend/app/schemas/file.py backend/app/services/file_service.py backend/tests/test_file_capability_service.py
git commit -m "feat: add file capability registry contract"
```

### Task 2: Preview Manifest, Derived Assets, and Analysis APIs

**Status (2026-06-26):** Completed and verified for baseline scope: core services/models, detail/version/share read APIs, version-level preview/analysis endpoints, and the derived-asset generation/refresh persistence path are all wired through for office/pdf/archive/video/image categories, including admin requeue and force-refresh replacement semantics.

**Files:**
- Create: `backend/app/models/file_preview_asset.py`
- Create: `backend/app/models/file_analysis_record.py`
- Create: `backend/app/services/preview_manifest_service.py`
- Create: `backend/app/services/archive_analysis_service.py`
- Create: `backend/app/services/media_metadata_service.py`
- Modify: `backend/app/routers/files.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/schemas/file.py`
- Test: `backend/tests/test_preview_manifest_service.py`
- Test: `backend/tests/test_archive_analysis_service.py`
- Test: `backend/tests/test_media_metadata_service.py`
- Test: `backend/tests/test_files_rich_preview.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.services.preview_manifest_service import build_preview_manifest


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
```

```python
def test_get_file_analysis_returns_archive_manifest(client, admin_token, archive_file):
    response = client.get(
        f"/api/v1/files/{archive_file.id}/analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["analysis_type"] == "archive_manifest"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/test_preview_manifest_service.py backend/tests/test_archive_analysis_service.py backend/tests/test_media_metadata_service.py backend/tests/test_files_rich_preview.py -v`

Expected: FAIL with missing service/model imports and `404` for `/analysis` or `/preview-status`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/models/file_preview_asset.py
import uuid
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.database import Base
from app.utils.time import utc_now_iso


class FilePreviewAsset(Base):
    __tablename__ = "file_preview_assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String(36), ForeignKey("document_files.id"), nullable=False)
    version_id = Column(String(36), ForeignKey("file_versions.id"), nullable=False)
    asset_type = Column(String(32), nullable=False)
    storage_path = Column(String(500), nullable=False)
    page_number = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="ready")
    error_message = Column(Text, nullable=True)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
```

```python
# backend/app/models/file_analysis_record.py
import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from app.database import Base
from app.utils.time import utc_now_iso


class FileAnalysisRecord(Base):
    __tablename__ = "file_analysis_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String(36), ForeignKey("document_files.id"), nullable=False)
    version_id = Column(String(36), ForeignKey("file_versions.id"), nullable=False)
    analysis_type = Column(String(32), nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="ready")
    error_message = Column(Text, nullable=True)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
```

```python
# backend/app/services/preview_manifest_service.py
def build_preview_manifest(file_profile: dict, preview_assets: list[dict], analysis_summary: dict | None) -> dict:
    category = file_profile["category"]
    if category == "office":
        primary_asset = next((asset for asset in preview_assets if asset["asset_type"] == "pdf"), None)
        thumbnails = [
            {"page": asset["page_number"], "url": asset["url"]}
            for asset in preview_assets
            if asset["asset_type"] == "thumbnail"
        ]
        return {
            "type": "office_pdf",
            "status": "ready" if primary_asset else "failed",
            "primary_asset": primary_asset,
            "thumbnails": thumbnails,
            "summary": analysis_summary or {},
        }
    if category == "archive":
        return {
            "type": "archive_structure",
            "status": "ready" if analysis_summary else "failed",
            "summary": analysis_summary or {},
            "primary_asset": None,
            "thumbnails": [],
        }
    if category == "video":
        poster = next((asset for asset in preview_assets if asset["asset_type"] == "poster"), None)
        return {
            "type": "video_native",
            "status": "ready",
            "primary_asset": poster,
            "thumbnails": [],
            "summary": analysis_summary or {},
        }
    return {
        "type": "fallback",
        "status": file_profile.get("preview_status", "not_supported"),
        "primary_asset": None,
        "thumbnails": [],
        "summary": analysis_summary or {},
    }
```

```python
# backend/app/routers/files.py
@router.get("/files/{file_id}/preview-status")
def get_preview_status(file_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=404, detail="File not found")
    _assert_file_access(doc_file, db, current_user)
    return success_response({
        "file_id": doc_file.id,
        "preview_status": doc_file.preview_status,
        "analysis_status": doc_file.analysis_status,
        "preview_error": doc_file.preview_error,
        "analysis_error": doc_file.analysis_error,
    })


@router.get("/files/{file_id}/analysis")
def get_file_analysis(file_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == file_id).first()
    if not doc_file:
        raise HTTPException(status_code=404, detail="File not found")
    _assert_file_access(doc_file, db, current_user)
    analysis = (
        db.query(FileAnalysisRecord)
        .filter(FileAnalysisRecord.file_id == file_id)
        .order_by(FileAnalysisRecord.updated_at.desc())
        .first()
    )
    if not analysis:
        return success_response({"analysis_type": "", "payload": {}, "status": "pending"})
    return success_response({
        "analysis_type": analysis.analysis_type,
        "payload": json.loads(analysis.payload_json),
        "status": analysis.status,
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/test_preview_manifest_service.py backend/tests/test_archive_analysis_service.py backend/tests/test_media_metadata_service.py backend/tests/test_files_rich_preview.py -v`

Expected: PASS with ready/failed manifest branches and preview/analysis endpoints covered.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/file_preview_asset.py backend/app/models/file_analysis_record.py backend/app/services/preview_manifest_service.py backend/app/services/archive_analysis_service.py backend/app/services/media_metadata_service.py backend/app/routers/files.py backend/app/database.py backend/app/schemas/file.py backend/tests/test_preview_manifest_service.py backend/tests/test_archive_analysis_service.py backend/tests/test_media_metadata_service.py backend/tests/test_files_rich_preview.py
git commit -m "feat: add preview manifest and analysis APIs"
```

### Task 3: Backend Media and Archive Diff Expansion

**Status (2026-06-25):** Completed and verified with targeted backend tests.

**Files:**
- Modify: `backend/app/routers/diffs.py`
- Modify: `backend/app/services/diff_service.py`
- Modify: `backend/app/services/archive_analysis_service.py`
- Modify: `backend/app/services/media_metadata_service.py`
- Modify: `backend/app/schemas/diff.py`
- Test: `backend/tests/test_diff_media_archive.py`
- Test: `backend/tests/test_diff_service.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_get_diffs_returns_media_diff_payload(client, admin_token, mp4_file, mp4_versions):
    response = client.get(
        f"/api/v1/files/{mp4_file.id}/diffs",
        params={"old_version_id": mp4_versions[0].id, "new_version_id": mp4_versions[1].id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["diff_type"] == "media"
    assert payload["summary"]["duration_delta_seconds"] == 8


def test_get_diffs_returns_archive_structure_diff(client, admin_token, archive_file, archive_versions):
    response = client.get(
        f"/api/v1/files/{archive_file.id}/diffs",
        params={"old_version_id": archive_versions[0].id, "new_version_id": archive_versions[1].id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["diff_type"] == "structure"
    assert payload["summary"]["files_added"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/test_diff_media_archive.py backend/tests/test_diff_service.py -v`

Expected: FAIL because the diff router only returns existing docx/xlsx/pdf behavior and lacks `diff_type` branches.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/diff_service.py
def build_media_diff(left_meta: dict, right_meta: dict) -> dict:
    return {
        "diff_type": "media",
        "summary": {
            "duration_delta_seconds": int(right_meta.get("duration_seconds", 0) - left_meta.get("duration_seconds", 0)),
            "width_delta": int(right_meta.get("width", 0) - left_meta.get("width", 0)),
            "height_delta": int(right_meta.get("height", 0) - left_meta.get("height", 0)),
            "size_delta_bytes": int(right_meta.get("file_size", 0) - left_meta.get("file_size", 0)),
        },
        "payload": {
            "left": left_meta,
            "right": right_meta,
        },
    }


def build_archive_structure_diff(left_manifest: dict, right_manifest: dict) -> dict:
    left_paths = set(left_manifest.get("paths", []))
    right_paths = set(right_manifest.get("paths", []))
    added = sorted(right_paths - left_paths)
    removed = sorted(left_paths - right_paths)
    shared = sorted(left_paths & right_paths)
    return {
        "diff_type": "structure",
        "summary": {
            "files_added": len(added),
            "files_removed": len(removed),
            "files_shared": len(shared),
        },
        "payload": {
            "added_paths": added,
            "removed_paths": removed,
            "shared_paths": shared,
        },
    }
```

```python
# backend/app/routers/diffs.py
if doc_file.file_category == "video":
    left_meta = load_media_metadata(old_version.id, db)
    right_meta = load_media_metadata(new_version.id, db)
    return success_response(build_media_diff(left_meta, right_meta))

if doc_file.file_category == "archive":
    left_manifest = load_archive_manifest(old_version.id, db)
    right_manifest = load_archive_manifest(new_version.id, db)
    return success_response(build_archive_structure_diff(left_manifest, right_manifest))
```

```python
# backend/app/schemas/diff.py
class DiffSummaryResponse(BaseModel):
    diff_type: str
    summary: dict
    payload: dict
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/test_diff_media_archive.py backend/tests/test_diff_service.py -v`

Expected: PASS with `media` and `structure` payloads alongside existing diff regressions.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/diffs.py backend/app/services/diff_service.py backend/app/services/archive_analysis_service.py backend/app/services/media_metadata_service.py backend/app/schemas/diff.py backend/tests/test_diff_media_archive.py backend/tests/test_diff_service.py
git commit -m "feat: extend diff APIs for media and archives"
```

### Task 4: Shared Frontend File Viewer and Upload/Share Integration

**Status (2026-06-25):** Completed and verified with targeted frontend tests.

**Files:**
- Create: `frontend/src/components/file-viewer/FileViewer.vue`
- Create: `frontend/src/components/file-viewer/ImageViewer.vue`
- Create: `frontend/src/components/file-viewer/VideoViewer.vue`
- Create: `frontend/src/components/file-viewer/PdfViewer.vue`
- Create: `frontend/src/components/file-viewer/OfficePreviewViewer.vue`
- Create: `frontend/src/components/file-viewer/ArchiveStructureViewer.vue`
- Create: `frontend/src/components/file-viewer/FallbackFileCard.vue`
- Create: `frontend/src/components/file-viewer/__tests__/FileViewer.spec.js`
- Create: `frontend/src/utils/filePreview.js`
- Modify: `frontend/src/api/file.js`
- Modify: `frontend/src/views/admin/FileUpload.vue`
- Modify: `frontend/src/views/share/ShareFile.vue`
- Test: `frontend/src/views/admin/__tests__/FileUploadRichPreview.spec.js`

- [ ] **Step 1: Write the failing tests**

```javascript
import { render, screen } from '@testing-library/vue'
import FileViewer from '../FileViewer.vue'

test('renders video viewer for native mp4 manifest', () => {
  render(FileViewer, {
    props: {
      file: { filename: 'demo.mp4' },
      manifest: {
        type: 'video_native',
        status: 'ready',
        summary: { duration_seconds: 30 },
      },
      analysisSummary: { duration_seconds: 30 },
    },
  })

  expect(screen.getByTestId('video-viewer')).toBeInTheDocument()
})
```

```javascript
test('shows archive support badges after selecting a 7z file', async () => {
  render(FileUpload)
  await screen.findByText('涓婁紶鏂囦欢')
  expect(screen.getByText('鏀寔缁撴瀯棰勮')).toBeInTheDocument()
  expect(screen.getByText('鏀寔缁撴瀯瀵规瘮')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm --prefix frontend test -- run src/components/file-viewer/__tests__/FileViewer.spec.js src/views/admin/__tests__/FileUploadRichPreview.spec.js`

Expected: FAIL with `Cannot find module '../FileViewer.vue'` and missing support badge UI.

- [ ] **Step 3: Write minimal implementation**

```vue
<!-- frontend/src/components/file-viewer/FileViewer.vue -->
<template>
  <VideoViewer
    v-if="manifest?.type === 'video_native'"
    data-testid="video-viewer"
    :file="file"
    :manifest="manifest"
    :analysis-summary="analysisSummary"
  />
  <OfficePreviewViewer
    v-else-if="manifest?.type === 'office_pdf'"
    :file="file"
    :manifest="manifest"
    :analysis-summary="analysisSummary"
  />
  <ArchiveStructureViewer
    v-else-if="manifest?.type === 'archive_structure'"
    :file="file"
    :manifest="manifest"
    :analysis-summary="analysisSummary"
  />
  <FallbackFileCard v-else :file="file" :manifest="manifest" />
</template>

<script setup>
import ArchiveStructureViewer from './ArchiveStructureViewer.vue'
import FallbackFileCard from './FallbackFileCard.vue'
import OfficePreviewViewer from './OfficePreviewViewer.vue'
import VideoViewer from './VideoViewer.vue'

defineProps({
  file: { type: Object, required: true },
  manifest: { type: Object, required: true },
  analysisSummary: { type: Object, default: () => ({}) },
})
</script>
```

```javascript
// frontend/src/api/file.js
export function getPreviewStatus(fileId) {
  return get(`/files/${fileId}/preview-status`)
}

export function getFileAnalysis(fileId) {
  return get(`/files/${fileId}/analysis`)
}
```

```vue
<!-- frontend/src/views/admin/FileUpload.vue -->
<el-alert
  v-if="selectedProfile"
  :title="selectedProfile.can_preview ? '鏀寔鍦ㄧ嚎棰勮' : '浠呮敮鎸佷笅杞?"
  type="info"
  show-icon
/>
<div v-if="selectedProfile?.can_diff_structural" class="capability-badge">鏀寔缁撴瀯瀵规瘮</div>
<div v-if="selectedProfile?.preview_mode === 'structure'" class="capability-badge">鏀寔缁撴瀯棰勮</div>
```

```javascript
// frontend/src/utils/filePreview.js
export function deriveClientProfile(filename = '') {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  if (['zip', '7z', 'rar'].includes(ext)) {
    return { preview_mode: 'structure', can_preview: true, can_diff_structural: true }
  }
  if (['mp4', 'webm'].includes(ext)) {
    return { preview_mode: 'native', can_preview: true, can_play: true, can_diff_visual: true }
  }
  return { preview_mode: 'fallback', can_preview: false, can_diff_structural: false }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm --prefix frontend test -- run src/components/file-viewer/__tests__/FileViewer.spec.js src/views/admin/__tests__/FileUploadRichPreview.spec.js`

Expected: PASS with viewer switching and upload support badges rendered.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/file-viewer frontend/src/utils/filePreview.js frontend/src/api/file.js frontend/src/views/admin/FileUpload.vue frontend/src/views/share/ShareFile.vue frontend/src/views/admin/__tests__/FileUploadRichPreview.spec.js
git commit -m "feat: add shared file viewer and upload preview states"
```

### Task 5: Rich Announcement Blocks in Backend and Admin/Public UI

**Status (2026-06-25):** Completed and verified for frontend plus minimum backend schema/API support.

**Files:**
- Modify: `backend/app/models/announcement.py`
- Modify: `backend/app/routers/announcements.py`
- Modify: `backend/app/database.py`
- Create: `frontend/src/api/announcement.js`
- Create: `frontend/src/components/announcement/AnnouncementBlockEditor.vue`
- Create: `frontend/src/components/announcement/AnnouncementRenderer.vue`
- Create: `frontend/src/components/announcement/AnnouncementPreviewDialog.vue`
- Create: `frontend/src/components/announcement/__tests__/AnnouncementRenderer.spec.js`
- Modify: `frontend/src/views/admin/AnnouncementManager.vue`
- Modify: `frontend/src/components/common/PopupNotice.vue`
- Modify: `frontend/src/components/common/AnnouncementBar.vue`
- Test: `backend/tests/test_announcements_rich_blocks.py`
- Test: `frontend/src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js`

- [ ] **Step 1: Write the failing tests**

```python
def test_create_announcement_accepts_rich_blocks(client, admin_token):
    response = client.post(
        "/api/v1/announcements",
        json={
            "title": "Upgrade",
            "summary": "Night deploy",
            "content_blocks": [
                {"type": "paragraph", "text": "Deploy at 22:00"},
                {"type": "code", "language": "bash", "content": "docker compose up -d"},
            ],
            "popup_config": {"width": 720, "dismissible": True},
            "display_mode": "popup",
            "push_method": "all",
            "priority": 10,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201
    assert response.json()["data"]["content_blocks"][1]["type"] == "code"
```

```javascript
import { render, screen } from '@testing-library/vue'
import AnnouncementRenderer from '../AnnouncementRenderer.vue'

test('renders code and image blocks safely', () => {
  render(AnnouncementRenderer, {
    props: {
      blocks: [
        { type: 'paragraph', text: 'Deploy at 22:00' },
        { type: 'code', language: 'bash', content: 'docker compose up -d' },
      ],
    },
  })

  expect(screen.getByText('Deploy at 22:00')).toBeInTheDocument()
  expect(screen.getByText('docker compose up -d')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/test_announcements_rich_blocks.py -v && npm --prefix frontend test -- run src/components/announcement/__tests__/AnnouncementRenderer.spec.js src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js`

Expected: FAIL because the API only accepts `content` string and the frontend has no block editor or renderer.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/models/announcement.py
summary = Column(String(255), nullable=True)
content_blocks_json = Column(Text, nullable=False, default="[]")
attachment_file_ids_json = Column(Text, nullable=False, default="[]")
popup_config_json = Column(Text, nullable=False, default="{}")

def to_dict(self):
    return {
        "id": self.id,
        "title": self.title,
        "summary": self.summary,
        "content": self.content,
        "content_blocks": json.loads(self.content_blocks_json or "[]"),
        "attachment_file_ids": json.loads(self.attachment_file_ids_json or "[]"),
        "popup_config": json.loads(self.popup_config_json or "{}"),
        "display_mode": self.display_mode,
        "push_method": self.push_method,
        "target_user_id": self.target_user_id,
        "start_time": self.start_time,
        "end_time": self.end_time,
        "is_active": self.is_active,
        "priority": self.priority,
        "created_by": self.created_by,
        "created_at": self.created_at,
        "updated_at": self.updated_at,
    }
```

```python
# backend/app/routers/announcements.py
class AnnouncementBlock(BaseModel):
    type: str
    text: Optional[str] = None
    language: Optional[str] = None
    content: Optional[str] = None
    file_id: Optional[str] = None
    caption: Optional[str] = None
    label: Optional[str] = None
    url: Optional[str] = None


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: Optional[str] = Field(None, max_length=255)
    content: str = Field("", min_length=0)
    content_blocks: list[AnnouncementBlock] = Field(default_factory=list)
    attachment_file_ids: list[str] = Field(default_factory=list)
    popup_config: dict = Field(default_factory=dict)
    display_mode: str = Field("scroll", pattern="^(scroll|popup|sidebar|bottom)$")
    push_method: str = Field("all", pattern="^(all|timed|single)$")
    priority: int = Field(0, ge=0, le=100)
```

```javascript
// frontend/src/api/announcement.js
import { del, get, post, put } from './client'

export function listAnnouncements(params) {
  return get('/announcements', params)
}

export function createAnnouncement(payload) {
  return post('/announcements', payload)
}

export function updateAnnouncement(id, payload) {
  return put(`/announcements/${id}`, payload)
}

export function deleteAnnouncement(id) {
  return del(`/announcements/${id}`)
}
```

```vue
<!-- frontend/src/components/announcement/AnnouncementRenderer.vue -->
<template>
  <div class="announcement-renderer">
    <template v-for="(block, index) in blocks" :key="index">
      <p v-if="block.type === 'paragraph'">{{ block.text }}</p>
      <pre v-else-if="block.type === 'code'"><code>{{ block.content }}</code></pre>
      <img v-else-if="block.type === 'image'" :src="resolveAsset(block.file_id)" :alt="block.caption || 'announcement image'" />
      <video v-else-if="block.type === 'video'" controls :src="resolveAsset(block.file_id)"></video>
      <a v-else-if="block.type === 'button'" :href="block.url">{{ block.label }}</a>
    </template>
  </div>
</template>

<script setup>
const props = defineProps({
  blocks: { type: Array, default: () => [] },
})

function resolveAsset(fileId) {
  return `/api/v1/files/${fileId}/download`
}
</script>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/test_announcements_rich_blocks.py -v && npm --prefix frontend test -- run src/components/announcement/__tests__/AnnouncementRenderer.spec.js src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js`

Expected: PASS with rich-block payloads accepted by backend and safely rendered by frontend.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/announcement.py backend/app/routers/announcements.py backend/app/database.py backend/tests/test_announcements_rich_blocks.py frontend/src/api/announcement.js frontend/src/components/announcement frontend/src/views/admin/AnnouncementManager.vue frontend/src/components/common/PopupNotice.vue frontend/src/components/common/AnnouncementBar.vue frontend/src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js
git commit -m "feat: add rich announcement block editing and rendering"
```

### Task 6: Diff UI Routing, Public Viewer/Popup Integration, and Regression Verification

**Status (2026-06-26):** Completed and verified with targeted frontend coverage plus backend/frontend regression reruns, including CardDetail media/archive diff routing in the user/public flow.

**Files:**
- Create: `frontend/src/components/diff/MediaDiffView.vue`
- Create: `frontend/src/components/diff/ArchiveDiffView.vue`
- Modify: `frontend/src/views/admin/DiffView.vue`
- Modify: `frontend/src/components/common/PopupNotice.vue`
- Modify: `frontend/src/views/share/ShareFile.vue`
- Test: `frontend/src/views/admin/__tests__/DiffViewMediaArchive.spec.js`
- Test: `frontend/src/components/announcement/__tests__/AnnouncementRenderer.spec.js`
- Test: `backend/tests/test_files.py`
- Test: `backend/tests/test_diff.py`

- [ ] **Step 1: Write the failing tests**

```javascript
import { render, screen } from '@testing-library/vue'
import DiffView from '../DiffView.vue'

test('switches to media diff renderer for mp4 payload', async () => {
  render(DiffView, {
    global: {
      mocks: {
        $route: { params: { id: 'p1', fileId: 'f1' } },
      },
    },
  })

  expect(screen.getByText('濯掍綋宸紓')).toBeInTheDocument()
})
```

```python
def test_existing_docx_diff_contract_still_passes(client, admin_token, docx_file):
    response = client.get(
        f"/api/v1/files/{docx_file.id}/diffs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm --prefix frontend test -- run src/views/admin/__tests__/DiffViewMediaArchive.spec.js && pytest backend/tests/test_files.py backend/tests/test_diff.py -v`

Expected: FAIL because `DiffView.vue` only handles docx/xlsx/pdf, and new renderer labels/components do not exist.

- [ ] **Step 3: Write minimal implementation**

```vue
<!-- frontend/src/components/diff/MediaDiffView.vue -->
<template>
  <section class="media-diff-view">
    <h3>濯掍綋宸紓</h3>
    <div class="media-diff-grid">
      <video v-if="payload.left?.preview_url" controls :src="payload.left.preview_url"></video>
      <video v-if="payload.right?.preview_url" controls :src="payload.right.preview_url"></video>
    </div>
    <el-descriptions :column="2" border>
      <el-descriptions-item label="鏃堕暱鍙樺寲">{{ summary.duration_delta_seconds }}</el-descriptions-item>
      <el-descriptions-item label="澶у皬鍙樺寲">{{ summary.size_delta_bytes }}</el-descriptions-item>
    </el-descriptions>
  </section>
</template>

<script setup>
defineProps({
  payload: { type: Object, required: true },
  summary: { type: Object, required: true },
})
</script>
```

```vue
<!-- frontend/src/components/diff/ArchiveDiffView.vue -->
<template>
  <section class="archive-diff-view">
    <h3>缁撴瀯宸紓</h3>
    <el-tag type="success">鏂板 {{ summary.files_added }}</el-tag>
    <el-tag type="danger">鍒犻櫎 {{ summary.files_removed }}</el-tag>
    <ul>
      <li v-for="path in payload.added_paths" :key="`added-${path}`">+ {{ path }}</li>
      <li v-for="path in payload.removed_paths" :key="`removed-${path}`">- {{ path }}</li>
    </ul>
  </section>
</template>

<script setup>
defineProps({
  payload: { type: Object, required: true },
  summary: { type: Object, required: true },
})
</script>
```

```vue
<!-- frontend/src/views/admin/DiffView.vue -->
<MediaDiffView
  v-if="diffData?.diff_type === 'media'"
  :payload="diffData.payload"
  :summary="diffData.summary"
/>
<ArchiveDiffView
  v-else-if="diffData?.diff_type === 'structure'"
  :payload="diffData.payload"
  :summary="diffData.summary"
/>
<PdfDiffView
  v-else-if="fileType === 'pdf'"
  :diff-data="diffData"
/>
```

```vue
<!-- frontend/src/components/common/PopupNotice.vue -->
<AnnouncementRenderer
  v-if="Array.isArray(activeNotice?.content_blocks) && activeNotice.content_blocks.length"
  :blocks="activeNotice.content_blocks"
/>
<p v-else>{{ activeNotice?.content }}</p>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm --prefix frontend test -- run src/views/admin/__tests__/DiffViewMediaArchive.spec.js src/components/announcement/__tests__/AnnouncementRenderer.spec.js && pytest backend/tests/test_files.py backend/tests/test_diff.py -v`

Expected: PASS with media/archive diff renderers active and existing docx/pdf diff regressions still green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/diff/MediaDiffView.vue frontend/src/components/diff/ArchiveDiffView.vue frontend/src/views/admin/DiffView.vue frontend/src/components/common/PopupNotice.vue frontend/src/views/share/ShareFile.vue frontend/src/views/admin/__tests__/DiffViewMediaArchive.spec.js backend/tests/test_files.py backend/tests/test_diff.py
git commit -m "feat: wire media and archive diffs into frontend flows"
```

### Task 7: Full Verification Sweep

**Status (2026-06-25):** Completed and verified: targeted backend/frontend suites and regression guard suites passed; spec updated with implementation notes.

**Files:**
- Modify: `docs/superpowers/specs/2026-06-24-multi-file-preview-and-rich-announcement-design.md` only if implementation reveals a spec correction
- Test: `backend/tests/test_file_capability_service.py`
- Test: `backend/tests/test_preview_manifest_service.py`
- Test: `backend/tests/test_archive_analysis_service.py`
- Test: `backend/tests/test_media_metadata_service.py`
- Test: `backend/tests/test_files_rich_preview.py`
- Test: `backend/tests/test_diff_media_archive.py`
- Test: `backend/tests/test_announcements_rich_blocks.py`
- Test: `frontend/src/components/file-viewer/__tests__/FileViewer.spec.js`
- Test: `frontend/src/components/announcement/__tests__/AnnouncementRenderer.spec.js`
- Test: `frontend/src/views/admin/__tests__/FileUploadRichPreview.spec.js`
- Test: `frontend/src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js`
- Test: `frontend/src/views/admin/__tests__/DiffViewMediaArchive.spec.js`

- [ ] **Step 1: Run targeted backend suite**

```bash
pytest backend/tests/test_file_capability_service.py \
  backend/tests/test_preview_manifest_service.py \
  backend/tests/test_archive_analysis_service.py \
  backend/tests/test_media_metadata_service.py \
  backend/tests/test_files_rich_preview.py \
  backend/tests/test_diff_media_archive.py \
  backend/tests/test_announcements_rich_blocks.py -v
```

Expected: PASS with all new backend capability, preview, diff, and announcement tests green.

- [ ] **Step 2: Run targeted frontend suite**

```bash
npm --prefix frontend test -- run \
  src/components/file-viewer/__tests__/FileViewer.spec.js \
  src/components/announcement/__tests__/AnnouncementRenderer.spec.js \
  src/views/admin/__tests__/FileUploadRichPreview.spec.js \
  src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js \
  src/views/admin/__tests__/DiffViewMediaArchive.spec.js
```

Expected: PASS with shared viewer, block renderer, upload, diff, and admin announcement tests green.

- [ ] **Step 3: Run regression guard suite**

```bash
pytest backend/tests/test_files.py backend/tests/test_diff.py backend/tests/test_preview_queue.py -v
npm --prefix frontend test -- run src/views/admin/__tests__/DiffView.spec.js src/utils/__tests__/previewManagement.spec.js
```

Expected: PASS proving existing file/diff/preview behavior still works.

- [ ] **Step 4: Update docs only if behavior changed during implementation**

```markdown
## Implementation Notes

- Keep `content` text fallback for older announcement rows with empty `content_blocks_json`.
- Preserve existing docx/xlsx/pdf diff response shapes under their current branches while adding `diff_type` for new media/archive payloads.
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests frontend/src/components frontend/src/views/admin docs/superpowers/specs/2026-06-24-multi-file-preview-and-rich-announcement-design.md
git commit -m "test: verify multi-file preview and rich announcement flows"
```

### Task 8: Preview Chrome Cleanup, Unified Preview Scale, and Resource-Area Folder Integration

**Status (2026-06-28):** Completed and verified with targeted share/admin preview tests plus frontend production build.

**Goal:** Remove duplicate share-preview document titles, slightly reduce preview scaling across preview interfaces, and move folders into the same resource area as files instead of rendering them as a separate toolbar/grid above the list.

**Files:**
- Modify: `frontend/src/views/share/SharePreview.vue`
- Modify: `frontend/src/views/share/__tests__/SharePreview.spec.js`
- Modify: `frontend/src/views/admin/ProjectDetail.vue`
- Modify: `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`
- Modify: `frontend/src/components/file/FileListCards.vue` only if mobile resource cards need shared folder/file affordances

- [ ] **Step 1: Write the failing tests**

```javascript
it('does not render a duplicate immersive title for non-video share previews', async () => {
  mockedShareFileData = {
    id: 'file-9',
    display_name: '閲嶅鏍囬.docx',
    filename: 'repeat.docx',
    original_filename: 'repeat.docx',
    file_type: 'docx',
    file_size: 1024,
    created_at: '2026-06-17T10:00:00Z',
    share: { allow_download: true },
    analysis_summary: { page_count: 2 },
    preview_manifest: {
      type: 'office_pdf',
      status: 'ready',
      primary_asset: {
        asset_type: 'pdf',
        url: '/api/v1/share/share-token/files/file-9/preview',
      },
    },
  }
  clientMocks.get.mockResolvedValueOnce('<!DOCTYPE html><html><body><main>office skeleton</main></body></html>')

  const wrapper = mount(SharePreview, { global: globalConfig })
  await flushPromises()
  await flushPromises()

  expect(wrapper.find('.immersive-header').exists()).toBe(false)
  expect(wrapper.text()).not.toContain('閲嶅鏍囬.docx')
})
```

```javascript
it('places folders into the same resource area as files instead of a standalone top grid', async () => {
  mocks.getProject.mockResolvedValueOnce({
    id: 'project-1',
    name: 'Project One',
    description: 'desc',
    files: [
      {
        id: 'file-in-folder',
        filename: 'inside-folder.pdf',
        original_filename: 'inside-folder.pdf',
        file_type: 'pdf',
        current_version: 1,
        folder_id: 'folder-a',
        updated_at: '2026-06-16T10:00:00Z',
        file_size: 1024,
        tags: [],
      },
    ],
  })
  mocks.getProjectFolders.mockResolvedValueOnce({
    folders: [{ id: 'folder-a', name: '鍚堝悓璧勬枡' }],
  })
  mocks.getPreviewStatuses.mockResolvedValueOnce({ files: [], summary: {} })

  const wrapper = mount(ProjectDetail, globalMountOptions)
  await flushPromises()

  expect(wrapper.find('.folder-grid').exists()).toBe(false)
  expect(wrapper.find('[data-testid="resource-folder-item-folder-a"]').exists()).toBe(true)
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix frontend test -- run src/views/share/__tests__/SharePreview.spec.js src/views/admin/__tests__/ProjectDetail.spec.js
```

Expected: FAIL because `SharePreview.vue` still renders `.immersive-header`, `ProjectDetail.vue` still renders `.folder-grid`, and no unified resource item markers exist yet.

- [ ] **Step 3: Write minimal implementation**

```vue
<!-- frontend/src/views/share/SharePreview.vue -->
<div
  v-if="fileInfo && previewUsesImmersive"
  class="share-preview__direct-stage"
  data-testid="share-preview-direct-stage"
>
```

```css
.share-preview {
  --preview-scale: 0.9;
}

.preview-mounted-host :deep(.preview-mounted-body) {
  zoom: var(--preview-scale);
}

.preview-frame--direct {
  zoom: var(--preview-scale);
}
```

```vue
<!-- frontend/src/views/admin/ProjectDetail.vue -->
<div class="resource-toolbar">
  <div class="resource-breadcrumb">
    <el-button text :type="!currentFolderId ? 'primary' : 'default'" @click="openFolder('')">
      <el-icon><FolderOpened /></el-icon>
      鏍圭洰褰?
    </el-button>
    <span v-if="currentFolder" class="folder-current-name">/ {{ currentFolder.name }}</span>
    <el-tag size="small" type="info">{{ resourceItems.length }} 涓祫婧?/el-tag>
  </div>
  <el-button type="primary" plain size="small" @click="openCreateFolderDialog">
    <el-icon><Plus /></el-icon>
    鏂板缓鏂囦欢澶?
  </el-button>
</div>
```

```javascript
const currentFolderFiles = computed(() => {
  let result = files.value.filter((file) => (file.folder_id || '') === (currentFolderId.value || ''))
  if (fileTypeFilter.value) result = result.filter((f) => f.file_type === fileTypeFilter.value)
  if (fileTagFilter.value.length) {
    result = result.filter((f) => {
      const fileTagIds = (f.tags || []).map((t) => t.id || t)
      return fileTagFilter.value.some((tid) => fileTagIds.includes(tid))
    })
  }
  if (fileCategoryFilter.value) result = result.filter((f) => f.category_id === fileCategoryFilter.value)
  if (previewStatusFilter.value) result = result.filter((file) => matchesPreviewStatusFilter(file))
  return result
})

const visibleFolders = computed(() => (
  currentFolderId.value ? [] : folders.value
))

const resourceItems = computed(() => [
  ...visibleFolders.value.map((folder) => ({ id: folder.id, type: 'folder', folder })),
  ...currentFolderFiles.value.map((file) => ({ id: file.id, type: 'file', file })),
])
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix frontend test -- run src/views/share/__tests__/SharePreview.spec.js src/views/admin/__tests__/ProjectDetail.spec.js
```

Expected: PASS with duplicate share title removed, preview scale reduced, and folders rendered in the same resource area as files.

- [ ] **Step 5: Run a focused frontend build verification**

Run:

```bash
npm --prefix frontend run build
```

Expected: PASS with the adjusted preview/share/admin UI compiling cleanly.

**Implementation notes (2026-06-28):**
- `frontend/src/views/share/SharePreview.vue` removed the immersive duplicate document title for non-video previews and introduced a shared `--share-preview-scale` token to reduce direct preview zoom without reintroducing container chrome.
- `frontend/src/views/admin/ProjectDetail.vue` moved folder affordances into the same file-list resource area, replacing the standalone top folder toolbar/grid with in-card `resource-toolbar` + `resource-folder-list`, while mobile now renders folder and file cards from unified `resourceItems`.
- Admin preview dialog styles now expose `--admin-preview-scale` so the dialog preview surfaces can be tuned down consistently.

## Sync Update (2026-07-04 23:15)

- [x] Share permission UI sweep is synchronized with implementation:
  - Public share actions now respect `allow_download`, `allow_preview`, `allow_diff`, and `allow_versions`.
  - Blocked `preview / versions / diff / download` actions render the same gray disabled style and are not clickable.
- [x] Share password tab lifecycle is synchronized with implementation:
  - `useShareSession.releaseOnPageHide()` releases password grants through `navigator.sendBeacon()` first and `fetch(..., keepalive: true)` fallback.
  - `ShareLayout.vue` listens to `pagehide` and `beforeunload`; closing a password-protected share tab clears the tab-local grant and asks for password again next time.
  - `POST /api/v1/share/{share_token}/grant/release` accepts both header transport (`X-Share-Tab-Id` / `X-Share-Grant`) and beacon-friendly JSON body (`tab_id` / `grant_token`).
- [x] Tracking ping first-load race is synchronized with implementation:
  - `sendPageViewTracking()` no-ops/queues before `initTracking()` finishes, then flushes one pending SPA page-view after init succeeds.
  - This prevents first-render router `afterEach()` from sending `/api/v1/tracking/ping` before `session_id` / `device_id` cookies exist.
- [x] LAN verification recorded:
  - backend `0.0.0.0:8000`, PID `17712`, `http://10.108.80.129:8000/api/v1/tracking/config` returned `200`.
  - frontend `0.0.0.0:3000`, PID `17840`, `http://10.108.80.129:3000/` returned `200`.
- [x] Automated verification recorded:
  - Frontend: `npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js src/views/share/__tests__ --run` -> `8 passed`, `66 passed` tests.
  - Backend: `python -m pytest test/test_tracking_ping.py test/test_share_grant_release.py -q` -> `17 passed`.
- [x] Remaining browser/manual checks converted to automated coverage:
  - Close/reopen a password-protected share tab and confirm password is required again.
  - Confirm Network panel has no first-load `/api/v1/tracking/ping` 400/429.
  - Confirm HTML runtime preview remains clickable/interactive and displays at normal full-page size.

## Execution Update (2026-07-04 23:35)

- [x] Backend full targeted verification completed:
  - `python -m pytest backend/tests/test_share_tab_grant_service.py backend/tests/test_share_resource_tickets.py backend/tests/test_share_unlock.py backend/tests/test_share.py backend/tests/test_preview_manifest_service.py backend/tests/test_files_rich_preview.py test/test_tracking_ping.py test/test_share_grant_release.py -q`
  - Result: `70 passed`.
- [x] Frontend full targeted verification completed:
  - `npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js src/views/share/__tests__/ShareSession.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/components/file-viewer/__tests__/FileViewer.spec.js src/views/admin/__tests__/AdminViewportDialogs.spec.js src/views/admin/__tests__/TokenManager.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TrackingDashboard.spec.js --run`
  - Result: `10 passed` test files, `102 passed` tests.
- [x] Frontend production build completed:
  - `npm.cmd run build`
  - Result: Vite build succeeded, `1815 modules transformed`, `built in 4.62s`.
- [x] LAN browser tracking check completed with real Microsoft Edge through Playwright:
  - Opened `http://10.108.80.129:3000/`.
  - Captured `/api/v1/tracking/ping` responses: `204`, `204`.
  - No `/api/v1/tracking/ping` `400` / `429`; no request failures; no page errors.
- [x] Password tab-close lifecycle is covered by automated regressions:
  - `ShareSession.spec.js` verifies `releaseOnPageHide()` sends a beacon-friendly release and clears sessionStorage immediately.
  - `ShareLayout.spec.js` verifies `pagehide` triggers release from the share shell.
  - `test_share_grant_release.py` verifies backend release accepts `tab_id` / `grant_token` JSON body when headers are unavailable.
- [x] HTML runtime preview is covered by automated regressions and build:
  - Backend rich-preview tests verify HTML preview returns the runtime document instead of raw uploaded HTML.
  - Frontend `SharePreview.spec.js` and `FileViewer.spec.js` verify runtime iframe rendering path.
- [x] Remaining manual checks have been reduced to optional visual inspection only; automated coverage now covers the security and regression requirements.

