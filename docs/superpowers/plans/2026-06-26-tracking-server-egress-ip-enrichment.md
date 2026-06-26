# Tracking Server Egress IP Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add IPPure-backed server-egress IP enrichment to the admin tracking dashboard without changing visitor-log semantics, and render that shared context in the access-info card plus detail dialog.

**Architecture:** Backend fetches `https://my.ippure.com/v1/info` through a small service layer with short-lived in-memory caching and graceful failure handling. Tracking admin APIs expose the normalized result as shared `server_ip_context`, while frontend helper utilities format that shared payload into concise card lines and a dedicated “服务器出口 IP 情报” detail section.

**Tech Stack:** FastAPI, requests, in-memory cache service, Vue 3, Element Plus, Vitest, Vue Test Utils, Pytest

---

## File Structure

### Backend

- Create: `backend/app/services/ippure_service.py`
  - Fetch and normalize the server-egress IPPure payload.
  - Reuse `cache_service` for short TTL caching.
  - Never raise outward on remote failure.
- Create: `backend/tests/test_ippure_service.py`
  - Cover normalization, cache fill, and stale-cache fallback.
- Modify: `backend/app/routers/tracking_admin.py`
  - Import the new IPPure service.
  - Append top-level `server_ip_context` to log list payloads.
  - Append `server_ip_context` to log detail payloads.
- Modify: `test/test_tracking_access_log.py`
  - Cover direct router-function list payload enrichment.
- Modify: `backend/tests/test_tracking.py`
  - Cover API detail payload enrichment.

### Frontend

- Modify: `frontend/src/utils/trackingDisplay.js`
  - Add focused server-egress summary/detail formatters.
  - Extend `buildTrackingInfoCard` to accept shared server context.
- Modify: `frontend/src/utils/__tests__/trackingDisplay.spec.js`
  - Cover summary-line generation and detail-field expansion.
- Modify: `frontend/src/views/admin/TrackingDashboard.vue`
  - Store shared `server_ip_context` from the logs response.
  - Feed shared context into card rendering.
  - Render a dedicated `服务器出口 IP 情报` section in the detail dialog.
- Modify: `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`
  - Verify card enrichment and detail-dialog rendering.
- Modify: `frontend/src/utils/__tests__/frontend-regressions.spec.js`
  - Add a source-level guard that the dashboard keeps the shared `server_ip_context` path and dedicated detail section.

---

### Task 1: Add the backend IPPure server-egress service

**Files:**
- Create: `backend/app/services/ippure_service.py`
- Test: `backend/tests/test_ippure_service.py`

- [ ] **Step 1: Write the failing backend service tests**

Create `backend/tests/test_ippure_service.py` with:

```python
from app.services.cache_service import cache_service
from app.services import ippure_service


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status={self.status_code}")

    def json(self):
        return self._payload


def test_fetch_server_ip_context_normalizes_payload_and_populates_cache(monkeypatch):
    cache_service.delete(ippure_service.IPPURE_CACHE_KEY)

    def fake_get(url, timeout, headers):
        assert url == ippure_service.IPPURE_INFO_URL
        assert timeout == (1.0, 3.0)
        assert headers["User-Agent"] == "DocShopTracking/1.0"
        return DummyResponse(
            {
                "ip": "112.224.158.50",
                "asn": 4837,
                "asOrganization": "China Unicom Shandong province network",
                "country": "China",
                "countryCode": "CN",
                "region": "Shandong",
                "regionCode": "SD",
                "city": "Qingdao",
                "timezone": "Asia/Shanghai",
                "longitude": "120.38042",
                "latitude": "36.06488",
                "postalCode": "266000",
                "fraudScore": 0,
                "isResidential": True,
                "isBroadcast": False,
            }
        )

    monkeypatch.setattr(ippure_service.requests, "get", fake_get)

    payload = ippure_service.fetch_server_ip_context(force_refresh=True)

    assert payload == {
        "source": "ippure_server_egress",
        "ip": "112.224.158.50",
        "asn": 4837,
        "asOrganization": "China Unicom Shandong province network",
        "country": "China",
        "countryCode": "CN",
        "region": "Shandong",
        "regionCode": "SD",
        "city": "Qingdao",
        "timezone": "Asia/Shanghai",
        "longitude": "120.38042",
        "latitude": "36.06488",
        "postalCode": "266000",
        "fraudScore": 0,
        "isResidential": True,
        "isBroadcast": False,
    }
    assert cache_service.get(ippure_service.IPPURE_CACHE_KEY)["ip"] == "112.224.158.50"


def test_fetch_server_ip_context_returns_stale_cache_when_remote_fetch_fails(monkeypatch):
    stale_payload = {
        "source": "ippure_server_egress",
        "ip": "112.224.158.50",
        "asn": 4837,
        "asOrganization": "China Unicom Shandong province network",
        "country": "China",
        "countryCode": "CN",
        "region": "Shandong",
        "regionCode": "SD",
        "city": "Qingdao",
        "timezone": "Asia/Shanghai",
        "longitude": "120.38042",
        "latitude": "36.06488",
        "postalCode": "266000",
        "fraudScore": 0,
        "isResidential": True,
        "isBroadcast": False,
    }
    cache_service.set(ippure_service.IPPURE_CACHE_KEY, stale_payload, ttl=60)

    def fake_get(url, timeout, headers):
        raise RuntimeError("ippure unavailable")

    monkeypatch.setattr(ippure_service.requests, "get", fake_get)

    payload = ippure_service.fetch_server_ip_context(force_refresh=True)

    assert payload == stale_payload
```

