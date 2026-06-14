# Preview Generation Management Design

Date: 2026-06-14

## Goal

Add a low-resource, admin-visible preview generation management system for Word/PDF previews. Uploads should enqueue asynchronous preview generation by default, administrators should see generation status/progress/storage usage, and preview caches should be easy to regenerate or clean without blocking user preview requests.

## Current Context

The project already has the core conversion pipeline:

- Upload flow in `backend/app/routers/files.py` calls `trigger_preconversion(file_id, storage_path, file_type)` for `docx`, `doc`, and `pdf`.
- `backend/app/services/conversion_service.py` converts Word/PDF to persisted PDF and JPEG page images.
- `backend/app/services/document_store.py` stores original files, PDFs, page images, and `meta.json` under `data/documents/{file_id}/`.
- The admin project detail page already exposes basic rebuild preview buttons using `/api/v1/admin/files/preconvert`.

Missing pieces:

- Persistent task state and progress.
- Admin preview status summary.
- Per-file preview storage usage.
- Failure reason display.
- Cache cleanup controls.
- Low-concurrency queue to prevent upload-time preview work from consuming too much CPU/RAM.

## Chosen Approach

Use a lightweight in-process preview queue plus file-level `meta.json` status.

This avoids adding a database table or external worker dependency. It fits the current architecture because preview artifacts already live in `document_store`, and the existing conversion path already writes conversion metadata there.

## Preview Job State Model

Each previewable file will expose a normalized preview status:

- `missing`: no valid PDF/images exist.
- `queued`: job accepted and waiting.
- `pdf_generating`: Word/PDF normalization is running.
- `pdf_ready`: PDF exists; images are not complete yet.
- `images_generating`: JPEG page generation is running.
- `ready`: PDF and required page images are available.
- `failed`: generation failed; `error` explains why.
- `interrupted`: previous process stopped while the job was incomplete.
- `unsupported`: file type cannot have managed preview.

Progress uses integer percent:

- `queued`: 0
- `pdf_generating`: 10-45
- `pdf_ready`: 50
- `images_generating`: 50-99 based on rendered page count
- `ready`: 100
- `failed` / `interrupted`: last known progress, capped below 100 unless artifacts are valid

`meta.json` will store a `preview` object:

```json
{
  "preview": {
    "status": "images_generating",
    "progress": 72,
    "stage": "正在生成页面图片",
    "queued_at": "2026-06-14T10:00:00Z",
    "started_at": "2026-06-14T10:00:03Z",
    "updated_at": "2026-06-14T10:01:18Z",
    "finished_at": null,
    "error": null,
    "source_hash": "...",
    "pdf_hash": "...",
    "page_count": 80,
    "rendered_pages": 42,
    "storage_bytes": 12582912
  }
}
```

Existing keys such as `pdf_source_hash`, `pdf_generated_at`, `pdf_image_hash`, `page_count`, `image_dpi`, `image_quality`, and `images_generated_at` remain for cache validation.

## Backend Design

### Preview Queue Service

Create a focused service, `backend/app/services/preview_queue.py`, responsible for:

- Enqueueing preview jobs.
- Deduplicating running/queued jobs per `file_id`.
- Running jobs with low concurrency.
- Updating `meta.json` progress.
- Returning snapshots for admin APIs.

Default resource settings:

- `PREVIEW_QUEUE_MAX_ACTIVE=1` file at a time.
- `PREVIEW_IMAGE_MAX_WORKERS=2` or `min(os.cpu_count(), 4)` with an environment override.
- Existing `adaptive_dpi(page_count)` remains in use, so larger files generate lower-DPI images.

Queue behavior:

- Upload automatically calls `enqueue_preview_generation(...)` for previewable files.
- Admin rebuild calls enqueue with `force=True`, which clears stale preview artifacts first.
- If a job is already queued or running and `force=False`, return existing status rather than enqueueing duplicate work.
- If process starts and sees `meta.preview.status` in a running state with no in-memory job, normalize it to `interrupted` on the next status scan.

### Progress Updates

PDF generation and image generation update the same `preview` meta object.

For page rendering progress, `document_store.generate_images(...)` should accept an optional callback:

```python
progress_callback(rendered_pages: int, total_pages: int) -> None
```

The callback updates `meta.preview.rendered_pages` and `meta.preview.progress`.

### Preview Storage Usage

Add document store helpers to calculate preview cache size:

- PDF size under `pdf/document.pdf`.
- Image sizes under `images/`, including hash subdirectories if present.
- Optional original size is not counted as preview cache; the admin panel focuses on generated preview artifacts.

