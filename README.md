# DocShop

DocShop 是一个文档管理、预览、版本对比与分享系统。后端使用 **FastAPI + SQLAlchemy**，前端使用 **Vue 3 + Vite + Element Plus**。生产环境推荐使用 **Docker Compose 单容器部署**，也支持 Windows/Linux 本地部署。

## 功能概览

- 文档上传、分类、版本管理与分享
- PDF/DOC/DOCX/XLS/XLSX 预览生成
- 文档版本差异对比
- 管理员后台、用户管理、密码修改
- 访问统计、分享访问控制
- Docker 单容器部署，内置 Nginx、FastAPI、前端静态资源和 LibreOffice

## 目录结构

```text
.
├── backend/                 # FastAPI 后端
├── frontend/                # Vue 3 前端
├── data/                    # Docker/本地默认持久化目录
├── docs/                    # 部署、依赖、设计文档
├── scripts/                 # 部署和诊断脚本
├── Dockerfile               # 生产镜像
├── docker-compose.yml       # Docker Compose 部署
├── .env.example             # 环境变量模板
└── README.md
```

## 推荐配置

| 项目 | 最低要求 | 推荐 |
| --- | --- | --- |
| CPU | 2 核 | 4 核以上 |
| 内存 | 2 GB | 4 GB 以上，文档较大建议 8 GB |
| 磁盘 | 10 GB | 视上传文件量扩容 |
| Docker | Docker Engine / Docker Desktop | Docker Compose v2 |
| Python 本地部署 | Python 3.11+ | Python 3.11/3.12 |
| Node 本地部署 | Node.js 18+ | Node.js 20 LTS |

> 说明：Docker 镜像内置 LibreOffice、中文字体和公式字体，Linux/Docker 下无需安装 Microsoft Word。Windows 本地部署如安装 Microsoft Word，会优先尝试 Word COM 转换以获得更高保真度。

## Docker 快速启动

详细说明见 [`docs/docker-deployment.md`](docs/docker-deployment.md)。

Windows PowerShell：

```powershell
Copy-Item .env.example .env
.\scripts\docker-up.ps1 -Port 8080
```

Linux/macOS：

```bash
cp .env.example .env
./scripts/deploy.sh
```

访问：`http://127.0.0.1:8080/`，局域网访问使用 `http://服务器局域网IP:8080/`。

Docker 镜像内置 LibreOffice、中文字体与公式字体，支持 Linux 容器内 Word/Excel 预览转 PDF，含 Word 公式渲染。默认低占用配置为 `UVICORN_WORKERS=1`、`PREVIEW_IMAGE_MAX_WORKERS=1`。

---

# 一、Docker Compose 部署（Windows / Linux 通用，推荐）

Docker 部署会把前端、后端、Nginx、LibreOffice 打包到同一个容器中，数据默认持久化到宿主机 `./data`。

## 1. 安装 Docker

### Windows

1. 安装 Docker Desktop for Windows。
2. 启用 WSL2 backend。
3. 打开 PowerShell，确认命令可用：

```powershell
docker --version
docker compose version
```

### Linux（Ubuntu/Debian 示例）

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker

docker --version
docker compose version
```

如需让当前用户免 `sudo` 执行 Docker：

```bash
sudo usermod -aG docker $USER
# 退出 SSH/终端后重新登录生效
```

## 2. 准备环境变量

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

默认 `.env` 中 `SECRET_KEY=auto`。Docker 容器每次启动时会自动生成新的随机密钥。

### Linux/macOS Shell

```bash
cp .env.example .env
```

默认 `.env` 中 `SECRET_KEY=auto`。Docker 容器每次启动时会自动生成新的随机密钥。

> 注意：自动随机密钥会让容器重启前签发的登录 token/session 失效，用户需要重新登录。若希望重启后保持登录状态，把 `.env` 中 `SECRET_KEY=auto` 改为固定随机值，例如 `python -c "import secrets; print(secrets.token_hex(32))"` 生成的值。

常用 `.env` 配置：

```env
SECRET_KEY=auto
DOCSHOP_PORT=8080
DOCSHOP_IMAGE=docshop:latest
DATABASE_URL=sqlite:////app/data/docshop.db
UPLOAD_DIR=/app/data/uploads
LOG_DIR=/app/data/logs
TEMP_DIR=/app/data/temp
MAX_FILE_SIZE=104857600
CORS_ORIGINS=*
DOCX2PDF_TIMEOUT_SECONDS=300
PREVIEW_PDF_TIMEOUT_SECONDS=300
PREVIEW_IMAGE_MAX_WORKERS=1
UVICORN_WORKERS=1
ADMIN_USERNAME=admin
ADMIN_PASSWORD=请替换为强密码
APT_MIRROR=http://mirrors.tuna.tsinghua.edu.cn/debian
APT_SECURITY_MIRROR=http://mirrors.tuna.tsinghua.edu.cn/debian-security
```

> `ADMIN_USERNAME` / `ADMIN_PASSWORD` 可选。仅在账号不存在时创建，不会覆盖已有管理员密码。

### MobileModels 本地缓存（访问日志手机型号映射）

```env
MOBILE_MODEL_SYNC_ENABLED=true
MOBILE_MODEL_SYNC_INTERVAL_HOURS=168
MOBILE_MODEL_SOURCE_URL=https://raw.githubusercontent.com/KHwang9883/MobileModels-csv/main/models.csv
MOBILE_MODEL_CACHE_DIR=/app/data/cache
MOBILE_MODEL_DOWNLOAD_TIMEOUT_SECONDS=15
MOBILE_MODEL_MAX_DOWNLOAD_BYTES=20971520
```

说明：

- 访问日志会优先展示解析后的 `device_display_name`，例如 `Huawei P40 / ANA-AL00`。
- 缓存文件保存在 `/app/data/cache`（宿主机对应 `./data/cache`），包括：`mobile_models.csv`、`mobile_models.json`、`mobile_models.meta.json`。
- 首次无缓存或缓存过期时，后端会在后台触发刷新，不阻塞正常请求。
- 刷新失败时继续使用旧缓存；如果本地完全无缓存，则回退为原有设备名展示逻辑。
- 数据来源：`MobileModels-csv`，授权协议 `CC BY-NC-SA 4.0`。

> `DOCKER_BASE_MIRROR` 用于基础镜像智能换源；留空时默认不先走 Docker Hub，而是按 `DOCKER_MIRROR_CANDIDATES` 候选列表测速并选择最快源（默认 `docker.m.daocloud.io/library,registry.cn-hangzhou.aliyuncs.com/library`，超时由 `DOCKER_MIRROR_TIMEOUT_SECONDS` 控制）。如需官方源，设置 `DOCKER_BASE_MIRROR=off`。`APT_MIRROR` / `APT_SECURITY_MIRROR` 用于加速 Docker 构建阶段的 Debian 依赖下载。国内服务器建议保留默认清华源；如所在网络访问清华源慢，可换成阿里云源：`http://mirrors.aliyun.com/debian` 和 `http://mirrors.aliyun.com/debian-security`。

## 3. 构建并启动

### Windows PowerShell

```powershell
docker compose build
docker compose up -d
```

或使用项目脚本：

```powershell
.\scripts\docker-build.ps1 -Up -Port 8080
```

### Linux Shell

```bash
docker compose build
docker compose up -d
```

如果构建卡在 `apt-get update` / `apt-get install`，先中断后确认 `.env` 中有：

```env
APT_MIRROR=http://mirrors.tuna.tsinghua.edu.cn/debian
APT_SECURITY_MIRROR=http://mirrors.tuna.tsinghua.edu.cn/debian-security
```

然后重新构建：

```bash
docker compose build --no-cache docshop
docker compose up -d
```

## 4. 访问系统

- 本机访问：`http://127.0.0.1:8080/`
- 局域网访问：`http://服务器LAN-IP:8080/`
- 健康检查：`http://127.0.0.1:8080/health`

如果要修改端口，编辑 `.env`：

