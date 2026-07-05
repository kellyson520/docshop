# Tracking Device Parsing and Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade admin tracking so device rows show normalized brand/model details, analytics cards use a compact browser-first layout, and backend parsing correctly uses Client Hints, User-Agent, and referer normalization.

**Architecture:** The backend keeps `TrackingMiddleware` as the single source of device/browser/platform parsing, enriched with Client Hints and referer normalization before writing `AccessLog`. The frontend consumes those normalized fields through focused formatter helpers and a reshaped `TrackingDashboard.vue` layout that promotes browser distribution as the primary analytics card while keeping device/OS cards compact.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite additive schema updates, Vue 3, Element Plus, Vitest, Pytest

---

## File Structure

### Backend

- Modify: `backend/app/middlewares/tracking.py`
  - Add Client Hints parsing.
  - Add referer normalization.
  - Add signal-merging helpers so `sec-ch-*` wins for browser/platform/mobile classification while UA still fills model/brand.
- Modify: `backend/app/models/access_log.py`
  - Add normalized referer columns.
  - Return those fields from `to_dict()`.
- Modify: `backend/app/database.py`
  - Extend additive schema updates for existing `access_logs` tables.
- Create: `test/test_tracking_middleware.py`
  - Unit tests for Client Hints parsing, referer normalization, Android cleanup, and Windows/Edge normalization.
- Create: `test/test_tracking_access_log.py`
  - Unit tests for `AccessLog.to_dict()` and additive `access_logs` column SQL generation.

### Frontend

- Modify: `frontend/src/utils/trackingDisplay.js`
  - Add device primary/secondary/tooltip formatters and compact fallback rules.
- Modify: `frontend/src/utils/__tests__/trackingDisplay.spec.js`
  - Cover the new formatter behavior.
- Modify: `frontend/src/views/admin/TrackingDashboard.vue`
  - Replace the upper three-table split with browser primary card + right-side compact cards.
  - Upgrade the log `设备` cell into a structured three-line block.
- Create: `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`
  - Verify the browser-first layout structure and device summary rendering.

## Task 1: Backend parsing helpers for Client Hints, referer, and normalized device signals

**Files:**
- Create: `test/test_tracking_middleware.py`
- Modify: `backend/app/middlewares/tracking.py`

- [ ] **Step 1: Write the failing backend parsing tests**

```python
from app.middlewares.tracking import TrackingMiddleware


def test_parse_client_hints_prefers_edge_on_windows():
    middleware = TrackingMiddleware(app=None)
    headers = {
        "sec-ch-ua": '"Microsoft Edge";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0"
        ),
    }

    hints = middleware._parse_client_hints(headers)

    assert hints["browser_name"] == "Edge"
    assert hints["browser_version"] == "149"
    assert hints["os_name"] == "Windows"
    assert hints["device_type"] == "desktop"


def test_parse_referer_normalizes_external_domain():
    middleware = TrackingMiddleware(app=None)

    referer = middleware._parse_referer(
        "https://www.limestart.cn/",
        request_host="docshop.local",
    )

    assert referer["referer_host"] == "www.limestart.cn"
    assert referer["referer_domain"] == "limestart.cn"
    assert referer["referer_type"] == "external"


def test_simple_user_agent_parse_cleans_android_model_noise():
    middleware = TrackingMiddleware(app=None)
    ua = (
        "Mozilla/5.0 (Linux; Android 14; Xiaomi 14 Build/UKQ1.230917.001; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.0.0 Mobile Safari/537.36"
    )

    parsed = middleware._simple_user_agent_parse(ua)

    assert parsed["device_type"] == "mobile"
    assert parsed["device_brand"] == "Xiaomi"
    assert parsed["device_model"] == "Xiaomi 14"
    assert parsed["os_name"] == "Android"
```

- [ ] **Step 2: Run the backend parsing tests and confirm they fail**

Run:

```bash
pytest test/test_tracking_middleware.py -v
```

Expected:

```text
FAILED test/test_tracking_middleware.py::test_parse_client_hints_prefers_edge_on_windows
FAILED test/test_tracking_middleware.py::test_parse_referer_normalizes_external_domain
FAILED test/test_tracking_middleware.py::test_simple_user_agent_parse_cleans_android_model_noise
```

- [ ] **Step 3: Implement Client Hints parsing, referer normalization, and signal merging in `tracking.py`**

