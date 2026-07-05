# Unified Event Channel and Resource URL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. User override: do not commit, push, reset, clean, or otherwise mutate git history.

**Goal:** Build a reusable SSE-based event channel, migrate config hot sync away from frontend polling, centralize browser-facing resource URL construction, and document backend request path mapping.

**Architecture:** Backend adds an in-process async event bus, an SSE router at `/api/v1/events/stream`, and a lightweight `.env` watcher started from FastAPI lifespan. Frontend adds a fetch-based SSE client, a composable subscription wrapper, and a single `resourceUrl.js` utility used by preview/download/avatar/cover/share code paths.

**Tech Stack:** FastAPI / Starlette `StreamingResponse`, asyncio, pytest; Vue 3 Composition API, Vitest, Vite, JavaScript `fetch` streams.

---

## File Structure

### Backend create

- `backend/app/services/event_bus.py`
  - Defines `EventEnvelope`, `EventSubscriber`, `EventBus`, global `event_bus`, and helpers for publishing config events.
  - Keeps queue management and SSE formatting out of routers.

- `backend/app/services/config_watch.py`
  - Defines `ConfigFileWatcher` and hashing/debounce logic for `.env` changes.
  - Calls `apply_runtime_settings()` and publishes `config.updated` when external file edits are detected.

- `backend/app/routers/events.py`
  - Defines `GET /api/v1/events/stream`.
  - Authenticates users, validates topics, subscribes to `event_bus`, and streams SSE frames.

- `backend/tests/test_event_bus.py`
  - Unit tests for event envelope creation, topic filtering, queue policy, and SSE formatting.

- `backend/tests/test_config_watch.py`
  - Unit tests for fingerprint change detection and publishing config events.

### Backend modify

- `backend/app/main.py`
  - Include `events.router`.
  - Start and stop `ConfigFileWatcher` in lifespan.

- `backend/app/routers/settings.py`
  - After successful runtime `.env` write and apply, publish `config.updated`.
  - Export or reuse `_env_abs_path()` for watcher setup through `config_watch`.

### Frontend create

- `frontend/src/services/eventStream.js`
  - Fetch-based SSE client with Authorization header, parser, heartbeats, reconnect, and callbacks.

- `frontend/src/composables/useEventChannel.js`
  - Vue composable for mounting/unmounting event subscriptions.

- `frontend/src/utils/resourceUrl.js`
  - Central browser-facing URL builder for avatar, cover, file preview/download/page/assets, share preview/download/page/assets, and announcement attachment.

- `frontend/src/services/__tests__/eventStream.spec.js`
  - Tests SSE parser, auth header, event dispatch, reconnect conditions.

- `frontend/src/utils/__tests__/resourceUrl.spec.js`
  - Tests resource URL builders and normalization.

### Frontend modify

- `frontend/src/utils/assetUrl.js`
  - Delegate avatar/static asset normalization to `resourceUrl.js` or keep as compatibility wrapper.

- `frontend/src/utils/cover.js`
  - Delegate to `resourceUrl.js`.

- `frontend/src/utils/preview.js`
  - Delegate preview URL construction to `resourceUrl.js`.

- `frontend/src/views/admin/AdminSettings.vue`
  - Remove polling interval constants and timers.
  - Subscribe to `config` events and reload settings on `config.updated`.

- `frontend/src/views/admin/DiffView.vue`
  - Replace inline file preview URL builder with `resourceUrl.js`.

- `frontend/src/components/announcement/AnnouncementRenderer.vue`
  - Replace inline attachment URL with `buildAnnouncementAttachmentUrl()`.

- `frontend/src/views/share/ShareDiff.vue`
  - Replace share download URL builder with `buildShareDownloadUrl()`.

- `frontend/src/views/share/ShareFile.vue`
  - Replace share download URL builder with `buildShareDownloadUrl()`.

- `frontend/src/views/share/SharePreview.vue`
  - Replace share preview and preview asset path handling with `resourceUrl.js` where URLs are locally constructed.

- `frontend/src/views/share/ShareProject.vue`
  - Replace share folder and file download URL builders with `resourceUrl.js`.

### Docs create

- `docs/backend-route-map.md`
  - Human-readable backend route grouping extracted from routers.

---

## Task 1: Backend Event Bus Unit

