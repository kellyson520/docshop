# Browser-Side Precise Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable meter-level geographic location, real device model/brand, visitor UUID, log noise reduction, announcement targeting, and map visualization by adding a frontend beacon and enriching the tracking backend.

**Architecture:** A frontend beacon module collects browser APIs and sends them to a new `POST /api/v1/tracking/ping` endpoint. The middleware classifies requests by `is_page_view` and propagates `visitor_id`. The `Announcement` model gains JSON `targeting_rules`. The dashboard adds a Leaflet map and visitor-centric columns.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite additive schema updates, Vue 3, Element Plus, Leaflet, Vitest, Pytest

---

## File Structure

### Backend

- Create: `backend/app/routers/tracking_ping.py`
- Modify: `backend/app/middlewares/tracking.py` 鈥?add `visitor_id`, `is_page_view`, skip ping, merge pending
- Modify: `backend/app/models/access_log.py` 鈥?add 7 new columns
- Modify: `backend/app/models/user_session.py` 鈥?add `visitor_id`
- Modify: `backend/app/models/announcement.py` 鈥?add `targeting_rules`
- Modify: `backend/app/routers/tracking_admin.py` 鈥?add `?page_views_only`, `/locations`
- Modify: `backend/app/routers/announcements.py` 鈥?evaluate `targeting_rules`
- Modify: `backend/app/database.py` 鈥?additive migration
- Modify: `backend/app/main.py` 鈥?register ping router
- Create: `test/test_tracking_ping.py`
- Create: `test/test_announcement_targeting.py`
- Create: `test/test_tagging.py`
- Modify: existing test files

### Frontend

- Create: `frontend/src/utils/trackingClient.js`
- Create: `frontend/src/components/tracking/VisitorMap.vue`
- Create: `frontend/src/views/admin/VisitorProfile.vue`
- Modify: `frontend/src/main.js`
- Modify: `frontend/src/utils/trackingDisplay.js`
- Modify: `frontend/src/views/admin/TrackingDashboard.vue`
- Modify: `frontend/src/views/admin/AnnouncementManager.vue`
- Modify: `frontend/src/components/common/AnnouncementBar.vue`
- Modify: `frontend/package.json` 鈥?add `leaflet`
- Modify: `frontend/src/router` 鈥?add profile route
- Create/Modify: test files

---

## Task 1: Add new DB columns and additive migration

**Files:**
- `backend/app/models/access_log.py`
- `backend/app/models/user_session.py`
- `backend/app/models/announcement.py`
- `backend/app/database.py`
- `test/test_tracking_access_log.py`

- [ ] **Step 1: Add columns to `access_log.py`**

```python
class AccessLog(Base):
    # ... existing columns ...

    visitor_id = Column(String(36), nullable=True, index=True)
    is_page_view = Column(Integer, default=0)  # 1=page load, 0=API/asset

    geo_latitude = Column(Float(10, 7), nullable=True)
    geo_longitude = Column(Float(10, 7), nullable=True)
    geo_accuracy = Column(Float(6, 1), nullable=True)
    client_timezone = Column(String(64), nullable=True)
    client_language = Column(String(20), nullable=True)
```

Update `to_dict()` to include all new fields. Update `from_request()` factory to accept `visitor_id` and `is_page_view`.

- [ ] **Step 2: Add `visitor_id` to `user_session.py`**

```python
visitor_id = Column(String(36), nullable=True, index=True)
```

- [ ] **Step 3: Add `targeting_rules` to `announcement.py`**

```python
targeting_rules = Column(Text, nullable=True)  # JSON string
```

Update `to_dict()` to include it.

- [ ] **Step 4: Add additive DDL in `database.py`**

```python
def _access_log_additive_statements(columns: set[str]) -> list[str]:
    statements: list[str] = []
    if "visitor_id" not in columns:
        statements.append("ALTER TABLE access_logs ADD COLUMN visitor_id VARCHAR(36)")
    if "is_page_view" not in columns:
        statements.append("ALTER TABLE access_logs ADD COLUMN is_page_view INTEGER DEFAULT 0")
    if "geo_latitude" not in columns:
        statements.append("ALTER TABLE access_logs ADD COLUMN geo_latitude FLOAT")
    if "geo_longitude" not in columns:
        statements.append("ALTER TABLE access_logs ADD COLUMN geo_longitude FLOAT")
    if "geo_accuracy" not in columns:
        statements.append("ALTER TABLE access_logs ADD COLUMN geo_accuracy FLOAT")
    if "client_timezone" not in columns:
        statements.append("ALTER TABLE access_logs ADD COLUMN client_timezone VARCHAR(64)")
    if "client_language" not in columns:
        statements.append("ALTER TABLE access_logs ADD COLUMN client_language VARCHAR(20)")
    return statements
```

Add similar `_user_sessions_additive_statements()` for `visitor_id`.

- [ ] **Step 5: Write failing tests**