```python
from urllib.parse import parse_qsl, urlencode, urlparse


_KNOWN_DEVICE_BRANDS = {
    "xiaomi": "Xiaomi",
    "redmi": "Redmi",
    "huawei": "HUAWEI",
    "honor": "HONOR",
    "vivo": "vivo",
    "oppo": "OPPO",
    "oneplus": "OnePlus",
    "samsung": "Samsung",
    "realme": "realme",
}


def _clean_client_hint_value(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().strip('"')


def _registrable_domain(host: str | None) -> str | None:
    if not host:
        return None
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _normalize_brand_model(self, brand: str | None, model: str | None) -> tuple[str | None, str | None]:
    brand = (brand or "").strip()
    model = (model or "").strip()
    if brand:
        brand = _KNOWN_DEVICE_BRANDS.get(brand.lower(), brand.title() if brand.islower() else brand)
    if model and brand and model.lower().startswith(brand.lower() + " "):
        return brand, model
    if model and brand and model.lower() == brand.lower():
        return brand, brand
    return brand or None, model or None


def _parse_client_hints(self, headers: dict[str, str]) -> dict[str, str | None]:
    raw_ua = headers.get("sec-ch-ua", "")
    brands = re.findall(r'"([^"]+)";v="([^"]+)"', raw_ua)
    browser_name = None
    browser_version = None
    for brand, version in brands:
        if brand == "Not)A;Brand":
            continue
        if brand == "Microsoft Edge":
            browser_name = "Edge"
            browser_version = version.split(".")[0]
            break
        if brand in {"Chromium", "Google Chrome"} and browser_name is None:
            browser_name = "Chrome"
            browser_version = version.split(".")[0]

    platform = _clean_client_hint_value(headers.get("sec-ch-ua-platform"))
    mobile_flag = headers.get("sec-ch-ua-mobile")
    device_type = "mobile" if mobile_flag == "?1" else "desktop" if mobile_flag == "?0" else None

    return {
        "browser_name": browser_name,
        "browser_version": browser_version,
        "os_name": platform,
        "device_type": device_type,
    }


def _parse_referer(self, referer: str | None, request_host: str | None) -> dict[str, str | None]:
    if not referer:
        return {"referer_host": None, "referer_domain": None, "referer_type": "direct"}
    try:
        parsed = urlparse(referer)
    except ValueError:
        return {"referer_host": None, "referer_domain": None, "referer_type": "unknown"}

    host = parsed.hostname
    if not host:
        return {"referer_host": None, "referer_domain": None, "referer_type": "unknown"}

    referer_domain = _registrable_domain(host)
    request_domain = _registrable_domain(request_host)
    referer_type = "internal" if request_domain and referer_domain == request_domain else "external"
    return {
        "referer_host": host,
        "referer_domain": referer_domain,
        "referer_type": referer_type,
    }
```

- [ ] **Step 4: Wire the helpers into `_log_access()` and `_parse_user_agent()`**

```python
user_agent_str = request.headers.get("user-agent", "")
client_hints = self._parse_client_hints(dict(request.headers))
ua_info = self._parse_user_agent(user_agent_str) if user_agent_str else {}
device_info = self._merge_device_signals(client_hints, ua_info)
referer_info = self._parse_referer(
    request.headers.get("referer"),
    request.url.hostname if getattr(request, "url", None) else None,
)

log = AccessLog(
    ...,
    device_type=device_info.get("device_type"),
    device_brand=device_info.get("device_brand"),
    device_model=device_info.get("device_model"),
    os_name=device_info.get("os_name"),
    browser_name=device_info.get("browser_name"),
    browser_version=device_info.get("browser_version"),
    referer=request.headers.get("referer"),
    referer_host=referer_info.get("referer_host"),
    referer_domain=referer_info.get("referer_domain"),
    referer_type=referer_info.get("referer_type"),
)
```

- [ ] **Step 5: Re-run the backend parsing tests and confirm they pass**

Run:

```bash
pytest test/test_tracking_middleware.py -v
```

Expected:

```text
PASSED test/test_tracking_middleware.py::test_parse_client_hints_prefers_edge_on_windows
PASSED test/test_tracking_middleware.py::test_parse_referer_normalizes_external_domain
PASSED test/test_tracking_middleware.py::test_simple_user_agent_parse_cleans_android_model_noise
```

