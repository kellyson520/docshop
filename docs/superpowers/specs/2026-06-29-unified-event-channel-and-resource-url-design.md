# 2026-06-29 统一事件通道、资源 URL 收口与后台路径映射设计

## 目标

本次设计覆盖 3 个目标：

1. 把当前管理员设置页对配置的 3 秒轮询刷新，升级为全项目可复用的统一事件通道。
2. 扫描并统一前端所有图片 / 文件 / 预览 / 下载 URL 的拼接入口，避免组件内散落硬编码路径。
3. 梳理后台主要请求路径分组，形成便于理解和后续维护的映射。

## 现状与问题

### 1. 配置热同步

当前 `frontend/src/views/admin/AdminSettings.vue` 仅在安全页签打开时启动 3 秒轮询，请求 `/api/v1/settings` 以刷新配置。问题是：

- 轮询有无效请求开销。
- 机制只服务于单页，无法复用于公告、任务进度、追踪状态等后续实时场景。
- 页面自己控制轮询生命周期，缺少统一的连接、重连、异常处理策略。

### 2. 资源 URL 拼接分散

目前头像和封面已部分收口，但文件预览、文件下载、share 预览、share 下载、公告附件等 URL 仍散落在组件和工具函数内，主要问题是：

- 组件里直接写 `/api/v1/...`，维护成本高。
- 普通文件和分享态文件 URL 规则相似但不统一。
- 测试里也复制了大量 URL 模板，修改协议时回归成本高。

### 3. 后台路径认知成本高

后端路由按模块分散在多个 router 文件中，虽然结构本身合理，但从页面行为追踪到具体后端路径时需要跨多个文件搜索，不利于后续继续收口和做实时事件映射。

## 范围

### 本次纳入范围

- 建立统一事件通道（以 SSE 协议为基础）
- 建立统一前端资源 URL 构建模块
- 将管理员设置页改为事件订阅驱动刷新
- 为后续公告刷新、追踪状态、任务进度等场景预留复用接口
- 输出后台主要路由映射文档

### 本次不纳入范围

- 不引入 WebSocket 作为主实时协议
- 不做跨进程 / 跨实例的分布式消息系统
- 不做事件持久化、离线补偿、消息重放
- 不在本次直接改造全部业务页为实时模式，只完成统一机制和首个配置场景接入

## 备选方案

### 方案 A：SSE 协议 + fetch 流式客户端（推荐）

后端提供统一 `text/event-stream` 长连接入口，前端使用 `fetch` + `ReadableStream` 读取事件流，并保留现有 `Authorization: Bearer` 头鉴权方式。

优点：

- 适合当前单向服务端推送场景
- 与 FastAPI 和现有 token 鉴权兼容性好
- 能抽象成 topic 订阅机制
- 比 WebSocket 更轻，改造成本低

缺点：

- 需要自己实现一层事件流解析与重连逻辑

### 方案 B：原生 EventSource + 单独 stream token

通过普通 API 先换取短期 stream token，再用原生 `EventSource` 连接。

优点：

- 前端基础使用更直接

缺点：

- 需要额外的 token 签发、续签、失效控制
- 增加一层新的认证复杂度，收益不高

### 方案 C：WebSocket 统一总线

优点：

- 双向能力最强，扩展面广

缺点：

- 对当前需求偏重
- 鉴权、连接管理、断线恢复复杂度更高

## 结论

采用 **方案 A：SSE 协议 + fetch 流式客户端**。

理由：

- 当前明确需求是“后端向前端广播变化”，单向推送即可。
- 现有 API 认证基于 `Authorization` 头，使用 fetch 能直接复用。
- 后续公告刷新、追踪状态、任务进度都可以按 topic 继续扩展，而不需要立刻引入更重的双向通道。

## 设计总览

### 后端新增模块

建议新增：

- `backend/app/services/event_bus.py`
- `backend/app/services/config_watch.py`
- `backend/app/routers/events.py`

### 前端新增模块

建议新增：

- `frontend/src/services/eventStream.js`
- `frontend/src/composables/useEventChannel.js`
- `frontend/src/utils/resourceUrl.js`

### 现有模块改造重点