```env
DOCSHOP_PORT=18080
```

然后重启：

```bash
docker compose up -d
```

## 5. 查看状态和日志

```bash
docker compose ps
docker compose logs --tail=200 docshop
docker compose exec docshop curl -fs http://localhost/health
```

## 6. 停止、重启、更新

```bash
# 停止并保留数据
docker compose down

# 重启
docker compose restart

# 重新构建并更新
docker compose build --no-cache
docker compose up -d
```

## 7. 数据目录和备份

Docker 默认挂载：

```text
宿主机 ./data  ->  容器 /app/data
```

重要数据：

```text
./data/docshop.db       # SQLite 数据库
./data/uploads/         # 上传文件
./data/covers/          # 封面/预览相关文件
./data/logs/            # 日志
./data/temp/            # 临时文件
```

备份时至少备份整个 `data` 目录：

### Windows PowerShell

```powershell
Compress-Archive -Path .\data -DestinationPath .\backup-docshop-data.zip -Force
```

### Linux

```bash
tar -czf backup-docshop-data.tar.gz data
```

## 8. 旧版本数据库兼容

如果旧部署中存在：

```text
/app/data/docdist.db
```

新容器启动时会在 `docshop.db` 不存在的情况下自动复制为：

```text
/app/data/docshop.db
```

也兼容旧布局中的：

```text
/app/backend/data/docshop.db
```

迁移只复制、不覆盖。因此从旧名称或旧目录布局升级到 DocShop 时，先备份并保留原 `data` 目录即可。

---

# 二、Windows 本地开发/部署

适合开发调试，生产环境仍推荐 Docker。

## 1. 安装依赖

安装：

- Python 3.11+
- Node.js 18+
- Microsoft Word（可选，用于 Windows Word COM 高保真 DOC/DOCX 转 PDF）

确认版本：

```powershell
python --version
node --version
npm --version
```

## 2. 后端启动

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item ..\.env.example .env
```

编辑 `backend\.env`，建议本地开发配置：

```env
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-to-32chars-min
DATABASE_URL=sqlite:///./data/docshop.db
UPLOAD_DIR=./data/uploads
LOG_DIR=./data/logs
TEMP_DIR=./data/temp
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080","http://127.0.0.1:3000"]
LOG_LEVEL=DEBUG
DOCX2PDF_TIMEOUT_SECONDS=300
PREVIEW_PDF_TIMEOUT_SECONDS=300
PREVIEW_IMAGE_MAX_WORKERS=1
```

启动后端：

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端地址：

- API: `http://127.0.0.1:8000/api/v1`
- 健康检查：`http://127.0.0.1:8000/health`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`

## 3. 前端启动

新开一个 PowerShell：

```powershell
cd frontend
npm install
npm run dev
```

默认访问：`http://127.0.0.1:3000/`

## 4. Windows 局域网访问

后端监听局域网：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端监听局域网：

```powershell
cd frontend
npm run dev -- --host 0.0.0.0 --port 3000
```

Windows 防火墙需要放行 3000/8000 端口。访问：

```text
http://你的Windows局域网IP:3000/
```

项目也提供局域网启动脚本：

```powershell
.\start-lan.bat
```

---

# 三、Linux 本地部署（非 Docker）

适合不使用 Docker 的服务器。生产使用时建议配合 systemd + Nginx。

以下以 Ubuntu/Debian 为例。

## 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip \
  nodejs npm \
  nginx curl sqlite3 \
  libreoffice libreoffice-writer libreoffice-calc libreoffice-math \
  fonts-noto-cjk fonts-wqy-microhei fonts-wqy-zenhei \
  fonts-opensymbol fonts-stix fonts-dejavu-core fontconfig \
  poppler-utils

fc-cache -fv
```

> 如果系统仓库中的 Node.js 版本低于 18，建议使用 NodeSource、nvm 或发行版新版源安装 Node.js 18+。

## 2. 部署代码

```bash
cd /opt
sudo mkdir -p docshop
sudo chown $USER:$USER docshop
cd docshop
# 将项目代码放到 /opt/docshop，或在此处 git clone
```

## 3. 后端 Python 环境

```bash
cd /opt/docshop/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

