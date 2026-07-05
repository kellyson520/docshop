"""统一 diff 结果结构。

各 diff engine 历史上返回过不同字段名：
- DOCX: paragraph_diffs / tables / images
- PDF: page_diffs / table_diffs
- XLSX: sheets / cells / sheet_diffs

这里不丢弃原始字段，只补齐对外稳定消费的 canonical 字段。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping, Optional


CANONICAL_KEYS = ("text", "tables", "images", "metadata", "summary", "stats")
IMAGE_KEYS = ("added", "deleted", "replaced", "resized")


def _as_list(value: Any) -> List[Any]:
    """把可能缺失/单值的字段安全转换为 list。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _empty_images() -> Dict[str, List[Any]]:
    return {key: [] for key in IMAGE_KEYS}


def _normalize_images(value: Any) -> Dict[str, List[Any]]:
    """统一图片 diff 字段，兼容 list 和 dict 两种历史格式。"""
    images = _empty_images()
    if isinstance(value, Mapping):
        for key in IMAGE_KEYS:
            images[key] = _as_list(value.get(key))
        # 兼容旧字段名
        if not images["added"]:
            images["added"] = _as_list(value.get("new") or value.get("additions"))
        if not images["deleted"]:
            images["deleted"] = _as_list(value.get("removed") or value.get("deletions"))
        return images

    # 旧格式若直接给 list，则视为图片变化集合，不猜测类型，放到 added 方便展示。
    if value:
        images["added"] = _as_list(value)
    return images


def _first_list(raw: Mapping[str, Any], keys: Iterable[str]) -> List[Any]:
    for key in keys:
        value = raw.get(key)
        if value is not None:
            return _as_list(value)
    return []


def _count_text_ops(text: List[Any]) -> Dict[str, int]:
    stats = {
        "text_changes": len(text),
        "text_added": 0,
        "text_deleted": 0,
        "text_modified": 0,
        "text_moves": 0,
    }
    for item in text:
        if not isinstance(item, Mapping):
            continue
        op = str(
            item.get("op")
            or item.get("operation")
            or item.get("type")
            or item.get("change_type")
            or ""
        ).lower()
        if "add" in op or op == "insert":
            stats["text_added"] += 1
        elif "delete" in op or "remove" in op:
            stats["text_deleted"] += 1
        elif "move" in op or "reorder" in op:
            stats["text_moves"] += 1
        elif "modify" in op or "replace" in op or "change" in op:
            stats["text_modified"] += 1
    return stats


def _derive_stats(text: List[Any], tables: List[Any], images: Mapping[str, List[Any]]) -> Dict[str, int]:
    stats = _count_text_ops(text)
    stats.update(
        {
            "tables_changed": len(tables),
            "image_added": len(images.get("added", [])),
            "image_deleted": len(images.get("deleted", [])),
            "image_replaced": len(images.get("replaced", [])),
            "image_resized": len(images.get("resized", [])),
        }
    )
    stats["image_changes"] = (
        stats["image_added"]
        + stats["image_deleted"]
        + stats["image_replaced"]
        + stats["image_resized"]
    )
    stats["total_changes"] = stats["text_changes"] + stats["tables_changed"] + stats["image_changes"]
    return stats


def _default_summary(status: str, total_changes: int) -> str:
    if status == "failed":
        return "差异计算失败"
    if total_changes == 0:
        return "未发现差异"
    return f"发现 {total_changes} 处差异"


def normalize_diff_result(
    raw: Optional[Mapping[str, Any]],
    *,
    file_type: Optional[str] = None,
    elapsed_ms: Optional[int] = None,
    status: str = "completed",
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """返回包含 canonical diff 字段的结果。

    Args:
        raw: diff engine 原始返回。
        file_type: 文件类型（docx/pdf/xlsx），写入 metadata 供前端展示。
        elapsed_ms: 计算耗时毫秒。
        status: completed/failed 等任务状态。
        error: 失败摘要。
    """
    result: Dict[str, Any] = deepcopy(dict(raw or {}))

    changes = result.get("changes")
    if not isinstance(changes, Mapping):
        changes = {}

    text = _first_list(
        result,
        ("text", "paragraph_diffs", "page_diffs", "cell_diffs", "cells", "sheets", "sheet_diffs"),
    )
    if not text:
        text = _as_list(changes.get("text"))

    tables = _first_list(result, ("tables", "table_diffs"))
    if not tables:
        tables = _as_list(changes.get("tables"))

    images = _normalize_images(result.get("images") or changes.get("images"))

    nodes = _as_list(result.get("nodes") or changes.get("nodes"))
    attributes = _as_list(result.get("attributes") or changes.get("attributes"))
    resources = _as_list(result.get("resources") or changes.get("resources"))

    metadata = dict(result.get("metadata") or changes.get("metadata") or {})
    if file_type:
        metadata["file_type"] = file_type
    if elapsed_ms is not None:
        metadata["elapsed_ms"] = int(elapsed_ms)

    derived_stats = _derive_stats(text, tables, images)
    stats = dict(derived_stats)
    stats.update(result.get("stats") or changes.get("stats") or {})
    # 关键聚合字段以后端 normalizer 为准，避免 legacy stats 漏计图片/表格。
    stats["text_changes"] = derived_stats["text_changes"]
    stats["tables_changed"] = derived_stats["tables_changed"]
    stats["image_added"] = derived_stats["image_added"]
    stats["image_deleted"] = derived_stats["image_deleted"]
    stats["image_replaced"] = derived_stats["image_replaced"]
    stats["image_resized"] = derived_stats["image_resized"]
    stats["image_changes"] = derived_stats["image_changes"]
    stats["total_changes"] = derived_stats["total_changes"]

    summary = result.get("summary") or changes.get("summary") or _default_summary(status, stats["total_changes"])

    result.update(
        {
            "text": text,
            "tables": tables,
            "images": images,
            "nodes": nodes,
            "attributes": attributes,
            "resources": resources,
            "metadata": metadata,
            "summary": summary,
            "stats": stats,
            "status": status,
            "error": error,
            "changes": {
                "text": text,
                "tables": tables,
                "images": images,
                "nodes": nodes,
                "attributes": attributes,
                "resources": resources,
                "metadata": metadata,
                "summary": summary,
                "stats": stats,
            },
        }
    )
    return result
