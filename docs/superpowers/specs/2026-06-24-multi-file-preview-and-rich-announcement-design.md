# Multi-File Preview and Rich Announcement Design

Date: 2026-06-24

## Goal

Expand DocShop to support more daily-use file types such as MP4, ZIP, 7Z, PPT, and related office/media/archive formats across both frontend and admin flows, while adding safe rich-content popup announcements that support image, video, code, and file-reference blocks.

## Scope

This design covers:

- Admin upload and management enhancements
- Frontend and backend unified preview behavior
- Native preview, converted preview, structural preview, and graceful degradation
- Version comparison extensions for document, media, and archive files
- Announcement popup content blocks and renderer

This design does not cover:

- Arbitrary HTML announcement embedding
- External preview SaaS or third-party hosted preview engines
- Deep archive extraction browsing or downloading inner archive members in Phase 1

## Chosen Approach

Use a unified file capability layer shared by backend and frontend.

Core strategy:

1. Backend classifies each file into a stable category and generates a `capabilities` object.
2. Backend produces a `preview_manifest` and `analysis_summary` for the current file/version.
3. Frontend uses a shared `FileViewer` to render by manifest instead of scattered extension checks.
4. Preview generation stays self-hosted and uses the existing conversion chain where possible.
5. When preview cannot be generated, the UI degrades to metadata + error message + download entry.
6. Announcement popup content uses safe JSON blocks rather than raw HTML embedding.

This approach is preferred over page-by-page patching because DocShop already has upload, preview, versioning, diff, and announcement features. A shared capability layer keeps new file types from fragmenting logic across admin upload pages, project detail pages, share pages, and announcement popups.

## Product Decisions Confirmed

- Audience: both frontend users and backend admins
- Initial file coverage: common office/media/archive/document types
- Preview strategy: graded preview with graceful degradation
- Announcement popup embed strategy: safe rich content blocks
- Comparison scope: visual/structural comparison should expand beyond text-only flows
- Technical route: self-hosted preview first, convert when possible, degrade when necessary

## File Type Coverage

Initial target coverage:

- Images: `jpg`, `jpeg`, `png`, `gif`, `webp`, `svg`
- Video: `mp4`, `webm`
- Audio: `mp3`, `wav`
- Documents: `pdf`, `txt`, `md`
- Office: `doc`, `docx`, `xls`, `xlsx`, `ppt`, `pptx`
- Archives: `zip`, `7z`, `rar`

Future additions should only require extending the capability registry and viewer mapping, not rewriting business pages.

## Preview Grading Model

### Level A: Native Direct Preview

Use direct browser or existing frontend rendering:

- Images: inline image preview
- Video: native player for `mp4`/`webm`
- Audio: native audio player
- PDF: existing or shared PDF viewer
- Text: plain text/markdown/code-style rendering

### Level B: Converted Preview

Use backend conversion outputs:

- `doc`/`docx` -> PDF
- `xls`/`xlsx` -> PDF or generated page images
- `ppt`/`pptx` -> PDF plus page thumbnails

These conversions should reuse the current self-hosted preview pipeline and remain version-aware.

### Level C: Structural Preview

Used for archives:

- `zip`, `7z`, `rar`
- Show archive file tree
- Show total file count, directory count, total size, depth summary
- Show sampled inner paths and structural metadata

Phase 1 is read-only structure preview, not full in-browser extraction browsing.

### Level D: Graceful Degradation

When preview or analysis fails:

- Show file icon, file name, size, upload time, version information
- Show preview failure reason
- Show download button
- Keep previous successful derived preview if available for historical versions

## Unified Capability Model

Every file/version should expose a stable capability payload:

```json
{
  "category": "office",
  "ext": "pptx",
  "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "capabilities": {
    "can_preview": true,
    "can_play": false,
    "can_diff_visual": true,
    "can_diff_structural": false,
    "can_download": true,
    "can_extract_metadata": true,
    "can_generate_thumbnail": true
  },
  "preview_status": "ready",
  "preview_fallback": "download_only"
}
```

Status values:

- `pending`
- `processing`
- `ready`
- `failed`
- `not_supported`

Fallback modes:

- `download_only`
- `metadata_only`
- `structure_only`

## Backend Architecture

### 1. File Capability Service

Add a backend service such as:

- `backend/app/services/file_capability_service.py`

Responsibilities:

- Map extension/MIME to file category
- Determine preview/play/diff capabilities
- Decide primary preview strategy
- Define fallback behavior

This service becomes the single source of truth for supported file behavior.

### 2. Preview Manifest Service

Add:

- `backend/app/services/preview_manifest_service.py`

Responsibilities:

- Build `preview_manifest` for current file/version
- Resolve primary asset URLs and thumbnail collections
- Normalize frontend-facing preview metadata

Example manifest:

```json
{
  "type": "office_pdf",
  "status": "ready",
  "primary_asset": {
    "asset_type": "pdf",
    "url": "/api/v1/files/file_1/versions/v2/assets/main"
  },
  "thumbnails": [
    { "page": 1, "url": "/api/v1/files/file_1/versions/v2/assets/thumb-1" }
  ]
}
```

