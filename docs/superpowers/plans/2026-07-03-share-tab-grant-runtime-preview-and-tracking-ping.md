# Share Tab Grant銆丷untime HTML Preview 涓?Tracking Ping 淇 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **User constraint:** Do not commit, push, reset, clean, or otherwise mutate git history.

**Goal:** 璁╁甫瀵嗙爜鍒嗕韩鏀逛负 tab 绾цВ閿佸苟鍦ㄥ叧 tab 鍚庡け鏁堬紝鎶婂垎浜祫婧愰摼鎺ョ粺涓€鏀跺彛鍒扮煭鏃?ticket锛屼繚鐣?HTML 浜掑姩浣嗕笉鍐嶇洿鎺ヨ繑鍥炲師濮嬩笂浼?HTML锛屽悓鏃朵慨澶嶉灞?tracking ping 429銆?

**Architecture:** 鍚庣鏂板 DB-backed 鐨?share tab grant 涓?share resource ticket 灞傦紝骞跺紩鍏ュ鐢ㄥ湪 `/files/*` 涓?`/share/*` 鐨?runtime HTML preview service銆傚墠绔柊澧?share session composable锛岀粺涓€瑙ｉ攣銆乭eartbeat銆乺elease 鍜?ticket 鐢宠锛涘垎浜〉榛樿鍚?tab 瀵艰埅锛屼笉鍐嶉粯璁よ烦鏂?tab锛泃racking 浠呯Щ闄ゅ垵濮嬪寲闃舵鐨勯噸澶?`page_path` 涓婃姤銆?

**Tech Stack:** FastAPI銆丼QLAlchemy additive schema updater銆乂ue 3 Composition API銆丄xios銆乂itest銆乸ytest銆?

---

## Progress Update (2026-07-04)

- [x] Task 1 `tracking ping` 429 fix implemented and verified
  - frontend: `frontend/src/utils/trackingClient.js`
  - tests: `frontend/src/utils/__tests__/trackingClient.spec.js`, `test/test_tracking_ping.py`
- [x] Task 2 backend `share tab grant` model/service implemented and verified
  - files: `backend/app/models/share_tab_grant.py`, `backend/app/services/share_tab_grant_service.py`
- [x] Task 3 share session / header-grant rollout implemented and verified
  - frontend regression on `SharePreview.spec.js` fixed on 2026-07-04
  - backend direct-call regression in `backend/tests/test_share.py` updated to current request signature on 2026-07-04
- [x] Task 4 `share resource ticket` backend service, route wiring, and frontend URL wiring verified by targeted suites
- [x] Task 5 `runtime HTML preview` implemented and verified by backend rich-preview tests, share preview tests, FileViewer tests, and production build
- [x] Task 6 protocol/docs final sync completed across related docs/plans/specs
- [x] Task 7 end-to-end targeted verification completed

## Progress Update (2026-07-04 23:10)

- [x] LAN dev services restarted / verified after code changes
  - backend: `0.0.0.0:8000`, PID `17712`, health check `http://10.108.80.129:8000/api/v1/tracking/config` returned `200`
  - frontend: `0.0.0.0:3000`, PID `17840`, health check `http://10.108.80.129:3000/` returned `200`
  - logs: `backend/lan-backend.out.log`, `backend/lan-backend.err.log`, `frontend/lan-frontend.out.log`, `frontend/lan-frontend.err.log`
- [x] Follow-up Task 1 fix: first SPA page-view no longer races before `initTracking()`
  - `frontend/src/utils/trackingClient.js` now gates page-view pings until tracking config/init finishes.
  - If router `afterEach()` fires early, it stores one pending page-view payload and flushes it after init ping succeeds.
  - Regression added in `frontend/src/utils/__tests__/trackingClient.spec.js`: `queues the first SPA page view until tracking init finishes`.
- [x] Follow-up Task 3 fix: password-protected share grant is released on tab close/pagehide
  - `frontend/src/composables/useShareSession.js` adds `releaseOnPageHide()` using `navigator.sendBeacon()` first and `fetch(..., keepalive: true)` fallback.
  - `frontend/src/views/share/ShareLayout.vue` registers `pagehide` and `beforeunload` listeners and removes them on unmount.
  - `backend/app/routers/share.py` release endpoint now accepts beacon-friendly JSON body fallback: `tab_id` / `grant_token`, while preserving header-based release.
  - Regression added in `frontend/src/views/share/__tests__/ShareSession.spec.js`, `frontend/src/views/share/__tests__/ShareLayout.spec.js`, and `test/test_share_grant_release.py`.
- [x] Share permission disabled-state sweep verified
  - Share actions `preview / versions / diff / download` and folder package download keep the unified gray disabled style when blocked by share permissions.
  - Existing share regressions now cover `allow_download`, `allow_preview`, `allow_diff`, and `allow_versions` disabled states.
- [x] Targeted verification completed
  - Frontend: `npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js src/views/share/__tests__ --run`
    - Result: `8 passed` test files, `66 passed` tests.
  - Backend: `python -m pytest test/test_tracking_ping.py test/test_share_grant_release.py -q`
    - Result: `17 passed`.
- [x] Remaining manual/browser verification converted to automated checks where possible
  - Password tab-close lifecycle covered by frontend/backend regressions for `pagehide`, `sendBeacon`, and JSON-body release.
  - Browser Network check completed with Playwright + Microsoft Edge: first-load `/api/v1/tracking/ping` returned `204`, `204`; no `400` / `429`.
  - HTML runtime preview path covered by backend rich-preview tests, frontend iframe tests, and production build; only optional human visual inspection remains.


## File Structure

### Backend create

- `backend/app/models/share_tab_grant.py`
  - 瀵嗙爜鍒嗕韩 tab 绾?grant 鏁版嵁妯″瀷銆?

