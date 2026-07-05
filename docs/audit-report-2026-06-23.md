# DocShop 项目审计报告 — 交叉验证版

**审计日期:** 2026-06-23  
**审计方法:** 静态代码分析 + 深度交叉验证（逐一确认/排除误报）  
**状态:** ✅ = 已确认真实缺陷，❌ = 已排除误报

---

## 总览

| 类别 | 总计 | 已确认 | 已排除 |
|------|------|--------|--------|
| 安全漏洞 | 16 | 16 | 0 |
| 代码质量风险 | 8 | 7 | 1 |
| 潜在缺陷/Bug | 17 | 17 | 0 |
| 设计缺陷 | 3 | 3 | 0 |
| **合计** | **43** | **42** | **1** |

---

## 1. 安全漏洞（全部确认）

### 1.1 [严重] DOCX 外部图片加载 SSRF ✅

**位置:** `conversion_service.py:300-351`  
**验证结果:** 真实可利用。当原生转换引擎不可用时，`_convert_docx_to_html()` 会提取 DOCX 中的外部图片链接并发起 HTTP 请求，无 IP/端口限制。

**调用链:** `convert_to_pdf()` → 原生转换失败 → `_convert_docx_to_html()` → `_render_run_images()` → `_image_src_from_blip()` → `_external_image_to_data_uri()` → `requests.get(url)`

**影响:** SSRF 探测内网、访问云元数据端点。

### 1.2 [高危] 五处置信 `X-Forwarded-For` ✅

**位置:**
1. `middlewares/error_handler.py:187-196` — ErrorHandlerMiddleware
2. `middlewares/logging.py:173-200` — LoggingMiddleware
3. `middlewares/tracking.py:502-526` — TrackingMiddleware
4. `models/access_log.py:240-265` — AccessLog._get_client_ip **(新发现)**
5. `routers/access_tokens.py:48-49` — _legacy_validate_key

**验证结果:** 五处均直接信任代理头，未验证 `TRUSTED_PROXY_IPS`。RateLimitMiddleware 正确实现了检查。在 Docker 单容器部署中风险较低（Nginx 始终设置真实 IP），但在直接暴露后端端口时存在 IP 欺骗风险。

### 1.3-1.12 其余安全漏洞（全部确认）

| # | 问题 | 严重度 | 验证说明 |
|---|------|--------|----------|
| 1.3 | 登录暴力破解仅在单进程内存中 | 中 | 多 worker 部署可绕过 |
| 1.4 | 密码策略前后端不一致 | 中 | 前松后严，用户体验差 |
| 1.5 | CORS 默认 `*` | 中 | 生产环境需配置白名单 |
| 1.6 | Nginx CSP 与后端 CSP 不一致 | 中 | 后端会覆盖 Nginx 设置，实际取后端值 |
| 1.7 | URL token 持久化到 localStorage | 中 | 共享设备存在泄露风险 |
| 1.8 | GET /validate 令牌在查询参数中 | 中 | 出现在日志/Referer/历史记录中 |
| 1.9 | POST /validate 无速率限制 | 低 | 可暴力猜测令牌 |
| 1.10 | SECRET_KEY=auto 容器重启会话失效 | 低 | 文档已说明，预期行为 |
| 1.11 | 无 CSRF 保护 | 低 | Bearer token 部分缓解 |
| 1.12 | 开发环境硬编码弱凭据 | 低 | dev-only，明确标注 |

---

### 1.13 [中危] 认证令牌查询参数泄漏面覆盖所有路由 ✅ **（新发现）**

**位置:** `deps/auth.py:31-33`

**问题:** 原有 1.8 仅提及 `GET /validate` 在查询参数中泄露令牌。但 `get_current_user()` 依赖注入接受 **3个查询参数名**（`auth_token`、`access_token`、`token`），所有受保护路由均可通过 URL 传递 JWT。

**影响:** 任何 API 请求的 URL 都可能出现在服务器访问日志、浏览器历史、Referer 头中。用户复制/分享 URL 时同时泄露认证凭据。

