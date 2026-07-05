# Admin Dialog and Share Granularity Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. User override: do not commit, push, reset, clean, or otherwise mutate git history.

**Goal:** Fix admin dialogs that open against the inner scroll container instead of the current viewport, align share-token editing granularity with the current share dialog, and remove visible mojibake from the file action menu.

**Architecture:** Frontend adds one reusable admin dialog prop helper plus one shared share-access policy helper. Admin pages opt into the shared viewport dialog contract so dialogs are teleported to `body` and centered in the viewport. TokenManager reuses the same share-access policy vocabulary as ProjectDetail and submits the aligned payload without accidentally clearing an existing password.

**Tech Stack:** Vue 3 Composition API, Element Plus dialogs/forms, Vitest source-regression + component tests, Vite build.

---

## Progress Update (2026-07-04 23:10)

- [x] Share permission granularity is now reflected in public share action UI
  - `frontend/src/views/share/ShareProject.vue`: project/file list actions now respect `allow_download`, `allow_preview`, `allow_diff`, and `allow_versions`; blocked actions render disabled/gray and are not clickable.
  - `frontend/src/views/share/ShareFile.vue`: version download and "view diff" actions respect share permission flags.
  - `frontend/src/views/share/ShareDiff.vue`: old/new version downloads respect `allow_download`.
- [x] Regression coverage added / verified
  - `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
  - `frontend/src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
  - `frontend/src/views/share/__tests__/ShareDiff.spec.js`
  - `frontend/src/views/share/__tests__/ShareProjectDisplayName.spec.js`
  - `frontend/src/views/share/__tests__/ShareLayout.spec.js`
- [x] Verification command run on 2026-07-04 23:08
  - `npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js src/views/share/__tests__ --run`
  - Result: `8 passed` test files, `66 passed` tests.

## File Structure

### Frontend create

- `frontend/src/utils/adminDialog.js`
  - Shared admin dialog props for viewport-level dialogs.

- `frontend/src/utils/shareAccess.js`
  - Shared share policy mode options and normalization helpers.

- `frontend/src/views/admin/__tests__/AdminViewportDialogs.spec.js`
  - Source-level regression test for shared admin dialog usage and global styling.

- `frontend/src/views/admin/__tests__/TokenManager.spec.js`
  - Component-level regression tests for aligned share-token editing fields and payload handling.

### Frontend modify

- `frontend/src/style.css`
  - Global reusable styling for `.admin-viewport-dialog`.

- `frontend/src/views/admin/ProjectList.vue`
  - Apply shared viewport dialog props to the create-project dialog.

- `frontend/src/views/admin/TrackingDashboard.vue`
  - Apply shared viewport dialog props to module and access-info dialogs.

- `frontend/src/views/admin/TokenManager.vue`
  - Apply shared viewport dialog props to dialogs.
  - Align share-token edit form with current share dialog permissions.
  - Prevent implicit password clearing.
  - Improve share-token restriction summary text.

- `frontend/src/views/admin/ProjectDetail.vue`
  - Reuse shared share-access helper.
  - Apply shared viewport dialog props to admin dialogs that should open in the current viewport.
  - Fix `share-access` menu mojibake to `瀹夊叏鍒嗕韩`.

- `frontend/src/views/admin/CardManage.vue`
  - Apply shared viewport dialog props to edit/upload/delete dialogs.

- `frontend/src/views/admin/AnnouncementManager.vue`
  - Apply shared viewport dialog props to the announcement editor dialog.

- `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`
  - Add regression coverage for the `瀹夊叏鍒嗕韩` menu label.

---

## Task 1: Red Tests for Viewport Dialog Contract

**Files:**
- Create: `frontend/src/views/admin/__tests__/AdminViewportDialogs.spec.js`

- [x] **Step 1: Write a source regression test**

Cover:

- `ProjectList.vue` uses `ADMIN_VIEWPORT_DIALOG_PROPS`.
- `TokenManager.vue` uses the shared dialog props on all four dialogs.
- `TrackingDashboard.vue` uses the shared dialog props on both dialogs.
- `ProjectDetail.vue`, `CardManage.vue`, and `AnnouncementManager.vue` use the shared dialog props on their admin dialogs.
- `style.css` defines reusable `.admin-viewport-dialog` body sizing rules.

