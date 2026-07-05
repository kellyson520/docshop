# Browser-Side Precise Tracking Design

Date: 2026-06-17

## Goal

Extend the tracking system so that the admin dashboard receives meter-level geographic location and real device model/brand information sourced from browser-native APIs, instead of relying solely on server-side User-Agent parsing and GeoIP city-level lookup. Additionally, reduce log noise, introduce a stable visitor UUID, enable announcement targeting based on tracking data, and display locations on a map instead of raw coordinates.

## Current Context

The project already records access logs with device and location fields:

- `backend/app/middlewares/tracking.py` parses User-Agent + Client Hints on every request and writes `AccessLog`.
- `backend/app/models/access_log.py` contains `device_type`, `device_brand`, `device_model`, `os_name`, `browser_name`, `ip_country`, `ip_city`, `ip_isp`, `ip_asn`.
- Location is obtained via GeoIP (MaxMind geoip2) which resolves IP to city-level (~km accuracy).
- Device model is parsed server-side from User-Agent strings; desktop UAs never reveal hardware, and mobile UA parsing frequently yields `null` or noisy fragments.
- `screen_resolution` column exists but is always `null` 鈥?no frontend code ever sends it.
- Every HTTP request (including API calls, static assets) creates an `AccessLog` entry, creating noise.
- The `Announcement` model has `push_method` (`all`/`timed`/`single`) but no geographic or device-based targeting rules.
- The tracking dashboard shows raw IP country/city text, not a map.

### Current Limitations

| Data | Current Source | Accuracy | Problem |
|---|---|---|---|
| Geographic location | GeoIP (IP 鈫?city) | ~km | Not usable for meter-level scenarios |
| Device model | Server UA parsing | Low | Desktop = "PC"/"Mac", mobile often "unknown" |
| Screen resolution | No source | N/A | DB column always `null` |
| CPU / RAM / touch | No source | N/A | No insight into hardware capability |
| Timezone / language | No source | N/A | Could help session attribution |
| Log noise | Every request logged | N/A | API polling, asset loads clutter the log |
| Visitor identity | device_id cookie | Session-scoped | No stable cross-session visitor identifier |
| Announcement targeting | push_method only | N/A | Cannot target by city, device type, or timezone |
| Location visualization | Text only | N/A | Cannot see clusters or patterns on a map |

## Chosen Approach

Five enhancements on top of the existing tracking system:

1. **Precise tracking beacon** 鈥?frontend module collects browser-native APIs (geolocation, screen, hardware, UA Client Hints) and sends them to `POST /api/v1/tracking/ping`.
2. **Log noise reduction** 鈥?a new `is_page_view` flag on `AccessLog` distinguishes real page loads from API/asset requests; the dashboard defaults to filtering noise out.
3. **Stable visitor UUID** 鈥?the existing `device_id` cookie is re-purposed as a first-class `visitor_id` column on `AccessLog` and `UserSession`, surfaced in the dashboard as a clickable identifier.
4. **Announcement targeting** 鈥?extend the `Announcement` model with JSON `targeting_rules` that support conditions on `city`, `country`, `device_type`, `os_name`, `browser_name`, `timezone`, `visitor_id`, and `is_authenticated`. The `GET /active` endpoint evaluates rules against the request context.
5. **Map visualization** 鈥?replace the raw coordinate text in the dashboard with an embedded Leaflet map showing visitor location pins.

---

## Enhancement 1: Frontend Tracking Beacon

### Why Not Extend GeoIP or UA Parsing Further?

- **Geolocation**: GeoIP databases fundamentally cannot provide meter-level accuracy 鈥?they operate on ISP/IP block registration data. The only way to get meter-level coordinates is the browser's `navigator.geolocation` API.
- **Device model**: Desktop browsers do not include hardware model in any HTTP header. The `sec-ch-ua-model` Client Hint (part of User-Agent Client Hints API, `navigator.userAgentData.getHighEntropyValues()`) is the only reliable source for real model info on Chromium browsers.

### Frontend Beacon Payload

The tracking client collects the following when the page loads, gated by `TrackingConfig` switches:

**Phase 1 鈥?synchronous (sent immediately, ~0ms delay):**

