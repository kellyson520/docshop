"""
文件校验模块

提供文件类型验证、文件名清理、文件大小检查等功能。
使用 Magic Bytes 和 MIME 类型双重验证确保文件类型安全。
"""

import os
import re
import struct
import zipfile
from pathlib import Path
from typing import Optional, Tuple, BinaryIO
from io import BytesIO

from app.config import settings
from app.exceptions import FileValidationError
from app.utils.logger import logger

# 允许的 MIME 类型映射
ALLOWED_MIME_TYPES = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'application/msword': '.doc',
    'application/vnd.ms-excel': '.xls',
}

# 文件类型签名（Magic Bytes）
FILE_TYPE_SIGNATURES = {
    b'%PDF': '.pdf',
    b'PK\x03\x04': 'zip',  # ZIP格式，需要进一步判断（DOCX/XLSX 都是 ZIP 格式）
    b'\xd0\xcf\x11\xe0': 'ole',  # OLE 格式（旧版 DOC/XLS）
}

# 文件头读取大小
HEADER_SIZE = 8


def validate_file_type(file_path: Path, declared_filename: str) -> str:
    """
    验证文件类型
    
    通过文件扩展名、文件大小、文件头签名和 MIME 类型多重验证文件类型。
    防止伪造文件扩展名攻击。
    
    Args:
        file_path: 文件路径
        declared_filename: 声明的文件名（用户上传时的文件名）
        
    Returns:
        str: 文件类型 ('pdf', 'docx', 'xlsx', 'doc', 'xls')
        
    Raises:
        FileValidationError: 文件校验失败时抛出
    """
    logger.debug(f"开始验证文件: {declared_filename}, 路径: {file_path}")
    
    try:
        # 1. 检查文件扩展名
        ext = _validate_extension(declared_filename)
        logger.debug(f"文件扩展名验证通过: {ext}")
        
        # 2. 检查文件是否存在且可读
        _validate_file_exists(file_path)
        
        # 3. 检查文件大小
        _validate_file_size(file_path)
        
        # 4. 检查文件头签名
        detected_type = _detect_file_type_by_signature(file_path)
        logger.debug(f"文件签名检测类型: {detected_type}")
        
        # 5. 验证文件头与扩展名是否匹配
        actual_type = _validate_file_consistency(file_path, ext, detected_type)
        logger.debug(f"文件一致性验证通过，实际类型: {actual_type}")
        
        return actual_type
        
    except FileValidationError:
        raise
    except Exception as e:
        logger.error(f"文件验证过程中发生未知错误: {e}", exc_info=True)
        raise FileValidationError(
            message=f"文件验证失败: {str(e)}",
            filename=declared_filename
        )


def _validate_extension(filename: str) -> str:
    """
    验证文件扩展名
    
    Args:
        filename: 文件名
        
    Returns:
        str: 小写的扩展名
        
    Raises:
        FileValidationError: 扩展名不合法时抛出
    """
    ext = Path(filename).suffix.lower()
    
    if not ext:
        raise FileValidationError(
            message="文件缺少扩展名",
            filename=filename,
            reason="missing_extension"
        )
    
    if ext not in settings.ALLOWED_FILE_TYPES:
        raise FileValidationError(
            message=f"不支持的文件类型: {ext}",
            filename=filename,
            reason="unsupported_type"
        )
    
    return ext


def _validate_file_size(file_path: Path) -> None:
    """
    验证文件大小
    
    Args:
        file_path: 文件路径
        
    Raises:
        FileValidationError: 文件大小不符合要求时抛出
    """
    try:
        file_size = file_path.stat().st_size
        
        if file_size == 0:
            raise FileValidationError(
                message="文件不能为空",
                reason="empty_file"
            )
        
        if file_size > settings.MAX_FILE_SIZE:
            max_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise FileValidationError(
                message=f"文件大小超过限制: 最大 {max_mb:.1f}MB, 实际 {actual_mb:.1f}MB",
                reason="file_too_large"
            )
        
        logger.debug(f"文件大小验证通过: {file_size} bytes")
        
    except FileValidationError:
        raise
    except Exception as e:
        logger.error(f"检查文件大小时出错: {e}")
        raise FileValidationError(
            message=f"无法读取文件大小: {str(e)}",
            reason="size_check_failed"
        )


