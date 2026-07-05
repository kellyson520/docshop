# Mobile UI Shell And Compatible Video Preview Design

## Goal

在保持桌面端交互基本稳定的前提下，完成两条并行增强：

1. 为分享页 / 后台资源区 / 预览页继续收口独立 mobile UI shell。
2. 为视频预览补上兼容移动端播放的 derived preview asset，解决“有画面但无声音”与不同端解码兼容性问题。

## Scope

### 本轮立即落地

- `backend/app/services/media_metadata_service.py`
- `backend/app/services/preview_queue.py`
- `backend/app/services/preview_manifest_service.py`
- `backend/app/routers/files.py`
- `backend/app/routers/share.py`
- `frontend/src/components/file-viewer/VideoViewer.vue`
- `frontend/src/components/file-viewer/__tests__/FileViewer.spec.js`
- `frontend/src/views/share/SharePreview.vue`
- `frontend/src/views/share/__tests__/SharePreview.spec.js`
- 与上述链路直接相关的 backend tests

### 后续同主题继续推进

- `frontend/src/views/share/ShareLayout.vue`
- `frontend/src/views/share/ShareProject.vue`
- `frontend/src/views/admin/ProjectDetail.vue`
- `frontend/src/components/file/FileListCards.vue`
- 后台弹窗 / 工具栏 / 资源区 mobile shell 收口

## Confirmed Decisions

1. **移动端采用独立 shell**：不新增业务路由，不拆业务逻辑，只在移动端切换壳层与交互模式。
2. **桌面端最小联动**：现有桌面布局尽量不重做。
3. **视频兼容链路采用 derived asset**：服务端新增兼容播放版本，目标格式为 `mp4 / H.264 / AAC`。
4. **HTML 预览维持当前决策**：继续使用原生独立页跳转，不回退 iframe。
5. **后台私有场景优先复用 `/preview` 路由**：避免直接把 Bearer 鉴权问题扩散到 `<video src="/preview-assets/...">`。

## Problem Summary

当前视频预览虽然已经有 `poster` 与原始 `video` 资产，但仍存在三个问题：

1. 原视频编码不稳定时，移动端浏览器 / WebView 可能只出画面不出声音。
2. 当前 manifest 只认 `video`，没有 `preview_video` 这类兼容预览资产的优先级表达。
3. 后台私有预览仍大量走 `/preview`，如果只让前端直连 `/preview-assets/{asset_id}`，会引入鉴权携带问题。

## Chosen Approach

采用“**兼容预览视频资产 + manifest 优先级升级 + `/preview` 路由兜底**”的方案。

### 方案拆分

#### Phase A：先修视频兼容预览链路

- preview worker 在视频任务中额外尝试生成 `preview_video`
- manifest 对视频优先返回 `preview_video`
- `/preview` 路由对视频优先回放 `preview_video`
- 前端视频组件接受 `preview_video`

#### Phase B：继续推进 mobile UI shell

- 复用现有 `resourceItems` / `FileListCards`
- 移动端改为独立壳层、底部动作区、轻量标题区、可折叠信息区
- 桌面端只保留必要联动样式与数据模型

本轮先执行 Phase A，因为它是当前最明确的功能缺口，且能直接修复移动端视频无声问题。

## Architecture

### 1. Derived Preview Asset Contract

视频 native preview worker 输出三类资产：

- `poster`
- `preview_video`
- `video`

其中：

- `preview_video` 是兼容播放版本，优先给预览使用
- `video` 继续表示原始 native 视频预览来源，保留给旧链路和兜底

如果 ffmpeg 不可用或转码失败：

- 不阻塞整条视频预览链路
- 继续保留 `video` + `poster`
- manifest 回退到旧行为

### 2. Manifest Contract

视频 manifest 约束如下：

- `primary_asset`：优先 `preview_video`，否则 `video`，再否则 `poster`
- `poster_asset`：保持不变
- `original_asset`：当存在原始 `video` 且主资产为 `preview_video` 时额外提供，便于后续下载/调试/显式切换

这样旧前端不会因字段缺失崩掉，新前端可以直接消费更适合播放的主资产。

### 3. Preview URL Strategy

不同资产 URL 规则如下：

- `poster` / `preview_video`：走 `/preview-assets/{asset_id}`
- `video` / `pdf` / `html`：继续保留 `/preview`

这样分享链路可以直接拿到安全的 share-token preview asset URL；后台私有链路则继续优先通过 `/preview` 访问，由服务端决定是否回放兼容视频资产。

### 4. `/preview` Route Fallback

`/api/v1/files/{file_id}/preview`
与
`/api/v1/share/{token}/files/{file_id}/preview`

在命中视频类别时：

1. 先查当前版本 `preview_video` 资产
2. 找到则直接流式返回该 mp4
3. 否则回退到原始 `video` 文件

这样后台弹窗、旧前端 fallback manifest、以及仍然依赖 `/preview` 的场景都能自动受益。

### 5. Frontend Consumption

前端只需要把视频主资产视为“可播放视频”即可，不再硬编码只能接受 `asset_type === "video"`。

具体表现：

- `VideoViewer` 接受 `video` 或 `preview_video`
- `SharePreview.vue` 的 renderable manifest 判断接受 `preview_video`
- fallback `buildPreviewManifest()` 仍可继续指向 `/preview`，因为后端已具备兼容视频兜底

## Mobile UI Shell Follow-Up Direction

视频兼容链路稳定后，移动端继续按以下方向收口：

1. **分享资源列表**：以卡片 / 分组条目 / 轻量筛选条为主。
2. **后台资源区**：与桌面同数据模型，但换成单列、强操作层级的移动壳层。
3. **预览页**：标题信息区折叠化，主要空间让给内容本身。
4. **弹窗与工具栏**：移动端优先 bottom sheet / sticky action bar，而不是桌面浮层直接缩放。

## Error Handling

- ffmpeg 不存在：`preview_video` 缺失，但预览整体仍返回 ready。
- ffmpeg 运行失败：仅记录兼容视频未生成，不阻塞原始视频预览。
- preview asset 丢失：`/preview-assets` 返回 404，`/preview` 仍可回退原始视频。
- manifest 缺少 `preview_video`：前端继续按旧视频资产渲染。

## Testing Strategy

### Backend

新增 / 更新测试覆盖：

1. 兼容视频转码 helper 在 ffmpeg 可用时生成 `preview_video`
2. preview queue 对视频持久化 `poster + preview_video + video`
3. manifest 在存在 `preview_video` 时优先把它作为 `primary_asset`
4. admin `/preview` 路由优先流式返回 `preview_video`
5. share `/preview` 路由优先流式返回 `preview_video`

### Frontend

新增 / 更新测试覆盖：

1. `FileViewer` / `VideoViewer` 能渲染 `preview_video`
2. `SharePreview` 接受 `preview_video` manifest
3. 旧 `video` manifest 仍保持兼容

## Out Of Scope

- 新增多码率自适应播放
- 引入 HLS / DASH
- 重写 preview asset 鉴权体系
- 本轮直接完成全部 mobile shell 视觉收口

## Validation

满足以下条件即视为本轮目标达成：

1. 视频 worker 能在可用环境下生成 `preview_video`
2. 视频 manifest 优先输出 `preview_video`
3. admin/share `/preview` 路由命中视频时优先返回兼容 mp4
4. 分享页视频预览能直接消费 `preview_video`
5. 旧数据没有 `preview_video` 时，原有视频预览不回归