**Files:**
- Create: `backend/app/services/event_bus.py`
- Create: `backend/tests/test_event_bus.py`

- [ ] **Step 1: Write tests for event publishing and subscriber filtering**

Create `backend/tests/test_event_bus.py` with tests that import `EventBus`, subscribe to `config`, publish a `config.updated` event, and assert only matching-topic subscribers receive it.

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_event_bus.py -q
```

Expected before implementation: import or symbol errors.

- [ ] **Step 2: Implement minimal event bus**

Implement in `backend/app/services/event_bus.py`:

- `EventEnvelope` dataclass with `id`, `topic`, `type`, `scope`, `ts`, `version`, `payload`.
- `EventSubscriber` with `topics`, `user_id`, `role`, bounded `asyncio.Queue`.
- `EventBus.subscribe(...)` async context manager.
- `EventBus.publish(...)` that delivers to matching topics without blocking indefinitely.
- `format_sse(event_name, event_id, data)` helper.
- Global `event_bus = EventBus()`.
- `publish_config_updated(changed_keys, source)` async helper.

- [ ] **Step 3: Verify event bus tests pass**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_event_bus.py -q
```

Expected: all tests pass.

---

## Task 2: Backend SSE Router

**Files:**
- Create: `backend/app/routers/events.py`
- Modify: `backend/app/main.py`
- Create/update backend event route tests if existing test client auth helpers are available; otherwise verify by unit-testing route helpers and run import tests.

- [ ] **Step 1: Inspect existing auth dependency usage**

Check existing routers for `get_current_user` and `get_current_admin`. Use the same dependency style as `settings.py`.

- [ ] **Step 2: Implement `/api/v1/events/stream`**

Create `backend/app/routers/events.py`:

- `router = APIRouter(prefix="/api/v1/events", tags=["events"])`
- `GET /stream`
- Query param `topics: str = "config"`
- Validate against allowed topic set: `config`, `announcements`, `tracking`, `tasks`
- Admin-only topics in first version: `config`, `tracking`
- Subscribe to global `event_bus`
- Stream `ready`, published events, and `heartbeat`
- Use `StreamingResponse(..., media_type="text/event-stream")`
- Headers:
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`

- [ ] **Step 3: Register router in main**

Modify `backend/app/main.py` imports and route registration:

- Add `events` to router import list.
- Add `app.include_router(events.router)` near other `/api/v1` routers.

- [ ] **Step 4: Verify imports**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
python -c "from app.main import app; print('ok')"
```

Expected: `ok`.

---

## Task 3: Config Watcher and Settings Publish

**Files:**
- Create: `backend/app/services/config_watch.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/routers/settings.py`
- Create: `backend/tests/test_config_watch.py`

- [ ] **Step 1: Write watcher tests**

Create `backend/tests/test_config_watch.py` to validate:

- A missing file returns empty fingerprint but does not crash.
- A content change changes fingerprint.
- `check_once()` publishes once when fingerprint changes after initial baseline.

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_config_watch.py -q
```

Expected before implementation: import or symbol errors.

- [ ] **Step 2: Implement `ConfigFileWatcher`**

In `backend/app/services/config_watch.py` implement:

- `fingerprint_file(path)` using mtime, size, and SHA-256 content hash for small `.env` file.
- `ConfigFileWatcher(env_path_provider, interval_seconds=1.0, debounce_seconds=0.25)`.
- `start()` creating an asyncio task.
- `stop()` cancelling and awaiting task.
- `check_once()` for tests.
- On external change: `apply_runtime_settings(env_path)` then `publish_config_updated(changed_keys=[], source="env-file")`.

- [ ] **Step 3: Publish events after settings API saves**

Modify `backend/app/routers/settings.py`:

- Import `asyncio` and `publish_config_updated`.
- After `_write_env(env_body)` and `apply_runtime_settings(...)`, publish `config.updated`.
- Because the route is currently sync, use a small helper that schedules on the running loop if one exists, otherwise runs via `asyncio.run()` safely for test contexts.

- [ ] **Step 4: Start watcher in lifespan**

Modify `backend/app/main.py`:

- Import `ConfigFileWatcher` and settings router module as needed.
- Create watcher during startup after required directories exist.
- Store on `app.state.config_watcher`.
- Stop it during shutdown.

- [ ] **Step 5: Verify backend focused tests**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_event_bus.py tests/test_config_watch.py -q
python -c "from app.main import app; print('ok')"
```

