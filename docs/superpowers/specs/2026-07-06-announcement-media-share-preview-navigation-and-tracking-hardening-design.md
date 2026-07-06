# Announcement Media, Share Preview Navigation, and Tracking Hardening Design

## Context

截至 **2026-07-06**，这一轮需要一起收口的是真实线上行为问题，而不是再做抽象整理：

1. **公告富内容块仍然停留在手填 `file_id` 阶段**
   - `image` / `video` 只能手工填 `file_id`
   - 不能像 Windows 资源管理器那样从项目里逐级选择素材
   - 不能直接本地上传后先落到 `/temp/` 再保存提升
   - 也没有安全可控的嵌入代码块能力

2. **分享预览页 / 文件详情页的返回链路丢失来源上下文**
   - `SharePreview.vue` 和 `ShareFile.vue` 当前 `goBack()` 都直接回 `/s/:token`
   - 从某个文件夹里点开的文件预览，返回后不会回到原文件夹视图
   - 从文件详情进入预览，返回后也不会回到文件详情

3. **HTML 沉浸式预览虽然已经可交互，但缺少稳定的“外层返回控制”**
   - 当前 HTML 预览走全屏 iframe / runtime stage
   - 预览内容本身可点击、可互动，这一点必须保留
   - 但沉浸式状态下缺少一个始终可见、位于 iframe 外层的返回按钮

4. **分享预览页顶部版本时间显示错误**
   - 标题已经显示 `v3`
   - 但顶部时间 chip 仍然使用 `fileInfo.created_at`
   - 实际上 `GET /api/v1/share/{token}/files/{id}` 当前并没有暴露“当前版本对应的时间”
   - 结果就是 **V3 仍显示 V1/文件初建时间**

5. **`POST /api/v1/tracking/ping` 仍会出现 benign duplicate 触发的 429**
   - 目前后端对同 identity 做 10 秒限流
   - 带 `page_path` 的 page-view 已经按页面路径分组，但前端没有“同页冷却 / 去重”
   - 所以重复同页 page-view 仍可能在 DevTools 中看到 `429 Too Many Requests`
   - 这类重复请求对用户没有价值，应该降噪，而不是当成异常噪音

6. **关于“前端加密 / 混淆 / 公私钥防看源码”的诉求，需要落到真实安全边界上**
   - 浏览器里最终要执行的代码，不可能靠前端公私钥、混淆或“假加密”实现真正不可见
   - 本轮真正应该继续强化的是：
     - 受控 preview/runtime 输出
     - announcement embed 白名单
     - 资源 ticket / grant
     - 页面内上下文隔离与最小暴露

## Goals

1. 公告块支持 **项目资源选择 + 本地上传暂存 + 安全嵌入 iframe**。
2. 分享项目页、文件详情页、预览页之间的返回链路变为**来源上下文驱动**。
3. HTML 沉浸式预览增加**外层侧边返回按钮**，且不破坏互动能力。
4. 分享预览页顶部版本元信息改为显示**当前版本时间**。
5. tracking ping 对 benign duplicate 做**前后端双层降噪**，避免再看到无意义 429。
6. 不破坏现有：
   - tab 级密码失效机制
   - 公开浏览 / 分享权限边界
   - HTML 预览可点击互动

## Non-Goals

1. 不重做整套分享路由体系。
2. 不把公告素材并入普通项目文件库的权限/生命周期模型。
3. 不把 JS 混淆、公私钥包装、前端“加密源码”当成安全边界。
4. 不修改现有 managed share token 的权限语义。
5. 不在这一轮顺带重构公告推送业务（定时/单人/全员）本身。

## User Constraints

- 项目路径：`C:\Users\lihuo\Desktop\docshop`
- 继续保留 HTML/runtime 预览的**点击互动**能力
- 继续保留“**带密码分享页关闭标签页后密码失效**”的现有机制
- 当前环境可能只有 **HTTP**，方案不能依赖 HTTPS 才能工作
- 不做 commit / push / reset / clean

