# Share and Public Permission Full Decoupling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make public-browse permissions and managed share permissions coexist without runtime coupling.

**Architecture:** Keep legacy public browse on resource access policy and resource-scoped access grants, while making managed `ShareToken` requests resolve a share-only runtime policy. Normalize old `policy_mode` data to a single canonical independent-share mode and update admin UI copy accordingly.

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3 Composition API, Element Plus, pytest, Vitest.

---

## File Structure

### Backend modify

- `backend/app/routers/share.py`
  - Remove runtime dependence on resource public policy for managed share links
- `backend/app/routers/share_tokens.py`
  - Normalize managed share `policy_mode` to the canonical decoupled mode
- `backend/app/models/share_token.py`
  - Keep compatibility field, but update default/canonical mode if needed
- `backend/tests/test_share.py`
  - Add managed-share-vs-public-policy decoupling regressions
- `backend/tests/test_share_tokens_api.py`
  - Add/update create/update normalization expectations

### Frontend modify

- `frontend/src/utils/shareAccess.js`
  - Normalize any old share policy mode to independent mode and update UI text
- `frontend/src/utils/shareTokenForm.js`
  - Always emit the canonical independent share mode
- `frontend/src/utils/__tests__/shareTokenForm.spec.js`
  - Add/update normalization coverage
- `frontend/src/views/admin/ProjectDetail.vue`
  - Replace share policy-mode selector with fixed decoupling copy
- `frontend/src/views/admin/TokenManager.vue`
  - Replace share policy-mode selector with fixed decoupling copy
- `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`
  - Verify managed share dialog uses independent share-permission semantics
- `frontend/src/views/admin/__tests__/TokenManager.spec.js`
  - Verify managed share editor/detail summary uses independent semantics

### Docs modify

- `docs/superpowers/specs/2026-07-05-share-public-permission-full-decoupling-design.md`
- `docs/superpowers/plans/2026-07-05-share-public-permission-full-decoupling.md`
- `docs/frontend-browser-resource-protocol.md`

---

## Task 1: Backend share runtime decoupling

**Files:**
- Modify: `backend/tests/test_share.py`
- Modify: `backend/app/routers/share.py`

- [x] **Step 1: Write failing managed-share decoupling tests**

Add tests covering:

```python
def test_managed_share_token_ignores_public_file_password_policy(...):
    ...


def test_managed_share_preview_ticket_ignores_public_file_password_policy(...):
    ...
```

- [x] **Step 2: Run targeted tests to verify RED**

Run:

```powershell
python -m pytest backend/tests/test_share.py -q
```

Expected: the new managed-share decoupling tests fail because managed shares still inherit resource public policy.

- [x] **Step 3: Implement minimal runtime decoupling**

Requirements:

- managed share links return a share-only effective policy
- legacy public browse keeps resource policy behavior unchanged
- share login / share password flows remain unchanged

- [x] **Step 4: Run targeted tests to verify GREEN**

Run:

```powershell
python -m pytest backend/tests/test_share.py -q
```

Expected: pass.

---

## Task 2: Backend share-token canonical mode normalization

**Files:**
- Modify: `backend/tests/test_share_tokens_api.py`
- Modify: `backend/app/routers/share_tokens.py`
- Modify: `backend/app/models/share_token.py`

- [x] **Step 1: Write/update failing normalization tests**

Cover:

```python
def test_create_share_token_normalizes_policy_mode_to_independent(...):
    ...


def test_update_share_token_normalizes_policy_mode_to_independent(...):
    ...
```

- [x] **Step 2: Run targeted tests to verify RED**

Run:

```powershell
python -m pytest backend/tests/test_share_tokens_api.py -q
```

Expected: failures because create/update still preserve incoming inherit mode.

- [x] **Step 3: Implement minimal canonical normalization**

Requirements:

- persisted mode becomes `override_with_token_policy`
- API payload returns the canonical independent mode
- no schema migration required

- [x] **Step 4: Run targeted tests to verify GREEN**

Run:

```powershell
python -m pytest backend/tests/test_share_tokens_api.py -q
```

Expected: pass.

---

## Task 3: Frontend managed share form normalization

**Files:**
- Modify: `frontend/src/utils/__tests__/shareTokenForm.spec.js`
- Modify: `frontend/src/utils/shareAccess.js`
- Modify: `frontend/src/utils/shareTokenForm.js`

- [x] **Step 1: Write/update failing helper tests**

Cover:

```js
it('normalizes legacy inherit share policy mode to independent share mode', () => { ... })
it('always emits canonical independent share mode in mutation payloads', () => { ... })
```

- [x] **Step 2: Run targeted tests to verify RED**

Run:

```powershell
npm.cmd run test -- src/utils/__tests__/shareTokenForm.spec.js --run
```

Expected: failures because helpers still preserve inherit mode.

- [x] **Step 3: Implement helper normalization**

Requirements:

- normalize any incoming mode to `override_with_token_policy`
- update text to reflect independent share permissions

- [x] **Step 4: Run targeted tests to verify GREEN**

Run:

```powershell
npm.cmd run test -- src/utils/__tests__/shareTokenForm.spec.js --run
```

