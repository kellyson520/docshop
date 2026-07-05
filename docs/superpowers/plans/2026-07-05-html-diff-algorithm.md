# HTML Diff Algorithm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **User constraint:** Do not commit, push, reset, clean, or otherwise mutate git history.

**Goal:** Replace the current HTML "side-by-side preview only" comparison with a semantic HTML diff that detects text, DOM node, attribute, resource, and table changes while keeping runtime preview security boundaries.

**Architecture:** Backend adds `HtmlDiffEngine` under the existing diff engine registry and returns the same canonical diff shape used by other engines. Frontend adds `HtmlDiffView.vue` and changes `DiffView.vue` so HTML files render real diff summaries/hunks plus side-by-side runtime previews instead of `stats.total_changes = 0`. Tests are written first for engine behavior and UI routing.

**Tech Stack:** Python stdlib `html.parser`, `difflib.SequenceMatcher`, FastAPI diff service, Vue 3 Composition API, Vitest, pytest.

---

## File Structure

### Backend create

- `backend/app/diff_engine/html_diff.py`
  - Parses and normalizes HTML into semantic nodes.
  - Compares text blocks, attributes, links/images/resources, tables, and moved nodes.
  - Emits canonical `html_diff` result with bounded snippets.

- `backend/tests/test_html_diff.py`
  - TDD coverage for semantic text changes, moved nodes, attributes/resources, tables, and factory registration.

### Backend modify

- `backend/app/diff_engine/factory.py`
  - Register `html` and `htm` with `HtmlDiffEngine`.

- `backend/app/services/diff_service.py`
  - Map `html_diff` to diff type `html`.

- `backend/app/schemas/diff_result.py`
  - Preserve `nodes`, `attributes`, and `resources` in normalized results.

### Frontend create

- `frontend/src/components/diff/HtmlDiffView.vue`
  - Renders semantic HTML diff cards, filters, and optional runtime preview iframe pair.

- `frontend/src/components/diff/__tests__/HtmlDiffView.spec.js`
  - Verifies summary cards, filters, and escaped snippets.

### Frontend modify

- `frontend/src/views/admin/DiffView.vue`
  - Use real `getDiffs()` for HTML files.
  - Route `diff_type === "html"` / payload type `html_diff` to `HtmlDiffView`.
  - Keep side-by-side runtime iframe URLs as preview context.

- `frontend/src/views/admin/__tests__/DiffView.spec.js`
  - Verify HTML files no longer use `html_preview` fallback with zero changes.

---

## Task 1: Backend HTML Diff Engine

**Files:**
- Create: `backend/tests/test_html_diff.py`
- Create: `backend/app/diff_engine/html_diff.py`
- Modify: `backend/app/diff_engine/factory.py`
- Modify: `backend/app/services/diff_service.py`
- Modify: `backend/app/schemas/diff_result.py`

- [x] **Step 1: Write failing backend tests**

Cover:

```python
def test_html_diff_detects_text_attribute_resource_table_and_move(tmp_path):
    ...

def test_html_diff_is_registered_for_html_and_htm():
    ...
```

Expected before implementation:

```powershell
python -m pytest backend/tests/test_html_diff.py -q
```

fails because `HtmlDiffEngine` and registry entries do not exist.

- [x] **Step 2: Implement minimal semantic parser and diff engine**

Implementation requirements:

- Strip comments, `script`, and `style`.
- Collapse whitespace.
- Tokenize semantic nodes:
  - headings, paragraphs, list items, table rows/cells, links, images, form controls.
- Compare nodes by stable key first, then fuzzy text.
- Classify:
  - `added`, `deleted`, `modified`, `moved`, `attribute_changed`, `resource_changed`, `table_changed`.
- Escape/cap snippets; never emit full raw HTML.

- [x] **Step 3: Register engine and normalize result**

Register:

```python
ENGINE_REGISTRY = {
    "docx": DocxDiffEngine,
    "xlsx": XlsxDiffEngine,
    "pdf": PdfDiffEngine,
    "html": HtmlDiffEngine,
    "htm": HtmlDiffEngine,
}
```

Map `html_diff` to stored `diff_type = "html"`.

- [x] **Step 4: Run backend verification**

Run:

```powershell
python -m pytest backend/tests/test_html_diff.py backend/tests/test_diff_result_schema.py backend/tests/test_diff_service.py -q
```

Expected: all pass.

---

## Task 2: Frontend HTML Diff View

**Files:**
- Create: `frontend/src/components/diff/HtmlDiffView.vue`
- Create: `frontend/src/components/diff/__tests__/HtmlDiffView.spec.js`
- Modify: `frontend/src/views/admin/DiffView.vue`
- Modify: `frontend/src/views/admin/__tests__/DiffView.spec.js`

- [x] **Step 1: Write failing frontend tests**

