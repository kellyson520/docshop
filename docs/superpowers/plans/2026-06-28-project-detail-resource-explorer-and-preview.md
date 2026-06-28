# Project Detail Resource Explorer And Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make admin project browsing behave like a Windows-style mixed folder/file explorer, keep folder open on single click, and restore a visible bold skeleton title while shrinking DOC/PDF preview presentation.

**Architecture:** Keep the current admin page as the orchestration layer, but switch the desktop table from file-only rows to mixed resource rows (`parent` / `folder` / `file`). Keep the preview dialog frontend-only for scaling/layout concerns, and restore the visible skeleton title at the HTML generator level in `conversion_service.py` so both inline image HTML and lazy page skeleton HTML share the same title contract.

**Tech Stack:** Vue 3, Element Plus, Vitest, Python, FastAPI preview conversion service, Pytest.

---

### Task 1: Lock preview skeleton title requirements with failing backend tests

**Files:**
- Modify: `backend/tests/test_preview_performance.py`
- Modify: `backend/app/services/conversion_service.py` (next task)

- [ ] **Step 1: Write the failing test for inline image HTML title rendering**

Add this test near the existing `_build_images_html` assertions in `backend/tests/test_preview_performance.py`:

```python
def test_inline_images_html_keeps_visible_bold_centered_title(tmp_path):
    from app.services.conversion_service import _build_images_html

    image = tmp_path / "page_0001.jpg"
    image.write_bytes(b"jpg")

    html = _build_images_html("file-id", [str(image)], 1, title="汽车服务 - protable.docx · v3")

    assert '<div class="preview-shell">' in html
    assert '<h1 class="preview-title">汽车服务 - protable.docx · v3</h1>' in html
    assert '.preview-title{text-align:center;' in html
    assert 'font-weight:700' in html
    assert 'max-width:min(100%,980px)' in html
```

- [ ] **Step 2: Write the failing test for lazy skeleton HTML title rendering**

Add this test below the existing `build_skeleton_html` regression block in `backend/tests/test_preview_performance.py`:

```python
def test_skeleton_html_keeps_visible_bold_centered_title():
    from app.services.conversion_service import build_skeleton_html

    html = build_skeleton_html("file-id", 2, 2, title="汽车服务 - protable.docx · v3")

    assert '<div class="preview-shell">' in html
    assert '<h1 class="preview-title">汽车服务 - protable.docx · v3</h1>' in html
    assert '.preview-title{text-align:center;' in html
    assert 'font-weight:700' in html
    assert 'max-width:min(100%,980px)' in html
```

- [ ] **Step 3: Run the targeted backend tests to verify they fail**

Run from `C:\Users\lihuo\Desktop\docshop\backend`:

```powershell
python -m pytest tests/test_preview_performance.py -k "visible_bold_centered_title" -v
```

Expected: FAIL because current HTML only keeps `<title>` metadata and does not emit a visible `.preview-title` block or `.preview-shell` wrapper.

- [ ] **Step 4: Commit the failing tests**

```powershell
git -C C:\Users\lihuo\Desktop\docshop add -- backend/tests/test_preview_performance.py
git -C C:\Users\lihuo\Desktop\docshop commit -m "test: cover preview skeleton title shell"
```

### Task 2: Implement shared backend skeleton title shell for DOC/PDF preview HTML

**Files:**
- Modify: `backend/app/services/conversion_service.py` (around `_build_images_html`, `build_skeleton_html`)
- Test: `backend/tests/test_preview_performance.py`

- [ ] **Step 1: Add the shared shell/title markup to `_build_images_html`**

Update `_build_images_html` so the returned HTML body wraps page markup like this:

