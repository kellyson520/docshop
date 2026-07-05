# HTTP/HTTPS Preview, Tracking Ping, and Security Header Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **User constraint:** Do not commit, push, reset, clean, or otherwise mutate git history.

**Goal:** Make runtime HTML preview, tracking ping, and security headers automatically adapt to HTTP vs HTTPS so LAN/HTTP deployments work without browser blocking, while HTTPS keeps strict protections.

**Architecture:** Introduce one shared request-scheme helper in backend, move tracking identity bootstrap to `/tracking/config` + browser storage, and let security headers only emit strict cross-origin transport policies for trusted HTTPS requests. Remove nginx-level CSP/COOP/CORP overrides so per-route application headers control runtime HTML preview correctly.

**Tech Stack:** FastAPI, Starlette middleware, SQLAlchemy, Vue/Vitest utility tests, pytest, nginx.

---


## Progress Update (2026-07-05 19:07)

- [x] Added protocol-aware regressions before implementation
  - Backend red tests confirmed for HTTP HSTS/COOP/CORP, cookie `secure`, and `/tracking/config` identifiers.
  - Frontend red tests confirmed for storage bootstrap and no-id no-ping fallback.
- [x] Implemented HTTP/HTTPS auto compatibility
  - Added `backend/app/utils/request_scheme.py` and reused it in `security_headers.py` + `tracking.py`.
  - `/api/v1/tracking/config` now returns `device_id` / `session_id` from request state or cookie fallback.
  - `frontend/src/utils/trackingClient.js` now persists identifiers into storage, prefers storage over cookies, and suppresses id-less beacons.
  - `backend/nginx.conf` no longer overrides app-level CSP / COOP / CORP globally, so runtime HTML preview headers can take effect.
- [x] Verification completed
  - `python -m pytest backend/tests/test_security_headers.py backend/tests/test_tracking_middleware.py backend/tests/test_public_tracking_runtime.py -q` -> `55 passed`
  - `python -m pytest backend/tests/test_security_headers.py backend/tests/test_tracking_middleware.py backend/tests/test_tracking.py backend/tests/test_public_tracking_runtime.py -q` -> `131 passed`
  - `python -m pytest test/test_tracking_ping.py -q` -> `16 passed`
  - `npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js --run` -> `9 passed`
  - `npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js --run` -> `4 passed` files, `51 passed` tests
  - `npm.cmd run build` -> Vite production build succeeded (`1820 modules transformed`, built in `4.62s`)
- [x] Final verification refresh
  - `python -m pytest backend/tests/test_security_headers.py backend/tests/test_tracking_middleware.py backend/tests/test_tracking.py backend/tests/test_public_tracking_runtime.py test/test_tracking_ping.py -q` -> `147 passed`
  - `npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js --run` -> `4 passed` files, `51 passed` tests
  - `npm.cmd run build` -> success (`1820 modules transformed`, built in `4.62s`)
- [x] Effective behavior after fix
  - HTTP mode omits `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, and HSTS to avoid ignored warnings on untrusted origins.
  - HTTPS mode keeps strict transport isolation and secure tracking cookies.
  - Runtime HTML preview is no longer blocked by nginx-wide `script-src 'self'` when the app emits preview-specific CSP.

## File Structure

### Backend create

- `backend/app/utils/request_scheme.py`
  - Detect effective request scheme from `X-Forwarded-Proto` or request URL.
- `backend/tests/test_public_tracking_runtime.py`
  - Regression tests for `/api/v1/tracking/config` returning reusable identifiers.

### Backend modify

- `backend/app/middlewares/security_headers.py`
  - Emit COOP/CORP/HSTS only for HTTPS requests; keep preview-specific CSP behavior.
- `backend/app/middlewares/tracking.py`
  - Set cookie `secure` dynamically from actual request scheme.
- `backend/app/routers/tracking_ping.py`
  - Return `device_id` and `session_id` from config endpoint.
- `backend/tests/test_security_headers.py`
  - Add scheme-aware coverage for HTTP vs HTTPS headers.
- `backend/tests/test_tracking_middleware.py`
  - Add scheme-aware cookie assertions.
- `backend/nginx.conf`
  - Remove global CSP / COOP / CORP overrides that break runtime preview.

### Frontend modify

- `frontend/src/utils/trackingClient.js`
  - Persist tracking identifiers from config, read storage first, and avoid ping when ids are absent.
- `frontend/src/utils/__tests__/trackingClient.spec.js`
  - Cover storage bootstrap, cookie-unreadable HTTPOnly flow, and no-id no-ping fallback.

---

## Task 1: Add failing backend tests for protocol-aware security headers

**Files:**
- Modify: `backend/tests/test_security_headers.py`

- [ ] **Step 1: Add helper support for request scheme and forwarded proto**

```python
def _create_mock_request(*, scheme="http", forwarded_proto=None):
    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/test"
    mock_request.url.scheme = scheme
    mock_request.headers = {}
    if forwarded_proto is not None:
        mock_request.headers["x-forwarded-proto"] = forwarded_proto
    return mock_request
