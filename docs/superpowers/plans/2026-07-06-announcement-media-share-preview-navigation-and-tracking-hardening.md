# Announcement Media, Share Preview Navigation, and Tracking Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **User constraint:** Do not commit, push, reset, clean, or otherwise mutate git history.

**Goal:** Implement announcement project/local media blocks plus safe iframe embeds, context-aware share back navigation, correct share preview version timestamps, and duplicate tracking ping de-noise without breaking interactive HTML preview.

**Architecture:** Add an announcement-asset domain with temp upload and promotion, normalize announcement blocks into an explicit `project_file | announcement_asset | embed` contract, carry share navigation context through explicit route query helpers, expose `current_version_entry` from the shared file payload, and treat duplicate same-page tracking pings as idempotent rather than noisy errors.

**Tech Stack:** FastAPI, SQLAlchemy, existing file/share routers, Vue 3 Composition API, Element Plus, pytest, Vitest.

---

## File Structure

### Backend create

- `backend/app/models/announcement_asset.py`
  - Stores temp/active announcement media assets that do not live in the normal project file library.
- `backend/app/services/announcement_asset_service.py`
  - Handles temp upload, promotion, embed sanitization, and asset URL metadata.
- `backend/tests/test_announcement_assets.py`
  - Covers temp upload, promotion, and temp access rules.

### Backend modify

- `backend/app/models/__init__.py`
  - Registers `AnnouncementAsset`.
- `backend/app/database.py`
  - Ensures the new table is created with the existing metadata bootstrap.
- `backend/app/routers/announcements.py`
  - Extends block schema, adds temp upload/content endpoints, promotes temp assets on save, and sanitizes embed blocks.
- `backend/app/routers/files.py`
  - Extends `_build_file_detail_payload()` to include `current_version_entry`.
- `backend/app/routers/share.py`
  - Carries richer version metadata through share payloads where needed.
- `backend/app/routers/tracking_ping.py`
  - De-noises duplicate same-page page-view pings.
- `backend/tests/test_announcements_rich_blocks.py`
  - Extends announcement CRUD tests to cover new block shapes.
- `backend/tests/test_share.py`
  - Verifies share file payload returns `current_version_entry`.
- `test/test_tracking_ping.py`
  - Verifies duplicate same-page page-view handling and preserved non-page-path rate limiting.

### Frontend create

- `frontend/src/api/announcementAssets.js`
  - Uploads temp announcement assets and resolves announcement-asset content URLs.
- `frontend/src/components/announcement/AnnouncementAssetPickerDialog.vue`
  - Project/file explorer style picker for announcement image/video blocks.
- `frontend/src/components/announcement/__tests__/AnnouncementAssetPickerDialog.spec.js`
  - Tests picker navigation and selection behavior.
- `frontend/src/utils/announcementBlocks.js`
  - Normalizes legacy/new block shapes and exposes renderer helpers.
- `frontend/src/utils/__tests__/announcementBlocks.spec.js`
  - Verifies block normalization and source-type compatibility.

### Frontend modify

- `frontend/src/views/admin/AnnouncementManager.vue`
  - Uses normalized blocks, launches picker/upload flows, and previews embed/media consistently.
- `frontend/src/components/announcement/AnnouncementBlockEditor.vue`
  - Adds source-mode controls, local upload, project picker, and embed block editing.
- `frontend/src/components/announcement/AnnouncementRenderer.vue`
  - Renders `project_file`, `announcement_asset`, and sanitized iframe embeds.
- `frontend/src/components/announcement/__tests__/AnnouncementBlockEditor.spec.js`
  - Covers source switching and upload/picker emissions.
- `frontend/src/components/announcement/__tests__/AnnouncementRenderer.spec.js`
  - Covers media/embed rendering behavior.
- `frontend/src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js`
  - Verifies manager payloads now include new block contract fields.
- `frontend/src/utils/shareRoute.js`
  - Gains query-aware builders plus share navigation context helpers.
- `frontend/src/utils/__tests__/shareRoute.spec.js`
  - Verifies `from`, `folder_scope`, and `folder_id` path generation.
- `frontend/src/views/share/ShareProject.vue`
  - Syncs folder view with query, forwards navigation context, and preserves three-state folder semantics.
- `frontend/src/views/share/ShareFile.vue`
  - Returns to project context correctly and forwards context into preview/diff routes.
