# DocShop 全量强化设计

**日期:** 2026-06-07  
**范围:** 用户确认“全部采纳”的 9 项改进：安全初始化、DOCX diff、前端 diff 体验、大文档性能、自动化测试、统一 schema、后台任务/历史、权限审计、发布运维。

## 1. 设计目标

DocShop 要从“能跑的文档对比工具”升级为“可稳定演示、可回归测试、可维护扩展”的文档对比平台。重点不是继续堆叠页面，而是把 diff 数据结构、权限边界、任务状态、前端显示、测试样本和启动运维形成闭环。

## 2. 推荐方案

采用渐进式强化：保留当前 FastAPI + Vue 3 + Element Plus 架构，不做大迁移；先补统一 schema 和防御性适配，再在 DOCX diff、前端 diff view、用户/token 管理、运维脚本上做小步可测改动。

备选方案 A 是重写 diff 引擎和 UI，收益高但风险和时间不可控；备选方案 B 是只做样式优化，短期好看但核心稳定性不足。当前采用渐进式强化最适合连续迭代。

## 3. 后端架构

新增一个 diff result normalization 层，统一 PDF/DOCX/XLSX 的返回结构：`text`、`tables`、`images`、`metadata`、`summary`、`stats`。各 diff engine 可继续保留格式细节，但 API/service 对外输出时必须规范化。

DOCX 图片对比继续以 occurrence 为单位，记录 hash、文件名、尺寸、段落位置、关系类型、data uri。段落调序、表格行列调序继续单独作为 move/reorder 类变更，不再混入 delete/add。

后台任务和历史先做轻量版：不引入 Celery，不大改数据库；在 diff service/API 记录耗时、状态、错误摘要，并让前端可以显示最近 diff 结果的任务级信息。

## 4. 前端架构

Diff 页面采用“摘要 + 筛选工具条 + 虚拟/分段渲染 + 图片/表格专用面板”的结构。颜色降低饱和度，保持和现有深色侧栏、玻璃卡片风格一致；动画只保留轻量 CSS transition，避免造成页面闪动和卡顿。

DOCX diff view 增加：类型筛选、操作筛选、搜索、高亮、只看图片/表格/移动；图片变更显示缩略图、hash、尺寸、位置、替换左右对比；表格变更采用更接近 Excel 的单元格级高亮。

## 5. 安全和权限

保留当前管理员默认账号用于本地演示，但新增 reset admin password 脚本和默认密码风险提示。未登录或未携带 token 必须被前端路由和 axios 层拦截；管理员专属页面继续由角色守卫保护。

用户管理继续集中到管理员侧：创建用户开关、角色、权限、token 面板统一显示和管理。敏感 token 不在最终输出中暴露。

## 6. 测试策略

后端采用 pytest：新增 schema normalization、图片删除/替换/尺寸变化、段落调序、表格行列变化、diff 任务指标测试。前端采用 vitest：DiffSummary、DocxDiffView、DiffView 对统一 schema 和筛选搜索进行组件测试。E2E 采用 Playwright：登录、上传原文档/变体、打开 diff、检查文本/表格/图片区域。

## 7. 运维

新增 `scripts/start_dev.ps1` 和 `scripts/stop_dev.ps1`，统一启动/停止前后端，写入 PID 文件和日志。新增 `scripts/reset_admin_password.py`，用于重置管理员密码。所有脚本路径固定，便于用户直接运行。

## 8. 已批准执行

用户已在 2026-06-07 明确回复“全部采纳”。本 spec 不再等待额外确认，直接进入 implementation plan 和执行。
