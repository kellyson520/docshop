# Mobile UI Shell And Compatible Video Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compatible derived video preview asset that fixes mobile playback issues, wire it through manifest and preview routes, and leave the mobile UI shell follow-up with a clear next sequencing point.

**Architecture:** Backend video preview generation will persist `poster + preview_video + video`, preview manifests will prioritize `preview_video`, and both private/share `/preview` routes will stream the compatible asset first so old and new frontend paths benefit. Frontend only needs to treat `preview_video` as a playable video asset while preserving current HTML/image/PDF behavior.

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3, Element Plus, Pytest, Vitest, ffmpeg/ffprobe-backed media helpers.

---

## Progress Update (2026-06-28)

### Already Completed

- 分享页 HTML 预览已切换为原生独立页跳转。
- 非视频沉浸式预览已去掉重复标题，并统一缩放比例。
- 后台资源区 folders/files 已进入统一资源区模型，预览比例已做一轮收口。
- 视频预览已有 `poster` 与 `video` derived asset，但还没有兼容播放版本。

### Completed In This Pass

- **Task 1-4：** 兼容视频预览 derived-asset 链路已完成：
  - worker 持久化 `poster + preview_video + video`
  - manifest 优先输出 `preview_video`
  - private/share `/preview` 优先回放兼容 mp4
  - 前端视频预览可直接消费 `preview_video`

### Next Follow-Up

- 继续推进 share/admin/preview 的独立 mobile UI shell 收口

### Verification Snapshot (2026-06-28)

- Backend targeted suite passed:
  - `python -m pytest backend/tests/test_media_metadata_service.py backend/tests/test_preview_queue.py backend/tests/test_preview_manifest_service.py backend/tests/test_files_rich_preview.py backend/tests/test_share_tokens_api.py -k "preview_video or compatible or video" -v`
- Frontend targeted suite passed:
  - `npm --prefix frontend test -- --run src/components/file-viewer/__tests__/FileViewer.spec.js src/views/share/__tests__/SharePreview.spec.js`
- Frontend build passed:
  - `npm --prefix frontend run build`

### Task Status Snapshot

- Task 1 - Completed and verified
- Task 2 - Completed and verified
- Task 3 - Completed and verified
- Task 4 - Completed and verified

---

## File Structure

### Backend files

- Modify: `backend/app/services/media_metadata_service.py` — add compatible video transcode helper
- Modify: `backend/app/services/preview_queue.py` — persist `preview_video`
- Modify: `backend/app/services/preview_manifest_service.py` — prioritize `preview_video`
- Modify: `backend/app/routers/files.py` — private `/preview` prefers compatible asset
- Modify: `backend/app/routers/share.py` — shared `/preview` prefers compatible asset
- Test: `backend/tests/test_media_metadata_service.py`
- Test: `backend/tests/test_preview_queue.py`
- Test: `backend/tests/test_preview_manifest_service.py`
- Test: `backend/tests/test_files_rich_preview.py`
- Test: `backend/tests/test_share_tokens_api.py`

### Frontend files

- Modify: `frontend/src/components/file-viewer/VideoViewer.vue`
- Modify: `frontend/src/components/file-viewer/__tests__/FileViewer.spec.js`
- Modify: `frontend/src/views/share/SharePreview.vue`
- Modify: `frontend/src/views/share/__tests__/SharePreview.spec.js`

## Task 1: Lock the compatible preview-video contract with failing tests

**Files:**
- Modify: `backend/tests/test_media_metadata_service.py`
- Modify: `backend/tests/test_preview_queue.py`
- Modify: `backend/tests/test_preview_manifest_service.py`
- Modify: `backend/tests/test_files_rich_preview.py`
- Modify: `backend/tests/test_share_tokens_api.py`
- Modify: `frontend/src/components/file-viewer/__tests__/FileViewer.spec.js`
- Modify: `frontend/src/views/share/__tests__/SharePreview.spec.js`

- [ ] **Step 1: Add the backend helper test for compatible preview video generation**

