# Tracking Server Egress IP Enrichment Design

Date: 2026-06-26

## Goal

Enhance the admin tracking dashboard so the device/access info card and detail dialog can display additional network intelligence sourced from IPPure, using the DocShop server's current egress IP as shared context.

## Confirmed Constraint

The public IPPure endpoint currently available for this project is:

- `https://my.ippure.com/v1/info`

Based on verification in this environment, it returns information for the calling server's current egress IP and does not support reliable lookup of arbitrary visitor IPs through query parameters or common forwarding headers.

This design therefore does **not** attempt to enrich each log row's `ip_address`.

## Scope

This design covers:

- Backend integration with IPPure server-egress IP info
- Shared response enrichment for tracking log list and log detail APIs
- Frontend card/detail rendering for the new shared IP intelligence
- Short-term caching and graceful degradation
- Focused backend/frontend tests

This design does not cover:

- Per-visitor IP enrichment
- Database persistence of IPPure results
- Replacing the existing visitor/device/location fields collected from logs
- Changes to unrelated multi-file preview or announcement flows

## Chosen Approach

Use a backend service that fetches and caches the server egress IP intelligence, then expose it as an explicit shared payload named `server_ip_context` in tracking APIs.

Frontend consumes that shared payload and renders it with clear labeling such as “服务器出口 IP 情报”, so users can distinguish it from the actual visitor log fields.

This approach is preferred over copying the same IPPure payload into every log item because:

1. It preserves semantics: shared server context is not mistaken for row-specific visitor data.
2. It avoids repeated payload bloat in paginated log lists.
3. It is easier to evolve later if a true per-IP lookup capability becomes available.

## Product Decision

The admin tracking dashboard should show two different kinds of network information:

1. **Visitor-side log information**
   - existing `ip_address`
   - `ip_country`
   - `ip_city`
   - browser geolocation / timezone / language

2. **Server-side shared IP intelligence**
   - current server egress IP
   - ASN / AS organization
   - country / region / city / postal code
   - timezone
   - fraud score
   - residential / broadcast flags

These two layers must remain visually and semantically separated.

## Backend Architecture

### 1. New service

Add:

- `backend/app/services/ippure_service.py`

Responsibilities:

- Request `https://my.ippure.com/v1/info`
- Normalize the response into a stable internal shape
- Cache successful responses with short TTL
- Return a safe fallback payload when the remote request fails

Suggested normalized shape:

```json
{
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
  "isResidential": true,
  "isBroadcast": false
}
```

### 2. Caching strategy

Use existing in-memory cache infrastructure and cache the normalized payload for a short TTL, recommended:

- 300 seconds to 600 seconds

Behavior:

- If cache hit: return cached payload
- If remote fetch succeeds: refresh cache
- If remote fetch fails and cache exists: return stale cached payload if available
- If remote fetch fails and no cache exists: return `null` or omitted `server_ip_context`

### 3. Tracking router integration

Update:

- `GET /admin/tracking/logs`
- `GET /admin/tracking/logs/{log_id}`

Response contract changes:

#### List API

```json
{
  "total": 2,
  "page": 1,
  "page_size": 20,
  "items": [...],
  "server_ip_context": {
    "source": "ippure_server_egress",
    "ip": "112.224.158.50"
  }
}
```

#### Detail API

```json
{
  "id": "log-1",
  "ip_address": "127.0.0.1",
  "...": "...",
  "server_ip_context": {
    "source": "ippure_server_egress",
    "ip": "112.224.158.50"
  }
}
```

### 4. Failure behavior

If IPPure is unavailable:

- Do not fail the tracking API request
- Return logs normally
- Omit `server_ip_context` or set it to `null`
- Log the fetch failure for diagnostics

This enrichment is additive only and must never block dashboard access.

## Frontend Architecture

### 1. Data flow

Tracking dashboard currently builds device/access cards from log rows. After this change:

- log list remains row-based
- `server_ip_context` is stored once at page level
- helper functions receive row + optional shared server context

Main touched files:

- `frontend/src/views/admin/TrackingDashboard.vue`
- `frontend/src/utils/trackingDisplay.js`

### 2. Card rendering

The existing card should keep visitor/device details unchanged, then append one concise server-egress summary line when `server_ip_context` exists.

Recommended compact summary priority:

1. geographic summary
2. risk / residential markers
3. ASN summary

Example outputs:

- `服务器出口IP · Qingdao, Shandong, CN`
- `风险 0 · 住宅IP · 非广播`
- `AS4837 · China Unicom Shandong province network`

The exact combination can be split across one or two lines depending on layout fit, but the label must explicitly say `服务器出口IP`.

### 3. Detail dialog rendering

Add a separate section in the access info dialog:

- title: `服务器出口 IP 情报`

Suggested fields:

- 出口 IP
- 国家/地区
- 省/州
- 城市
- 邮编
- 时区
- ASN
- AS 组织
- 风险分
- 住宅 IP
- 广播 IP

This section must not replace the existing visitor/device technical details block.

### 4. Visual separation rule

Frontend must avoid any presentation that implies:

- the server egress IP equals the visitor IP
- the IPPure location is the visitor location

All UI copy should reinforce that this is shared environment intelligence from the server side.

## Helper Design

Extend `trackingDisplay.js` with small, isolated helpers such as:

- `formatServerIpGeoSummary`
- `formatServerIpRiskSummary`
- `formatServerIpNetworkSummary`
- `buildServerIpContextDetails`

Possible update:

- `buildTrackingInfoCard(row, serverIpContext?)`

The helper layer should encapsulate formatting rules so `TrackingDashboard.vue` remains mostly declarative.

## API/Schema Notes

No SQLAlchemy model or database schema change is required for Phase 1.

Reason:

- The data is not row-specific
- The payload is short-lived context
- Persisting it in `AccessLog` would blur semantics and create stale data risk

## Testing Strategy

### Backend

Add tests for:

1. IPPure service success normalization
2. IPPure service graceful failure
3. tracking log list includes `server_ip_context`
4. tracking log detail includes `server_ip_context`

Mock network calls so tests do not depend on the external endpoint.

### Frontend

Add tests for:

1. card helper formatting with server IP context
2. helper formatting fallback without server IP context
3. dashboard rendering of the new server-egress summary
4. detail dialog rendering of the server IP intelligence section

## Rollout

### Phase 1

- add backend IPPure service
- integrate with tracking admin APIs
- render server egress IP summary in card and detail dialog
- ship tests

### Phase 2

If later a real arbitrary-IP lookup capability becomes available, keep the same UI separation and introduce a second payload for visitor-IP enrichment rather than overloading `server_ip_context`.

## Success Criteria

This work is successful when:

1. Tracking dashboard log list still loads normally.
2. Device/access info cards show additional server egress IP context when available.
3. Detail dialog shows a dedicated `服务器出口 IP 情报` section.
4. IPPure request failures do not break the page.
5. Tests cover both enriched and degraded paths.