| JSON Field | Browser API | Condition | DB Column |
|---|---|---|---|
| `screen_resolution` | `window.screen.width 脳 window.screen.height` | Always | `screen_resolution` |
| `screen_avail` | `window.screen.availWidth 脳 window.screen.availHeight` | Always | `raw_data` JSON |
| `screen_color_depth` | `window.screen.colorDepth` | Always | `raw_data` JSON |
| `screen_pixel_ratio` | `window.devicePixelRatio` | Always | `raw_data` JSON |
| `screen_orientation` | `window.screen.orientation?.type` | Always | `raw_data` JSON |
| `platform` | `navigator.platform` | Always (most useful on Safari) | `raw_data` JSON |
| `hardware_concurrency` | `navigator.hardwareConcurrency` | All except iOS Safari | `raw_data` JSON |
| `device_memory` | `navigator.deviceMemory` | Chrome only | `raw_data` JSON |
| `max_touch_points` | `navigator.maxTouchPoints` | Always | `raw_data` JSON |
| `touch_support` | `'ontouchstart' in window` | Always | `raw_data` JSON |
| `pointer_coarse` | `matchMedia('(pointer: coarse)').matches` | Always | `raw_data` JSON |
| `pointer_fine` | `matchMedia('(pointer: fine)').matches` | Always | `raw_data` JSON |
| `hover_hover` | `matchMedia('(hover: hover)').matches` | Always | `raw_data` JSON |
| `any_pointer_coarse` | `matchMedia('(any-pointer: coarse)').matches` | Always | `raw_data` JSON |
| `any_pointer_fine` | `matchMedia('(any-pointer: fine)').matches` | Always | `raw_data` JSON |
| `network_type` | `navigator.connection?.effectiveType` | Chrome only | `raw_data` JSON |
| `network_downlink` | `navigator.connection?.downlink` | Chrome only | `raw_data` JSON |
| `network_rtt` | `navigator.connection?.rtt` | Chrome only | `raw_data` JSON |
| `network_save_data` | `navigator.connection?.saveData` | Chrome only | `raw_data` JSON |
| `language` | `navigator.language` | Always | `client_language` |
| `timezone` | `Intl.DateTimeFormat().resolvedOptions().timeZone` | Always | `client_timezone` |
| `geo_latitude` | `navigator.geolocation.getCurrentPosition()` 鈫?`coords.latitude` | Location ON + user permission | `geo_latitude` |
| `geo_longitude` | `navigator.geolocation.getCurrentPosition()` 鈫?`coords.longitude` | Location ON + user permission | `geo_longitude` |
| `geo_accuracy` | `navigator.geolocation.getCurrentPosition()` 鈫?`coords.accuracy` | Location ON + user permission | `geo_accuracy` |

**Phase 2 鈥?asynchronous (sent ~2s later via second beacon):**

| JSON Field | Browser API | Condition | DB Column |
|---|---|---|---|
| `device_brand` | `navigator.userAgentData.getHighEntropyValues()` 鈫?`brands[*].brand` | Chromium only | `device_brand` |
| `device_model` | `navigator.userAgentData.getHighEntropyValues()` 鈫?`model` | Chromium only | `device_model` |
| `cpu_architecture` | `navigator.userAgentData.getHighEntropyValues()` 鈫?`architecture` | Chromium only | `raw_data` JSON |
| `cpu_bitness` | `navigator.userAgentData.getHighEntropyValues()` 鈫?`bitness` | Chromium only | `raw_data` JSON |
| `platform_version` | `navigator.userAgentData.getHighEntropyValues()` 鈫?`platformVersion` | Chromium only | `raw_data` JSON |
| `browser_full_version` | `navigator.userAgentData.getHighEntropyValues()` 鈫?`uaFullVersion` | Chromium only | `raw_data` JSON |
| `storage_quota_gb` | `navigator.storage.estimate()` 鈫?`quota / (1024鲁)` | Always | `raw_data` JSON |

**Why two phases?** Phase 1 collects zero-latency synchronous values and fires immediately on DOMContentLoaded. Phase 2 defers the async-heavy UA Client Hints (which may trigger a permission check) and Storage estimate to avoid blocking the first beacon or page paint. Since the backend updates the same AccessLog row by `session_id`, the second ping merges into the same record seamlessly.

