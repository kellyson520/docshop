# DocShop Web UI/UX 审计记录（2026-06-11）

本文件记录前端界面和交互体验的轻量审计结论，便于后续持续优化。

## 已发现问题

### 1. 响应式断点不统一

- `useResponsive.js`、布局组件和部分页面样式存在不同的 tablet/desktop 边界。
- 建议统一为：mobile `<768px`，tablet `768-1199px`，desktop `>=1200px`。

### 2. 动效和交互反馈分散

- 全局按钮、卡片、弹窗、空状态的 hover/active 反馈不完全一致。
- 建议保留低成本 CSS transform/opacity 动效，并遵守 `prefers-reduced-motion`。

### 3. 移动端弹窗和表格体验可继续优化

- Element Plus 的 tabs、dialog、table 在移动端仍有局部拥挤。
- 建议对管理后台高频页面逐步增加移动端 sheet、横向滚动提示和安全区 padding。

### 4. 组件复用空间

- `PageHeader.vue`、`SkeletonCard.vue`、`SkeletonTable.vue`、`EmptyState.vue` 可继续统一在列表页/详情页中使用。
- 未使用组件需要确认用途，避免长期死代码。

## 后续建议

1. 统一响应式断点和页面容器宽度。
2. 对上传、预览生成、批量公开等长任务补充更明确的 loading 和失败原因。
3. Diff 页面继续优化段落/表格差异展示。
4. 分享与访问令牌管理页继续补充状态、复制、过期提示。