### 3. Derived Preview Assets

Add a model such as:

- `backend/app/models/file_preview_asset.py`

Suggested fields:

- `id`
- `file_id`
- `version_id`
- `asset_type`
- `storage_path`
- `page_number`
- `width`
- `height`
- `size_bytes`
- `sort_order`
- `status`
- `error_message`
- `created_at`

Supported `asset_type` values:

- `pdf`
- `thumbnail`
- `page_image`
- `cover_frame`
- `poster`
- `text_extract`
- `archive_index`

### 4. File Analysis Records

Add a model such as:

- `backend/app/models/file_analysis_record.py`

Suggested fields:

- `id`
- `file_id`
- `version_id`
- `analysis_type`
- `payload_json`
- `status`
- `error_message`
- `created_at`
- `updated_at`

Supported `analysis_type` values:

- `media_metadata`
- `archive_manifest`
- `office_summary`
- `text_summary`
- `diff_baseline`

### 5. Version-Aware Preview State

Preview and analysis must be version-specific.

Each file version should independently track:

- `preview_status`
- `analysis_status`
- `preview_error`
- `analysis_error`
- `preview_refresh_token`
- `derived_asset_version`

This avoids mixing current-file metadata with per-version preview outputs.

## API Design

### File Detail Response Enhancement

Existing file detail APIs should return:

- `capabilities`
- `preview_manifest`
- `analysis_summary`

Example:

```json
{
  "id": "file_1",
  "filename": "demo.pptx",
  "file_category": "office",
  "capabilities": {
    "can_preview": true,
    "can_play": false,
    "can_diff_visual": true,
    "can_diff_structural": false,
    "can_download": true
  },
  "preview_manifest": {
    "type": "office_pdf",
    "status": "ready"
  },
  "analysis_summary": {
    "page_count": 18
  }
}
```

### Preview Status APIs

Add:

- `GET /api/v1/files/{file_id}/preview-status`
- `GET /api/v1/files/{file_id}/versions/{version_id}/preview-status`

Used for:

- upload completion polling
- admin preview generation visibility
- retry and failure messaging

### Analysis APIs

Add:

- `GET /api/v1/files/{file_id}/analysis`
- `GET /api/v1/files/{file_id}/versions/{version_id}/analysis`

Examples:

- archive tree and counts
- video metadata and poster info
- office page count and preview summary

### Diff API Enhancement

Use a unified compare response:

- `GET /api/v1/diffs/files/{file_id}?left_version=1&right_version=2`

Response includes:

- `diff_type`
- `summary`
- `payload`

`diff_type` values:

- `content`
- `media`
- `structure`

### Announcement CRUD Enhancement

Announcement admin APIs should accept:

- `title`
- `summary`
- `content_blocks`
- `attachment_file_ids`
- `popup_config`
- `display_mode`
- `push_method`
- `priority`
- `is_active`

Public active announcement API should return render-ready block content.

## Frontend Architecture

### Shared File Viewer Layer

Add shared components such as:

- `frontend/src/components/file-viewer/FileViewer.vue`
- `ImageViewer.vue`
- `VideoViewer.vue`
- `PdfViewer.vue`
- `OfficePreviewViewer.vue`
- `ArchiveStructureViewer.vue`
- `FallbackFileCard.vue`

Responsibilities:

- `FileViewer` reads `preview_manifest`
- child viewers render per preview type
- all user/admin surfaces reuse the same viewer entry point

### Upload Flow Enhancements

Enhance `frontend/src/views/admin/FileUpload.vue` to show:

- support badges before upload
- preview/play/diff capability hints
- upload-complete preview generation state
- failure messages and retry actions

This page should no longer embed ad hoc extension logic beyond calling shared utilities and API data.

### File Detail / Version Page Enhancements

File-related detail pages should show:

1. Primary preview area
2. File metadata
3. Analysis/structure section
4. Version switcher and compare entry

Type-specific behavior:

- MP4: player + metadata
- PPT/PPTX: PDF preview + thumbnail navigation
- ZIP/7Z: archive tree + structure summary
- unsupported types: fallback card

### Announcement Editor Components

Add:

- `frontend/src/components/announcement/AnnouncementBlockEditor.vue`
- `AnnouncementPreviewDialog.vue`

Supported block types:

- paragraph
- image
- video
- code
- button
- file_reference

Admin flow should support left-side editing and right-side preview.

### Announcement Renderer Components

Add:

- `frontend/src/components/announcement/AnnouncementRenderer.vue`
- `AnnouncementPopup.vue`

Capabilities:

- image display
- inline or modal video playback
- code block rendering with syntax class hooks
- file reference cards backed by shared file viewer

## Announcement Data Model

Extend announcement storage from simple `title + content` into structured content.

### Base Fields

- `title`
- `summary`
- `display_mode`
- `priority`
- `push_method`
- `target_user_id`
- `start_time`
- `end_time`
- `is_active`

### Content Fields

- `content_blocks_json`
- `attachment_file_ids_json`
- `popup_config_json`

