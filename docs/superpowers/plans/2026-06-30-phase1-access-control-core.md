# Phase 1 Access Control Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. User override: work directly on `master`; do not commit, push, reset, clean, or otherwise mutate git history.

**Goal:** Build the first usable access-control core for DocShop: persistent password-gated share access, login/group-based resource policies, unified server-side authorization decisions, and file/share preview-download anti-bypass enforcement.

**Architecture:** Backend-first delivery. Add additive SQLAlchemy models for groups and resource access policy, centralize authorization in a new `access_control_service`, and make `/api/v1/files/*` plus `/api/v1/share/*` call the same decision layer. Share password unlock uses a short-lived signed cookie grant so browser-native preview/download requests can participate without adding a frontend resource-ticket protocol yet.

**Tech Stack:** FastAPI, SQLAlchemy, signed cookies/HMAC, pytest; existing Vue share views only for minimal unlock flow wiring if backend errors require it.

---

## File Structure

### Backend create

- `backend/app/models/user_group.py`
  - Defines `UserGroup` and `UserGroupMember`.
  - Keeps group identity and membership separate from `User`.

- `backend/app/models/resource_access_policy.py`
  - Defines `ResourceAccessPolicy` and `ResourceAccessGroup`.
  - Stores per-resource visibility mode plus action-level flags.

- `backend/app/services/access_control_service.py`
  - Defines action constants, subject/context builders, policy resolution, and unified `authorize_resource_action(...)`.

- `backend/app/services/share_access_grant_service.py`
  - Defines signed short-lived unlock grant creation/validation for password-protected shares.

- `backend/app/routers/access_control.py`
  - Admin-only endpoints for group CRUD, membership updates, and resource policy CRUD.

- `backend/tests/test_access_control_service.py`
  - Unit tests for policy resolution and allow/deny matrix.

- `backend/tests/test_access_control_api.py`
  - API tests for group/policy management.

- `backend/tests/test_share_unlock.py`
  - Tests password unlock flow, unlock cookie issuance, invalid password lockout, and share access replay.

- `backend/tests/security/test_phase1_access_control_regressions.py`
  - Cross-route security regressions for preview/page/asset/download/diff/version anti-bypass checks.

- `docs/access-control-matrix.md`
  - Human-readable matrix for `visibility x action x subject`.

### Backend modify

- `backend/app/models/__init__.py`
  - Export new models so metadata registration is predictable.

- `backend/app/models/user.py`
  - Keep `User` lean; only add relationship helpers if needed.

- `backend/app/models/share_token.py`
  - Add persistent password/login/action policy fields needed for share tokens.

- `backend/app/database.py`
  - Add additive schema update statements for new tables/columns in existing databases.

- `backend/app/services/share_token_service.py`
  - Stop treating share token checks as the full authorization layer.
  - Delegate final read decisions to `access_control_service`.

- `backend/app/deps/auth.py`
  - Keep JWT behavior, but expose helper(s) reusable by unlock-aware share flows if needed.

- `backend/app/routers/share_tokens.py`
  - Accept and update new share-token fields: `require_login`, `password`, `allow_preview`, `allow_diff`, `allow_versions`, `policy_mode`.

- `backend/app/routers/share.py`
  - Add `POST /api/v1/share/{share_token}/unlock`.
  - Enforce unified authorization on share metadata, versions, diff, preview, asset, page, and download routes.

- `backend/app/routers/files.py`
  - Replace `_assert_file_access(...)` point checks with unified action-based authorization.

- `backend/app/routers/diffs.py`
  - Route diff detail/list access through unified authorization where applicable.

- `backend/app/main.py`
  - Register `access_control.router`.

- `backend/tests/test_database.py`
  - Extend additive schema coverage for new tables/columns.

- `backend/tests/test_share.py`
  - Update share route expectations for password/login/group gating.

- `backend/tests/test_share_tokens_api.py`
  - Extend create/update API coverage for new token policy fields.

- `backend/tests/test_files.py`
  - Update preview/download/version authorization assertions.

### Frontend minimal modify (only if needed to complete unlock loop)

- `frontend/src/api/share.js`
  - Add `unlockShareAccess(token, password)` API helper.

- `frontend/src/views/share/ShareProject.vue`
  - If backend returns password-required response, show unlock UI and retry.

- `frontend/src/views/share/ShareFile.vue`
  - Same unlock retry path for file-level share page.

- `frontend/src/views/share/SharePreview.vue`
  - Same unlock retry path for preview shell so cookie-based unlock can activate browser resource loads.

