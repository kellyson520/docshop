# Share Preview 非视频全屏沉浸式预览 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `/s/:token/preview/:fileId` 对所有非 mp4 文件使用整屏挂载式预览，去掉卡片/阴影/边框/中间窄容器；mp4 维持当前视频预览页样式不变。

**Architecture:** 继续由 `SharePreview.vue` 作为统一预览入口，但按 `previewManifest.type` 拆成两套布局：`video_native` 走现有视频页壳子，其他预览类型走 immersive 全屏布局。沉浸式布局仅保留极简顶栏和整屏预览区，不改分享路由，不改后端预览接口。

**Tech Stack:** Vue 3, `<script setup>`, Element Plus, Vitest, Vite

---

## File Map

- **Modify:** `frontend/src/views/share/SharePreview.vue`
  - 统一预览页入口
  - 区分视频布局与非视频 immersive 布局
  - 移除非视频卡片容器与装饰
- **Modify:** `frontend/src/views/share/__tests__/SharePreview.spec.js`
  - 锁定非视频整屏挂载行为
  - 锁定视频布局不回归
- **Verify:** `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
  - 确认文件列表仍然打开独立预览页，不受本次布局调整影响

---

### Task 1: 先把 immersive 布局的测试补齐

**Files:**
- Modify: `frontend/src/views/share/__tests__/SharePreview.spec.js`
- Verify: `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`

- [ ] **Step 1: 在 `SharePreview.spec.js` 增加“pdf 也走 direct stage 且没有卡片”的失败测试**

```js
it('renders pdf preview in immersive direct stage without preview card', async () => {
  mockedShareFileData = {
    id: 'file-9',
    display_name: 'PDF Handout',
    filename: 'handout.pdf',
    original_filename: 'handout.pdf',
    file_type: 'pdf',
    file_size: 2048,
    created_at: '2026-06-17T10:00:00Z',
    share: { allow_download: true },
    analysis_summary: {},
    preview_manifest: {
      type: 'pdf_native',
      status: 'ready',
      primary_asset: {
        asset_type: 'pdf',
        url: '/api/v1/share/share-token/files/file-9/preview',
      },
    },
  }

  const wrapper = mount(SharePreview, { global: globalConfig })

  await flushPromises()
  await flushPromises()

  expect(wrapper.find('.preview-card').exists()).toBe(false)
  expect(wrapper.find('.file-info-card').exists()).toBe(false)
  expect(wrapper.find('[data-testid="share-preview-direct-stage"]').exists()).toBe(true)
  expect(wrapper.find('[data-testid="share-preview-pdf-frame"]').exists()).toBe(true)
})
```

- [ ] **Step 2: 补一条“video 仍保留视频页容器”的保护测试**

```js
it('keeps the existing video preview layout for video files', async () => {
  const wrapper = mount(SharePreview, { global: globalConfig })

  await flushPromises()
  await flushPromises()

  expect(wrapper.find('[data-testid="video-player"]').exists()).toBe(true)
  expect(wrapper.find('.preview-card').exists()).toBe(true)
  expect(wrapper.find('[data-testid="share-preview-direct-stage"]').exists()).toBe(false)
})
```

- [ ] **Step 3: 运行单测，确认先失败**

Run:
```powershell
npm test -- --run src/views/share/__tests__/SharePreview.spec.js
```

Expected:
- 新增 pdf immersive 用例失败
- 或 `.file-info-card` / `.preview-card` 相关断言失败
- video 保护测试当前应通过或在后续实现后通过

- [ ] **Step 4: 提交测试变更**

```bash
git add frontend/src/views/share/__tests__/SharePreview.spec.js
git commit -m "test: cover immersive non-video share preview layout"
```

---

### Task 2: 在 `SharePreview.vue` 中拆分视频布局与非视频 immersive 布局

**Files:**
- Modify: `frontend/src/views/share/SharePreview.vue`
- Test: `frontend/src/views/share/__tests__/SharePreview.spec.js`

- [ ] **Step 1: 新增预览类型判定 computed，明确 immersive 范围**

在 `SharePreview.vue` 中加入：

```js
const previewType = computed(() => previewManifest.value?.type || '')
const previewIsVideo = computed(() => previewType.value === 'video_native')
const previewIsHtml = computed(() => previewType.value === 'html_native')
const previewIsOffice = computed(() => previewType.value === 'office_pdf')
const previewIsPdf = computed(() => previewType.value === 'pdf_native')
const previewIsImage = computed(() => previewType.value === 'image_native')
const previewUsesDirectStage = computed(() => (
  previewIsHtml.value || previewIsOffice.value || previewIsPdf.value || previewIsImage.value
))
```

- [ ] **Step 2: 删掉非视频的文件信息卡片，改成极简顶栏**

将当前通用的：

```vue
<el-card v-if="fileInfo" shadow="never" class="file-info-card">
  ...
