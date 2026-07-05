# DocShop Animation Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve DocShop frontend motion with low-cost CSS/Vue transitions, better page changes, smoother controls, and reduced-motion safety.

**Architecture:** Keep animation mostly CSS-only via `frontend/src/style.css` and Vue `<transition>` wrappers in route/layout entry points. Avoid adding runtime animation dependencies; use transform/opacity and scoped Element Plus selectors for performance.

**Tech Stack:** Vue 3, Vue Router, Element Plus, CSS transitions/keyframes, Vitest source regression tests.

---

### Task 1: Add animation regression tests

**Files:**
- Modify: `frontend/src/utils/__tests__/frontend-regressions.spec.js`

- [ ] Add tests asserting route transitions exist in `App.vue` and `ResponsiveLayout.vue`.
- [ ] Add tests asserting global motion CSS covers Element Plus overlays, tables, progress, loading, and reduced motion.
- [ ] Run `npm test -- frontend/src/utils/__tests__/frontend-regressions.spec.js --run` and confirm the new tests fail before implementation.

### Task 2: Implement route and layout transitions

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/layouts/ResponsiveLayout.vue`
- Modify: `frontend/src/layouts/PublicLayout.vue`

- [ ] Wrap top-level routed components with `docshop-route` transition.
- [ ] Add `mode="out-in"` and `appear` to internal layout transitions.
- [ ] Keep existing `keep-alive` behavior for high-traffic views.

### Task 3: Expand low-cost global motion system

**Files:**
- Modify: `frontend/src/style.css`

- [ ] Add `--motion-ui-slow`, `--motion-ui-soft`, and spring-like easing variables.
- [ ] Add `docshop-route`, `docshop-pop`, `docshop-breathe`, and refined `fade-slide` transition classes.
- [ ] Add Element Plus overlay, dialog, drawer, table, progress, skeleton, upload, and loading transitions using transform/opacity/color/shadow only.
- [ ] Keep `prefers-reduced-motion` override authoritative.

### Task 4: Remove layout-heavy transition patterns from key components

**Files:**
- Modify selected Vue files containing `transition: all` in common card/filter/share/login/notice components.

- [ ] Replace `transition: all` with explicit property lists.
- [ ] Preserve visual intent while avoiding layout-heavy animation.

### Task 5: Verify

**Files:**
- Test: `frontend/src/utils/__tests__/frontend-regressions.spec.js`

- [ ] Run focused regression test.
- [ ] Run frontend build.
- [ ] Report changed files and verification output.