- `frontend/src/views/share/SharePreview.vue`
  - Uses context-aware back navigation, renders the HTML side back rail, and shows current-version timestamp.
- `frontend/src/views/share/ShareDiff.vue`
  - Preserves context when returning to file detail.
- `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
  - Verifies project -> file/preview navigation forwards context.
- `frontend/src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
  - Verifies file detail preview links keep context.
- `frontend/src/views/share/__tests__/SharePreview.spec.js`
  - Verifies back targets, side back rail, and current-version timestamp rendering.
- `frontend/src/views/share/__tests__/ShareDiff.spec.js`
  - Verifies diff back navigation preserves file/project context.
- `frontend/src/utils/trackingClient.js`
  - Adds same-page cooldown / de-noise behavior.
- `frontend/src/utils/__tests__/trackingClient.spec.js`
  - Verifies cooldown behavior and retained cross-page sends.

### Docs modify

- `docs/superpowers/specs/2026-07-06-announcement-media-share-preview-navigation-and-tracking-hardening-design.md`
- `docs/superpowers/plans/2026-07-06-announcement-media-share-preview-navigation-and-tracking-hardening.md`

---

## Task 1: Backend announcement asset domain, block schema, and embed sanitization

**Files:**
- Create: `backend/app/models/announcement_asset.py`
- Create: `backend/app/services/announcement_asset_service.py`
- Create: `backend/tests/test_announcement_assets.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/routers/announcements.py`
- Modify: `backend/tests/test_announcements_rich_blocks.py`

- [ ] **Step 1: Write the failing backend tests for temp upload, promotion, and embed sanitization**

Add tests like:

```python
def test_upload_temp_announcement_asset_returns_preview_descriptor(client, auth_headers):
    response = client.post(
        '/api/v1/announcements/assets/temp',
        headers=auth_headers,
        files={'file': ('poster.png', b'png-data', 'image/png')},
    )

    assert response.status_code == 201
    payload = response.json()['data']
    assert payload['status'] == 'temp'
    assert payload['media_type'] == 'image'
    assert payload['asset_id']
    assert '/api/v1/announcements/assets/' in payload['preview_url']


def test_create_announcement_promotes_temp_assets_and_sanitizes_embed_blocks(client, auth_headers):
    upload = client.post(
        '/api/v1/announcements/assets/temp',
        headers=auth_headers,
        files={'file': ('clip.mp4', b'video-data', 'video/mp4')},
    )
    asset_id = upload.json()['data']['asset_id']

    response = client.post(
        '/api/v1/announcements',
        headers=auth_headers,
        json={
            'title': 'Notice',
            'content': 'Fallback text',
            'content_blocks': [
                {'type': 'image', 'source_type': 'announcement_asset', 'asset_id': asset_id, 'caption': 'Poster'},
                {
                    'type': 'embed',
                    'provider': 'iframe',
                    'embed_html': '<iframe src="https://player.bilibili.com/player.html?bvid=BV1" onclick="alert(1)"></iframe><script>alert(1)</script>',
                    'caption': 'Video',
                },
            ],
        },
    )

    assert response.status_code == 201
    blocks = response.json()['data']['content_blocks']
    assert blocks[0]['source_type'] == 'announcement_asset'
    assert blocks[0]['asset_id'] == asset_id
    assert '<script' not in blocks[1]['embed_html']
    assert 'onclick=' not in blocks[1]['embed_html']
```

Also extend `backend/tests/test_announcements_rich_blocks.py` with a compatibility test for legacy image/video blocks that only contain `file_id`.

- [ ] **Step 2: Run targeted backend tests to verify RED**

Run:

```powershell
python -m pytest backend/tests/test_announcement_assets.py backend/tests/test_announcements_rich_blocks.py -q
```

Expected before implementation: missing model/service/routes/schema failures.

- [ ] **Step 3: Implement the announcement asset model/service and router changes minimally**

Add the model and service signatures first:

```python
class AnnouncementAsset(Base):
    __tablename__ = 'announcement_assets'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    announcement_id = Column(String(36), nullable=True)
    status = Column(String(20), nullable=False, default='temp')
    media_type = Column(String(20), nullable=False)
    mime_type = Column(String(120), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    storage_path = Column(Text, nullable=False)
    created_by = Column(String(36), nullable=False)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
```