```python
def test_generate_compatible_video_preview_uses_ffmpeg_when_available(monkeypatch, tmp_path):
    import app.services.media_metadata_service as media_metadata_service

    source = tmp_path / "demo.mov"
    source.write_bytes(b"video")
    output = tmp_path / "preview-video.mp4"
    calls = []

    def fake_run(args, capture_output, timeout, check):
        calls.append(args)
        output.write_bytes(b"preview-video")
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(media_metadata_service, "_find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(media_metadata_service.subprocess, "run", fake_run)

    result = media_metadata_service.generate_compatible_video_preview(str(source), str(output))

    assert result == {"path": str(output), "generated": True}
    assert calls[0][0] == "ffmpeg"
    assert calls[0][-1] == str(output)
```

- [ ] **Step 2: Add the queue test for `poster + preview_video + video` persistence**

```python
def test_video_enqueue_and_worker_persist_compatible_preview_assets(monkeypatch, tmp_path, db):
    from app.services import document_store, preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    preview_queue.reset_queue_for_tests()

    source = tmp_path / "demo.mp4"
    source.write_bytes(b"fake mp4 bytes")
    poster = tmp_path / "poster.jpg"
    poster.write_bytes(b"poster")
    compatible = tmp_path / "preview-video.mp4"
    compatible.write_bytes(b"compatible")
    doc_file, version = _create_versioned_file(
        db,
        source,
        filename="demo.mp4",
        file_type="mp4",
        file_category="video",
        mime_type="video/mp4",
    )

    monkeypatch.setattr(
        preview_queue,
        "extract_video_poster_frame",
        lambda _source_path, _output_path: {"path": str(poster), "generated": True},
        raising=False,
    )
    monkeypatch.setattr(
        preview_queue,
        "generate_compatible_video_preview",
        lambda _source_path, _output_path: {"path": str(compatible), "generated": True},
        raising=False,
    )
    monkeypatch.setattr(
        preview_queue,
        "extract_video_metadata",
        lambda _source_path: {"dimensions": {"width": 1920, "height": 1080}, "codec": "h264"},
        raising=False,
    )

    preview_queue.enqueue_preview_generation(
        doc_file.id,
        str(source),
        "mp4",
        autostart=False,
        project_id=doc_file.project_id,
        file_size=source.stat().st_size,
        updated_at=doc_file.updated_at,
    )
    preview_queue._worker_loop()

    db.expire_all()
    assets = db.query(FilePreviewAsset).filter(FilePreviewAsset.version_id == version.id).all()

    assert [asset.asset_type for asset in assets] == ["poster", "preview_video", "video"]
    assert assets[1].storage_path == str(compatible)
```

- [ ] **Step 3: Add the manifest tests for preview-video priority**

```python
def test_build_preview_manifest_payload_for_video_prefers_preview_video_asset():
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

    assert manifest["primary_asset"]["asset_type"] == "preview_video"
    assert manifest["primary_asset"]["url"] == "/api/v1/files/f1/preview-assets/asset-preview"
    assert manifest["original_asset"]["asset_type"] == "video"
```

- [ ] **Step 4: Add route tests proving `/preview` prefers the compatible asset**

```python
def test_preview_file_prefers_compatible_preview_video_asset(...):
    response = client.get(f"/api/v1/files/{doc_file.id}/preview", headers=auth_headers)

    assert response.status_code == 200
    assert response.content == b"compatible-video"
    assert response.headers["content-type"].startswith("video/mp4")
```

```python
def test_shared_preview_prefers_compatible_preview_video_asset(...):
    response = client.get(f"/api/v1/share/{share_token.token}/files/{doc.id}/preview")

    assert response.status_code == 200
    assert response.content == b"compatible-video"
    assert response.headers["content-type"].startswith("video/mp4")
```

- [ ] **Step 5: Add frontend tests accepting `preview_video`**

```javascript
it('renders the video viewer when the primary asset is preview_video', () => {
  render(FileViewer, {
    props: {
      file: { filename: 'demo.mp4' },
      manifest: {
        type: 'video_native',
        status: 'ready',
        primary_asset: { asset_type: 'preview_video', url: '/api/v1/files/file-1/preview-assets/asset-preview' },
        poster_asset: { asset_type: 'poster', url: '/api/v1/files/file-1/preview-assets/asset-poster' },
      },
      analysisSummary: { codec: 'h264' },
    },
  })

  expect(screen.getByTestId('video-player')).toHaveAttribute(
    'src',
    '/api/v1/files/file-1/preview-assets/asset-preview',
  )
})
```