创建配置：

```bash
cp /opt/docshop/.env.example /opt/docshop/backend/.env
```

编辑 `/opt/docshop/backend/.env`：

```env
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=请替换为至少32字符的随机密钥
DATABASE_URL=sqlite:////opt/docshop/data/docshop.db
UPLOAD_DIR=/opt/docshop/data/uploads
LOG_DIR=/opt/docshop/data/logs
TEMP_DIR=/opt/docshop/data/temp
CORS_ORIGINS=*
LOG_LEVEL=INFO
DOCX2PDF_TIMEOUT_SECONDS=300
PREVIEW_PDF_TIMEOUT_SECONDS=300
PREVIEW_IMAGE_MAX_WORKERS=1
UVICORN_WORKERS=1
```

创建数据目录：

```bash
mkdir -p /opt/docshop/data/{uploads,logs,temp,cache,covers,avatars}
```

## 4. 构建前端

```bash
cd /opt/docshop/frontend
npm install
npm run build
```

构建产物位于：

```text
/opt/docshop/frontend/dist
```

## 5. systemd 后端服务

创建服务文件：

```bash
sudo tee /etc/systemd/system/docshop.service > /dev/null <<'EOF'
[Unit]
Description=DocShop FastAPI backend
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/docshop/backend
EnvironmentFile=/opt/docshop/backend/.env
ExecStart=/opt/docshop/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers
Restart=always
RestartSec=5
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
EOF
```

授权目录：

```bash
sudo chown -R www-data:www-data /opt/docshop/data /opt/docshop/backend
```

启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now docshop
sudo systemctl status docshop
```

查看日志：

```bash
journalctl -u docshop -f
```

## 6. Nginx 反向代理

创建配置：

```bash
sudo tee /etc/nginx/sites-available/docshop > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 100m;

    root /opt/docshop/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/docshop /etc/nginx/sites-enabled/docshop
sudo nginx -t
sudo systemctl reload nginx
```

访问：

```text
http://服务器IP/
```

---

# 四、常用运维命令

## Docker

```bash
docker compose ps
docker compose logs -f docshop
docker compose exec docshop bash
docker compose exec docshop sqlite3 /app/data/docshop.db '.tables'
docker compose exec docshop soffice --headless --version
docker compose restart docshop
```

## Linux systemd

```bash
sudo systemctl status docshop
sudo systemctl restart docshop
journalctl -u docshop -n 200 --no-pager
sudo nginx -t
sudo systemctl reload nginx
```

## 本地测试

```bash
python -m pytest backend/tests/test_docker_deployment_contract.py backend/tests/test_config.py -q
python -m pytest backend/tests/test_settings_password.py backend/tests/test_public_project_uploader.py backend/tests/test_share.py -q
```

前端构建测试：

```bash
cd frontend
npm run build
```

---

# 五、常见问题

## 1. PDF conversion failed / 预览生成失败

Docker/Linux：

```bash
docker compose exec docshop soffice --headless --version
```

或 Linux 本地：

```bash
soffice --headless --version
fc-list | grep -i "noto\|wqy" | head
```

处理建议：

1. 确认 LibreOffice 已安装。
2. 确认中文字体和公式字体已安装并执行 `fc-cache -fv`；公式预览依赖 `libreoffice-math`、OpenSymbol/STIX/DejaVu 字体。
3. 调大超时：

```env
DOCX2PDF_TIMEOUT_SECONDS=300
PREVIEW_PDF_TIMEOUT_SECONDS=300
```

4. 降低并发，避免低内存机器卡死：

```env
PREVIEW_IMAGE_MAX_WORKERS=1
UVICORN_WORKERS=1
```

5. 对异常大的 DOCX/PDF，建议先在办公软件中另存为 PDF 后上传。

## 2. Docker 启动后访问不了

检查：

```bash
docker compose ps
docker compose logs --tail=200 docshop
curl http://127.0.0.1:8080/health
```

确认：

- `.env` 中 `SECRET_KEY=auto` 或已设置固定随机密钥。
- 端口没有被占用。
- 防火墙允许 `DOCSHOP_PORT`。

## 3. 管理员账号不存在

在 `.env` 设置：

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=强密码
```