- `backend/app/services/share_tab_grant_service.py`
  - issue / validate / heartbeat / release tab grant銆?

- `backend/app/services/share_resource_ticket_service.py`
  - issue / validate share resource ticket銆?

- `backend/app/services/html_runtime_preview_service.py`
  - HTML runtime preview 杞瘧銆佽祫婧愰噸鍐欍€佸叆鍙ｉ〉鐢熸垚銆?

- `backend/tests/test_share_tab_grant_service.py`
  - grant 鐢熷懡鍛ㄦ湡鍗曟祴銆?

- `backend/tests/test_share_resource_tickets.py`
  - resource ticket 鍗曟祴銆?

### Backend modify

- `backend/app/database.py`
  - 娉ㄥ唽鏂拌〃骞跺仛 additive schema 鏇存柊銆?

- `backend/app/models/__init__.py`
  - 瀵煎嚭 `ShareTabGrant`銆?

- `backend/app/routers/share.py`
  - unlock / heartbeat / release / resource-ticket 鎺ュ彛涓庡叏閾捐矾鏍￠獙銆?

- `backend/app/routers/files.py`
  - HTML 棰勮鏀规帴 runtime preview service銆?

- `backend/app/services/preview_manifest_service.py`
  - HTML manifest 浠?`html_native` 鍒囨崲鍒?`html_runtime`銆?

- `backend/tests/test_share_unlock.py`
  - 浠?cookie 璇箟鍒囧埌 tab grant + release銆?

- `backend/tests/test_share.py`
  - 琛ュ垎浜」鐩?鏂囦欢/涓嬭浇鍦?tab grant 涓?ticket 涓嬬殑鍥炲綊銆?

- `backend/tests/test_preview_manifest_service.py`
  - HTML manifest 鏂█鏇存柊銆?

- `backend/tests/test_files_rich_preview.py`
  - HTML 棰勮涓嶅啀鐩存帴绛変簬鍘熷鏂囦欢鍐呭銆?

### Frontend create

- `frontend/src/composables/useShareSession.js`
  - `share_tab_id`銆乬rant 瀛樺偍銆乽nlock/heartbeat/release銆乻hare headers銆?

- `frontend/src/utils/shareResourceTickets.js`
  - 璧勬簮 ticket 鐢宠涓庣煭鏃剁紦瀛樸€?

- `frontend/src/views/share/__tests__/ShareSession.spec.js`
  - share session 鐢熷懡鍛ㄦ湡涓庡悓 tab 琛屼负鍥炲綊銆?

### Frontend modify

- `frontend/src/api/client.js`
  - 鏀寔姣忔 share 璇锋眰鎸夐渶娉ㄥ叆棰濆 headers銆?

- `frontend/src/api/share.js`
  - unlock / heartbeat / release / resource-ticket API 灏佽銆?

- `frontend/src/utils/resourceUrl.js`
  - share 璧勬簮 URL 鏀规帴 `ticket` 鍙傛暟锛岃€屼笉鏄亣璁?cookie / auth_token銆?

- `frontend/src/views/share/ShareLayout.vue`
  - 鎵樼 heartbeat / release 鐢熷懡鍛ㄦ湡銆?

- `frontend/src/views/share/ShareProject.vue`
  - 缁熶竴浣跨敤 share session锛涢瑙堥粯璁ゅ悓 tab锛涗笅杞?璧勬簮鏀硅蛋 ticket銆?

- `frontend/src/views/share/ShareFile.vue`
  - 鍘婚噸 unlock 閫昏緫锛涚増鏈?涓嬭浇鏀硅蛋 ticket銆?

- `frontend/src/views/share/SharePreview.vue`
  - 鍘绘帀 `location.replace(raw html)`锛孒TML 鏀规覆鏌?runtime iframe銆?

- `frontend/src/components/file-viewer/FileViewer.vue`
  - 鏀寔 `html_runtime` manifest銆?

- `frontend/src/components/file-viewer/HtmlViewer.vue`
  - iframe 鎸囧悜 runtime entry銆?

- `frontend/src/components/file-viewer/__tests__/FileViewer.spec.js`
  - HTML viewer 鏂█鍒囧埌 runtime manifest銆?

- `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
  - 棰勮鎸夐挳榛樿鍚?tab 涓?ticket 涓嬭浇鍥炲綊銆?

- `frontend/src/views/share/__tests__/SharePreview.spec.js`
  - HTML 棰勮涓嶅啀瑁歌烦杞紝瑙ｉ攣鍚庝粛鍦?share shell 鍐呰繍琛屻€?

- `frontend/src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
  - 鐗堟湰椤佃В閿佷笌涓嬭浇 URL 鍥炲綊銆?

- `frontend/src/utils/trackingClient.js`
  - init ping 鍘绘帀 `page_path`銆?

- `frontend/src/utils/__tests__/trackingClient.spec.js`
  - tracking 鍘婚噸鍥炲綊銆?

### Docs modify

- `docs/frontend-browser-resource-protocol.md`
  - 璁板綍 share tab grant / resource ticket / runtime HTML preview 鍗忚銆?

### Cross-suite modify

- `test/test_tracking_ping.py`
  - 璁板綍鈥滃垵濮嬪寲 ping 涓嶅垱寤?page view锛宲age view 浠嶇嫭绔嬩笂鎶モ€濈殑鍥炲綊銆?

---

## Task 1: 淇 tracking/ping 棣栧睆鍙屽彂 429

**Files:**
- Modify: `frontend/src/utils/trackingClient.js`
- Modify: `frontend/src/utils/__tests__/trackingClient.spec.js`
- Modify: `test/test_tracking_ping.py`

- [x] **Step 1: 鍏堝啓鍓嶇澶辫触鐢ㄤ緥锛岄攣瀹?`initTracking()` 涓嶅簲鍐嶅甫 `page_path`**