Expected: tests pass and import prints `ok`.

---

## Task 4: Frontend Event Stream Client

**Files:**
- Create: `frontend/src/services/eventStream.js`
- Create: `frontend/src/services/__tests__/eventStream.spec.js`

- [ ] **Step 1: Write tests for SSE parser and client options**

Create tests that verify:

- `parseSseFrames()` parses `event`, `id`, and JSON `data`.
- Empty heartbeat frames do not emit app events.
- `buildEventStreamUrl(['config'])` returns `/api/v1/events/stream?topics=config`.

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/services/__tests__/eventStream.spec.js --run
```

Expected before implementation: import errors.

- [ ] **Step 2: Implement `eventStream.js`**

Implement:

- `buildEventStreamUrl(topics)`
- `parseSseFrames(buffer)`
- `createEventStreamClient({ topics, fetchImpl, getToken, onEvent, onError, onStateChange })`
- `start()` and `stop()` methods
- Reconnect with bounded exponential backoff
- Authorization header using `Bearer ${token}` when token exists

- [ ] **Step 3: Verify event stream tests pass**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/services/__tests__/eventStream.spec.js --run
```

Expected: pass.

---

## Task 5: Vue Composable and AdminSettings Migration

**Files:**
- Create: `frontend/src/composables/useEventChannel.js`
- Modify: `frontend/src/views/admin/AdminSettings.vue`
- Modify: `frontend/src/views/admin/__tests__/AdminSettings.spec.js`

- [ ] **Step 1: Implement composable**

Create `useEventChannel.js` that:

- Accepts `{ topics, onEvent, enabled }`.
- Starts client on mount.
- Stops client on unmount.
- Returns state: `connected`, `lastEvent`, `error`, `restart`, `stop`.

- [ ] **Step 2: Remove polling from AdminSettings**

Modify `AdminSettings.vue`:

- Remove `SECURITY_REFRESH_INTERVAL_MS`, `settingsRefreshTimer`, `startSettingsRefresh`, `stopSettingsRefresh`, and tab-driven polling calls.
- Add `useEventChannel({ topics: ['config'], onEvent })`.
- On `event.topic === 'config' && event.type === 'config.updated'`, call existing load/refresh settings function.
- Keep manual save behavior: after save, reload settings once for immediate feedback.

- [ ] **Step 3: Update AdminSettings tests**

Adjust tests to assert:

- Polling interval is no longer created.
- When mocked event callback receives `config.updated`, settings reload function/API is called.

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/views/admin/__tests__/AdminSettings.spec.js --run
```

Expected: pass.

---

## Task 6: Resource URL Helper

**Files:**
- Create: `frontend/src/utils/resourceUrl.js`
- Create: `frontend/src/utils/__tests__/resourceUrl.spec.js`
- Modify: `frontend/src/utils/assetUrl.js`
- Modify: `frontend/src/utils/cover.js`
- Modify: `frontend/src/utils/preview.js`

- [ ] **Step 1: Write resource URL tests**

Create tests covering:

- `resolveAvatarUrl('avatars/u/a.png') -> '/api/v1/avatars/u/a.png'`
- `resolveCoverUrl('/covers/c.png') -> '/api/v1/covers/c.png'`
- External `https://`, `data:`, `blob:` are unchanged.
- `buildFilePreviewUrl('f1', { version: 2, authToken: 'tok', cacheKey: 'c' })`.
- `buildFilePageUrl('f1', 3, { version: 2, authToken: 'tok' })`.
- `buildFilePreviewAssetUrl('f1', 'a1')`.
- `buildFileDownloadUrl('f1')` and `buildFileDownloadUrl('f1', 'v1', 'pdf')`.
- `buildSharePreviewUrl('s1', 'f1')`.
- `buildShareDownloadUrl('s1', 'f1', 'v1', 'pdf')`.
- `buildShareFolderDownloadUrl('s1', 'folder1')`.
- `buildAnnouncementAttachmentUrl('file1')`.

- [ ] **Step 2: Implement helper**

Implement `resourceUrl.js` with small helpers:

- `normalizePath(value)`
- `isExternalUrl(value)`
- `withQuery(path, params)`
- Static asset resolvers
- File/share URL builders

- [ ] **Step 3: Delegate old helpers**

Modify:

- `assetUrl.js` to re-export/delegate `resolveAvatarUrl` and `resolveApiAssetUrl`.
- `cover.js` to call `resolveCoverUrl` from `resourceUrl.js`.
- `preview.js` to call `buildFilePreviewUrl` and retain `buildPreviewSrcdoc()` behavior.

- [ ] **Step 4: Verify URL utility tests**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/utils/__tests__/resourceUrl.spec.js src/utils/__tests__/cover.spec.js src/utils/preview.test.js --run
```

Expected: pass.

---

## Task 7: Refactor Scattered Resource URL Call Sites

**Files:**
- Modify: `frontend/src/components/announcement/AnnouncementRenderer.vue`
- Modify: `frontend/src/views/admin/DiffView.vue`
- Modify: `frontend/src/views/share/ShareDiff.vue`
- Modify: `frontend/src/views/share/ShareFile.vue`
- Modify: `frontend/src/views/share/SharePreview.vue`
- Modify: `frontend/src/views/share/ShareProject.vue`
- Update related tests only where expectations need import/mocking adjustments.

- [ ] **Step 1: Replace announcement attachment URL**

Use `buildAnnouncementAttachmentUrl(fileId)` in `AnnouncementRenderer.vue`.

- [ ] **Step 2: Replace admin preview URL builder**

Use `buildFilePreviewUrl(fileId, { version, authToken: token, cacheKey })` in `DiffView.vue`.

- [ ] **Step 3: Replace share download builders**

Use:

- `buildShareDownloadUrl(token, fileId, versionId, format)`
- `buildShareFolderDownloadUrl(token, folderId)`
- `buildSharePreviewUrl(token, fileId)`

in share views.

- [ ] **Step 4: Scan remaining browser-facing hardcoded URLs**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
Get-ChildItem frontend\src -Recurse -Include *.js,*.vue | Select-String -Pattern '(/api/v1/files/|/api/v1/share/|/api/v1/covers/|/api/v1/avatars/)'
```

Expected: remaining occurrences are in `resourceUrl.js`, tests, backend route-map docs, or intentionally stored API response fixtures.

- [ ] **Step 5: Run related frontend tests**

Run focused tests for changed areas:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/views/share/__tests__ src/views/admin/__tests__/DiffView.spec.js src/utils/__tests__/resourceUrl.spec.js --run
```

Expected: pass.

---

## Task 8: Backend Route Map Doc

**Files:**
- Create: `docs/backend-route-map.md`

- [ ] **Step 1: Write route map documentation**

Create route map grouped by:

- System
- Auth
- Settings
- Events
- Users/Admin
- Projects
- Files
- Diffs
- Cards
- Share/Public
- Share Tokens
- Tracking
- Announcements/Notices/Exams
- Access Tokens
- Static Assets

- [ ] **Step 2: Verify doc has events and static asset routes**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
Select-String -Path docs\backend-route-map.md -Pattern '/api/v1/events/stream','/api/v1/covers','/api/v1/avatars'
```

Expected: all three patterns are present.

---

## Task 9: Final Verification

**Files:**
- No new files unless fixing discovered failures.

- [ ] **Step 1: Backend focused verification**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_event_bus.py tests/test_config_watch.py -q
python -c "from app.main import app; print('ok')"
```

Expected: tests pass and import prints `ok`.

- [ ] **Step 2: Frontend focused verification**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/services/__tests__/eventStream.spec.js src/utils/__tests__/resourceUrl.spec.js src/views/admin/__tests__/AdminSettings.spec.js --run
```

Expected: pass.

- [ ] **Step 3: Frontend build**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Git status only**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
git status --short
```

Expected: show local modifications only. Do not commit.

---

## Self-Review

- Spec coverage: Tasks cover unified event channel, config hot sync, resource URL centralization, backend route map, error handling, and tests.
- Placeholder scan: No `TODO`, `TBD`, or implementation-later placeholders are used as required plan content.
- Type consistency: Backend event envelope fields are consistent across bus/router/watcher. Frontend resource URL function names match call-site migration tasks.
- User override: All commit steps are intentionally omitted because the user requested no local commits.