```python
css = (
    "html,body{margin:0;padding:0;background:#f5f7fb;"
    "font-family:\"Microsoft YaHei\",\"SimSun\",sans-serif;color:#111}"
    ".preview-shell{max-width:min(100%,980px);margin:0 auto;padding:16px 0 28px}"
    ".preview-title{text-align:center;font-size:20px;line-height:1.35;font-weight:700;"
    "margin:0 0 18px;color:#111}"
    ".page{margin:0 0 12px 0;text-align:center;contain:layout style paint}"
    ".page img{display:block;max-width:100%;width:auto;height:auto;margin:0 auto}"
    ".page-num{color:#999;font-size:11px;padding:4px 0 10px}"
    "@media print{body{background:#fff}.preview-shell{max-width:none;padding:0}.page{page-break-after:always}}"
    "@media(max-width:640px){.preview-shell{padding:12px 0 20px}.preview-title{font-size:18px}.page{margin-bottom:10px}}"
)
return (
    '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    f'<title>{preview_title}</title><style>{css}</style></head>'
    f'<body><div class="preview-shell"><h1 class="preview-title">{preview_title}</h1>{"".join(img_tags)}</div></body></html>'
)
```

- [ ] **Step 2: Mirror the same shell/title contract in `build_skeleton_html`**

Update `build_skeleton_html` so the CSS and returned body use the same shell/title structure:

```python
css = (
    "html,body{margin:0;padding:0;background:#f5f7fb;"
    "font-family:\"Microsoft YaHei\",\"SimSun\",sans-serif;color:#111}"
    ".preview-shell{max-width:min(100%,980px);margin:0 auto;padding:16px 0 28px}"
    ".preview-title{text-align:center;font-size:20px;line-height:1.35;font-weight:700;"
    "margin:0 0 18px;color:#111}"
    ".page{margin:0 0 12px 0;text-align:center;min-height:auto;padding:0;display:block;background:transparent}"
    ".page img{display:block;max-width:100%;width:auto;height:auto;margin:0 auto}"
    ".page-num{color:#999;font-size:11px;padding:4px 0 10px}"
    ".page-loading{color:#aaa;font-size:13px}"
    "@media print{body{background:#fff}.preview-shell{max-width:none;padding:0}.page{page-break-after:always}}"
    "@media(max-width:640px){.preview-shell{padding:12px 0 20px}.preview-title{font-size:18px}.page{margin-bottom:10px}}"
)
return (
    '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    f'<title>{preview_title}</title><style>{css}</style></head>'
    f'<body><div class="preview-shell"><h1 class="preview-title">{preview_title}</h1>{"".join(pages)}</div></body></html>'
)
```

- [ ] **Step 3: Re-run the targeted backend tests to verify they pass**

Run from `C:\Users\lihuo\Desktop\docshop\backend`:

```powershell
python -m pytest tests/test_preview_performance.py -k "visible_bold_centered_title" -v
```

Expected: PASS for both new title-shell tests.

- [ ] **Step 4: Commit the backend preview fix**

```powershell
git -C C:\Users\lihuo\Desktop\docshop add -- backend/app/services/conversion_service.py backend/tests/test_preview_performance.py
git -C C:\Users\lihuo\Desktop\docshop commit -m "feat: restore preview skeleton title shell"
```

### Task 3: Lock desktop mixed-resource explorer behavior with failing frontend tests

**Files:**
- Modify: `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`
- Modify: `frontend/src/views/admin/ProjectDetail.vue` (next task)

- [ ] **Step 1: Add a source-contract test for the desktop table data source and row-click handler**

Append this test near the existing desktop layout/source assertions in `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`:

```javascript
it('binds the desktop table to mixed resource rows and removes the standalone folder grid', async () => {
  const fs = await import('node:fs')
  const path = await import('node:path')
  const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
  const source = fs.readFileSync(sourcePath, 'utf-8')

  expect(source).toContain(':data="resourceItems"')
  expect(source).toContain('@row-click="handleResourceRowClick"')
  expect(source).toContain('@click.stop="openFolder(row.resourceId)"')
  expect(source).not.toContain('class="resource-folder-list"')
})
```

- [ ] **Step 2: Add a runtime test for folder-first ordering and single-click open behavior**

Append this test below the existing mobile folder/resourceItems regression in `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`:

```javascript
it('keeps folders before files in resourceItems and opens folder rows with a single row click', async () => {
  mocks.getProject.mockResolvedValueOnce({
    id: 'project-1',
    name: 'Project One',
    description: 'desc',
    files: [
      {
        id: 'file-root',
        filename: 'root-file.pdf',
        original_filename: 'root-file.pdf',
        file_type: 'pdf',
        current_version: 1,
        updated_at: '2026-06-16T10:00:00Z',
        file_size: 1024,
        folder_id: '',
        tags: [],
      },
    ],
  })
  mocks.getProjectFolders.mockResolvedValueOnce({
    folders: [{ id: 'folder-a', name: '合同资料' }],
  })
  mocks.getPreviewStatuses.mockResolvedValueOnce({ files: [], summary: {} })

  const wrapper = mount(ProjectDetail, globalMountOptions)
  await flushPromises()

  const resourceItems = getExpose(wrapper, 'resourceItems')
  const normalizedItems = Array.isArray(resourceItems) ? resourceItems : (resourceItems?.value || [])
  expect(normalizedItems.map((item) => item.type)).toEqual(['folder', 'file'])

  const handleResourceRowClick = getExpose(wrapper, 'handleResourceRowClick')
  expect(typeof handleResourceRowClick).toBe('function')

  handleResourceRowClick(normalizedItems[0])
  await flushPromises()

  expect(mocks.routerReplace).toHaveBeenLastCalledWith({
    path: '/admin/projects/project-1',
    query: { folder_id: 'folder-a' },
    hash: '',
  })
})
```

- [ ] **Step 3: Add a source-contract test for the tighter preview dialog scale token**

Append this test near the existing preview style assertions in `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`:

```javascript
it('uses a reduced centered admin preview shell instead of the old oversized iframe fill', async () => {
  const fs = await import('node:fs')
  const path = await import('node:path')
  const sourcePath = path.resolve(__dirname, '../ProjectDetail.vue')
  const source = fs.readFileSync(sourcePath, 'utf-8')

  expect(source).toContain('--admin-preview-scale: 0.82;')
  expect(source).toContain('justify-content: center;')
  expect(source).toContain('background: #f5f7fb;')
})
```

- [ ] **Step 4: Run the targeted frontend tests to verify they fail**

Run from `C:\Users\lihuo\Desktop\docshop\frontend`:

```powershell
npx vitest run src/views/admin/__tests__/ProjectDetail.spec.js
```

Expected: FAIL because the desktop table still binds `filteredFiles`, the standalone folder grid still exists, there is no `handleResourceRowClick`, and the preview scale token is still `0.92`.

- [ ] **Step 5: Commit the failing frontend tests**

```powershell
git -C C:\Users\lihuo\Desktop\docshop add -- frontend/src/views/admin/__tests__/ProjectDetail.spec.js
git -C C:\Users\lihuo\Desktop\docshop commit -m "test: cover project detail mixed explorer"
```

### Task 4: Implement the mixed desktop explorer and tighter preview dialog layout

**Files:**
- Modify: `frontend/src/views/admin/ProjectDetail.vue`
- Test: `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`

- [ ] **Step 1: Replace root-only folder visibility with mixed resource rows**

In `frontend/src/views/admin/ProjectDetail.vue`, replace the old `visibleFolders` / `resourceItems` block with a mixed-row model like this:

```javascript
const visibleFolders = computed(() => {
  if (getFileSearchKeyword()) return []
  if (hasLocalFileFilters.value) return []
  return currentFolderId.value ? [] : folders.value
})

const parentResourceItem = computed(() => {
  if (!currentFolderId.value) return null
  return {
    id: 'parent-folder-row',
    resourceId: '',
    type: 'parent',
    name: '..',
  }
})

const resourceItems = computed(() => {
  const items = []
  if (parentResourceItem.value) items.push(parentResourceItem.value)
  items.push(
    ...visibleFolders.value.map((folder) => ({
      id: `folder-${folder.id}`,
      resourceId: folder.id,
      type: 'folder',
      name: folder.name || '未命名文件夹',
      fileCount: getFolderFileCount(folder.id),
      folder,
    })),
  )
  items.push(
    ...filteredFiles.value.map((file) => ({
      ...file,
      resourceId: file.id,
      type: 'file',
    })),
  )
  return items
})
```

- [ ] **Step 2: Add a single-click row handler and keep file-only actions isolated**

Add these helpers near `openFolder` / row behavior helpers:

```javascript
function isFolderResource(row) {
  return row?.type === 'folder'
}

function isParentResource(row) {
  return row?.type === 'parent'
}

function isFileResource(row) {
  return !row?.type || row.type === 'file'
}

function handleResourceRowClick(row) {
  if (isParentResource(row)) {
    openFolder('')
    return
  }
  if (isFolderResource(row)) {
    openFolder(row.resourceId || row.folder?.id || '')
  }
}
```

Keep `@click.stop` on folder/file action buttons and dropdown triggers so row click does not fire during rename/delete/share/preview actions.

- [ ] **Step 3: Rework the desktop table to consume `resourceItems` and branch per row type**

Update the desktop table template from:

```vue
<el-table
  :data="filteredFiles"
  stripe
  style="width: 100%"
  row-key="id"
  :row-class-name="tableRowClassName"
  @expand-change="onExpandChange"
  class="file-table"
>
```

To:

```vue
<el-table
  :data="resourceItems"
  stripe
  style="width: 100%"
  row-key="id"
  :row-class-name="tableRowClassName"
  @row-click="handleResourceRowClick"
  @expand-change="onExpandChange"
  class="file-table"
>
```

Then branch each desktop column:

```vue
<el-table-column type="expand">
  <template #default="{ row }">
    <div v-if="row.type === 'file'" class="version-expand" v-loading="row._loadingVersions">
      <!-- keep existing version list -->
    </div>
    <div v-else class="version-expand version-expand--empty">文件夹不提供版本历史</div>
  </template>
</el-table-column>

<el-table-column label="文件名" min-width="180">
  <template #default="{ row }">
    <div class="file-name-cell" :class="{ 'file-name-cell--folder': row.type === 'folder' || row.type === 'parent' }">
      <el-icon :size="20" :class="row.type === 'file' ? getFileTypeColor(row.file_type) : 'file-icon-folder'">
        <FolderOpened v-if="row.type === 'parent'" />
        <Folder v-else-if="row.type === 'folder'" />
        <component :is="getFileTypeIcon(row.file_type)" v-else />
      </el-icon>
      <div class="file-info">
        <span class="file-name">{{ row.type === 'file' ? getFileDisplayName(row) : row.name }}</span>
        <span class="file-path" v-if="row.type === 'file'">文件 ID：{{ shortFileId(row.id) }}</span>
        <span class="file-path" v-else-if="row.type === 'folder'">单击打开文件夹</span>
        <span class="file-path" v-else>返回根目录</span>
      </div>
    </div>
  </template>
</el-table-column>
```

Use the same pattern for type / preview / info / action columns:

```vue
<el-tag v-if="row.type === 'folder'" size="small" type="warning">文件夹</el-tag>
<el-tag v-else-if="row.type === 'parent'" size="small" type="info">上一级</el-tag>
<el-tag v-else size="small" :type="getFileTypeTagType(row.file_type)">{{ row.file_type?.toUpperCase() }}</el-tag>
```

```vue
<div v-if="row.type === 'file'" class="preview-status-cell">
  <!-- keep existing preview status block -->
</div>
<span v-else class="resource-cell-placeholder">—</span>
```

```vue
<div v-if="row.type === 'folder'" class="file-meta-cell">
  <span class="file-meta-main">{{ row.fileCount }} 个文件</span>
  <span class="file-meta-sub">单击进入文件夹</span>
</div>
<div v-else-if="row.type === 'parent'" class="file-meta-cell">
  <span class="file-meta-main">返回根目录</span>
  <span class="file-meta-sub">单击回到上一级</span>
</div>
<div v-else class="file-meta-cell">
  <!-- keep existing file metadata -->
</div>
```