### Example `content_blocks_json`

```json
[
  { "type": "paragraph", "text": "系统升级通知" },
  { "type": "image", "file_id": "img_1", "caption": "升级示意图" },
  { "type": "video", "file_id": "vid_1", "autoplay": false },
  { "type": "code", "language": "bash", "content": "docker compose up -d" },
  { "type": "button", "label": "查看详情", "url": "/notice/123" }
]
```

### Example `popup_config_json`

```json
{
  "width": 720,
  "theme": "default",
  "show_once": true,
  "autoplay_video": false,
  "dismissible": true,
  "max_height": 760,
  "layout_mode": "stacked"
}
```

This preserves safety and consistency without allowing arbitrary embedded HTML or script execution.

## Comparison Design

### 1. Content Diff

Used for:

- `txt`
- `md`
- `doc`
- `docx`
- `pdf`
- `ppt`
- `pptx`

Primary output:

- document/page summary
- text/page deltas where supported

### 2. Media Diff

Used for:

- video files
- image files

Primary output:

- side-by-side preview
- duration/resolution/size changes
- poster or first-frame comparison for video

### 3. Structural Diff

Used for:

- `zip`
- `7z`
- `rar`

Primary output:

- added paths
- removed paths
- changed same-path entries
- total file count and total size changes

Frontend should keep a shared diff shell and switch renderer based on `diff_type`.

## Key Type-Specific Behavior

### MP4

- direct playback in frontend and admin
- extract duration, resolution, codec, poster frame
- compare duration, resolution, size, and poster frame between versions

### PPT / PPTX

- convert to PDF
- generate page thumbnails
- preview via PDF and thumbnail navigation
- compare page counts and representative page-level differences

### ZIP / 7Z

- analyze archive tree
- show hierarchical structure and counts
- compare by added/removed/changed paths
- do not expose arbitrary full extraction browsing in Phase 1

## Security and Risk Controls

### Archive Safety

- scan structure only
- limit max entry count
- limit max nesting depth
- limit manifest payload size
- reject malformed or hostile archive structures gracefully

### Video Safety

- whitelist supported media formats
- metadata or poster extraction failure must not block download
- playback can continue without poster asset

### Announcement Safety

Because announcement content uses safe blocks:

- no arbitrary HTML input
- no inline script execution
- code block content is displayed as text only
- image/video should prefer platform file references
- button URLs should use protocol and destination validation

## Error Handling

Use consistent failure categories:

- `conversion_failed`
- `analysis_failed`
- `not_supported`

Frontend should consistently display:

- user-friendly reason
- file metadata
- fallback action
- preview retry action in admin context

## Rollout Plan

### Phase 1

- file capability registry
- preview manifest generation
- shared `FileViewer`
- MP4 direct playback
- PPT/PPTX PDF + thumbnail preview
- ZIP/7Z structure preview
- announcement block content for text/image/video/code

### Phase 2

- diff type extension
- video comparison
- archive structure diff
- PPT page-level diff summary
- announcement file-reference block

### Phase 3

- more file formats
- more robust preview task scheduling/management
- announcement themes and templates

## Testing Strategy

### Backend Tests

- file capability recognition
- preview manifest generation
- MP4 metadata parsing
- PPT/PPTX preview outputs
- ZIP/7Z archive manifest generation
- diff response per `diff_type`
- announcement block payload validation

### Frontend Tests

- `FileViewer` manifest-based component switching
- MP4 player rendering
- archive tree rendering
- office/PDF fallback logic
- announcement block editor add/remove/update flows
- popup rendering for image/video/code blocks
- diff renderer switching by `diff_type`

### Integration Tests

Core end-to-end flows:

1. upload MP4 -> generate metadata/poster -> play in admin/frontend
2. upload PPTX -> convert preview -> render PDF/thumbs in admin/frontend
3. upload ZIP/7Z -> build structure manifest -> render structure preview and compare

### Regression Priorities

Must not break:

- existing `doc`/`docx`/`xls`/`xlsx`/`pdf` preview behavior
- existing version upload flow
- existing download routes
- existing announcement CRUD basics
- existing diff page foundations

## Impacted Existing Areas

Based on current project structure, the main impacted areas are expected to include:

- `backend/app/routers/files.py`
- `backend/app/routers/announcements.py`
- related file/version models and schemas
- `frontend/src/views/admin/FileUpload.vue`
- existing diff views
- `frontend/src/views/admin/AnnouncementManager.vue`
- shared frontend preview utilities and new viewer components

## Recommended Boundaries

Phase 1 should focus on building the shared capability foundation and the highest-value file types rather than trying to make every format deeply interactive at once.

The most important architectural rule is:

**business pages should not make independent per-extension rendering decisions; they should consume backend-declared capabilities and manifests.**

## Implementation Notes

- Keep `content` text fallback for older announcement rows whose `content_blocks_json` is empty.
- Preserve existing docx/xlsx/pdf diff payload shapes under their current engine paths while adding media/archive branches.
- Keep `DiffResponse.diff_data` as a JSON string contract so existing frontend parsing continues to work.