**What we deliberately don't collect:** WebGL renderer strings, Canvas image hashes, AudioContext fingerprints, and font lists. These are the tracking industry's "dark patterns" 鈥?high-entropy fingerprints that can uniquely identify a device, blocked by browser anti-fingerprinting protections, and incompatible with a privacy-respecting analytics system.

### Cross-Browser Device Detection Strategy

Different browsers expose different signals. The collection stack is designed to extract maximum signal from each:

| Browser | Best Signal | Fallback |
|---|---|---|
| **Chrome/Edge (Chromium)** | `userAgentData.getHighEntropyValues()` 鈫?real model, architecture, bitness | Server UA parsing |
| **Safari (macOS)** | `navigator.platform` 鈫?"MacIntel" / "macOS"; `hardwareConcurrency` (15+); all pointer/hover queries | Server UA parsing |
| **Safari (iOS)** | `navigator.platform` 鈫?"iPhone" / "iPad"; `any-pointer: fine` + `any-pointer: coarse` 鈫?detect iPad + keyboard; `screen_pixel_ratio` (2=Retina, 3=Super Retina); `screen_avail` vs `screen_resolution` 鈫?detect Home Bar (iPhone X+) | Server UA parsing |
| **Firefox** | All cross-browser fields | Server UA parsing |

**Detection priority for device type:**

| Priority | Signal | Source | Example |
|---|---|---|---|
| 1 (highest) | Real device model string | `userAgentData` (Chromium) | "Pixel 8 Pro" |
| 2 | Platform type from `navigator.platform` | Safari (only browser still returning truthful values) | "iPhone", "iPad", "MacIntel" |
| 3 | Pointer + hover + touch hints | `matchMedia` queries (all browsers) | `pointer: coarse` + `hover: none` = phone/tablet |
| 4 | Pixel ratio + screen avail | `devicePixelRatio`, `screen.availHeight` | Retina + Home Bar detection |
| 5 (lowest) | Server-side UA regex fallback | `_simple_user_agent_parse` | "iPhone 15", "SM-G9910" |

### Safari Limitations & Safari-Unique Value

**What Safari CANNOT provide** (no data loss 鈥?gracefully degrades to null):

| Missing API | Impact | Mitigation |
|---|---|---|
| `navigator.userAgentData` | No `device_brand`, `device_model`, `architecture`, `bitness` | Fall back to server-side `_simple_user_agent_parse` |
| `navigator.deviceMemory` | No RAM info | Field stays `null` |
| `navigator.connection` | No network type/bandwidth | Field stays `null` |
| `navigator.hardwareConcurrency` (iOS) | No CPU core count on iOS Safari | Field stays `null` |
| Geolocation (HTTP origins) | `getCurrentPosition` calls error callback | GeoIP fallback unchanged |

**What ONLY Safari can provide:**

| Signal | Why Safari Only | Value |
|---|---|---|
| `navigator.platform = "iPhone"` or `"iPad"` | Chrome's `navigator.platform` is frozen to `"Win32"`/`"MacIntel"`; only Safari returns the real device category | Distinguishes iPhone/iPad/Mac at a glance 鈥?no UA parsing needed |
| `any-pointer: fine` + `hover: hover` 鈮?`pointer: coarse` | Safari on iPad + Magic Keyboard returns `pointer: coarse` for the touch-first profile but `any-pointer: fine` for the connected keyboard/trackpad | Detects "iPad used as laptop" combo 鈥?impossible on Chrome |
| `screen_avail.height < screen.height` | iPhone X+ with Home Bar has a large gap between physical and available screen; Safari reports this accurately | Detects notch/Home Bar devices vs older iPhones |

### Privacy Controls

- **Geolocation is always opt-in**: The browser shows the native permission dialog. If the user denies it, `geo_latitude`/`geo_longitude` remain `null`. The frontend never retries after denial.
- **Tracking config gating**: Before collecting location data, the frontend fetches `GET /api/v1/tracking/config` and checks `enable_location_tracking`. If 0, it skips geolocation entirely and never triggers the permission prompt.
- **IP anonymization**: When `TrackingConfig.anonymize_ip` is true, the backend rounds `geo_latitude`/`geo_longitude` to 3 decimal places (~111m precision) before persisting.
- **All non-coordinate data**: `hardware_concurrency`, `device_memory`, `max_touch_points`, `language`, `timezone` are not personally identifiable and are stored as enrichment.