def _validate_file_exists(file_path: Path) -> None:
    """
    验证文件是否存在且可读
    
    Args:
        file_path: 文件路径
        
    Raises:
        FileValidationError: 文件不存在或不可读时抛出
    """
    if not file_path.exists():
        raise FileValidationError(
            message=f"文件不存在: {file_path}",
            reason="file_not_found"
        )
    
    if not file_path.is_file():
        raise FileValidationError(
            message=f"路径不是文件: {file_path}",
            reason="not_a_file"
        )
    
    if not os.access(file_path, os.R_OK):
        raise FileValidationError(
            message=f"文件不可读: {file_path}",
            reason="file_not_readable"
        )


def _detect_file_type_by_signature(file_path: Path) -> str:
    """
    通过文件头签名检测文件类型
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 检测到的文件类型标识
        
    Raises:
        FileValidationError: 无法识别文件类型时抛出
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(HEADER_SIZE)
        
        if len(header) < 4:
            raise FileValidationError(
                message="文件头信息不足，无法识别文件类型",
                reason="insufficient_header"
            )
        
        # 检查 PDF
        if header.startswith(b'%PDF'):
            return 'pdf'
        
        # 检查 ZIP 格式（DOCX/XLSX）
        if header.startswith(b'PK\x03\x04'):
            return _detect_zip_content_type(file_path)
        
        # 检查 OLE 格式（旧版 DOC/XLS）
        if header.startswith(b'\xd0\xCF\x11\xE0'):
            return _detect_ole_content_type(file_path)
        
        # 尝试使用 python-magic（如果可用）
        try:
            import magic
            mime = magic.from_file(str(file_path), mime=True)
            if mime in ALLOWED_MIME_TYPES:
                return ALLOWED_MIME_TYPES[mime].lstrip('.')
        except ImportError:
            logger.debug("python-magic 不可用，跳过 MIME 检测")
        except Exception as e:
            logger.warning(f"Magic 检测失败: {e}")
        
        raise FileValidationError(
            message="无法识别的文件格式",
            reason="unknown_format"
        )
        
    except FileValidationError:
        raise
    except Exception as e:
        logger.error(f"检测文件签名时出错: {e}")
        raise FileValidationError(
            message=f"文件签名检测失败: {str(e)}",
            reason="signature_check_failed"
        )


# ZIP 炸弹防御常量
_MAX_ZIP_ENTRY_SIZE = 10 * 1024 * 1024  # 单条目最大未压缩大小 10MB
_MAX_ZIP_COMPRESSION_RATIO = 100  # 最大压缩比（压缩前/压缩后）


def _detect_zip_content_type(file_path: Path) -> str:
    """
    检测 ZIP 压缩包内的文件类型（用于 DOCX/XLSX）
    
    Args:
        file_path: ZIP 文件路径
        
    Returns:
        str: 'docx' 或 'xlsx'
        
    Raises:
        FileValidationError: 无法识别或检测到 ZIP 炸弹时抛出
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            namelist = zf.namelist()

            # ZIP 炸弹防御：遍历所有条目检查压缩比和未压缩大小
            total_uncompressed = 0
            for entry_name in namelist:
                try:
                    info = zf.getinfo(entry_name)
                    total_uncompressed += info.file_size
                    if info.file_size > _MAX_ZIP_ENTRY_SIZE:
                        raise FileValidationError(
                            message=f"ZIP 条目过大: {entry_name}",
                            reason="zip_bomb_size"
                        )
                    if info.compress_size > 0 and (info.file_size / info.compress_size) > _MAX_ZIP_COMPRESSION_RATIO:
                        raise FileValidationError(
                            message=f"ZIP 条目压缩比异常: {entry_name}",
                            reason="zip_bomb_ratio"
                        )
                except (KeyError, FileValidationError):
                    raise
                except Exception:
                    continue
            if total_uncompressed > _MAX_ZIP_ENTRY_SIZE * 5:
                raise FileValidationError(
                    message="ZIP 文件总未压缩大小超出限制",
                    reason="zip_bomb_total_size"
                )

            # 检查 DOCX 特征文件
            if 'word/document.xml' in namelist:
                return 'docx'

            # 检查 XLSX 特征文件
            if 'xl/workbook.xml' in namelist:
                return 'xlsx'
            
            # 检查 [Content_Types].xml 中的类型声明
            if '[Content_Types].xml' in namelist:
                # ZIP 炸弹防御：检查压缩比和未压缩大小
                info = zf.getinfo('[Content_Types].xml')
                if info.file_size > _MAX_ZIP_ENTRY_SIZE:
                    raise FileValidationError(
                        message="文件条目过大，可能是压缩炸弹攻击",
                        reason="zip_bomb_size"
                    )
                if info.compress_size > 0 and (info.file_size / info.compress_size) > _MAX_ZIP_COMPRESSION_RATIO:
                    raise FileValidationError(
                        message="文件压缩比异常，可能是压缩炸弹攻击",
                        reason="zip_bomb_ratio"
                    )
                try:
                    content_types = zf.read('[Content_Types].xml').decode('utf-8', errors='ignore')
                    if 'wordprocessingml.document' in content_types:
                        return 'docx'
                    if 'spreadsheetml.sheet' in content_types:
                        return 'xlsx'
                except Exception as e:
                    logger.warning(f"解析 Content_Types.xml 失败: {e}")
        
        raise FileValidationError(
            message="无法识别的 ZIP 文件内容",
            reason="unknown_zip_content"
        )
        
    except zipfile.BadZipFile:
        raise FileValidationError(
            message="文件不是有效的 ZIP 格式",
            reason="invalid_zip"
        )
    except Exception as e:
        logger.error(f"检测 ZIP 内容时出错: {e}")
        raise FileValidationError(
            message=f"ZIP 文件检测失败: {str(e)}",
            reason="zip_check_failed"
        )


