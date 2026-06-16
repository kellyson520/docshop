# Device Tracking Display Design

Date: 2026-06-16

## Goal

Improve the admin tracking dashboard so operators can quickly identify the actual client device being used. The tracking log should display device type plus a normalized brand/model summary in the existing `设备` column, with cleaner layout and more consistent row sizing. Backend parsing should also be strengthened so mobile, tablet, and desktop visits all return the best available device model instead of generic or noisy values.

## Current Context

The project already records device-related fields in tracking logs:

- `backend/app/models/access_log.py` contains `device_type`, `device_brand`, `device_model`, `os_name`, and `browser_name`.
- `backend/app/middlewares/tracking.py` populates those fields during request logging.
- `GET /admin/tracking/logs` already returns those fields through `AccessLog.to_dict()`.

The current admin UI is the main gap:

- `frontend/src/views/admin/TrackingDashboard.vue` only shows a tag for `device_type` in the `设备` column.
- `frontend/src/utils/trackingDisplay.js` does not yet provide any helper for normalized device brand/model display.

The current backend fallback parser is also too weak:

- Apple mobile devices are only generically recognized.
- Android parsing can produce noisy model strings.
- Desktop devices usually collapse to broad values like `PC` or `Mac`.
- There is no normalization strategy that prefers clean, stable labels over raw UA fragments.

## Chosen Approach

Use a combined frontend + backend enhancement:

1. Keep the existing `设备` column instead of adding new columns.
2. Upgrade the cell into a structured multi-line device summary.
3. Strengthen backend User-Agent fallback parsing and normalization.
4. Prefer short, stable, readable device descriptions over overfitted or dirty raw values.

This keeps the table compact while meaningfully improving recognizability for all device classes.

## User-Facing Display Rules

The existing `设备` column becomes the primary quick-recognition entry for hardware context.

Each device cell should display three information layers:

1. **Device type tag**
   - `桌面端`
   - `移动端`
   - `平板`

2. **Primary device summary**
   - Preferred form: `brand + model`
   - If only model exists: show model
   - If only brand exists: show brand
   - If neither exists: show a normalized fallback label

3. **Secondary environment summary**
   - `OS · Browser`
   - Example: `Android · Chrome`
   - Example: `macOS · Safari`

Example target outputs:

- `移动端 / Xiaomi 14 / Android · Chrome`
- `平板 / Apple iPad / iOS · Safari`
- `桌面端 / Windows PC / Windows · Edge`
- `桌面端 / Apple Mac / macOS · Safari`

The table still keeps separate `系统` and `浏览器` columns for single-dimension filtering and scanning, but the device column becomes the operator’s main glanceable summary.

## Fallback and Normalization Rules

The system should avoid dumping raw UA fragments into the UI. When exact model detection is not trustworthy, it should return stable generalized values.

### Mobile

- If normalized brand and model are available, show both.
- If only model is reliable, show model.
- If nothing reliable is available, fall back to:
  - `未知手机` for `mobile`
  - `未知平板` for `tablet`

### Desktop

Desktop browsers usually do not expose true hardware models in the UA, so the fallback must be intentionally generalized:

- Windows → `Windows PC`
- macOS → `Apple Mac`
- Linux → `Linux PC`
- Other desktop → `桌面设备`

### Data Cleanliness Principle

- Prefer readable normalization over raw completeness.
- Reject obviously dirty model fragments.
- Keep output short enough for dense tables.
- Never surface long UA substrings like full engine/platform segments.

## Backend Design

### Parsing Priority

`backend/app/middlewares/tracking.py` continues to use a two-stage strategy:

1. **Client Hints parser:** `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`
2. **Primary parser:** `user_agents.parse(...)`
3. **Fallback parser:** enhanced `_simple_user_agent_parse(...)`

Client Hints should be preferred for browser family, browser version, platform, and mobile-vs-desktop classification when present, because they are often cleaner than legacy UA strings. `user_agents` and the fallback parser should continue to provide device brand/model enrichment.

If the primary parser yields useful `device.brand` and `device.model`, preserve them after light normalization. If the primary parser is missing, unavailable, or too vague, the fallback parser supplies a better stable value.

### Client Hints Rules

When available, parse these headers before relying on legacy UA heuristics:

- `sec-ch-ua`
- `sec-ch-ua-mobile`
- `sec-ch-ua-platform`

Normalization rules:

- ignore fake brands such as `Not)A;Brand`
- if `Microsoft Edge` is present, normalize browser to `Edge`
- otherwise recognize stable browser families such as Chromium, Chrome, Safari, and Firefox where applicable
- extract a compact major version from the client hints brand/version tuple
- `sec-ch-ua-mobile=?1` should bias classification toward `mobile`
- `sec-ch-ua-mobile=?0` should bias classification toward non-mobile
- `sec-ch-ua-platform` should normalize to `Windows`, `Android`, `iOS`, `macOS`, or `Linux`

