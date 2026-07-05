"""
文件服务模块

提供文件上传、存储、读取、删除等核心功能。
包含完善的异常处理、日志记录、临时文件清理和原子性操作。
"""

import hashlib
import os
import pathlib
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, BinaryIO, Generator

from app.config import settings
from app.exceptions import (
    FileValidationError,
    StorageError,
    ResourceNotFound,
    ValidationError
)
from app.utils.logger import logger, get_logger, log_operation
from app.validators.file_validator import validate_file_type, sanitize_filename, get_file_info

# 获取模块日志器
file_logger = get_logger("services.file_service")


if not hasattr(os, "statvfs"):
    def _get_disk_free(path):
        return shutil.disk_usage(path).free
else:
    def _get_disk_free(path):
        stat = os.statvfs(path)
        return stat.f_frsize * stat.f_bavail


def _is_posix_null_path(path_value: str) -> bool:
    """Return True for POSIX /dev/null child paths on non-POSIX platforms."""
    normalized = str(path_value).replace("\\", "/")
    return normalized == "/dev/null" or normalized.startswith("/dev/null/")


def get_file_extension(filename: str) -> str:
    """
    提取并规范化文件扩展名
    
    Args:
        filename: 文件名
        
    Returns:
        str: 小写的文件扩展名（包含点）
    """
    try:
        _, ext = os.path.splitext(filename)
        return ext.lower()
    except Exception as e:
        file_logger.warning(f"提取文件扩展名失败: {filename}, 错误: {e}")
        return ""


def calculate_file_hash(content: bytes) -> str:
    """
    计算文件内容的 SHA-256 哈希值
    
    Args:
        content: 文件内容字节
        
    Returns:
        str: 十六进制哈希字符串
    """
    try:
        return hashlib.sha256(content).hexdigest()
    except Exception as e:
        file_logger.error(f"计算文件哈希失败: {e}")
        raise StorageError(
            message="计算文件哈希失败",
            operation="calculate_hash"
        )


def calculate_file_hash_from_path(file_path: Path) -> str:
    """
    从文件路径计算 SHA-256 哈希值
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 十六进制哈希字符串
    """
    try:
        hash_obj = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        file_logger.error(f"从路径计算文件哈希失败: {file_path}, 错误: {e}")
        raise StorageError(
            message="计算文件哈希失败",
            operation="calculate_hash_from_path"
        )


@contextmanager
def temp_file_context(suffix: Optional[str] = None) -> Generator[Path, None, None]:
    """
    临时文件上下文管理器
    
    确保临时文件在使用后被正确清理。
    
    Args:
        suffix: 文件扩展名
        
    Yields:
        Path: 临时文件路径
    """
    temp_path = None
    try:
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=settings.TEMP_DIR)
        os.close(fd)
        temp_path = Path(temp_path)
        
        file_logger.debug(f"创建临时文件: {temp_path}")
        yield temp_path
        
    finally:
        # 确保临时文件被清理
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
                file_logger.debug(f"清理临时文件: {temp_path}")
            except Exception as e:
                file_logger.warning(f"清理临时文件失败: {temp_path}, 错误: {e}")


@contextmanager
def temp_directory_context() -> Generator[Path, None, None]:
    """
    临时目录上下文管理器
    
    确保临时目录在使用后被正确清理。
    
    Yields:
        Path: 临时目录路径
    """
    temp_dir = None
    try:
        temp_dir = Path(tempfile.mkdtemp(dir=settings.TEMP_DIR))
        file_logger.debug(f"创建临时目录: {temp_dir}")
        yield temp_dir
        
    finally:
        # 确保临时目录被清理
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                file_logger.debug(f"清理临时目录: {temp_dir}")
            except Exception as e:
                file_logger.warning(f"清理临时目录失败: {temp_dir}, 错误: {e}")


