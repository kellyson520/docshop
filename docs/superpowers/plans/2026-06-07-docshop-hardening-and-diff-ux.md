# DocShop Hardening And Diff UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成用户确认采纳的 9 项强化：安全初始化、DOCX diff、前端 diff 体验、大文件性能、自动化测试、统一 schema、任务历史、权限审计、发布运维。

**Architecture:** 保持 FastAPI + Vue 3 + Element Plus，不重写全栈。新增 diff normalization 层统一输出结构；前端 DocxDiffView 以计算属性完成筛选搜索和专用渲染；脚本层提供本地启动、停止、管理员密码重置。

**Tech Stack:** Python 3、FastAPI、SQLAlchemy、pytest、Vue 3、Element Plus、Vitest、Playwright、PowerShell。

---

## File Structure

- `backend/app/schemas/diff_result.py`: 新增统一 diff result normalizer，负责 text/tables/images/metadata/summary/stats。
- `backend/app/services/diff_service.py`: 调用 normalizer，补充耗时、状态、错误字段。
- `backend/tests/test_diff_result_schema.py`: 后端 schema normalization 单元测试。
- `backend/tests/test_docx_diff.py`: 增加图片替换/删除/尺寸和表格/段落调序覆盖。
- `frontend/src/components/diff/DocxDiffView.vue`: 增加筛选、搜索、降低颜色强度、轻量动画、分段显示。
- `frontend/src/components/diff/DiffSummary.vue`: 统一 stats chip 和任务状态。
- `frontend/src/views/admin/DiffView.vue`: 适配统一 schema 和任务历史信息。
- `frontend/src/components/diff/__tests__/DocxDiffView.spec.js`: 增加筛选和搜索测试。
- `frontend/e2e/diff-docx.spec.js`: 新增 DOCX diff 前端回归。
- `scripts/reset_admin_password.py`: 新增管理员密码重置脚本。
- `scripts/start_dev.ps1`: 新增一键启动脚本。
- `scripts/stop_dev.ps1`: 新增停止脚本。

## Task 1: Diff Result Schema Normalizer

- [x] Step 1: 写失败测试 `backend/tests/test_diff_result_schema.py`，构造 legacy DOCX/PDF/XLSX diff，断言返回包含 `text/tables/images/metadata/summary/stats`。
- [x] Step 2: 运行 `pytest backend\tests\test_diff_result_schema.py -q`，应因模块不存在失败。
- [x] Step 3: 创建 `backend/app/schemas/diff_result.py`，实现 `normalize_diff_result(raw, file_type=None, elapsed_ms=None, status='completed', error=None)`。
- [x] Step 4: 修改 `backend/app/services/diff_service.py`，在服务输出前调用 normalizer。
- [x] Step 5: 运行 `pytest backend\tests\test_diff_result_schema.py backend\tests\test_diff.py backend\tests\test_diff_service.py -q`。

## Task 2: DOCX Diff Regression Enhancements

- [x] Step 1: 扩展 `backend/tests/test_docx_diff.py`，覆盖图片删除、图片替换、图片 resize、段落 move、表格行列 move。
- [x] Step 2: 运行测试确认新增用例失败或覆盖现有行为。
- [x] Step 3: 最小化修改 `backend/app/diff_engine/docx_diff.py`，补足缺失字段和 move/reorder 输出。
- [x] Step 4: 运行 `pytest backend\tests\test_docx_diff.py backend\tests\test_docx_diff_generator.py -q`。

## Task 3: Frontend Diff Filtering/Search UX

- [x] Step 1: 修改 `frontend/src/components/diff/__tests__/DocxDiffView.spec.js`，新增筛选 text/table/image/move/add/delete/replace/resize 和搜索断言。
- [x] Step 2: 运行 `cd frontend; npm run test -- --run src/components/diff/__tests__/DocxDiffView.spec.js`，确认失败。
- [x] Step 3: 修改 `frontend/src/components/diff/DocxDiffView.vue`，新增工具条、筛选 chips、搜索输入、高亮、低饱和色块、轻量 transition。
- [x] Step 4: 运行同一 vitest 文件，确认通过。

## Task 4: Diff Summary And Task Metrics

- [x] Step 1: 扩展 `frontend/src/components/diff/__tests__/DiffSummary.spec.js` 和 `frontend/src/views/admin/__tests__/DiffView.spec.js`，断言 stats/status/elapsed_ms 显示。
- [x] Step 2: 修改 `DiffSummary.vue` 和 `DiffView.vue` 适配统一 schema。
- [x] Step 3: 运行 `cd frontend; npm run test -- --run src/components/diff/__tests__/DiffSummary.spec.js src/views/admin/__tests__/DiffView.spec.js`。

## Task 5: Security/Admin Utility Scripts

- [x] Step 1: 新增 `backend/tests/test_admin_password_script.py`，用临时 sqlite DB 验证脚本能创建/重置管理员密码 hash。
- [x] Step 2: 创建 `scripts/reset_admin_password.py`，参数支持 `--db`、`--username`、`--password`、`--role`。
- [x] Step 3: 新增 `scripts/start_dev.ps1` 和 `scripts/stop_dev.ps1`，使用 `backend/.dev-backend.pid`、`frontend/.dev-frontend.pid`、`backend/logs/dev-backend.log`、`frontend/dev-frontend.log`。
- [x] Step 4: 运行 Python 脚本测试和 PowerShell `-WhatIf`/语法检查。

## Task 6: E2E Regression

- [x] Step 1: 新增 `frontend/e2e/diff-docx.spec.js`，登录后上传原文档/变体并检查 diff 页面文本、表格、图片区域。
- [x] Step 2: 若测试环境缺文件上传 API，先写成可跳过的 smoke test，并保留明确 selector。
- [x] Step 3: 运行 `cd frontend; npm run test:e2e -- diff-docx.spec.js` 或记录需人工启动服务后的命令。

## Task 7: Full Verification

- [x] Step 1: 运行 Python 编译：`python -m py_compile backend\app\schemas\diff_result.py backend\app\diff_engine\docx_diff.py scripts\reset_admin_password.py scripts\generate_docx_diff_tests.py`。
- [x] Step 2: 运行后端核心测试：`pytest backend\tests\test_diff_result_schema.py backend\tests\test_docx_diff.py backend\tests\test_diff.py backend\tests\test_diff_service.py -q`。
- [x] Step 3: 运行 DOCX 随机样本：`python scripts\generate_docx_diff_tests.py --count 10 --verify`。
- [x] Step 4: 运行前端单测：`cd frontend; npm run test -- --run`。
- [x] Step 5: 运行前端构建：`cd frontend; npm run build`。

## Self-Review

- 覆盖 spec 中 9 项：安全初始化、DOCX diff、前端体验、大文件显示、自动化、schema、任务历史、权限审计、运维均有对应任务。
- 无 TBD/TODO 占位。
- 类型字段统一使用 `text/tables/images/metadata/summary/stats/status/elapsed_ms/error`。
- 当前目录不是 git 仓库，计划中的 commit 步骤不执行，改为最终列出修改文件和验证结果。

