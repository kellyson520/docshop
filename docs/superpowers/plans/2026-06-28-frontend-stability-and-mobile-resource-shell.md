# Frontend Stability And Mobile Resource Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 淇褰撳墠宸茬‘璁ょ殑 2 涓墠绔洖褰掑け璐ワ紝骞跺畬鎴?share/admin 璧勬簮鍖虹Щ鍔ㄧ澶栧３鐨勬渶鍚庝竴杞€滃幓妯悜鍙虫粦渚濊禆鈥濇敹鍙ｃ€?
**Architecture:** 淇濇寔鐜版湁鍚庣鎺ュ彛銆乣resourceItems` 缁熶竴璧勬簮妯″瀷鍜?`FileListCards` 鍗＄墖浣撶郴涓嶅彉锛屽彧鍋氬墠绔ǔ瀹氭€т笌浣撻獙鏀跺彛銆傜涓€闃舵缁熶竴 `ShareProject.vue` 鐨勫叧闂笅杞芥枃妗堝苟鍘绘帀 UTF-8 BOM锛岀浜岄樁娈垫妸杩囨湡鐨勫墠绔洖褰掓柇瑷€鍚屾鍒板綋鍓?`resource-toolbar + resourceItems` 濂戠害锛岀涓夐樁娈电Щ闄?share/admin 璧勬簮 breadcrumb 鍦ㄦ墜鏈虹鐨?`overflow-x: auto` 渚濊禆骞舵敹绱ф寜閽爡鏍笺€?
**Tech Stack:** Vue 3, Element Plus, Vitest, Vite, Node `fs` source guards.

---

## Confirmed Baseline (2026-06-28)

- `npm --prefix frontend test -- run src/utils/__tests__/frontend-regressions.spec.js` 褰撳墠 **44 椤归噷 2 椤瑰け璐?*銆?- 澶辫触 1锛歚production UI copy does not leak mojibake placeholders`
  - 褰撳墠 `frontend/src/views/share/ShareProject.vue` 鐪熷疄鏂囨涓?`褰撳墠鍒嗕韩鏈紑鏀句笅杞絗 + `绂佹涓嬭浇`
  - 鍘熷洖褰掕繕鍦ㄦ鏌ユ棫瀛楃涓?  - 鏂囦欢鍚屾椂甯︽湁 **UTF-8 BOM**
- 澶辫触 2锛歚ProjectDetail supports project folders and moving files without changing file table behavior`
  - 褰撳墠瀹炵幇宸茬粡鏄?`resource-toolbar + resourceItems + resource-folder-item-*`
  - 鍘熷洖褰掍粛鍦ㄦ鏌ュ凡鍒犻櫎鐨?`folder-toolbar / folder-grid / folder-card`
- 棰濆宸茬‘璁ょ殑浣撻獙閬楃暀锛?  - `ShareProject.vue` 涓?`ProjectDetail.vue` 鐨勬墜鏈虹 `resource-breadcrumb` 浠嶅湪 media block 涓娇鐢?`overflow-x: auto`
  - 杩欎細璁╄祫婧愬尯 breadcrumb/鏍圭洰褰曞垏鎹㈢户缁繚鐣欌€滈渶瑕佹í鍚戞粦鍔ㄢ€濈殑娈嬩綑浜や簰

---

## File Structure

### Frontend files

- Modify: `frontend/src/views/share/ShareProject.vue`
  - 缁熶竴鍏抽棴涓嬭浇鏂囨
  - 鍘绘帀 UTF-8 BOM
  - 璋冩暣鎵嬫満绔祫婧?breadcrumb 涓烘崲琛屽竷灞€