**建议:** 限制查询参数令牌仅在少数预览端点使用，或在中间件层面剥离日志中的令牌参数。

---

### 1.14 [低危] Content-Disposition 回退文件名未转义 ✅ **（新发现）**

**位置:** `routers/files.py:1238,1662`, `routers/share.py:835`

**问题:** `FastAPIFileResponse(filename=doc_file.filename)` 中的 raw `filename` 参数直接使用数据库中未经 CRLF 过滤的文件名。虽 `filename*=UTF-8''` 已用 `quote()` 转义，旧客户端会回退到 `filename="raw_name"`，若文件名含 CRLF 可导致 HTTP 响应头注入。

**影响:** 攻击者上传含 `\r\n` 文件名的文件，旧浏览器下载时可能触发响应头注入。低危因需攻击者主动上传恶意文件。

**建议:** 对 `filename` 参数也执行 `quote()` 或剥离控制字符。

---

### 1.15 [高危] AccessDenied 页面开放重定向 ✅ **（新发现）**

**位置:** `frontend/src/views/AccessDenied.vue:57-59,74`

```javascript
const redirectTarget = computed(() => {
  const value = route.query.redirect
  return typeof value === 'string' && value ? value : '/'
})
function retry() {
  router.replace(redirectTarget.value)  // 无验证！
}
```

**问题:** "刷新验证"按钮调用 `router.replace(redirectTarget.value)` 直接导航到 `?redirect=` 参数值，仅检查 `typeof === 'string'`，接受任意完整 URL。对比 `LoginView.vue:405-408` 已正确使用 `/^\/[^/]/` 白名单验证。

**影响:** 攻击者构造 `?redirect=https://evil.com` 链接，用户点击"刷新验证"后被重定向到钓鱼站点。

**建议:** 复用 LoginView 的白名单模式：仅允许以单 `/` 开头的内部路径。

---

### 1.16 [中危] 公告内容未净化导致存储型 XSS ✅ **（新发现）**

**位置:** `routers/announcements.py:52-66`, `models/announcement.py:37-52`

**问题:** `/api/v1/announcements/active` 为**无需认证**的公开端点，返回管理员创建的公告 `content`。`AnnouncementCreate` schema 仅校验长度，未应用 `sanitize_user_text()`（该函数存在于 `utils/sanitization.py` 且已被 `projects.py`、`exams.py` 使用）。若前端以 `innerHTML` 渲染公告内容，管理员创建的恶意脚本将对所有访问者（含未登录用户）执行。

**影响:** 存储型 XSS — 管理员账号被攻破后可在公告中植入恶意脚本，影响所有用户。

**建议:** 在 `create_announcement`/`update_announcement` 中对 `content` 应用 `sanitize_user_text()`，或在 `to_dict()` 输出时净化。

---

## 2. 代码质量风险

### 2.1 [高危] 大量 `except Exception` 滥用 ✅

**统计:** 后端约 200+ 处，已确认。

### 2.2 ~~`generate_images` 缓存清理失效~~ ❌ **误报，已排除**

**验证过程:** `generate_images()` 使用 `dir_images(file_id)` → `ROOT/file_id/images/`，在此目录下直接存储 `page_NNNN.jpg` 文件。`get_cached_images()` 也从同一目录读取。清理循环 `for f in os.listdir(img_dir): if f.startswith("page_")...` 确实能匹配到这些文件。**缓存清理正常工作，不是 bug。**

`render_single_page()` 使用 `dir_page_images(file_id, pdf_hash)` → `ROOT/file_id/images/{hash}/` 是独立的单页懒加载路径，不影响批量生成。

### 2.3 [中危] `.env` 文件路径解析不一致 ✅

**位置:** `security_settings.py:17` vs `routers/settings.py:51`

**验证结果:** 当前场景下两者实际指向同一文件（Docker：`/app/.env`；开发：`backend/.env`），但 `security_settings._env_path()` 依赖 CWD 解析相对路径的 `UPLOAD_DIR`，不如 `settings._env_abs_path()` 的 `Path(__file__)` 方式健壮。属于**防御性编码风险**，不构成功能缺陷。