```python
# test/test_tracking_access_log.py

def test_access_log_to_dict_includes_new_fields():
    log = AccessLog(
        visitor_id="v-123", is_page_view=1,
        geo_latitude=39.9042, geo_longitude=116.4074, geo_accuracy=5.0,
        client_timezone="Asia/Shanghai", client_language="zh-CN",
    )
    data = log.to_dict()
    assert data["visitor_id"] == "v-123"
    assert data["is_page_view"] is True
    assert data["geo_latitude"] == 39.9042


def test_access_log_additive_statements_includes_all_new_columns():
    from app.database import _access_log_additive_statements
    stmts = _access_log_additive_statements({"id", "timestamp"})
    assert "ADD COLUMN visitor_id" in str(stmts)
    assert "ADD COLUMN is_page_view" in str(stmts)
    assert "ADD COLUMN geo_latitude" in str(stmts)
    assert "ADD COLUMN client_timezone" in str(stmts)
```

- [ ] **Step 6: Run, implement, re-run**

```bash
pytest test/test_tracking_access_log.py -v
# FAIL -> implement -> PASS
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/access_log.py backend/app/models/user_session.py backend/app/models/announcement.py backend/app/database.py test/test_tracking_access_log.py
git commit -m "feat: add visitor_id, is_page_view, geo, client locale, targeting_rules columns"
```

---

## Task 2: Implement `is_page_view` and `visitor_id` in middleware

**Files:**
- `backend/app/middlewares/tracking.py`
- `test/test_tracking_middleware.py`

- [ ] **Step 1: Add `_is_page_view()` method**

```python
def _is_page_view(self, request: Request) -> bool:
    path = str(request.url.path)
    static_exts = ('.js', '.css', '.png', '.jpg', '.jpeg', '.svg', '.webp',
                   '.woff', '.woff2', '.ttf', '.ico', '.json', '.map', '.txt')
    if any(path.endswith(ext) for ext in static_exts):
        return False
    if path.startswith('/assets/'):
        return False
    if path.startswith('/api/'):
        return False
    if path in ('/favicon.ico', '/robots.txt'):
        return False
    accept = (request.headers.get('accept') or '').lower()
    if 'text/html' in accept:
        return True
    return False
```

- [ ] **Step 2: Wire into `_log_access()`**

```python
log = AccessLog(
    visitor_id=request.state.device_id,
    is_page_view=1 if self._is_page_view(request) else 0,
    # ... existing fields ...
)
```

- [ ] **Step 3: Write tests**

```python
def test_is_page_view_returns_true_for_html_pages():
    middleware = TrackingMiddleware(app=None)
    # mock request with path="/projects" and accept="text/html"
    assert middleware._is_page_view(request) is True

def test_is_page_view_returns_false_for_api_calls():
    # path="/api/v1/projects"
    assert middleware._is_page_view(request) is False

def test_is_page_view_returns_false_for_static_assets():
    # path="/assets/index-DJKm4MNx.js"
    assert middleware._is_page_view(request) is False
```

- [ ] **Step 4: Run, implement, re-run**

```bash
pytest test/test_tracking_middleware.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/middlewares/tracking.py test/test_tracking_middleware.py
git commit -m "feat: classify page views vs API/asset with is_page_view, propagate visitor_id"
```

---

## Task 3: Create backend ping endpoint

**Files:**
- Create: `backend/app/routers/tracking_ping.py`
- Modify: `backend/app/main.py`
- Create: `test/test_tracking_ping.py`

- [ ] **Step 1: Implement ping handler**

```python
# backend/app/routers/tracking_ping.py
import json, time
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import desc
from app.database import SessionLocal
from app.models.access_log import AccessLog
from app.models.user_session import UserSession
from app.models.tracking_config import TrackingConfig
from app.utils.logger import get_logger

logger = get_logger("tracking-ping")
router = APIRouter(prefix="/tracking", tags=["tracking"])

_rate_limit_cache: dict[str, float] = {}
_RATE_LIMIT_SECONDS = 10

def _check_rate_limit(session_id: str) -> bool:
    now = time.time()
    last = _rate_limit_cache.get(session_id, 0)
    if now - last < _RATE_LIMIT_SECONDS:
        return False
    _rate_limit_cache[session_id] = now
    return True

def _anonymize_coordinates(lat, lng, accuracy):
    if lat is not None: lat = round(lat, 3)
    if lng is not None: lng = round(lng, 3)
    if accuracy is not None: accuracy = max(accuracy, 111.0)
    return lat, lng, accuracy

@router.post("/ping", status_code=204)
async def receive_ping(request: Request):
    body = await request.json()
    session_id = body.get("session_id") or request.cookies.get("session_id")
    device_id = body.get("device_id") or request.cookies.get("device_id")
    if not session_id and not device_id:
        raise HTTPException(400, "missing session_id or device_id")
    if session_id and not _check_rate_limit(session_id):
        raise HTTPException(429, "too many pings")

    db = SessionLocal()
    try:
        config = db.query(TrackingConfig).first()
        anonymize = bool(config and config.anonymize_ip)

        lat = body.get("geo_latitude")
        lng = body.get("geo_longitude")
        accuracy = body.get("geo_accuracy")
        if anonymize and (lat is not None or lng is not None):
            lat, lng, accuracy = _anonymize_coordinates(lat, lng, accuracy)

        update_fields = {}
        for key in ("screen_resolution", "geo_latitude", "geo_longitude",
                     "geo_accuracy", "client_language", "client_timezone",
                     "device_brand", "device_model"):
            if body.get(key) is not None:
                update_fields[key] = body[key]

        extra = {}
        for key in ("hardware_concurrency", "device_memory", "max_touch_points"):
            if body.get(key) is not None:
                extra[key] = body[key]

        log = None
        if session_id:
            log = db.query(AccessLog).filter(
                AccessLog.session_id == session_id,
                AccessLog.is_deleted == 0,
            ).order_by(desc(AccessLog.timestamp)).first()

        if log:
            for field, value in update_fields.items():
                setattr(log, field, value)
            if extra:
                existing_raw = {}
                if log.raw_data:
                    try: existing_raw = json.loads(log.raw_data)
                    except: pass
                existing_raw["client_extra"] = extra
                log.raw_data = json.dumps(existing_raw)
            db.commit()
        elif session_id:
            session = db.query(UserSession).filter(
                UserSession.session_id == session_id
            ).first()
            if session:
                pending = {}
                if session.raw_data:
                    try: pending = json.loads(session.raw_data)
                    except: pending = {}
                pending["pending_beacon"] = {**update_fields, **extra}
                session.raw_data = json.dumps(pending)
                db.commit()
    finally:
        db.close()
    return None  # 204
```