- Modify: `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
  - 閿佸畾鍏抽棴涓嬭浇 warning 琛屼负
  - 閿佸畾 share 璧勬簮鍖烘墜鏈虹涓嶅啀渚濊禆妯悜婊氬姩
- Modify: `frontend/src/views/admin/ProjectDetail.vue`
  - 璋冩暣鎵嬫満绔祫婧?breadcrumb 涓烘崲琛屽竷灞€
- Modify: `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`
  - 閿佸畾 admin 璧勬簮鍖烘墜鏈虹涓嶅啀渚濊禆妯悜婊氬姩
- Modify: `frontend/src/components/file/FileListCards.vue`
  - 浼樺寲鎵嬫満绔姩浣滃尯鏍呮牸锛岄伩鍏嶇獎灞忔寜閽户缁尋鍘?- Modify: `frontend/src/utils/__tests__/frontend-regressions.spec.js`
  - 鎶婅繃鏈熷洖褰掑悓姝ュ埌褰撳墠 canonical copy 涓庣粺涓€璧勬簮鍖哄疄鐜?
### Verification-only files

- Verify: `frontend/src/views/share/__tests__/ShareProjectDisplayName.spec.js`
- Verify: `frontend/src/views/share/__tests__/SharePreview.spec.js`

---

### Task 1: Canonical ShareProject copy cleanup and UTF-8/BOM normalization

**Files:**
- Modify: `frontend/src/views/share/ShareProject.vue`
- Modify: `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
- Modify: `frontend/src/utils/__tests__/frontend-regressions.spec.js`

- [ ] **Step 1: Write the failing regression + runtime tests**

```javascript
// frontend/src/utils/__tests__/frontend-regressions.spec.js
it('ShareProject source keeps canonical closed-download copy without UTF-8 BOM', () => {
  const source = readSource('src/views/share/ShareProject.vue')

  expect(source.charCodeAt(0)).not.toBe(0xfeff)
  expect(source).toContain('褰撳墠鍒嗕韩鏈紑鏀句笅杞?)
  expect(source).toContain('绂佹涓嬭浇')
})
```

```javascript
// frontend/src/views/share/__tests__/ShareProjectPreview.spec.js
const mocks = vi.hoisted(() => ({
  routerPush: vi.fn(),
  downloadViaIframe: vi.fn(),
  messageWarning: vi.fn(),
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    warning: mocks.messageWarning,
  },
}))

it('blocks folder download with the canonical warning copy when download is disabled', async () => {
  shareApiMocks.getShareProject.mockResolvedValueOnce({
    project: { name: 'Shared Project', description: '' },
    share: { allow_download: false },
    folders: [{ id: 'folder-1', name: 'Contracts' }],
    files: [
      {
        id: 'file-1',
        display_name: 'Read Only PDF',
        original_filename: 'readonly.pdf',
        filename: 'readonly.pdf',
        folder_id: '',
        file_type: 'pdf',
        current_version: 1,
        updated_at: '2026-06-28T10:00:00Z',
        download_formats: ['pdf'],
        versions: [{ id: 'version-1' }],
      },
    ],
  })

  const wrapper = mount(ShareProject, { global: globalConfig })
  await flushPromises()
  await flushPromises()

  expect(wrapper.text()).toContain('绂佹涓嬭浇')

  const vm = wrapper.vm.$?.setupState
  expect(typeof vm.downloadFolderBundle).toBe('function')

  vm.downloadFolderBundle({ id: 'folder-1', name: 'Contracts' })

  expect(mocks.messageWarning).toHaveBeenCalledWith('褰撳墠鍒嗕韩鏈紑鏀句笅杞?)
  expect(mocks.downloadViaIframe).not.toHaveBeenCalled()
})
```

- [ ] **Step 2: Run the tests to confirm the current state fails**

Run:

```powershell
npm --prefix frontend test -- run src/utils/__tests__/frontend-regressions.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js
```

Expected:
- `ShareProject source keeps canonical closed-download copy without UTF-8 BOM` FAIL because `ShareProject.vue` still contains BOM
- the existing stale copy assertion in `frontend-regressions.spec.js` is still red before Task 1 implementation finishes

- [ ] **Step 3: Implement canonical copy constants and remove BOM**

```vue
<!-- frontend/src/views/share/ShareProject.vue -->
<script setup>
const CLOSED_DOWNLOAD_COPY = '褰撳墠鍒嗕韩鏈紑鏀句笅杞?
const CLOSED_DOWNLOAD_BUTTON_COPY = '绂佹涓嬭浇'

function downloadFolderBundle(folder) {
  if (!folder?.id) return
  if (!allowDownload.value) {
    ElMessage.warning(CLOSED_DOWNLOAD_COPY)
    return
  }
  downloadViaIframe(`/api/v1/share/${token}/folders/${folder.id}/download`)
}
</script>
```

