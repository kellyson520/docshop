# Public Browse Access Dialog and Runtime Grant Design

## Context

The current admin experience has two mismatches:

1. Public-browse access control for projects/files is not surfaced in the same way as share-token permissions.
2. The share-token list renders a long inline “限制” text block instead of a focused dialog.

The user wants:

- The “限制” area in share-token management changed into a dialog-based detail view.
- Project-level and file-level **public browse** access settings aligned with share permissions.
- Public browse to support the same major controls as share permissions:
  - preview
  - diff/change
  - versions
  - download
  - password access
  - user-group access
- Password access for public browse to be **tab-scoped**: closing the tab invalidates the password grant and requires re-entry next time.
- Existing public homepage cards continue to display projects and continue to route through `/s/:token`.

## Goals

1. Add complete admin-side editors for public browse access on both projects and files.
2. Convert the share-token “限制” column into a concise summary + modal detail view.
3. Preserve the current share-page shell (`/s/:token`) while making **resource access policy** the primary authority for public browse.
4. Add a public-browse password runtime grant that is scoped to the current tab and released on page close.
5. Keep existing manual share-token flows intact; this work focuses on public browse.

## Non-Goals

- Do not replace the `/s/:token` public/share shell with a new dedicated public route system.
- Do not remove or redesign existing manual share-token capability flags.
- Do not mutate git history or commit as part of this work.

## User Constraints

- Work in `C:\Users\lihuo\Desktop\docshop`.
- No commit / push / reset / clean.
- HTML/runtime preview must remain clickable and interactive.
- Password-based public browse must expire when the protected tab is closed.

## Existing Architecture

### Public browse entry

- Homepage project cards load from `GET /api/v1/share/public-projects`.
- Cards route into `buildShareHomePath(token)` which resolves to `/s/:token`.
- `Project.share_token` is the legacy token used for these public browse routes.

### Resource policy model

`backend/app/models/resource_access_policy.py` already stores resource-level policy:

- `visibility`
- `password_hash`
- `password_hint`
- `allow_preview`
- `allow_download_original`
- `allow_download_converted`
- `allow_diff`
- `allow_versions`

`backend/app/services/access_control_service.py` already resolves and enforces:

- `inherit`
- `private`
- `public`
- `login_required`
- `password_required`
- `groups_required`

### Share runtime

`backend/app/routers/share.py` already handles:

- optional current user on share routes
- share-token password unlock
- tab-scoped share grants
- share resource tickets for preview/download/page assets

This is useful, but legacy public browse currently lacks a resource-policy password unlock flow.

## Chosen Design

### 1. Admin-side access editors

#### File settings dialog

The existing file settings dialog in `ProjectDetail.vue` will remain a modal, but it will be expanded into two sections:

1. file metadata
2. public browse access

The public browse section will expose:

- visibility
  - file: `inherit`, `private`, `public`, `password_required`, `groups_required`
- action flags
  - preview
  - diff
  - versions
  - download
- password inputs
  - password
  - clear password
  - password hint
- group selection

#### Project access dialog

A separate project-level modal will be added in `ProjectDetail.vue` for project public browse access.

It will expose the same controls except `inherit` is not valid for projects.

### 2. Share-token “限制” detail dialog

`TokenManager.vue` will stop rendering all restrictions inline.

Instead it will render:

- compact counts / summary in-table
- a `权限详情` button that opens a read-only modal

The detail modal will show:

- view/download quotas
- login requirement
- password hint / whether password exists
- preview / diff / versions / download flags
- policy mode
- expiry state

### 3. Runtime authority split

Public browse keeps the existing `/s/:token` shell, but the authority is clarified:

- **share link**: routing shell and runtime preview container
- **resource access policy**: actual authority for public browse access

For legacy public project browsing (`Project.share_token` route), access decisions are driven by resource policy.

Manual share tokens remain unchanged and keep their current permission flow.

### 4. Visibility semantics

#### Project visibility

For project-level public browse policy:

- `public`: visible and directly accessible
- `password_required`: visible on homepage, access requires password unlock
- `groups_required`: visible on homepage, access requires login + matching group
- `private`: invalid for homepage-visible public projects

Admin-side save behavior will reject or warn on the conflicting combination:

- `project.is_public == true`
- `project policy visibility == private`

#### File visibility

For file-level public browse policy:

- `inherit`: follow project
- `private`: block this file even if project shell is accessible
- `public`: always accessible under public shell
- `password_required`: requires file-level password unlock
- `groups_required`: requires file-level group membership check