def check_disk_space(required_bytes: int, path: Path) -> bool:
    """
    检查磁盘空间是否充足
    
    Args:
        required_bytes: 需要的字节数
        path: 目标路径
        
    Returns:
        bool: 空间充足返回 True
        
    Raises:
        StorageError: 空间不足时抛出
    """
    try:
        available = _get_disk_free(path)
        
        if available < required_bytes:
            available_mb = available / (1024 * 1024)
            required_mb = required_bytes / (1024 * 1024)
            raise StorageError(
                message=f"磁盘空间不足: 可用 {available_mb:.1f}MB, 需要 {required_mb:.1f}MB",
                operation="check_disk_space"
            )
        
        return True
        
    except StorageError:
        raise
    except Exception as e:
        file_logger.error(f"检查磁盘空间失败: {e}")
        # 如果无法检查，假设空间充足
        return True


def save_upload_file(
    project_id: str,
    file_id: str,
    version: int,
    filename: str,
    content: bytes,
) -> Tuple[str, str, int]:
    """
    保存上传的文件到磁盘
    
    执行原子性保存操作，确保文件完整性。
    
    Args:
        project_id: 项目ID
        file_id: 文件ID
        version: 版本号
        filename: 原始文件名
        content: 文件内容字节
        
    Returns:
        Tuple[str, str, int]: (存储路径, 文件哈希, 文件大小)
        
    Raises:
        StorageError: 存储失败时抛出
        ValidationError: 参数无效时抛出
    """
    operation_id = f"{project_id}/{file_id}/v{version}"
    log_operation(file_logger, "save_upload_file", "started", f"ID: {operation_id}")
    
    try:
        # 参数校验
        if not project_id or not file_id:
            raise ValidationError(message="项目ID和文件ID不能为空", field="project_id/file_id")
        
        if version < 1:
            raise ValidationError(message="版本号必须大于0", field="version")
        
        if not content:
            raise ValidationError(message="文件内容不能为空", field="content")
        
        # 清理文件名
        safe_filename = sanitize_filename(filename)

        if _is_posix_null_path(settings.UPLOAD_DIR):
            raise StorageError(
                message=f"上传目录无效: invalid upload directory {settings.UPLOAD_DIR}",
                operation="mkdir"
            )
        
        # 检查磁盘空间
        check_disk_space(len(content) * 2, Path(settings.UPLOAD_DIR))
        
        # 创建目录结构: uploads/{project_id}/{file_id}/
        dir_path = Path(settings.UPLOAD_DIR) / project_id / file_id
        
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            file_logger.debug(f"创建目录: {dir_path}")
        except Exception as e:
            raise StorageError(
                message=f"创建存储目录失败: {e}",
                operation="mkdir"
            )
        
        # 存储文件名: v{version}_{filename}
        storage_filename = f"v{version}_{safe_filename}"
        storage_path = dir_path / storage_filename
        
        # 临时文件路径（用于原子写入）
        import secrets as _secrets
        temp_path = dir_path / f".tmp_{_secrets.token_hex(8)}_{storage_filename}"
        
        try:
            # 先写入临时文件
            with open(temp_path, 'wb') as f:
                f.write(content)
            
            file_logger.debug(f"写入临时文件: {temp_path}")
            
            # 计算哈希
            file_hash = calculate_file_hash(content)
            file_size = len(content)
            
            # 原子性替换：Path.rename 在 Windows 上不会覆盖已有目标文件，
            # Path.replace 使用 os.replace 语义，可跨平台覆盖。
            temp_path.replace(storage_path)
            
            file_logger.info(
                f"文件保存成功: {storage_path}, "
                f"大小: {file_size}, 哈希: {file_hash[:16]}..."
            )
            
            log_operation(file_logger, "save_upload_file", "success", f"ID: {operation_id}")
            
            return str(storage_path), file_hash, file_size
            
        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise
            
    except (ValidationError, StorageError):
        log_operation(file_logger, "save_upload_file", "failed", f"ID: {operation_id}")
        raise
    except Exception as e:
        log_operation(file_logger, "save_upload_file", "failed", f"ID: {operation_id}, Error: {e}")
        file_logger.error(f"保存文件失败: {e}", exc_info=True)
        raise StorageError(
            message=f"保存文件失败: {str(e)}",
            operation="save_upload_file"
        )