- [ ] **Step 6: Commit the parsing helper work**

```bash
git add test/test_tracking_middleware.py backend/app/middlewares/tracking.py
git commit -m "feat: normalize tracking client hints and referer"
```

## Task 2: Persist normalized referer fields and additive schema updates

**Files:**
- Create: `test/test_tracking_access_log.py`
- Modify: `backend/app/models/access_log.py`
- Modify: `backend/app/database.py`

- [ ] **Step 1: Write the failing persistence and schema-update tests**

```python
from app.database import _access_log_additive_statements
from app.models.access_log import AccessLog


def test_access_log_to_dict_includes_normalized_referer_fields():
    log = AccessLog(
        id="log-1",
        timestamp="2026-06-16T12:00:00Z",
        ip_address="127.0.0.1",
        referer="https://www.limestart.cn/",
        referer_host="www.limestart.cn",
        referer_domain="limestart.cn",
        referer_type="external",
    )

    data = log.to_dict()

    assert data["referer"] == "https://www.limestart.cn/"
    assert data["referer_host"] == "www.limestart.cn"
    assert data["referer_domain"] == "limestart.cn"
    assert data["referer_type"] == "external"


def test_access_log_additive_statements_only_add_missing_columns():
    statements = _access_log_additive_statements({"id", "timestamp", "referer"})

    assert "ALTER TABLE access_logs ADD COLUMN referer_host VARCHAR(255)" in statements
    assert "ALTER TABLE access_logs ADD COLUMN referer_domain VARCHAR(255)" in statements
    assert "ALTER TABLE access_logs ADD COLUMN referer_type VARCHAR(32)" in statements
```

- [ ] **Step 2: Run the persistence tests and confirm they fail**

Run:

```bash
pytest test/test_tracking_access_log.py -v
```

Expected:

```text
FAILED test/test_tracking_access_log.py::test_access_log_to_dict_includes_normalized_referer_fields
FAILED test/test_tracking_access_log.py::test_access_log_additive_statements_only_add_missing_columns
```

- [ ] **Step 3: Add normalized referer columns and serializer output**

```python
class AccessLog(Base):
    ...
    referer = Column(Text)
    referer_host = Column(String(255))
    referer_domain = Column(String(255))
    referer_type = Column(String(32))
    ...
    def to_dict(self, include_raw: bool = False) -> dict:
        data = {
            ...,
            "referer": self.referer,
            "referer_host": self.referer_host,
            "referer_domain": self.referer_domain,
            "referer_type": self.referer_type,
            ...,
        }
        return data
```

- [ ] **Step 4: Add additive schema statements for existing databases**

```python
def _access_log_additive_statements(columns: set[str]) -> list[str]:
    statements: list[str] = []
    if "referer_host" not in columns:
        statements.append("ALTER TABLE access_logs ADD COLUMN referer_host VARCHAR(255)")
    if "referer_domain" not in columns:
        statements.append("ALTER TABLE access_logs ADD COLUMN referer_domain VARCHAR(255)")
    if "referer_type" not in columns:
        statements.append("ALTER TABLE access_logs ADD COLUMN referer_type VARCHAR(32)")
    return statements


def _ensure_schema_updates() -> None:
    with engine.begin() as conn:
        inspector = inspect(conn)
        ...
        if inspector.has_table("access_logs"):
            access_log_columns = {column["name"] for column in inspector.get_columns("access_logs")}
            for statement in _access_log_additive_statements(access_log_columns):
                conn.execute(text(statement))
                db_logger.info("Applied access_logs additive schema update: %s", statement)
```

- [ ] **Step 5: Re-run the persistence tests and confirm they pass**

Run:

```bash
pytest test/test_tracking_access_log.py -v
```

Expected:

```text
PASSED test/test_tracking_access_log.py::test_access_log_to_dict_includes_normalized_referer_fields
PASSED test/test_tracking_access_log.py::test_access_log_additive_statements_only_add_missing_columns
```

- [ ] **Step 6: Commit the persistence work**

```bash
git add test/test_tracking_access_log.py backend/app/models/access_log.py backend/app/database.py
git commit -m "feat: persist normalized tracking referer fields"
```

## Task 3: Frontend device formatter helpers and regression coverage