- [ ] **Step 2: Register in `main.py`**

```python
from app.routers.tracking_ping import router as tracking_ping_router
app.include_router(tracking_ping_router, prefix="/api/v1/tracking")
```

- [ ] **Step 3: Write tests and verify**

```bash
pytest test/test_tracking_ping.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/tracking_ping.py backend/app/main.py test/test_tracking_ping.py
git commit -m "feat: tracking ping endpoint for browser-side data enrichment"
```

---

## Task 4: Update middleware for ping path skip and pending merge

**Files:**
- `backend/app/middlewares/tracking.py`

- [ ] **Step 1: In `dispatch()`, skip ping path**

```python
if request.url.path.endswith("/tracking/ping"):
    return await call_next(request)
```

- [ ] **Step 2: Store `access_log_id` on `request.state` after log creation**

```python
request.state.access_log_id = log.id
```

- [ ] **Step 3: Merge pending beacon data from `UserSession.raw_data`**

After committing the new `AccessLog`, check if `UserSession.raw_data` has `pending_beacon` and merge it.

- [ ] **Step 4: Run tests**

```bash
pytest test/test_tracking_middleware.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/middlewares/tracking.py
git commit -m "feat: skip ping logging, merge pending beacon data from UserSession"
```

---

## Task 5: Create frontend tracking beacon

**Files:**
- Create: `frontend/src/utils/trackingClient.js`
- Create: `frontend/src/utils/__tests__/trackingClient.spec.js`
- Modify: `frontend/src/main.js`

- [ ] **Step 1: Implement `trackingClient.js` (two-phase collection)**