- `backend/app/main.py`：注册事件 router、在 lifespan 中启动 / 停止配置监听
- `backend/app/routers/settings.py`：配置保存成功后发布 `config.updated`
- `frontend/src/views/admin/AdminSettings.vue`：移除 3 秒轮询，改为订阅 `config` topic
- `frontend/src/utils/assetUrl.js`、`frontend/src/utils/preview.js`：折叠或迁移到新的统一 URL 构建模块
- `ShareDiff.vue` / `ShareFile.vue` / `SharePreview.vue` / `ShareProject.vue` / `AnnouncementRenderer.vue` / `DiffView.vue`：改为调用统一 URL helper

## 统一事件通道设计

### 路由

新增统一事件流入口：

- `GET /api/v1/events/stream`

请求参数：

- `topics=config,announcements,tracking,tasks`

约束：

- 必须登录
- 只允许订阅调用者有权限访问的 topic
- 未授权 topic 不进入订阅集合

可选扩展参数（先预留，不要求首版完整实现）：

- `last_event_id`
- `client_id`

### 事件主题

首版按 topic 分流：

- `config`：运行期配置变化，管理员可订阅
- `announcements`：公告变化，登录用户可订阅
- `tracking`：追踪 / 审计相关变化，管理员可订阅
- `tasks`：后台任务进度，任务所属用户或管理员可订阅

### 事件 envelope

统一事件结构：

```json
{
  "id": "evt_20260629_xxx",
  "topic": "config",
  "type": "config.updated",
  "scope": "global",
  "ts": "2026-06-29T12:34:56Z",
  "version": "config:42",
  "payload": {
    "changed_keys": ["LOG_LEVEL", "MAX_FILE_SIZE"]
  }
}
```

字段说明：

- `id`：事件唯一标识
- `topic`：订阅主题
- `type`：细粒度事件类型
- `scope`：作用域，如 `global` / `user:<id>` / `task:<id>`
- `ts`：事件时间
- `version`：当前主题版本号或单调递增标识
- `payload`：非敏感载荷

设计约束：

- `config` 事件不直接广播完整配置值，更不广播敏感项。
- `config` 事件只广播“发生变化”与“变化键集合”，前端收到后再重新请求 `/api/v1/settings`。
- 这样可以减少敏感信息泄露风险，并保持单一读源。

### 后端事件总线

`event_bus.py` 提供进程内发布订阅能力：

- topic 级订阅
- 每个连接一个有界异步队列
- 发布时向匹配 topic 的订阅者投递 envelope
- 支持过滤 scope / user / role

边界：

- 这是单进程 / 单实例内总线
- 不解决多实例广播问题
- 对当前本地和现有部署形态足够

### 连接与队列策略

每个订阅连接维护：

- 订阅 topic 集合
- 用户上下文（user id / role）
- bounded queue（例如 100 条）
- 最近心跳时间

慢消费者策略：

- 队列满时不阻塞全局发布
- 对低优先级事件采取覆盖或丢弃旧事件策略
- 对关键 topic（如 `config`）优先保证最新态，不追求完整历史

### SSE 输出格式

服务端按 SSE 标准输出：

```text
event: config.updated
id: evt_20260629_xxx
data: {...json...}

```

补充两类内部事件：

- `event: heartbeat`
- `event: ready`

其中：

- `ready`：连接建立后立即发一次，前端可据此确认订阅成功
- `heartbeat`：周期性发送，避免中间网络层静默断开

### 配置变更来源

配置变化有两个来源：

1. **后端 API 写入**
   - `PUT /api/v1/settings`
   - `_write_env(...)`
   - `apply_runtime_settings(...)`
   - 发布 `config.updated`

2. **手工编辑 `.env`**
   - 后端后台 watcher 检测 `.env` 文件变化
   - 重新加载运行时配置
   - 发布 `config.updated`

### `.env` 监听设计

新增 `config_watch.py`，职责：

- 记录 `.env` 的 mtime + 内容 fingerprint
- 在后台任务中定期检查变化
- 检测到变化后去抖、重新加载并发布事件

说明：

- 用户当前要求的“更干净事件 / 长连接方案”针对的是前端同步方式，因此本次关键改造点是前端从轮询转为事件订阅。
- `.env` 文件监听在后端内部可以保持轻量实现，不额外引入复杂实时基础设施。
- 为控制依赖面，首版 watcher 采用后台轻量检查 + fingerprint 去重，而不是新增 WebSocket 或强依赖额外文件监听库。

