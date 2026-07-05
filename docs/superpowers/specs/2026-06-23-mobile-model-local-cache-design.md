# Mobile Model Local Cache Design

Date: 2026-06-23

## Goal

Improve access-log device display by resolving mobile User-Agent model codes such as `ANA-AL00`, `SM-G9980`, or `M2012K11AC` to readable brand/model names, using the MobileModels CSV data as a low-cost local cache.

## Chosen Approach

Use a local cache file, not a database table, for Phase 1.

Data source:

- Primary CSV URL: `https://raw.githubusercontent.com/KHwang9883/MobileModels-csv/main/models.csv`
- Source project: `https://github.com/KHwang9883/MobileModels`
- CSV project: `https://github.com/KHwang9883/MobileModels-csv`

Local files:

- `data/cache/mobile_models.csv` stores the downloaded CSV.
- `data/cache/mobile_models.json` stores the normalized lookup map.
- `data/cache/mobile_models.meta.json` stores update time, source URL, and row count.

The application must keep working when the network is unavailable. If the cache cannot be refreshed, the resolver uses the last successful cache. If no cache exists, it falls back to existing device display behavior.

## Backend Components

### `app/services/mobile_model_resolver.py`

Responsibilities:

1. Load normalized model mapping from `mobile_models.json`.
2. Extract possible model codes from User-Agent strings.
3. Resolve model codes to readable fields.
4. Keep an in-memory lookup cache with file mtime invalidation.
5. Return a small result object/dict:

```python
{
  "device_model_code": "ANA-AL00",
  "device_brand_name": "Huawei",
  "device_model_name": "P40",
  "device_display_name": "Huawei P40 / ANA-AL00"
}
```

Resolution should be conservative:

- Prefer exact match on normalized model code.
- Normalize case and separators where safe.
- Do not guess a model name if there is no exact match.
- Keep original behavior for desktop, bots, tablets, and unknown devices.

### `app/services/mobile_model_sync.py`

Responsibilities:

1. Download CSV with timeout and retries.
2. Parse the known CSV columns.
3. Build a compact normalized JSON map keyed by model code.
4. Write files atomically through temporary files and rename.
5. Enforce size limits to avoid accidentally caching a bad or huge response.

Default behavior:

- Startup attempts refresh only when cache is missing or older than 7 days.
- Refresh failure logs a warning but does not fail startup.
- Optional admin/manual refresh can be added later, not in Phase 1.

## Storage Fields

Add optional fields to `AccessLog`:

- `device_model_code`
- `device_model_name`
- `device_brand_name`
- `device_display_name`

SQLite migration is additive only. Existing rows remain valid.

`AccessLog.to_dict()` includes these fields.

## Tracking Flow

1. `TrackingMiddleware` receives request.
2. Existing User-Agent parsing determines device type, OS, browser.
3. Mobile model resolver extracts and resolves model code.
4. If matched, middleware stores model fields in `AccessLog`.
5. Admin log API returns these fields through `to_dict()`.
6. Frontend log table displays `device_display_name` first, then falls back to existing device summary.

## Frontend Display

Update `trackingDisplay.js`:

- `formatDevicePrimary(row)` should prefer `row.device_display_name`.
- Existing browser/OS/device type fallback stays unchanged.
- Tooltip/secondary display can include the raw model code when useful.

Tracking dashboard should not fetch the model mapping directly. It only consumes log API fields.

## Configuration

Add settings with safe defaults:

```env
MOBILE_MODEL_SYNC_ENABLED=true
MOBILE_MODEL_SYNC_INTERVAL_HOURS=168
MOBILE_MODEL_SOURCE_URL=https://raw.githubusercontent.com/KHwang9883/MobileModels-csv/main/models.csv
MOBILE_MODEL_CACHE_DIR=/app/data/cache
MOBILE_MODEL_DOWNLOAD_TIMEOUT_SECONDS=15
```

Local Windows/dev defaults use `./data/cache` through existing data path conventions.

## Error Handling

- Network timeout: keep old cache and log warning.
- Invalid CSV: keep old cache and log warning.
- Missing cache: return unresolved result and do not block request.
- Oversized response: reject and keep old cache.
- Resolver exceptions inside middleware: catch, log debug/warning, continue logging base access log.

## Privacy and Licensing Notes

The mapping uses device model codes from User-Agent and does not add new tracking identifiers. It only makes existing User-Agent-derived data more readable.

MobileModels is licensed under CC BY-NC-SA 4.0. This project should keep attribution in docs and avoid bundling it into commercial redistributions without confirming license compatibility.

## Tests

Backend tests:

- Resolver extracts model code from representative Android User-Agent strings.
- Resolver maps exact model code to display name from a small fixture CSV/JSON.
- Resolver returns empty result for unknown devices.
- Sync parser writes normalized cache atomically from fixture CSV.
- Sync failure keeps previous cache.
- AccessLog fields and migrations are additive.
- TrackingMiddleware stores resolved fields when model is known.

Frontend tests:

- `formatDevicePrimary()` prefers `device_display_name`.
- Existing fallback still works when no resolved model exists.
- TrackingDashboard source keeps display logic delegated to `trackingDisplay.js`.

## Out of Scope for Phase 1

- Admin UI for manual model-cache refresh.
- Database table for model mappings.
- Background scheduler UI and progress bar.
- Fuzzy matching beyond safe normalization.
- Storing every imported model row in SQLite.
