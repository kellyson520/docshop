# Precise Tracking Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Implement the low-risk first phase of browser-side precise tracking: visitor ID, page-view filtering, optional browser geolocation enrichment, and clearer admin log display.

**Architecture:** Keep existing TrackingMiddleware as the source of base access logs. Add a small browser beacon that enriches the latest log through a new ping endpoint. Store only practical low-risk browser fields and keep geolocation behind existing tracking config switches.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite additive schema updates, Vue 3, Element Plus, Vitest, Pytest

---

## File Structure

### Backend

- Modify: `backend/app/models/access_log.py`
  - Add `visitor_id`, `is_page_view`, `geo_latitude`, `geo_longitude`, `geo_accuracy`, `client_timezone`, `client_language`.
  - Include fields in `to_dict()`.
- Modify: `backend/app/models/user_session.py`
  - Add `visitor_id` for future correlation.
- Modify: `backend/app/database.py`
  - Add additive SQLite migrations for the new columns.
- Modify: `backend/app/middlewares/tracking.py`
  - Populate `visitor_id` from existing device cookie.
  - Classify real page views vs API/assets.
  - Skip `/api/v1/tracking/ping` to avoid self-logging noise.
- Create: `backend/app/routers/tracking_ping.py`
  - `POST /api/v1/tracking/ping` enriches latest access log by session/device.
- Modify: `backend/app/routers/tracking_admin.py`
  - Add `page_views_only` filter to logs endpoint if missing.
- Modify: `backend/app/main.py`
  - Register tracking ping router.
- Create/Modify tests:
  - `test/test_tracking_access_log.py`
  - `test/test_tracking_middleware.py`
  - `test/test_tracking_ping.py`

### Frontend

- Create: `frontend/src/utils/trackingClient.js`
  - Fetch tracking config, collect low-risk browser info, optionally collect geolocation, send beacon.
- Modify: `frontend/src/main.js`
  - Initialize tracking after app startup/DOMContentLoaded.
- Modify/Create: `frontend/src/utils/trackingDisplay.js`
  - Add `formatGeoLocation()` if missing.
- Modify: `frontend/src/views/admin/TrackingDashboard.vue`
  - Add only-page-view switch, visitor ID column, readable location/timezone/language display.
- Create tests:
  - `frontend/src/utils/__tests__/trackingClient.spec.js`
  - Update/create tracking display/dashboard regression tests where practical.

---

## Task 1: Backend storage fields and additive migration

- [x] Write failing tests asserting `AccessLog.to_dict()` exposes new fields and `_access_log_additive_statements()` adds missing columns.
- [x] Run `python -m pytest -o addopts='-q' test/test_tracking_access_log.py` and confirm RED.
- [x] Add model columns and migration statements.
- [x] Re-run test and confirm GREEN.

## Task 2: Middleware visitor ID and page-view classification

- [x] Write failing tests for `_is_page_view()` HTML/API/asset classification and for ping path skip helper if available.
- [x] Run `python -m pytest -o addopts='-q' test/test_tracking_middleware.py` and confirm RED.
- [x] Implement minimal middleware changes.
- [x] Re-run test and confirm GREEN.

## Task 3: Tracking ping endpoint

- [x] Write failing tests for:
  - accepts `session_id/device_id` payload;
  - updates latest access log with geo/timezone/language/screen fields;
  - anonymizes coordinates when config says anonymize;
  - rate limits duplicate pings.
- [x] Run `python -m pytest -o addopts='-q' test/test_tracking_ping.py` and confirm RED.
- [x] Implement `backend/app/routers/tracking_ping.py` and router registration.
- [x] Re-run test and confirm GREEN.

## Task 4: Frontend tracking beacon

- [x] Write failing Vitest for:
  - config disables tracking -> no beacon;
  - location disabled -> no geolocation call;
  - device/location enabled -> sends expected low-risk payload.
- [x] Run `npm test -- --run src/utils/__tests__/trackingClient.spec.js` and confirm RED.
- [x] Implement `trackingClient.js` and wire `main.js`.
- [x] Re-run test and confirm GREEN.

## Task 5: Admin tracking log UI polish

- [x] Add/adjust frontend regression tests checking page-view filter param and location formatter.
- [x] Run relevant Vitest and confirm RED if test is new.
- [x] Update `TrackingDashboard.vue` and `trackingDisplay.js`.
- [x] Re-run Vitest and confirm GREEN.

## Task 6: Final verification

- [x] Backend compile:
  `python -m py_compile app/models/access_log.py app/models/user_session.py app/database.py app/middlewares/tracking.py app/routers/tracking_ping.py app/routers/tracking_admin.py app/main.py`
- [x] Backend tests:
  `python -m pytest -o addopts='-q' test/test_tracking_access_log.py test/test_tracking_middleware.py test/test_tracking_ping.py`
- [x] Frontend tests:
  `npm test -- --run src/utils/__tests__/trackingClient.spec.js src/utils/__tests__/frontend-regressions.spec.js`
- [x] Frontend build:
  `npm run build`

## Self-Review

- Scope is limited to first phase: no Leaflet, no visitor profile aggregate, no announcement targeting editor.
- Field names match the original spec: `visitor_id`, `is_page_view`, `geo_latitude`, `geo_longitude`, `geo_accuracy`, `client_timezone`, `client_language`.
- Privacy: geolocation is gated by server config and browser permission; anonymization is server-side.

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

