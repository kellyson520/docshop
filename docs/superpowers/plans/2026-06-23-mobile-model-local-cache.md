# Mobile Model Local Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve mobile User-Agent model codes to readable phone names in access logs using a low-cost local MobileModels CSV cache.

**Architecture:** Add a backend CSV sync/cache layer and a resolver used by `TrackingMiddleware`. Store only resolved display fields in `AccessLog`; frontend consumes those fields and keeps existing fallback behavior.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite additive migrations, Python stdlib CSV/JSON/urllib, Vue 3, Vitest, Pytest

---

## File Structure

### Backend

- Create: `backend/app/services/mobile_model_resolver.py`
  - Extract model codes from User-Agent.
  - Load `mobile_models.json` cache.
  - Resolve model fields conservatively.
- Create: `backend/app/services/mobile_model_sync.py`
  - Download MobileModels CSV.
  - Parse and normalize it.
  - Write `mobile_models.csv`, `mobile_models.json`, `mobile_models.meta.json` atomically.
- Modify: `backend/app/config.py`
  - Add mobile-model cache settings with safe defaults.
- Modify: `backend/app/models/access_log.py`
  - Add resolved model fields and include them in `to_dict()`.
- Modify: `backend/app/database.py`
  - Add additive SQLite migration columns.
- Modify: `backend/app/middlewares/tracking.py`
  - Resolve model info from User-Agent when writing access logs.
  - Trigger stale/missing cache refresh in a non-blocking way.
- Modify/Create tests:
  - `test/test_mobile_model_resolver.py`
  - `test/test_mobile_model_sync.py`
  - `test/test_tracking_access_log.py`
  - `test/test_tracking_middleware.py`

### Frontend

- Modify: `frontend/src/utils/trackingDisplay.js`
  - Prefer `device_display_name` in device primary display.
- Modify tests:
  - `frontend/src/utils/__tests__/trackingDisplay.spec.js`
  - `frontend/src/utils/__tests__/frontend-regressions.spec.js`

---

## Task 1: Add AccessLog storage fields and migration

**Files:**
- Modify: `backend/app/models/access_log.py`
- Modify: `backend/app/database.py`
- Test: `test/test_tracking_access_log.py`

- [ ] Write failing tests asserting `AccessLog.to_dict()` exposes:
  - `device_model_code`
  - `device_model_name`
  - `device_brand_name`
  - `device_display_name`

- [ ] Write failing migration test asserting `_access_log_additive_statements()` contains additive SQL for the four columns.

- [ ] Run:

```powershell
python -m pytest -o addopts='-q' test/test_tracking_access_log.py
```

Expected: FAIL because model fields/migrations do not exist.

- [ ] Add nullable columns to `AccessLog`:

```python
device_model_code = Column(String(100), nullable=True)
device_model_name = Column(String(255), nullable=True)
device_brand_name = Column(String(100), nullable=True)
device_display_name = Column(String(255), nullable=True)
```

- [ ] Include those fields in `to_dict()`.

- [ ] Add SQLite additive migration statements in `backend/app/database.py`.

- [ ] Re-run the same pytest command.

Expected: PASS.

---

## Task 2: Implement local cache parser and resolver

**Files:**
- Create: `backend/app/services/mobile_model_resolver.py`
- Test: `test/test_mobile_model_resolver.py`

- [ ] Write failing tests with a tiny cache fixture:

```python
mapping = {
    "ANA-AL00": {
        "brand_title": "Huawei",
        "model_name": "P40",
        "ver_name": "ANA-AL00",
    },
    "SM-G9980": {
        "brand_title": "Samsung",
        "model_name": "Galaxy S21 Ultra",
        "ver_name": "SM-G9980",
    },
}
```

Test cases:

- UA containing `ANA-AL00` resolves to `Huawei P40 / ANA-AL00`.
- UA containing `SM-G9980` resolves to `Samsung Galaxy S21 Ultra / SM-G9980`.
- Unknown UA returns `{}`.
- Resolver does not guess on partial codes.