---

## Task 1: Schema Foundation for Groups and Resource Policies

**Files:**
- Create: `backend/app/models/user_group.py`
- Create: `backend/app/models/resource_access_policy.py`
- Modify: `backend/app/models/share_token.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/database.py`
- Modify/Test: `backend/tests/test_database.py`
- Create: `docs/access-control-matrix.md`

- [ ] **Step 1: Write failing schema tests**

Add focused tests in `backend/tests/test_database.py` to assert:

```python
def test_init_db_adds_phase1_access_control_columns():
    init_db()
    inspector = inspect(engine)
    share_columns = {c["name"] for c in inspector.get_columns("share_tokens")}
    assert "require_login" in share_columns
    assert "password_hash" in share_columns
    assert "allow_preview" in share_columns

def test_init_db_creates_access_control_tables():
    init_db()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "user_groups" in tables
    assert "user_group_members" in tables
    assert "resource_access_policies" in tables
    assert "resource_access_groups" in tables
```

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_database.py -k "phase1_access_control or access_control_tables" -q
```

Expected before implementation: FAIL with missing tables/columns.

- [ ] **Step 2: Implement additive models**

Create `backend/app/models/user_group.py` with:

```python
class UserGroup(Base):
    __tablename__ = "user_groups"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120), unique=True, nullable=False)
    code = Column(String(80), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
    updated_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())