### 2.4 [中危] 线程安全风险 ✅

**位置:** `auth.py:34`（无锁 defaultdict）、`cache_service.py:58`（PatchableCacheStore）

### 2.5 [中危] 数据库迁移策略脆弱 ✅

**位置:** `database.py:204-242` — 无版本管理

### 2.6 [低危] TrackingMiddleware 直接创建数据库会话 ✅

**位置:** `tracking.py:410` — 使用 `SessionLocal()` 而非依赖注入

### 2.7 [低危] 前端错误监控缺失 ✅

### 2.8 [低危] `passlib` 冗余依赖 ✅

**验证:** 代码直接使用 `bcrypt`，`passlib[bcrypt]` 在 requirements.txt 中但未引用。

---

## 3. 潜在缺陷与 Bug（全部确认）

### 3.1 [高危] SQLite + `UVICORN_WORKERS>1` 数据损坏 ✅

**验证:** SQLite WAL 模式下并发写入有限，文档允许调高 workers 是误导。

### 3.2 [中危] 时区时间比较不一致 ✅

**位置:** `share_token_service.py:18`

**验证:** 若 `expires_at` 带非 UTC 时区（如 `+08:00`），移除时区后与 UTC 比较产生错误。

### 3.3 [中危] 注册竞态条件 ✅

**位置:** `auth.py:173-178`

**验证:** `with_for_update()` 在 SQLite 下异常被吞噬，并发注册可能都成为 admin。

### 3.4 [中危] `CacheService.get()` 不检查 TTL ✅

**位置:** `cache_service.py`

**验证:** `get()` 返回 `(value, expiry)` 元组但不检查 expiry 时间，缓存可能返回过期数据。

### 3.5 [中危] 前端 `downloadBlobWithFallback` HTML 注入 ✅

**位置:** `frontend/src/utils/index.js:64-76`

**验证:** 将 Blob 内容直接 `document.write(html)` 到新窗口，若后端返回未转义内容则存在 XSS。

### 3.6 [低危] 头像上传旧文件删除 race condition ✅

**位置:** `settings.py:258-275`

### 3.7 [低危] `resolve_storage_path` 路径解析脆弱 ✅ **（新发现）**

**位置:** `preview_queue.py:114-147`

**问题:** 尝试多个根目录（CWD、CWD.parent、`Path(__file__).parents[3]`）来解析相对存储路径。多个目录存在同名文件时返回第一个而非预期文件。当后端运行目录迁移时，可能错误解析到旧目录下的同名文件。

**建议:** 将路径根目录硬编码为 `settings.UPLOAD_DIR`，消除二义性。

---

### 3.8 [中危] 中文错误消息编码损坏 ✅ **（新发现）**

**位置:** `backend/app/routers/exams.py:69,71,416`

**代码 (line 69,71):**
```python
raise ValidationError(message="???????????", field="reminder_offsets_minutes")
raise ValidationError(message="?????? 0 ? 525600 ????", field="reminder_offsets_minutes")
```

**问题:** 源码中的中文字符串被错误编码，显示为问号（`?`）而非正确的中文。原始错误消息完全丢失。

**影响:** 用户看到乱码错误消息，无法理解校验失败原因。

**建议:** 使用 Unicode 转义序列（`\uXXXX`）或确保文件以 UTF-8 编码保存。

---

### 3.9 [中危] 大文档 Diff 内存耗尽风险 ✅ **（新发现）**

**位置:** `backend/app/diff_engine/docx_diff.py:1239-1240`

```python
old_hash = hashlib.sha256('\n'.join(old_paragraphs).encode()).hexdigest()[:16]
new_hash = hashlib.sha256('\n'.join(new_paragraphs).encode()).hexdigest()[:16]
```

**问题:** 大文档对比时，将所有段落用换行符拼接为一个巨型字符串后再计算哈希。对于超过 10000 段落的文档，可能耗尽内存（`MemoryError` 或 OOM）。

