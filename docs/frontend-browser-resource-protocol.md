# Frontend Browser Resource Protocol

Updated: 2026-07-05 18:36 CST

## 1. Goal

This document defines the frontend contract for any resource that the browser loads directly, especially under share/public-browse routes.

The current protocol has four goals:

1. Centralize browser resource URL construction.
2. Keep managed share-password grants and legacy public-browse password grants separate.
3. Keep browser-native preview/download requests behind short-lived tickets instead of exposing long-lived credentials.
4. Preserve interactive runtime HTML preview without exposing raw uploaded HTML as the preview response body.

## 2. Protocol Layers

### 2.1 Business APIs

Business APIs are called from `frontend/src/api/*` with `fetch`/`axios`.

Typical examples:

- `/api/v1/projects`
- `/api/v1/settings`
- `/api/v1/access-control/*`

### 2.2 Browser-Native Resources

Browser-native resources are loaded by elements such as:

- `<img src>`
- `<iframe src>`
- `<video src>`
- `<a href>`
- `window.open(...)`

These requests cannot rely on custom auth headers, so they must use centralized URL helpers plus short-lived tickets.

### 2.3 Share/Public Route Shell

Frontend share/public page routes are centralized in:

- `frontend/src/utils/shareRoute.js`

Browser resource URLs are centralized in:

- `frontend/src/utils/resourceUrl.js`
- `frontend/src/utils/shareResourceTickets.js`

The view layer must not manually concatenate `/api/v1/files/...`, `/api/v1/share/...`, or `/s/...` templates.

## 3. Runtime Session Types

### 3.1 Managed Share Session

Managed share tokens continue to use the existing share-password runtime session:

- composable: `frontend/src/composables/useShareSession.js`
- headers: `X-Share-Tab-Id`, `X-Share-Grant`
- lifecycle:
  - unlock after password entry
  - heartbeat while active
  - release on `pagehide`

`releaseOnPageHide()` first uses `navigator.sendBeacon()` and falls back to `fetch(..., keepalive: true)`.

### 3.2 Legacy Public-Browse Access Session

Legacy public browse under `/s/:token` now has its own resource-scoped runtime session:

- composable: `frontend/src/composables/usePublicAccessSession.js`
- unlock endpoint: `POST /api/v1/share/{share_token}/public-access/unlock`
- heartbeat endpoint: `POST /api/v1/share/{share_token}/public-access/grant/heartbeat`
- release endpoint: `POST /api/v1/share/{share_token}/public-access/grant/release`
- headers: `X-Access-Tab-Id`, `X-Access-Grant`

Key rules:

- the storage key is scoped by `share_token + resource_type + resource_id`
- closing the protected tab invalidates the password grant
- reopening the page requires password entry again
- file-level unlock can inherit project-level policy; backend resolves the effective policy scope
- project-level public unlock may omit `resource_id`; backend infers the current project id

## 4. Resource Tickets

Browser-native preview/download/page requests still use short-lived resource tickets.

Frontend entry point:

- `frontend/src/utils/shareResourceTickets.js`

Current behavior:

- if a managed share session is active, ticket requests forward `X-Share-*`
- if a legacy public-access session is active, ticket requests forward `X-Access-*`
- preview/download/page/asset URLs consume the short-lived ticket instead of raw long-lived credentials

## 5. Access-Control Semantics

### 5.1 Admin Resource Policy Editing

Admin-side public-browse policy editing is exposed through:

- `frontend/src/api/accessControl.js`
- `frontend/src/utils/resourceAccessForm.js`
- `frontend/src/views/admin/ProjectDetail.vue`

Supported policy fields:

- `visibility`
- `allow_preview`
- `allow_diff`
- `allow_versions`
- merged `allow_download`
- `password`
- `clear_password`
- `password_hint`
- `group_codes`

Project scope does not allow `inherit`.
File scope does allow `inherit`.

### 5.2 Managed Share vs Public-Browse Decoupling

The permission split is now strict:

- **managed share links** only use share-login, share-password, share action flags, and share quotas
- **legacy public browse** only uses resource public-browse visibility, public-browse action flags, and `X-Access-*` runtime grants
- managed share requests no longer inherit resource `visibility`, group requirements, or public-browse password requirements at runtime

### 5.3 Legacy Public Route Errors

Frontend share/public pages treat backend errors as follows:

- `share_password_required`: managed share token password required
- `resource_password_required`: legacy public resource password required
- `login_required`: login required before access
- `group_required`: logged-in user lacks required group
- `action_forbidden`: action blocked by policy flags

## 6. HTML Runtime Preview Boundary

HTML preview must remain interactive and must not expose the raw uploaded HTML source directly as the preview payload.

Current boundary:

- frontend renders runtime preview in an iframe
- backend serves a translated runtime preview document
- preview remains clickable / interactive
- diff UI uses bounded semantic snippets rather than dumping full uploaded HTML source

This means frontend obfuscation is not treated as the security boundary. The actual boundary remains:

- backend authorization
- tab-scoped grants
- short-lived tickets
- runtime-preview translation layer

## 7. Integration Boundaries

The intended responsibility split is:

- `src/api/*`: business APIs
- `resourceUrl.js`: browser resource URLs
- `shareRoute.js`: frontend page routes
- `useShareSession.js`: managed share password lifecycle
- `usePublicAccessSession.js`: legacy public resource-password lifecycle
- `shareResourceTickets.js`: ticket request + short-lived ticket cache

Components should consume these helpers rather than re-implementing protocol details.

## 8. Sync Update (2026-07-05 18:36 CST)

- [x] Admin public-browse dialogs are implemented for project and file scope.
- [x] TokenManager now uses a compact restriction summary plus a read-only detail dialog.
- [x] Legacy public browse now supports resource-scoped runtime password grants.
- [x] Closing a password-protected public-browse tab invalidates the current password grant and requires re-entry on reopen.
- [x] Ticket issuance now supports both managed share grants and legacy public-access grants.
- [x] Runtime HTML preview remains interactive and no longer relies on returning raw uploaded HTML as the preview response.
- [x] Managed share links are now fully independent from public-browse visibility and action policy at runtime.
- [x] Share-token create/update now canonicalize `policy_mode` to `override_with_token_policy`.

## 9. Verification Record

### Backend

Command:

```powershell
python -m pytest backend/tests/test_access_control_api.py backend/tests/test_resource_access_grant_service.py backend/tests/test_share.py backend/tests/test_share_resource_tickets.py backend/tests/test_share_tokens_api.py backend/tests/security/test_phase1_access_control_regressions.py -q
```

Result:

- `62 passed`

### Frontend

Command:

```powershell
npm.cmd run test -- src/utils/__tests__/resourceAccessForm.spec.js src/utils/__tests__/shareAccess.spec.js src/utils/__tests__/shareTokenForm.spec.js src/composables/__tests__/usePublicAccessSession.spec.js src/utils/__tests__/shareResourceTickets.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TokenManager.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js --run
```

Result:

- `10 passed` test files
- `102 passed` tests

### Frontend Build

Command:

```powershell
npm.cmd run build
```

Result:

- Vite build succeeded
- `1820 modules transformed`
- `built in 4.68s`

### LAN Verification

- Not re-run in this permission-decoupling pass.
- Previous LAN startup verification from `2026-07-05 16:05 CST` remains documented in earlier progress notes.

## 10. Optional Follow-Up

- Add a dedicated automated test for `ShareDiff.vue` public-access session wiring.
- If needed, run an additional browser-side smoke test for legacy public project -> file -> preview -> diff navigation on the live LAN instance.