```vue
<!-- frontend/src/views/share/ShareProject.vue -->
<el-tooltip v-else :content="CLOSED_DOWNLOAD_COPY" placement="top">
  <el-button text disabled size="small" class="action-btn">
    <el-icon><Download /></el-icon> {{ CLOSED_DOWNLOAD_BUTTON_COPY }}
  </el-button>
</el-tooltip>
```

```powershell
$path = 'C:\Users\lihuo\Desktop\docshop\frontend\src\views\share\ShareProject.vue'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$content = [System.IO.File]::ReadAllText($path)
[System.IO.File]::WriteAllText($path, $content, $utf8NoBom)
```

- [ ] **Step 4: Re-run the focused tests**

Run:

```powershell
npm --prefix frontend test -- run src/utils/__tests__/frontend-regressions.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js
```

Expected:
- the BOM/canonical-copy guard PASS
- the `ShareProjectPreview.spec.js` warning behavior PASS
- `frontend-regressions.spec.js` should now only keep the legacy ProjectDetail resource-contract failure until Task 2

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/share/ShareProject.vue frontend/src/views/share/__tests__/ShareProjectPreview.spec.js frontend/src/utils/__tests__/frontend-regressions.spec.js
git commit -m "fix: normalize share project copy and utf8 encoding"
```

---

### Task 2: Align stale resource-area regression guards to the shipped unified resource model

**Files:**
- Modify: `frontend/src/utils/__tests__/frontend-regressions.spec.js`

- [ ] **Step 1: Replace the stale legacy assertions with the current `resourceItems` contract**

```javascript
// frontend/src/utils/__tests__/frontend-regressions.spec.js
it('ProjectDetail keeps folders inside the unified resource area and avoids legacy folder grids', () => {
  const viewSource = readSource('src/views/admin/ProjectDetail.vue')
  const apiSource = readSource('src/api/project.js')

  expect(apiSource).toContain('getProjectFolders')
  expect(apiSource).toContain('createProjectFolder')
  expect(apiSource).toContain('renameProjectFolder')
  expect(apiSource).toContain('deleteProjectFolder')
  expect(apiSource).toContain('moveProjectFileToFolder')

  expect(viewSource).toContain('resource-toolbar')
  expect(viewSource).toContain(':data="resourceItems"')
  expect(viewSource).toContain('currentFolderId')
  expect(viewSource).toContain('filteredFiles')
  expect(viewSource).toContain('openMoveFileDialog')
  expect(viewSource).toContain('moveFileDialogVisible')
  expect(viewSource).toContain('resource-folder-item-${row.resourceId}')
  expect(viewSource).toContain('resource-folder-item-${item.resourceId}')
  expect(viewSource).toContain('openFolder(row.resourceId)')
  expect(viewSource).not.toContain('folder-toolbar')
  expect(viewSource).not.toContain('folder-grid')
  expect(viewSource).not.toContain('folder-card')
})
```

- [ ] **Step 2: Run the regression file to confirm the stale failure is gone**

Run:

```powershell
npm --prefix frontend test -- run src/utils/__tests__/frontend-regressions.spec.js
```

Expected:
- the previous `ProjectDetail supports project folders...` failure disappears
- if Task 1 is already complete, the whole `frontend-regressions.spec.js` file should be green

- [ ] **Step 3: Minimal implementation is test-only for this task**

```text
No production Vue code should change here.
This task only updates stale regression expectations from the removed
folder-toolbar/folder-grid/folder-card contract to the shipped
resource-toolbar/resourceItems/resource-folder-item-* contract.
```

- [ ] **Step 4: Re-run the same regression guard to verify it stays green**

Run:

```powershell
npm --prefix frontend test -- run src/utils/__tests__/frontend-regressions.spec.js
```

Expected:
- PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/__tests__/frontend-regressions.spec.js
git commit -m "test: sync resource area regression guards to unified model"
```

---

### Task 3: Remove the remaining mobile horizontal-swipe dependency from share/admin resource breadcrumbs