Cover:

```js
it('renders html semantic diff sections and escapes snippets', async () => { ... })
it('routes html_diff payloads to HtmlDiffView instead of zero-change preview fallback', async () => { ... })
```

Run:

```powershell
npm.cmd run test -- src/components/diff/__tests__/HtmlDiffView.spec.js src/views/admin/__tests__/DiffView.spec.js --run
```

Expected before implementation: fails because `HtmlDiffView.vue` does not exist and `DiffView.vue` still uses `html_preview` fallback.

- [x] **Step 2: Implement `HtmlDiffView.vue`**

View requirements:

- summary cards for added/deleted/modified/moved/attribute/resource/table changes
- filter buttons for all/text/structure/attributes/resources/tables
- escaped snippets using Vue interpolation only, not `v-html`
- side-by-side iframe previews when `payload.old_preview_url` / `payload.new_preview_url` exist

- [x] **Step 3: Wire `DiffView.vue`**

- Remove HTML-specific early return fallback.
- Let HTML call `getDiffs()`.
- Render `HtmlDiffView` for:
  - `diffData.diff_type === "html"`
  - `diffData.type === "html_diff"`
  - `fileType === "html" || fileType === "htm"` with html payload.

- [x] **Step 4: Run frontend verification**

Run:

```powershell
npm.cmd run test -- src/components/diff/__tests__/HtmlDiffView.spec.js src/views/admin/__tests__/DiffView.spec.js --run
```

Expected: all pass.

---

## Task 3: Full Verification and Docs

**Files:**
- Modify: `docs/frontend-browser-resource-protocol.md`
- Modify: `docs/superpowers/plans/2026-07-05-html-diff-algorithm.md`

- [x] **Step 1: Run targeted backend suite**

```powershell
python -m pytest backend/tests/test_html_diff.py backend/tests/test_diff_result_schema.py backend/tests/test_diff_service.py -q
```

- [x] **Step 2: Run targeted frontend suite**

```powershell
npm.cmd run test -- src/components/diff/__tests__/HtmlDiffView.spec.js src/views/admin/__tests__/DiffView.spec.js --run
```

- [x] **Step 3: Run build**

```powershell
npm.cmd run build
```

- [x] **Step 4: Update docs with completed status**

Record exact test/build results and any remaining optional UI review items.

---

## Self-Review

- Spec coverage:
  - Real HTML semantic diff: Task 1
  - UI rendering and filtering: Task 2
  - Verification/docs: Task 3
- Placeholder scan:
  - No TODO/TBD placeholders.
- Type consistency:
  - Backend result type: `html_diff`
  - Stored `diff_type`: `html`
  - Frontend component: `HtmlDiffView`
- User constraint:
  - No commit/reset/clean/push steps.


---

## Execution Update (2026-07-05 12:18)

- [x] Backend HTML semantic diff engine implemented:
  - Added `backend/app/diff_engine/html_diff.py`.
  - Registered `html` / `htm` in diff engine factory.
  - Mapped `html_diff` persistence to stored `diff_type = "html"`.
  - Preserved `nodes`, `attributes`, and `resources` in normalized diff payloads.
- [x] Frontend HTML semantic diff view implemented:
  - Added `frontend/src/components/diff/HtmlDiffView.vue`.
  - HTML comparisons now call real diff API instead of zero-change `html_preview` fallback.
  - UI renders text / structure / attribute / resource / table filters and optional side-by-side runtime iframe previews.
  - Snippets are rendered through Vue interpolation; no raw full HTML source is injected with `v-html`.
- [x] LAN services verified:
  - Backend: `0.0.0.0:8000`, PID `20764`, `http://10.108.80.128:8000/api/v1/tracking/config` returned `200 OK`.
  - Frontend: `0.0.0.0:3000`, Vite node PID `7728` (`.lan-frontend.pid` launcher PID `22144`), `http://10.108.80.128:3000/` returned `200 OK`.
- [x] Automated verification completed:
  - Backend: `python -m pytest backend/tests/test_html_diff.py backend/tests/test_diff_result_schema.py backend/tests/test_diff_service.py -q` -> `15 passed in 6.26s`.
  - Frontend: `npm.cmd run test -- src/components/diff/__tests__/HtmlDiffView.spec.js src/views/admin/__tests__/DiffView.spec.js --run` -> `2 passed` test files, `3 passed` tests.
  - Build: `npm.cmd run build` -> Vite build succeeded, `1817 modules transformed`, `built in 5.02s`; only existing Rollup `/* #__PURE__ */` annotation warning from `@vueuse/core`.
- [x] Remaining optional improvements recorded:
  - This is semantic HTML diff, not screenshot/pixel diff.
  - Future enhancement candidates: visual screenshot diff, computed CSS/style diff, and richer move matching for heavily reordered nested layouts.