### Cache Cleanup

Add helpers to remove generated preview artifacts without deleting original uploads:

- `clear_preview_cache(file_id)` removes `pdf/` and `images/` contents and resets preview status to `missing`.
- `clear_failed_preview_caches()` scans files with failed/interrupted statuses and clears generated artifacts if requested.

Cleanup must not delete `original/` or file version storage paths.

### Admin APIs

Add or extend admin endpoints under `backend/app/routers/files.py`:

1. `GET /api/v1/admin/files/previews`
   - Returns per-file preview status and global summary.
   - Optional query: `project_id`, `status`, `file_type`.

2. `POST /api/v1/admin/files/preconvert`
   - Existing endpoint remains but uses the new queue service.
   - Body: `{ "file_ids": [], "force": false }`.
   - Empty `file_ids` means enqueue all previewable files missing/failed/interrupted preview.

3. `DELETE /api/v1/admin/files/{file_id}/preview-cache`
   - Clears one file's generated preview artifacts.

4. `POST /api/v1/admin/files/preview-cache/cleanup`
   - Body: `{ "statuses": ["failed", "interrupted"], "older_than_days": null }`.
   - Clears matching preview artifacts.

All endpoints require admin role.

## Frontend Design

Use the existing `frontend/src/views/admin/ProjectDetail.vue` as the first integration point because it already lists files and has preview/rebuild controls.

Add a preview generation management section above or near the file table:

- Summary cards:
  - Ready previews.
  - Running/queued jobs.
  - Failed/interrupted jobs.
  - Generated preview storage size.
- Control buttons:
  - Generate missing previews.
  - Rebuild selected/all previews.
  - Clean failed previews.
  - Refresh status.

Add a `Preview Status` column to the file table:

- Status tag: missing, queued, generating, ready, failed.
- Progress bar for queued/running states.
- Storage size for ready previews.
- Failure reason tooltip for failed previews.

Polling:

- Poll `GET /admin/files/previews` every 2 seconds only while any file is queued/running.
- Stop polling when all jobs are terminal.
- Refresh immediately after enqueue/cleanup actions.

Visual direction:

- Use a compact operations-dashboard style.
- Avoid heavy animations; use subtle status pulses only for active jobs.
- Keep dense information readable for administrators managing many files.

## Data Flow

1. User uploads a previewable file.
2. Upload route saves file and calls the preview queue service.
3. Queue marks file `queued` in `meta.json`.
4. Background worker starts:
   - stores original if needed;
   - creates or reuses PDF;
   - renders images with low worker count;
   - updates progress after each stage/page batch;
   - marks `ready` with storage size.
5. Admin page polls status endpoint while jobs are active.
6. Preview requests use cached PDF/images when available; otherwise they keep existing safe fallback behavior.

## Error Handling

- Conversion errors mark `preview.status = failed` with a short `error` message.
- Unsupported file types return `unsupported` and are excluded from bulk generation.
- Interrupted tasks are detected when `meta.json` says queued/running but no in-memory job exists.
- Cleanup errors return HTTP 500 with file id and reason, without deleting originals.
- A failed file can be requeued with `force=true`.

## Resource Strategy

- Do not generate previews synchronously from preview requests.
- Keep default active file jobs to 1.
- Keep per-file image rendering workers low.
- Use existing adaptive DPI for large documents.
- Prefer URL-based page loading for large previews instead of embedding base64 images.
- Store progress in small JSON updates; no database migration is required.

## Testing Strategy

Backend tests:

- Enqueue creates/updates `meta.preview` as `queued`.
- Duplicate enqueue does not create duplicate jobs.
- Successful generation transitions to `ready` and records storage bytes.
- Failed generation records `failed` and error.
- Cleanup removes PDF/images but leaves original files intact.
- Admin status endpoint returns summary counts and per-file status.

Frontend tests:

- Preview summary renders counts and storage.
- Running jobs show progress bar.
- Failed jobs show failure reason.
- Polling starts for active jobs and stops for terminal states.
- Rebuild/cleanup actions call the expected APIs and refresh status.

Manual verification:

- Upload DOCX and confirm it queues automatically.
- Watch progress in admin UI.
- Open preview after ready and confirm images load quickly.
- Force rebuild one file.
- Clear one preview cache and confirm status returns to `missing`.

## Non-Goals

- No external task queue such as Celery/RQ.
- No new database table in the first implementation.
- No multi-server coordination.
- No full historical job audit log.
- No per-user preview scheduling policy.

These can be added later if deployment grows beyond one backend process.