Client Hints should not replace model extraction logic for Android hardware. They mainly provide cleaner browser and platform identification.

### Apple Rules

- `iPhone` → brand `Apple`, model `iPhone`
- `iPad` → brand `Apple`, model `iPad`
- `Macintosh` / `Mac OS` → brand `Apple`, model `Mac`

The system should not invent false Apple generation-level models such as `iPhone 14 Pro` unless they are actually available from a reliable source.

### Android Rules

For Android UA parsing, extract a likely model candidate from the device segment before `Build/` and then clean it:

- Remove noise such as locale fragments, `wv`, extra semicolon blocks, and version-only tokens.
- Detect and normalize common vendors:
  - `Xiaomi`
  - `Redmi`
  - `HUAWEI`
  - `HONOR`
  - `vivo`
  - `OPPO`
  - `OnePlus`
  - `Samsung`
  - `realme`

Brand normalization should standardize casing and avoid duplicated output like `Xiaomi Xiaomi 14`.

If the extracted candidate is too noisy or too generic, fall back to:

- `Android Device` for mobile
- `Android Tablet` for tablet

### Desktop Rules

Desktop fallback should intentionally be broad but readable:

- Windows → brand `Microsoft` or normalized display `Windows PC`
- macOS → brand `Apple`, model `Mac`
- Linux → brand `Linux`, model `PC`

The display layer may collapse these into the final user-facing string rather than showing unnatural combinations.

### Normalization Helper

Introduce a dedicated normalization helper in the tracking parsing path so backend output is consistent before it reaches the UI. The helper should:

- trim whitespace
- normalize casing
- remove duplicate brand/model repetition
- discard meaningless placeholders
- convert empty results into `None`

This helper should be used for both the `user_agents` result and the fallback parser result.

### Referer Parsing Rules

The backend should strengthen referer handling instead of storing it only as an opaque raw string.

Suggested normalized referer fields:

- raw referer URL
- referer host, for example `www.limestart.cn`
- referer registrable domain, for example `limestart.cn`
- referer type:
  - `direct`
  - `internal`
  - `external`
  - `unknown`

Normalization rules:

- no referer header -> `direct`
- same-site referer -> `internal`
- different-site referer -> `external`
- invalid or unparsable referer -> `unknown`

The raw referer value can remain persisted for audit/debugging, but UI and analytics logic should prefer the normalized host/domain when available.

### Example Expected Parsing

For a request such as:

- `referer: https://www.limestart.cn/`
- `sec-ch-ua: "Microsoft Edge";v="149", "Chromium";v="149", "Not)A;Brand";v="24"`
- `sec-ch-ua-mobile: ?0`
- `sec-ch-ua-platform: "Windows"`
- `user-agent: ... Edg/149.0.0.0`

The normalized result should converge toward:

- referer host: `www.limestart.cn`
- referer domain: `limestart.cn`
- referer type: `external`
- browser name: `Edge`
- browser version: `149`
- platform / OS: `Windows`
- device type: `desktop`
- user-facing device summary: `Windows PC`

## Frontend Design

### Tracking Log Table

In `frontend/src/views/admin/TrackingDashboard.vue`, update the `设备` column from a single tag to a compact structured block:

- first row: device type tag
- second row: primary device summary
- third row: secondary OS/browser summary

The existing `系统` and `浏览器` columns remain, but their content stays short and single-line.

### Display Helpers

Add focused helpers in `frontend/src/utils/trackingDisplay.js`, such as:

- `formatDevicePrimary(row)`
- `formatDeviceSecondary(row)`
- `formatDeviceTooltip(row)`
- `formatDeviceFallback(row)`

These helpers should centralize display logic instead of embedding complex branching directly in the Vue template.

### Responsive Layout

The design should avoid adding any extra columns, because the admin tracking table is already dense. The upgraded device cell must work within the current table structure, including on smaller screens or narrower browser windows.

### Statistics Section Layout Rework

The `访问统计` area should not keep the current three-way equal split for device type, browser, and operating system. Real data density is uneven, and equal-width tables create mismatched container heights and large blank areas under shorter cards.

Replace that with a primary-secondary layout:

- left primary card: browser distribution
- right upper compact card: device type
- right lower compact card: operating system

Recommended desktop grid:

- outer columns: `1.6fr 1fr`
- right side rows: `1fr 1fr`

This gives the longest dataset to the widest area and prevents short datasets from visually wasting space. The `7天趋势` block should remain on its own full-width row below, so it is no longer stretched apart by the tallest distribution card above it.

## Layout and Typography Rules

The current device section feels visually uneven. The new layout should make every row more consistent.

### Column Width

Increase the `设备` column width from the current narrow tag-oriented width to approximately `180-220px`, with final tuning based on the existing table balance.