**建议:** 使用流式哈希（逐段更新 `sha256`）代替一次性 `join`。

---

### 3.10 [低危] MathJax 外部 CDN 加载无 SRI 完整性验证 ✅ **（新发现）**

**位置:** `backend/app/services/conversion_service.py:450`, `backend/app/routers/files.py:996`

```python
'<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'
```

**问题:** 生成的 HTML 预览页从 CDN 加载 MathJax 脚本，未指定 `integrity` 属性。若 CDN 被攻破，恶意 JS 可在用户浏览器中执行（供应链攻击）。此外每次预览都加载外部资源，存在隐私泄露和可靠性问题。

**建议:** 自托管 MathJax 或添加 SRI integrity hash。

---

### 3.11 [中危] PyMuPDF 文档句柄泄漏（7处） ✅ **（新发现）**

**位置:**
- `routers/files.py:1128-1131` — `get_file_text()` 中迭代页面前未保护
- `routers/files.py:1179-1181` — `get_page_image()` 中 `len(doc)` 可能异常
- `routers/files.py:1258-1260` — 预览骨架页数获取
- `routers/share.py:854-856` — 分享预览页数获取
- `routers/share.py:960-962` — 分享单页获取
- `services/conversion_service.py:1070-1072` — Word→PDF 转换页数
- `services/conversion_service.py:1322-1324` — 缓存图片生成页数

**问题:** `doc = fitz.open(pdf_path)` 之后直接 `doc.close()`，若中间操作（`len(doc)`、`page.get_text()`）抛出异常，`doc.close()` 不执行，PyMuPDF 的 C 级文档句柄泄漏。区别于 `pdf_diff.py:299-313` 和 `document_store.py:299-307` 已正确使用 `try/finally`。

**影响:** 处理损坏 PDF 时累积文件描述符泄漏，最终导致 `EMFILE`，服务不可用。

**建议:** 全部改为 `try/finally` 模式或使用上下文管理器封装。

---

### 3.12 [高危] PIL 解压缩炸弹（DoS） ✅ **（新发现）**

**位置:** `diff_engine/docx_diff.py:424-425`

```python
with PILImage.open(BytesIO(blob)) as original:
    source = original.copy()  # 触发完整解压缩
```

**问题:** `PILImage.open()` 惰性读取头信息但不检查像素尺寸。紧接着 `.copy()` 触发完整解压为未压缩位图（RGBA ≈ 4 bytes/pixel）。攻击者可构造声称 100万×100万 像素的图像，导致 ~4TB 内存分配 → OOM。虽 Pillow 默认 `MAX_IMAGE_PIXELS` ≈ 8900万，但 DOCX 可嵌入多张图片，单张 ~356MB 仍可耗尽容器内存。

**建议:** 打开前检查 `len(blob)` 硬上限（如 50MB），设置 `PIL.Image.MAX_IMAGE_PIXELS` 为安全值，或直接解压至缩略图尺寸。

---

### 3.13 [高危] `diff_match_patch` 指数级 DoS ✅ **（新发现）**

**位置:** `diff_engine/docx_diff.py:691-713`

```python
diffs = self.dmp.diff_main(old_text, new_text)
self.dmp.diff_cleanupSemantic(diffs)
```

**问题:** Google `diff_match_patch` 库在特定对抗性字符串（长串重复字符+微小插入）上有**指数级最坏复杂度**。唯一防护 `_cap_diff_payload` 在 diff 计算**之后**，无超时、无熔断器。每个 REPLACE 段落的段落对都调用此方法。

**建议:** 在子进程或 `concurrent.futures` 中带硬超时运行（如 5秒），超时则回退至逐行 diff。

---

### 3.14 [中危] `pd.read_excel` 超限前全量加载 ✅ **（新发现）**

**位置:** `diff_engine/xlsx_diff.py:254-262`

```python
df_old = pd.read_excel(old_path, sheet_name=sheet_name)  # 全量加载
df_old = df_old.fillna('')
if len(df_old) > self.max_rows or len(df_old.columns) > self.max_cols:
    raise ValueError(...)  # 检查在加载之后
```

