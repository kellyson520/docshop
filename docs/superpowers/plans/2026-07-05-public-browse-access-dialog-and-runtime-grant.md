# Public Browse Access Dialog and Runtime Grant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **User constraint:** Do not commit, push, reset, clean, or otherwise mutate git history.

**Goal:** Add project/file public-browse access editors, modal-based restriction details, and legacy public-route tab-scoped password grants while keeping `/s/:token` as the public shell.

**Architecture:** Extend existing resource access policy APIs for admin editing, add a resource-scoped runtime grant for legacy public browse under share routes, and update admin/share Vue views to consume those capabilities. Manual managed share tokens keep their current behavior; legacy public project shells gain resource-policy-driven password/group enforcement.

**Tech Stack:** FastAPI, SQLAlchemy, existing access control services, Vue 3 Composition API, Element Plus, pytest, Vitest.

---

## File Structure

### Backend create

- `backend/app/models/resource_access_grant.py`
  - Stores legacy public-browse tab-scoped resource unlock grants.
- `backend/app/services/resource_access_grant_service.py`
  - Issue/validate/heartbeat/release resource grants.
- `backend/tests/test_resource_access_grant_service.py`
  - TDD coverage for grant lifecycle.

### Backend modify

- `backend/app/models/__init__.py`
  - Register new model import.
- `backend/app/database.py`
  - Ensure grant table migration/creation.
- `backend/app/routers/access_control.py`
  - Add group list endpoint and extend policy GET/PUT payloads.
- `backend/app/routers/share.py`
  - Add public-access unlock/heartbeat/release endpoints and legacy public-route enforcement/ticket integration.
- `backend/app/services/access_control_service.py`
  - Add merged download helpers if needed and preserve password/group semantics.
- `backend/tests/test_access_control_api.py`
  - Add policy password/download/group-list coverage.
- `backend/tests/test_share.py`
  - Add legacy public-browse password/group route coverage.
- `backend/tests/test_share_resource_tickets.py`
  - Add resource-access-grant ticket issuance coverage.

### Frontend create

- `frontend/src/api/accessControl.js`
  - Admin public-browse policy APIs + legacy public-access unlock APIs.
- `frontend/src/utils/resourceAccessForm.js`
  - Normalize editor state and payloads for project/file public-browse access.
- `frontend/src/composables/usePublicAccessSession.js`
  - Legacy public-route tab-scoped access grant lifecycle.
- `frontend/src/utils/__tests__/resourceAccessForm.spec.js`
  - Form normalization/mutation tests.
- `frontend/src/composables/__tests__/usePublicAccessSession.spec.js`
  - Grant lifecycle tests.

### Frontend modify

- `frontend/src/views/admin/ProjectDetail.vue`
  - Expand file settings and add project public-browse access modal.
- `frontend/src/views/admin/TokenManager.vue`
  - Replace inline restriction wall with detail dialog.
- `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`
  - Add admin public-browse dialog coverage.
- `frontend/src/views/admin/__tests__/TokenManager.spec.js`
  - Add detail dialog coverage.
- `frontend/src/views/share/ShareProject.vue`
  - Handle legacy public resource password/group requirements.
- `frontend/src/views/share/ShareFile.vue`
  - Handle file-level public access gating.
- `frontend/src/views/share/SharePreview.vue`
  - Handle file-level public access gating for runtime preview.
- `frontend/src/views/share/ShareDiff.vue`
  - Handle file-level public access gating for diff.
- `frontend/src/utils/shareResourceTickets.js`
  - Attach public-access headers when active.
- `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
  - Cover project password flow and group/login denial.
- `frontend/src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
  - Cover file resource-password ticket flow.
- `frontend/src/views/share/__tests__/SharePreview.spec.js`
  - Cover preview unlock path and access headers.

### Docs modify

- `docs/frontend-browser-resource-protocol.md`
- `docs/superpowers/specs/2026-07-05-public-browse-access-dialog-and-runtime-grant-design.md`
- `docs/superpowers/plans/2026-07-05-public-browse-access-dialog-and-runtime-grant.md`

---

## Task 1: Backend access-control admin API enhancements

**Files:**
- Modify: `backend/app/routers/access_control.py`
- Modify: `backend/tests/test_access_control_api.py`