```python
def store_temp_announcement_asset(db: Session, upload_file, *, user_id: str) -> dict[str, Any]:
    ...


def promote_announcement_assets(db: Session, *, announcement_id: str, blocks: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
    ...


def sanitize_announcement_embed(raw_html: str) -> dict[str, str]:
    ...
```

Then extend `AnnouncementBlock` and the block sanitization pipeline:

```python
class AnnouncementBlock(BaseModel):
    type: str = Field(..., min_length=1, max_length=32)
    source_type: Optional[str] = None
    asset_id: Optional[str] = None
    file_id: Optional[str] = None
    embed_html: Optional[str] = None
    src: Optional[str] = None
    caption: Optional[str] = None
```

Add routes:

```python
@router.post('/assets/temp', status_code=status.HTTP_201_CREATED)
def upload_announcement_temp_asset(...):
    ...


@router.get('/assets/{asset_id}/content')
def get_announcement_asset_content(...):
    ...
```

Implementation rules:
- local uploads land under `TEMP_DIR/announcement-assets/...`
- create/update announcement promotes referenced temp asset ids before commit returns
- legacy `{type, file_id}` blocks normalize to `source_type='project_file'`
- embed blocks only keep sanitized iframe content from whitelisted providers

- [ ] **Step 4: Re-run targeted backend tests to verify GREEN**

Run:

```powershell
python -m pytest backend/tests/test_announcement_assets.py backend/tests/test_announcements_rich_blocks.py -q
```

Expected: pass.

---

## Task 2: Frontend announcement picker/upload/embed editor and renderer

**Files:**
- Create: `frontend/src/api/announcementAssets.js`
- Create: `frontend/src/components/announcement/AnnouncementAssetPickerDialog.vue`
- Create: `frontend/src/components/announcement/__tests__/AnnouncementAssetPickerDialog.spec.js`
- Create: `frontend/src/utils/announcementBlocks.js`
- Create: `frontend/src/utils/__tests__/announcementBlocks.spec.js`
- Modify: `frontend/src/views/admin/AnnouncementManager.vue`
- Modify: `frontend/src/components/announcement/AnnouncementBlockEditor.vue`
- Modify: `frontend/src/components/announcement/AnnouncementRenderer.vue`
- Modify: `frontend/src/components/announcement/__tests__/AnnouncementBlockEditor.spec.js`
- Modify: `frontend/src/components/announcement/__tests__/AnnouncementRenderer.spec.js`
- Modify: `frontend/src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js`

- [ ] **Step 1: Write the failing frontend tests for picker navigation, source switching, and embed rendering**

Add tests such as:

```js
it('emits a project_file block after selecting a project resource', async () => {
  const wrapper = mount(AnnouncementBlockEditor, { props: { modelValue: [{ type: 'image' }] } })
  await wrapper.vm.applyProjectSelection(0, { id: 'file-1', file_type: 'png' })
  expect(wrapper.emitted('update:modelValue').at(-1)[0][0]).toEqual(
    expect.objectContaining({ type: 'image', source_type: 'project_file', file_id: 'file-1' }),
  )
})

it('emits an announcement_asset block after local upload succeeds', async () => {
  uploadTempAnnouncementAsset.mockResolvedValue({ asset_id: 'asset-1', media_type: 'video', preview_url: '/api/v1/announcements/assets/asset-1/content' })
  ...
})

it('renders sanitized iframe embeds from embed blocks', async () => {
  const wrapper = mount(AnnouncementRenderer, {
    props: {
      blocks: [{ type: 'embed', provider: 'iframe', embed_html: '<iframe src="https://player.bilibili.com/player.html?bvid=BV1"></iframe>' }],
    },
  })
  expect(wrapper.find('iframe').attributes('src')).toContain('player.bilibili.com')
})
```

Also extend `AnnouncementManagerRichBlocks.spec.js` to assert saved payloads include `source_type`, `asset_id`, and `embed_html` where applicable.

- [ ] **Step 2: Run targeted frontend tests to verify RED**

Run:

```powershell
npm.cmd run test -- src/components/announcement/__tests__/AnnouncementAssetPickerDialog.spec.js src/utils/__tests__/announcementBlocks.spec.js src/components/announcement/__tests__/AnnouncementBlockEditor.spec.js src/components/announcement/__tests__/AnnouncementRenderer.spec.js src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js --run
```