**Files:**
- Modify: `frontend/src/views/share/ShareProject.vue`
- Modify: `frontend/src/views/admin/ProjectDetail.vue`
- Modify: `frontend/src/components/file/FileListCards.vue`
- Modify: `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
- Modify: `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`

- [ ] **Step 1: Add source-guard tests for wrapped mobile resource controls**

```javascript
// frontend/src/views/share/__tests__/ShareProjectPreview.spec.js
it('wraps share mobile resource controls instead of forcing horizontal breadcrumb scrolling', async () => {
  const fs = await import('node:fs')
  const path = await import('node:path')
  const source = fs.readFileSync(path.resolve(__dirname, '../ShareProject.vue'), 'utf-8')
  const mobileStart = source.indexOf('@media (max-width: 767px)')
  const mobileBlock = source.slice(mobileStart)

  expect(mobileBlock).toContain('.resource-breadcrumb')
  expect(mobileBlock).toContain('flex-wrap: wrap;')
  expect(mobileBlock).toContain('white-space: normal;')
  expect(mobileBlock).not.toContain('overflow-x: auto;')
})
```

```javascript
// frontend/src/views/admin/__tests__/ProjectDetail.spec.js
it('wraps admin mobile resource controls instead of forcing horizontal breadcrumb scrolling', async () => {
  const fs = await import('node:fs')
  const path = await import('node:path')
  const source = fs.readFileSync(path.resolve(__dirname, '../ProjectDetail.vue'), 'utf-8')
  const mobileStart = source.indexOf('@media (max-width: 768px)')
  const mobileBlock = source.slice(mobileStart)

  expect(mobileBlock).toContain('.resource-breadcrumb')
  expect(mobileBlock).toContain('flex-wrap: wrap;')
  expect(mobileBlock).toContain('white-space: normal;')
  expect(mobileBlock).not.toContain('overflow-x: auto;')
})
```

```javascript
// frontend/src/views/admin/__tests__/ProjectDetail.spec.js
it('uses an auto-fit mobile action grid for resource cards instead of a rigid two-column clamp', async () => {
  const fs = await import('node:fs')
  const path = await import('node:path')
  const source = fs.readFileSync(
    path.resolve(__dirname, '../../../components/file/FileListCards.vue'),
    'utf-8',
  )

  expect(source).toContain('repeat(auto-fit, minmax(132px, 1fr))')
  expect(source).toContain('white-space: normal;')
})
```

- [ ] **Step 2: Run the targeted mobile-shell tests to verify they fail first**

Run:

```powershell
npm --prefix frontend test -- run src/views/share/__tests__/ShareProjectPreview.spec.js src/views/admin/__tests__/ProjectDetail.spec.js
```

Expected:
- the new mobile-wrap assertions FAIL because both views still contain `overflow-x: auto`
- the FileListCards rigid `repeat(2, minmax(0, 1fr))` assertion also FAIL

- [ ] **Step 3: Implement wrapped breadcrumb and denser action-grid styles**

```vue
<!-- frontend/src/views/share/ShareProject.vue -->
@media (max-width: 767px) {
  .resource-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .resource-breadcrumb {
    width: 100%;
    overflow: visible;
    flex-wrap: wrap;
    row-gap: 8px;
    white-space: normal;
  }

  .folder-root-btn,
  .folder-current-name {
    max-width: 100%;
  }

  .folder-current-name {
    flex: 1 1 100%;
    white-space: normal;
    word-break: break-word;
  }
}
```

```vue
<!-- frontend/src/views/admin/ProjectDetail.vue -->
@media (max-width: 768px) {
  .resource-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .resource-breadcrumb {
    width: 100%;
    overflow: visible;
    flex-wrap: wrap;
    row-gap: 8px;
    white-space: normal;
  }

  .folder-current-name {
    flex: 1 1 100%;
    white-space: normal;
    word-break: break-word;
  }
}
```

```vue
<!-- frontend/src/components/file/FileListCards.vue -->
@media (max-width: 767px) {
  .file-list-card__actions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
    align-items: stretch;
  }

  .file-list-card__actions :deep(.el-button),
  .file-list-card__actions :deep(.el-dropdown),
  .file-list-card__actions :deep(.el-dropdown .el-button) {
    width: 100%;
    white-space: normal;
  }
}
```

- [ ] **Step 4: Re-run the mobile-shell tests**

Run:

```powershell
npm --prefix frontend test -- run src/views/share/__tests__/ShareProjectPreview.spec.js src/views/admin/__tests__/ProjectDetail.spec.js
```

Expected:
- PASS
- no more source guards expecting horizontal breadcrumb scroll

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/share/ShareProject.vue frontend/src/views/admin/ProjectDetail.vue frontend/src/components/file/FileListCards.vue frontend/src/views/share/__tests__/ShareProjectPreview.spec.js frontend/src/views/admin/__tests__/ProjectDetail.spec.js
git commit -m "style: wrap mobile resource shells and tighten card actions"
```