- [ ] **Step 1: Write failing backend API tests for merged download/password/group list behavior**

Add tests such as:

```python
def test_admin_can_list_access_groups(client, auth_headers, db_session):
    ...


def test_policy_put_accepts_password_clear_and_merged_allow_download(client, auth_headers, db_session, test_user):
    ...
```

Cover:
- `GET /api/v1/access-control/groups`
- `PUT policy` accepts `password`, `clear_password`, `allow_download`
- `GET policy` returns `has_password` and merged `allow_download`

- [ ] **Step 2: Run targeted backend tests to verify RED**

Run:

```powershell
python -m pytest backend/tests/test_access_control_api.py -q
```

Expected before implementation: failures for missing endpoint / missing payload fields.

- [ ] **Step 3: Implement admin API enhancements minimally**

Implementation requirements:
- add `GET /groups`
- hash password when `password` is non-empty
- clear password hash when `clear_password` is true and no replacement password
- map merged `allow_download` to both download flags
- include `allow_download` + `has_password` in serialized policy payload

- [ ] **Step 4: Re-run targeted backend tests to verify GREEN**

Run:

```powershell
python -m pytest backend/tests/test_access_control_api.py -q
```

Expected: pass.

---

## Task 2: Backend legacy public-browse runtime grant

**Files:**
- Create: `backend/app/models/resource_access_grant.py`
- Create: `backend/app/services/resource_access_grant_service.py`
- Create: `backend/tests/test_resource_access_grant_service.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/routers/share.py`
- Modify: `backend/tests/test_share.py`
- Modify: `backend/tests/test_share_resource_tickets.py`

- [ ] **Step 1: Write failing grant lifecycle tests**

Add tests covering:

```python
def test_issue_validate_heartbeat_and_release_resource_access_grant(db_session):
    ...


def test_resource_access_grant_rejects_wrong_resource_or_tab(db_session):
    ...
```

- [ ] **Step 2: Run targeted grant tests to verify RED**

Run:

```powershell
python -m pytest backend/tests/test_resource_access_grant_service.py -q
```

Expected: module/service/model missing.

- [ ] **Step 3: Implement grant model/service**

Requirements:
- store `share_token`, `resource_type`, `resource_id`, `tab_id`, `grant_hash`
- validate by exact resource + tab
- heartbeat extends expiry
- release sets `released_at`

- [ ] **Step 4: Write failing legacy public-route tests**

Add tests covering:
- public project root with `password_required` returns `resource_password_required`
- unlock endpoint accepts correct password and returns grant
- protected file under public project can require its own password
- `groups_required` produces `login_required` / `group_required`
- ticket issuance works when access grant is active

- [ ] **Step 5: Run targeted share tests to verify RED**

Run:

```powershell
python -m pytest backend/tests/test_share.py backend/tests/test_share_resource_tickets.py -q
```

Expected: failures for missing endpoints/details/grant integration.

- [ ] **Step 6: Implement legacy public-access runtime endpoints and enforcement**

Implementation requirements:
- add `/api/v1/share/{share_token}/public-access/unlock`
- add `/grant/heartbeat` and `/grant/release`
- only apply resource-grant flow to legacy public browse shells
- preserve existing managed share-token password behavior
- extend ticket issuance to accept `X-Access-Tab-Id` / `X-Access-Grant`
- return `resource_password_required` when legacy public resource policy blocks access

- [ ] **Step 7: Re-run targeted backend runtime tests to verify GREEN**

Run:

```powershell
python -m pytest backend/tests/test_resource_access_grant_service.py backend/tests/test_share.py backend/tests/test_share_resource_tickets.py -q
```

Expected: all pass.

---

## Task 3: Frontend admin public-browse access dialogs

**Files:**
- Create: `frontend/src/api/accessControl.js`
- Create: `frontend/src/utils/resourceAccessForm.js`
- Create: `frontend/src/utils/__tests__/resourceAccessForm.spec.js`
- Modify: `frontend/src/views/admin/ProjectDetail.vue`
- Modify: `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`

- [ ] **Step 1: Write failing frontend tests for access form helper and ProjectDetail dialogs**

Add tests covering:

```js
it('normalizes merged public-browse access form state', () => { ... })
it('opens file settings with public-browse controls and saves merged payload', async () => { ... })
it('opens project public-browse dialog and saves project policy', async () => { ... })
```