**Files:**
- Modify: `frontend/src/utils/trackingDisplay.js`
- Modify: `frontend/src/utils/__tests__/trackingDisplay.spec.js`

- [ ] **Step 1: Extend the frontend formatter tests first**

```javascript
import {
  formatDevicePrimary,
  formatDeviceSecondary,
  formatDeviceTooltip,
  getDeviceTypeText,
} from '../trackingDisplay'

it('formats desktop fallback with normalized windows summary', () => {
  const row = {
    device_type: 'desktop',
    device_brand: 'Microsoft',
    device_model: 'PC',
    os_name: 'Windows',
    browser_name: 'Edge',
    browser_version: '149',
  }

  expect(formatDevicePrimary(row)).toBe('Windows PC')
  expect(formatDeviceSecondary(row)).toBe('Windows · Edge 149')
  expect(formatDeviceTooltip(row)).toContain('Windows PC')
  expect(getDeviceTypeText('desktop')).toBeTruthy()
})

it('falls back to unknown mobile label when brand and model are absent', () => {
  const row = {
    device_type: 'mobile',
    os_name: 'Android',
    browser_name: 'Chrome',
  }

  expect(formatDevicePrimary(row)).toBe('未知手机')
  expect(formatDeviceSecondary(row)).toBe('Android · Chrome')
})
```

- [ ] **Step 2: Run the formatter spec and confirm it fails**

Run:

```bash
cd frontend
npx vitest run src/utils/__tests__/trackingDisplay.spec.js
```

Expected:

```text
FAIL  src/utils/__tests__/trackingDisplay.spec.js
ReferenceError: formatDevicePrimary is not defined
```

- [ ] **Step 3: Implement the formatter helpers in `trackingDisplay.js`**

```javascript
export function formatDeviceFallback(row = {}) {
  if (row.device_type === 'desktop') {
    if (row.os_name === 'Windows') return 'Windows PC'
    if (row.os_name === 'macOS') return 'Apple Mac'
    if (row.os_name === 'Linux') return 'Linux PC'
    return '桌面设备'
  }
  if (row.device_type === 'tablet') return '未知平板'
  if (row.device_type === 'mobile') return '未知手机'
  return getDistributionLabel(row.device_model || row.device_brand || 'unknown')
}

export function formatDevicePrimary(row = {}) {
  const brand = row.device_brand?.trim()
  const model = row.device_model?.trim()
  if (brand && model && model.toLowerCase() === 'pc' && row.os_name === 'Windows') return 'Windows PC'
  if (brand && model && model.toLowerCase() === 'mac') return 'Apple Mac'
  if (brand && model) return model.toLowerCase().startsWith(brand.toLowerCase()) ? model : `${brand} ${model}`
  if (model) return model
  if (brand) return brand
  return formatDeviceFallback(row)
}

export function formatDeviceSecondary(row = {}) {
  const os = getDistributionLabel(row.os_name)
  const browser = [row.browser_name, row.browser_version].filter(Boolean).join(' ')
  if (os && browser && os !== UNKNOWN_LABEL && browser !== UNKNOWN_LABEL) return `${os} · ${browser}`
  if (browser) return browser
  return os
}

export function formatDeviceTooltip(row = {}) {
  return [getDeviceTypeText(row.device_type), formatDevicePrimary(row), formatDeviceSecondary(row)]
    .filter(Boolean)
    .join(' / ')
}
```

- [ ] **Step 4: Re-run the formatter spec and confirm it passes**

Run:

```bash
cd frontend
npx vitest run src/utils/__tests__/trackingDisplay.spec.js
```

Expected:

```text
PASS  src/utils/__tests__/trackingDisplay.spec.js
```

- [ ] **Step 5: Commit the formatter changes**

```bash
git add frontend/src/utils/trackingDisplay.js frontend/src/utils/__tests__/trackingDisplay.spec.js
git commit -m "feat: format normalized tracking device summaries"
```

## Task 4: Reshape `TrackingDashboard.vue` layout and render the device summary block

**Files:**
- Create: `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`
- Modify: `frontend/src/views/admin/TrackingDashboard.vue`

- [ ] **Step 1: Write the failing dashboard layout test**