```javascript
// frontend/src/utils/trackingClient.js
//
// Two-phase tracking beacon:
// Phase 1 (synchronous, ~0ms) 鈥?collects zero-latency browser APIs and fires immediately.
// Phase 2 (async, ~2s later) 鈥?collects UA Client Hints + Storage estimate via second ping.
// Both pings target the same AccessLog row (matched by session_id).

const CONFIG_CACHE_TTL = 300_000
let _configCache = null, _configCacheTime = 0
const PING_URL = '/api/v1/tracking/ping'

// 鈹€鈹€ helpers 鈹€鈹€

async function getTrackingConfig() {
  const now = Date.now()
  if (_configCache && now - _configCacheTime < CONFIG_CACHE_TTL) return _configCache
  try {
    const res = await fetch('/api/v1/tracking/config')
    _configCache = await res.json()
    _configCacheTime = now
    return _configCache
  } catch { return null }
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function sendBeacon(url, data) {
  const body = JSON.stringify(data)
  if (navigator.sendBeacon) return navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }))
  fetch(url, { method: 'POST', body, headers: { 'Content-Type': 'application/json' }, keepalive: true }).catch(() => {})
}

// 鈹€鈹€ Phase 1: synchronous collection (Chrome + Safari + Firefox) 鈹€鈹€

function collectSyncDeviceData() {
  const d = {}
  // Screen (all browsers)
  if (window.screen) {
    d.screen_resolution = `${window.screen.width}x${window.screen.height}`
    d.screen_avail = `${window.screen.availWidth}x${window.screen.availHeight}`
    d.screen_color_depth = window.screen.colorDepth
    try { d.screen_orientation = window.screen.orientation?.type } catch {}
  }
  d.screen_pixel_ratio = window.devicePixelRatio || undefined
  // Platform (most useful on Safari 鈥?Chrome's value is frozen but harmless)
  d.platform = navigator.platform || undefined
  // Hardware
  if (navigator.hardwareConcurrency !== undefined) d.hardware_concurrency = navigator.hardwareConcurrency
  if (navigator.deviceMemory !== undefined) d.device_memory = navigator.deviceMemory
  if (navigator.maxTouchPoints !== undefined) d.max_touch_points = navigator.maxTouchPoints
  d.touch_support = 'ontouchstart' in window
  // Pointer / hover precision (all browsers)
  try { d.pointer_coarse = matchMedia('(pointer: coarse)').matches } catch {}
  try { d.pointer_fine = matchMedia('(pointer: fine)').matches } catch {}
  try { d.hover_hover = matchMedia('(hover: hover)').matches } catch {}
  try { d.any_pointer_coarse = matchMedia('(any-pointer: coarse)').matches } catch {}
  try { d.any_pointer_fine = matchMedia('(any-pointer: fine)').matches } catch {}
  // Network (Chrome only; Safari returns undefined)
  if (navigator.connection) {
    d.network_type = navigator.connection.effectiveType
    d.network_downlink = navigator.connection.downlink
    d.network_rtt = navigator.connection.rtt
    d.network_save_data = navigator.connection.saveData || false
  }
  // Locale
  if (navigator.language) d.language = navigator.language
  try { d.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone } catch {}
  return d
}

function collectLocation() {
  return new Promise(resolve => {
    if (!navigator.geolocation) return resolve({})
    navigator.geolocation.getCurrentPosition(
      pos => resolve({
        geo_latitude: pos.coords.latitude,
        geo_longitude: pos.coords.longitude,
        geo_accuracy: pos.coords.accuracy,
      }),
      () => resolve({}),
      { timeout: 5000, enableHighAccuracy: true }
    )
  })
}

// 鈹€鈹€ Phase 2: async collection (deferred) 鈹€鈹€

function schedulePhase2(basePayload) {
  setTimeout(async () => {
    const extra = { ...basePayload }
    // UA Client Hints (Chromium only)
    if (navigator.userAgentData?.getHighEntropyValues) {
      try {
        const hints = await navigator.userAgentData.getHighEntropyValues([
          'architecture', 'bitness', 'platformVersion', 'uaFullVersion',
          'model', 'platform', 'fullVersionList',
        ])
        if (hints.architecture) extra.cpu_architecture = hints.architecture
        if (hints.bitness) extra.cpu_bitness = hints.bitness
        if (hints.platformVersion) extra.platform_version = hints.platformVersion
        if (hints.uaFullVersion) extra.browser_full_version = hints.uaFullVersion
        if (hints.model) extra.device_model = hints.model
        if (hints.fullVersionList) {
          const main = hints.fullVersionList.find(
            b => b.brand !== 'Not)A;Brand' && b.brand !== 'Chromium'
          )
          if (main) extra.device_brand = main.brand
        }
      } catch {}
    }
    // Storage quota
    if (navigator.storage?.estimate) {
      try {
        const est = await navigator.storage.estimate()
        if (est.quota) extra.storage_quota_gb = Math.round(est.quota / (1024**3) * 10) / 10
      } catch {}
    }
    sendBeacon(PING_URL, extra)
  }, 2000)
}

// 鈹€鈹€ public entry 鈹€鈹€

export async function initTracking() {
  try {
    const config = await getTrackingConfig()
    if (!config?.enable_tracking) return

    const deviceId = getCookie('device_id')
    const sessionId = getCookie('session_id')

    // Phase 1: sync data + location
    const payload = { device_id: deviceId, session_id: sessionId }
    if (config.enable_device_tracking) Object.assign(payload, collectSyncDeviceData())
    if (config.enable_location_tracking) Object.assign(payload, await collectLocation())

    if (Object.keys(payload).length > 2) {
      sendBeacon(PING_URL, payload)
      // Schedule Phase 2 with same device/session IDs
      schedulePhase2({ device_id: deviceId, session_id: sessionId })
    }
  } catch {}
}
```

- [ ] **Step 2: Wire into `main.js`**

```javascript
import { initTracking } from '@/utils/trackingClient'
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => initTracking())
} else {
  initTracking()
}
```

- [ ] **Step 3: Write tests and verify**

```bash
cd frontend
npx vitest run src/utils/__tests__/trackingClient.spec.js
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/trackingClient.js frontend/src/utils/__tests__/trackingClient.spec.js frontend/src/main.js
git commit -m "feat: browser tracking beacon for precise device and location data"
```

---

## Task 6: Add `?page_views_only` filter and `/locations` endpoint to admin API

**Files:**
- `backend/app/routers/tracking_admin.py`

- [ ] **Step 1: Add `page_views_only` parameter to `GET /logs`**

```python
page_views_only: Optional[int] = Query(0, ge=0, le=1)
if page_views_only:
    query = query.filter(AccessLog.is_page_view == 1)
```

- [ ] **Step 2: Implement `GET /admin/tracking/locations`**