## Existing Architecture

### 1. 公告富内容块现状

相关文件：
- `backend/app/models/announcement.py`
- `backend/app/routers/announcements.py`
- `frontend/src/views/admin/AnnouncementManager.vue`
- `frontend/src/components/announcement/AnnouncementBlockEditor.vue`
- `frontend/src/components/announcement/AnnouncementRenderer.vue`

当前块类型只有：
- `paragraph`
- `code`
- `button`
- `image`
- `video`

其中 `image` / `video` 的数据结构仍只有：

```json
{
  "type": "image",
  "file_id": "...",
  "caption": "..."
}
```

这意味着：
- 编辑器只能手填 `file_id`
- 渲染器只能把它当成普通文件资源
- 没有 temp 生命周期
- 没有 embed 白名单

### 2. 分享返回链路现状

相关文件：
- `frontend/src/utils/shareRoute.js`
- `frontend/src/views/share/ShareProject.vue`
- `frontend/src/views/share/ShareFile.vue`
- `frontend/src/views/share/SharePreview.vue`
- `frontend/src/views/share/ShareDiff.vue`

当前问题：
- `buildShareFilePath()` / `buildSharePreviewPath()` 不支持上下文 query
- `ShareProject.vue` 的 `currentFolderId` 只保存在本地 state 中
- `ShareFile.vue` / `SharePreview.vue` 的 `goBack()` 固定回 `/s/:token`

此外，`ShareProject.vue` 的文件夹状态实际上有 **三态**：
- `null`：全部文件
- `''`：根目录
- `folderId`：具体文件夹

如果只传 `folder_id`，无法区分“全部文件”和“根目录”。

### 3. 分享预览版本时间现状

相关文件：
- `frontend/src/views/share/SharePreview.vue`
- `backend/app/routers/share.py`
- `backend/app/routers/files.py`

当前 `SharePreview.vue`：
- 标题版本号来自 `current_version`
- 时间 chip 仍然显示 `formatDate(fileInfo.created_at)`

而 `GET /api/v1/share/{token}/files/{id}` 当前返回：
- 文件级 `created_at`
- 文件级 `updated_at`
- `current_version`
- 但**没有**当前版本的 `created_at`

因此前端即使想显示当前版本时间，也拿不到准确数据。

### 4. tracking ping 现状

相关文件：
- `frontend/src/utils/trackingClient.js`
- `backend/app/routers/tracking_ping.py`
- `frontend/src/utils/__tests__/trackingClient.spec.js`
- `test/test_tracking_ping.py`

当前行为：
- 后端 `_RATE_LIMIT_SECONDS = 10`
- 带 `page_path` 的请求按 `identity|page|page_path` 限流
- 不带 `page_path` 的请求按 identity 限流
- 前端 `sendPageViewTracking()` 没有同页冷却
- 后端对 benign duplicate page-view 直接返回 `429`

这说明：
- 真正恶意高频请求仍可保留 429
- 但重复同页 page-view 不应继续当成错误噪音

## Chosen Design

## 1. 公告块数据结构升级

### 1.1 Canonical block schema

公告块升级为以下 canonical 结构：

#### paragraph

```json
{
  "type": "paragraph",
  "text": "部署将于今晚 22:00 开始"
}
```

#### code

```json
{
  "type": "code",
  "language": "bash",
  "content": "docker compose up -d"
}
```

#### button

```json
{
  "type": "button",
  "label": "查看详情",
  "url": "/docs/deploy"
}
```

#### image / video

```json
{
  "type": "image",
  "source_type": "project_file",
  "file_id": "file_123",
  "caption": "封面图"
}
```

```json
{
  "type": "video",
  "source_type": "announcement_asset",
  "asset_id": "ann_asset_123",
  "caption": "宣传视频"
}
```

#### embed