Expected before implementation: missing component/helper/API and failing assertions on old `file_id`-only behavior.

- [ ] **Step 3: Implement the announcement editor, picker, upload, and renderer changes minimally**

Create a single normalization helper first:

```js
export function normalizeAnnouncementBlock(block = {}) {
  const type = String(block.type || 'paragraph')
  if (type === 'image' || type === 'video') {
    return {
      type,
      source_type: block.source_type || (block.file_id ? 'project_file' : 'announcement_asset'),
      file_id: block.file_id || '',
      asset_id: block.asset_id || '',
      caption: block.caption || '',
    }
  }
  if (type === 'embed') {
    return {
      type: 'embed',
      provider: 'iframe',
      src: block.src || '',
      embed_html: block.embed_html || '',
      caption: block.caption || '',
    }
  }
  return { ...block, type }
}
```

Add the asset API helpers:

```js
export function uploadTempAnnouncementAsset(file) {
  const form = new FormData()
  form.append('file', file)
  return post('/announcements/assets/temp', form)
}

export function buildAnnouncementAssetContentUrl(assetId) {
  return assetId ? `/api/v1/announcements/assets/${assetId}/content` : ''
}
```

Implementation requirements:
- `AnnouncementBlockEditor.vue` supports `paragraph / code / button / image / video / embed`
- media blocks show source switch: project picker or local upload
- picker dialog supports project -> folder -> file drill-down and emits selected file id
- local upload replaces temporary File objects with stable `asset_id`
- renderer resolves `project_file` and `announcement_asset` separately
- embed blocks render controlled iframe wrappers only

- [ ] **Step 4: Re-run targeted frontend tests to verify GREEN**

Run:

```powershell
npm.cmd run test -- src/components/announcement/__tests__/AnnouncementAssetPickerDialog.spec.js src/utils/__tests__/announcementBlocks.spec.js src/components/announcement/__tests__/AnnouncementBlockEditor.spec.js src/components/announcement/__tests__/AnnouncementRenderer.spec.js src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js --run
```

Expected: pass.

---

## Task 3: Share navigation context propagation and HTML side back rail

**Files:**
- Modify: `frontend/src/utils/shareRoute.js`
- Modify: `frontend/src/utils/__tests__/shareRoute.spec.js`
- Modify: `frontend/src/views/share/ShareProject.vue`
- Modify: `frontend/src/views/share/ShareFile.vue`
- Modify: `frontend/src/views/share/SharePreview.vue`
- Modify: `frontend/src/views/share/ShareDiff.vue`
- Modify: `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
- Modify: `frontend/src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
- Modify: `frontend/src/views/share/__tests__/SharePreview.spec.js`
- Modify: `frontend/src/views/share/__tests__/ShareDiff.spec.js`

- [ ] **Step 1: Write the failing navigation-context and HTML back-rail tests**

Add tests like:

```js
it('builds preview paths with explicit folder scope context', () => {
  expect(buildSharePreviewPath('share-token', 'file-1', {
    from: 'project',
    folder_scope: 'folder',
    folder_id: 'folder-a',
  })).toBe('/s/share-token/preview/file-1?from=project&folder_scope=folder&folder_id=folder-a')
})

it('returns from share preview to the file detail page when from=file', async () => {
  ...
  await wrapper.vm.goBack()
  expect(routerPush).toHaveBeenCalledWith('/s/share-token/files/file-1?from=project&folder_scope=folder&folder_id=folder-a')
})

it('renders a floating side back rail for immersive html previews', async () => {
  ...
  expect(wrapper.find('[data-testid="share-preview-side-back"]').exists()).toBe(true)
})
```

Also add a `ShareDiff.spec.js` regression that asserts the diff page keeps `folder_scope` / `folder_id` when navigating back to file detail.

- [ ] **Step 2: Run targeted share navigation tests to verify RED**

Run:

```powershell
npm.cmd run test -- src/utils/__tests__/shareRoute.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareDiff.spec.js --run
```

Expected before implementation: missing query-aware builders, missing side back rail, and wrong back destinations.

- [ ] **Step 3: Implement query-aware share helpers and view wiring minimally**

Start by making route builders query-aware:

```js
export function buildShareHomePath(token, query = {}) {
  const normalizedToken = normalizeSegment(token)
  return normalizedToken ? withQuery(`/s/${normalizedToken}`, query) : ''
}

export function buildSharePreviewPath(token, fileId, query = {}) {
  const basePath = buildShareHomePath(token)
  const normalizedFileId = normalizeSegment(fileId)
  return basePath && normalizedFileId ? withQuery(`${basePath.replace(/\?.*$/, '')}/preview/${normalizedFileId}`, query) : ''
}
```

Add explicit context helpers:

```js
export function buildShareContextQuery({ from = 'project', folderScope = 'root', folderId = '' } = {}) {
  return folderScope === 'folder'
    ? { from, folder_scope: 'folder', folder_id: folderId }
    : { from, folder_scope: folderScope }
}
```

Implementation requirements:
- `ShareProject.vue` restores folder state from route query and updates query when folders change
- preview/version/diff/file-detail links forward the context query
- `ShareFile.vue` returns to project view using forwarded context
- `SharePreview.vue` resolves `from=file` vs `from=project` and adds a floating side back control for immersive HTML previews
- `ShareDiff.vue` uses the same context-aware file-detail return path

- [ ] **Step 4: Re-run targeted share navigation tests to verify GREEN**

Run:

```powershell
npm.cmd run test -- src/utils/__tests__/shareRoute.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareDiff.spec.js --run
```

Expected: pass.

---

## Task 4: Share preview current-version metadata contract and timestamp rendering

**Files:**
- Modify: `backend/app/routers/files.py`
- Modify: `backend/app/routers/share.py`
- Modify: `backend/tests/test_share.py`
- Modify: `frontend/src/views/share/SharePreview.vue`
- Modify: `frontend/src/views/share/__tests__/SharePreview.spec.js`

- [ ] **Step 1: Write the failing backend/frontend tests for `current_version_entry` and v3 timestamp rendering**

Add tests like:

```python
def test_get_shared_file_returns_current_version_entry(client, share_token, shared_file_id):
    response = client.get(f'/api/v1/share/{share_token}/files/{shared_file_id}')
    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['current_version_entry']['version'] == payload['current_version']
    assert payload['current_version_entry']['created_at']
```

```js
it('renders the current version timestamp instead of file created_at in the preview shell', async () => {
  mockedShareFileData = {
    ...mockedShareFileData,
    created_at: '2026-06-16T10:27:00Z',
    current_version: 3,
    current_version_entry: {
      id: 'ver-3',
      version: 3,
      created_at: '2026-06-18T08:10:00Z',
      updated_at: '2026-06-18T08:10:00Z',
      file_size: 4096,
      changelog: 'Answer edition',
    },
  }
  ...
  expect(wrapper.text()).toContain('2026-06-18T08:10:00Z')
  expect(wrapper.text()).not.toContain('2026-06-16T10:27:00Z')
})
```

- [ ] **Step 2: Run targeted metadata tests to verify RED**

Run:

```powershell
python -m pytest backend/tests/test_share.py -q
npm.cmd run test -- src/views/share/__tests__/SharePreview.spec.js --run
```

Expected before implementation: backend lacks `current_version_entry`; frontend still renders `fileInfo.created_at`.

- [ ] **Step 3: Implement `current_version_entry` in the shared payload helper and consume it in SharePreview**

Add the payload field where the resolved version is already known:

```python
payload.update(
    {
        'current_version_entry': {
            'id': resolved_version.id,
            'version': resolved_version.version,
            'created_at': resolved_version.created_at,
            'updated_at': resolved_version.updated_at or resolved_version.created_at,
            'file_size': resolved_version.file_size,
            'changelog': resolved_version.changelog,
        } if resolved_version else None,
    }
)
```

Then update the preview timestamp computation:

```js
const currentPreviewTimestamp = computed(() => (
  fileInfo.value?.current_version_entry?.created_at
  || fileInfo.value?.updated_at
  || fileInfo.value?.created_at
  || ''
))
```

Implementation requirements:
- both desktop and mobile preview shells use `currentPreviewTimestamp`
- if share project list already constructs a latest-version summary, include `created_at` there too for consistency
- no extra versions API request is added to `SharePreview.vue`

- [ ] **Step 4: Re-run targeted metadata tests to verify GREEN**

Run:

```powershell
python -m pytest backend/tests/test_share.py -q
npm.cmd run test -- src/views/share/__tests__/SharePreview.spec.js --run
```