### 5. Download flag normalization

The admin UI should present a **single** `download` toggle, matching share permissions.

Backend storage remains unchanged:

- `allow_download_original`
- `allow_download_converted`

Mapping rules:

- UI save `allow_download=true` => both backend flags `true`
- UI save `allow_download=false` => both backend flags `false`
- GET payload exposes a merged `allow_download`

### 6. Admin API changes

#### Existing policy read/write endpoints are extended

Continue using:

- `GET /api/v1/access-control/policies/{resource_type}/{resource_id}`
- `PUT /api/v1/access-control/policies/{resource_type}/{resource_id}`

Enhancements:

- accept `password`
- accept `clear_password`
- accept merged `allow_download`
- return merged `allow_download`
- return `has_password`
- continue returning `group_codes`

#### Group list endpoint

Add:

- `GET /api/v1/access-control/groups`

This is required so admin dialogs can render a real group selector instead of a free-text code field.

### 7. Public browse runtime password grant

Because file-level passwords may differ from project-level passwords, legacy share-tab grants keyed only by share token are not sufficient.

The design adds a separate public-browse runtime grant for legacy public routes.

#### Storage

Add a new table for resource-scoped grants, e.g. `resource_access_grants`, with:

- `id`
- `share_token`
- `resource_type`
- `resource_id`
- `tab_id`
- `grant_hash`
- `created_at`
- `last_seen_at`
- `expires_at`
- `released_at`

`share_token` is stored so grants are limited to the current legacy public shell and can be reused across project/file pages only for the exact protected resource they unlocked.

#### Runtime endpoints

Add legacy-public runtime endpoints under the existing share shell:

- `POST /api/v1/share/{share_token}/public-access/unlock`
- `POST /api/v1/share/{share_token}/public-access/grant/heartbeat`
- `POST /api/v1/share/{share_token}/public-access/grant/release`

Payload identifies the protected resource:

- `resource_type`
- `resource_id`
- `password`

Transport uses:

- `X-Access-Tab-Id`
- `X-Access-Grant`

Release also accepts JSON body for `sendBeacon()` fallback.

### 8. Share route enforcement for public browse

For legacy public routes only (`resolved.share_token` absent / legacy share shell):

- project and file actions should consult resource policy
- if policy is `password_required`, a valid resource access grant is required
- if policy is `groups_required`, authenticated user + group match are required

Manual managed share tokens keep their current share-password semantics.

### 9. Share resource tickets integration

Public-browse resource passwords must still work for browser-native resources like:

- iframe preview
- PDF pages
- preview assets
- downloads

Therefore `issueShareResourceTicket` behavior must be extended so that, for legacy public browse:

- it can validate a resource access grant
- it can issue a ticket after successful validation
- downstream preview/download endpoints can continue using ticket-based access for browser-native requests

### 10. Frontend runtime session design

Add a new composable for legacy public browse, separate from `useShareSession.js`, for example:

- `usePublicAccessSession(shareToken, resourceType, resourceId)`

Responsibilities:

- create / persist per-tab `access_tab_id`
- unlock one protected project/file resource
- heartbeat current grant
- release on `pagehide` / `beforeunload`
- expose `withAccessHeaders()`
- expose error helpers for `resource_password_required`

This composable is used only for legacy public browse routes.

### 11. Frontend share-page behavior

#### ShareProject.vue

- If project root returns `resource_password_required`, open password modal for project resource.
- If route returns `login_required` or `group_required`, render a clear access-denied message.
- Continue using the existing share shell and file list UI.

#### ShareFile.vue / SharePreview.vue / ShareDiff.vue

- If file route returns `resource_password_required`, open password modal for that file resource.
- If file route returns `login_required` or `group_required`, render access-denied message.
- When preview/download needs a ticket, include resource access headers if a public access grant is active.

### 12. UX rules

- Homepage cards still display public projects even when project visibility is `password_required` or `groups_required`.
- `private` is not allowed for a project that is still marked public on the homepage.
- Disabled actions in share/public views must remain gray and unclickable, matching the existing disabled-share behavior.
- Runtime preview must remain interactive and full-page friendly.

## Error Semantics

### Public browse API errors

- `resource_password_required`: this resource needs password unlock for the current tab
- `share_password_required`: unchanged, only for manual managed share-token passwords
- `login_required`: authentication needed
- `group_required`: logged in but user not in authorized groups
- `action_forbidden`: action disabled by access flags

## Testing Strategy

### Backend