---

### Task 4: Final verification sweep

**Files:**
- Verify only

- [ ] **Step 1: Run the frontend regression + share/admin targeted suites**

Run:

```powershell
npm --prefix frontend test -- run src/utils/__tests__/frontend-regressions.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/ShareProjectDisplayName.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/share/__tests__/SharePreview.spec.js
```

Expected:
- all selected tests PASS

- [ ] **Step 2: Run the frontend production build**

Run:

```powershell
npm --prefix frontend run build
```

Expected:
- build succeeds with exit code 0

- [ ] **Step 3: Sanity-check the shipped behaviors manually**

```text
1. ShareProject 妗岄潰绔細
   - 涓嬭浇鍏抽棴鏃舵寜閽粛鏄剧ず鈥滅姝笅杞解€?   - 鐐瑰嚮鏂囦欢澶逛笅杞藉彧寮?warning锛屼笉鍙戣捣 iframe 涓嬭浇

2. ShareProject 鎵嬫満绔細
   - 璧勬簮 breadcrumb/root 鎸夐挳鎹㈣鏄剧ず
   - 涓嶉渶瑕佹í鍚戝彸婊戞墠鑳界湅鍒板綋鍓嶇洰褰曞拰璧勬簮璁℃暟

3. ProjectDetail 鎵嬫満绔細
   - 鏂囦欢澶逛笌鏂囦欢缁х画鍦ㄥ悓涓€璧勬簮鍖?   - breadcrumb/root/褰撳墠鐩綍鍙嚜鐒舵崲琛?   - 璧勬簮鍗＄墖鍔ㄤ綔鎸夐挳涓嶄細琚?rigid 涓ゅ垪鎸ゅ帇
```

- [ ] **Step 4: Commit the verification checkpoint**

```bash
git add frontend/src/utils/__tests__/frontend-regressions.spec.js frontend/src/views/share/__tests__/ShareProjectPreview.spec.js frontend/src/views/admin/__tests__/ProjectDetail.spec.js frontend/src/components/file/FileListCards.vue frontend/src/views/share/ShareProject.vue frontend/src/views/admin/ProjectDetail.vue
git commit -m "test: verify frontend stability and mobile resource shell polish"
```

---

## Deferred Follow-Up (separate plan recommended)

The following items are intentionally **not** folded into this plan because they are a different subsystem from the current frontend stabilization pass:

- Tracking / `visitor_ip_context` cache TTL and graceful fallback copy
- Private/LAN visitor-IP labeling in tracking detail cards
- IP enrichment retry/refresh controls in the admin tracking dialog

If needed, create a separate tracking-focused plan instead of widening this frontend stabilization plan.

---

## Self-Review

- **Spec coverage:**  
  - 宸茬‘璁ょ殑 2 涓墠绔洖褰掑け璐ワ細Task 1 + Task 2  
  - 绉诲姩绔祫婧愬尯鈥滀笉瑕佸啀闈犳í鍚戝彸婊戔€濓細Task 3  
  - 鏈€缁堝洖褰掍笌鏋勫缓楠岃瘉锛歍ask 4

- **Placeholder scan:**  
  - 鏃?`TODO` / `TBD` / 鈥滃悗缁疄鐜扳€濆紡鍗犱綅  
  - 姣忎釜浠诲姟閮藉甫浜嗗叿浣撴枃浠躲€佹祴璇曚唬鐮併€佸懡浠ゅ拰棰勬湡缁撴灉

- **Type consistency:**  
  - 缁熶竴浣跨敤 `resourceItems / resource-toolbar / resource-breadcrumb / resource-folder-item-*`  
  - 缁熶竴浣跨敤 `褰撳墠鍒嗕韩鏈紑鏀句笅杞絗 浣滀负鍏抽棴涓嬭浇 canonical copy  
  - `FileListCards.vue` 鎵嬫満绔姩浣滄爡鏍肩粺涓€浣跨敤 `repeat(auto-fit, minmax(132px, 1fr))`

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