```

- [ ] **Step 2: Add failing HTTP assertions**

```python
@pytest.mark.asyncio
async def test_http_request_omits_coop_corp_and_hsts():
    middleware = SecurityHeadersMiddleware(app=MagicMock())
    with patch("app.middlewares.security_headers.settings") as mock_settings:
        mock_settings.is_production.return_value = True
        response = await _call_middleware(middleware, scheme="http")

    assert "Cross-Origin-Opener-Policy" not in response.headers
    assert "Cross-Origin-Resource-Policy" not in response.headers
    assert "Strict-Transport-Security" not in response.headers
```

- [ ] **Step 3: Add failing HTTPS assertions**

```python
@pytest.mark.asyncio
async def test_https_request_keeps_coop_corp_and_hsts():
    middleware = SecurityHeadersMiddleware(app=MagicMock())
    with patch("app.middlewares.security_headers.settings") as mock_settings:
        mock_settings.is_production.return_value = True
        response = await _call_middleware(middleware, scheme="https")

    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert "Strict-Transport-Security" in response.headers
```

- [ ] **Step 4: Run the targeted backend test file and confirm failure**

Run:

```powershell
python -m pytest backend/tests/test_security_headers.py -q
```

Expected: FAIL before implementation because middleware currently always emits COOP/CORP and production HSTS.

## Task 2: Add failing backend tests for tracking identifiers and cookie security

**Files:**
- Modify: `backend/tests/test_tracking_middleware.py`
- Create: `backend/tests/test_public_tracking_runtime.py`

- [ ] **Step 1: Add failing cookie assertions for HTTP vs HTTPS**

```python
assert session_cookie_calls[0].kwargs["secure"] is False
```

and

```python
@pytest.mark.asyncio
async def test_dispatch_new_session_uses_secure_cookie_for_https():
    ...
    assert session_cookie_calls[0].kwargs["secure"] is True
    assert device_cookie_calls[0].kwargs["secure"] is True
```

- [ ] **Step 2: Add failing config endpoint regression**

```python
def test_tracking_config_returns_request_state_identifiers(client, db_session):
    response = client.get("/api/v1/tracking/config")
    payload = response.json()["data"]
    assert payload["device_id"]
    assert payload["session_id"]
```

- [ ] **Step 3: Add cookie reuse regression**

```python
def test_tracking_config_reuses_existing_cookie_identifiers(client, db_session):
    client.cookies.set("device_id", "device-cookie")
    client.cookies.set("session_id", "session-cookie")
    response = client.get("/api/v1/tracking/config")
    payload = response.json()["data"]
    assert payload["device_id"] == "device-cookie"
    assert payload["session_id"] == "session-cookie"
```

- [ ] **Step 4: Run targeted backend tests and confirm failure**

Run:

```powershell
python -m pytest backend/tests/test_tracking_middleware.py backend/tests/test_public_tracking_runtime.py -q
```

Expected: FAIL before implementation because cookies use `settings.is_production()` and config does not return identifiers.

## Task 3: Add failing frontend tests for storage bootstrap and no-id no-ping fallback

**Files:**
- Modify: `frontend/src/utils/__tests__/trackingClient.spec.js`

- [ ] **Step 1: Update test deps to include storage-backed ids from config**

```js
const deps = makeDeps({
  enable_tracking: true,
  enable_device_tracking: true,
  enable_location_tracking: false,
  device_id: 'visitor-1',
  session_id: 'session-1',
})
```

- [ ] **Step 2: Add failing storage bootstrap regression**

```js
it('persists identifiers from tracking config and reuses them for page views', async () => {
  const { initTracking, sendPageViewTracking } = await loadTrackingClient()
  const deps = makeDeps({ enable_tracking: true, device_id: 'visitor-9', session_id: 'session-9' }, '')

  await initTracking(deps)
  deps.beacons.length = 0
  sendPageViewTracking(deps)
  const payload = await beaconJson(deps.beacons[0])
  expect(payload.device_id).toBe('visitor-9')
  expect(payload.session_id).toBe('session-9')
})
```

- [ ] **Step 3: Replace the old unreadable-cookie expectation with a no-id no-ping regression**

```js
it('does not send a page-view beacon when config and cookies both lack identifiers', async () => {
  const { initTracking, sendPageViewTracking } = await loadTrackingClient()
  const deps = makeDeps({ enable_tracking: true, enable_device_tracking: true, enable_location_tracking: false }, '')

  await initTracking(deps)
  deps.beacons.length = 0
  const sent = sendPageViewTracking(deps)

  expect(sent).toBe(false)
  expect(deps.beacons).toHaveLength(0)
})
```

- [ ] **Step 4: Run the targeted frontend test and confirm failure**

Run:

```powershell
npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js --run
```

Expected: FAIL before implementation because identifiers are cookie-only and page view still sends beacons without ids.

## Task 4: Implement minimal backend compatibility changes

**Files:**
- Create: `backend/app/utils/request_scheme.py`
- Modify: `backend/app/middlewares/security_headers.py`
- Modify: `backend/app/middlewares/tracking.py`
- Modify: `backend/app/routers/tracking_ping.py`
- Modify: `backend/nginx.conf`

- [ ] **Step 1: Add shared request-scheme helper**

```python
from fastapi import Request