```javascript
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TrackingDashboard from '../TrackingDashboard.vue'

vi.mock('@/api/client', () => ({
  get: vi.fn((url) => {
    if (url === '/admin/tracking/config') return Promise.resolve({ enable_tracking: 1 })
    if (url === '/admin/tracking/realtime') return Promise.resolve({ recent_visits: 1, online_sessions: 1, active_users: [], top_paths: [] })
    if (url === '/admin/tracking/stats') {
      return Promise.resolve({
        total_visits: 10,
        unique_visitors: 5,
        device_distribution: [{ type: 'desktop', count: 8 }, { type: 'mobile', count: 2 }],
        browser_distribution: [{ name: 'Edge', count: 8 }, { name: 'Chrome Mobile WebView', count: 2 }],
        os_distribution: [{ name: 'Windows', count: 8 }, { name: 'Android', count: 2 }],
        trend: [{ label: '2026-06-16', visits: 10, visitors: 5 }],
        country_distribution: [],
        status_distribution: [],
        response_time: { avg_ms: 20, min_ms: 10, max_ms: 30 },
      })
    }
    if (url === '/admin/tracking/logs') {
      return Promise.resolve({
        total: 1,
        items: [{
          id: 'log-1',
          timestamp: '2026-06-16T12:00:00Z',
          ip_address: '127.0.0.1',
          device_type: 'desktop',
          device_brand: 'Microsoft',
          device_model: 'PC',
          os_name: 'Windows',
          browser_name: 'Edge',
          browser_version: '149',
          request_path: '/demo',
          response_status: 200,
          response_time_ms: 10,
        }],
      })
    }
    return Promise.resolve({})
  }),
  put: vi.fn(),
  del: vi.fn(),
}))

describe('TrackingDashboard', () => {
  it('renders browser as the primary analytics card and shows the normalized device summary', async () => {
    const wrapper = mount(TrackingDashboard, {
      global: {
        stubs: {
          PageHeader: { template: '<div><slot name="actions" /></div>' },
        },
        directives: { loading: {} },
      },
    })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('.distribution-browser-card').exists()).toBe(true)
    expect(wrapper.find('.distribution-side-stack').exists()).toBe(true)
    expect(wrapper.text()).toContain('Windows PC')
    expect(wrapper.text()).toContain('Windows · Edge 149')
  })
})
```

- [ ] **Step 2: Run the dashboard spec and confirm it fails**

Run:

```bash
cd frontend
npx vitest run src/views/admin/__tests__/TrackingDashboard.spec.js
```

Expected:

```text
FAIL  src/views/admin/__tests__/TrackingDashboard.spec.js
AssertionError: expected false to be true
```

- [ ] **Step 3: Refactor the analytics distribution section and device cell markup**

```vue
<div class="distribution-shell">
  <section class="distribution-browser-card">
    <h4>浏览器</h4>
    <el-table :data="browserDistributionRows" size="small" stripe>
      <el-table-column prop="label" label="浏览器" />
      <el-table-column prop="count" label="数量" width="80" align="center" />
    </el-table>
  </section>

  <div class="distribution-side-stack">
    <section class="distribution-compact-card">
      <h4>设备类型</h4>
      <div class="compact-metric-list">
        <div v-for="item in deviceDistributionRows" :key="item.label" class="compact-metric-row">
          <span>{{ item.label }}</span>
          <strong>{{ item.count }}</strong>
        </div>
      </div>
    </section>

    <section class="distribution-compact-card">
      <h4>操作系统</h4>
      <el-table :data="osDistributionRows" size="small" stripe class="compact-os-table">
        <el-table-column prop="label" label="系统" />
        <el-table-column prop="count" label="数量" width="80" align="center" />
      </el-table>
    </section>
  </div>
</div>
```

- [ ] **Step 4: Replace the log device cell with the structured summary block and matching CSS**

```vue
<el-table-column prop="device_type" label="设备" width="200">
  <template #default="{ row }">
    <div class="device-summary" :title="formatDeviceTooltip(row)">
      <el-tag size="small" :type="getDeviceTypeTag(row.device_type)">
        {{ getDeviceTypeText(row.device_type) }}
      </el-tag>
      <div class="device-summary__primary">{{ formatDevicePrimary(row) }}</div>
      <div class="device-summary__secondary">{{ formatDeviceSecondary(row) }}</div>
    </div>
  </template>
</el-table-column>
```