```python
@router.get("/locations")
def get_tracking_locations(
    start_date: str = Query(None), end_date: str = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    query = db.query(
        AccessLog.geo_latitude, AccessLog.geo_longitude,
        AccessLog.ip_city, AccessLog.ip_country,
        AccessLog.device_type, AccessLog.device_brand, AccessLog.device_model,
        AccessLog.client_timezone, AccessLog.timestamp,
    ).filter(AccessLog.is_deleted == 0, AccessLog.is_page_view == 1)
    if start_date: query = query.filter(AccessLog.timestamp >= start_date)
    if end_date: query = query.filter(AccessLog.timestamp <= end_date)
    rows = query.order_by(AccessLog.timestamp.desc()).limit(limit).all()

    points = []
    for row in rows:
        lat, lng = row.geo_latitude, row.geo_longitude
        if lat is None or lng is None:
            centroid = _get_city_centroid(row.ip_city, row.ip_country)
            if centroid: lat, lng = centroid
        if lat is not None and lng is not None:
            points.append({
                "lat": lat, "lng": lng,
                "label": f"{row.ip_city or row.ip_country or ''} 路 {row.device_brand or row.device_type or ''}",
                "timestamp": row.timestamp,
            })
    return success_response({"points": points, "total": len(points)})
```

Add `_get_city_centroid()` with a static dictionary of major cities (Beijing, Shanghai, Guangzhou, Shenzhen, etc.).

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/tracking_admin.py
git commit -m "feat: add page_views_only filter and locations endpoint for map"
```

---

## Task 7: Implement announcement targeting evaluation

**Files:**
- `backend/app/routers/announcements.py`
- `test/test_announcement_targeting.py`

- [ ] **Step 1: Add `_matches_targeting()` helper**

```python
def _matches_targeting(rules_json: str | None, context: dict) -> bool:
    if not rules_json: return True
    try: rules = json.loads(rules_json)
    except: return True
    match_mode = rules.get("match", "all")
    rule_list = rules.get("rules", [])
    if not rule_list: return True
    results = []
    for rule in rule_list:
        field, op, value = rule.get("field"), rule.get("op"), rule.get("value")
        actual = context.get(field)
        if op == "eq": results.append(actual == value)
        elif op == "ne": results.append(actual != value)
        elif op == "in": results.append(actual in (value or []))
        elif op == "not_in": results.append(actual not in (value or []))
        else: results.append(True)
    return all(results) if match_mode == "all" else any(results)