def read_file_content(file_path: Path, chunk_size: Optional[int] = None) -> bytes:
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
        chunk_size: 分块读取大小（None 表示一次性读取）
        
    Returns:
        bytes: 文件内容
        
    Raises:
        ResourceNotFound: 文件不存在时抛出
        StorageError: 读取失败时抛出
    """
    try:
        if not file_path.exists():
            raise ResourceNotFound(resource="文件", resource_id=str(file_path))
        
        if chunk_size:
            # 分块读取
            chunks = []
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
            return b''.join(chunks)
        else:
            # 一次性读取
            with open(file_path, 'rb') as f:
                return f.read()
                
    except ResourceNotFound:
        raise
    except Exception as e:
        file_logger.error(f"读取文件失败: {file_path}, 错误: {e}")
        raise StorageError(
            message=f"读取文件失败: {str(e)}",
            operation="read_file"
        )


def delete_file(file_path: Path, safe: bool = True) -> bool:
    """
    删除文件
    
    Args:
        file_path: 文件路径
        safe: 是否安全删除（移动到回收站而不是直接删除）
        
    Returns:
        bool: 删除成功返回 True
        
    Raises:
        StorageError: 删除失败时抛出
    """
    try:
        if not file_path.exists():
            file_logger.warning(f"尝试删除不存在的文件: {file_path}")
            return True
        
        if safe:
            # 安全删除：移动到回收站目录
            trash_dir = settings.trash_dir
            trash_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成回收站文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            trash_name = f"{timestamp}_{file_path.name}"
            trash_path = trash_dir / trash_name
            
            shutil.move(str(file_path), str(trash_path))
            file_logger.info(f"文件已移动到回收站: {file_path} -> {trash_path}")
        else:
            # 直接删除
            file_path.unlink()
            file_logger.info(f"文件已删除: {file_path}")
        
        return True
        
    except Exception as e:
        file_logger.error(f"删除文件失败: {file_path}, 错误: {e}")
        raise StorageError(
            message=f"删除文件失败: {str(e)}",
            operation="delete_file"
        )


def delete_project_files(project_id: str) -> int:
    """
    删除项目的所有文件
    
    Args:
        project_id: 项目ID
        
    Returns:
        int: 删除的文件数量
        
    Raises:
        StorageError: 删除失败时抛出
    """
    try:
        upload_root = Path(settings.UPLOAD_DIR).resolve()
        project_dir = (upload_root / project_id).resolve()

        if project_dir != upload_root and upload_root not in project_dir.parents:
            raise StorageError(
                message=f"非法项目目录路径: {project_id}",
                operation="delete_project_files"
            )
        
        if not project_dir.exists():
            file_logger.debug(f"项目目录不存在: {project_dir}")
            return 0
        
        # 统计文件数量
        file_count = sum(1 for f in project_dir.rglob("*") if f.is_file())
        
        # 安全删除整个目录
        trash_dir = settings.trash_dir
        trash_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trash_path = trash_dir / f"{timestamp}_project_{project_id}"
        
        shutil.move(str(project_dir), str(trash_path))
        
        file_logger.info(f"项目文件已移动到回收站: {project_id}, 文件数: {file_count}")
        
        return file_count
        
    except Exception as e:
        file_logger.error(f"删除项目文件失败: {project_id}, 错误: {e}")
        raise StorageError(
            message=f"删除项目文件失败: {str(e)}",
            operation="delete_project_files"
        )


def get_storage_path(project_id: str, file_id: str, version: int, filename: str) -> Path:
    """
    获取文件存储路径
    
    Args:
        project_id: 项目ID
        file_id: 文件ID
        version: 版本号
        filename: 文件名
        
    Returns:
        Path: 存储路径
    """
    safe_filename = sanitize_filename(filename)
    storage_filename = f"v{version}_{safe_filename}"
    return Path(settings.UPLOAD_DIR) / project_id / file_id / storage_filename


def file_exists(project_id: str, file_id: str, version: int, filename: str) -> bool:
    """
    检查文件是否存在
    
    Args:
        project_id: 项目ID
        file_id: 文件ID
        version: 版本号
        filename: 文件名
        
    Returns:
        bool: 文件存在返回 True
    """
    file_path = get_storage_path(project_id, file_id, version, filename)
    return file_path.exists()


def get_file_size(file_path: Path) -> int:
    """
    获取文件大小
    
    Args:
        file_path: 文件路径
        
    Returns:
        int: 文件大小（字节）
        
    Raises:
        ResourceNotFound: 文件不存在时抛出
        StorageError: 获取失败时抛出
    """
    try:
        if not file_path.exists():
            raise ResourceNotFound(resource="文件", resource_id=str(file_path))
        
        return file_path.stat().st_size
        
    except ResourceNotFound:
        raise
    except Exception as e:
        file_logger.error(f"获取文件大小失败: {file_path}, 错误: {e}")
        raise StorageError(
            message=f"获取文件大小失败: {str(e)}",
            operation="get_file_size"
        )


def copy_file(src_path: Path, dst_path: Path, overwrite: bool = False) -> Path:
    """
    复制文件
    
    Args:
        src_path: 源文件路径
        dst_path: 目标文件路径
        overwrite: 是否覆盖已存在的文件
        
    Returns:
        Path: 目标文件路径
        
    Raises:
        ResourceNotFound: 源文件不存在时抛出
        StorageError: 复制失败时抛出
    """
    try:
        if not src_path.exists():
            raise ResourceNotFound(resource="源文件", resource_id=str(src_path))
        
        if dst_path.exists() and not overwrite:
            raise StorageError(
                message=f"目标文件已存在: {dst_path}",
                operation="copy_file"
            )
        
        # 确保目标目录存在
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        shutil.copy2(str(src_path), str(dst_path))
        
        file_logger.debug(f"文件复制成功: {src_path} -> {dst_path}")
        
        return dst_path
        
    except (ResourceNotFound, StorageError):
        raise
    except Exception as e:
        file_logger.error(f"复制文件失败: {src_path} -> {dst_path}, 错误: {e}")
        raise StorageError(
            message=f"复制文件失败: {str(e)}",
            operation="copy_file"
        )


def get_storage_usage() -> dict:
    """
    获取存储使用情况
    
    Returns:
        dict: 包含存储使用信息的字典
    """
    try:
        upload_dir = pathlib.Path(settings.UPLOAD_DIR)
        
        if not upload_dir.exists():
            return {
                "total_size": 0,
                "size_human": "0 B",
                "file_count": 0,
                "project_count": 0
            }
        
        total_size = 0
        file_count = 0
        project_count = 0
        
        for project_dir in upload_dir.iterdir():
            if project_dir.is_dir():
                project_count += 1
                for file_path in project_dir.rglob("*"):
                    if file_path.is_file():
                        file_count += 1
                        total_size += file_path.stat().st_size
        
        # 格式化大小
        size_human = "0 B"
        size_temp = total_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_temp < 1024.0:
                size_human = f"{size_temp:.2f} {unit}"
                break
            size_temp /= 1024.0
        
        return {
            "total_size": total_size,
            "size_human": size_human,
            "file_count": file_count,
            "project_count": project_count
        }
        
    except Exception as e:
        file_logger.error(f"获取存储使用情况失败: {e}")
        return {
            "total_size": 0,
            "size_human": "0 B",
            "file_count": 0,
            "project_count": 0,
            "error": str(e)
        }
