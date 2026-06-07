"""
安全工具模块
- file_integrity_ok(): 验证文件 SHA-256 与预期值匹配
- log_security_event(): 安全事件审计日志
"""

import hashlib
import os
from pathlib import Path


def file_sha256(path: str) -> str:
    """计算文件 SHA-256 哈希。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def file_integrity_ok(path: str, expected_hash: str) -> bool:
    """
    验证文件完整性：读取磁盘文件，与数据库记录的文件哈希比对。

    Returns:
        True 若哈希匹配，False 若文件不存在或哈希不一致。
    """
    if not os.path.exists(path):
        return False
    try:
        actual = file_sha256(path)
        return actual == expected_hash
    except OSError:
        return False


def log_security_event(logger, event_type: str, resource: str, user_id: str = "unknown", **ctx):
    """
    记录安全相关事件到审计日志。

    Args:
        logger: 日志器实例
        event_type: "FILE_INTEGRITY_FAIL" | "UPLOAD_SIZE_EXCEED" | "RATE_LIMIT_HIT" | ...
        resource: 资源标识（file_id / project_id）
        user_id: 触发用户
        **ctx: 额外上下文
    """
    logger.warning(
        f"SECURITY | {event_type} | user={user_id} | resource={resource} | "
        + " ".join(f"{k}={v}" for k, v in ctx.items())
    )
