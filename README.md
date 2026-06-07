# DocDist - 文档差异比对系统

DocDist 是一个专业的文档差异比对系统，支持 PDF、DOCX、XLSX 等多种文档格式的智能比对，帮助用户快速识别文档变更内容。

## 功能特性

### 核心功能
- **多格式支持**: 支持 PDF、DOCX、XLSX 等主流文档格式的差异比对
- **智能比对引擎**: 基于文档类型的专用比对算法，精确识别文本、表格、段落等变更
- **版本管理**: 完整的文档版本控制，支持历史版本回溯和对比
- **项目管理**: 按项目组织文档，支持多项目并行管理

### 安全与权限
- **JWT 认证**: 基于 Token 的安全认证机制
- **角色管理**: 支持管理员和普通用户角色
- **权限控制**: 细粒度的项目和文件访问权限

### 用户界面
- **现代化 UI**: 基于 Vue 3 的响应式前端界面
- **实时预览**: 差异结果实时渲染，支持高亮显示
- **导出功能**: 支持将比对结果导出为多种格式

### 系统特性
- **RESTful API**: 完整的 API 接口，支持第三方集成
- **容器化部署**: 基于 Docker 的一键部署方案
- **自动备份**: 内置数据备份和恢复机制

## 快速开始

### 环境要求
- Docker >= 20.0
- Docker Compose >= 2.0
- Git

### 开发环境搭建

1. **克隆仓库**
```bash
git clone <repository-url>
cd docdist
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的配置项
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问应用**
- 前端界面: http://localhost:8080
- API 文档: http://localhost:8000/docs

### 本地开发

#### 后端开发
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### 前端开发
```bash
cd frontend
npm install
npm run dev
```

## 生产部署

### 使用 Docker Compose

1. **准备环境**
```bash
# 创建数据目录
mkdir -p /data/docdist/uploads
mkdir -p /data/docdist/backup

# 设置权限
chmod 755 /data/docdist
```

2. **配置生产环境**
```bash
# 复制并编辑生产环境配置
cp .env.example .env.production
# 修改以下关键配置：
# - SECRET_KEY: 设置为强密码
# - DATABASE_URL: 使用生产数据库
# - LOG_LEVEL: 设置为 WARNING 或 ERROR
```

3. **执行部署**
```bash
./scripts/deploy.sh
```

### 手动部署

1. **构建镜像**
```bash
docker-compose -f docker-compose.yml build
```

2. **启动服务**
```bash
docker-compose -f docker-compose.yml up -d
```

3. **运行健康检查**
```bash
./scripts/health_check.sh
```

## API 文档

### 认证接口
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/register` - 用户注册
- `GET /api/v1/auth/me` - 获取当前用户信息
- `POST /api/v1/auth/change-password` - 修改密码

### 项目接口
- `GET /api/v1/projects` - 获取项目列表
- `POST /api/v1/projects` - 创建项目
- `GET /api/v1/projects/{id}` - 获取项目详情
- `PUT /api/v1/projects/{id}` - 更新项目
- `DELETE /api/v1/projects/{id}` - 删除项目
- `GET /api/v1/projects/{id}/stats` - 获取项目统计

### 文件接口
- `GET /api/v1/projects/{id}/files` - 获取文件列表
- `POST /api/v1/projects/{id}/files` - 上传文件
- `GET /api/v1/files/{id}` - 获取文件详情
- `DELETE /api/v1/files/{id}` - 删除文件
- `GET /api/v1/files/{id}/download` - 下载文件
- `GET /api/v1/files/{id}/versions` - 获取文件版本
- `POST /api/v1/files/{id}/versions` - 上传新版本

### Diff 接口
- `GET /api/v1/projects/{id}/diffs` - 获取 Diff 列表
- `POST /api/v1/diffs` - 创建 Diff
- `GET /api/v1/diffs/{id}` - 获取 Diff 详情
- `DELETE /api/v1/diffs/{id}` - 删除 Diff
- `GET /api/v1/diffs/{id}/export` - 导出 Diff 结果

### 健康检查
- `GET /api/v1/health` - 服务健康状态

完整的 API 文档可在启动服务后访问 http://localhost:8000/docs 查看。

## 测试运行

### 运行所有测试
```bash
cd backend
pytest
```

### 运行特定测试
```bash
# 仅运行认证测试
pytest tests/test_auth.py

# 仅运行项目测试
pytest tests/test_projects.py

# 仅运行文件测试
pytest tests/test_files.py

# 仅运行 Diff 测试
pytest tests/test_diff.py
```

### 测试覆盖率
```bash
pytest --cov=app --cov-report=html
```

### 测试配置
测试使用 SQLite 内存数据库，自动创建和销毁测试数据，不会影响生产环境。

## 配置说明

### 基础配置
| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| SECRET_KEY | JWT 密钥 | - |
| DATABASE_URL | 数据库连接 URL | sqlite:///./data/docdist.db |
| UPLOAD_DIR | 文件上传目录 | ./data/uploads |

### 安全配置
| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| ACCESS_TOKEN_EXPIRE_MINUTES | Token 过期时间(分钟) | 1440 |
| MAX_FILE_SIZE | 最大文件大小(字节) | 52428800 (50MB) |
| ALLOWED_FILE_TYPES | 允许的文件类型 | .pdf,.docx,.xlsx |

### 性能配置
| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| MAX_WORKERS | 最大工作进程数 | 4 |
| DIFF_ENGINE_TIMEOUT | Diff 引擎超时时间(秒) | 300 |

### 日志配置
| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| LOG_LEVEL | 日志级别 | INFO |
| LOG_RETENTION_DAYS | 日志保留天数 | 30 |

## 运维脚本

### 备份脚本
```bash
./scripts/backup.sh
```
自动备份数据库和上传文件，保留最近 30 天的备份。

### 健康检查
```bash
./scripts/health_check.sh
```
检查服务健康状态，可配合 cron 定时执行。

### 部署脚本
```bash
./scripts/deploy.sh
```
自动化部署流程，包含备份、构建、健康检查等步骤。

## 常见问题

### Q: 如何重置管理员密码？
A: 目前需要通过数据库直接修改，后续版本将支持邮箱找回密码功能。

### Q: 支持哪些文档格式？
A: 当前支持 PDF、DOCX、XLSX 格式，后续将支持 PPTX 等更多格式。

### Q: 最大支持多大的文件？
A: 默认最大支持 50MB，可通过 `MAX_FILE_SIZE` 配置项调整。

### Q: 如何配置 HTTPS？
A: 建议使用 Nginx 反向代理配置 HTTPS，参考 `nginx.conf` 文件。

### Q: 数据库如何迁移？
A: 使用 Alembic 进行数据库迁移：
```bash
cd backend
alembic revision --autogenerate -m "migration message"
alembic upgrade head
```

### Q: 如何查看日志？
A: 
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend

# 实时跟踪日志
docker-compose logs -f backend
```

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **ORM**: SQLAlchemy
- **认证**: JWT + bcrypt
- **文档处理**: PyPDF2, python-docx, openpyxl

### 前端
- **框架**: Vue 3
- **构建工具**: Vite
- **状态管理**: Pinia
- **UI 组件**: Element Plus
- **HTTP 客户端**: Axios

### 部署
- **容器化**: Docker + Docker Compose
- **Web 服务器**: Nginx
- **进程管理**: Uvicorn

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 联系方式

如有问题或建议，欢迎提交 Issue 或 Pull Request。
