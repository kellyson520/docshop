# DocShop Docker 单容器部署指南

本文档面向局域网、单台服务器和 VPS 的低占用部署。Docker 镜像内包含：

- Vue 前端静态资源
- FastAPI/Uvicorn 后端
- Nginx 反向代理
- SQLite 本地数据库
- LibreOffice + 中文/公式字体，用于 DOC/DOCX/XLS/XLSX 预览转 PDF（含公式渲染）

默认只有一个容器，数据挂载到宿主机 `./data`。

依赖清单详见 [`docs/dependencies.md`](docs/dependencies.md)，包含 Python、Node、LibreOffice、字体和系统包说明。

## 一、推荐配置

| 项目 | 最低 | 推荐 |
| --- | --- | --- |
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB，大文件预览建议 8 GB |
| 磁盘 | 10 GB | 按上传文件量扩容 |
| Docker | Docker Engine / Docker Desktop | Docker Compose v2 |

低占用默认：

```env
PREVIEW_IMAGE_MAX_WORKERS=1
UVICORN_WORKERS=1
DOCKER_MEMORY_LIMIT=2G
DOCKER_CPU_LIMIT=2.0
```

## 二、快速启动

### Windows PowerShell

```powershell
Copy-Item .env.example .env
# 可选：编辑 .env，设置 ADMIN_USERNAME / ADMIN_PASSWORD / DOCSHOP_PORT
.\scripts\docker-up.ps1 -Port 8080
```

### Linux/macOS

```bash
cp .env.example .env
# 可选：编辑 .env，设置 ADMIN_USERNAME / ADMIN_PASSWORD / DOCSHOP_PORT
./scripts/deploy.sh
```

或直接使用 Compose：

```bash
docker compose up -d --build docshop
```

访问地址：

- 本机：`http://127.0.0.1:8080/`
- 局域网：`http://服务器局域网IP:8080/`
- 健康检查：`http://127.0.0.1:8080/health`

端口由 `.env` 中的 `DOCSHOP_PORT` 控制。

## 三、环境变量重点说明

### SECRET_KEY

`.env.example` 默认：

```env
SECRET_KEY=auto
```

这会让容器每次启动自动生成临时密钥。优点是开箱即用；缺点是容器重启后旧登录 token/session 会失效，需要重新登录。

长期部署建议改为固定随机值：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

然后写入：

```env
SECRET_KEY=生成的随机值
```

### 管理员初始化

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=请替换为强密码
```

仅当账号不存在时创建，不覆盖已有密码。

### 上传大小

```env
MAX_FILE_SIZE=104857600
```

默认 100 MiB。Nginx 已同步配置 `client_max_body_size 100m`。

### MobileModels 本地缓存

```env
MOBILE_MODEL_SYNC_ENABLED=true
MOBILE_MODEL_SYNC_INTERVAL_HOURS=168
MOBILE_MODEL_SOURCE_URL=https://raw.githubusercontent.com/KHwang9883/MobileModels-csv/main/models.csv
MOBILE_MODEL_CACHE_DIR=/app/data/cache
MOBILE_MODEL_DOWNLOAD_TIMEOUT_SECONDS=15
MOBILE_MODEL_MAX_DOWNLOAD_BYTES=20971520
```

说明：

- 容器内缓存目录默认是 `/app/data/cache`，宿主机对应 `./data/cache`。
- 会生成 `mobile_models.csv`、`mobile_models.json`、`mobile_models.meta.json` 三个文件。
- 缓存缺失或过期时，请求链路只负责异步触发刷新；访问日志写入不会等待下载完成。
- 下载/解析失败时保留旧缓存继续使用；若没有任何缓存，则前端继续显示原始设备品牌/型号回退文案。
- 数据来源 `MobileModels-csv`，使用时需保留 `CC BY-NC-SA 4.0` 归属说明。

### 预览转换

```env
DOCX2PDF_TIMEOUT_SECONDS=300
PREVIEW_PDF_TIMEOUT_SECONDS=300
PREVIEW_IMAGE_MAX_WORKERS=1
```

Docker/Linux 容器内已经安装 LibreOffice、中文字体和公式字体：

- `libreoffice-writer`
- `libreoffice-calc`
- `libreoffice-math`
- `fonts-noto-cjk`
- `fonts-wqy-microhei`
- `fonts-wqy-zenhei`
- `fonts-opensymbol`
- `fonts-stix`
- `fonts-dejavu-core`
- `fontconfig`

如果 Word 文档里有公式，容器会通过 `libreoffice-math` 和 OpenSymbol/STIX/DejaVu 字体渲染公式，再由 PDF 转图片。若大 Word/Excel 预览失败，优先调大超时，低内存机器保持并发为 1。

## 四、构建加速

### 1. 基础镜像智能换源

推荐使用脚本构建。默认优先从候选镜像源中测速选择最快源，不先走 Docker Hub；只有设置 `DOCKER_BASE_MIRROR=off` 才会强制使用官方源：

```powershell
.\scripts\docker-build.ps1 -Up -Port 8080
```

Linux/VPS：

```bash
bash scripts/vps-build.sh --pull --up
```

也可以手动指定候选镜像源或固定镜像前缀：

```env
# 自动测速候选源，选择最快的一个
DOCKER_MIRROR_CANDIDATES=docker.m.daocloud.io/library,registry.cn-hangzhou.aliyuncs.com/library
DOCKER_MIRROR_TIMEOUT_SECONDS=2