鍦?`frontend/src/utils/__tests__/trackingClient.spec.js` 澧炲姞涓€涓槑纭尯鍒嗏€滃垵濮嬪寲 ping鈥濆拰鈥滈〉闈㈡祻瑙?ping鈥濈殑鐢ㄤ緥锛屼緥濡傦細

```js
it('sends init tracking without page_path and keeps page_path only for SPA page views', async () => {
  const deps = makeDeps({ enable_tracking: true, enable_device_tracking: true, enable_location_tracking: false })

  await initTracking(deps)
  const initPayload = await beaconJson(deps.beacons[0])
  expect(initPayload.page_path).toBeUndefined()

  sendPageViewTracking(deps)
  const pageViewPayload = await beaconJson(deps.beacons[1])
  expect(pageViewPayload.page_path).toBe('/admin/tracking')
})
```

- [x] **Step 2: 璺戝墠绔崟娴嬶紝纭褰撳墠瀹炵幇浼氬け璐?*

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/utils/__tests__/trackingClient.spec.js --run
```

Expected before implementation:  
FAIL锛屽師鍥犳槸 `initTracking()` 褰撳墠浠嶇劧鍖呭惈 `page_path`銆?

- [x] **Step 3: 鐢ㄦ渶灏忓疄鐜扮Щ闄ゅ垵濮嬪寲 ping 鐨?`page_path`**

鍦?`frontend/src/utils/trackingClient.js` 鎶婂垵濮嬪寲 payload 鏀规垚浠呬繚鐣欎細璇?璁惧淇℃伅锛?

```js
export async function initTracking({
  fetchImpl = fetch,
  navigatorObj = navigator,
  windowObj = window,
  documentObj = document,
} = {}) {
  const config = await getTrackingConfig(fetchImpl)
  if (!config?.enable_tracking) return false

  const payload = {
    ...buildTrackingIdentifiers({ documentObj }),
  }

  if (config.enable_device_tracking !== false) {
    Object.assign(payload, collectSyncDeviceData({ navigatorObj, windowObj }))
    Object.assign(payload, await collectHighEntropyDeviceData(navigatorObj))
  }
  if (config.enable_location_tracking) {
    Object.assign(payload, await collectLocation(navigatorObj))
  }

  sendTrackingBeacon(payload, { navigatorObj, fetchImpl })
  return true
}
```

- [x] **Step 4: 澧炲姞鍚庣鍥炲綊锛岀‘璁も€滄棤 `page_path` 鐨?ping 涓嶆槸 page view鈥?*

鍦?`test/test_tracking_ping.py` 琛ヤ竴涓悗绔洖褰掞紝鑰屼笉鏄慨鏀归檺娴侀€昏緫锛?

```python
@pytest.mark.asyncio
async def test_receive_ping_without_page_path_updates_session_context_only(monkeypatch):
    from app.routers import tracking_ping

    log = SimpleNamespace(raw_data=None)
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=log)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    response = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-init",
        "device_id": "visitor-init",
        "client_language": "zh-CN",
    }))

    assert response.status_code == 204
    assert db.added == []
```

- [x] **Step 5: 閲嶆柊璺戝墠鍚庣瀹氬悜鐢ㄤ緥**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/utils/__tests__/trackingClient.spec.js --run

cd C:\Users\lihuo\Desktop\docshop
pytest test/test_tracking_ping.py -q
```

Expected:  
Vitest PASS锛沺ytest PASS锛涘悗绔?`_RATE_LIMIT_SECONDS = 10` 涓嶉渶瑕佷慨鏀广€?

---

## Task 2: 寤虹珛鍚庣 Share Tab Grant 鍩虹璁炬柦

**Files:**
- Create: `backend/app/models/share_tab_grant.py`
- Create: `backend/app/services/share_tab_grant_service.py`
- Create: `backend/tests/test_share_tab_grant_service.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/database.py`

- [x] **Step 1: 鍏堝啓 grant 鐢熷懡鍛ㄦ湡澶辫触鐢ㄤ緥**

鍦?`backend/tests/test_share_tab_grant_service.py` 鍏堥攣瀹?3 涓牳蹇冨満鏅細

```python
def test_issue_and_validate_share_tab_grant(db_session):
    from app.services.share_tab_grant_service import issue_share_tab_grant, validate_share_tab_grant

    token = issue_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        ttl_seconds=45,
    )

    grant = validate_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        raw_grant=token,
    )
    assert grant is not None


def test_validate_share_tab_grant_rejects_different_tab(db_session):
    from app.services.share_tab_grant_service import issue_share_tab_grant, validate_share_tab_grant

    token = issue_share_tab_grant(db_session, share_token="share-1", tab_id="tab-a", ttl_seconds=45)

    grant = validate_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-b",
        raw_grant=token,
    )
    assert grant is None


def test_release_share_tab_grant_invalidates_future_validation(db_session):
    from app.services.share_tab_grant_service import issue_share_tab_grant, release_share_tab_grant, validate_share_tab_grant

    token = issue_share_tab_grant(db_session, share_token="share-1", tab_id="tab-a", ttl_seconds=45)
    release_share_tab_grant(db_session, share_token="share-1", tab_id="tab-a", raw_grant=token)

    assert validate_share_tab_grant(db_session, "share-1", "tab-a", token) is None
```