- [ ] **Step 2: Run targeted frontend tests to verify RED**

Run:

```powershell
npm.cmd run test -- src/utils/__tests__/resourceAccessForm.spec.js src/views/admin/__tests__/ProjectDetail.spec.js --run
```

Expected: failures for missing helper/API/dialog state.

- [ ] **Step 3: Implement access-control frontend API/helper**

Requirements:
- fetch/update resource policy
- list access groups
- normalize `allow_download`
- support `password`, `clear_password`, `group_codes`
- expose project/file defaults with `inherit` only for file scope

- [ ] **Step 4: Implement ProjectDetail public-browse dialogs**

Requirements:
- expand file settings modal with a public-browse section
- add project-level access button + modal
- load policy + groups on open
- save file metadata and file policy together from file settings modal
- reject or warn when saving a public project with `private` visibility

- [ ] **Step 5: Re-run targeted frontend tests to verify GREEN**

Run:

```powershell
npm.cmd run test -- src/utils/__tests__/resourceAccessForm.spec.js src/views/admin/__tests__/ProjectDetail.spec.js --run
```

Expected: pass.

---

## Task 4: Frontend share-token restriction dialog

**Files:**
- Modify: `frontend/src/views/admin/TokenManager.vue`
- Modify: `frontend/src/views/admin/__tests__/TokenManager.spec.js`

- [ ] **Step 1: Write failing TokenManager detail-dialog test**

Add a test such as:

```js
it('opens a read-only restriction detail dialog instead of rendering all limits inline', async () => { ... })
```

Cover:
- `权限详情` button exists
- dialog opens with expected summary items and quota fields

- [ ] **Step 2: Run targeted TokenManager tests to verify RED**

Run:

```powershell
npm.cmd run test -- src/views/admin/__tests__/TokenManager.spec.js --run
```

Expected: failure because dialog behavior does not exist.

- [ ] **Step 3: Implement detail dialog minimally**

Requirements:
- keep compact in-table summary
- move full restriction display into read-only modal
- preserve existing share-access summary helper usage

- [ ] **Step 4: Re-run targeted TokenManager tests to verify GREEN**

Run:

```powershell
npm.cmd run test -- src/views/admin/__tests__/TokenManager.spec.js --run
```

Expected: pass.

---

## Task 5: Frontend legacy public-browse access session and share pages

**Files:**
- Create: `frontend/src/composables/usePublicAccessSession.js`
- Create: `frontend/src/composables/__tests__/usePublicAccessSession.spec.js`
- Modify: `frontend/src/api/accessControl.js`
- Modify: `frontend/src/utils/shareResourceTickets.js`
- Modify: `frontend/src/views/share/ShareProject.vue`
- Modify: `frontend/src/views/share/ShareFile.vue`
- Modify: `frontend/src/views/share/SharePreview.vue`
- Modify: `frontend/src/views/share/ShareDiff.vue`
- Modify: `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
- Modify: `frontend/src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
- Modify: `frontend/src/views/share/__tests__/SharePreview.spec.js`

- [ ] **Step 1: Write failing public-access session tests**

Add tests covering:

```js
it('stores public access grant by resource and releases on pagehide', async () => { ... })
it('adds X-Access headers when a public access grant is active', async () => { ... })
```

- [ ] **Step 2: Run targeted session/unit tests to verify RED**

Run:

```powershell
npm.cmd run test -- src/composables/__tests__/usePublicAccessSession.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js --run
```

Expected: failures for missing composable/error handling.

- [ ] **Step 3: Implement public access session + ticket header wiring**

Requirements:
- unlock/heartbeat/release against new legacy public-access endpoints
- scope storage key by `share_token + resource_type + resource_id`
- `releaseOnPageHide()` uses `sendBeacon()` first
- `shareResourceTickets.js` forwards access headers when session active

- [ ] **Step 4: Implement share-view public-browse gating**

Requirements:
- `ShareProject.vue` handles `resource_password_required`, `login_required`, `group_required`
- `ShareFile.vue` / `SharePreview.vue` / `ShareDiff.vue` handle file-level public access errors
- keep existing managed share-token password flow intact
- no raw source exposure; runtime preview remains interactive