### Transport

Use `navigator.sendBeacon(url, blob)` where blob is `new Blob([JSON.stringify(payload)], { type: 'application/json' })`. This guarantees delivery even during page unload. Fallback to `fetch()` with `keepalive: true`.

### New Module: `frontend/src/utils/trackingClient.js`

Two-phase data collection 鈥?synchronous first, asynchronous deferred:

```
Application startup
  鈫?fetch GET /api/v1/tracking/config
  鈫?determine enabled capabilities (location / device)
  鈫?鈺愨晲鈺?Phase 1: synchronous collection (鈮?ms) 鈺愨晲鈺?  collect screen_resolution, screen_avail, screen_color_depth,
  screen_pixel_ratio, screen_orientation, platform,
  hardwareConcurrency, deviceMemory, maxTouchPoints, touch_support,
  pointer_coarse, pointer_fine, hover_hover,
  any_pointer_coarse, any_pointer_fine,
  network_type, network_downlink, network_rtt, network_save_data,
  language, timezone
  (if location ON: navigator.geolocation.getCurrentPosition())
  鈫?send POST /api/v1/tracking/ping (first beacon, sendBeacon)
  鈫?send POST /api/v1/tracking/ping (first beacon, sendBeacon)
  鈫?鈺愨晲鈺?Phase 2: asynchronous collection (鈮?s later) 鈺愨晲鈺?  if Chromium:
    navigator.userAgentData.getHighEntropyValues([
      'architecture','bitness','platformVersion','uaFullVersion',
      'model','platform','fullVersionList'
    ])
  if Storage API available:
    navigator.storage.estimate() 鈫?quota
  鈫?send POST /api/v1/tracking/ping (second beacon, merges into same AccessLog)
```

---

## Enhancement 2: Log Noise Reduction

### Problem

Current `TrackingMiddleware._log_access()` fires on **every HTTP request**, including:
- Static assets (JS, CSS, images, fonts) 鈥?high volume, no useful signal
- API polling calls (e.g., realtime stats refresh every 30s)
- SPA route transitions (XHR/fetch, not real page views)

This produces thousands of entries per user session, burying meaningful page views.

### Solution: `is_page_view` Flag

Add a new column `is_page_view` to `AccessLog`:

```python
is_page_view = Column(Integer, default=0)  # 1=actual page navigation, 0=API/asset request
```

**Classification rules in middleware**:

| Request Pattern | `is_page_view` | Rationale |
|---|---|---|
| `GET /` (HTML) | 1 | Main page load |
| `GET /login` | 1 | Login page |
| `GET /admin/*` (HTML) | 1 | Admin pages served as HTML |
| `GET /api/*` | 0 | API calls |
| `GET *.js, *.css, *.png, *.svg` | 0 | Static assets |
| `GET /assets/*` | 0 | Vite build output |
| SPA route transitions (XHR) | 0 | Not a full page load |

Implementation: in `TrackingMiddleware.dispatch()`, check `request.url.path` and `request.headers.get('accept')`:

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

### Dashboard Filtering

Add a toggle to the logs section:

```vue
<el-switch v-model="pageViewsOnly" active-text="浠呴〉闈㈡祻瑙? inactive-text="鍏ㄩ儴璇锋眰" @change="fetchLogs" />
```

The `GET /admin/tracking/logs` endpoint gains `?page_views_only=1` to filter.

---

## Enhancement 3: Stable Visitor UUID

### Problem

The current `device_id` is a UUID stored in a 1-year cookie, but it's not surfaced in the admin dashboard as a primary visitor identifier. There's no way to correlate multiple sessions from the same browser.

### Solution

Add a dedicated `visitor_id` column to `AccessLog` and `UserSession`:

```python
visitor_id = Column(String(36), nullable=True, index=True)
```

The middleware already generates `device_id` in `request.state.device_id`. At log creation time:

```python
log = AccessLog(
    visitor_id=request.state.device_id,  # the stable 1-year cookie UUID
    ...
)
```