- [x] **Step 2: 璺戝悗绔崟娴嬶紝纭褰撳墠浠撳簱杩樻病鏈夎繖濂楄兘鍔?*

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
pytest backend/tests/test_share_tab_grant_service.py -q
```

Expected before implementation:  
FAIL锛屽洜涓烘ā鍨嬪拰 service 閮借繕涓嶅瓨鍦ㄣ€?

- [x] **Step 3: 鏂板妯″瀷銆乻chema updater 涓?service**

鍏堝畾涔夋ā鍨嬶紝鍐嶅湪 `database.py` 鐨?additive schema updater 閲岃ˉ寤鸿〃锛?

```python
class ShareTabGrant(Base):
    __tablename__ = "share_tab_grants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    share_token = Column(String(255), nullable=False, index=True)
    tab_id = Column(String(120), nullable=False, index=True)
    grant_hash = Column(String(128), nullable=False)
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    released_at = Column(DateTime, nullable=True)
```

`backend/app/services/share_tab_grant_service.py` 鎻愪緵鏄庣‘鎺ュ彛锛?

```python
def issue_share_tab_grant(db: Session, *, share_token: str, tab_id: str, ttl_seconds: int = 45) -> str: ...
def validate_share_tab_grant(db: Session, share_token: str, tab_id: str, raw_grant: str | None): ...
def heartbeat_share_tab_grant(db: Session, share_token: str, tab_id: str, raw_grant: str | None, ttl_seconds: int = 45): ...
def release_share_tab_grant(db: Session, share_token: str, tab_id: str, raw_grant: str | None) -> bool: ...
```

- [x] **Step 4: 鍐嶈ˉ heartbeat 琛屼负鐢ㄤ緥**

鍦ㄥ悓涓€涓祴璇曟枃浠惰ˉ heartbeat 缁懡鏂█锛?

```python
def test_heartbeat_extends_share_tab_grant_expiry(db_session):
    from app.services.share_tab_grant_service import (
        issue_share_tab_grant,
        validate_share_tab_grant,
        heartbeat_share_tab_grant,
    )

    token = issue_share_tab_grant(db_session, share_token="share-1", tab_id="tab-a", ttl_seconds=5)
    grant = validate_share_tab_grant(db_session, "share-1", "tab-a", token)
    before = grant.expires_at

    refreshed = heartbeat_share_tab_grant(db_session, "share-1", "tab-a", token, ttl_seconds=45)
    assert refreshed.expires_at >= before
```

- [x] **Step 5: 璺戝悗绔?grant 鍩虹璁炬柦娴嬭瘯**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
pytest backend/tests/test_share_tab_grant_service.py -q
```

Expected:  
PASS锛岃鏄?tab grant 鐨勭鍙戙€佹牎楠屻€佺画鍛姐€侀噴鏀惧凡缁忓彲鐢ㄣ€?

---

## Task 3: 鎶婂垎浜В閿佸垏鍒?Tab Grant锛屽苟缁熶竴鍓嶇 Share Session

**Files:**
- Modify: `backend/app/routers/share.py`
- Modify: `backend/tests/test_share_unlock.py`
- Modify: `backend/tests/test_share.py`
- Create: `frontend/src/composables/useShareSession.js`
- Modify: `frontend/src/api/client.js`
- Modify: `frontend/src/api/share.js`
- Modify: `frontend/src/views/share/ShareLayout.vue`
- Modify: `frontend/src/views/share/ShareProject.vue`
- Modify: `frontend/src/views/share/ShareFile.vue`
- Modify: `frontend/src/views/share/SharePreview.vue`
- Create: `frontend/src/views/share/__tests__/ShareSession.spec.js`
- Modify: `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
- Modify: `frontend/src/views/share/__tests__/SharePreview.spec.js`
- Modify: `frontend/src/views/share/__tests__/ShareFilePreviewManifest.spec.js`

- [x] **Step 1: 鍏堟妸鍚庣 unlock 闆嗘垚娴嬭瘯鏀规垚鈥滆繑鍥?grant body 鑰屼笉鏄彧鐪?cookie鈥?*

鍦?`backend/tests/test_share_unlock.py` 涓紝鎶婃棫鏂█锛?

```python
assert "share_access_grant=" in response.headers.get("set-cookie", "")
```

鏀逛负鏂扮殑 contract锛?

```python
response = client.post(
    f"/api/v1/share/{share_token.token}/unlock",
    headers={"X-Share-Tab-Id": "tab-a"},
    json={"password": "OpenSesame!1"},
)

assert response.status_code == 200
payload = response.json()["data"]
assert payload["unlocked"] is True
assert payload["grant_token"]
assert payload["heartbeat_interval_seconds"] == 30
```

骞惰ˉ release 鍥炲綊锛?

```python
release = client.post(
    f"/api/v1/share/{share_token.token}/grant/release",
    headers={
        "X-Share-Tab-Id": "tab-a",
        "X-Share-Grant": payload["grant_token"],
    },
)
assert release.status_code == 200
```

- [x] **Step 2: 鍐欏墠绔?share session 澶辫触鐢ㄤ緥锛岄攣瀹氬悓 tab/鍏?tab/鍚?tab 瀵艰埅琛屼负**

鍦?`frontend/src/views/share/__tests__/ShareSession.spec.js` 澧炲姞鏈€灏忓洖褰掞細

```js
it('reuses the same share_tab_id across refreshes in one tab', () => {
  sessionStorage.clear()
  const first = ensureShareTabId()
  const second = ensureShareTabId()
  expect(second).toBe(first)
})

it('clears stored grant after releaseCurrentShareSession resolves', async () => {
  sessionStorage.setItem('docshop_share_grant:share-token', 'grant-1')
  await releaseCurrentShareSession()
  expect(sessionStorage.getItem('docshop_share_grant:share-token')).toBeNull()
})
```

鍦?`ShareProjectPreview.spec.js` 鎶婇粯璁ら瑙堣涓洪攣鎴愬悓 tab锛?

```js
expect(mocks.routerPush).toHaveBeenCalledWith('/s/share-token/preview/file-1')
expect(openSpy).not.toHaveBeenCalled()
```

- [x] **Step 3: 璺戝け璐ョ敤渚?*

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
pytest backend/tests/test_share_unlock.py -q

cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/views/share/__tests__/ShareSession.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js --run
```