Expected: pass.

---

## Task 5: Tracking ping same-page cooldown and duplicate de-noise

**Files:**
- Modify: `frontend/src/utils/trackingClient.js`
- Modify: `frontend/src/utils/__tests__/trackingClient.spec.js`
- Modify: `backend/app/routers/tracking_ping.py`
- Modify: `test/test_tracking_ping.py`

- [ ] **Step 1: Write the failing frontend/backend tests for duplicate same-page de-noise**

Add tests like:

```js
it('suppresses duplicate same-page page-view beacons inside the cooldown window', async () => {
  const { initTracking, sendPageViewTracking } = await loadTrackingClient()
  const deps = makeDeps({ enable_tracking: true, enable_device_tracking: true, enable_location_tracking: false })

  await initTracking(deps)
  deps.beacons.length = 0

  const first = sendPageViewTracking(deps)
  const second = sendPageViewTracking(deps)

  expect(first).toBe(true)
  expect(second).toBe(false)
  expect(deps.beacons).toHaveLength(1)
})
```

```python
@pytest.mark.asyncio
async def test_receive_ping_returns_204_for_duplicate_same_page_view(monkeypatch):
    from app.routers import tracking_ping

    log = SimpleNamespace(raw_data=None)
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=log)
    monkeypatch.setattr(tracking_ping, 'SessionLocal', lambda: db)
    tracking_ping._rate_limit_cache.clear()

    first = await tracking_ping.receive_ping(FakeRequest({
        'session_id': 'session-pages',
        'device_id': 'visitor-pages',
        'page_path': '/s/demo',
    }))
    second = await tracking_ping.receive_ping(FakeRequest({
        'session_id': 'session-pages',
        'device_id': 'visitor-pages',
        'page_path': '/s/demo',
    }))

    assert first.status_code == 204
    assert second.status_code == 204
```

Keep the existing regression that repeated non-page-path pings still raise `429`.

- [ ] **Step 2: Run targeted tracking tests to verify RED**

Run:

```powershell
python -m pytest test/test_tracking_ping.py -q
npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js --run
```

Expected before implementation: duplicate same-page page view still sends twice and backend still returns `429`.

- [ ] **Step 3: Implement frontend cooldown and backend idempotent duplicate handling**

Add frontend cooldown state first:

```js
const PAGE_VIEW_COOLDOWN_MS = 10_000
const pageViewSentAt = new Map()

function shouldSkipPageView(pagePath, now = Date.now()) {
  const last = pageViewSentAt.get(pagePath) || 0
  if (now - last < PAGE_VIEW_COOLDOWN_MS) return true
  pageViewSentAt.set(pagePath, now)
  return false
}
```

Then branch backend duplicate handling by `page_path` presence:

```python
rate_key = _rate_limit_identity(str(identity), page_path)
allowed = _check_rate_limit(rate_key)
if not allowed and page_path:
    return Response(status_code=204)
if not allowed:
    raise HTTPException(status_code=429, detail='too many pings')
```

Implementation requirements:
- same-page duplicate page views inside 10 seconds no-op on the frontend
- backend returns `204` only for duplicate requests that include `page_path`
- existing non-page-path rate limit behavior stays intact
- keep cross-page page view sends working normally

- [ ] **Step 4: Re-run targeted tracking tests to verify GREEN**

Run:

```powershell
python -m pytest test/test_tracking_ping.py -q
npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js --run
```

Expected: pass.

---

## Task 6: Full verification and docs sync

**Files:**
- Modify: `docs/superpowers/specs/2026-07-06-announcement-media-share-preview-navigation-and-tracking-hardening-design.md`
- Modify: `docs/superpowers/plans/2026-07-06-announcement-media-share-preview-navigation-and-tracking-hardening.md`

- [ ] **Step 1: Run the backend verification suite**

```powershell
python -m pytest backend/tests/test_announcement_assets.py backend/tests/test_announcements_rich_blocks.py backend/tests/test_share.py test/test_tracking_ping.py -q
```

Expected: all pass.

- [ ] **Step 2: Run the frontend verification suite**

```powershell
npm.cmd run test -- src/components/announcement/__tests__/AnnouncementAssetPickerDialog.spec.js src/utils/__tests__/announcementBlocks.spec.js src/components/announcement/__tests__/AnnouncementBlockEditor.spec.js src/components/announcement/__tests__/AnnouncementRenderer.spec.js src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js src/utils/__tests__/shareRoute.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareDiff.spec.js src/utils/__tests__/trackingClient.spec.js --run
```