# 或固定某个镜像前缀
DOCKER_BASE_MIRROR=docker.m.daocloud.io/library
DOCKER_BASE_MIRROR=registry.cn-hangzhou.aliyuncs.com/library  # 阿里云国内源
DOCKER_BASE_MIRROR=off  # 强制 Docker Hub 官方源
```

或直接指定完整基础镜像：

```env
NODE_IMAGE=docker.m.daocloud.io/library/node:18.20.8-alpine3.20
PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.11.11-slim-bookworm
# 阿里云示例：
NODE_IMAGE=registry.cn-hangzhou.aliyuncs.com/library/node:18.20.8-alpine3.20
PYTHON_IMAGE=registry.cn-hangzhou.aliyuncs.com/library/python:3.11.11-slim-bookworm
```

### 2. Debian apt / Python pip 加速

默认使用清华源：

```env
APT_MIRROR=http://mirrors.tuna.tsinghua.edu.cn/debian
APT_SECURITY_MIRROR=http://mirrors.tuna.tsinghua.edu.cn/debian-security
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
```

如果你在海外或访问官方源更快，可改为：

```env
APT_MIRROR=http://deb.debian.org/debian
APT_SECURITY_MIRROR=http://deb.debian.org/debian-security
PIP_INDEX_URL=https://pypi.org/simple
PIP_TRUSTED_HOST=
```

构建失败示例：

```text
ReadTimeoutError: HTTPSConnectionPool(host='files.pythonhosted.org', port=443): Read timed out
```

处理：保留或设置 `PIP_INDEX_URL`，然后重新构建：

```bash
docker compose build --no-cache docshop
docker compose up -d docshop
```

## 五、日常运维

### 查看状态

```bash
docker compose ps
docker compose logs --tail=200 docshop
docker compose logs -f docshop
```

Windows：

```powershell
.\scripts\docker-logs.ps1 -Tail 200
.\scripts\docker-logs.ps1 -Follow
```

### 健康检查

```bash
curl -fs http://127.0.0.1:8080/health
./scripts/health_check.sh
```

容器内检查预览依赖：

```bash
docker compose exec docshop soffice --headless --version
docker compose exec docshop fc-list | grep -i "noto\|wqy\|opensymbol\|stix\|dejavu" | head
```

### 停止/重启

```bash
docker compose restart docshop
docker compose down
```

Windows：

```powershell
.\scripts\docker-down.ps1
```

默认不会删除宿主机 `./data`。

## 六、数据目录与备份

默认挂载：

```text
宿主机 ./data -> 容器 /app/data
```

关键文件：

```text
./data/docshop.db       SQLite 数据库
./data/uploads/         上传文件
./data/covers/          封面/预览相关文件
./data/logs/            日志
./data/temp/            临时文件
```

最简单备份方式：停止服务后备份整个 `data` 目录。

Windows：

```powershell
Compress-Archive -Path .\data -DestinationPath .\backup-docshop-data.zip -Force
```

Linux：

```bash
tar -czf backup-docshop-data.tar.gz data
```

容器内备份脚本：

```bash
docker compose exec docshop /app/scripts/backup.sh
```

默认写入容器内 `/backup/docshop`。如需持久化到宿主机，可临时复制出来：

```bash
docker compose cp docshop:/backup/docshop ./backup
```

恢复脚本：

```bash
# 从默认备份目录恢复最近一次备份，执行前会确认
docker compose exec docshop /app/scripts/restore.sh

# 非交互恢复
docker compose exec -e RESTORE_ASSUME_YES=true docshop /app/scripts/restore.sh
```

恢复后建议：

```bash
docker compose restart docshop
```

## 七、旧版本兼容

如果旧数据目录中只有：

```text
data/docdist.db
```

或者旧布局中存在：

```text
backend/data/docshop.db
```

容器启动时会在 `data/docshop.db` 不存在的情况下自动复制迁移为 `docshop.db`。迁移只复制、不移动，并且不会覆盖已有的 `data/docshop.db`；升级前仍建议备份整个 `data` 目录。

## 八、常见问题

### 1. Word/Excel 预览失败

检查：

```bash
docker compose exec docshop soffice --headless --version
docker compose logs --tail=200 docshop
```

建议：

1. 保持 `PREVIEW_IMAGE_MAX_WORKERS=1`。
2. 调大 `DOCX2PDF_TIMEOUT_SECONDS=600`。
3. 确认文件不是损坏或加密文档。
4. 对特别大的文档，先手动另存为 PDF 后上传。

### 2. 局域网无法访问

检查：

```bash
docker compose ps
```

确认端口映射类似：

```text
0.0.0.0:8080->80/tcp
```

然后放行防火墙：

```bash
sudo ufw allow 8080/tcp
```

Windows 需要允许 Docker Desktop 或对应端口通过防火墙。

### 3. 端口占用

修改 `.env`：

```env
DOCSHOP_PORT=18080
```

重启：

```bash
docker compose up -d docshop
```

### 4. 构建阶段下载慢

优先确认 `.env` 中保留了 `APT_*` 和 `PIP_*` 镜像配置。必要时执行：

```bash
docker compose build --no-cache docshop
```

### 5. SECRET_KEY 改动后需要重新登录

这是正常行为。固定 `SECRET_KEY` 后后续重启不会再让 token 因密钥变化失效。