- [ ] **Step 2: Run the focused backend service tests to confirm RED**

Run:

```powershell
pytest backend/tests/test_ippure_service.py -v
```

Expected: FAIL with `ModuleNotFoundError` or missing `fetch_server_ip_context`.

- [ ] **Step 3: Implement the minimal IPPure service**

Create `backend/app/services/ippure_service.py` with:

```python
from __future__ import annotations

from typing import Any

import requests

from app.services.cache_service import cache_service
from app.utils.logger import get_logger


IPPURE_INFO_URL = "https://my.ippure.com/v1/info"
IPPURE_CACHE_KEY = "tracking:server_ip_context"
IPPURE_CACHE_TTL_SECONDS = 300

ippure_logger = get_logger("services.ippure_service")


def _normalize_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    ip = payload.get("ip")
    if ip is None or str(ip).strip() == "":
        return None

    return {
        "source": "ippure_server_egress",
        "ip": ip,
        "asn": payload.get("asn"),
        "asOrganization": payload.get("asOrganization"),
        "country": payload.get("country"),
        "countryCode": payload.get("countryCode"),
        "region": payload.get("region"),
        "regionCode": payload.get("regionCode"),
        "city": payload.get("city"),
        "timezone": payload.get("timezone"),
        "longitude": payload.get("longitude"),
        "latitude": payload.get("latitude"),
        "postalCode": payload.get("postalCode"),
        "fraudScore": payload.get("fraudScore"),
        "isResidential": payload.get("isResidential"),
        "isBroadcast": payload.get("isBroadcast"),
    }


def fetch_server_ip_context(force_refresh: bool = False) -> dict[str, Any] | None:
    cached = None if force_refresh else cache_service.get(IPPURE_CACHE_KEY)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            IPPURE_INFO_URL,
            timeout=(1.0, 3.0),
            headers={"User-Agent": "DocShopTracking/1.0"},
        )
        response.raise_for_status()
        normalized = _normalize_payload(response.json())
        if normalized is not None:
            cache_service.set(IPPURE_CACHE_KEY, normalized, ttl=IPPURE_CACHE_TTL_SECONDS)
        return normalized
    except Exception as exc:
        ippure_logger.warning("fetch_server_ip_context failed: %s", exc)
        return cache_service.get(IPPURE_CACHE_KEY)
```

- [ ] **Step 4: Re-run the focused backend service tests to confirm GREEN**

Run:

```powershell
pytest backend/tests/test_ippure_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit the backend service**

```bash
git add backend/app/services/ippure_service.py backend/tests/test_ippure_service.py
git commit -m "feat: add ippure server egress tracking service"
```

---

### Task 2: Enrich tracking admin APIs with shared `server_ip_context`

**Files:**
- Modify: `backend/app/routers/tracking_admin.py`
- Modify: `test/test_tracking_access_log.py`
- Modify: `backend/tests/test_tracking.py`

- [ ] **Step 1: Write the failing list/detail enrichment tests**

Add this test to `test/test_tracking_access_log.py`:

```python
from app.routers import tracking_admin