### 前端事件客户端

`eventStream.js` 负责：

- 建立 `fetch('/api/v1/events/stream?...')`
- 注入 `Authorization` 头
- 使用 `ReadableStream` 按 chunk 解析 SSE 帧
- 识别 `event` / `id` / `data`
- 心跳保活
- 自动重连（指数退避）

`useEventChannel.js` 负责：

- 以 composable 暴露订阅接口
- 支持按 topic 注册回调
- 支持组件 mount / unmount 生命周期自动订阅与清理
- 在认证失效时通知现有登录流程

### AdminSettings 接入方式

`AdminSettings.vue` 改造为：

- 页面初始化请求一次 `/settings`
- 打开设置页后订阅 `config` topic
- 收到 `config.updated` 后调用现有设置加载逻辑
- 移除 3 秒 interval 轮询

行为结果：

- 后台保存设置，页面立即收到变化
- 直接编辑 `.env`，只要 watcher 检测到变化，页面也会自动刷新

## 统一资源 URL 收口设计

### 设计原则

- 所有“给浏览器直接访问的资源 URL”统一由 helper 构建
- `api/*.js` 继续负责 XHR / Axios 请求
- 组件、view、renderer 不再手写 `/api/v1/...` 字符串拼接
- 旧 helper 如 `assetUrl.js` / `preview.js` 可以保留兼容封装，但新的唯一出口是 `resourceUrl.js`

### 模块职责

新增 `frontend/src/utils/resourceUrl.js`，统一提供：

#### 静态资源

- `resolveAvatarUrl(avatarPath)`
- `resolveCoverUrl(coverPath)`

#### 普通文件

- `buildFilePreviewUrl(fileId, options)`
- `buildFilePageUrl(fileId, pageNum, options)`
- `buildFilePreviewAssetUrl(fileId, assetId, options)`
- `buildFileDownloadUrl(fileId, versionId, format)`
- `buildFileHtmlUrl(fileId, options)`
- `buildFileTextUrl(fileId, options)`

#### 分享态文件

- `buildSharePreviewUrl(token, fileId, options)`
- `buildSharePageUrl(token, fileId, pageNum, options)`
- `buildSharePreviewAssetUrl(token, fileId, assetId, options)`
- `buildShareDownloadUrl(token, fileId, versionId, format)`
- `buildShareFolderDownloadUrl(token, folderId)`

#### 附件 / 杂项

- `buildAnnouncementAttachmentUrl(fileId)`

### 兼容策略

helper 需兼容以下输入：

- 已经是 `/api/v1/...` 的绝对站内路径
- `avatars/...`、`covers/...` 这种相对片段
- `/avatars/...`、`/covers/...` 这种带斜杠片段
- `http(s)://` 外链
- `data:`、`blob:` URL

### 首批收口改造清单

明确改造这些现有散点：

- `frontend/src/components/announcement/AnnouncementRenderer.vue`
- `frontend/src/views/share/ShareDiff.vue`
- `frontend/src/views/share/ShareFile.vue`
- `frontend/src/views/share/SharePreview.vue`
- `frontend/src/views/share/ShareProject.vue`
- `frontend/src/views/admin/DiffView.vue`
- `frontend/src/utils/preview.js`

以及对应测试：

- share 相关测试
- file viewer 相关测试
- preview 工具测试
- cover / avatar 工具测试

### 不直接改造的边界

- `api/*.js` 内部调用后端数据接口的路径不纳入本次资源 URL helper
- 这类路径已经由 Axios `baseURL=/api/v1` 统一管理，不和浏览器资源地址混用

## 后台路径映射

### 认证

- `/api/v1/auth/login`
- `/api/v1/auth/register`
- `/api/v1/auth/registration-policy`
- `/api/v1/auth/me`

### 设置

- `GET /api/v1/settings`
- `PUT /api/v1/settings`
- `POST /api/v1/settings/change-password`
- `GET /api/v1/settings/devices`
- `POST /api/v1/settings/devices/logout-all`
- `POST /api/v1/settings/avatar`

### 用户与管理