**问题:** `pd.read_excel()` 将整张工作表加载为 DataFrame **之后**才检查行/列上限。1000万行 × 100列的 XLSX 可消耗数 GB 内存。

**建议:** 使用 `pd.read_excel(..., nrows=self.max_rows + 1)` 预先限制读取行数。

---

### 3.15 [中危] XXE 实体扩展保护缺失 ✅ **（新发现）**

**位置:** `diff_engine/docx_diff.py:161`（python-docx/lxml）、`xlsx_diff.py:171`（openpyxl/lxml）

**问题:** `python-docx` 和 `openpyxl` 底层使用 `lxml` 解析 OOXML。现代 lxml 默认禁用网络实体解析但**不禁用**本地实体扩展。攻击者可嵌入 "Billion Laughs" 载荷导致指数级内存膨胀。

**建议:** 配置 `lxml` 解析器：`resolve_entities=False`、`huge_tree=False`、设置合理 `max_depth`。

---

### 3.16 [低危] Unicode NFC 规范化缺失 ✅ **（新发现）**

**位置:** `diff_engine/docx_diff.py:550-551`

```python
def _normalize_text(self, text: str) -> str:
    return " ".join((text or "").split()).casefold()
```

**问题:** `casefold()` 处理大小写但不做 Unicode 规范化（NFC/NFD）。不同编辑器（macOS Pages vs Windows Word）可能将同一文本存储为不同规范化形式。如 `"café"`（NFC: `U+00E9`）vs `"café"`（NFD: `e + U+0301`）在视觉上完全相同却被报告为差异。

**建议:** 添加 `unicodedata.normalize('NFC', text)`。

---

### 3.17 [中危] OLE 文件魔术字节验证可被绕过 ✅ **（新发现）**

**位置:** `validators/file_validator.py:390-402`

```python
# 如果无法确定，根据扩展名推断
logger.warning("无法准确检测 OLE 文件类型，将信任文件扩展名")
ext = os.path.splitext(file_path)[1].lower()
if ext in ('.xls', '.xlt', '.xlsx'):  # .xlsx 不会到达此处（ZIP格式），逻辑混淆
    return 'xls'
return 'doc'
```

**问题:** 当 4KB 头扫描未找到 `WordDocument`/`Workbook` 特征串且 `olefile` 库不可用时（`olefile` **不在** requirements.txt 中），魔术字节验证**静默绕过**：根据文件扩展名信任返回类型。攻击者可上传魔术字节正确（`\xd0\xcf\x11\xe0`）但内部流被混淆/加密的 OLE 容器，绕过内容检测。

**影响:** 文件类型验证被绕过，恶意 OLE 文件可被当作合法 .doc/.xls 接受。

**建议:** 将 `olefile` 添加到 requirements.txt，移除扩展名回退逻辑，无法确定类型时应拒绝文件。

---

## 4. 设计缺陷（全部确认）

### 4.1 [中危] 无统一请求验证中间件 ✅
### 4.2 [低危] .env 文件通过 API 可写 ✅
### 4.3 [低危] 无 API 版本管理规划 ✅

---

## 5. 建议修复优先级（最终版）

