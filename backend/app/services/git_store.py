"""
Git 风格的内容寻址存储引擎

借鉴 Git 的设计：
- 按 SHA-256 哈希存储对象（去重）
- 支持 delta 链：base → delta1 → delta2 → ...
- 稀疏检出：按需重建任意版本
- pack 索引：加速查找
"""

import os
import json
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("storage.git_store")


class GitStore:
    """Git 风格的对象存储"""

    def __init__(self):
        self.objects_dir = Path(settings.UPLOAD_DIR).parent / "objects"
        self.refs_dir = self.objects_dir / "refs"
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self.refs_dir.mkdir(parents=True, exist_ok=True)

    # ---- 核心：内容寻址存储 ----

    def put_object(self, content: bytes) -> str:
        """存储对象，返回 SHA-256 哈希（去重）"""
        h = hashlib.sha256(content).hexdigest()
        obj_path = self.objects_dir / h[:2] / h[2:]
        if not obj_path.exists():
            obj_path.parent.mkdir(parents=True, exist_ok=True)
            obj_path.write_bytes(content)
            logger.debug(f"Object stored: {h[:12]}... ({len(content)} bytes)")
        else:
            logger.debug(f"Object deduplicated: {h[:12]}...")
        return h

    def get_object(self, obj_hash: str) -> Optional[bytes]:
        """读取对象"""
        obj_path = self.objects_dir / obj_hash[:2] / obj_hash[2:]
        if obj_path.exists():
            return obj_path.read_bytes()
        return None

    def object_exists(self, obj_hash: str) -> bool:
        return (self.objects_dir / obj_hash[:2] / obj_hash[2:]).exists()

    # ---- Delta 链 ----

    def put_delta_chain(self, chain: List[dict]) -> str:
        """存储 delta 链（JSON），返回链的哈希"""
        data = json.dumps(chain, ensure_ascii=False).encode()
        return self.put_object(data)

    def get_delta_chain(self, chain_hash: str) -> Optional[List[dict]]:
        """读取 delta 链"""
        data = self.get_object(chain_hash)
        if data:
            return json.loads(data)
        return None

    # ---- 版本引用（类似 Git refs） ----

    def update_ref(self, file_id: str, version: int, obj_hash: str, mode: str = "full"):
        """更新版本引用"""
        ref_dir = self.refs_dir / file_id
        ref_dir.mkdir(parents=True, exist_ok=True)
        ref_file = ref_dir / f"v{version}"
        ref_file.write_text(json.dumps({
            "hash": obj_hash,
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }))

    def get_ref(self, file_id: str, version: int) -> Optional[dict]:
        """读取版本引用"""
        ref_file = self.refs_dir / file_id / f"v{version}"
        if ref_file.exists():
            return json.loads(ref_file.read_text())
        return None

    def list_refs(self, file_id: str) -> List[int]:
        """列出文件的所有版本号"""
        ref_dir = self.refs_dir / file_id
        if not ref_dir.exists():
            return []
        versions = []
        for f in ref_dir.iterdir():
            if f.name.startswith("v"):
                try:
                    versions.append(int(f.name[1:]))
                except ValueError:
                    pass
        return sorted(versions)

    # ---- 重建 ----

    def reconstruct(self, file_id: str, target_version: int) -> Optional[bytes]:
        """从 delta 链重建目标版本"""
        versions = self.list_refs(file_id)
        if target_version not in versions:
            return None

        # 找到最近的 full 版本
        base_ver = None
        for v in reversed(range(1, target_version + 1)):
            ref = self.get_ref(file_id, v)
            if ref and ref.get("mode") == "full":
                base_ver = v
                break

        if base_ver is None:
            return None

        # 从基版本开始，依次应用 delta
        ref = self.get_ref(file_id, base_ver)
        current = self.get_object(ref["hash"])
        if current is None:
            return None

        for v in range(base_ver + 1, target_version + 1):
            ref = self.get_ref(file_id, v)
            if not ref:
                continue
            chain = self.get_delta_chain(ref["hash"])
            if not chain:
                # 不是 delta，直接读取
                current = self.get_object(ref["hash"])
                continue
            # 应用 delta 链
            current = self._apply_delta_chain(current, chain)

        return current

    def _apply_delta_chain(self, base: bytes, chain: List[dict]) -> bytes:
        """应用 delta 链到基版本"""
        try:
            diff_data = json.loads(base) if isinstance(base, bytes) else base
            if not isinstance(diff_data, dict):
                return base

            for delta in chain:
                ops = delta.get("operations", [])
                for op in ops:
                    if op.get("type") == "replace_paragraph":
                        idx = op.get("index", 0)
                        text = op.get("text", "")
                        paragraphs = diff_data.get("paragraphs", [])
                        if idx < len(paragraphs):
                            paragraphs[idx] = text
                        elif idx == len(paragraphs):
                            paragraphs.append(text)
                    elif op.get("type") == "insert_paragraph":
                        text = op.get("text", "")
                        diff_data.setdefault("paragraphs", []).append(text)
                    elif op.get("type") == "delete_paragraph":
                        idx = op.get("index", 0)
                        paragraphs = diff_data.get("paragraphs", [])
                        if idx < len(paragraphs):
                            paragraphs.pop(idx)

            return json.dumps(diff_data, ensure_ascii=False).encode()
        except Exception:
            return base

    # ---- 存储统计 ----

    def get_stats(self) -> dict:
        """获取存储统计"""
        total_objects = 0
        total_size = 0
        if self.objects_dir.exists():
            for obj in self.objects_dir.rglob("*"):
                if obj.is_file() and obj.parent.name != "refs":
                    total_objects += 1
                    total_size += obj.stat().st_size

        total_refs = 0
        if self.refs_dir.exists():
            for ref in self.refs_dir.rglob("v*"):
                if ref.is_file():
                    total_refs += 1

        return {
            "objects": total_objects,
            "total_size": total_size,
            "size_human": self._human_size(total_size),
            "refs": total_refs,
            "dedup_saved": self._estimate_saved(),
        }

    def _human_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _estimate_saved(self) -> str:
        """估算去重节省的空间"""
        if not self.objects_dir.exists():
            return "0 B"
        # 简单估算：总对象数 vs 唯一哈希数
        all_hashes = set()
        total = 0
        for d in self.objects_dir.iterdir():
            if d.is_dir() and len(d.name) == 2:
                for f in d.iterdir():
                    if f.is_file():
                        total += 1
                        all_hashes.add(d.name + f.name)
        saved = total - len(all_hashes)
        return f"{saved} duplicates" if saved > 0 else "0 duplicates"


# 全局实例
git_store = GitStore()