然后重启：

```bash
docker compose up -d
```

如果账号已经存在，该配置不会覆盖现有密码。管理员可在系统内修改密码。

## 4. 局域网其他电脑打不开

确认服务监听和防火墙：

- Docker：确认端口映射为 `0.0.0.0:8080->80` 或类似状态。
- Windows：放行 Docker Desktop / Node / Python 或指定端口。
- Linux：放行端口，例如：

```bash
sudo ufw allow 8080/tcp
sudo ufw allow 80/tcp
```

## 5. 升级后数据看起来丢失

确认挂载的 `data` 目录是否还是原来的目录：

```bash
ls -lah data
```

DocShop 默认数据库为：

```text
data/docshop.db
```

启动脚本会在 `data/docshop.db` 不存在时自动执行保守迁移：

- `data/docdist.db` -> `data/docshop.db`
- `backend/data/docshop.db` -> `data/docshop.db`

迁移只复制、不移动，并且不会覆盖已有的 `data/docshop.db`。升级前仍建议先备份整个 `data` 目录。

---

# 六、更多文档

- Docker 详细部署：[`docs/docker-deployment.md`](docs/docker-deployment.md)
- 必要依赖清单：[`docs/dependencies.md`](docs/dependencies.md)

## Docker 开发热更新

开发环境可以使用 `docker-compose.dev.yml` 做代码挂载，方便后续直接调整代码并热更新：

- 后端：`./backend/app` 挂载到 `/app/app`，`uvicorn --reload` 会自动重载 Python 代码。
- 前端：`./frontend` 挂载到 `/frontend`，Vite HMR 会自动刷新页面。
- 数据：`./data` 挂载到 `/app/data`，上传文件、缓存、数据库会保留在宿主机。
- 依赖：`frontend-node-modules` 使用 Docker volume，避免宿主机空目录覆盖容器内 `node_modules`。

前台运行：

```bash
docker compose -f docker-compose.dev.yml up --build
```

后台运行：

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

默认访问地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- 健康检查：`http://localhost:8000/health`

局域网访问时，把 `localhost` 换成服务器局域网 IP，例如：

```text
http://192.168.1.10:5173
```

常用命令：

```bash
# 查看全部日志
docker compose -f docker-compose.dev.yml logs -f

# 只看后端日志
docker compose -f docker-compose.dev.yml logs -f backend

# 只看前端日志
docker compose -f docker-compose.dev.yml logs -f frontend

# 停止开发环境
docker compose -f docker-compose.dev.yml down

# requirements.txt 或 package-lock.json 变化后重新构建
docker compose -f docker-compose.dev.yml up -d --build
```

注意事项：

- 开发 compose 不走生产 Nginx，前端请求 API 通过 Vite proxy 转发到后端。
- Windows / WSL / Docker Desktop 文件监听不稳定时，可以保留 `CHOKIDAR_USEPOLLING=true`。
- 正式发布请使用 `docker-compose.yml`，开发 compose 只用于代码挂载和热更新。


## Docker 发布与热更新速查

### 生产部署

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f docshop
```

生产 compose 数据挂载：

- `./data:/app/data`

Linux 容器内 Word 预览需要 LibreOffice/字体支持；发布镜像已内置 LibreOffice、中文字体、公式字体和预览基础依赖。低占用部署建议保持 `PREVIEW_IMAGE_MAX_WORKERS=1`，按机器性能再逐步调高。

### 开发热更新

```bash
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml logs -f backend frontend
```

开发 compose 代码挂载：

- `./backend/app:/app/app`
- `./frontend:/frontend`
- `./data:/app/data`

修改后端 Python 代码由 uvicorn reload 自动生效；修改前端由 Vite HMR 自动刷新。requirements.txt 或 package-lock.json 变更后重新执行开发热更新构建命令。