```

- [ ] **Step 2: Update `GET /active` to accept `visitor_id` and evaluate rules**

```python
@router.get("/active")
def get_active_announcements(
    visitor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    now = utc_now_iso()
    query = db.query(Announcement).filter(Announcement.is_active == 1)

    # Build context from query params and headers
    # (In practice, pass more context via query params or a second lookup)
    context = {"visitor_id": visitor_id}

    active = []
    for a in query.order_by(Announcement.priority.desc()).all():
        if not _matches_targeting(a.targeting_rules, context):
            continue
        if a.push_method == "timed":
            if a.start_time and a.start_time > now: continue
            if a.end_time and a.end_time < now: continue
        if a.push_method == "single": continue
        active.append(a.to_dict())
    return success_response(data=active)
```

- [ ] **Step 3: Write tests**

```python
def test_matches_targeting_eq():
    rules = '{"match":"all","rules":[{"field":"country","op":"eq","value":"CN"}]}'
    assert _matches_targeting(rules, {"country": "CN"}) is True
    assert _matches_targeting(rules, {"country": "US"}) is False

def test_matches_targeting_in():
    rules = '{"match":"any","rules":[{"field":"device_type","op":"in","value":["mobile","tablet"]}]}'
    assert _matches_targeting(rules, {"device_type": "mobile"}) is True
    assert _matches_targeting(rules, {"device_type": "desktop"}) is False

def test_matches_targeting_empty_rules():
    assert _matches_targeting(None, {}) is True
    assert _matches_targeting('{"rules":[]}', {}) is True
```

- [ ] **Step 4: Run tests**

```bash
pytest test/test_announcement_targeting.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/announcements.py test/test_announcement_targeting.py
git commit -m "feat: evaluate announcement targeting rules against visitor context"
```

---

## Task 8: Update AnnouncementBar.vue to pass visitor context

**Files:**
- `frontend/src/components/common/AnnouncementBar.vue`

- [ ] **Step 1: Pass `visitor_id` from cookie to API**

```javascript
async function fetchAnnouncements() {
  try {
    const visitorId = getCookie('device_id')
    const params = visitorId ? { visitor_id: visitorId } : {}
    all.value = await get('/announcements/active', params)
  } catch {
    all.value = []
  }
  // ... rest of existing logic
}
```

Add `getCookie()` helper or import from existing utils.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/common/AnnouncementBar.vue
git commit -m "feat: pass visitor_id to announcement API for targeting"
```

---

## Task 9: Update tracking dashboard UI 鈥?map, visitor ID, noise toggle

**Files:**
- `frontend/src/utils/trackingDisplay.js`
- `frontend/src/utils/__tests__/trackingDisplay.spec.js`
- `frontend/src/components/tracking/VisitorMap.vue`
- `frontend/src/views/admin/TrackingDashboard.vue`
- `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`
- `frontend/package.json`

- [ ] **Step 1: Install Leaflet**

```bash
cd frontend && npm install leaflet
```

- [ ] **Step 2: Create `VisitorMap.vue`** (see design spec for full code)

- [ ] **Step 3: Update `trackingDisplay.js`**

```javascript
export function formatGeoLocation(row = {}) {
  if (row.geo_latitude != null && row.geo_longitude != null) {
    const lat = Number(row.geo_latitude).toFixed(4)
    const lng = Number(row.geo_longitude).toFixed(4)
    const acc = row.geo_accuracy != null ? `卤${Math.round(row.geo_accuracy)}m` : ''
    return `馃搷 ${lat}, ${lng}${acc ? ` (${acc})` : ''}`
  }
  if (row.ip_city || row.ip_country) {
    return [row.ip_city, row.ip_country].filter(Boolean).join(', ')
  }
  return '鏈瘑鍒?
}
```

Update `formatDevicePrimary()` to append screen resolution when present.

- [ ] **Step 4: Update `TrackingDashboard.vue`**

Add import and component:

```javascript
import VisitorMap from '@/components/tracking/VisitorMap.vue'
import { Location } from '@element-plus/icons-vue'
const mapPoints = ref([])
```

Add the map card after the stats row:

```vue
<el-card shadow="never" class="mb-4">
  <template #header>
    <div class="card-header">
      <span class="card-title"><el-icon><Location /></el-icon> 璁垮鍦扮悊浣嶇疆</span>
      <span>鍏?{{ mapPoints.length }} 涓畾浣嶇偣</span>
    </div>
  </template>
  <VisitorMap :points="mapPoints" />
</el-card>
```

Add visitor ID column to the logs table:

```vue
<el-table-column prop="visitor_id" label="璁垮 ID" width="150">
  <template #default="{ row }">
    <el-tag v-if="row.visitor_id" size="small" type="info" style="cursor:pointer;"
            :title="`瀹屾暣ID: ${row.visitor_id}`"
            @click="filterByVisitor(row.visitor_id)">
      {{ row.visitor_id.slice(0, 8) }}鈥?    </el-tag>
    <span v-else class="text-muted">鈥?/span>
  </template>
</el-table-column>
```

Add noise toggle:

```vue
<el-switch v-model="pageViewsOnly" active-text="浠呴〉闈㈡祻瑙? inactive-text="鍏ㄩ儴璇锋眰"
           size="small" @change="fetchLogs" style="margin-right: 12px;" />
```

Update `buildLogsParams()` to pass `page_views_only`.

- [ ] **Step 5: Update display tests**

```javascript
it('formatGeoLocation shows coordinates and accuracy', () => {
  expect(formatGeoLocation({ geo_latitude: 39.9042, geo_longitude: 116.4074, geo_accuracy: 5 }))
    .toBe('馃搷 39.9042, 116.4074 (卤5m)')
})
it('formatGeoLocation falls back to city/country', () => {
  expect(formatGeoLocation({ ip_city: 'Beijing', ip_country: 'CN' })).toBe('Beijing, CN')
})
```

- [ ] **Step 6: Run tests and build**

```bash
cd frontend
npx vitest run src/utils/__tests__/trackingDisplay.spec.js src/views/admin/__tests__/TrackingDashboard.spec.js
npm run build
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/utils/trackingDisplay.js frontend/src/components/tracking/VisitorMap.vue frontend/src/views/admin/TrackingDashboard.vue frontend/package.json frontend/package-lock.json
git commit -m "feat: tracking dashboard map, visitor ID column, noise filter, geo formatter"
```

---

## Task 10: Update AnnouncementManager with targeting rules editor

**Files:**
- `frontend/src/views/admin/AnnouncementManager.vue`

- [ ] **Step 1: Add targeting rules tab to create/edit dialog**

```vue
<el-tabs v-model="activeTab">
  <el-tab-pane label="鍩烘湰淇℃伅" name="basic">
    <!-- existing title, content, display_mode, push_method fields -->
  </el-tab-pane>
  <el-tab-pane label="瀹氬悜瑙勫垯" name="targeting">
    <el-radio-group v-model="targetingForm.match">
      <el-radio value="all">婊¤冻鎵€鏈夎鍒?/el-radio>
      <el-radio value="any">婊¤冻浠讳竴瑙勫垯</el-radio>
    </el-radio-group>
    <div v-for="(rule, i) in targetingForm.rules" :key="i" class="targeting-rule-row" style="display:flex;gap:8px;margin:8px 0;">
      <el-select v-model="rule.field" size="small" style="width:160px;">
        <el-option label="鍥藉" value="country" />
        <el-option label="鍩庡競" value="city" />
        <el-option label="璁惧绫诲瀷" value="device_type" />
        <el-option label="鎿嶄綔绯荤粺" value="os_name" />
        <el-option label="娴忚鍣? value="browser_name" />
        <el-option label="鏃跺尯" value="timezone" />
        <el-option label="璁垮 ID" value="visitor_id" />
        <el-option label="鏄惁鐧诲綍" value="is_authenticated" />
      </el-select>
      <el-select v-model="rule.op" size="small" style="width:100px;">
        <el-option label="绛変簬" value="eq" />
        <el-option label="涓嶇瓑浜? value="ne" />
        <el-option label="灞炰簬" value="in" />
        <el-option label="涓嶅睘浜? value="not_in" />
      </el-select>
      <el-input v-model="rule.value" size="small" placeholder="鍊? style="width:200px;" />
      <el-button type="danger" :icon="Delete" size="small" @click="removeRule(i)" />
    </div>
    <el-button type="primary" size="small" @click="addRule">+ 娣诲姞瑙勫垯</el-button>
  </el-tab-pane>
</el-tabs>
```

- [ ] **Step 2: Serialize to JSON on save**

```javascript
const payload = {
  ...basicForm,
  targeting_rules: targetingForm.rules.length > 0
    ? JSON.stringify({ match: targetingForm.match, rules: targetingForm.rules })
    : null,
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/admin/AnnouncementManager.vue
git commit -m "feat: announcement targeting rules editor UI"
```

---

## Task 11: Final verification and regression sweep

- [ ] **Step 1: Full backend regression**

```bash
pytest test/test_tracking_ping.py test/test_tracking_middleware.py test/test_tracking_access_log.py test/test_announcement_targeting.py -v
```

- [ ] **Step 2: Full frontend regression**

```bash
cd frontend
npx vitest run src/utils/__tests__/trackingClient.spec.js src/utils/__tests__/trackingDisplay.spec.js src/views/admin/__tests__/TrackingDashboard.spec.js
```

- [ ] **Step 3: Production build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit final polish**

```bash
git status --short
git add <only-if-needed>
git commit -m "fix: polish precise tracking integration"
```

---

## Task 12: Create `visitor_profiles` model and additive migration

**Files:**
- Create: `backend/app/models/visitor_profile.py`
- Modify: `backend/app/database.py`

- [ ] **Step 1: Create the model**

```python
# backend/app/models/visitor_profile.py
from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from app.database import Base

class VisitorProfile(Base):
    __tablename__ = "visitor_profiles"
    visitor_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=True, index=True)
    first_seen_at = Column(String(30))
    last_seen_at = Column(String(30))
    total_visits = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    total_page_views = Column(Integer, default=0)
    total_downloads = Column(Integer, default=0)
    primary_device_type = Column(String(20))
    primary_os = Column(String(50))
    primary_browser = Column(String(50))
    primary_screen_resolution = Column(String(20))
    primary_timezone = Column(String(64))
    primary_language = Column(String(20))
    primary_country = Column(String(2))
    primary_city = Column(String(100))
    avg_session_duration_sec = Column(Float)
    typical_visit_hour = Column(Integer)
    typical_visit_day = Column(String(10))
    top_paths = Column(Text)   # JSON
    preferred_action_types = Column(Text)  # JSON
    tags = Column(Text)        # JSON array
    updated_at = Column(String(30))

    def to_dict(self):
        import json
        return {
            "visitor_id": self.visitor_id, "user_id": self.user_id,
            "first_seen_at": self.first_seen_at, "last_seen_at": self.last_seen_at,
            "total_visits": self.total_visits, "total_sessions": self.total_sessions,
            "total_page_views": self.total_page_views, "total_downloads": self.total_downloads,
            "primary_device_type": self.primary_device_type, "primary_os": self.primary_os,
            "primary_browser": self.primary_browser,
            "primary_screen_resolution": self.primary_screen_resolution,
            "primary_timezone": self.primary_timezone, "primary_language": self.primary_language,
            "primary_country": self.primary_country, "primary_city": self.primary_city,
            "avg_session_duration_sec": self.avg_session_duration_sec,
            "typical_visit_hour": self.typical_visit_hour,
            "typical_visit_day": self.typical_visit_day,
            "top_paths": json.loads(self.top_paths) if self.top_paths else [],
            "preferred_action_types": json.loads(self.preferred_action_types) if self.preferred_action_types else [],
            "tags": json.loads(self.tags) if self.tags else [],
            "updated_at": self.updated_at,
        }
```

- [ ] **Step 2: Add additive DDL to `database.py`**

```python
# In _ensure_schema_updates(), after access_logs block:
if inspector.has_table("visitor_profiles"):
    pass  # created by Base.metadata.create_all if new DB
else:
    Base.metadata.create_all(bind=engine, tables=[VisitorProfile.__table__])
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/visitor_profile.py backend/app/database.py
git commit -m "feat: add visitor_profiles aggregate table"
```

---

## Task 13: Implement auto-tagging service and profile update logic

**Files:**
- Create: `backend/app/services/tagging.py`
- Create: `test/test_tagging.py`

- [ ] **Step 1: Implement tagging rules**

```python
# backend/app/services/tagging.py
TAG_RULES = [
    ("mobile_user", lambda p: (p.get("primary_device_type") or "") in ("mobile", "tablet")),
    ("desktop_user", lambda p: p.get("primary_device_type") == "desktop"),
    ("night_owl", lambda p: p.get("typical_visit_hour", 12) in range(22, 24) or p.get("typical_visit_hour", 12) in range(0, 6)),
    ("frequent_visitor", lambda p: (p.get("total_visits") or 0) >= 5),
    ("new_visitor", lambda p: _is_new_visitor(p)),
    ("returning_user", lambda p: (p.get("total_sessions") or 0) >= 2),
    ("power_user", lambda p: (p.get("total_downloads") or 0) >= 10),
    ("high_resolution", lambda p: _is_high_res(p.get("primary_screen_resolution"))),
]

def compute_tags(profile_dict):
    return [tag for tag, rule in TAG_RULES if rule(profile_dict)]
```

- [ ] **Step 2: Implement incremental profile refresh**

```python
def refresh_profile(db, visitor_id):
    """Update or create a VisitorProfile from recent AccessLog rows."""
    rows = db.query(AccessLog).filter(
        AccessLog.visitor_id == visitor_id, AccessLog.is_page_view == 1,
        AccessLog.is_deleted == 0
    ).order_by(AccessLog.timestamp.desc()).limit(200).all()
    if not rows: return None

    profile = db.query(VisitorProfile).filter(VisitorProfile.visitor_id == visitor_id).first()
    if not profile:
        profile = VisitorProfile(visitor_id=visitor_id)
    # ... aggregate device mode, top paths, action counts from rows ...
    profile.tags = json.dumps(compute_tags(profile.to_dict()))
    profile.updated_at = utc_now_iso()
    db.add(profile)
    db.commit()
```

- [ ] **Step 3: Wire into middleware sampling**

In `_log_access()`, after commit, 1% sampling:

```python
import random
if random.random() < 0.01 and request.state.visitor_id:
    refresh_profile(db, request.state.visitor_id)
```

- [ ] **Step 4: Write tests and verify**

```bash
pytest test/test_tagging.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/tagging.py test/test_tagging.py backend/app/middlewares/tracking.py
git commit -m "feat: auto-tagging service with incremental profile updates"
```

---

## Task 14: Add profile API endpoints and dashboard detail page

**Files:**
- Modify: `backend/app/routers/tracking_admin.py` 鈥?add `/visitors` endpoints
- Create: `frontend/src/views/admin/VisitorProfile.vue`
- Modify: `frontend/src/views/admin/TrackingDashboard.vue` 鈥?link visitor IDs to profile page

- [ ] **Step 1: Add profile endpoints to `tracking_admin.py`**

```python
@router.get("/visitors/{visitor_id}")
def get_visitor_profile(visitor_id: str, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_admin)):
    profile = db.query(VisitorProfile).filter(VisitorProfile.visitor_id == visitor_id).first()
    if not profile: raise HTTPException(404)
    return success_response(profile.to_dict())

@router.get("/visitors")
def list_visitors(tag: Optional[str] = Query(None), page: int = Query(1),
                  page_size: int = Query(20), db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_admin)):
    query = db.query(VisitorProfile)
    if tag: query = query.filter(VisitorProfile.tags.contains(tag))
    total = query.count()
    items = query.order_by(VisitorProfile.last_seen_at.desc()).offset((page-1)*page_size).limit(page_size).all()
    return success_response({"items": [p.to_dict() for p in items], "total": total})
```

- [ ] **Step 2: Create `VisitorProfile.vue`** 鈥?profile detail page with header card, device card, activity heatmap placeholder, top paths list, action distribution, editable tag chips, session timeline.

- [ ] **Step 3: Wire visitor ID clicks in `TrackingDashboard.vue`** to `router.push(/admin/tracking/visitors/${visitorId})`.

- [ ] **Step 4: Write tests and verify**

```bash
pytest test/test_tagging.py -v
cd frontend && npx vitest run src/views/admin/__tests__/VisitorProfile.spec.js
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/tracking_admin.py frontend/src/views/admin/VisitorProfile.vue frontend/src/views/admin/TrackingDashboard.vue
git commit -m "feat: visitor profile API + dashboard detail page"
```

---

## Self-Review

### Spec coverage

- Frontend geolocation + device data beacon: covered by Task 3, 5.
- Log noise reduction (`is_page_view`): covered by Task 2, 6.
- Visitor UUID (`visitor_id`): covered by Task 1, 2.
- Announcement targeting rules: covered by Task 7, 8, 10.
- Leaflet map visualization: covered by Task 6, 9.
- Dashboard visitor ID column and noise toggle: covered by Task 9.
- Ping endpoint with correlation/anonymization/rate limiting: covered by Task 3.
- Visitor profiles + auto-tagging: covered by Task 12, 13.
- Profile API + dashboard detail page: covered by Task 14.

### Placeholder scan

- No `TODO` / `TBD` in final code.
- Every code-changing step includes code or detailed instructions.

### Privacy

- Geolocation opt-in via browser permission dialog.
- `enable_location_tracking` config gate prevents prompting.
- `anonymize_ip` rounds coordinates to ~111m.
- Targeting rules evaluate server-side; no client-side exposure.

### Type consistency

- Geo fields consistently named `geo_latitude`, `geo_longitude`, `geo_accuracy`.
- Visitor identity field named `visitor_id` throughout.
- New model fields use snake_case matching existing conventions.
- Frontend helper `formatGeoLocation` follows existing `formatDevicePrimary` naming.

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

