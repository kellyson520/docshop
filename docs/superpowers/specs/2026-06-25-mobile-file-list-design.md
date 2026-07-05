# Mobile File List Design

## Goal

Make DocShop file lists usable on phones without horizontal scrolling while keeping the current dense desktop table experience.

## Scope

- Share project file list: `frontend/src/views/share/ShareProject.vue`
- Admin project file list: `frontend/src/views/admin/ProjectDetail.vue`
- Reusable mobile card list component for file records
- Keep desktop/tablet table layout unchanged

## Chosen Approach

Use responsive split rendering:

- `desktop/tablet`: continue using `el-table`
- `mobile (<768px)`: switch to stacked file cards

This avoids right-swipe-only interaction on phones and matches mature file/productivity UI patterns.

## Mobile Card Structure

Each card shows:

1. file icon + file name
2. type/version/status badges
3. update time and summary metadata
4. compact action row

Admin cards additionally show preview status and expose the same actions as the table menu through compact buttons.

## Reusable Component

Create a shared presentational component with slots so share/admin can reuse layout but keep different metadata/actions:

- `frontend/src/components/file/FileListCards.vue`

Slots:

- `badges`
- `meta`
- `summary`
- `actions`

## Styling Direction

- enterprise / mature / touch-friendly
- rounded cards
- strong title hierarchy
- subdued secondary metadata
- horizontally wrapping badges
- larger tap targets for primary actions

## Validation

Add failing tests first for:

- share page renders mobile card list
- admin page renders mobile card list and key actions

Then implement and run targeted frontend tests.
