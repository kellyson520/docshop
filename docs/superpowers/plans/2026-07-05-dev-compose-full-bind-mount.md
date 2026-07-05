# Dev Docker Compose Full Bind Mount Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **User constraint:** 只改开发版 compose，默认挂载整个项目目录，避免后续改代码频繁重建。

**Goal:** 让 `docker-compose.dev.yml` 默认把整个项目根目录挂载进开发容器，使前后端改代码/配置后无需重复构建镜像。

**Architecture:** `backend` 与 `frontend` 都统一挂载项目根目录到容器内同一路径，后端从挂载后的 `backend/` 目录直接启动热重载；前端保留独立 `node_modules` volume，并在容器启动时从镜像内预装依赖自动补种到挂载目录，避免全量挂载把依赖覆盖掉。

**Tech Stack:** Docker Compose, bind mounts, named volume, Vite, Uvicorn.

---

## Progress Update (2026-07-05 19:10)

- [ ] 修改 `docker-compose.dev.yml` 为根目录全量挂载
- [ ] 验证 `docker compose -f docker-compose.dev.yml config` 通过
- [ ] 记录新的启动行为与注意事项