**Dashboard changes**:
- Add a `璁垮 ID` column showing `visitor_id` as a shortened clickable badge (e.g., `a1b2c3d4鈥)
- Full UUID shown in tooltip on hover
- Clicking the visitor ID filters the logs table to show all entries from that visitor

---

## Enhancement 4: Announcement Targeting

### Problem

The current `Announcement.push_method` only supports `all`, `timed`, and `single` (by `target_user_id`). There's no way to say "show this popup only to mobile users in Beijing".

### Solution

Add a JSON `targeting_rules` column to the `Announcement` model:

```python
targeting_rules = Column(Text, nullable=True)  # JSON string
```

Schema for `targeting_rules`:

```json
{
  "match": "all",
  "rules": [
    { "field": "country", "op": "eq", "value": "CN" },
    { "field": "city", "op": "eq", "value": "Beijing" },
    { "field": "device_type", "op": "eq", "value": "mobile" },
    { "field": "os_name", "op": "in", "value": ["Android", "iOS"] },
    { "field": "visitor_id", "op": "eq", "value": "a1b2c3d4-e5f6-..." },
    { "field": "is_authenticated", "op": "eq", "value": true }
  ]
}
```

Supported operators: `eq`, `ne`, `in`, `not_in`.

**Backend evaluation** (in `GET /api/v1/announcements/active`):

```python
def _matches_targeting(rules_json: str | None, context: dict) -> bool:
    if not rules_json:
        return True
    try:
        rules = json.loads(rules_json)
    except (json.JSONDecodeError, TypeError):
        return True
    match_mode = rules.get("match", "all")
    rule_list = rules.get("rules", [])
    if not rule_list:
        return True
    results = []
    for rule in rule_list:
        field = rule.get("field")
        op = rule.get("op")
        value = rule.get("value")
        actual = context.get(field)
        if op == "eq":
            results.append(actual == value)
        elif op == "ne":
            results.append(actual != value)
        elif op == "in":
            results.append(actual in (value or []))
        elif op == "not_in":
            results.append(actual not in (value or []))
        else:
            results.append(True)
    return all(results) if match_mode == "all" else any(results)
```

**Admin UI** (`AnnouncementManager.vue`): Add a `瀹氬悜瑙勫垯` tab with a rule editor form.

**Frontend** (`AnnouncementBar.vue`): Pass `visitor_id` from cookie to `GET /announcements/active`.

---

## Enhancement 5: Map Display

### Problem

The tracking dashboard shows location as raw text (`Beijing, CN` or `馃搷 39.9042, 116.4074`). Operators cannot visually see visitor clusters or geographic distribution patterns.

### Solution

Replace the location text display with an interactive map using **Leaflet** (lightweight, no API key required).

**New component**: `frontend/src/components/tracking/VisitorMap.vue`

```vue
<template>
  <div ref="mapContainer" class="visitor-map" style="height: 400px; border-radius: 12px;"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  points: { type: Array, default: () => [] },
})
const mapContainer = ref(null)
let map = null
let markers = null

onMounted(() => {
  map = L.map(mapContainer.value).setView([35, 105], 4)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '漏 OpenStreetMap contributors',
  }).addTo(map)
  markers = L.layerGroup().addTo(map)
  renderPoints()
})

watch(() => props.points, () => renderPoints(), { deep: true })