```vue
<div v-if="row.type === 'folder'" class="action-buttons action-buttons-compact">
  <el-button text type="primary" size="small" @click.stop="openFolder(row.resourceId)">
    <el-icon><FolderOpened /></el-icon>
    打开
  </el-button>
  <el-dropdown trigger="click" @click.stop @command="(command) => handleFolderAction(command, row.folder)">
    <el-button text size="small" class="more-action-button" @click.stop>
      <el-icon><MoreFilled /></el-icon>
      更多
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="rename">重命名</el-dropdown-item>
        <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</div>
<div v-else-if="row.type === 'parent'" class="action-buttons action-buttons-compact">
  <el-button text type="primary" size="small" @click.stop="openFolder('')">
    <el-icon><FolderOpened /></el-icon>
    返回
  </el-button>
</div>
<div v-else class="action-buttons action-buttons-compact">
  <!-- keep existing file actions -->
</div>
```

Delete the old standalone desktop folder block entirely:

```vue
<div v-if="!isMobile && visibleFolders.length" class="resource-folder-list">
  ...
</div>
```

- [ ] **Step 4: Tighten preview dialog scaling and center the reading surface**

Replace the old preview container styles in `frontend/src/views/admin/ProjectDetail.vue` with this direction:

```css
.preview-container {
  --admin-preview-scale: 0.82;
  height: 70vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fb;
}

.preview-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.preview-body {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  padding: 0 8px 12px;
}

.preview-iframe-container {
  width: min(100%, 1040px);
  height: 100%;
  min-height: 500px;
  margin: 0 auto;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 8px;
  background: #fff;
  zoom: var(--admin-preview-scale);
  transform-origin: top center;
}
```

Remove now-unused `.resource-folder-list`, `.folder-card`, `.folder-card-main`, and `.folder-more-btn` desktop-only card styles.

- [ ] **Step 5: Run the targeted frontend tests to verify they pass**

Run from `C:\Users\lihuo\Desktop\docshop\frontend`:

```powershell
npx vitest run src/views/admin/__tests__/ProjectDetail.spec.js
```

Expected: PASS for the new resource explorer assertions plus existing mobile/preview regressions.

- [ ] **Step 6: Commit the frontend implementation**

```powershell
git -C C:\Users\lihuo\Desktop\docshop add -- frontend/src/views/admin/ProjectDetail.vue frontend/src/views/admin/__tests__/ProjectDetail.spec.js
git -C C:\Users\lihuo\Desktop\docshop commit -m "feat: unify project detail resource explorer"
```

### Task 5: Run focused cross-layer verification and prepare the HTML diff follow-up

**Files:**
- No new code files
- Verification only for the implemented explorer/preview work

- [ ] **Step 1: Run the combined targeted verification suite**

Run from `C:\Users\lihuo\Desktop\docshop`:

```powershell
python -m pytest backend/tests/test_preview_performance.py -k "visible_bold_centered_title" -v
cd frontend
npx vitest run src/views/admin/__tests__/ProjectDetail.spec.js
```

Expected: both commands PASS.

- [ ] **Step 2: Sanity-check the spec coverage before handoff**

Use this checklist against the finished code:

```text
- desktop folders are no longer rendered as standalone cards above the table
- desktop table consumes resourceItems instead of filteredFiles
- folders remain ahead of files
- folder rows open on single click
- row action buttons stop propagation
- DOC/PDF skeleton HTML includes a visible centered bold title
- preview dialog scale token is reduced from 0.92 to 0.82 and centered
```

Expected: every line can be pointed to in code or test coverage.

- [ ] **Step 3: Commit the final verification checkpoint**

```powershell
git -C C:\Users\lihuo\Desktop\docshop status --short
```

Expected: clean working tree except for any intentional follow-up docs.

- [ ] **Step 4: Start the separate HTML diff debugging pass only after this plan is complete**

Do **not** fold HTML diff changes into the same code commit chain. Open a new task sequence that begins with evidence gathering in the current diff flow.

Use these first commands from `C:\Users\lihuo\Desktop\docshop`:

```powershell
Select-String -Path frontend\src\views\admin\ProjectDetail.vue,frontend\src\views\admin\DiffView.vue,frontend\src\components\diff\*.vue -Pattern 'html|diff|preview|iframe' -Context 2,4
python -m pytest backend/tests -k html -v
cd frontend
npx vitest run src/views/admin/__tests__/DiffView.spec.js src/views/admin/__tests__/ProjectDetailHtmlPreview.spec.js
```

Expected: a reproducible root-cause starting point for the separate lightweight HTML diff repair.
