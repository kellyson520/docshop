# Docker 部署加固设计（2026-06-15）

## 背景

当前 Docker 部署存在三个直接影响使用的问题：Linux 容器缺少 LibreOffice/中文字体导致 DOCX 转 PDF 失败；健康检查走 `/api/v1/health` 但 Nginx 没有代理根 `/health`；启动脚本把 Uvicorn 放到后台后直接 `exec nginx`，后端异常退出时容器不一定退出。

## 目标

- 单机 Docker Compose 一条命令部署前端、后端、Nginx。
- 数据持久化到宿主机 `./data`。
- 容器内支持 DOC/DOCX/XLS/XLSX 到 PDF 的 Linux 转换路径。
- 健康检查同时支持 `/health` 和 `/api/v1/health`。
- 启动脚本正确处理 Uvicorn/Nginx 子进程生命周期。
- 提供干净的 `.env.example`、部署文档和脚本。

## 方案

采用单容器部署，保留现有架构：前端构建产物由 Nginx 静态服务提供，`/api/` 与健康检查反向代理到容器内 `127.0.0.1:8000` 的 FastAPI。运行镜像安装 LibreOffice Writer/Calc、中文字体、fontconfig、poppler-utils 和 tini。

Compose 默认暴露宿主机 `8080`，避免占用/权限问题；容器内仍监听 `80`。SQLite、上传文件、日志和临时文件都放在 `/app/data`，由 `./data:/app/data` 持久化。

## 预览参数

默认使用保守参数：

- `DOCX2PDF_TIMEOUT_SECONDS=300`
- `PREVIEW_PDF_TIMEOUT_SECONDS=300`
- `PREVIEW_IMAGE_MAX_WORKERS=1`
- `UVICORN_WORKERS=1`

这样优先保证低配机器稳定，不让并发渲染拖死进度条。资源更强时可手动调高 worker。

## 验证

新增部署契约测试覆盖 Dockerfile、Compose、Nginx、启动脚本和 `.env.example` 的关键要求。实际部署验证使用：

```bash
python -m pytest backend/tests/test_docker_deployment_contract.py -q
docker compose config
docker compose build
docker compose up -d
docker compose exec docshop curl -fs http://localhost/health
```
