"""
差异计算服务模块

提供文档版本之间的差异计算功能。
支持多种文件类型的差异比较，包括 DOCX、XLSX、PDF 等。
"""

import json
import os
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.file_version import FileVersion
from app.models.document_file import DocumentFile
from app.models.diff_record import DiffRecord
from app.diff_engine.factory import get_diff_engine
from app.exceptions import ResourceNotFound, DiffCalculationError
from app.schemas.diff_result import normalize_diff_result
from app.utils.logger import get_logger, log_audit

# 获取模块日志器
diff_logger = get_logger("services.diff_service")


def compute_diff(old_version_id: str, new_version_id: str, db: Session) -> DiffRecord:
    """
    计算两个文件版本之间的差异并保存结果。

    Args:
        old_version_id: 旧版本ID
        new_version_id: 新版本ID
        db: 数据库会话

    Returns:
        DiffRecord: 差异记录

    Raises:
        ResourceNotFound: 版本或文件记录不存在时抛出
        DiffCalculationError: 差异计算失败时抛出
    """
    diff_logger.info(f"开始计算差异 - old: {old_version_id}, new: {new_version_id}")

    # 获取版本记录
    old_version = db.query(FileVersion).filter(FileVersion.id == old_version_id).first()
    new_version = db.query(FileVersion).filter(FileVersion.id == new_version_id).first()

    if not old_version:
        raise ResourceNotFound(resource="文件版本", resource_id=old_version_id)
    if not new_version:
        raise ResourceNotFound(resource="文件版本", resource_id=new_version_id)

    # 获取文件记录以确定文件类型
    doc_file = db.query(DocumentFile).filter(DocumentFile.id == new_version.file_id).first()
    if not doc_file:
        raise ResourceNotFound(resource="文件记录", resource_id=new_version.file_id)

    # 文件存在性预检查
    if not os.path.exists(old_version.storage_path):
        raise ResourceNotFound(
            resource="旧版本文件",
            resource_id=old_version.storage_path,
        )
    if not os.path.exists(new_version.storage_path):
        raise ResourceNotFound(
            resource="新版本文件",
            resource_id=new_version.storage_path,
        )

    # 获取差异计算引擎
    try:
        engine = get_diff_engine(doc_file.file_type)
    except Exception as e:
        diff_logger.error(f"获取差异引擎失败 - file_type: {doc_file.file_type}, 错误: {e}")
        raise DiffCalculationError(
            message=f"不支持的文件类型: {doc_file.file_type}",
            file_type=doc_file.file_type,
        )

    # 执行差异计算
    try:
        started_at = time.perf_counter()
        diff_result = engine.compare(old_version.storage_path, new_version.storage_path)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        diff_result = normalize_diff_result(
            diff_result,
            file_type=doc_file.file_type,
            elapsed_ms=elapsed_ms,
            status="completed",
            error=None,
        )
    except Exception as e:
        diff_logger.error(
            f"差异引擎计算失败 - old: {old_version.storage_path}, "
            f"new: {new_version.storage_path}, 错误: {e}",
            exc_info=True,
        )
        raise DiffCalculationError(
            message=f"差异计算过程中发生错误: {str(e)}",
            file_type=doc_file.file_type,
        )

    # 确定差异类型
    diff_type_map = {
        "docx_diff": "text",
        "xlsx_diff": "cell",
        "pdf_diff": "visual",
    }
    diff_type = diff_type_map.get(diff_result.get("type", ""), "text")

    # 创建差异记录
    diff_record = DiffRecord(
        old_version_id=old_version_id,
        new_version_id=new_version_id,
        diff_type=diff_type,
        diff_data=json.dumps(diff_result, ensure_ascii=False),
        summary=diff_result.get("summary", ""),
    )

    db.add(diff_record)
    db.commit()
    db.refresh(diff_record)

    # 审计日志
    log_audit(
        user_id="system",
        action="compute_diff",
        resource=f"diff:{diff_record.id}",
        result="success",
        details=f"old_version={old_version_id}, new_version={new_version_id}, type={diff_type}",
    )

    diff_logger.info(f"差异计算完成 - diff_id: {diff_record.id}, type: {diff_type}")

    return diff_record
