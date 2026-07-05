"""
文档持久化存储层 — 三层平行结构

每个文档目录:  data/documents/{file_id}/
  ├── original/    原始上传文件
  ├── pdf/         PDF 版本（Word→PDF 转换结果）
  ├── images/      页面图片（page_001.jpg ... page_NNN.jpg）
  └── meta.json    缓存元数据（哈希、页数、生成时间）

设计要点:
  - SHA-256 哈希驱动缓存失效 → 原始文件变了才重新生成
  - 图片固定用 JPEG (quality=85)，比 PNG 快 3-5× 且体积小
  - 多页并行渲染 (ThreadPoolExecutor, max_workers=4)
  - original/ 下只存一个 symlink/副本，由 upload 流程写入
"""

import os
import json
import hashlib
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("services.document_store")

# ── 存储根目录 ──
ROOT = str(settings.documents_dir)


def _path_under_root(*parts: str) -> str:
    """Resolve a document-store path and ensure it stays inside ROOT."""
    root = Path(ROOT).resolve()
    target = root.joinpath(*[str(part) for part in parts]).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"非法文档存储路径: {target}") from exc
    return str(target)


def doc_root(file_id: str) -> str:
    return _path_under_root(file_id)


def dir_original(file_id: str) -> str:
    return _path_under_root(file_id, "original")


def dir_pdf(file_id: str) -> str:
    return _path_under_root(file_id, "pdf")


def dir_images(file_id: str) -> str:
    return _path_under_root(file_id, "images")


def dir_page_images(file_id: str, pdf_hash: str) -> str:
    """按 PDF hash 判断已缓存页面是否仍可复用。"""
    safe_hash = (pdf_hash or "unknown")[:16]
    return os.path.join(dir_images(file_id), safe_hash)



def meta_path(file_id: str) -> str:
    return _path_under_root(file_id, "meta.json")


def _ensure_dirs(file_id: str) -> None:
    for d in [dir_original(file_id), dir_pdf(file_id), dir_images(file_id)]:
        os.makedirs(d, exist_ok=True)


# ── 哈希 ──

def file_sha256(path: str) -> str:
    """公开 SHA-256 — 供上传流程去重使用。"""
    return _file_sha256(path)


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _read_meta(file_id: str) -> Dict[str, Any]:
    mp = meta_path(file_id)
    if os.path.exists(mp):
        try:
            with open(mp, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _write_meta(file_id: str, data: Dict[str, Any]) -> None:
    _ensure_dirs(file_id)
    mp = meta_path(file_id)
    tmp = mp + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, mp)


def update_preview_meta(file_id: str, **updates: Any) -> Dict[str, Any]:
    """Merge preview generation state into meta.json and return the preview object."""
    meta = _read_meta(file_id)
    preview = dict(meta.get("preview") or {})
    preview.update(updates)
    preview["updated_at"] = _now_iso()
    meta["preview"] = preview
    _write_meta(file_id, meta)
    return preview


def preview_storage_bytes(file_id: str) -> int:
    """Return generated preview cache size (pdf/ + images/), excluding original/."""
    total = 0
    for root_dir in (dir_pdf(file_id), dir_images(file_id)):
        if not os.path.isdir(root_dir):
            continue
        for current_root, _dirs, files in os.walk(root_dir):
            for name in files:
                path = os.path.join(current_root, name)
                try:
                    total += os.path.getsize(path)
                except OSError:
                    pass
    return total


def clear_preview_cache(file_id: str) -> Dict[str, Any]:
    """Remove generated preview artifacts while preserving original uploads."""
    removed_bytes = preview_storage_bytes(file_id)
    for root_dir in (dir_pdf(file_id), dir_images(file_id)):
        if os.path.isdir(root_dir):
            shutil.rmtree(root_dir, ignore_errors=True)
        os.makedirs(root_dir, exist_ok=True)

    meta = _read_meta(file_id)
    for key in (
        "pdf_source_hash",
        "pdf_generated_at",
        "pdf_image_hash",
        "page_count",
        "image_dpi",
        "image_quality",
        "images_generated_at",
        "pdf_conversion_failed_hash",
        "pdf_conversion_failed_at",
    ):
        meta.pop(key, None)
    meta["preview"] = {
        "status": "missing",
        "progress": 0,
        "stage": "预览缓存已清理",
        "queued_at": None,
        "started_at": None,
        "updated_at": _now_iso(),
        "finished_at": None,
        "error": None,
        "storage_bytes": 0,
    }
    _write_meta(file_id, meta)
    return {"file_id": file_id, "removed_bytes": removed_bytes}