class UserGroupMember(Base):
    __tablename__ = "user_group_members"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String(36), ForeignKey("user_groups.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(String(30), nullable=False, default=lambda: utc_now_iso())
```

Create `backend/app/models/resource_access_policy.py` with:

```python
class ResourceAccessPolicy(Base):
    __tablename__ = "resource_access_policies"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_type = Column(String(20), nullable=False, index=True)
    resource_id = Column(String(36), nullable=False, index=True)
    visibility = Column(String(30), nullable=False, default="inherit")
    password_hash = Column(String(255), nullable=True)
    password_hint = Column(String(120), nullable=True)
    allow_preview = Column(Integer, nullable=False, default=1)
    allow_download_original = Column(Integer, nullable=False, default=1)
    allow_download_converted = Column(Integer, nullable=False, default=1)
    allow_diff = Column(Integer, nullable=False, default=1)
    allow_versions = Column(Integer, nullable=False, default=1)
```

- [ ] **Step 3: Extend `ShareToken` persistence**

Modify `backend/app/models/share_token.py` to add:

```python
require_login = Column(Integer, nullable=False, default=0)
password_hash = Column(String(255), nullable=True)
password_hint = Column(String(120), nullable=True)
allow_preview = Column(Integer, nullable=False, default=1)
allow_diff = Column(Integer, nullable=False, default=1)
allow_versions = Column(Integer, nullable=False, default=1)
policy_mode = Column(String(40), nullable=False, default="inherit_resource_policy")
```

Also update `to_dict()` to emit these fields as booleans/strings.

- [ ] **Step 4: Wire metadata and additive schema updates**

Update `backend/app/models/__init__.py` imports so the new tables register with `Base.metadata`.

Update `backend/app/database.py` `_ensure_schema_updates()` to:

```python
if inspector.has_table("share_tokens"):
    columns = {column["name"] for column in inspector.get_columns("share_tokens")}
    additive_columns = {
        "require_login": "ALTER TABLE share_tokens ADD COLUMN require_login INTEGER NOT NULL DEFAULT 0",
        "password_hash": "ALTER TABLE share_tokens ADD COLUMN password_hash VARCHAR(255)",
        "password_hint": "ALTER TABLE share_tokens ADD COLUMN password_hint VARCHAR(120)",
        "allow_preview": "ALTER TABLE share_tokens ADD COLUMN allow_preview INTEGER NOT NULL DEFAULT 1",
        "allow_diff": "ALTER TABLE share_tokens ADD COLUMN allow_diff INTEGER NOT NULL DEFAULT 1",
        "allow_versions": "ALTER TABLE share_tokens ADD COLUMN allow_versions INTEGER NOT NULL DEFAULT 1",
        "policy_mode": "ALTER TABLE share_tokens ADD COLUMN policy_mode VARCHAR(40) NOT NULL DEFAULT 'inherit_resource_policy'",
    }
```

and ensure new tables are created through `Base.metadata.create_all(...)`.

- [ ] **Step 5: Write the access-control matrix doc**

Create `docs/access-control-matrix.md` with a concise matrix like:

```markdown
| visibility | anonymous | logged-in | group-member | unlocked-share | admin |
| --- | --- | --- | --- | --- | --- |
| public | preview/download per action flags | same | same | same | allow |
| login_required | deny | allow | allow | deny | allow |
| password_required | deny unless unlock grant | deny unless unlock grant | deny unless unlock grant | allow | allow |
| groups_required | deny | deny unless member | allow | deny | allow |
```

- [ ] **Step 6: Verify schema tests pass**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_database.py -k "phase1_access_control or access_control_tables" -q
```

Expected: PASS.

---

## Task 2: Unified Authorization Service

**Files:**
- Create: `backend/app/services/access_control_service.py`
- Create: `backend/tests/test_access_control_service.py`
- Modify: `backend/app/services/share_token_service.py`

- [ ] **Step 1: Write failing authorization matrix tests**

Create `backend/tests/test_access_control_service.py` with cases like:

```python
def test_public_policy_allows_preview_for_anonymous():
    decision = authorize_resource_action(
        subject=AccessSubject.anonymous(),
        resource=AccessResource(resource_type="file", resource_id="f1", owner_id="u1"),
        action="view_preview",
        policy=build_policy(visibility="public", allow_preview=1),
    )
    assert decision.allowed is True

def test_group_policy_denies_non_member():
    decision = authorize_resource_action(
        subject=AccessSubject(user_id="u2", role="user", group_codes={"sales"}),
        resource=AccessResource(resource_type="file", resource_id="f1", owner_id="u1"),
        action="view_preview",
        policy=build_policy(visibility="groups_required", groups={"legal"}),
    )
    assert decision.allowed is False
    assert decision.reason == "group_required"
```

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_access_control_service.py -q
```

Expected before implementation: FAIL with missing module/symbols.

- [ ] **Step 2: Implement the decision layer**

Create `backend/app/services/access_control_service.py` with:

```python
ACCESS_ACTIONS = {
    "view_metadata",
    "view_preview",
    "view_page_asset",
    "view_diff",
    "view_versions",
    "download_original",
    "download_converted",
    "manage_share",
    "manage_policy",
}

@dataclass
class AccessSubject:
    user_id: str | None
    role: str | None
    group_codes: set[str]
    authenticated: bool
    share_unlocked: bool = False

@dataclass
class AccessDecision:
    allowed: bool
    reason: str
```

Implement:

- `load_user_group_codes(db, user_id)`
- `resolve_resource_policy(db, resource_type, resource_id, project_id=None)`
- `authorize_resource_action(subject, resource, action, policy, share_token=None)`
- `require_resource_action(...)` wrapper that raises `HTTPException` consistently

- [ ] **Step 3: Move share-token checks below policy checks**

Modify `backend/app/services/share_token_service.py` so it keeps:

- token expiry / counters / scope helpers

but no longer treats `assert_share_token_allowed(...)` as the final access decision for preview/download/version/diff routes.

Expected end shape:

```python
resolved = resolve_share_token(raw_token, db, action="view")
token = resolved["share_token"]
assert_share_token_allowed(token, action="view")
decision = authorize_resource_action(..., share_token=token, ...)
```

- [ ] **Step 4: Verify focused service tests**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_access_control_service.py tests/test_share_token_limits.py -q
```

Expected: PASS.

---

## Task 3: Admin APIs for Groups and Resource Policies

**Files:**
- Create: `backend/app/routers/access_control.py`
- Create: `backend/tests/test_access_control_api.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_access_control_api.py` with:

```python
def test_admin_can_create_group(client, admin_token):
    response = client.post(
        "/api/v1/access-control/groups",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Legal", "code": "legal", "description": "legal reviewers"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["code"] == "legal"

def test_admin_can_set_file_policy(client, admin_token, seeded_file):
    response = client.put(
        f"/api/v1/access-control/policies/file/{seeded_file.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"visibility": "groups_required", "group_codes": ["legal"], "allow_preview": True},
    )
    assert response.status_code == 200
    assert response.json()["data"]["visibility"] == "groups_required"
```

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_access_control_api.py -q
```

Expected before implementation: FAIL with 404/import errors.

- [ ] **Step 2: Implement admin router**

Create `backend/app/routers/access_control.py`:

```python
router = APIRouter(prefix="/api/v1/access-control", tags=["access-control"])

@router.post("/groups")
def create_group(...): ...

@router.put("/groups/{group_id}/members")
def replace_group_members(...): ...

@router.put("/policies/{resource_type}/{resource_id}")
def upsert_policy(...): ...

@router.get("/policies/{resource_type}/{resource_id}")
def get_policy(...): ...
```

Use `get_current_admin` on all endpoints.

- [ ] **Step 3: Register the router**

Modify `backend/app/main.py` imports/registration:

```python
from app.routers import access_control
app.include_router(access_control.router)
```

- [ ] **Step 4: Verify admin API tests pass**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_access_control_api.py -q
python -c "from app.main import app; print('ok')"
```

Expected: tests pass and `ok`.

---

## Task 4: Persistent Share Password Unlock and Short-Lived Grant Cookie

**Files:**
- Create: `backend/app/services/share_access_grant_service.py`
- Create: `backend/tests/test_share_unlock.py`
- Modify: `backend/app/routers/share_tokens.py`
- Modify: `backend/app/routers/share.py`

- [ ] **Step 1: Write failing unlock tests**

Create `backend/tests/test_share_unlock.py`:

```python
def test_unlock_sets_short_lived_cookie(client, password_protected_share_token):
    response = client.post(
        f"/api/v1/share/{password_protected_share_token}/unlock",
        json={"password": "OpenSesame!1"},
    )
    assert response.status_code == 200
    assert "share_access_grant" in response.headers.get("set-cookie", "")

def test_locked_share_preview_denies_without_cookie(client, password_protected_share_token, seeded_file):
    response = client.get(f"/api/v1/share/{password_protected_share_token}/files/{seeded_file.id}/preview")
    assert response.status_code == 403
    assert response.json()["detail"] == "share_password_required"
```

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_share_unlock.py -q
```

Expected before implementation: FAIL.

- [ ] **Step 2: Implement signed unlock grants**

Create `backend/app/services/share_access_grant_service.py` with:

```python
COOKIE_NAME = "share_access_grant"

def issue_share_access_grant(share_token: str, expires_in_seconds: int = 900) -> str:
    payload = {"share_token": share_token, "exp": int(time.time()) + expires_in_seconds}
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), serialized_payload, hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"