def _detect_ole_content_type(file_path: Path) -> str:
    """
    检测 OLE 格式文件类型（旧版 DOC/XLS）
    
    Args:
        file_path: OLE 文件路径
        
    Returns:
        str: 'doc' 或 'xls'
    """
    try:
        # 读取更多内容来检测 OLE 类型
        with open(file_path, 'rb') as f:
            content = f.read(4096)
        
        # 检查 WordDocument 流
        if b'WordDocument' in content:
            return 'doc'
        
        # 检查 Workbook 流
        if b'Workbook' in content or b'Book' in content:
            return 'xls'
        
        # 尝试使用 olefile 库
        try:
            import olefile
            ole = olefile.OleFileIO(file_path)
            streams = ole.listdir()
            
            for stream in streams:
                stream_name = '/'.join(stream)
                if 'WordDocument' in stream_name:
                    ole.close()
                    return 'doc'
                if 'Workbook' in stream_name or 'Book' in stream_name:
                    ole.close()
                    return 'xls'
            
            ole.close()
        except ImportError:
            logger.debug("olefile 库不可用")
        
        # 如果无法确定，根据扩展名信任
        logger.warning("无法准确检测 OLE 文件类型，将信任文件扩展名")
        return 'doc'  # 默认假设为 doc
        
    except Exception as e:
        logger.error(f"检测 OLE 类型时出错: {e}")
        return 'doc'


