# Exam Custom Segmented Reminders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让考试提醒支持考试开始前任意多个自定义时间点，并兼容原来的 15 分钟、5 分钟、开始时提醒。

**Architecture:** 在 ExamSchedule 上新增 JSON 字符串字段 `reminder_offsets_minutes` 存储分钟偏移数组；后端用 helper 规范化、兼容旧字段、生成对应 ExamReminder；前端在考试弹窗中用 tag/预设按钮维护数组并随创建/编辑提交。

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic，Vue 3 + Element Plus + Vitest，pytest。

---

### Task 1: 后端分段提醒数据与兼容

**Files:**
- Modify: `backend/app/models/exam_schedule.py`
- Modify: `backend/app/schemas/exam.py`
- Modify: `backend/app/routers/exams.py`
- Modify: `backend/app/database.py` 或已有 additive migration 位置
- Test: `backend/tests/test_exams.py` 或 `backend/tests/test_exam_model.py`

- [ ] Step 1: 写失败测试：创建考试传 `reminder_offsets_minutes: [1440, 120, 30, 10, 0]`，响应和详情返回同数组。
- [ ] Step 2: 写失败测试：旧字段 `reminder_15min=1, reminder_5min=1, reminder_start=1` 且无新字段时返回 `[15, 5, 0]`。
- [ ] Step 3: 写失败测试：`/exams/upcoming` 在考试前 30 分钟窗口返回 `before_30` 类型提醒，未到 10 分钟时不返回 `before_10`。
- [ ] Step 4: 实现字段、schema 校验、helper、迁移补列、创建/更新提醒重建。
- [ ] Step 5: 运行相关 pytest，确认通过。

### Task 2: 前端考试弹窗自定义提醒 UI

**Files:**
- Modify: `frontend/src/components/exam/ExamDialog.vue`
- Modify: `frontend/src/stores/exam.js` if payload normalization exists there
- Test: existing `frontend/src/components` or `frontend/src/stores` tests; if no mount test exists, add static regression in `frontend/src/utils/__tests__/frontend-regressions.spec.js`

- [ ] Step 1: 写失败测试：ExamDialog 源码包含 `reminder_offsets_minutes`、预设提醒、添加自定义提醒、删除提醒、排序去重逻辑。
- [ ] Step 2: 实现 UI：预设按钮 5/10/15/30/60/120/1440，开始时 0，自定义数字+单位分钟/小时/天。
- [ ] Step 3: 提交 payload 时包含 `reminder_offsets_minutes`，同时映射旧字段保证兼容。
- [ ] Step 4: 运行前端相关 Vitest。

### Task 3: 最终验证

**Files:**
- No direct file changes.

- [ ] Step 1: 后端运行 `python -m compileall app -q`。
- [ ] Step 2: 后端运行相关考试 pytest。
- [ ] Step 3: 前端运行相关 Vitest。
- [ ] Step 4: 前端运行 `npm run build`。
- [ ] Step 5: 汇总变更和验证结果。