### Vertical Structure

Each cell uses a fixed stacked structure:

- row 1: tag
- row 2: device brand/model
- row 3: OS/browser summary

### Typography

- tag: existing small tag size
- primary line: medium emphasis, consistent line height
- secondary line: smaller, muted color

### Overflow Handling

- primary and secondary lines should use ellipsis
- full content should be available through tooltip
- long noisy strings should already be reduced by backend normalization before reaching this layer

### Consistent Row Height

The goal is not to make every row pixel-identical, but rows should remain visually stable:

- fixed internal spacing between stacked lines
- no uncontrolled wrapping of long model strings
- no multi-line UA spillover

This addresses the current complaint that the table looks messy and elements appear at inconsistent sizes.

## Distribution Card Rules

The upper analytics block should feel compact and balanced rather than like three unrelated tables.

### Browser Distribution Card

- use it as the primary card
- allow greater height than the side cards
- show top rows by default
- if the list is long, prefer internal scrolling or controlled expansion instead of making the whole section excessively tall

### Device Type Card

Device type usually has only a few rows, so it should not sit inside a large empty table shell. Prefer a compact summary style:

- dense list rows, or
- small metric rows with label and count

The visual goal is to make the card feel intentionally compact, not unfinished.

### Operating System Card

Operating system can remain a compact table or list, but should use:

- tighter row height
- fixed card height aligned with the right-side stack
- internal scrolling when the list is longer than the visible area

### Trend Separation

The `7天趋势` block should start immediately below the distribution section with fixed spacing. It must not inherit large vertical whitespace caused by uneven card heights above.

### Responsive Behavior

On smaller widths:

- collapse the distribution section into a single-column stack
- order it as browser, device type, operating system
- keep title height, card spacing, and inner padding consistent

This preserves the desktop optimization without creating cramped side cards on small screens.

## Data Flow

1. Request enters tracking middleware.
2. Middleware parses Client Hints when available.
3. Middleware parses User-Agent with primary parser, then fallback if needed.
4. Backend normalization produces stable device, browser, platform, and referer-derived fields.
5. Access log persists normalized fields.
6. Admin logs API returns normalized fields unchanged.
7. Frontend helpers build the final compact display for the existing `设备` column.
8. Frontend places browser, device type, and operating system data into the new primary-secondary analytics layout.

## Error Handling and Edge Cases

- If UA parsing fails completely, keep `device_type` if possible and use fallback labels.
- If Client Hints are partially present, use the available pieces without requiring all headers.
- If `user_agents` is unavailable, the fallback parser must still produce readable results.
- If Android extraction yields obvious garbage, discard it rather than exposing it.
- If OS or browser is missing, secondary summary should degrade gracefully, for example showing only one side instead of `unknown · unknown`.
- If both `device_brand` and `device_model` are absent, frontend should show the normalized fallback rather than blank content.
- If referer parsing fails, keep the raw referer if available but classify the normalized type as `unknown`.

## Testing Strategy

### Backend Tests

Add coverage for the enhanced fallback parser and normalization behavior:

- Client Hints parse `Microsoft Edge` correctly from `sec-ch-ua`
- `sec-ch-ua-platform` normalizes Windows correctly
- `sec-ch-ua-mobile=?0` supports desktop classification
- referer `https://www.limestart.cn/` normalizes host/domain and classifies as `external`
- iPhone UA returns `Apple / iPhone`
- iPad UA returns `Apple / iPad`
- common Android phone UA returns a cleaned model
- common Android tablet UA returns tablet classification and cleaned value
- Windows UA returns normalized desktop fallback
- macOS UA returns `Apple / Mac`
- dirty Android candidate is rejected and replaced by generalized fallback

### Frontend Tests

Add coverage for device display helpers and the tracking dashboard table:

- device column renders type tag + primary summary + secondary summary
- missing brand/model falls back correctly
- overflow content still exposes tooltip text
- system/browser summary degrades gracefully when one side is missing
- browser distribution renders as the primary analytics card
- device type and operating system render as compact side cards without large empty filler
- trend block remains visually independent below the distribution area

### Manual Verification

Verify with real admin tracking rows covering:

- Edge on Windows with Client Hints present
- external referer such as `www.limestart.cn`
- iPhone / iPad visits
- Android phone visits
- Android tablet visits
- Windows desktop visits
- macOS desktop visits
- Linux desktop visits
- uneven browser/device/os list lengths
- no large blank vertical area under short analytics cards

The desired outcome is that the table is easier to scan and that most rows now show a recognizable device summary instead of only a generic device type.

## Non-Goals

- No new standalone device-model analytics dashboard in this change.
- No new separate `品牌` or `型号` table columns.
- No attempt to guarantee exact physical hardware identification for desktop browsers.
- No device fingerprint redesign in this iteration.

These can be considered in later tracking analytics work if needed.