def _validate_file_consistency(file_path: Path, declared_ext: str, detected_type: str) -> str:
    """
    验证声明的文件类型与实际类型是否一致
    
    Args:
        file_path: 文件路径
        declared_ext: 声明的扩展名
        detected_type: 检测到的类型
        
    Returns:
        str: 验证通过的文件类型
        
    Raises:
        FileValidationError: 类型不一致时抛出
    """
    # 扩展名到类型的映射
    ext_to_type = {
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.xlsx': 'xlsx',
        '.doc': 'doc',
        '.xls': 'xls',
    }
    
    declared_type = ext_to_type.get(declared_ext)
    
    if declared_type != detected_type:
        # 允许某些兼容情况
        compatible_pairs = [
            ('doc', 'docx'),  # 旧版 Word 可能被识别为新版
            ('xls', 'xlsx'),  # 旧版 Excel 可能被识别为新版
        ]
        
        if (declared_type, detected_type) not in compatible_pairs:
            raise FileValidationError(
                message=f"文件头与扩展名不符: 声明为 {declared_ext}, 实际为 {detected_type}",
                reason="type_mismatch"
            )
    
    return detected_type


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    清理文件名，移除危险字符
    
    防止路径遍历攻击和文件名注入攻击。
    
    Args:
        filename: 原始文件名
        max_length: 最大文件名长度
        
    Returns:
        str: 清理后的文件名
    """
    if not filename:
        return "unnamed_file"
    
    # 保存原始扩展名（处理 .ext 这种情况）
    original_ext = Path(filename).suffix
    # 对于 .pdf 这种情况，Path.suffix 返回 ''，我们需要手动提取
    if not original_ext and filename.startswith('.'):
        # 尝试从 .pdf 中提取 pdf 作为扩展名
        potential_ext = filename[1:]
        if potential_ext and not any(c in potential_ext for c in '/\\:*?"<>|'):
            original_ext = filename  # 使用 .pdf 作为扩展名
    
    # 移除路径分隔符和危险字符
    # 包括: / \ : * ? " < > | 和控制字符
    sanitized = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', '_', filename)
    
    # 替换连续的 .. 为 _（防止路径遍历）
    sanitized = re.sub(r'\.\.+', '_', sanitized)
    
    # 移除以点开头的文件名（隐藏文件）
    sanitized = sanitized.lstrip('.')
    
    # 如果清理后只剩下扩展名（如 .pdf -> pdf），使用 unnamed_file 作为前缀
    if sanitized == original_ext.lstrip('.'):
        sanitized = "unnamed_file" + original_ext
    
    # 限制长度
    if len(sanitized) > max_length:
        # 保留扩展名
        path_obj = Path(sanitized)
        name = path_obj.stem
        ext = path_obj.suffix
        
        # 截断名称部分
        max_name_length = max_length - len(ext)
        if max_name_length < 1:
            # 扩展名太长，只保留扩展名
            sanitized = ext[:max_length]
        else:
            sanitized = name[:max_name_length] + ext
    
    # 确保文件名不为空
    ext = Path(sanitized).suffix if sanitized else ""
    if not sanitized or sanitized == ext:
        sanitized = "unnamed_file" + (ext if ext else "")
    
    return sanitized


def get_file_info(file_path: Path) -> dict:
    """
    获取文件详细信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        dict: 包含文件信息的字典
    """
    try:
        stat = file_path.stat()
        return {
            "path": str(file_path),
            "size": stat.st_size,
            "size_human": _format_file_size(stat.st_size),
            "created_at": stat.st_ctime,
            "modified_at": stat.st_mtime,
            "is_readable": os.access(file_path, os.R_OK),
            "is_writable": os.access(file_path, os.W_OK),
        }
    except Exception as e:
        logger.error(f"获取文件信息失败: {e}")
        return {
            "path": str(file_path),
            "error": str(e)
        }


def _format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为人类可读格式
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化后的文件大小
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"