def is_https_request(request: Request | None) -> bool:
    if request is None:
        return False
    forwarded = str(request.headers.get("x-forwarded-proto", "")).split(",")[0].strip().lower()
    if forwarded in {"http", "https"}:
        return forwarded == "https"
    return str(getattr(request.url, "scheme", "") or "").lower() == "https"
```

- [ ] **Step 2: Use the helper in tracking middleware cookie writes**

```python
secure_cookie = is_https_request(request)
response.set_cookie(..., secure=secure_cookie)
```

- [ ] **Step 3: Return `device_id` and `session_id` from `/tracking/config`**

```python
return success_response({
    "enable_tracking": ...,
    "device_id": getattr(request.state, "device_id", None) or request.cookies.get("device_id"),
    "session_id": getattr(request.state, "session_id", None) or request.cookies.get("session_id"),
})
```

- [ ] **Step 4: Emit COOP/CORP/HSTS only for HTTPS requests**

```python
is_https = is_https_request(request)
if is_https:
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
if settings.is_production() and is_https:
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
```

- [ ] **Step 5: Remove nginx global CSP / COOP / CORP override lines**

Delete:

```nginx
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header Cross-Origin-Resource-Policy "same-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; ..." always;
```

- [ ] **Step 6: Run targeted backend tests and make them pass**

Run:

```powershell
python -m pytest backend/tests/test_security_headers.py backend/tests/test_tracking_middleware.py backend/tests/test_public_tracking_runtime.py -q
```

Expected: PASS.

## Task 5: Implement minimal frontend tracking compatibility changes

**Files:**
- Modify: `frontend/src/utils/trackingClient.js`
- Modify: `frontend/src/utils/__tests__/trackingClient.spec.js`

- [ ] **Step 1: Read identifiers from storage first, cookie second**

```js
function buildTrackingIdentifiers({ documentObj = document, localStorageObj, sessionStorageObj } = {}) {
  const deviceId = localStorageObj?.getItem?.(TRACKING_DEVICE_STORAGE_KEY) || getCookie('device_id', documentObj)
  const sessionId = sessionStorageObj?.getItem?.(TRACKING_SESSION_STORAGE_KEY) || getCookie('session_id', documentObj)
  ...
}
```

- [ ] **Step 2: Persist identifiers returned by config**

```js
function persistTrackingIdentifiers(config, { localStorageObj, sessionStorageObj } = {}) {
  if (config?.device_id) localStorageObj?.setItem?.(TRACKING_DEVICE_STORAGE_KEY, config.device_id)
  if (config?.session_id) sessionStorageObj?.setItem?.(TRACKING_SESSION_STORAGE_KEY, config.session_id)
}
```

- [ ] **Step 3: Bootstrap storage during `initTracking()` and block id-less page-view pings**

```js
persistTrackingIdentifiers(config, { localStorageObj, sessionStorageObj })
const identifiers = buildTrackingIdentifiers({ documentObj, localStorageObj, sessionStorageObj })
if (!identifiers.device_id && !identifiers.session_id) return false
```

- [ ] **Step 4: Run the targeted frontend test and make it pass**

Run:

```powershell
npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js --run
```

Expected: PASS.

## Task 6: Final verification and documentation sync

**Files:**
- Modify: `docs/superpowers/plans/2026-07-05-http-https-preview-tracking-compat.md`

- [ ] **Step 1: Run expanded backend verification**

```powershell
python -m pytest backend/tests/test_security_headers.py backend/tests/test_tracking_middleware.py backend/tests/test_tracking.py backend/tests/test_public_tracking_runtime.py -q
```

Expected: PASS.

- [ ] **Step 2: Run expanded frontend verification**

```powershell
npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js --run
```

Expected: PASS.

- [ ] **Step 3: Run frontend production build**

```powershell
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 4: Sync execution results into this plan file**

Document:
- Which tests passed
- That HTTP mode omits COOP/CORP/HSTS
- That HTTPS mode keeps strict transport isolation
- That runtime HTML preview is no longer broken by nginx global CSP overrides
