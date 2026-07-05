# Global Access Denied Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a global non-compliant access page for visitors without login or access token, and run the app on LAN.

**Architecture:** Keep the existing `accessGate.js` as the gate policy module, add `/access-denied` as a public route, and route unauthorized visitors there instead of `/login`. The page is a standalone Vue view with login/refresh/home actions.

**Tech Stack:** Vue 3, Vue Router, Vitest, Vite.

---

### Task 1: Gate Policy and Route

**Files:**
- Modify: `frontend/src/router/accessGate.js`
- Modify: `frontend/src/router/__tests__/accessGate.spec.js`
- Modify: `frontend/src/router/index.js`

- [ ] Add tests for `/access-denied` public access and target redirect behavior.
- [ ] Implement minimal access denied constants/helpers.
- [ ] Register `/access-denied` and use it for failed global gate.

### Task 2: Access Denied View

**Files:**
- Create: `frontend/src/views/AccessDenied.vue`

- [ ] Create a polished responsive non-compliant access page.
- [ ] Add login, refresh, and home actions.

### Task 3: Verification and LAN Startup

**Commands:**
- `npm run test -- src/router/__tests__/accessGate.spec.js --run`
- `npm run build`
- Start backend on `0.0.0.0:8000`.
- Start frontend on `0.0.0.0:5173`.