function renderPoints() {
  if (!markers) return
  markers.clearLayers()
  props.points.forEach(p => {
    const marker = L.marker([p.lat, p.lng])
      .bindPopup(p.label || `${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}`)
    markers.addLayer(marker)
  })
  if (props.points.length > 0 && map) {
    map.fitBounds(markers.getBounds().pad(0.1))
  }
}
</script>
```

**New backend endpoint**: `GET /admin/tracking/locations`

Returns up to 200 `{lat, lng, label, timestamp}` points. Prefers `geo_latitude/geo_longitude`; falls back to city centroid lookup via a static dictionary of known cities.

---

## Enhancement 6: User Profiling (Visitor Profiles)

### Problem

Data is scattered across three tables (`access_logs`, `user_sessions`, `users`) with no aggregated visitor-level view. There's no way to answer "what kind of user is this?" 鈥?only isolated raw log rows. Announcement targeting is limited to per-request context; there's no persistent profile to target against.

### Solution

Add a **`visitor_profiles`** aggregate table that incrementally summarizes each visitor into one row. A lightweight background task (triggered every 5 minutes or on each `_log_access` via sampling) updates the profile. The dashboard gains a profile detail page, and announcement targeting gains `tag` as a new rule field.

### `visitor_profiles` Schema

```sql
CREATE TABLE visitor_profiles (
    visitor_id VARCHAR(36) PRIMARY KEY,        -- device_id
    user_id VARCHAR(36),                       -- bound login user (nullable)
    first_seen_at DATETIME,
    last_seen_at DATETIME,
    total_visits INT DEFAULT 0,
    total_sessions INT DEFAULT 0,
    total_page_views INT DEFAULT 0,
    total_downloads INT DEFAULT 0,

    -- Aggregated device profile (mode of last 30 days)
    primary_device_type VARCHAR(20),
    primary_os VARCHAR(50),
    primary_browser VARCHAR(50),
    primary_screen_resolution VARCHAR(20),
    primary_timezone VARCHAR(64),
    primary_language VARCHAR(20),
    primary_country VARCHAR(2),
    primary_city VARCHAR(100),

    -- Aggregated behavior
    avg_session_duration_sec FLOAT,
    typical_visit_hour INT,           -- most common hour (0-23)
    typical_visit_day VARCHAR(10),    -- "weekday" | "weekend" | "mixed"
    top_paths TEXT,                   -- JSON: [{"path":"/projects","count":42},...]
    preferred_action_types TEXT,      -- JSON: ["view","download","diff"]

    -- Auto-computed tags (JSON array)
    tags TEXT,                        -- ["mobile_user","frequent_visitor","night_owl",...]

    -- Timestamps
    updated_at DATETIME
);
```

### Auto-Tagging Rules

Tags are computed from profile fields via simple rules. They can be referenced in `Announcement.targeting_rules`:

```json
{"field": "tag", "op": "in", "value": ["mobile_user", "frequent_visitor"]}
```

| Tag | Rule |
|---|---|
| `mobile_user` | >70% of visits from mobile/tablet |
| `desktop_user` | >70% of visits from desktop |
| `chrome_user` | >80% of visits use Chrome |
| `safari_user` | >80% of visits use Safari |
| `night_owl` | Peak visit hour in 22:00-06:00 |
| `morning_person` | Peak visit hour in 06:00-12:00 |
| `frequent_visitor` | 鈮? visits in last 7 days |
| `new_visitor` | First seen within 24 hours |
| `returning_user` | 鈮? total visits |
| `high_resolution` | Primary screen 鈮?2560脳1440 |
| `power_user` | 鈮?0 downloads + diffs |
| `content_creator` | 鈮? uploads |
| `sharer` | Created 鈮? share token |
| `exam_user` | Accessed exam-related paths |

### Profile API Endpoints

```
GET  /admin/tracking/visitors/{visitor_id}    鈫?full profile object
GET  /admin/tracking/visitors?tag=mobile_user&page=1 鈫?paginated list, filterable by tag
POST /admin/tracking/visitors/{visitor_id}/tags      鈫?manually add/remove tags
GET  /admin/tracking/visitors/{visitor_id}/timeline  鈫?recent session history
```

### Dashboard: Profile Detail Page

Clicking a visitor ID in the tracking dashboard navigates to `/admin/tracking/visitors/{visitor_id}`, showing:

- **Header**: Visitor ID, first/last seen, total visits/sessions/page-views, bound user (if any)
- **Device card**: Primary device type, OS, browser, screen, timezone, language, country
- **Activity heatmap**: 24h 脳 7d grid showing visit density
- **Top paths**: Ranked list of most-visited URLs
- **Action distribution**: Pie chart of view/download/diff/upload/share
- **Tags**: Editable tag chips with auto-suggested additions
- **Session timeline**: Chronological list of recent sessions with entry/exit paths

### Profile Update Strategy

Profiles are updated **incrementally** via a background task (not per-request to avoid write amplification):

| Trigger | What updates |
|---|---|
| Every 5 minutes (cron) | Batch update all profiles with new access_logs since last run |
| `_log_access` sampling (1% of requests) | Opportunistic single-profile refresh |

This avoids adding latency to every request while keeping profiles fresh within 5 minutes.

### Privacy & Ethics Boundaries

| 鉂?Not tracked | Rationale |
|---|---|
| Page DOM content | Severe privacy violation |
| Keystrokes / clipboard | Illegal / sensitive data |
| Camera / microphone data | Requires explicit user consent |
| Cross-device correlation (unless logged in) | Cross-user tracking |
| Third-party cookies | Browsers are deprecating them |

| 鈿狅笍 Handled with care |
|---|
| Canvas/WebGL/Audio fingerprints 鈥?not collected (see Enhancement 1) |
| Precise geolocation 鈥?rounded to ~111m when anonymization is on |
| Visitor profiles 鈥?anonymous UUID only, never linked to real identity unless user logs in |

---

## Backend Design Summary

### New/Modified Files

| File | Change |
|---|---|
| `backend/app/models/access_log.py` | Add `visitor_id`, `is_page_view`, `geo_latitude`, `geo_longitude`, `geo_accuracy`, `client_timezone`, `client_language` |
| `backend/app/models/user_session.py` | Add `visitor_id` |
| `backend/app/models/announcement.py` | Add `targeting_rules` JSON column |
| `backend/app/middlewares/tracking.py` | Set `visitor_id`, `is_page_view`; skip ping path; merge pending beacon |
| `backend/app/routers/tracking_ping.py` | New: `POST /api/v1/tracking/ping` |
| `backend/app/routers/tracking_admin.py` | Add `?page_views_only`; add `/locations` endpoint |
| `backend/app/routers/announcements.py` | Evaluate `targeting_rules` in `/active` |
| `backend/app/routers/tagging.py` | New: auto-tagging service + profile endpoints |
| `backend/app/models/visitor_profile.py` | New: `visitor_profiles` aggregate table |
| `backend/app/database.py` | Additive migration for all new columns |
| `backend/app/main.py` | Register ping router |
| `test/test_tracking_ping.py` | New |
| `test/test_announcement_targeting.py` | New |
| `test/*.py` | Update existing |

### New DB Columns on `access_logs`

| Column | Type | Nullable | Default |
|---|---|---|---|
| `visitor_id` | `String(36)` | Yes | `null` |
| `is_page_view` | `Integer` | No | `0` |
| `geo_latitude` | `Double` | Yes | `null` |
| `geo_longitude` | `Double` | Yes | `null` |
| `geo_accuracy` | `Double` | Yes | `null` |
| `client_timezone` | `VARCHAR(64)` | Yes | `null` |
| `client_language` | `VARCHAR(20)` | Yes | `null` |

### Ping Endpoint: `POST /api/v1/tracking/ping`

- Correlates by `session_id` cookie
- Updates the latest `AccessLog` for that session
- Rate limited: 1 ping per session per 10 seconds
- `anonymize_ip=true` rounds lat/lng to 3 decimal places (~111m)
- Returns 204 No Content

---

## Frontend Design Summary

### New/Modified Files

| File | Change |
|---|---|
| `frontend/src/utils/trackingClient.js` | New beacon module |
| `frontend/src/main.js` | Import and init tracking |
| `frontend/src/utils/trackingDisplay.js` | Add `formatGeoLocation()`; update `formatDevicePrimary()` |
| `frontend/src/views/admin/TrackingDashboard.vue` | Add map card, visitor ID column, noise toggle |
| `frontend/src/components/tracking/VisitorMap.vue` | New Leaflet map component |
| `frontend/src/views/admin/AnnouncementManager.vue` | Add targeting rules editor |
| `frontend/src/views/admin/VisitorProfile.vue` | New: visitor profile detail page |
| `frontend/src/components/common/AnnouncementBar.vue` | Pass visitor_id to API |
| `frontend/package.json` | Add `leaflet` dependency |
| Various `__tests__/*` | Updated for new features |

### New Dependency

```bash
npm install leaflet
```

Leaflet is MIT-licensed, ~40KB gzipped, no API key required.

---

## Data Flow (Complete)

```
1. Browser loads page
2. TrackingMiddleware sets device_id / session_id cookies (existing)
3. Middleware writes initial AccessLog:
   - visitor_id = device_id
   - is_page_view = 1 if HTML page, 0 if API/asset
4. Frontend trackingClient.js fires:
   a. Fetch config (GET /api/v1/tracking/config)
   b. Collect browser APIs
   c. If location enabled, request geolocation (user prompt)
   d. POST /api/v1/tracking/ping
5. Backend ping handler correlates by session_id:
   a. UPDATE access_logs SET geo_latitude=..., screen_resolution=...
   b. Respects anonymize_ip rounding
6. Admin dashboard:
   a. GET /admin/tracking/logs?page_views_only=1 鈫?filtered log list
   b. GET /admin/tracking/locations 鈫?geo points for map
   c. Leaflet map renders visitor pins
7. Announcement system:
   a. AnnouncementBar.vue calls GET /api/v1/announcements/active?visitor_id=...
   b. Backend evaluates targeting_rules against visitor context
   c. Only matching announcements returned
8. Profile pipeline (background):
   a. Every 5 minutes: batch UPDATE visitor_profiles from new AccessLog rows
   b. Tags re-computed from updated profile fields
   c. Admin clicks visitor ID 鈫?GET /admin/tracking/visitors/{id} 鈫?profile detail page
```

---

## Error Handling and Edge Cases

- **User denies geolocation**: `geo_latitude`/`geo_longitude` remain `null`. No retry. GeoIP fallback continues.
- **Non-Chromium browser**: `userAgentData` is `undefined`. Existing server-side UA parsing is the fallback.
- **Beacon arrives before `AccessLog` is committed**: Data stored on `UserSession`; middleware merges on next write.
- **Beacon never arrives (ad blocker, JS error)**: No data loss 鈥?server-side fields already exist.
- **sendBeacon not supported**: Fallback to `fetch()` with `keepalive: true`.
- **HTTPS required for geolocation**: In dev with HTTP, geolocation API calls error callback. Degrades gracefully.
- **Rate limit hit**: 10-second cooldown silently drops duplicate pings.
- **Leaflet tiles fail to load**: Map shows grey background. Non-critical 鈥?table still shows location data.
- **Targeting rules with missing context**: If rule references `city` but GeoIP city is null, rule returns false for `eq`/`in`, true for `ne`/`not_in`.

---

## Testing Strategy

### Backend Tests

| Test file | Coverage |
|---|---|
| `test/test_tracking_ping.py` | Ping correlation, anonymization, rate limiting, pending merge |
| `test/test_tracking_middleware.py` | `is_page_view` classification, `visitor_id` propagation |
| `test/test_tracking_access_log.py` | New column serialization, additive DDL |
| `test/test_announcement_targeting.py` | Rule evaluation, context building, edge cases |
| `test/test_tagging.py` | Tag computation rules, profile aggregation, manual tag CRUD |
| `test/test_visitor_profile.py` | Profile model serialization, additive DDL, incremental update logic |

### Frontend Tests

| Test file | Coverage |
|---|---|
| `trackingClient.spec.js` | Payload shape, sendBeacon, geolocation gating |
| `trackingDisplay.spec.js` | `formatGeoLocation`, screen resolution in device primary |
| `TrackingDashboard.spec.js` | Map card, visitor ID column, noise filter toggle |
| `VisitorMap.spec.js` | Points rendering, empty state |
| `VisitorProfile.spec.js` | Profile detail rendering, tag chips, timeline list |
| `AnnouncementManager.spec.js` | Targeting rules form add/remove/save |

---

## Non-Goals

- No real-time reverse geocoding (street address from lat/lng). Map shows raw coordinate pins.
- No IP geolocation service replacement 鈥?GeoIP is still the fallback.
- No WebSocket or push for real-time map updates.
- No user-facing map in `UserActivities.vue` 鈥?admin-only.
- No change to the existing UA parser fallback 鈥?it continues to work as-is.
- No ML-based profiling 鈥?tags are rule-based only.
- No cross-device tracking 鈥?visitor_id is cookie-scoped to one browser.
- Profile data retained per `data_retention_days` config; no infinite retention.

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