Expected: all pass.

- [ ] **Step 3: Run the frontend build**

```powershell
npm.cmd run build
```

Expected: Vite build succeeds.

- [ ] **Step 4: Update the spec/plan files with exact verification outputs and any remaining optional follow-ups**

Record:
- backend pytest result
- frontend vitest result
- build result
- whether share preview now returns to folder/file context correctly
- whether SharePreview now shows the current version timestamp
- whether duplicate same-page tracking ping noise is gone

---

## Self-Review

- Spec coverage:
  - announcement asset domain, temp upload, embed whitelist: Tasks 1-2
  - share navigation context and HTML side back rail: Task 3
  - current-version timestamp contract: Task 4
  - tracking duplicate de-noise: Task 5
  - verification/docs sync: Task 6
- Placeholder scan:
  - No TODO/TBD placeholders.
- Type consistency:
  - Announcement media blocks use `source_type`, `file_id`, `asset_id`
  - Share context uses `from`, `folder_scope`, `folder_id`
  - Share preview payload uses `current_version_entry`
- User constraint:
  - No commit/reset/clean/push steps are included.

## Execution Update (2026-07-06)

- Completed in worktree: `C:\Users\lihuo\Desktop\docshop\.worktrees\annc-share-nav-tracking-20260706`
- Backend verification:
  - `python -m pytest backend/tests/test_announcement_assets.py backend/tests/test_announcements_rich_blocks.py backend/tests/test_share.py test/test_tracking_ping.py -q`
  - Result: `52 passed in 7.68s`
- Frontend verification:
  - `npm.cmd run test -- src/components/announcement/__tests__/AnnouncementAssetPickerDialog.spec.js src/utils/__tests__/announcementBlocks.spec.js src/components/announcement/__tests__/AnnouncementBlockEditor.spec.js src/components/announcement/__tests__/AnnouncementRenderer.spec.js src/views/admin/__tests__/AnnouncementManagerRichBlocks.spec.js src/utils/__tests__/shareRoute.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareDiff.spec.js src/utils/__tests__/trackingClient.spec.js --run`
  - Result: `11 passed, 78 passed in 3.78s`
- Frontend build:
  - `npm.cmd run build`
  - Result: `vite build` succeeded in `4.63s`
  - Note: build output only reported non-blocking Rollup `/* #__PURE__ */` annotation warnings from `@vueuse/core`
- Verified outcomes:
  - Share preview/file/diff/project routes now preserve `from`, `folder_scope`, `folder_id`
  - HTML immersive preview now shows a dedicated side back control without dropping iframe interaction
  - SharePreview metadata now prefers `current_version_entry.created_at`
  - Same-page duplicate tracking page-views are suppressed on the frontend and return `204` on the backend
- Remaining optional follow-ups:
  - If later needed, auto-normalize invalid share folder query back into URL after folder deletion/move
  - Expand announcement embed whitelist beyond the current bilibili-focused baseline only when concrete providers are confirmed

## Follow-up Update (2026-07-06, LAN startup hardening)

- Newly discovered blocker:
  - local/backend dev startup without `.env` failed because `SECRET_KEY` defaulted to `docshop-secret-key-change-me-32chars` while the validator simultaneously rejected any value containing `change-me`
- Fix applied:
  - changed the built-in development default to a valid stable key: `docshop-dev-secret-key-local-default-2026`
  - added `is_builtin_secret_key()` so production warning logic still flags built-in/placeholder secrets instead of silently accepting them
- Added regression coverage:
  - `test_settings_can_boot_without_secret_key_env`
  - `test_validate_settings_warns_for_builtin_dev_secret_in_production`
- Verification:
  - `python -m pytest tests/test_config.py -q`
  - Result: `53 passed in 2.44s`
  - `scripts/start_dev.ps1 -BackendHost 0.0.0.0 -FrontendHost 0.0.0.0`
  - Runtime check:
    - backend listening on `0.0.0.0:8000`
    - frontend listening on `0.0.0.0:3000`
    - `GET http://127.0.0.1:8000/health` -> `200`
    - `GET http://127.0.0.1:3000` -> `200`
