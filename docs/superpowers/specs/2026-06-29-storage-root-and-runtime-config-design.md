# DocShop 存储根统一与运行期配置热生效设计

## 背景

当前项目同时存在 `docshop/data` 与 `docshop/backend/data` 两套数据目录。根因不是单个 bug，而是以下因素叠加：

1. `.env` 中大量使用 `./data/...` 相对路径。
2. 本地开发脚本从 `backend/` 作为当前工作目录启动后端。
3. Docker 与 README 将仓库根 `./data` 视为默认持久化目录。
4. 后端多处通过 `Path(settings.UPLOAD_DIR).parent / ...` 继续隐式派生其他目录。

结果是同一份配置在不同启动方式下解析为不同物理目录，造成数据库、上传文件、缓存、日志、临时文件分叉。

与此同时，设置页当前的“热重载”本质仍是改写 `.env` 后依赖 `uvicorn --reload` 触发进程重启，这并不等于运行期配置热生效，也不利于架构清晰。

## 目标

本次重构目标：

1. 统一唯一存储根为 `docshop/data`。
2. 所有文件系统路径从统一存储根显式派生，不再依赖当前工作目录。
3. 将配置划分为“运行期可热生效”和“基础设施需重启”两类。
4. 设置接口对运行期配置做进程内刷新，不再把 `uvicorn --reload` 作为主生效机制。
5. 统一配置类错误的返回格式与日志记录。

不在本次范围内：

1. 在线修改数据库连接并重建 engine。
2. 在线迁移存量历史数据目录内容。
3. 一次性替换所有旧接口结构。

## 方案概述

采用“统一存储根 + 派生路径 + 运行期配置刷新服务”的中等规模收口方案。

### 1. 唯一存储根

新增 `STORAGE_ROOT` 配置，默认指向仓库根 `data` 目录。后端在加载配置时将其解析为绝对路径。

以下目录统一从 `STORAGE_ROOT` 派生：

- `UPLOAD_DIR = STORAGE_ROOT / uploads`
- `LOG_DIR = STORAGE_ROOT / logs`
- `TEMP_DIR = STORAGE_ROOT / temp`
- `MOBILE_MODEL_CACHE_DIR = STORAGE_ROOT / cache`
- `DOCUMENTS_DIR = STORAGE_ROOT / documents`
- `OBJECTS_DIR = STORAGE_ROOT / objects`
- `AVATARS_DIR = STORAGE_ROOT / avatars`
- `COVERS_DIR = STORAGE_ROOT / covers`
- `TRASH_DIR = STORAGE_ROOT / trash`

为降低首轮改动范围，保留现有 `UPLOAD_DIR` / `LOG_DIR` / `TEMP_DIR` / `MOBILE_MODEL_CACHE_DIR` 字段，但统一在配置层解析为绝对路径，并新增显式派生属性供新代码优先使用。

### 2. 路径解析规则

配置加载时遵循：

1. 绝对路径保持原样。
2. 相对路径一律相对于**仓库根目录**解析，而不是当前工作目录。
3. SQLite `DATABASE_URL` 如果使用本地文件路径（如 `sqlite:///./data/docshop.db`），同样转换为基于仓库根的绝对路径 URL。

这样本地脚本、手工启动、Docker、测试都能得到一致的路径结果。

### 3. 配置分层

#### 基础设施配置（需重启）

包括但不限于：

- `DATABASE_URL`
- `STORAGE_ROOT`
- `UPLOAD_DIR`
- `LOG_DIR`
- `TEMP_DIR`
- `MOBILE_MODEL_CACHE_DIR`

这些配置不作为设置页热更新对象。若前端传入，后端返回明确校验错误，提示“该配置需要重启后生效，不支持在线修改”。

#### 运行期配置（可热生效）

包括当前设置页已覆盖的：

- `FORCE_HTTPS`（仅配置值本身热刷新；后续是否被业务消费另算）
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `MAX_FILE_SIZE`
- `RATE_LIMIT_REQUESTS`
- `LOG_LEVEL`
- `ALLOWED_FILE_TYPES`
- `CORS_ORIGINS`