```json
{
  "type": "embed",
  "provider": "iframe",
  "src": "https://player.bilibili.com/player.html?...",
  "embed_html": "<iframe ...></iframe>",
  "caption": "Bilibili 视频"
}
```

### 1.2 Backward compatibility

现有历史数据中的：

```json
{
  "type": "image",
  "file_id": "file_legacy"
}
```

会在 normalize 阶段自动视为：

```json
{
  "type": "image",
  "source_type": "project_file",
  "file_id": "file_legacy"
}
```

因此：
- 老公告不需要数据迁移即可继续展示
- 新编辑保存后统一落成 canonical shape

## 2. 公告素材独立域 + temp 生命周期

### 2.1 不再复用普通项目文件库作为公告上传落点

本地上传的公告图片/视频不进入普通项目文件库；它们属于**公告素材域**。

新增 `announcement_assets` 记录，至少包含：
- `id`
- `announcement_id`（可空）
- `status`：`temp | active`
- `media_type`：`image | video`
- `mime_type`
- `original_name`
- `file_size`
- `storage_path`
- `preview_path`（如需要）
- `created_by`
- `created_at`
- `updated_at`

### 2.2 temp 上传规则

本地上传时：
- 物理文件先写入 `TEMP_DIR/announcement-assets/<asset_id>/...`
- 数据库记录为 `status='temp'`
- 前端立即拿到：
  - `asset_id`
  - `status`
  - `preview_url`
  - `original_name`
  - `media_type`

### 2.3 保存时提升

创建/更新公告时：
- 如果块里引用了 `source_type='announcement_asset'` 且 `asset_id` 指向 temp 资源
- 后端在保存公告前/过程中执行 promote：
  - 校验该 temp 资产属于当前管理员可用范围
  - 把文件迁移到公告正式素材目录
  - `status` 改为 `active`
  - 绑定 `announcement_id`

### 2.4 公开访问规则

公告素材内容访问遵循：
- `temp`：只允许管理员编辑态预览
- `active`：允许公告渲染页读取

这保证：
- 还没保存的临时素材不会成为公开长期地址
- 已发布公告的素材又能被公共渲染端正常访问

## 3. 公告素材交互：项目选择 + 本地上传并存

### 3.1 项目素材选择器

新增公告素材选择对话框，体验目标是“像 Windows 资源管理器一样逐级进入”：

1. 先选项目
2. 再看该项目文件夹树 / 当前目录资源
3. 逐级进入文件夹
4. 选中具体文件

该选择器只允许选择与块类型匹配的资源：
- `image` 块：图片类文件优先
- `video` 块：视频类文件优先

保存结果写入：
- `source_type='project_file'`
- `file_id='<selected file id>'`

### 3.2 本地上传

块编辑器同时提供：
- `从项目选择`
- `本地上传`

本地上传只负责产出：
- `source_type='announcement_asset'`
- `asset_id='<temp asset id>'`

### 3.3 为什么两个入口都保留

用户已经明确需要两种来源：
- 某些素材本来就在项目里，应该直接复用
- 某些素材只是公告临时物料，不应混进项目文件库

因此这两个入口必须共存，而不是二选一。

## 4. 安全嵌入块：只支持白名单 iframe

### 4.1 支持范围

新增 `embed` 块，但**不是任意 HTML 原样注入**，而是：
- 仅支持 `<iframe>`
- 只保留白名单属性
- 只允许白名单域名

初始 provider allowlist 先满足当前明确诉求：
- `player.bilibili.com`

### 4.2 清洗规则

后端做 authoritative sanitization：
- 移除 `script`
- 移除内联事件（如 `onclick`）
- 移除 `javascript:` / `data:` 可执行 URL
- 仅保留属性：
  - `src`
  - `width`
  - `height`
  - `allow`
  - `allowfullscreen`
  - `frameborder`
  - `scrolling`
  - `referrerpolicy`
  - `loading`
  - `title`