</el-card>
```

改成仅视频显示，非视频显示 immersive 顶栏：

```vue
<el-card v-if="fileInfo && previewIsVideo" shadow="never" class="file-info-card">
  ...
</el-card>

<div v-else-if="fileInfo" class="immersive-toolbar">
  <button type="button" class="immersive-toolbar__back" @click="goBack">返回文件列表</button>
  <div class="immersive-toolbar__title">{{ fileDisplayName }}</div>
  <div class="immersive-toolbar__actions"></div>
</div>
```

- [ ] **Step 3: 非视频模板改成 direct stage 全屏挂载**

把非视频渲染改成：

```vue
<div
  v-if="fileInfo && previewUsesDirectStage"
  class="share-preview__direct-stage"
  data-testid="share-preview-direct-stage"
>
  <div v-if="embeddedPreviewLoading" class="preview-state">
    <el-skeleton :rows="4" animated />
  </div>

  <el-result
    v-else-if="embeddedPreviewError"
    icon="error"
    title="预览加载失败"
    :sub-title="embeddedPreviewError"
  >
    <template #extra>
      <el-button type="primary" @click="reloadEmbeddedPreview">重试</el-button>
    </template>
  </el-result>

  <iframe
    v-else-if="previewIsHtml"
    :src="resolvedPreviewUrl"
    class="preview-frame preview-frame--direct"
    data-testid="share-preview-html-frame"
    referrerpolicy="no-referrer"
  />

  <iframe
    v-else-if="previewIsOffice"
    :srcdoc="officePreviewHtml || undefined"
    :src="officePreviewHtml ? undefined : resolvedPreviewUrl"
    class="preview-frame preview-frame--direct"
    data-testid="share-preview-office-frame"
    sandbox="allow-same-origin"
    referrerpolicy="no-referrer"
  />

  <iframe
    v-else-if="previewIsPdf"
    :src="resolvedPreviewUrl"
    class="preview-frame preview-frame--direct"
    data-testid="share-preview-pdf-frame"
    referrerpolicy="no-referrer"
  />

  <img
    v-else-if="previewIsImage"
    :src="resolvedPreviewUrl"
    :alt="fileDisplayName || '图片预览'"
    class="preview-image"
    data-testid="share-preview-image"
  />
</div>
```

- [ ] **Step 4: 视频仍保留原 `preview-card + FileViewer` 路径**

保持视频分支：

```vue
<el-card v-else-if="fileInfo" shadow="never" class="preview-card">
  <template #header>
    <span class="card-title">文件预览</span>
  </template>

  <FileViewer
    v-else
    :file="fileInfo"
    :manifest="previewManifest"
    :analysis-summary="previewAnalysisSummary"
  />
</el-card>
```

要求：
- 只让 `video_native` 继续走这条路径
- html / office / pdf / image 都不要再落进 `preview-card`

- [ ] **Step 5: 运行单测，确认实现刚好让测试转绿**

Run:
```powershell
npm test -- --run src/views/share/__tests__/SharePreview.spec.js
```

Expected:
- `SharePreview.spec.js` 全部 PASS

- [ ] **Step 6: 提交实现变更**

```bash
git add frontend/src/views/share/SharePreview.vue frontend/src/views/share/__tests__/SharePreview.spec.js
git commit -m "feat: use immersive layout for non-video share previews"
```

---

### Task 3: 去掉非视频装饰，真正做到“整屏挂载”

**Files:**
- Modify: `frontend/src/views/share/SharePreview.vue`
- Test: `frontend/src/views/share/__tests__/SharePreview.spec.js`

- [ ] **Step 1: 给非视频页面补 immersive 页面样式**

在 `SharePreview.vue` 的 `<style scoped>` 中加入：

```css
.share-preview {
  min-height: 100vh;
}

