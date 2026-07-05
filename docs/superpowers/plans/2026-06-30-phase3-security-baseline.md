# Phase 3 Security Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. User override: work directly on `master`; do not commit, push, reset, clean, or otherwise mutate git history.

**Goal:** Land the first Phase 3 hardening baseline: route-tiered rate limiting, tighter preview/security headers, preview error redaction, and an explicit frontend production sourcemap-off contract.

**Architecture:** Keep the change additive and low-risk. Backend hardening stays centralized in middleware plus a tiny preview error-redaction adjustment in resource routers; frontend exposure shrink is an explicit Vite build contract. The slice does not change existing permission semantics or the SSE/resource URL protocol.

**Tech Stack:** FastAPI / Starlette middleware, pytest, Vite.

---

## File Structure

### Backend modify
- `backend/app/config.py`
  - Optional route-tier limit settings for auth, share unlock, preview, and download traffic.
- `backend/app/middlewares/rate_limit.py`
  - Add per-route policy selection, scoped keys, per-policy counters, and policy-specific headers.
- `backend/app/middlewares/security_headers.py`
  - Tighten CSP/sandbox/robots/cross-origin headers and HTML preview cache policy.
- `backend/app/routers/files.py`
  - Redact preview conversion failures.
- `backend/app/routers/share.py`
  - Redact shared preview conversion failures.
- `backend/tests/test_config.py`
  - Cover new route-tier settings parsing.
- `backend/tests/test_rate_limit.py`
  - Cover route policy selection and scoped limit keys.
- `backend/tests/test_security_headers.py`
  - Cover preview sandbox/no-store and global anti-index/cross-origin headers.
- `backend/tests/test_files.py`
  - Cover preview failure redaction.

### Frontend modify
- `frontend/vite.config.js`
  - Make production `sourcemap: false` explicit.
- `backend/tests/test_docker_deployment_contract.py` or a focused contract test
  - Lock the explicit sourcemap-off contract if needed.

---

## Tasks

### Task 1: Route-tier rate limiting
- [ ] Add failing tests for login/share-unlock/preview/download policy selection and scoped keys.
- [ ] Implement additive settings + middleware policy selection.
- [ ] Verify focused rate-limit tests pass.

### Task 2: Preview/security headers baseline
- [ ] Add failing tests for preview sandbox/no-store plus anti-index/cross-origin headers.
- [ ] Tighten `security_headers.py`.
- [ ] Verify focused security-header tests pass.

### Task 3: Preview error redaction
- [ ] Add failing regression test proving preview 500s do not echo raw exception text.
- [ ] Redact file/share preview conversion errors while logging internally.
- [ ] Verify focused file/share tests pass.

### Task 4: Production build exposure contract
- [ ] Make Vite `sourcemap: false` explicit.
- [ ] Add/adjust a lightweight contract test if needed.
- [ ] Run focused backend/frontend verification.
