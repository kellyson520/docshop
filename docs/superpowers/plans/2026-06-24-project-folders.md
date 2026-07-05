# Project Folder Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow project files to be organized into lightweight folders, with create/rename/delete folder and move-file operations.

**Architecture:** Store folder metadata in the database and link files by nullable `folder_id`. Do not move physical files on disk so preview, diff, download, and share remain compatible.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite-compatible schema migration, Vue 3, Element Plus, Vitest/Pytest.

---

## Tasks

1. Add backend model `ProjectFolder` and nullable `DocumentFile.folder_id`.
2. Add startup migration compatibility for existing SQLite databases.
3. Add folder CRUD endpoints under `/api/v1/projects/{project_id}/folders`.
4. Add file move endpoint `PUT /api/v1/files/{file_id}/folder`.
5. Include `folder_id` in project file payloads and upload creation.
6. Add frontend project API helpers.
7. Update `ProjectDetail.vue` with folder toolbar, folder cards, breadcrumb, filtered files, move dialog, and upload-to-current-folder.
8. Add regression tests and run backend/frontend verification.