```javascript
it('renders share video previews when the backend manifest primary asset is preview_video', async () => {
  mockedShareFileData.preview_manifest.primary_asset = {
    asset_type: 'preview_video',
    url: '/api/v1/share/share-token/files/file-1/preview-assets/asset-preview',
  }

  const wrapper = mount(SharePreview, { global: globalConfig })
  await flushPromises()
  await flushPromises()

  expect(wrapper.find('[data-testid="video-player"]').attributes('src')).toBe(
    '/api/v1/share/share-token/files/file-1/preview-assets/asset-preview',
  )
})
```

- [ ] **Step 6: Run the targeted tests to verify they fail**

Run:

```powershell
python -m pytest backend/tests/test_media_metadata_service.py backend/tests/test_preview_queue.py backend/tests/test_preview_manifest_service.py backend/tests/test_files_rich_preview.py backend/tests/test_share_tokens_api.py -k "preview_video or compatible or video" -v
npm --prefix frontend test -- --run src/components/file-viewer/__tests__/FileViewer.spec.js src/views/share/__tests__/SharePreview.spec.js
```

Expected: FAIL because no `generate_compatible_video_preview` helper exists, video jobs only persist `poster + video`, manifests do not recognize `preview_video`, `/preview` still streams the original file, and the frontend only accepts `asset_type === "video"`.

## Task 2: Implement compatible preview-video generation and persistence

**Files:**
- Modify: `backend/app/services/media_metadata_service.py`
- Modify: `backend/app/services/preview_queue.py`
- Test: `backend/tests/test_media_metadata_service.py`
- Test: `backend/tests/test_preview_queue.py`

- [ ] **Step 1: Add the ffmpeg-based compatible video helper**

```python
def generate_compatible_video_preview(file_path: str, output_path: str) -> dict:
    ffmpeg = _find_ffmpeg()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if not ffmpeg:
        return {"path": str(output), "generated": False}

    try:
        completed = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(file_path),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(output),
            ],
            capture_output=True,
            timeout=120,
            check=False,
        )
    except Exception:
        return {"path": str(output), "generated": False}

    generated = completed.returncode == 0 and output.exists() and output.stat().st_size > 0
    return {"path": str(output), "generated": generated}
```

- [ ] **Step 2: Persist `preview_video` between `poster` and original `video` assets**

```python
compatible_video_path = os.path.join(document_store.dir_original(job.file_id), "preview-video.mp4")
compatible_video = generate_compatible_video_preview(preview_path, compatible_video_path)
if compatible_video.get("generated") and compatible_video.get("path") and os.path.exists(compatible_video["path"]):
    asset_specs.append(
        {
            "asset_type": "preview_video",
            "storage_path": compatible_video["path"],
            "width": dimensions.get("width"),
            "height": dimensions.get("height"),
            "sort_order": len(asset_specs),
        }
    )

asset_specs.append(
    {
        "asset_type": "video",
        "storage_path": preview_path,
        "width": dimensions.get("width"),
        "height": dimensions.get("height"),
        "sort_order": len(asset_specs),
    }
)
```

- [ ] **Step 3: Re-run the backend helper and queue tests**

Run:

```powershell
python -m pytest backend/tests/test_media_metadata_service.py backend/tests/test_preview_queue.py -k "preview_video or compatible or video" -v
```

Expected: PASS with `preview_video` generated when ffmpeg is available and persisted ahead of the original video asset.

## Task 3: Prioritize compatible preview video in manifest, preview routes, and frontend consumers

**Files:**
- Modify: `backend/app/services/preview_manifest_service.py`
- Modify: `backend/app/routers/files.py`
- Modify: `backend/app/routers/share.py`
- Modify: `frontend/src/components/file-viewer/VideoViewer.vue`
- Modify: `frontend/src/views/share/SharePreview.vue`
- Test: `backend/tests/test_preview_manifest_service.py`
- Test: `backend/tests/test_files_rich_preview.py`
- Test: `backend/tests/test_share_tokens_api.py`
- Test: `frontend/src/components/file-viewer/__tests__/FileViewer.spec.js`
- Test: `frontend/src/views/share/__tests__/SharePreview.spec.js`