- [x] **Step 2: Run the test and confirm it fails**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/views/admin/__tests__/AdminViewportDialogs.spec.js --run
```

Expected before implementation: failure because helper imports/bindings/styles do not exist yet.

---

## Task 2: Red Tests for Share-Token Granularity

**Files:**
- Create: `frontend/src/views/admin/__tests__/TokenManager.spec.js`
- Modify: `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`

- [x] **Step 1: Write TokenManager regression tests**

Cover:

- Opening share-token editor exposes aligned fields:
  - `require_login`
  - `password`
  - `password_hint`
  - `allow_preview`
  - `allow_diff`
  - `allow_versions`
  - `policy_mode`
  - password-clear control
- Saving submits the aligned payload.
- Blank password does **not** implicitly clear the current password.
- Explicit clear-password action sends `password: ''`.

- [x] **Step 2: Add ProjectDetail mojibake regression**

Add a source-level assertion that both `share-access` dropdown entries render `瀹夊叏鍒嗕韩` and no longer contain the mojibake text.

- [x] **Step 3: Run tests and confirm they fail**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/views/admin/__tests__/TokenManager.spec.js src/views/admin/__tests__/ProjectDetail.spec.js --run
```

Expected before implementation: failures because the fields/payload/label are not yet aligned.

---

## Task 3: Implement Shared Helpers and Apply Them

**Files:**
- Create: `frontend/src/utils/adminDialog.js`
- Create: `frontend/src/utils/shareAccess.js`
- Modify: `frontend/src/style.css`
- Modify: `frontend/src/views/admin/ProjectList.vue`
- Modify: `frontend/src/views/admin/TrackingDashboard.vue`
- Modify: `frontend/src/views/admin/TokenManager.vue`
- Modify: `frontend/src/views/admin/ProjectDetail.vue`
- Modify: `frontend/src/views/admin/CardManage.vue`
- Modify: `frontend/src/views/admin/AnnouncementManager.vue`

- [x] **Step 1: Add reusable admin dialog props**

Implement shared viewport dialog props:

- `appendToBody: true`
- `alignCenter: true`
- `lockScroll: true`

Add global `.admin-viewport-dialog` rules so the dialog body scrolls internally instead of requiring the admin container to scroll to the top.

- [x] **Step 2: Apply shared dialog props across admin pages**

Add `v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"` and `admin-viewport-dialog` classes to the affected admin dialogs.

- [x] **Step 3: Extract share policy mode helpers**

Move share policy mode options and normalization into `shareAccess.js`, then reuse from both `ProjectDetail.vue` and `TokenManager.vue`.

- [x] **Step 4: Align TokenManager share-token editor**

Implement:

- strategy mode selector
- login/password/password-hint controls
- preview/diff/version switches
- safe password handling
- expanded restriction summary text

- [x] **Step 5: Fix ProjectDetail mojibake**

Replace both `share-access` dropdown labels with `瀹夊叏鍒嗕韩`.

---

## Task 4: Verification

**Files:**
- No new files unless fixing test/build failures.

- [x] **Step 1: Run focused frontend tests**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/views/admin/__tests__/AdminViewportDialogs.spec.js src/views/admin/__tests__/TokenManager.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TrackingDashboard.spec.js --run
```

Expected: all pass.

- [x] **Step 2: Run frontend build**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run build
```

Expected: build succeeds.

- [x] **Step 3: Start backend only after frontend verification if the user wants to inspect**

Run the existing backend start command already used in this workspace after test/build pass.

---

## Self-Review

- Scope coverage: plan covers viewport-level admin dialogs, TokenManager granularity alignment, visible mojibake removal, and verification.
- Placeholder scan: no `TODO`/`TBD` placeholders left in execution steps.
- Type consistency: shared dialog prop names use Element Plus camelCase props; shared share policy helpers use the same `policy_mode` values already supported by backend routes.
- User override: no git mutation steps are included.

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