- [ ] Run:

```powershell
python -m pytest -o addopts='-q' test/test_mobile_model_resolver.py
```

Expected: FAIL because resolver module does not exist.

- [ ] Implement `normalize_model_code(value: str) -> str`:

```python
return re.sub(r"\s+", "", value or "").strip().upper()
```

- [ ] Implement `extract_model_codes(user_agent: str) -> list[str]`:
  - Extract tokens from Android UA segments.
  - Include tokens with uppercase letters/digits and separators `-`, `_`, `.`.
  - Ignore obvious generic tokens: `ANDROID`, `MOBILE`, `BUILD`, `LINUX`, `CHROME`, `SAFARI`, `VERSION`.

- [ ] Implement `MobileModelResolver(cache_path)`:
  - Loads JSON lazily.
  - Reloads when file mtime changes.
  - Returns dict fields only on exact normalized match.

- [ ] Re-run resolver tests.

Expected: PASS.

---

## Task 3: Implement MobileModels CSV sync/cache writer

**Files:**
- Create: `backend/app/services/mobile_model_sync.py`
- Modify: `backend/app/config.py`
- Test: `test/test_mobile_model_sync.py`

- [ ] Write failing tests for:
  - Parsing CSV rows with columns `model`, `brand_title`, `model_name`, `ver_name`.
  - Writing normalized JSON atomically.
  - Keeping existing cache when download/parser fails.
  - `is_cache_stale(meta_path, interval_hours=168)` behavior.

- [ ] Run:

```powershell
python -m pytest -o addopts='-q' test/test_mobile_model_sync.py
```

Expected: FAIL because sync module does not exist.

- [ ] Add config defaults in `backend/app/config.py`:

```python
MOBILE_MODEL_SYNC_ENABLED: bool = True
MOBILE_MODEL_SYNC_INTERVAL_HOURS: int = 168
MOBILE_MODEL_SOURCE_URL: str = "https://raw.githubusercontent.com/KHwang9883/MobileModels-csv/main/models.csv"
MOBILE_MODEL_CACHE_DIR: str = "./data/cache"
MOBILE_MODEL_DOWNLOAD_TIMEOUT_SECONDS: int = 15
MOBILE_MODEL_MAX_DOWNLOAD_BYTES: int = 20 * 1024 * 1024
```

- [ ] Implement CSV parsing using `csv.DictReader`.

- [ ] Implement atomic writes:

```python
tmp_path.write_text(...)
tmp_path.replace(final_path)
```

- [ ] Implement `refresh_mobile_model_cache(settings)` that:
  - Downloads CSV with timeout.
  - Rejects oversized response.
  - Writes raw CSV, normalized JSON, and meta JSON.
  - Returns a result dict with `updated`, `row_count`, and `error`.

- [ ] Re-run sync tests.

Expected: PASS.

---

## Task 4: Wire resolver into TrackingMiddleware

**Files:**
- Modify: `backend/app/middlewares/tracking.py`
- Test: `test/test_tracking_middleware.py`

- [ ] Write failing middleware tests asserting:
  - Known Android UA stores resolved model fields on `AccessLog`.
  - Unknown UA leaves fields empty.
  - Resolver errors do not prevent access log creation.

- [ ] Run:

```powershell
python -m pytest -o addopts='-q' test/test_tracking_middleware.py
```

Expected: FAIL because middleware does not resolve model fields.

- [ ] Instantiate or lazily access resolver in middleware using configured cache path.

- [ ] In the access-log construction path, merge resolved fields:

```python
resolved_model = resolve_mobile_model_from_user_agent(user_agent)
log.device_model_code = resolved_model.get("device_model_code")
log.device_model_name = resolved_model.get("device_model_name")
log.device_brand_name = resolved_model.get("device_brand_name")
log.device_display_name = resolved_model.get("device_display_name")
```

- [ ] Catch resolver exceptions and continue.

- [ ] Re-run middleware tests.

Expected: PASS.

---