- [ ] **Step 1: Map `preview_video` to preview-asset URLs and make it the manifest primary asset**

```python
elif asset_type in {"poster", "preview_video"} and asset_id:
    url = _preview_asset_url(file_id, asset_id, share_token)
```

```python
preview_video_asset = next((asset for asset in preview_assets if asset["asset_type"] == "preview_video"), None)
video_asset = next((asset for asset in preview_assets if asset["asset_type"] == "video"), None)
poster_asset = next((asset for asset in preview_assets if asset["asset_type"] == "poster"), None)
primary_asset = preview_video_asset or video_asset or poster_asset
```

```python
return {
    "type": "video_native",
    "status": "ready" if primary_asset else preview_status,
    "primary_asset": primary_asset,
    "poster_asset": poster_asset,
    "original_asset": video_asset,
    "thumbnails": [],
    "summary": analysis_summary or {},
}
```

- [ ] **Step 2: Make private/share `/preview` video responses prefer `preview_video`**

```python
def _find_version_preview_asset(db: Session, version_id: str, asset_type: str) -> Optional[FilePreviewAsset]:
    return (
        db.query(FilePreviewAsset)
        .filter(FilePreviewAsset.version_id == version_id, FilePreviewAsset.asset_type == asset_type)
        .order_by(FilePreviewAsset.sort_order.asc(), FilePreviewAsset.created_at.asc())
        .first()
    )
```

```python
if _previewable_category_for_file(doc_file) == "video":
    compatible_asset = _find_version_preview_asset(db, fv.id, "preview_video")
    if compatible_asset:
        return _stream_preview_asset(compatible_asset)
    return _stream_native_preview_file(doc_file, fv.storage_path)
```

在 `share.py` 中做同样处理。

- [ ] **Step 3: Accept `preview_video` in frontend video consumers**

```javascript
const videoUrl = computed(() => {
  const asset = props.manifest?.primary_asset || {}
  return ['video', 'preview_video'].includes(asset.asset_type) ? asset.url || '' : ''
})
```

```javascript
case 'video_native':
  return ['video', 'preview_video'].includes(assetType) && typeof assetUrl === 'string' && assetUrl.length > 0
```

- [ ] **Step 4: Re-run the targeted backend/frontend tests**

Run:

```powershell
python -m pytest backend/tests/test_preview_manifest_service.py backend/tests/test_files_rich_preview.py backend/tests/test_share_tokens_api.py -k "preview_video or compatible or video" -v
npm --prefix frontend test -- --run src/components/file-viewer/__tests__/FileViewer.spec.js src/views/share/__tests__/SharePreview.spec.js
```

Expected: PASS with manifests preferring `preview_video`, `/preview` routes streaming the compatible asset first, and frontend video views rendering either asset type.

## Task 4: Focused verification sweep and progress sync

**Files:**
- Modify: `docs/superpowers/specs/2026-06-28-mobile-ui-shell-and-compatible-video-preview-design.md` only if implementation reveals a contract correction

- [ ] **Step 1: Run the combined verification sweep**

```powershell
python -m pytest backend/tests/test_media_metadata_service.py backend/tests/test_preview_queue.py backend/tests/test_preview_manifest_service.py backend/tests/test_files_rich_preview.py backend/tests/test_share_tokens_api.py -k "preview_video or compatible or video" -v
npm --prefix frontend test -- --run src/components/file-viewer/__tests__/FileViewer.spec.js src/views/share/__tests__/SharePreview.spec.js
npm --prefix frontend run build
```

Expected: PASS.

- [ ] **Step 2: Sanity-check coverage against the spec**

```text
- video worker persists preview_video when ffmpeg is available
- manifest primary_asset prefers preview_video
- poster_asset remains available
- original video preview still works as fallback
- private /preview prefers preview_video
- shared /preview prefers preview_video
- frontend accepts preview_video without regressing old video manifests
```

- [ ] **Step 3: Sync the next follow-up entry**

Add this note to the progress summary if no further contract changes are needed:

```markdown
### Next Follow-Up

- Continue the mobile UI shell pass on share/admin/resource explorer using the existing unified resource model and FileListCards foundation.
```