- extend access-control API tests for:
  - merged download flag
  - password save / clear
  - group list endpoint
- add resource access grant service tests:
  - issue / validate / heartbeat / release
  - wrong resource / wrong tab / expired grant
- add legacy public share route tests:
  - project-level password_required on public project
  - file-level password_required on public project
  - groups_required returning login/group errors
  - ticket issuance with active resource access grant

### Frontend

- `ProjectDetail.spec.js`
  - file settings shows public-browse controls
  - project public-browse dialog loads/saves policy
  - merged download toggle maps correctly
- `TokenManager.spec.js`
  - “限制” column opens read-only detail dialog
- share view tests
  - project/file resource password modal flow
  - release-on-pagehide for public access grant
  - group/login denial rendering
  - resource-ticket requests include access headers when active

## Risks and Mitigations

1. **Conflict between legacy public browse and manual share-token password flow**
   - Mitigation: scope new runtime grant to legacy public browse only.

2. **File-level password different from project-level password**
   - Mitigation: resource grants are keyed to resource type/id, not just the share token.

3. **Browser-native preview/download requests cannot send custom headers**
   - Mitigation: extend ticket issuance instead of exposing raw protected URLs.

4. **Admin UI complexity in ProjectDetail.vue**
   - Mitigation: isolate API/form helpers and, where useful, split repeated dialog sections into focused helper logic.

## Open Decisions Resolved

- Share-token list restriction view becomes a dialog: **yes**
- Public browse settings apply to both file and project: **yes**
- Public project cards stay visible for password/group protected resources: **yes**
- Public browse continues to use `/s/:token`: **yes**
- Password unlock is tab-scoped and expires on tab close: **yes**

## Implementation Summary

This work extends the existing access-control model into a first-class admin-edited public browse policy, keeps the current public browse shell stable, and adds a separate resource-scoped runtime password grant for legacy public project flows so project-level and file-level protected browse remains secure without exposing raw browser-accessible content.

## Implementation Sync (2026-07-05 16:05 CST)

### Delivered

- Backend admin access-control API now supports:
  - `GET /api/v1/access-control/groups`
  - merged `allow_download`
  - `password` / `clear_password`
  - `has_password`
- Backend legacy public browse now supports:
  - `POST /api/v1/share/{share_token}/public-access/unlock`
  - `POST /api/v1/share/{share_token}/public-access/grant/heartbeat`
  - `POST /api/v1/share/{share_token}/public-access/grant/release`
- Ticket issuance for browser-native share resources now accepts legacy public-access runtime grants through `X-Access-Tab-Id` / `X-Access-Grant`.
- `ProjectDetail.vue` now exposes project-level and file-level public-browse policy dialogs.
- `TokenManager.vue` now uses a compact restriction summary plus a read-only detail dialog.
- Legacy public share views now consume `usePublicAccessSession.js` for resource-password unlock, heartbeat, and page-close release.

### Final Behavioral Clarifications

- Project-level legacy public unlock may send `resource_type='project'` with an empty `resource_id`; backend infers the current project id.
- When a file inherits a project-level password policy, frontend may still unlock from the file route; backend resolves the effective policy scope before issuing the grant.
- Public-access page-close invalidation is implemented at the share page level (`ShareProject.vue`, `ShareFile.vue`, `SharePreview.vue`, `ShareDiff.vue`) instead of moving the logic into `ShareLayout.vue`.
- Managed share-token password flow remains unchanged and separate from legacy public-browse resource-password flow.

### Verification

Backend:

```powershell
python -m pytest backend/tests/test_access_control_api.py backend/tests/test_resource_access_grant_service.py backend/tests/test_share.py backend/tests/test_share_resource_tickets.py -q
```

Result: `35 passed`

Frontend:

```powershell
npm.cmd run test -- src/utils/__tests__/resourceAccessForm.spec.js src/composables/__tests__/usePublicAccessSession.spec.js src/utils/__tests__/shareResourceTickets.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TokenManager.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js --run
```

Result: `8 passed` test files, `90 passed` tests

Build:

```powershell
npm.cmd run build
```

Result: Vite build succeeded with `1820 modules transformed`

LAN:

- `http://10.108.80.128:8000/api/v1/tracking/config` -> `200 OK`
- `http://10.108.80.128:3000/` -> `200 OK`

### Remaining Optional Improvements

- Add a dedicated automated regression for `ShareDiff.vue` public-access session/header wiring.
- Add a browser-level smoke test for the complete legacy public flow if a visual verification pass is required.
