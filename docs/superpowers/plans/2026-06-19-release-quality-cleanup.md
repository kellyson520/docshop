# DocShop Release Quality Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理发布版中剩余乱码和生产日志噪音，并增加质量守卫，避免回退。

**Architecture:** 用轻量静态质量测试守住 README、关键后端注释/文本、前端 API client 的生产日志边界；实现上只做低风险文本和日志封装修复，不改业务数据流。

**Tech Stack:** Python pytest、Vue/Vite/Vitest、PowerShell。

---

### Task 1: 文档和后端文本质量守卫

**Files:**
- Modify: `backend/tests/test_runtime_text_quality.py`
- Modify: `README.md`
- Modify: `backend/app/routers/files.py`

- [ ] Step 1: 在 `backend/tests/test_runtime_text_quality.py` 增加 README 和 files.py 的乱码检查，禁止新增 `????`、常见 mojibake。
- [ ] Step 2: 运行 `python -m pytest tests/test_runtime_text_quality.py -q --no-cov`，预期先失败，指向 README/files.py。
- [ ] Step 3: 重写 README Docker 热更新章节为正常中文，修复 files.py 注释中的乱码。
- [ ] Step 4: 再运行同一 pytest，预期通过。

### Task 2: 前端 API 日志生产环境收敛

**Files:**
- Modify: `frontend/src/api/client.js`
- Modify: `frontend/src/api/__tests__/client.spec.js`

- [ ] Step 1: 在 client 单测里增加静态断言：`client.js` 不允许裸 `console.log`，只能通过 debug helper 输出。
- [ ] Step 2: 运行 `npm run test -- --run src/api/__tests__/client.spec.js`，预期先失败。
- [ ] Step 3: 在 `client.js` 增加 `debugLog/debugWarn/debugError`，请求/响应/取消日志统一走 debug helper；生产默认不输出。
- [ ] Step 4: 再运行同一 Vitest，预期通过。

### Task 3: 最终验证

**Files:**
- No direct file changes.

- [ ] Step 1: 后端运行 `python -m compileall app -q`。
- [ ] Step 2: 后端运行 `python -m pytest tests/test_runtime_text_quality.py -q --no-cov`。
- [ ] Step 3: 前端运行 `npm run test -- --run src/api/__tests__/client.spec.js`。
- [ ] Step 4: 前端运行 `npm run build`。
- [ ] Step 5: 汇总 diff 和验证结果。