- `GET /api/v1/users`
- `POST /api/v1/users`
- `PUT /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`
- `GET /api/v1/users/settings/registration`
- `PUT /api/v1/users/settings/registration`
- `GET /api/v1/admin/users`
- `GET /api/v1/admin/settings`
- `GET /api/v1/admin/logs`

### 项目

- `GET /api/v1/projects/{project_id}`
- `GET /api/v1/projects/{project_id}/folders`
- `POST /api/v1/projects/{project_id}/folders`
- `PUT /api/v1/projects/{project_id}/folders/{folder_id}`
- `DELETE /api/v1/projects/{project_id}/folders/{folder_id}`
- `GET /api/v1/projects/{project_id}/folders/{folder_id}/download`
- `PUT /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/regenerate-token`
- `GET /api/v1/projects/{project_id}/stats`

### 文件

项目下文件列表 / 上传：

- `POST /api/v1/projects/{project_id}/files`
- `GET /api/v1/projects/{project_id}/files`

文件实体与预览：

- `GET /api/v1/files/{file_id}`
- `DELETE /api/v1/files/{file_id}`
- `GET /api/v1/files/{file_id}/preview-status`
- `GET /api/v1/files/{file_id}/analysis`
- `GET /api/v1/files/{file_id}/versions`
- `POST /api/v1/files/{file_id}/versions`
- `DELETE /api/v1/files/{file_id}/versions/{version_id}`
- `GET /api/v1/files/{file_id}/download`
- `GET /api/v1/files/{file_id}/versions/{version_id}/download`
- `GET /api/v1/files/{file_id}/versions/{version_id}/download/{format}`
- `GET /api/v1/files/{file_id}/preview`
- `GET /api/v1/files/{file_id}/pages/{page_num}`
- `GET /api/v1/files/{file_id}/preview-assets/{asset_id}`
- `GET /api/v1/files/{file_id}/html`
- `GET /api/v1/files/{file_id}/text`

后台预览管理：

- `GET /api/v1/admin/files/previews`
- `POST /api/v1/admin/files/preconvert`
- `DELETE /api/v1/admin/files/{file_id}/preview-cache`
- `POST /api/v1/admin/files/preview-cache/cleanup`

### Diff

- `POST /api/v1/diffs`
- `GET /api/v1/files/{file_id}/diffs`
- `GET /api/v1/files/{file_id}/diffs/{diff_id}`

### 卡片

- `GET /api/v1/cards/categories`
- `GET /api/v1/cards/tags`
- `GET /api/v1/cards/{card_id}`
- `POST /api/v1/cards/{card_id}/cover`
- `PUT /api/v1/cards/{card_id}/info`
- `POST /api/v1/cards/{card_id}/versions/compare`
- `GET /api/v1/cards/rank/download`
- `GET /api/v1/cards/rank/visit`
- `POST /api/v1/cards/{card_id}/visit`
- `GET /api/v1/cards/{card_id}/download`
- `DELETE /api/v1/cards/{card_id}`

### 分享与公开访问

- `GET /api/v1/share/public-exams`
- `GET /api/v1/share/public-exams/{exam_id}`
- `GET /api/v1/share/public-projects`
- `GET /api/v1/share/{share_token}`
- `GET /api/v1/share/{share_token}/files/{file_id}`
- `GET /api/v1/share/{share_token}/files/{file_id}/versions`
- `GET /api/v1/share/{share_token}/folders/{folder_id}/download`
- `GET /api/v1/share/{share_token}/files/{file_id}/diffs`
- `GET /api/v1/share/{share_token}/files/{file_id}/versions/{version_id}/download`
- `GET /api/v1/share/{share_token}/files/{file_id}/versions/{version_id}/download/{format}`
- `GET /api/v1/share/{share_token}/files/{file_id}/preview`
- `GET /api/v1/share/{share_token}/files/{file_id}/pages/{page_num}`
- `GET /api/v1/share/{share_token}/files/{file_id}/preview-assets/{asset_id}`
- `GET /api/v1/share/{share_token}/files/{file_id}/preview/pdf`

兼容旧前缀：

- `/api/v1/shares/*`

### share token 管理