前端可以做预校验，但**以后端清洗结果为准**。

### 4.3 安全边界说明

这不是“让用户绝对看不到嵌入内容代码”，而是：
- 禁止任意 script 注入
- 把可执行面收窄到白名单 iframe provider
- 保证公告块不会因为 embed 变成自由 HTML 容器

## 5. 公告渲染规则统一

### 5.1 project_file 与 announcement_asset 分流

渲染层不再只认 `file_id`。

- `source_type='project_file'`
  - 走现有项目文件预览/下载 URL 解析
  - 图片/视频优先走 previewable 资源，而不是一律走 download URL

- `source_type='announcement_asset'`
  - 走公告素材内容 URL

### 5.2 embed 渲染

`embed` 块使用受控 wrapper 渲染 sanitized iframe，不走 `v-html` 原样全放。

### 5.3 编辑预览与实际渲染共用同一套 block resolver

`AnnouncementManager.vue` 中的编辑态预览，和前台/弹窗公告实际渲染，共用同一套 normalize + resolve 逻辑，避免：
- 编辑器里能看，实际页面不能看
- 编辑器里是项目文件路径，实际页面是 announcement asset 路径
- embed 行为前后不一致

## 6. 分享返回链路改为上下文 query 驱动

## 6.1 Query contract

因为 `ShareProject.vue` 文件夹状态是三态，所以 query 不能只用 `folder_id`。

新的分享上下文 query：
- `from=project | file`
- `folder_scope=all | root | folder`
- `folder_id=<id>`（仅 `folder_scope=folder` 时需要）

示例：

从“全部文件”列表进入预览：

```text
/s/share-token/preview/file-1?from=project&folder_scope=all
```

从根目录进入文件详情：

```text
/s/share-token/files/file-1?from=project&folder_scope=root
```

从具体文件夹进入预览：

```text
/s/share-token/preview/file-1?from=project&folder_scope=folder&folder_id=folder-a
```

从文件详情再进入预览：

```text
/s/share-token/preview/file-1?from=file&folder_scope=folder&folder_id=folder-a
```

## 6.2 返回规则

### SharePreview

- `from=file`：返回 `/s/:token/files/:fileId`，并带回 folder context
- `from=project`：返回 `/s/:token`，并恢复对应文件夹/全部文件视图
- query 缺失或非法：fallback `/s/:token`

### ShareFile

- 如果自己是从 `project` 进入：返回 `/s/:token` + folder context
- 如果自己没有有效来源信息：fallback `/s/:token`

### ShareDiff

`ShareDiff.vue` 也要透传同样 query，否则：
- 文件详情带着 folder context 进入 diff
- diff 返回文件详情时上下文会丢

这会重新制造一轮导航断链，所以 diff 也必须并入同一套 helper。

## 6.3 ShareProject 状态持久化

`ShareProject.vue` 需要把当前文件夹视图与 route.query 双向同步：
- 初次进入时从 query 恢复 `currentFolderId`
- 切换文件夹时更新 query
- 点击“版本 / 预览 / 变更”时把 query 一并传下去

这样才能保证：
- 浏览器刷新后仍停留在正确文件夹视图
- 深链进入后返回链路不丢
- 预览 -> 返回 -> 继续操作 过程中状态一致

## 7. HTML 预览增加外层侧边返回按钮

### 7.1 目标

对于沉浸式 HTML/runtime 预览：
- 保持全屏预览和互动能力
- 增加一个始终可见的外层返回按钮
- 按钮位于 iframe 外层，不依赖 iframe 内页面自己提供返回 UI

### 7.2 交互要求

- 默认定位在左侧中部或左上偏中，保证易点
- 只占自己点击区域，不能盖住整个预览
- 点击后调用和顶部“返回”同一个上下文 `goBack()`

### 7.3 不改变的东西

- 不再回退到旧的 `location.replace()` 模式
- 不牺牲 iframe sandbox / runtime preview
- 不为了加返回按钮而影响 HTML 页内点击