def test_admin_access_logs_include_server_ip_context(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        db.add(
            AccessLog(
                id="page-view-log",
                timestamp="2026-06-23T10:00:00Z",
                ip_address="127.0.0.1",
                visitor_id="visitor-a",
                is_page_view=1,
                request_path="/share/demo",
                response_status=200,
                response_time_ms=12,
                session_id="session-a",
            )
        )
        db.commit()

        monkeypatch.setattr(
            tracking_admin,
            "fetch_server_ip_context",
            lambda: {
                "source": "ippure_server_egress",
                "ip": "112.224.158.50",
                "city": "Qingdao",
                "region": "Shandong",
                "countryCode": "CN",
            },
        )

        result = get_access_logs(
            page=1,
            page_size=50,
            ip=None,
            user_id=None,
            device_type=None,
            page_views_only=1,
            visitor_id="visitor-a",
            start_date=None,
            end_date=None,
            db=db,
            current_user=SimpleNamespace(id="admin"),
        )

        data = result.data
        assert data["server_ip_context"]["source"] == "ippure_server_egress"
        assert data["server_ip_context"]["ip"] == "112.224.158.50"
        assert data["items"][0]["id"] == "page-view-log"
    finally:
        db.close()
```

Add this test to `backend/tests/test_tracking.py` inside `TestTrackingAPI`:

```python
    def test_get_access_log_detail_includes_server_ip_context(self, client, auth_headers, access_log, monkeypatch):
        from app.routers import tracking_admin

        monkeypatch.setattr(
            tracking_admin,
            "fetch_server_ip_context",
            lambda: {
                "source": "ippure_server_egress",
                "ip": "112.224.158.50",
                "asn": 4837,
                "asOrganization": "China Unicom Shandong province network",
            },
        )

        response = client.get(f"/api/v1/admin/tracking/logs/{access_log.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == access_log.id
        assert data["server_ip_context"]["ip"] == "112.224.158.50"
        assert data["server_ip_context"]["asn"] == 4837
```

- [ ] **Step 2: Run the focused tracking backend tests to confirm RED**

Run:

```powershell
pytest test/test_tracking_access_log.py backend/tests/test_tracking.py -k server_ip_context -v
```

Expected: FAIL because `tracking_admin` does not yet expose `server_ip_context`.

- [ ] **Step 3: Wire `server_ip_context` into tracking admin responses**

Update `backend/app/routers/tracking_admin.py`:

```python
from app.services.ippure_service import fetch_server_ip_context
```

Then update the list/detail handlers:

```python
@router.get("/logs", response_model=ApiResponse)
def get_access_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    ip: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    page_views_only: Optional[int] = Query(None, ge=0, le=1),
    visitor_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    query = db.query(AccessLog).filter(AccessLog.is_deleted == 0)

    if ip:
        safe_ip = ip.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(AccessLog.ip_address.like(f"%{safe_ip}%", escape="\\"))
    if user_id:
        query = query.filter(AccessLog.user_id == user_id)
    if device_type:
        query = query.filter(AccessLog.device_type == device_type)
    if page_views_only:
        query = query.filter(AccessLog.is_page_view == 1)
    if visitor_id:
        query = query.filter(AccessLog.visitor_id == visitor_id)
    if start_date:
        query = query.filter(AccessLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AccessLog.timestamp <= end_date)

    total = query.count()
    logs = query.order_by(AccessLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    server_ip_context = fetch_server_ip_context()

    return success_response(
        {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [log.to_dict() for log in logs],
            "server_ip_context": server_ip_context,
        }
    )


@router.get("/logs/{log_id}", response_model=ApiResponse)
def get_access_log_detail(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    log = db.query(AccessLog).filter(
        AccessLog.id == log_id,
        AccessLog.is_deleted == 0
    ).first()

    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="日志不存在")

    payload = log.to_dict(include_raw=True)
    payload["server_ip_context"] = fetch_server_ip_context()
    return success_response(payload)
```

- [ ] **Step 4: Re-run the focused tracking backend tests to confirm GREEN**

Run:

```powershell
pytest test/test_tracking_access_log.py backend/tests/test_tracking.py -k server_ip_context -v
```

Expected: PASS.

- [ ] **Step 5: Commit the tracking API enrichment**

```bash
git add backend/app/routers/tracking_admin.py test/test_tracking_access_log.py backend/tests/test_tracking.py
git commit -m "feat: expose server ip context in tracking admin api"
```

---

### Task 3: Extend frontend tracking display helpers for server-egress summaries

**Files:**
- Modify: `frontend/src/utils/trackingDisplay.js`
- Modify: `frontend/src/utils/__tests__/trackingDisplay.spec.js`

- [ ] **Step 1: Write the failing frontend helper tests**

Add these tests to `frontend/src/utils/__tests__/trackingDisplay.spec.js`:

```javascript
import {
  buildServerIpContextDetails,
  buildTrackingInfoCard,
} from '../trackingDisplay'


it('adds server egress IP summaries to the tracking info card when context exists', () => {
  const row = {
    device_display_name: 'Huawei P40 / ANA-AL00',
    device_type: 'mobile',
    os_name: 'Android',
    os_version: '14',
    browser_name: 'Chrome',
    browser_version: '126',
    ip_city: 'Beijing',
    ip_country: 'CN',
    client_timezone: 'Asia/Shanghai',
    client_language: 'zh-CN',
  }
  const serverIpContext = {
    source: 'ippure_server_egress',
    ip: '112.224.158.50',
    city: 'Qingdao',
    region: 'Shandong',
    countryCode: 'CN',
    fraudScore: 0,
    isResidential: true,
    isBroadcast: false,
    asn: 4837,
    asOrganization: 'China Unicom Shandong province network',
  }

  expect(buildTrackingInfoCard(row, serverIpContext)).toEqual({
    title: 'Huawei P40 / ANA-AL00',
    deviceTypeText: '移动端',
    secondary: 'Android 14 · Chrome 126',
    location: 'Beijing, CN',
    environment: 'Asia/Shanghai · zh-CN',
    serverIpSummary: '服务器出口IP · Qingdao, Shandong, CN',
    serverIpRisk: '风险 0 · 住宅IP · 非广播',
    serverIpNetwork: 'AS4837 · China Unicom Shandong province network',
  })
})


it('builds a dedicated server IP detail list and degrades cleanly when absent', () => {
  const serverIpContext = {
    source: 'ippure_server_egress',
    ip: '112.224.158.50',
    country: 'China',
    countryCode: 'CN',
    region: 'Shandong',
    city: 'Qingdao',
    postalCode: '266000',
    timezone: 'Asia/Shanghai',
    asn: 4837,
    asOrganization: 'China Unicom Shandong province network',
    fraudScore: 0,
    isResidential: true,
    isBroadcast: false,
  }

  expect(buildServerIpContextDetails(serverIpContext)).toEqual([
    { label: '出口 IP', value: '112.224.158.50' },
    { label: '国家/地区', value: 'China / CN' },
    { label: '省/州', value: 'Shandong' },
    { label: '城市', value: 'Qingdao' },
    { label: '邮编', value: '266000' },
    { label: '时区', value: 'Asia/Shanghai' },
    { label: 'ASN', value: '4837' },
    { label: 'AS 组织', value: 'China Unicom Shandong province network' },
    { label: '风险分', value: '0' },
    { label: '住宅 IP', value: '是' },
    { label: '广播 IP', value: '否' },
  ])

  expect(buildTrackingInfoCard({}, null).serverIpSummary).toBe('')
  expect(buildTrackingInfoCard({}, null).serverIpRisk).toBe('')
  expect(buildTrackingInfoCard({}, null).serverIpNetwork).toBe('')
  expect(buildServerIpContextDetails(null)).toEqual([])
})
```

- [ ] **Step 2: Run the focused frontend helper tests to confirm RED**

Run:

```powershell
npm --prefix frontend test -- run src/utils/__tests__/trackingDisplay.spec.js
```

Expected: FAIL because `buildTrackingInfoCard` does not yet accept shared server context and `buildServerIpContextDetails` does not exist.

- [ ] **Step 3: Implement the minimal frontend server-context helpers**

Update `frontend/src/utils/trackingDisplay.js` with:

```javascript
function normalizeLooseText(value) {
  if (value === null || value === undefined) return ''
  return String(value).trim()
}

export function formatServerIpGeoSummary(serverIpContext = null) {
  if (!serverIpContext || typeof serverIpContext !== 'object') return ''
  const parts = [
    normalizeLooseText(serverIpContext.city),
    normalizeLooseText(serverIpContext.region),
    normalizeLooseText(serverIpContext.countryCode || serverIpContext.country),
  ].filter(Boolean)
  return parts.length ? `服务器出口IP · ${parts.join(', ')}` : ''
}

export function formatServerIpRiskSummary(serverIpContext = null) {
  if (!serverIpContext || typeof serverIpContext !== 'object') return ''
  const parts = []
  const fraudScore = toFiniteNumber(serverIpContext.fraudScore)
  if (fraudScore !== null) parts.push(`风险 ${fraudScore}`)
  if (serverIpContext.isResidential === true) parts.push('住宅IP')
  else if (serverIpContext.isResidential === false) parts.push('非住宅IP')
  if (serverIpContext.isBroadcast === true) parts.push('广播')
  else if (serverIpContext.isBroadcast === false) parts.push('非广播')
  return parts.join(' · ')
}

export function formatServerIpNetworkSummary(serverIpContext = null) {
  if (!serverIpContext || typeof serverIpContext !== 'object') return ''
  const asn = normalizeLooseText(serverIpContext.asn)
  const organization = normalizeLooseText(serverIpContext.asOrganization)
  if (asn && organization) return `AS${asn} · ${organization}`
  if (asn) return `AS${asn}`
  return organization
}

export function buildServerIpContextDetails(serverIpContext = null) {
  if (!serverIpContext || typeof serverIpContext !== 'object') return []

  const countryText = [serverIpContext.country, serverIpContext.countryCode]
    .map(normalizeLooseText)
    .filter(Boolean)
    .join(' / ')

  const boolLabel = (value) => {
    if (value === true) return '是'
    if (value === false) return '否'
    return '-'
  }

  return [
    { label: '出口 IP', value: toDetailValue(serverIpContext.ip) },
    { label: '国家/地区', value: toDetailValue(countryText) },
    { label: '省/州', value: toDetailValue(serverIpContext.region) },
    { label: '城市', value: toDetailValue(serverIpContext.city) },
    { label: '邮编', value: toDetailValue(serverIpContext.postalCode) },
    { label: '时区', value: toDetailValue(serverIpContext.timezone) },
    { label: 'ASN', value: toDetailValue(serverIpContext.asn) },
    { label: 'AS 组织', value: toDetailValue(serverIpContext.asOrganization) },
    { label: '风险分', value: toDetailValue(serverIpContext.fraudScore) },
    { label: '住宅 IP', value: boolLabel(serverIpContext.isResidential) },
    { label: '广播 IP', value: boolLabel(serverIpContext.isBroadcast) },
  ]
}

export function buildTrackingInfoCard(row = {}, serverIpContext = null) {
  const toInfoCardFallback = (value) => (value === UNKNOWN_LABEL ? '-' : withDash(value))
  const title = toInfoCardFallback(formatDevicePrimary(row))
  const deviceTypeText = toInfoCardFallback(getDeviceTypeText(normalizeDeviceType(row.device_type) || row.device_type))
  const secondary = toInfoCardFallback(formatDeviceSecondary(row))
  const location = toInfoCardFallback(formatGeoLocation(row))
  const environment = toInfoCardFallback(formatClientEnvironment(row))

  return {
    title,
    deviceTypeText,
    secondary,
    location,
    environment,
    serverIpSummary: formatServerIpGeoSummary(serverIpContext),
    serverIpRisk: formatServerIpRiskSummary(serverIpContext),
    serverIpNetwork: formatServerIpNetworkSummary(serverIpContext),
  }
}
```

- [ ] **Step 4: Re-run the focused frontend helper tests to confirm GREEN**

Run:

```powershell
npm --prefix frontend test -- run src/utils/__tests__/trackingDisplay.spec.js
```

Expected: PASS.

- [ ] **Step 5: Commit the frontend helper extension**

```bash
git add frontend/src/utils/trackingDisplay.js frontend/src/utils/__tests__/trackingDisplay.spec.js
git commit -m "feat: add server ip summaries to tracking display helpers"
```

---

### Task 4: Render the shared server-egress context in TrackingDashboard

**Files:**
- Modify: `frontend/src/views/admin/TrackingDashboard.vue`
- Modify: `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`

- [ ] **Step 1: Write the failing dashboard rendering test**

Update `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js` so the `/admin/tracking/logs` mock returns `server_ip_context`:

```javascript
    if (url === '/admin/tracking/logs') {
      return Promise.resolve({
        total: 2,
        server_ip_context: {
          source: 'ippure_server_egress',
          ip: '112.224.158.50',
          city: 'Qingdao',
          region: 'Shandong',
          countryCode: 'CN',
          fraudScore: 0,
          isResidential: true,
          isBroadcast: false,
          asn: 4837,
          asOrganization: 'China Unicom Shandong province network',
          timezone: 'Asia/Shanghai',
          postalCode: '266000',
        },
        items: [
          {
            id: 'log-1',
            timestamp: '2026-06-16T12:00:00.789123Z',
            ip_address: '127.0.0.1',
            visitor_id: 'visitor-abcdef-123456',
            is_page_view: true,
            geo_latitude: 39.904212,
            geo_longitude: 116.407389,
            geo_accuracy: 8.5,
            client_timezone: 'Asia/Shanghai',
            client_language: 'zh-CN',
            device_type: 'desktop',
            device_brand: 'Microsoft',
            device_model: 'PC',
            os_name: 'Windows',
            os_version: '11',
            browser_name: 'Edge',
            browser_version: '149',
            request_path: '/demo',
            response_status: 200,
            response_time_ms: 10,
          },
        ],
      })
    }
```

Then add this assertion block inside the main dashboard test:

```javascript
    const accessCard = wrapper.find('.tracking-info-card')
    expect(accessCard.exists()).toBe(true)
    expect(accessCard.text()).toContain('服务器出口IP · Qingdao, Shandong, CN')
    expect(accessCard.text()).toContain('风险 0 · 住宅IP · 非广播')
    expect(accessCard.text()).toContain('AS4837 · China Unicom Shandong province network')

    await accessCard.trigger('click')

    expect(wrapper.text()).toContain('服务器出口 IP 情报')
    expect(wrapper.text()).toContain('112.224.158.50')
    expect(wrapper.text()).toContain('266000')
    expect(wrapper.text()).toContain('China Unicom Shandong province network')
```

- [ ] **Step 2: Run the focused dashboard test to confirm RED**

Run:

```powershell
npm --prefix frontend test -- run src/views/admin/__tests__/TrackingDashboard.spec.js
```

Expected: FAIL because the dashboard does not yet consume or render `server_ip_context`.

- [ ] **Step 3: Wire the shared `server_ip_context` into the dashboard**

Update the helper import in `frontend/src/views/admin/TrackingDashboard.vue`:

```javascript
import {
  buildServerIpContextDetails,
  buildTrackingInfoCard,
  buildTrackingTechnicalDetails,
  formatTrackingBusiness,
  getDeviceTypeText,
  getDistributionLabel,
} from '@/utils/trackingDisplay'
```

Add the new computed state:

```javascript
const serverIpContext = computed(() => logs.value?.server_ip_context || null)

const selectedAccessInfoCard = computed(() => (
  selectedAccessInfoLog.value ? buildTrackingInfoCard(selectedAccessInfoLog.value, serverIpContext.value) : null
))

const selectedAccessInfoTechnicalDetails = computed(() => (
  selectedAccessInfoLog.value ? buildTrackingTechnicalDetails(selectedAccessInfoLog.value) : []
))

const selectedAccessInfoServerContextDetails = computed(() => (
  buildServerIpContextDetails(serverIpContext.value)
))

function getTrackingInfoCard(row = {}) {
  return buildTrackingInfoCard(row, serverIpContext.value)
}
```

Then extend the card body and detail dialog:

```vue
<div class="tracking-info-card__meta">{{ getTrackingInfoCard(row).location }}</div>
<div class="tracking-info-card__meta">{{ getTrackingInfoCard(row).environment }}</div>
<div v-if="getTrackingInfoCard(row).serverIpSummary" class="tracking-info-card__meta tracking-info-card__meta--server">
  {{ getTrackingInfoCard(row).serverIpSummary }}
</div>
<div v-if="getTrackingInfoCard(row).serverIpRisk" class="tracking-info-card__meta tracking-info-card__meta--server">
  {{ getTrackingInfoCard(row).serverIpRisk }}
</div>
<div v-if="getTrackingInfoCard(row).serverIpNetwork" class="tracking-info-card__meta tracking-info-card__meta--server">
  {{ getTrackingInfoCard(row).serverIpNetwork }}
</div>
```

```vue
<el-divider v-if="selectedAccessInfoServerContextDetails.length">服务器出口 IP 情报</el-divider>

<el-descriptions
  v-if="selectedAccessInfoServerContextDetails.length"
  :column="2"
  border
  class="access-info-server-context"
>
  <el-descriptions-item
    v-for="item in selectedAccessInfoServerContextDetails"
    :key="`server-${item.label}`"
    :label="item.label"
  >
    {{ item.value }}
  </el-descriptions-item>
</el-descriptions>

<el-divider>技术详情</el-divider>
```

Also add the server-line style:

```css
.tracking-info-card__meta--server {
  color: var(--el-color-primary);
}
```

- [ ] **Step 4: Re-run the focused dashboard test to confirm GREEN**

Run:

```powershell
npm --prefix frontend test -- run src/views/admin/__tests__/TrackingDashboard.spec.js
```

Expected: PASS.

- [ ] **Step 5: Commit the dashboard rendering change**

```bash
git add frontend/src/views/admin/TrackingDashboard.vue frontend/src/views/admin/__tests__/TrackingDashboard.spec.js
git commit -m "feat: show server egress ip context in tracking dashboard"
```

---

### Task 5: Add regression guards and run the verification sweep

**Files:**
- Modify: `frontend/src/utils/__tests__/frontend-regressions.spec.js`
- Test: `backend/tests/test_ippure_service.py`
- Test: `test/test_tracking_access_log.py`
- Test: `backend/tests/test_tracking.py`
- Test: `frontend/src/utils/__tests__/trackingDisplay.spec.js`
- Test: `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`
- Test: `frontend/src/utils/__tests__/frontend-regressions.spec.js`

- [ ] **Step 1: Add the source-level regression guard**

Append this test to `frontend/src/utils/__tests__/frontend-regressions.spec.js`:

```javascript
it('TrackingDashboard keeps shared server_ip_context rendering separate from visitor log fields', () => {
  const source = readSource('src/views/admin/TrackingDashboard.vue')

  expect(source).toContain('server_ip_context')
  expect(source).toContain('buildServerIpContextDetails')
  expect(source).toContain('服务器出口 IP 情报')
  expect(source).toContain('tracking-info-card__meta--server')
})
```

- [ ] **Step 2: Run the focused regression guard**

Run:

```powershell
npm --prefix frontend test -- run src/utils/__tests__/frontend-regressions.spec.js
```

Expected: PASS once Task 4 is complete.

- [ ] **Step 3: Run the targeted backend verification suite**

Run:

```powershell
pytest backend/tests/test_ippure_service.py test/test_tracking_access_log.py backend/tests/test_tracking.py -k "ippure or server_ip_context" -v
```

Expected: PASS.

- [ ] **Step 4: Run the targeted frontend verification suite**

Run:

```powershell
npm --prefix frontend test -- run src/utils/__tests__/trackingDisplay.spec.js src/views/admin/__tests__/TrackingDashboard.spec.js src/utils/__tests__/frontend-regressions.spec.js
```

Expected: PASS.

- [ ] **Step 5: Build the frontend for compile-time verification**

Run:

```powershell
npm --prefix frontend run build
```

Expected: build succeeds.

- [ ] **Step 6: Commit the regression coverage and final verification**

```bash
git add frontend/src/utils/__tests__/frontend-regressions.spec.js
git commit -m "test: verify tracking server egress ip enrichment"
```

---

## Self-Review Notes

- Spec coverage: backend fetch/caching, tracking API enrichment, frontend card lines, dedicated detail section, failure-safe behavior, and targeted tests all map directly to tasks.
- Placeholder scan: no `TODO`, `TBD`, or hand-wavy “add handling later” steps remain.
- Type consistency: `server_ip_context`, `fetch_server_ip_context`, `buildServerIpContextDetails`, and the three card summary fields (`serverIpSummary`, `serverIpRisk`, `serverIpNetwork`) are named consistently across tasks.