```javascript
import {
  formatTrackingBusiness,
  formatDevicePrimary,
  formatDeviceSecondary,
  formatDeviceTooltip,
  getDeviceTypeText,
  getDistributionLabel,
} from '@/utils/trackingDisplay'
```

```css
.distribution-shell {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 20px;
  align-items: start;
}

.distribution-side-stack {
  display: grid;
  grid-template-rows: 1fr 1fr;
  gap: 16px;
}

.distribution-browser-card,
.distribution-compact-card {
  min-width: 0;
}

.compact-metric-list {
  display: grid;
  gap: 10px;
}

.compact-metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid var(--border-color-light, #e4e9f0);
  border-radius: 10px;
  background: var(--surface-muted, #f6f8fb);
}

.device-summary {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.device-summary__primary {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device-summary__secondary {
  font-size: 12px;
  color: var(--text-tertiary, #7a8798);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 768px) {
  .distribution-shell {
    grid-template-columns: 1fr;
  }

  .distribution-side-stack {
    grid-template-rows: none;
  }
}
```

- [ ] **Step 5: Re-run the dashboard spec and confirm it passes**

Run:

```bash
cd frontend
npx vitest run src/views/admin/__tests__/TrackingDashboard.spec.js
```

Expected:

```text
PASS  src/views/admin/__tests__/TrackingDashboard.spec.js
```

- [ ] **Step 6: Commit the dashboard layout work**

```bash
git add frontend/src/views/admin/TrackingDashboard.vue frontend/src/views/admin/__tests__/TrackingDashboard.spec.js
git commit -m "feat: compact tracking analytics layout"
```

## Task 5: Final verification and regression sweep

**Files:**
- Modify: none expected
- Verify: `test/test_tracking_middleware.py`
- Verify: `test/test_tracking_access_log.py`
- Verify: `frontend/src/utils/__tests__/trackingDisplay.spec.js`
- Verify: `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`

- [ ] **Step 1: Run the backend tracking regression suite**

Run:

```bash
pytest test/test_tracking_middleware.py test/test_tracking_access_log.py -v
```

Expected:

```text
============================= test session starts =============================
...
PASSED test/test_tracking_middleware.py::test_parse_client_hints_prefers_edge_on_windows
PASSED test/test_tracking_middleware.py::test_parse_referer_normalizes_external_domain
PASSED test/test_tracking_middleware.py::test_simple_user_agent_parse_cleans_android_model_noise
PASSED test/test_tracking_access_log.py::test_access_log_to_dict_includes_normalized_referer_fields
PASSED test/test_tracking_access_log.py::test_access_log_additive_statements_only_add_missing_columns
============================== 5 passed in ... ===============================
```

- [ ] **Step 2: Run the frontend regression specs**

Run:

```bash
cd frontend
npx vitest run src/utils/__tests__/trackingDisplay.spec.js src/views/admin/__tests__/TrackingDashboard.spec.js
```

Expected:

```text
PASS  src/utils/__tests__/trackingDisplay.spec.js
PASS  src/views/admin/__tests__/TrackingDashboard.spec.js
```

- [ ] **Step 3: Run a production frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected:

```text
vite v... building for production...
✓ built in ...
```

- [ ] **Step 4: Commit only if verification required a tiny follow-up fix**

```bash
git status --short
git add <only-if-needed>
git commit -m "fix: polish tracking device analytics regressions"
```

## Self-Review

### Spec coverage

- Device brand/model display in the log `设备` column: covered by Task 3 and Task 4.
- Client Hints parsing (`sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`): covered by Task 1.
- Referer normalization (`host`, `domain`, `type`): covered by Task 1 and Task 2.
- Additive schema support for existing databases: covered by Task 2.
- Browser-first analytics layout with compact device/OS cards: covered by Task 4.
- Trend section staying independent from the upper card heights: covered by Task 4 CSS/layout task.
- Regression verification for backend + frontend + production build: covered by Task 5.

### Placeholder scan

- No `TODO` / `TBD`.
- Every code-changing step includes code.
- Every test step includes exact commands.

### Type consistency

- Referer keys are consistently named `referer_host`, `referer_domain`, and `referer_type`.
- Formatter names are consistently `formatDevicePrimary`, `formatDeviceSecondary`, `formatDeviceTooltip`, and `formatDeviceFallback`.
- Backend parsing flow consistently uses `Client Hints -> user_agents -> fallback UA parser`.