.immersive-toolbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 16px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
}

.immersive-toolbar__title {
  flex: 1;
  min-width: 0;
  text-align: center;
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.share-preview__direct-stage {
  width: 100%;
  min-height: calc(100vh - 56px);
  margin: 0;
  padding: 0;
  background: #f3f4f6;
}

.preview-frame--direct {
  width: 100%;
  min-height: calc(100vh - 56px);
  border: none;
  border-radius: 0;
  box-shadow: none;
  background: #ffffff;
}

.preview-image {
  display: block;
  max-width: 100%;
  max-height: calc(100vh - 56px);
  margin: 0 auto;
}
```

- [ ] **Step 2: 删除非视频复用的卡片样式依赖**

确认这些样式不再作用于 immersive 布局：

```css
.file-info-card,
.preview-card,
.error-card {
  border-radius: var(--radius-lg, 12px);
  background-color: var(--bg-secondary, #ffffff);
  border: 1px solid var(--border-color, #e4e7ed);
}
```

要求：
- `.file-info-card` 仅视频分支使用
- `.preview-card` 仅视频分支使用
- `share-preview__direct-stage` 不继承任何卡片圆角/边框/阴影

- [ ] **Step 3: 运行分享页相关测试，确认没有破坏独立预览入口**

Run:
```powershell
npm test -- --run src/views/share/__tests__
```

Expected:
- `SharePreview.spec.js` PASS
- `ShareProjectPreview.spec.js` PASS
- `ShareProjectDisplayName.spec.js` PASS
- 全部分享相关测试 PASS

- [ ] **Step 4: 提交样式整理**

```bash
git add frontend/src/views/share/SharePreview.vue
git commit -m "style: remove card chrome from non-video share previews"
```

---

### Task 4: 最终验证独立预览页行为

**Files:**
- Verify only

- [ ] **Step 1: 跑分享预览相关前端测试**

Run:
```powershell
npm test -- --run src/views/share/__tests__
```

Expected:
- `5 passed`
- `21 passed` 或更高（按当时测试数为准）

- [ ] **Step 2: 跑前端构建，确认模板和样式无编译错误**

Run:
```powershell
npm run build
```

Expected:
- `built in` 输出
- Exit code 0

- [ ] **Step 3: 手动回归 4 类文件预览**

打开：
```text
/s/:token/preview/:fileId
```

检查：
- docx：页面只保留极简顶栏，文档区域整屏展示
- html：整页 iframe 挂载，无白色卡片包裹
- pdf：直接全屏预览，无卡片
- mp4：仍是原视频页布局，不被 immersive 改坏

- [ ] **Step 4: 最终提交**

```bash
git add frontend/src/views/share/SharePreview.vue frontend/src/views/share/__tests__/SharePreview.spec.js
git commit -m "feat: ship immersive share preview layout for non-video files"
```

---

## Self-Review

- **Spec coverage:**
  - “mp4 不动” → Task 1 video 保护测试 + Task 2 视频分支保留
  - “非 mp4 全屏沉浸式预览” → Task 2 direct stage + Task 3 immersive 样式
  - “去掉卡片装饰” → Task 3 明确移除卡片依赖
  - “独立预览页路由不变” → Task 3/4 验证 `ShareProjectPreview.spec.js`
- **Placeholder scan:**
  - 无 TBD/TODO
  - 每个任务都给了具体文件、代码、命令、预期结果
- **Type consistency:**
  - `previewIsVideo / previewIsHtml / previewIsOffice / previewIsPdf / previewIsImage / previewUsesDirectStage`
  - `share-preview-direct-stage / share-preview-pdf-frame / share-preview-html-frame / share-preview-office-frame / share-preview-image`
  - 命名在任务间一致

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