# ── 哈希 → file_id 反向索引（跨上传去重）──

HASH_INDEX_DIR = os.path.join(ROOT, ".hash_index")


def _hash_index_path(source_hash: str) -> str:
    """hash 前2位 → 子目录，防单目录文件过多。"""
    prefix = source_hash[:2]
    d = os.path.join(HASH_INDEX_DIR, prefix)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, source_hash)


def register_hash(source_hash: str, file_id: str) -> None:
    """注册哈希 → file_id 映射，用于后续上传去重。"""
    p = _hash_index_path(source_hash)
    try:
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, file_id.encode("utf-8"))
        finally:
            os.close(fd)
    except FileExistsError:
        pass


def _lookup_hash(source_hash: str) -> Optional[str]:
    """查询哈希对应的 file_id，没有返回 None。"""
    p = _hash_index_path(source_hash)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            pass
    return None


def find_existing_file_id(source_path: str) -> Optional[str]:
    """
    根据文件内容哈希查找是否已有相同的文件。
    有则返回已有 file_id（可复用其 document_store），无则返回 None。
    """
    h = file_sha256(source_path)
    fid = _lookup_hash(h)
    if fid:
        logger.info(f"哈希去重命中: {source_path} → {fid}")
    return fid


def ensure_registered(file_id: str, source_path: str) -> None:
    """上传完成后注册哈希索引，供后续去重。"""
    h = file_sha256(source_path)
    register_hash(h, file_id)
    # 同时在 meta 中记录
    meta = _read_meta(file_id)
    meta["original_hash"] = h
    _write_meta(file_id, meta)
    logger.info(f"哈希索引已注册: {h[:16]} → {file_id}")


# ── 原始文件 ──

def store_original(file_id: str, source_path: str) -> str:
    """将上传的原始文件存入 original/ 目录，返回存储路径。"""
    _ensure_dirs(file_id)
    ext = os.path.splitext(source_path)[-1] or ".bin"
    dest = os.path.join(dir_original(file_id), f"original{ext}")
    if os.path.abspath(source_path) != os.path.abspath(dest):
        shutil.copy2(source_path, dest)
    return dest


# ── PDF 版本 ──

def get_cached_pdf(file_id: str, source_hash: str) -> Optional[str]:
    """
    检查是否有有效的缓存 PDF。
    比较 meta 中记录的 pdf_source_hash 与当前源哈希。
    """
    meta = _read_meta(file_id)
    if meta.get("pdf_source_hash") != source_hash:
        return None
    path = os.path.join(dir_pdf(file_id), "document.pdf")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        logger.info(f"PDF 缓存命中: {path}")
        return path
    return None


def store_pdf(file_id: str, pdf_path: str, source_hash: str) -> str:
    """将 PDF 存入 pdf/ 目录并更新 meta。"""
    _ensure_dirs(file_id)
    dest = os.path.join(dir_pdf(file_id), "document.pdf")
    if os.path.abspath(pdf_path) != os.path.abspath(dest):
        shutil.copy2(pdf_path, dest)
    meta = _read_meta(file_id)
    meta["pdf_source_hash"] = source_hash
    meta["pdf_generated_at"] = _now_iso()
    _write_meta(file_id, meta)
    logger.info(f"PDF 已持久化: {dest}")
    return dest


# ── 图片版本 ──

