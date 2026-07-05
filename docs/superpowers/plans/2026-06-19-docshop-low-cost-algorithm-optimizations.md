# DocShop Low-Cost Algorithm Optimizations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add low-cost ranking algorithms for preview jobs, preview cache cleanup, and project/file search relevance.

**Architecture:** Implement pure algorithm modules first, cover them with focused tests, then wire the algorithms into existing preview queue, preview admin cleanup, and project listing code. Avoid new infrastructure and keep all fallbacks safe.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, pytest, existing in-process preview queue and document_store cache layout.

---

## File Structure

- Create `backend/app/services/preview_scheduler.py`: pure preview job priority scoring and sorting helpers.
- Create `backend/app/services/preview_cache_policy.py`: pure cache cleanup candidate scoring plus safe cleanup executor.
- Create `backend/app/services/search_ranker.py`: pure lightweight search scoring helpers.
- Modify `backend/app/services/preview_queue.py`: call scheduler before popping next preview job.
- Modify `backend/app/routers/files.py`: enhance admin cleanup endpoint with policy-based cleanup and summary fields.
- Modify `backend/app/routers/projects.py`: use search ranker when `keyword` is present in project listing.
- Create tests:
  - `backend/tests/test_preview_scheduler.py`
  - `backend/tests/test_preview_cache_policy.py`
  - `backend/tests/test_search_ranker.py`

## Task 1: Preview job scheduler

**Files:**
- Create: `backend/app/services/preview_scheduler.py`
- Modify: `backend/app/services/preview_queue.py`
- Test: `backend/tests/test_preview_scheduler.py`

- [ ] Write failing tests for smaller files, newer files, failure penalty, and same-project fairness.
- [ ] Run `python -m pytest tests/test_preview_scheduler.py -q --no-cov` and confirm failure.
- [ ] Implement `PreviewJobContext`, `score_preview_job`, and `sort_preview_jobs`.
- [ ] Wire queue pop to sort by scheduler before popping.
- [ ] Run `python -m pytest tests/test_preview_scheduler.py tests/test_preview_queue.py -q --no-cov`.

## Task 2: Preview cache cleanup policy

**Files:**
- Create: `backend/app/services/preview_cache_policy.py`
- Modify: `backend/app/routers/files.py`
- Test: `backend/tests/test_preview_cache_policy.py`

- [ ] Write failing tests for cleanup score ordering and safe path guard.
- [ ] Run `python -m pytest tests/test_preview_cache_policy.py -q --no-cov` and confirm failure.
- [ ] Implement `PreviewCacheCandidate`, `score_cleanup_candidate`, `sort_cleanup_candidates`, and `is_safe_cache_path`.
- [ ] Extend admin preview cleanup summary with policy-selected candidates while preserving existing behavior.
- [ ] Run `python -m pytest tests/test_preview_cache_policy.py tests/test_admin_preview_management.py -q --no-cov`.

## Task 3: Search ranker

**Files:**
- Create: `backend/app/services/search_ranker.py`
- Modify: `backend/app/routers/projects.py`
- Test: `backend/tests/test_search_ranker.py`

- [ ] Write failing tests for exact/prefix/contains/display/tag/category scoring and stable ordering.
- [ ] Run `python -m pytest tests/test_search_ranker.py -q --no-cov` and confirm failure.
- [ ] Implement `score_search_item` and `rank_search_items`.
- [ ] Use ranker in project listing when keyword exists, after DB filtering but before pagination for ranked results.
- [ ] Run `python -m pytest tests/test_search_ranker.py tests/test_projects.py tests/test_projects_extended.py -q --no-cov`.

## Task 4: Final verification

- [ ] Run `python -m compileall app -q`.
- [ ] Run `python -m pytest tests/test_preview_scheduler.py tests/test_preview_cache_policy.py tests/test_search_ranker.py tests/test_admin_preview_management.py tests/test_preview_queue.py tests/test_projects.py tests/test_runtime_text_quality.py -q --no-cov`.
- [ ] Report changed files and verification output.