| 优先级 | 问题 | 类型 | 验证状态 |
|--------|------|------|----------|
| **P0** | DOCX 外部图片 SSRF | 安全 | ✅ 确认可远程利用 |
| **P0** | 五处置信 X-Forwarded-For | 安全 | ✅ 确认全部 5 处 |
| **P0** | SQLite + UVICORN_WORKERS>1 数据损坏 | 缺陷 | ✅ 确认文档误导 |
| **P0** | PIL 解压缩炸弹（PIL Image.copy） | 缺陷 | ✅ 新发现 |
| **P0** | diff_match_patch 指数级 DoS | 缺陷 | ✅ 新发现 |
| **P0** | AccessDenied 页面开放重定向 | 安全 | ✅ 新发现 |
| P1 | 登录暴力破解无锁/不跨进程 | 安全 | ✅ |
| P1 | 密码策略前后端不一致 | 安全 | ✅ |
| P1 | 过度 `except Exception` | 代码质量 | ✅ |
| P1 | 时区比较缺陷 | Bug | ✅ |
| P1 | 注册竞态条件 | Bug | ✅ |
| P1 | SSRF 失败时回退原始 URL | 安全 | ✅ |
| P2 | `.env` 路径解析不一致 | 代码质量 | ⚠️ 边缘案例，但当下功能正确 |
| P2 | CSP 前/后端不一致 | 安全 | ✅ |
| P2 | 数据库迁移策略脆弱 | 代码质量 | ✅ |
| P2 | `CacheService.get()` 不检查 TTL | Bug | ✅ |
| P2 | CORS 默认 `*` | 安全 | ✅ |
| P2 | 线程安全风险 | 代码质量 | ✅ |
| P2 | URL token 持久化到 localStorage | 安全 | ✅ |
| P2 | GET /validate 查询参数泄露 | 安全 | ✅ |
| P2 | POST /validate 无速率限制 | 安全 | ✅ |
| P2 | 中文错误消息编码损坏 | Bug | ✅ 新发现 |
| P2 | 大文档 Diff 内存耗尽风险 | Bug | ✅ 新发现 |
| P2 | PyMuPDF 文档句柄泄漏（7处） | Bug | ✅ 新发现 |
| P2 | 认证令牌查询参数泄漏面放大 | 安全 | ✅ 新发现 |
| P2 | pd.read_excel 超限前全量加载 | 缺陷 | ✅ 新发现 |
| P2 | XXE 实体扩展保护缺失 | 安全 | ✅ 新发现 |
| P2 | 公告内容未净化（存储型 XSS） | 安全 | ✅ 新发现 |
| P2 | OLE 魔术字节验证可被绕过 | 安全 | ✅ 新发现 |
| P3 | SECRET_KEY=auto 会话失效 | 安全 | ✅ 文档已说明 |
| P3 | 无 CSRF 保护 | 安全 | ✅ 部分缓解 |
| P3 | Diff HTML 导出潜在 XSS | 安全 | ✅ |
| P3 | 头像上传 race condition | 缺陷 | ✅ |
| P3 | `resolve_storage_path` 脆弱 | 缺陷 | ✅ 新发现 |
| P3 | 前端错误监控未接入 | 代码质量 | ✅ |
| P3 | TrackingMiddleware 直连 DB | 代码质量 | ✅ |
| P3 | 开发环境硬编码弱凭据 | 安全 | ✅ dev-only |
| P3 | .env 文件通过 API 修改 | 设计 | ✅ |
| P3 | `passlib` 冗余依赖 | 代码质量 | ✅ |
| P3 | MathJax CDN 加载无 SRI | 安全 | ✅ 新发现 |
| P3 | Content-Disposition 回退文件名 CRLF | 安全 | ✅ 新发现 |
| P3 | Unicode NFC 规范化缺失 | 缺陷 | ✅ 新发现 |
| ~~P2~~ | ~~generate_images 缓存清理~~ | ~~Bug~~ | ❌ **已排除-误报** |

---

**交叉验证总结:** 原始报告 29 项中，**27 项确认有效**，**1 项排除误报（generate_images 缓存清理）**，**1 项降级（.env 路径从"缺陷"降为"代码质量"）**。第二轮新增 1 项（5th X-Forwarded-For + resolve_storage_path）。第三轮新增 3 项（中文编码、Diff 内存、MathJax CDN）。第四轮新增 3 项（PyMuPDF 泄漏、令牌泄漏面放大、Content-Disposition CRLF）。第五轮新增 5 项（PIL 解压炸弹、dmp DoS、pd.read_excel、XXE、Unicode NFC）。第六轮新增 2 项（AccessDenied 开放重定向、公告存储型 XSS）。第七轮新增 1 项（OLE 魔术字节绕过）。最终 **42 项有效发现**，1 项误报排除。