- [ ] **Step 5: Re-run targeted share frontend tests to verify GREEN**

Run:

```powershell
npm.cmd run test -- src/composables/__tests__/usePublicAccessSession.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js --run
```

Expected: pass.

---

## Task 6: Full verification and docs sync

**Files:**
- Modify: `docs/frontend-browser-resource-protocol.md`
- Modify: `docs/superpowers/specs/2026-07-05-public-browse-access-dialog-and-runtime-grant-design.md`
- Modify: `docs/superpowers/plans/2026-07-05-public-browse-access-dialog-and-runtime-grant.md`

- [ ] **Step 1: Run targeted backend verification suite**

```powershell
python -m pytest backend/tests/test_access_control_api.py backend/tests/test_resource_access_grant_service.py backend/tests/test_share.py backend/tests/test_share_resource_tickets.py -q
```

- [ ] **Step 2: Run targeted frontend verification suite**

```powershell
npm.cmd run test -- src/utils/__tests__/resourceAccessForm.spec.js src/composables/__tests__/usePublicAccessSession.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TokenManager.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js --run
```

- [ ] **Step 3: Run frontend build**

```powershell
npm.cmd run build
```

- [ ] **Step 4: Verify LAN services still respond after changes**

```powershell
Invoke-WebRequest -UseBasicParsing http://10.108.80.128:8000/api/v1/tracking/config
Invoke-WebRequest -UseBasicParsing http://10.108.80.128:3000/
```

- [ ] **Step 5: Update docs with exact results and remaining optional improvements**

Record:
- tests/build outputs
- whether legacy public browse now supports tab-scoped password invalidation
- any remaining follow-up items (for example dedicated login redirect polish)

---

## Self-Review

- Spec coverage:
  - admin public-browse editors: Tasks 1, 3
  - legacy public runtime grant: Tasks 2, 5
  - restriction detail dialog: Task 4
  - verification/docs: Task 6
- Placeholder scan:
  - No TODO/TBD placeholders.
- Type consistency:
  - Admin policy payload uses merged `allow_download`
  - File scope supports `inherit`; project scope does not
  - Legacy public runtime errors use `resource_password_required`
- User constraint:
  - No commit/reset/clean/push steps.

## Execution Update (2026-07-05 16:05 CST)

Status:

- All checklist items in Tasks 1-6 are complete.
- The checkbox steps above are retained as the original execution plan/history.

Delivered summary:

- Task 1 complete: admin access-control API now supports group listing, merged `allow_download`, password set/clear, and `has_password`.
- Task 2 complete: legacy public browse now has resource-scoped runtime grants plus ticket validation support.
- Task 3 complete: project/file public-browse dialogs are wired in `ProjectDetail.vue`.
- Task 4 complete: `TokenManager.vue` now uses a modal-based restriction detail view.
- Task 5 complete: legacy public share pages now use `usePublicAccessSession.js` and merge public-access headers into ticket requests.
- Task 6 complete: backend verification, frontend verification, frontend build, LAN verification, and docs sync have all been run.

Verification record:

### Backend

```powershell
python -m pytest backend/tests/test_access_control_api.py backend/tests/test_resource_access_grant_service.py backend/tests/test_share.py backend/tests/test_share_resource_tickets.py -q
```

Result: `35 passed`

### Frontend

```powershell
npm.cmd run test -- src/utils/__tests__/resourceAccessForm.spec.js src/composables/__tests__/usePublicAccessSession.spec.js src/utils/__tests__/shareResourceTickets.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TokenManager.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js --run
```

Result: `8 passed` test files, `90 passed` tests

### Frontend Build

```powershell
npm.cmd run build
```

Result:

- success
- `1820 modules transformed`
- `built in 4.55s`

### LAN Verification

```powershell
Invoke-WebRequest -UseBasicParsing http://10.108.80.128:8000/api/v1/tracking/config
Invoke-WebRequest -UseBasicParsing http://10.108.80.128:3000/
```

Result:

- backend `200 OK`
- frontend `200 OK`

Optional follow-up:

- Add a dedicated `ShareDiff.vue` regression for public-access session/header wiring.
- If needed, run one more browser-side live smoke test against the LAN instance for full public project -> preview -> diff navigation.