## 8. 当前版本时间改为显式契约

## 8.1 后端新增 `current_version_entry`

`GET /api/v1/share/{token}/files/{id}` 新增：

```json
{
  "current_version_entry": {
    "id": "ver_3",
    "version": 3,
    "created_at": "2026-06-18T08:10:00Z",
    "updated_at": "2026-06-18T08:10:00Z",
    "file_size": 25653214,
    "changelog": "补充答案版内容"
  }
}
```

这比让前端自己猜更稳妥，因为：
- `SharePreview.vue` 当前只请求 `getShareFile()`
- 它并不会额外拉 `versions`
- 直接在 file detail payload 中给出当前版本元信息最简单、最稳定

### 8.2 前端显示优先级

`SharePreview.vue` 顶部时间 chip 改为：

1. `fileInfo.current_version_entry.created_at`
2. fallback `fileInfo.updated_at`
3. fallback `fileInfo.created_at`

这样即使后端暂时拿不到完整版本对象，也不会回退成空值。

### 8.3 一致性增强

如果 share project/file list 里已有最新版本摘要，也应补齐 `created_at`，避免之后别的界面再重复踩“版本号和时间源不一致”的坑。

## 9. tracking ping 429：前后端双层降噪

## 9.1 前端：同页 page-view cooldown

`trackingClient.js` 增加模块级去重/冷却：
- key：`page_path`
- window：10 秒

规则：
- 同一页面 10 秒内重复 `sendPageViewTracking()`，直接忽略
- 不影响跨页面切换上报
- 不影响 init beacon 的设备/会话采集职责

## 9.2 后端：同页重复 page-view 返回 204 而不是 429

后端保留真正的限流边界，但对 benign duplicate 做 idempotent 处理：

- 若请求**带 `page_path`**
- 且命中“同 identity + 同 page_path + 10 秒窗口”
- 则返回 `204 No Content`
- 不当作错误噪音

仍然保留 `429` 的场景：
- 不带 `page_path` 的异常高频 ping
- 真正不符合 benign duplicate 特征的滥用情况

### 9.3 为什么要双层都做

只改前端不够：
- 仍可能有竞态 / 重复触发 / 多入口调用

只改后端也不够：
- 前端仍会发出无价值请求

双层都做后：
- 正常浏览几乎看不到 429 噪音
- 真实限流能力仍保留

## 10. 关于“防看源码”的正式落地边界

这一轮正式采纳的边界是：
- 继续走 **runtime / controlled preview**
- embed 只允许白名单 iframe
- 公告本地上传走 temp -> promote，不直接暴露普通文件库路径
- 分享预览继续依赖 ticket / grant / route context，而不是暴露原始实现细节

**不会**采纳为主方案的内容：
- 前端公私钥“加密源码”
- 纯混淆当安全边界
- 试图让浏览器执行了代码但用户完全无法观察任何运行结果

也就是说，本轮的“更安全”是：
- 更少原始实现直接暴露
- 更可控的渲染入口
- 更严的 embed 面
- 更稳定的会话/导航/资源访问行为

而不是宣传一个做不到的“前端绝对不可逆”。

## Error Semantics

- 公告 embed 非白名单：`422 invalid_announcement_embed`
- 公告保存时引用了不存在/过期的 temp `asset_id`：`422 invalid_announcement_asset`
- 分享上下文 query 非法：忽略并回退默认返回路径
- tracking 同页重复 page-view：`204`，不报错
- `current_version_entry` 缺失：前端 fallback，不阻塞预览

## Testing Strategy

### Backend

1. 公告素材：
   - temp 上传成功
   - temp 资产在公告保存时被 promote
   - 历史 `file_id` 块兼容
   - embed 白名单清洗生效

2. 分享文件 detail payload：
   - `current_version_entry` 正确返回当前版本时间