## Task 5: Add non-blocking stale-cache refresh

**Files:**
- Modify: `backend/app/middlewares/tracking.py`
- Modify: `backend/app/main.py` only if startup hook is cleaner in current codebase
- Test: `test/test_mobile_model_sync.py` or `test/test_tracking_middleware.py`

- [ ] Write failing test proving stale/missing cache triggers refresh helper once without blocking request handling.

- [ ] Run focused test.

- [ ] Implement a small guard around background refresh:

```python
if mobile_model_cache_needs_refresh(settings) and not _mobile_model_refresh_in_flight:
    create_logged_task(refresh_mobile_model_cache_async(settings), name="mobile-model-cache-refresh")
```

- [ ] Ensure refresh is skipped when `MOBILE_MODEL_SYNC_ENABLED=false`.

- [ ] Re-run focused test.

Expected: PASS.

---

## Task 6: Frontend log display prefers resolved model names

**Files:**
- Modify: `frontend/src/utils/trackingDisplay.js`
- Test: `frontend/src/utils/__tests__/trackingDisplay.spec.js`
- Test: `frontend/src/utils/__tests__/frontend-regressions.spec.js`

- [ ] Write failing Vitest asserting:
  - `formatDevicePrimary({ device_display_name: 'Huawei P40 / ANA-AL00' })` returns that display name.
  - Existing fallback still returns browser/device text when `device_display_name` is missing.

- [ ] Run:

```powershell
cd frontend
npm test -- --run src/utils/__tests__/trackingDisplay.spec.js
```

Expected: FAIL because formatter does not prefer resolved display name.

- [ ] Update `formatDevicePrimary(row)` to return `row.device_display_name` first when present.

- [ ] Add/adjust source regression test confirming TrackingDashboard still imports `formatDevicePrimary` and does not fetch the mobile-model CSV directly.

- [ ] Re-run:

```powershell
npm test -- --run src/utils/__tests__/trackingDisplay.spec.js src/utils/__tests__/frontend-regressions.spec.js
```

Expected: PASS.

---

## Task 7: Documentation and attribution

**Files:**
- Modify: `docs/dependencies.md`
- Modify: `README.md` or `docs/docker-deployment.md`
- Optional: `.env.example`

- [ ] Add attribution note for MobileModels and license `CC BY-NC-SA 4.0`.

- [ ] Document cache files and settings:

```env
MOBILE_MODEL_SYNC_ENABLED=true
MOBILE_MODEL_SYNC_INTERVAL_HOURS=168
MOBILE_MODEL_SOURCE_URL=https://raw.githubusercontent.com/KHwang9883/MobileModels-csv/main/models.csv
MOBILE_MODEL_CACHE_DIR=/app/data/cache
MOBILE_MODEL_DOWNLOAD_TIMEOUT_SECONDS=15
```

- [ ] Document failure behavior: old cache remains in use, no cache falls back to existing device display.

---

## Task 8: Final verification

- [ ] Backend compile:

```powershell
cd backend
python -m py_compile app/services/mobile_model_resolver.py app/services/mobile_model_sync.py app/models/access_log.py app/database.py app/middlewares/tracking.py app/config.py
```

- [ ] Backend tests:

```powershell
cd C:\Users\lihuo\Desktop\docshop
python -m pytest -o addopts='-q' test/test_mobile_model_resolver.py test/test_mobile_model_sync.py test/test_tracking_access_log.py test/test_tracking_middleware.py
```

- [ ] Frontend tests:

```powershell
cd frontend
npm test -- --run src/utils/__tests__/trackingDisplay.spec.js src/utils/__tests__/frontend-regressions.spec.js
```

- [ ] Frontend build:

```powershell
cd frontend
npm run build
```

---

## Self-Review Notes

- The plan implements the selected local-cache approach only.
- It does not add a database table for all model mappings.
- It does not add admin UI refresh controls in Phase 1.
- It preserves existing behavior when the cache is absent or stale.
- It keeps matching conservative and exact to avoid wrong device names.