Expected before implementation:  
鍚庣 FAIL锛堟病鏈?tab grant header/release 璇箟锛夛紱鍓嶇 FAIL锛堟病鏈?composable锛岄瑙堥粯璁や粛鏂板紑 tab锛夈€?

- [x] **Step 4: 瀹炵幇鍚庣 unlock / heartbeat / release 璺敱**

`backend/app/routers/share.py` 鐨?unlock 鏀规垚鏄惧紡璇诲彇 tab header锛屽苟杩斿洖 grant body锛?

```python
@router.post("/{share_token}/unlock")
def unlock_share_access(
    share_token: str,
    request: Request,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    x_share_tab_id: str = Header(..., alias="X-Share-Tab-Id"),
):
    ...
    grant_token = issue_share_tab_grant(
        db,
        share_token=share_token,
        tab_id=x_share_tab_id,
        ttl_seconds=45,
    )
    return success_response(data={
        "unlocked": True,
        "grant_token": grant_token,
        "heartbeat_interval_seconds": 30,
    })
```

骞舵柊澧烇細

```python
@router.post("/{share_token}/grant/heartbeat")
def heartbeat_share_access(...): ...

@router.post("/{share_token}/grant/release")
def release_share_access(...): ...
```

鎵€鏈?share API 鐨勯壌鏉冨叆鍙ｆ敼涓鸿鍙栵細

- `X-Share-Tab-Id`
- `X-Share-Grant`

鑰屼笉鏄彧渚濊禆 `Cookie(None, alias=COOKIE_NAME)`銆?

- [x] **Step 5: 瀹炵幇鍓嶇 `useShareSession()` 骞舵妸 3 涓?share 椤甸潰鎺ュ埌缁熶竴浼氳瘽灞?*

`frontend/src/composables/useShareSession.js` 鑷冲皯鎻愪緵锛?

```js
const SHARE_TAB_STORAGE_KEY = 'docshop_share_tab_id'
const SHARE_GRANT_PREFIX = 'docshop_share_grant:'

export function ensureShareTabId(sessionStorageObj = window.sessionStorage) { ... }
export function readShareGrant(token, sessionStorageObj = window.sessionStorage) { ... }
export function writeShareGrant(token, grant, sessionStorageObj = window.sessionStorage) { ... }

export function useShareSession(token) {
  const tabId = ensureShareTabId()
  const grantToken = ref(readShareGrant(token))

  async function unlock(password) { ... }
  async function heartbeat() { ... }
  async function release() { ... }
  function withShareHeaders(headers = {}) {
    return {
      ...headers,
      'X-Share-Tab-Id': tabId,
      ...(grantToken.value ? { 'X-Share-Grant': grantToken.value } : {}),
    }
  }

  return { tabId, grantToken, unlock, heartbeat, release, withShareHeaders }
}
```

鍚屾椂锛?

- `ShareLayout.vue` 鎸傝浇 heartbeat / release
- `ShareProject.vue` 鍘绘帀榛樿 `window.open`
- `ShareProject.vue` / `ShareFile.vue` / `SharePreview.vue` 浣跨敤鍚屼竴浠?unlock state 涓庨敊璇鐞?

- [x] **Step 6: 璺戝垎浜細璇濆洖褰?*

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
pytest backend/tests/test_share_unlock.py backend/tests/test_share.py -q

cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/views/share/__tests__/ShareSession.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js --run
```

Expected:  
PASS锛屽苟涓斺€滈粯璁ら瑙堝悓 tab鈥濃€滃叧 tab/绂诲紑 share 瀛愭爲鍚庡彲 release鈥濆凡缁忓叿澶囪惤鐐广€?

---

## Task 4: 涓哄垎浜祫婧愬叆鍙ｆ帴鍏?Resource Ticket

**Files:**
- Create: `backend/app/services/share_resource_ticket_service.py`
- Create: `backend/tests/test_share_resource_tickets.py`
- Modify: `backend/app/routers/share.py`
- Modify: `backend/tests/test_share_unlock.py`
- Modify: `backend/tests/test_share.py`
- Create: `frontend/src/utils/shareResourceTickets.js`
- Modify: `frontend/src/api/share.js`
- Modify: `frontend/src/utils/resourceUrl.js`
- Modify: `frontend/src/views/share/ShareProject.vue`
- Modify: `frontend/src/views/share/ShareFile.vue`
- Modify: `frontend/src/views/share/SharePreview.vue`

- [x] **Step 1: 鍏堝啓 ticket 澶辫触鐢ㄤ緥**

鍦?`backend/tests/test_share_resource_tickets.py` 澧炲姞锛?

```python
def test_issue_and_validate_share_resource_ticket(db_session):
    from app.services.share_tab_grant_service import issue_share_tab_grant
    from app.services.share_resource_ticket_service import issue_share_resource_ticket, validate_share_resource_ticket

    grant_token = issue_share_tab_grant(db_session, share_token="share-1", tab_id="tab-a", ttl_seconds=45)
    ticket = issue_share_resource_ticket(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        raw_grant=grant_token,
        kind="preview",
        file_id="file-1",
        ttl_seconds=60,
    )

    claims = validate_share_resource_ticket(ticket, share_token="share-1", kind="preview", file_id="file-1")
    assert claims is not None
```

骞惰ˉ涓€鏉♀€渢icket 涓嶅彲璺ㄨ祫婧愬鐢ㄢ€濈殑鐢ㄤ緥锛?

```python
def test_share_resource_ticket_rejects_wrong_asset():
    ...