Expected: pass.

---

## Task 4: Frontend admin share dialogs copy and behavior

**Files:**
- Modify: `frontend/src/views/admin/ProjectDetail.vue`
- Modify: `frontend/src/views/admin/TokenManager.vue`
- Modify: `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`
- Modify: `frontend/src/views/admin/__tests__/TokenManager.spec.js`

- [x] **Step 1: Write/update failing admin-dialog tests**

Cover:

```js
it('shows fixed independent share-permission copy in ProjectDetail share dialog', async () => { ... })
it('shows fixed independent share-permission copy in TokenManager editor', async () => { ... })
```

- [x] **Step 2: Run targeted tests to verify RED**

Run:

```powershell
npm.cmd run test -- src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TokenManager.spec.js --run
```

Expected: failures because the old policy-mode selector still exists.

- [x] **Step 3: Implement minimal UI decoupling**

Requirements:

- remove runtime policy-mode selection from managed share dialogs
- replace it with explanatory note:
  - share permissions only affect share links
  - they do not inherit public-browse restrictions
- keep payload generation stable

- [x] **Step 4: Run targeted tests to verify GREEN**

Run:

```powershell
npm.cmd run test -- src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TokenManager.spec.js --run
```

Expected: pass.

---

## Task 5: Full verification and docs sync

**Files:**
- Modify: `docs/frontend-browser-resource-protocol.md`
- Modify: `docs/superpowers/specs/2026-07-05-share-public-permission-full-decoupling-design.md`
- Modify: `docs/superpowers/plans/2026-07-05-share-public-permission-full-decoupling.md`

- [x] **Step 1: Run targeted backend verification**

```powershell
python -m pytest backend/tests/test_share.py backend/tests/test_share_tokens_api.py -q
```

- [x] **Step 2: Run targeted frontend verification**

```powershell
npm.cmd run test -- src/utils/__tests__/shareTokenForm.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TokenManager.spec.js --run
```

- [x] **Step 3: Run focused cross-suite verification**

```powershell
python -m pytest backend/tests/test_access_control_api.py backend/tests/test_resource_access_grant_service.py backend/tests/test_share.py backend/tests/test_share_resource_tickets.py backend/tests/test_share_tokens_api.py -q
npm.cmd run test -- src/utils/__tests__/resourceAccessForm.spec.js src/utils/__tests__/shareTokenForm.spec.js src/composables/__tests__/usePublicAccessSession.spec.js src/utils/__tests__/shareResourceTickets.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TokenManager.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js --run
```

- [x] **Step 4: Run frontend build**

```powershell
npm.cmd run build
```

- [x] **Step 5: Update docs with exact outcomes**

Record:

- managed share links are now fully independent from public-browse policy
- legacy public browse still uses public-browse policy
- exact test/build outputs

---

## Self-Review

- Spec coverage:
  - runtime decoupling: Tasks 1, 5
  - canonical mode normalization: Tasks 2, 3
  - admin UI wording alignment: Task 4
  - docs and verification: Task 5
- Placeholder scan:
  - No TODO/TBD placeholders.
- Type consistency:
  - canonical managed-share mode is `override_with_token_policy`
  - legacy public runtime remains `resource_password_required`
  - managed share runtime remains `share_password_required`


## Execution Status (2026-07-05 18:36 CST)

Completed in this pass:

- managed `ShareToken` runtime policy no longer inherits public-browse resource visibility or action flags
- share-token create/update now normalizes `policy_mode` to `override_with_token_policy`
- frontend share helpers now normalize legacy modes to the canonical independent-share mode
- admin share dialogs no longer expose a runtime policy-mode selector and now explain the decoupled behavior explicitly
- security regression coverage was updated to reflect the new managed-share semantics

### Verification Outcomes

#### Backend targeted

```powershell
python -m pytest backend/tests/test_share.py::TestManagedSharePermissionDecoupling backend/tests/test_share_tokens_api.py -q
```

- `24 passed`

#### Backend focused cross-suite

```powershell
python -m pytest backend/tests/test_access_control_api.py backend/tests/test_resource_access_grant_service.py backend/tests/test_share.py backend/tests/test_share_resource_tickets.py backend/tests/test_share_tokens_api.py backend/tests/security/test_phase1_access_control_regressions.py -q
```

- `62 passed`

#### Frontend targeted

```powershell
npm.cmd run test -- src/utils/__tests__/shareTokenForm.spec.js src/utils/__tests__/shareAccess.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TokenManager.spec.js --run
```

- `4 passed` test files
- `53 passed` tests

#### Frontend focused cross-suite

```powershell
npm.cmd run test -- src/utils/__tests__/resourceAccessForm.spec.js src/utils/__tests__/shareAccess.spec.js src/utils/__tests__/shareTokenForm.spec.js src/composables/__tests__/usePublicAccessSession.spec.js src/utils/__tests__/shareResourceTickets.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TokenManager.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/views/share/__tests__/SharePreview.spec.js --run
```

- `10 passed` test files
- `102 passed` tests

#### Frontend build

```powershell
npm.cmd run build
```

- Vite build succeeded
- `1820 modules transformed`
- `built in 4.68s`
