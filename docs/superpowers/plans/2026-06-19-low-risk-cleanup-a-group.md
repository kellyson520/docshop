# DocShop Low-Risk Cleanup A Group Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理残留乱码、补齐前端 ObjectURL/timer 资源释放守卫，提升发布质量和长时间运行稳定性。

**Architecture:** 先用静态回归测试锁定问题，再做最小修改；不重构业务流程，不改变接口协议。文案质量由 pytest 守卫，前端资源释放由 Vitest 静态守卫和现有构建验证。

**Tech Stack:** Python pytest、Vue/Vite/Vitest、PowerShell。

---

### Task 1: 乱码清理范围扩展

**Files:**
- Modify: `backend/tests/test_runtime_text_quality.py`
- Modify: `backend/load_tests/locustfile.py`
- Modify: `backend/scripts/migrate_add_card_fields.py`
- Modify: `backend/scripts/migrate_add_exam_tables.py`
- Modify: `scripts/reset_admin_password.py`
- Modify: `docs/ui-ux-audit-2026-06-11.md`

- [ ] Step 1: 扩展文本质量测试，覆盖脚本、压测和 UI/UX 审计文档。
- [ ] Step 2: 运行 `python -m pytest tests/test_runtime_text_quality.py -q --no-cov`，预期失败并列出乱码文件。
- [ ] Step 3: 将脚本头部说明、错误提示、命令帮助、审计文档改为正常中文。
- [ ] Step 4: 再运行同一 pytest，预期通过。

### Task 2: 前端资源释放守卫

**Files:**
- Modify: `frontend/src/utils/__tests__/frontend-regressions.spec.js`
- Modify: `frontend/src/views/CardDetail.vue`
- Modify: `frontend/src/utils/index.js`
- Modify: `frontend/src/views/HomePage.vue`

- [ ] Step 1: 增加静态测试，要求 `createObjectURL` 相关文件同时调用 `revokeObjectURL`，并要求 HomePage 的 timer 在卸载时清理。
- [ ] Step 2: 运行 `npm run test -- --run src/utils/__tests__/frontend-regressions.spec.js`，预期先失败。
- [ ] Step 3: 修复缺失的 revokeObjectURL 和 clearTimeout/onUnmounted 清理。
- [ ] Step 4: 再运行同一 Vitest，预期通过。

### Task 3: 最终验证

**Files:**
- No direct file changes.

- [ ] Step 1: 后端运行 `python -m compileall app -q`。
- [ ] Step 2: 后端运行 `python -m pytest tests/test_runtime_text_quality.py -q --no-cov`。
- [ ] Step 3: 前端运行 `npm run test -- --run src/utils/__tests__/frontend-regressions.spec.js`。
- [ ] Step 4: 前端运行 `npm run build`。
- [ ] Step 5: 输出改动摘要和验证结果。