```

- [x] **Step 2: 璺?ticket 鍗曟祴锛岀‘璁ゅ綋鍓嶈繕鏈疄鐜?*

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
pytest backend/tests/test_share_resource_tickets.py -q
```

Expected before implementation:  
FAIL銆?

- [x] **Step 3: 瀹炵幇鍚庣 ticket service 涓庣鍙戞帴鍙?*

`backend/app/services/share_resource_ticket_service.py` 鎻愪緵锛?

```python
def issue_share_resource_ticket(
    db: Session,
    *,
    share_token: str,
    tab_id: str,
    raw_grant: str,
    kind: str,
    file_id: str | None = None,
    version_id: str | None = None,
    page_num: int | None = None,
    asset_id: str | None = None,
    format: str | None = None,
    ttl_seconds: int = 60,
) -> str: ...

def validate_share_resource_ticket(
    raw_ticket: str | None,
    *,
    share_token: str,
    kind: str,
    file_id: str | None = None,
    version_id: str | None = None,
    page_num: int | None = None,
    asset_id: str | None = None,
    format: str | None = None,
): ...
```

鍦?`share.py` 澧炲姞锛?

```python
@router.post("/{share_token}/resource-ticket")
def issue_share_resource_ticket_endpoint(...):
    ...
```

骞舵妸杩欎簺璧勬簮鍏ュ彛鏀规垚鎺ュ彈 `ticket`锛?

- `preview`
- `pages`
- `preview-assets`
- `versions/*/download`
- `download/{format}`
- `folders/*/download`

- [x] **Step 4: 瀹炵幇鍓嶇 ticket 鐢宠涓庤祫婧?URL 鏀跺彛**

`frontend/src/utils/shareResourceTickets.js` 寤虹珛涓€涓潪甯哥獎鐨?async helper锛?

```js
export async function getShareResourceUrl({
  token,
  session,
  kind,
  fileId,
  version,
  versionId,
  pageNum,
  assetId,
  format,
}) {
  const ticket = await issueShareResourceTicket(token, {
    kind,
    file_id: fileId,
    version,
    version_id: versionId,
    page_num: pageNum,
    asset_id: assetId,
    format,
  }, {
    headers: session.withShareHeaders(),
  })

  if (kind === 'preview') return buildSharePreviewUrl(token, fileId, { version, ticket })
  if (kind === 'page') return buildSharePageUrl(token, fileId, pageNum, { version, ticket })
  if (kind === 'preview_asset') return buildSharePreviewAssetUrl(token, fileId, assetId, { ticket })
  ...
}
```

鍚屾椂鎶?`resourceUrl.js` 鐨?share builder 鏀规垚鎺ユ敹 `ticket`锛?

```js
export function buildSharePreviewUrl(token, fileId, options = {}) {
  const { version, ticket, cacheKey } = options
  return withQuery(`/api/v1/share/${token}/files/${fileId}/preview`, {
    version,
    ticket,
    _preview: cacheKey,
  })
}
```

- [x] **Step 5: 璺戣祫婧愮エ鎹洖褰?*

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
pytest backend/tests/test_share_resource_tickets.py backend/tests/test_share_unlock.py backend/tests/test_share.py -q

cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js --run
```

Expected:  
PASS锛涘垎浜瑙堛€佸垎椤靛浘銆侀瑙堥檮浠躲€佷笅杞介摼鎺ラ兘寮€濮嬮€氳繃 ticket 鍖栬矾寰勮幏鍙栥€?

---

## Task 5: 鎶?HTML 棰勮鏀规垚 Runtime Preview锛岃€屼笉鏄洿鎺ヨ繑鍥炲師濮?HTML

**Files:**
- Create: `backend/app/services/html_runtime_preview_service.py`
- Modify: `backend/app/services/preview_manifest_service.py`
- Modify: `backend/app/routers/files.py`
- Modify: `backend/app/routers/share.py`
- Modify: `backend/tests/test_preview_manifest_service.py`
- Modify: `backend/tests/test_files_rich_preview.py`
- Modify: `backend/tests/test_share_unlock.py`
- Modify: `frontend/src/components/file-viewer/FileViewer.vue`
- Modify: `frontend/src/components/file-viewer/HtmlViewer.vue`
- Modify: `frontend/src/components/file-viewer/__tests__/FileViewer.spec.js`
- Modify: `frontend/src/views/share/SharePreview.vue`
- Modify: `frontend/src/views/share/__tests__/SharePreview.spec.js`

- [x] **Step 1: 鍏堟妸 manifest 涓?route 娴嬭瘯鏀规垚鈥滀笉鑳藉啀鐩存帴杩斿洖鍘熷 HTML鈥?*

鍦?`backend/tests/test_preview_manifest_service.py` 鎶?HTML 鏂█鏀逛负锛?

```python
def test_build_preview_manifest_for_html_uses_runtime_mode():
    manifest = build_preview_manifest(
        file_profile={"category": "html", "preview_mode": "native", "preview_status": "ready"},
        preview_assets=[
            {"asset_type": "html_runtime_entry", "url": "/api/v1/files/f1/preview?version=1"},
        ],
        analysis_summary={"title": "demo"},
    )

    assert manifest["type"] == "html_runtime"
    assert manifest["primary_asset"]["asset_type"] == "html_runtime_entry"