def validate_share_access_grant(raw_cookie: str | None, share_token: str) -> bool:
    ...
```

- [ ] **Step 3: Extend share-token create/update API**

Modify `backend/app/routers/share_tokens.py` create/update handlers to support:

```python
require_login = 1 if body.get("require_login") else 0
allow_preview = 1 if body.get("allow_preview", 1) else 0
allow_diff = 1 if body.get("allow_diff", 1) else 0
allow_versions = 1 if body.get("allow_versions", 1) else 0
policy_mode = str(body.get("policy_mode") or "inherit_resource_policy")
if "password" in body:
    token.password_hash = get_password_hash(str(body.get("password") or ""))
```

When the request clears password, set `password_hash = None`.

- [ ] **Step 4: Add unlock endpoint and lockout logic**

Modify `backend/app/routers/share.py`:

```python
@router.post("/{share_token}/unlock")
def unlock_share_access(...):
    if not token.password_hash:
        return success_response(data={"unlocked": True})
    if not verify_password(body["password"], token.password_hash):
        raise HTTPException(status_code=403, detail="share_password_invalid")
    response = JSONResponse(success_response(data={"unlocked": True}))
    response.set_cookie("share_access_grant", issue_share_access_grant(share_token), httponly=True, samesite="Lax")
    return response
```

Also add a tiny in-memory rate-limit window keyed by `client + share_token` in `share.py` for wrong-password bursts.

- [ ] **Step 5: Verify unlock tests and token API tests**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_share_unlock.py tests/test_share_tokens_api.py -q
```

Expected: PASS.

---

## Task 5: Route-Level Anti-Bypass Enforcement on Files and Shares

**Files:**
- Modify: `backend/app/routers/files.py`
- Modify: `backend/app/routers/share.py`
- Modify: `backend/app/routers/diffs.py`
- Modify/Test: `backend/tests/test_files.py`
- Modify/Test: `backend/tests/test_share.py`
- Create: `backend/tests/security/test_phase1_access_control_regressions.py`

- [ ] **Step 1: Write failing bypass regression tests**

Create `backend/tests/security/test_phase1_access_control_regressions.py`:

```python
def test_group_protected_file_page_asset_denies_non_member(client, seeded_group_policy_file, outsider_token):
    response = client.get(
        f"/api/v1/files/{seeded_group_policy_file.id}/pages/1",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 403

def test_password_protected_share_asset_requires_unlock_cookie(client, protected_share_token, seeded_file):
    response = client.get(
        f"/api/v1/share/{protected_share_token}/files/{seeded_file.id}/preview-assets/cover.png"
    )
    assert response.status_code == 403
```

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/security/test_phase1_access_control_regressions.py -q
```

Expected before implementation: FAIL.

- [ ] **Step 2: Replace `_assert_file_access` usages**

In `backend/app/routers/files.py`, replace direct owner-only checks with action-based checks:

```python
require_resource_action(
    db=db,
    user=current_user,
    resource_type="file",
    resource_id=doc_file.id,
    action="view_preview",
)
```

Map endpoints to actions:

- file detail -> `view_metadata`
- preview/html/text -> `view_preview`
- pages/preview-assets -> `view_page_asset`
- versions list -> `view_versions`
- diffs -> `view_diff`
- original download -> `download_original`
- converted download -> `download_converted`

- [ ] **Step 3: Apply the same mapping to share routes**

In `backend/app/routers/share.py`, after resolving share scope, call the same decision layer. The `subject` should consider:

- authenticated user from JWT if present
- validated unlock cookie
- share token flags (`require_login`, `allow_preview`, `allow_diff`, `allow_versions`, `allow_download`)

Expected pattern:

```python
subject = build_access_subject(
    db=db,
    user=current_user_or_none,
    share_unlocked=validate_share_access_grant(cookie, share_token.token),
)
require_resource_action(
    db=db,
    user=current_user_or_none,
    subject=subject,
    resource_type="file",
    resource_id=doc.id,
    project_id=project.id,
    action="view_page_asset",
    share_token=share_token,
)
```

- [ ] **Step 4: Route diff endpoints through unified authorization**

Update `backend/app/routers/diffs.py` and any file-scoped diff handlers so diff list/detail routes call `view_diff` checks before returning payloads.

- [ ] **Step 5: Verify focused backend security tests**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_access_control_service.py tests/test_share_unlock.py tests/test_files.py tests/test_share.py tests/security/test_phase1_access_control_regressions.py -q
```

Expected: PASS.

---

## Task 6: Minimal Frontend Unlock Loop (Only If Backend Contract Requires UI Handling)

**Files:**
- Modify: `frontend/src/api/share.js`
- Modify: `frontend/src/views/share/ShareProject.vue`
- Modify: `frontend/src/views/share/ShareFile.vue`
- Modify: `frontend/src/views/share/SharePreview.vue`
- Modify/Test: existing share view tests if present

- [ ] **Step 1: Add unlock API helper**

In `frontend/src/api/share.js` add:

```javascript
export function unlockShareAccess(token, password) {
  return api.post(`/share/${token}/unlock`, { password })
}
```

- [ ] **Step 2: Show unlock prompt on password-required errors**

In each share view, handle backend detail `share_password_required` by showing a password form and retrying load after unlock:

```javascript
if (err?.response?.data?.detail === 'share_password_required') {
  passwordRequired.value = true
  return
}
```

- [ ] **Step 3: Verify focused share view tests**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/views/share --run
```

Expected: PASS or, if no relevant tests exist yet, add one small regression test per changed view before implementation.

---

## Task 7: Final Phase 1 Verification

**Files:**
- No new files unless fixing failures discovered during verification.

- [ ] **Step 1: Backend verification suite**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
pytest tests/test_database.py tests/test_access_control_service.py tests/test_access_control_api.py tests/test_share_unlock.py tests/test_share_tokens_api.py tests/test_files.py tests/test_share.py tests/security/test_phase1_access_control_regressions.py -q
```

Expected: PASS.

- [ ] **Step 2: Backend import verification**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\backend
python -c "from app.main import app; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Optional frontend verification if Task 6 changed UI**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/views/share --run
npm run build
```

Expected: PASS.

- [ ] **Step 4: Final status check**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
git status --short
```

Expected: local file modifications only; do not commit.

---

## Self-Review

- Spec coverage:
  - Phase 1 user groups: Task 1 + Task 3
  - Resource access policy model: Task 1 + Task 2 + Task 3
  - Unified authorization service: Task 2
  - Persistent password gate + unlock: Task 4
  - File/share anti-bypass enforcement: Task 5
  - Audit-style matrix doc: Task 1
  - Minimal frontend unlock loop if required: Task 6
- Placeholder scan: No `TODO`, `TBD`, or deferred 鈥渋mplement later鈥?placeholders remain.
- Type consistency:
  - Visibility values are consistently `inherit`, `private`, `login_required`, `password_required`, `groups_required`, `public`.
  - Action names are consistent across service and router tasks.
  - Share cookie name is consistently `share_access_grant`.
- User override honored: no worktree, no commit, direct execution on `master`.

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