def get_cached_images(file_id: str, pdf_hash: str, expected_pages: int) -> Optional[List[str]]:
    """
    检查是否有有效的缓存图片。
    要求: meta.pdf_image_hash 匹配 且 图片数量 == expected_pages。
    """
    meta = _read_meta(file_id)
    if meta.get("pdf_image_hash") != pdf_hash:
        return None
    img_dir = dir_images(file_id)
    if not os.path.isdir(img_dir):
        return None
    files = sorted([
        f for f in os.listdir(img_dir)
        if f.startswith("page_") and f.endswith(".jpg")
    ])
    if len(files) == expected_pages and all(
        os.path.getsize(os.path.join(img_dir, f)) > 0 for f in files
    ):
        logger.info(f"图片缓存命中: {len(files)} 页")
        return [os.path.join(img_dir, f) for f in files]
    return None


def _render_page(args: tuple) -> str:
    """渲染单页 → JPEG，用于 ThreadPoolExecutor。"""
    i, pdf_path, img_dir, dpi, quality = args
    import fitz
    doc = fitz.open(pdf_path)
    try:
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        out = os.path.join(img_dir, f"page_{i+1:04d}.jpg")
        pix.pil_save(out, format="JPEG", quality=quality, optimize=True)
        return out
    finally:
        doc.close()


def render_single_page(
    file_id: str,
    pdf_path: str,
    page_num: int,
    page_count: int,
    pdf_hash: str,
    dpi: Optional[int] = None,
    quality: int = 75,
) -> str:
    """渲染单页 JPEG。

    使用 PDF hash 管理缓存目录，避免旧页面/串页。
    page_0001.jpg 等文件用于按页懒加载预览。
    """
    if page_num < 1 or page_num > page_count:
        raise IndexError(f"Page {page_num} out of range: 1..{page_count}")
    if dpi is None:
        dpi = adaptive_dpi(page_count)
    _ensure_dirs(file_id)
    img_dir = dir_page_images(file_id, pdf_hash)
    os.makedirs(img_dir, exist_ok=True)
    img_path = os.path.join(img_dir, f"page_{page_num:04d}.jpg")
    if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
        return img_path
    return _render_page((page_num - 1, pdf_path, img_dir, dpi, quality))


def adaptive_dpi(page_count: int) -> int:
    """根据页数自适应 DPI，平衡质量与速度。"""
    if page_count <= 50:
        return 150
    if page_count <= 200:
        return 120
    if page_count <= 500:
        return 100
    if page_count <= 1000:
        return 80
    return 60


def generate_images(
    file_id: str,
    pdf_path: str,
    page_count: int,
    pdf_hash: str,
    dpi: int = 120,
    quality: int = 75,
    max_workers: int = 6,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[str]:
    """
    PDF → 多页 JPEG 并行渲染，持久化到 images/ 目录。
    返回图片路径列表（按页码排序）。
    """
    img_dir = dir_images(file_id)
    _ensure_dirs(file_id)

    # 清理旧图片
    for f in os.listdir(img_dir):
        if f.startswith("page_") and f.endswith(".jpg"):
            os.unlink(os.path.join(img_dir, f))

    t0 = __import__("time").time()
    import fitz

    # 并行渲染：每个 worker 独立打开 PDF（PyMuPDF C核心支持并发读）
    tasks = [(i, pdf_path, img_dir, dpi, quality) for i in range(page_count)]

    results: List[tuple] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_render_page, t): t[0] for t in tasks}
        for fut in as_completed(futures):
            page_idx = futures[fut]
            try:
                path = fut.result()
                results.append((page_idx, path))
                completed += 1
                if progress_callback:
                    progress_callback(completed, page_count)
            except Exception as e:
                logger.error(f"第 {page_idx+1} 页渲染失败: {e}")

    # 按页码排序
    results.sort(key=lambda x: x[0])
    paths = [r[1] for r in results]

    elapsed = __import__("time").time() - t0
    total_kb = sum(os.path.getsize(p) for p in paths if os.path.exists(p)) // 1024
    logger.info(
        f"图片生成完成: {len(paths)}/{page_count} 页, "
        f"{total_kb}KB, {elapsed:.1f}s, workers={max_workers}"
    )

    # 持久化 meta
    meta = _read_meta(file_id)
    meta["pdf_image_hash"] = pdf_hash
    meta["page_count"] = page_count
    meta["image_dpi"] = dpi
    meta["image_quality"] = quality
    meta["images_generated_at"] = _now_iso()
    _write_meta(file_id, meta)

    return paths


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
