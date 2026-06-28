# Project Detail Resource Explorer And Preview Design

## Goal

Improve the admin project detail page so resource browsing feels closer to Windows Explorer and rich document preview feels more readable.

## Scope

- `frontend/src/views/admin/ProjectDetail.vue`
- `frontend/src/views/admin/__tests__/ProjectDetail.spec.js`
- Preview-specific tests if current coverage is split elsewhere
- Desktop and mobile resource listing consistency for folders/files inside the same data model

## Problem Summary

Current behavior has three usability issues:

1. DOC and PDF preview content appears too large in the preview dialog.
2. The HTML preview skeleton title is not being preserved in the intended visual hierarchy.
3. Desktop folders are rendered in a separate card strip above the file table instead of living in the same list as files, which increases scanning and operation cost.

## Chosen Approach

Use a unified resource-explorer layout:

- render folders and files in the same desktop table
- keep folders as normal rows, but sort them before files
- preserve breadcrumb navigation for path context only
- apply one preview scaling strategy for DOC and PDF because both are ultimately rendered through image-based HTML skeleton content
- keep the preview skeleton title, center it, and strengthen it visually

This best matches the user’s preferred Windows-style mental model while keeping the current project detail page architecture intact.

## Resource List Design

### Unified Table Data

Desktop should stop rendering a dedicated folder card section. Instead, it should render one mixed resource list sourced from the same `resourceItems` concept already used by the mobile card view.

Each row is either:

- a navigation row (`..`) when inside a folder
- a folder row
- a file row

### Ordering Rules

Within the current directory scope, rows should be ordered as:

1. parent navigation row (`..`) if not at root
2. folders
3. files

Existing search/filter behavior should continue to work, but display order must still prioritize folders before files.

### Folder Rows

Folder rows should look like ordinary table rows instead of standalone cards.

They should show:

- folder icon
- folder name
- type label as `文件夹`
- lightweight metadata such as file count if available

They should not show file-only preview/version/status fields. Those cells should either render a folder-specific placeholder or stay intentionally simplified.

Folder row actions should be limited to:

- open
- rename
- delete

### File Rows

File rows keep the current document-centric behavior:

- preview status
- version badge
- share action
- metadata/settings action
- more menu operations

### Breadcrumb Role

The breadcrumb stays above the table, but only as location context and quick navigation. It no longer acts as the main visual presentation for folders.

## Preview Dialog Design

### Scaling Strategy

DOC and PDF should share one preview scaling treatment because both are represented through converted page images inside HTML skeleton content.

The dialog should shift from an oversized fill-first presentation to a centered document-reading presentation:

- reduce effective preview scale
- constrain visible content width
- preserve comfortable top/bottom spacing
- avoid over-zooming on large screens

### Skeleton Title

The HTML skeleton title must be preserved inside the preview content rather than removed or visually hidden.

Required presentation:

- centered
- bold
- strong document title hierarchy
- visually similar to `汽车服务 - protable.docx • v3`

The title should remain clearly separated from page imagery/body content so the first screen reads like a document cover rather than a stretched canvas.

### Consistency

The title treatment should be the same for DOC and PDF preview modes wherever the HTML skeleton is used.

## Interaction Notes

- Opening a folder should continue to update current folder context and route state.
- Returning to root or parent should remain one-click.
- Empty-folder state should clearly indicate that the directory is empty, not that loading failed.
- Mobile should remain aligned with the same resource model so desktop and mobile do not drift in behavior.

## Testing Strategy

Add or update targeted tests for:

1. desktop mixed resource rendering includes folders in the same table flow as files
2. folders are ordered before files
3. folder rows expose folder actions instead of file preview actions
4. preview title text is preserved in the rendered preview dialog title/skeleton path
5. preview container uses the reduced shared scaling treatment for DOC/PDF paths

Prefer targeted component tests over broad snapshot-only assertions.

## Out of Scope

- redesigning backend folder APIs
- changing project search semantics beyond display ordering
- introducing drag-and-drop file manager interactions
- rewriting the preview generation pipeline

## Implementation Notes

Likely implementation path:

1. refactor desktop table data source from file-only rows to mixed resource rows
2. branch table-cell rendering by row type (`parent`, `folder`, `file`)
3. remove the standalone desktop folder-card block
4. tighten preview container sizing and skeleton title styling
5. update tests for mixed list and preview presentation contracts

## Validation

Implementation will be accepted when:

- desktop no longer shows folders as separate cards above the table
- folders and files appear in a single Windows-like list with folders first
- DOC/PDF preview is visibly less oversized
- HTML skeleton title remains present, centered, and bold
- targeted frontend tests cover the new rendering rules
