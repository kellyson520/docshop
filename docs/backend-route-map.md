# Backend Route Map

更新时间：2026-06-30  
提取方式：`backend/app/main.py` 中的 FastAPI `app.routes`

> 用途：把当前后端请求入口按业务分组，方便前后端排查调用链、继续做 URL 收口和事件化改造。

## System

- `GET /health`
- `GET /info`
- `GET /api/v1/health`
- `GET /openapi.json`
- `GET /docs`
- `GET /docs/oauth2-redirect`
- `GET /redoc`

## Auth

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `GET /api/v1/auth/registration-policy`
- `GET /api/v1/auth/me`

## Settings

- `GET /api/v1/settings`
- `PUT /api/v1/settings`
- `POST /api/v1/settings/change-password`
- `GET /api/v1/settings/devices`
- `POST /api/v1/settings/devices/logout-all`
- `POST /api/v1/settings/avatar`

## Events

- `GET /api/v1/events/stream`

## Users / Admin

### User management

- `GET /api/v1/users`
- `POST /api/v1/users`
- `PUT /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`

### Registration policy

- `GET /api/v1/users/settings/registration`
- `PUT /api/v1/users/settings/registration`

### Admin-only views

- `GET /api/v1/admin/users`
- `GET /api/v1/admin/settings`
- `GET /api/v1/admin/logs`

## Projects

- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PUT /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/regenerate-token`
- `GET /api/v1/projects/{project_id}/stats`

### Project folders

- `GET /api/v1/projects/{project_id}/folders`
- `POST /api/v1/projects/{project_id}/folders`
- `PUT /api/v1/projects/{project_id}/folders/{folder_id}`
- `DELETE /api/v1/projects/{project_id}/folders/{folder_id}`
- `GET /api/v1/projects/{project_id}/folders/{folder_id}/download`

### Project files

- `POST /api/v1/projects/{project_id}/files`
- `GET /api/v1/projects/{project_id}/files`

## Files

### File entity / storage

- `GET /api/v1/files/{file_id}`
- `DELETE /api/v1/files/{file_id}`
- `PUT /api/v1/files/{file_id}/folder`
- `GET /api/v1/storage/stats`

### File versions

- `GET /api/v1/files/{file_id}/versions`
- `POST /api/v1/files/{file_id}/versions`
- `PUT /api/v1/files/{file_id}/versions/reorder`
- `DELETE /api/v1/files/{file_id}/versions/{version_id}`
- `GET /api/v1/files/{file_id}/versions/{version_id}/download`
- `GET /api/v1/files/{file_id}/versions/{version_id}/download/{format}`
- `GET /api/v1/files/{file_id}/versions/{version_id}/reconstruct`

### File analysis / preview

- `GET /api/v1/files/{file_id}/preview-status`
- `GET /api/v1/files/{file_id}/versions/{version_id}/preview-status`
- `GET /api/v1/files/{file_id}/analysis`
- `GET /api/v1/files/{file_id}/versions/{version_id}/analysis`
- `GET /api/v1/files/{file_id}/preview`
- `GET /api/v1/files/{file_id}/pages/{page_num}`
- `GET /api/v1/files/{file_id}/preview-assets/{asset_id}`
- `GET /api/v1/files/{file_id}/html`
- `GET /api/v1/files/{file_id}/text`
- `GET /api/v1/files/{file_id}/download`

### File metadata helpers

- `PUT /api/v1/files/{file_id}/version/{version_id}/category-tags`
- `PUT /api/v1/files/{file_id}/versions/{version_id}/category-tags`

### Admin preview maintenance

- `GET /api/v1/admin/files/previews`
- `POST /api/v1/admin/files/preconvert`
- `DELETE /api/v1/admin/files/{file_id}/preview-cache`
- `POST /api/v1/admin/files/preview-cache/cleanup`

## Diffs

- `POST /api/v1/diffs`
- `GET /api/v1/files/{file_id}/diffs`
- `GET /api/v1/files/{file_id}/diffs/{diff_id}`

## Cards

- `GET /api/v1/cards`
- `GET /api/v1/cards/categories`
- `GET /api/v1/cards/tags`
- `GET /api/v1/cards/{card_id}`
- `POST /api/v1/cards/{card_id}/cover`
- `PUT /api/v1/cards/{card_id}/info`
- `POST /api/v1/cards/{card_id}/versions/compare`
- `GET /api/v1/cards/rank/download`
- `GET /api/v1/cards/rank/visit`
- `POST /api/v1/cards/{card_id}/visit`
- `GET /api/v1/cards/{card_id}/download`
- `DELETE /api/v1/cards/{card_id}`

## Share / Public

### Public discovery

- `GET /api/v1/share/public-exams`
- `GET /api/v1/share/public-exams/{exam_id}`
- `GET /api/v1/share/public-projects`

### Share entry and file browsing

- `GET /api/v1/share/{share_token}`
- `GET /api/v1/share/{share_token}/files/{file_id}`
- `GET /api/v1/share/{share_token}/files/{file_id}/versions`
- `GET /api/v1/share/{share_token}/files/{file_id}/diffs`

### Share downloads / previews

- `GET /api/v1/share/{share_token}/folders/{folder_id}/download`
- `GET /api/v1/share/{share_token}/files/{file_id}/versions/{version_id}/download`
- `GET /api/v1/share/{share_token}/files/{file_id}/versions/{version_id}/download/{format}`
- `GET /api/v1/share/{share_token}/files/{file_id}/preview`
- `GET /api/v1/share/{share_token}/files/{file_id}/pages/{page_num}`
- `GET /api/v1/share/{share_token}/files/{file_id}/preview-assets/{asset_id}`
- `GET /api/v1/share/{share_token}/files/{file_id}/preview/pdf`

### Legacy share endpoints

- `POST /api/v1/shares`
- `GET /api/v1/shares/{share_token}`
- `DELETE /api/v1/shares/{share_token}`

## Share Tokens

- `GET /api/v1/share-tokens/policy`
- `PUT /api/v1/share-tokens/policy`
- `GET /api/v1/share-tokens`
- `POST /api/v1/share-tokens`
- `PUT /api/v1/share-tokens/{token_id}`
- `POST /api/v1/share-tokens/{token_id}/regenerate`
- `DELETE /api/v1/share-tokens/{token_id}`

## Tracking / Audit

### User-facing

- `GET /api/v1/tracking/config`
- `POST /api/v1/tracking/ping`

### Admin-facing

- `GET /api/v1/admin/tracking/config`
- `PUT /api/v1/admin/tracking/config`
- `GET /api/v1/admin/tracking/stats`
- `GET /api/v1/admin/tracking/logs`
- `GET /api/v1/admin/tracking/logs/{log_id}`
- `DELETE /api/v1/admin/tracking/logs`
- `GET /api/v1/admin/tracking/sessions`
- `GET /api/v1/admin/tracking/realtime`

## Announcements / Notices / Exams

### Announcements

- `GET /api/v1/announcements/active`
- `GET /api/v1/announcements`
- `POST /api/v1/announcements`
- `PUT /api/v1/announcements/{announcement_id}`
- `DELETE /api/v1/announcements/{announcement_id}`

### Notices

- `GET /api/v1/notices`
- `PUT /api/v1/notices/{notice_id}/read`
- `PUT /api/v1/notices/read-all`

### Exams

- `GET /api/v1/exams`
- `POST /api/v1/exams`
- `GET /api/v1/exams/upcoming`
- `POST /api/v1/exams/{exam_id}/dismiss`
- `GET /api/v1/exams/{exam_id}`
- `PUT /api/v1/exams/{exam_id}`
- `DELETE /api/v1/exams/{exam_id}`

## Access Tokens

- `GET /api/v1/access-tokens/validate`
- `POST /api/v1/access-tokens/validate`
- `GET /api/v1/access-tokens`
- `POST /api/v1/access-tokens`
- `GET /api/v1/access-tokens/{token_id}`
- `PUT /api/v1/access-tokens/{token_id}`
- `DELETE /api/v1/access-tokens/{token_id}`

## Taxonomy

- `GET /api/v1/categories`
- `POST /api/v1/categories`
- `PUT /api/v1/categories/{cat_id}`
- `DELETE /api/v1/categories/{cat_id}`
- `GET /api/v1/tags`
- `POST /api/v1/tags`
- `PUT /api/v1/tags/{tag_id}`

## Static Assets

- `MOUNT /api/v1/covers`
- `MOUNT /api/v1/avatars`

## Notes

- `/api/v1/events/stream` 是本次统一事件通道入口。
- `/api/v1/covers`、`/api/v1/avatars` 是前端资源 URL 收口后的静态资源挂载点。
- 浏览器直连资源路径建议统一通过 `frontend/src/utils/resourceUrl.js` 生成，XHR/API 调用继续走 `src/api/*`。