这些配置在写入 `.env` 后立即刷新进程内运行时配置。

### 4. 热生效机制

新增运行期配置刷新入口：

1. 写入 `.env`
2. 重新加载 `Settings`
3. 原位更新全局 `settings`
4. 触发运行期副作用同步，例如日志级别刷新

保留当前 `touch .env` 逻辑仅作为开发环境兼容兜底，不再作为主要生效路径；若已完成进程内刷新，则不依赖进程重启。

### 5. 错误处理

对配置/存储相关错误统一分为两类：

1. **用户输入错误**：如试图在线修改需重启配置、路径非法、值格式无效，返回标准业务错误。
2. **系统执行错误**：如写 `.env` 失败、目录不可创建、日志重配置失败，记录错误日志并返回标准 500。

设置接口不再用模糊“保存成功”掩盖部分未生效情形，而是明确返回：

- 已即时生效
- 已保存但需重启（本轮采用禁止在线修改，因此通常直接报错）
- 保存失败

## 组件调整

### `backend/app/config.py`

负责：

- 增加仓库根 / backend 根 / storage 根解析能力
- 规范化相对目录与 SQLite 路径
- 提供显式派生目录属性
- 统一目录创建入口

### `backend/app/services/runtime_config.py`（新增）

负责：

- 定义哪些 key 允许运行期热刷新
- 刷新全局 `settings`
- 执行必要副作用同步（首轮至少包含 logger）

### `backend/app/utils/logger.py`

负责：

- 提供可重复调用的日志级别刷新函数
- 避免 logger 只在 import 时固定住旧配置

### `backend/app/routers/settings.py`

负责：

- 区分可热生效配置与基础设施配置
- 统一写 `.env`
- 在成功写入后调用运行期刷新服务
- 返回更准确的结果消息

### `backend/app/main.py`

负责：

- 启动时只使用显式派生路径
- 不再散落 `Path(settings.UPLOAD_DIR).parent / ...` 的目录推导

## 迁移策略

首轮不迁移磁盘上已有数据，只修正“以后默认往哪写”的逻辑。

若本机当前同时存在 `backend/data` 与 `data`，重构后：

1. 新写入会落到 `docshop/data`
2. 旧 `backend/data` 不自动删除
3. 若用户需要，可后续单独补迁移脚本

## 测试策略

新增/调整测试覆盖：

1. 相对 `UPLOAD_DIR` / `LOG_DIR` / `TEMP_DIR` / `MOBILE_MODEL_CACHE_DIR` 解析到仓库根 `data`
2. 相对 SQLite `DATABASE_URL` 解析到仓库根 `data/docshop.db`
3. 设置接口拒绝在线修改基础设施配置
4. 设置接口更新运行期配置后，全局 `settings` 立即反映新值
5. 日志级别刷新函数在 reload 后使用新级别
6. `main.py` 与其他关键模块优先使用显式路径属性而不是 `UPLOAD_DIR.parent`

## 风险与控制

### 风险 1：历史测试依赖旧的相对路径行为

控制：

- 只改“相对路径解析基准”，保留外部字段名
- 针对受影响配置测试同步更新

### 风险 2：logger 在 import 时固化旧状态

控制：

- 显式增加 `apply_runtime_settings()` / `reconfigure_logging()` 之类入口
- 用测试证明修改 `LOG_LEVEL` 后新配置会反映到 handler / logger

### 风险 3：大范围替换 `UPLOAD_DIR.parent`

控制：

- 首轮只替换配置、main、settings、少数关键服务中的公共派生点
- 其余位置继续兼容，因为 `UPLOAD_DIR` 已先被规范化到唯一根下

## 结果预期

重构完成后：

1. 本地开发与 Docker 默认都以 `docshop/data` 作为唯一存储根。
2. 设置页修改运行期配置可立即生效，不依赖 uvicorn 进程重启。
3. 基础设施配置不会再被误当成“保存成功且已生效”。
4. 配置/存储错误的日志与接口返回更一致、更可诊断。