```

鍦?`backend/tests/test_files_rich_preview.py` 鎶婃棫鏂█锛?

```python
assert response.text == html_content
```

鏀逛负锛?

```python
assert response.status_code == 200
assert "report.html" not in response.text or response.text != html_content
assert "docshop-runtime-preview" in response.text
```

- [x] **Step 2: 鍐欏墠绔け璐ョ敤渚嬶紝閿佸畾 SharePreview 涓嶅啀瑁歌烦杞師濮?HTML**

鍦?`frontend/src/views/share/__tests__/SharePreview.spec.js` 鎶?HTML 鐢ㄤ緥鏀逛负锛?

```js
it('renders runtime html preview inside the share shell instead of raw location.replace', async () => {
  mockedShareFileData = {
    ...mockedShareFileData,
    file_type: 'html',
    preview_manifest: {
      type: 'html_runtime',
      status: 'ready',
      primary_asset: {
        asset_type: 'html_runtime_entry',
        url: '/api/v1/share/share-token/files/file-1/preview?ticket=runtime-ticket',
      },
    },
  }

  const wrapper = mount(SharePreview, { global: globalConfig })
  await flushPromises()
  await flushPromises()

  expect(mockedLocation.replace).not.toHaveBeenCalled()
  expect(wrapper.find('[data-testid=\"share-preview-html-frame\"]').exists()).toBe(true)
})
```

- [x] **Step 3: 璺戝け璐ョ敤渚?*

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
pytest backend/tests/test_preview_manifest_service.py backend/tests/test_files_rich_preview.py backend/tests/test_share_unlock.py -q

cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/components/file-viewer/__tests__/FileViewer.spec.js src/views/share/__tests__/SharePreview.spec.js --run
```

Expected before implementation:  
FAIL锛屽洜涓哄綋鍓嶄粛鏄?`html_native`锛屽苟涓?share/html 棰勮杩樻槸 raw HTML / `location.replace(...)`銆?

- [x] **Step 4: 瀹炵幇 runtime HTML preview service 涓?manifest 鍒囨崲**

`backend/app/services/html_runtime_preview_service.py` 鑷冲皯鏆撮湶涓€涓ǔ瀹氬叆鍙ｏ細

```python
def build_runtime_html_preview(
    *,
    storage_path: str,
    title: str,
    asset_url_resolver,
) -> str:
    """Return a transformed runtime preview HTML document."""
```

`preview_manifest_service.py` 鐨?HTML 鍒嗘敮鏀规垚锛?

```python
if category == "html":
    primary_asset = next((asset for asset in preview_assets if asset["asset_type"] == "html_runtime_entry"), None)
    return {
        "type": "html_runtime",
        "status": "ready" if primary_asset else preview_status,
        "primary_asset": primary_asset,
        "thumbnails": [],
        "summary": analysis_summary or {},
    }
```

`files.py` 涓?`share.py` 瀵?`file_type == "html"` 涓嶅啀鐩存帴锛?

```python
with open(...): return HTMLResponse(content=html_content)
```

鑰屾敼鎴愶細

```python
runtime_html = build_runtime_html_preview(
    storage_path=fv.storage_path,
    title=preview_title,
    asset_url_resolver=...,
)
return HTMLResponse(content=runtime_html, headers={
    "Content-Security-Policy": "...",
    "Referrer-Policy": "no-referrer",
})
```

- [x] **Step 5: 鎺ュ墠绔?HtmlViewer / SharePreview**

`FileViewer.vue` 鏀寔鏂扮被鍨嬶細

```js
case 'html_runtime':
  return HtmlViewer
```

`HtmlViewer.vue` 缁х画鐢?iframe锛屼絾鏄庣‘鎵胯浇 runtime entry锛?

```vue
<iframe
  v-if="previewUrl"
  :src="previewUrl"
  class="html-viewer__frame"
  data-testid="html-viewer-frame"
  sandbox="allow-scripts allow-forms allow-modals allow-downloads"
  referrerpolicy="no-referrer"
/>
```

`SharePreview.vue` 鍘绘帀 `location.replace(resolvedPreviewUrl.value)` 璺緞锛孒TML 鏀瑰洖 share shell 鍐?iframe銆?

- [x] **Step 6: 璺?HTML runtime 鍥炲綊**

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
pytest backend/tests/test_preview_manifest_service.py backend/tests/test_files_rich_preview.py backend/tests/test_share_unlock.py -q

cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/components/file-viewer/__tests__/FileViewer.spec.js src/views/share/__tests__/SharePreview.spec.js --run
```

Expected:  
PASS锛汬TML 棰勮浠嶅彲宓屽叆浜掑姩锛屼絾涓嶅啀绛変簬鍘熷涓婁紶 HTML 鏂囨湰銆?

---

## Task 6: 鏇存柊璧勬簮鍗忚鏂囨。骞惰ˉ鍏呪€滀笉鏄潬娣锋穯/鍔犲瘑褰撳畨鍏ㄨ竟鐣屸€濈殑绾︽潫

**Files:**
- Modify: `docs/frontend-browser-resource-protocol.md`

- [x] **Step 1: 鍦ㄥ崗璁枃妗ｄ腑鍐欏叆鏂扮殑 share 璧勬簮璁块棶璇箟**

`docs/frontend-browser-resource-protocol.md` 鑷冲皯琛ラ綈杩?4 鐐癸細

```md
1. 甯﹀瘑鐮佸垎浜?API 浣跨敤 `X-Share-Tab-Id` + `X-Share-Grant`
2. 娴忚鍣ㄥ師鐢?share 璧勬簮浣跨敤鐭椂 `ticket`
3. HTML 棰勮浣跨敤 runtime preview锛岃€屼笉鏄師濮嬩笂浼?HTML
4. 鐢熶骇涓嶆妸娣锋穯 / 鍏閽ュ墠绔姞瀵嗗綋鎴愪富瀹夊叏杈圭晫
```

- [x] **Step 2: 鏄庣‘閿欒璇箟**

琛ュ厖锛?

```md
- 401: grant 澶辨晥 / 闇€瑕侀噸鏂扮櫥褰?
- 403: 鏈В閿併€乼icket 鏃犳晥銆佽祫婧愬姩浣滀笉鍏佽
- 404: 璧勬簮涓嶅瓨鍦ㄦ垨鎸夌瓥鐣ラ殣钘?
```

- [x] **Step 3: 鍐欏叆杩佺Щ杈圭晫**

鏂囨。鏄庣‘锛?

```md
- `resourceUrl.js` 鍙礋璐?URL family
- `useShareSession.js` 璐熻矗 share headers
- `shareResourceTickets.js` 璐熻矗 ticket 鐢宠涓庣煭鏃剁紦瀛?
- 瑙嗗浘灞備笉寰楀啀鐩存帴鎷?`/api/v1/share/...` 璧勬簮 URL
```

- [x] **Step 4: 浜哄伐澶嶆牳鏂囨。涓庤璁＄涓€鑷?*

Checklist:

- 鏄惁鍐欐槑鈥滃叧 tab 澶辨晥銆佸埛鏂板悓 tab 淇濈暀鈥?
- 鏄惁鍐欐槑鈥滈粯璁ゅ悓 tab 瀵艰埅鈥?
- 鏄惁鍐欐槑鈥淗TML 鍙簰鍔ㄤ絾涓嶄細鎵胯婧愮爜缁濆涓嶅彲瑙佲€?

- [x] **Step 5: 涓嶈窇鏋勫缓锛屽彧鍋氭枃妗?diff 鑷**

Expected:  
鏂囨。鏇存柊瀹屾垚涓斾笌 `docs/superpowers/specs/2026-07-03-share-tab-grant-runtime-preview-and-tracking-ping-design.md` 淇濇寔涓€鑷淬€?

---

## Task 7: 鍏ㄩ摼璺獙璇?

**Files:**
- No new files unless fixing regressions found here.

- [x] **Step 1: 璺戝悗绔畾鍚戞祴璇曢泦鍚?*

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop
pytest backend/tests/test_share_tab_grant_service.py backend/tests/test_share_resource_tickets.py backend/tests/test_share_unlock.py backend/tests/test_share.py backend/tests/test_preview_manifest_service.py backend/tests/test_files_rich_preview.py test/test_tracking_ping.py -q
```

Expected:  
鍏ㄩ儴 PASS銆?

- [x] **Step 2: 璺戝墠绔畾鍚戞祴璇曢泦鍚?*

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run test -- src/utils/__tests__/trackingClient.spec.js src/views/share/__tests__/ShareSession.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/components/file-viewer/__tests__/FileViewer.spec.js --run
```

Expected:  
鍏ㄩ儴 PASS銆?

- [x] **Step 3: 璺戝墠绔瀯寤?*

Run:

```powershell
cd C:\Users\lihuo\Desktop\docshop\frontend
npm run build
```

Expected:  
Vite build 鎴愬姛锛屾棤鏂板 import/route/manifest 閿欒銆?

- [x] **Step 4: 鍋氭墜宸ュ洖褰掕剼鏈?*

鎸変笅闈㈤『搴忎汉宸ラ獙璇侊細

```text
1. 鎵撳紑涓€涓甫瀵嗙爜鍒嗕韩 -> 杈撳叆瀵嗙爜 -> 鑳借繘鍏ラ」鐩〉
2. 鍚?tab 鍒锋柊 -> 浠嶅彲缁х画璁块棶
3. 鐐瑰嚮鏂囦欢 / 棰勮 / diff / versions / 涓嬭浇 -> 鍧囨甯?
4. 鍏抽棴璇?tab 鍚庨噸寮€鍚屼竴鍒嗕韩 -> 鍐嶆瑕佹眰杈撳叆瀵嗙爜
5. 鏂板紑绗簩涓?tab 鎵撳紑鍚屼竴鍒嗕韩 -> 涔熷繀椤婚噸鏂拌緭鍏ュ瘑鐮?
6. 棣栨鎵撳紑鍒嗕韩椤佃瀵?Network -> /api/v1/tracking/ping 涓嶅啀 429
7. 鎵撳紑 HTML 棰勮 -> 鍙互鐐瑰嚮浜掑姩锛屼絾涓嶅啀鏄師濮嬩笂浼?HTML 鐩存帴鍥炰紶
```

- [x] **Step 5: 璁板綍鏈€缁堢粨鏋?*

璁板綍锛?

- 鍝簺鍥炲綊閫氳繃
- 鏄惁杩樻湁鏈鐩栫殑 HTML 鍏煎鎬ф牱鏈?
- 鏄惁闇€瑕佹妸鈥滄樉寮忔柊寮€鍒嗕韩棰勮 tab鈥濅綔涓哄悗缁崟鐙渶姹?

---

## Self-Review

- Spec coverage:
  - tab 绾у瘑鐮佸垎浜細Task 2銆乀ask 3
  - 璧勬簮閾炬帴缁熶竴鏀跺彛锛歍ask 4銆乀ask 6
  - HTML runtime preview锛歍ask 5
  - tracking ping 429锛歍ask 1
  - 瀹夊叏杈圭晫璇存槑锛歍ask 5銆乀ask 6
- Placeholder scan:
  - 娌℃湁 `TODO`銆乣TBD`銆乣implement later`
  - 姣忎釜浠诲姟閮界粰鍑烘槑纭枃浠躲€佹祴璇曚笌鍛戒护
- Type consistency:
  - 鍚庣缁熶竴浣跨敤 `share_tab_grant` / `resource_ticket`
  - 鍓嶇缁熶竴浣跨敤 `useShareSession()` / `shareResourceTickets.js`
  - HTML manifest 缁熶竴鍛藉悕涓?`html_runtime`
- User constraint:
  - 璁″垝涓笉鍖呭惈 commit / reset / clean / push 姝ラ

---

**Plan complete and saved to `docs/superpowers/plans/2026-07-03-share-tab-grant-runtime-preview-and-tracking-ping.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

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