- `GET /api/v1/share-tokens/policy`
- `PUT /api/v1/share-tokens/policy`
- `PUT /api/v1/share-tokens/{token_id}`
- `POST /api/v1/share-tokens/{token_id}/regenerate`
- `DELETE /api/v1/share-tokens/{token_id}`

### 追踪 / 审计

- `GET /api/v1/tracking/config`
- `POST /api/v1/tracking/ping`
- `GET /api/v1/admin/tracking/config`
- `PUT /api/v1/admin/tracking/config`
- `GET /api/v1/admin/tracking/stats`
- `GET /api/v1/admin/tracking/logs`
- `GET /api/v1/admin/tracking/logs/{log_id}`
- `DELETE /api/v1/admin/tracking/logs`
- `GET /api/v1/admin/tracking/sessions`
- `GET /api/v1/admin/tracking/realtime`

### 内容类

- `/api/v1/announcements/*`
- `/api/v1/notices/*`
- `/api/v1/exams/*`

### 访问 token

- `/api/v1/access-tokens/*`

### 静态资源挂载

- `/api/v1/covers/*`
- `/api/v1/avatars/*`

### 系统

- `/health`
- `/info`
- `/api/v1/health`

## 错误处理

### 事件通道

必须处理：

- 鉴权失败：关闭连接并让前端走现有登录失效逻辑
- 非法 topic：忽略或返回 400，首版优先返回明确错误
- 网络中断：前端自动重连
- 慢消费者：队列有界，防止单个连接拖垮全局
- 心跳超时：服务端 / 前端均可主动关闭并重建

### URL helper

必须处理：

- 外链原样保留
- 已是完整站内路径则不重复拼接
- 缺失参数时返回空字符串或抛出可预测错误，避免生成错误 URL
- 文件 / share 两套路径参数顺序必须统一，避免组件手写时遗漏 `version`、`format`、`token`

## 测试策略

### 后端

新增 / 更新测试覆盖：

- `event_bus` 发布订阅与 topic 过滤
- 队列满载策略
- `/api/v1/events/stream` 鉴权与 topic 权限
- `PUT /api/v1/settings` 成功后发布 `config.updated`
- 手工修改 `.env` 被 watcher 检出后发布 `config.updated`
- watcher 去抖与 fingerprint 去重

### 前端

新增 / 更新测试覆盖：

- `eventStream.js` 的 SSE chunk 解析
- 自动重连与心跳处理
- `AdminSettings.vue` 收到 `config.updated` 后刷新数据
- `resourceUrl.js` 对 avatar / cover / file / share / announcement 的 URL 构建
- 相关组件由硬编码路径改为 helper 后的回归测试

### 验证命令

实现阶段完成后至少执行：

- 后端针对性 pytest
- 前端相关 vitest
- `npm run build`

## 实施顺序

1. 新增后端统一事件总线与事件 stream router
2. 将设置保存事件接入总线
3. 增加 `.env` watcher，把外部文件修改也转成 `config.updated`
4. 新增前端事件流服务与 composable
5. 将 `AdminSettings.vue` 从轮询改为订阅
6. 新增 `resourceUrl.js`
7. 批量替换散落的资源 URL 构建点并更新测试
8. 补充后台路径映射文档说明

## 风险与对应策略

### 风险 1：SSE 连接在代理层被静默断开

策略：

- 服务端定期 heartbeat
- 前端超时重连
- 连接建立后先发 `ready`

### 风险 2：配置变化事件过于频繁

策略：

- watcher 去抖
- `config` 事件只广播最新变更信息，不广播整份配置
- 前端收到事件后做单次刷新，不做连锁请求风暴

### 风险 3：URL helper 改造面大导致回归

策略：

- 先新增 helper，不直接删除旧函数
- 旧 helper 内部可逐步委托给新 helper
- 以测试保护关键分享预览 / 下载链路

## 验收标准

- 管理员设置页不再使用 3 秒轮询
- 后端通过 API 修改配置后，打开中的设置页能自动刷新
- 手工修改 `.env` 后，设置页能在 watcher 检测后自动刷新
- 前端主要浏览器资源 URL 不再在组件内直接手写 `/api/v1/...` 拼接
- 后端主要路由分组可通过本设计文档快速查阅
- 相关测试与构建通过

## 备注

- 按用户要求，本次只在本机落地，不做 git 提交。