3. tracking ping：
   - 同 session 同 page_path 的重复 page-view 返回 `204`
   - 不带 `page_path` 的高频 ping 仍保持 `429`

### Frontend

1. 公告编辑器：
   - image/video 可切换“项目选择 / 本地上传”
   - 可回填 `project_file` 与 `announcement_asset`
   - embed 输入校验与预览

2. 公告渲染器：
   - `project_file` 渲染
   - `announcement_asset` 渲染
   - embed iframe 渲染

3. 分享导航：
   - `ShareProject -> ShareFile -> SharePreview -> back`
   - `ShareProject(folder) -> SharePreview -> back`
   - `ShareFile -> ShareDiff -> back`

4. SharePreview：
   - 显示 `v3` 时使用 `current_version_entry.created_at`
   - HTML 沉浸式预览显示侧边返回按钮

5. trackingClient：
   - 同页 10 秒内重复 page-view 被抑制
   - 跨页面切换仍正常发送

## Risks and Mitigations

1. **公告历史块结构与新结构并存**
   - Mitigation：统一 normalize，写入时升级，读取时兼容。

2. **项目视图存在三态，单靠 `folder_id` 会丢语义**
   - Mitigation：明确引入 `folder_scope=all|root|folder`。

3. **白名单 embed 过严导致部分 iframe 无法嵌入**
   - Mitigation：先满足已明确需求的 `player.bilibili.com`，后续按 provider 增量放开。

4. **tracking 429 全改 204 会掩盖真实滥用**
   - Mitigation：只对“带 `page_path` 的同页重复 page-view”静默化，其他保留 429。

5. **前端单独修时间会继续依赖猜测**
   - Mitigation：后端显式提供 `current_version_entry`，前端只负责展示优先级。

## Open Decisions Resolved

- 公告素材是否继续只走 `file_id`：**否**
- 公告本地上传是否先落 `/temp/` 再保存：**是**
- 公告是否支持嵌入代码：**是，但只支持白名单 iframe/embed**
- 公告素材是否支持“项目内选择 + 本地上传”并存：**是**
- 分享返回链路是否只修公开/分享预览：**是，本轮只修 share/public 链路**
- tracking 429 是否纳入本轮整体方案：**是**
- SharePreview V3 时间错误是否纳入本轮整体方案：**是**

## Implementation Summary

这一轮采用的是一个**最小但闭环**的组合方案：
- 公告侧：从 `file_id` 手填升级为“**项目资源选择 + temp 上传公告素材 + 白名单 iframe embed**”
- 分享侧：把返回行为改成“**来源上下文 query 驱动**”，并给 HTML 沉浸式预览补齐**外层侧边返回按钮**
- 预览元信息侧：通过后端显式返回 `current_version_entry`，修掉“V3 仍显示 V1 时间”的问题
- tracking 侧：用“**前端同页 cooldown + 后端 benign duplicate 204**”把无意义 429 收口

这样可以同时解决用户看到的真实问题，又不会引入假的安全承诺。

## Implementation Status (2026-07-06)

- 已落地能力：
  - 公告块支持 `project_file | announcement_asset | embed`
  - 公告本地上传走 temp asset -> promote
  - 分享 project/file/preview/diff 路由已显式携带 `from / folder_scope / folder_id`
  - HTML 沉浸式分享预览已补侧边返回按钮
  - share file payload 已包含 `current_version_entry`
  - tracking 同页重复 page-view 已做前后端双层去噪
- 验证结果：
  - Backend: `52 passed in 7.68s`
  - Frontend targeted Vitest: `78 passed in 3.78s`
  - Frontend build: `vite build` 成功，只有 `@vueuse/core` 的非阻塞 `/* #__PURE__ */` 注释警告
- 当前结论：
  - 分享预览现在能返回到原文件夹或文件详情上下文
  - V3 预览时间现在显示当前版本时间，而不是文件初始创建时间
  - tracking 同页重复 page-view 不再制造无意义 429 噪声
