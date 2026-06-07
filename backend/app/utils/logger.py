"""
日志系统模块

提供统一的日志记录功能，包括应用日志和访问日志。
支持文件输出和控制台输出，包含详细的上下文信息。
支持 RotatingFileHandler 日志轮转、JSON 格式日志和请求上下文注入。
"""

import json
import logging
import logging.handlers
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings


class RequestContextFilter(logging.Filter):
    """
    请求上下文过滤器

    自动从线程本地存储中注入 request_id 到每条日志记录中，
    便于在日志中追踪完整的请求链路。
    """

    # 线程本地存储，用于保存当前请求的上下文信息
    _context = threading.local()

    @classmethod
    def set_request_id(cls, request_id: str):
        """设置当前线程的请求ID"""
        cls._context.request_id = request_id

    @classmethod
    def get_request_id(cls) -> Optional[str]:
        """获取当前线程的请求ID"""
        return getattr(cls._context, "request_id", None)

    @classmethod
    def clear(cls):
        """清除当前线程的请求上下文"""
        cls._context.request_id = None

    def filter(self, record: logging.LogRecord) -> bool:
        """为日志记录注入 request_id"""
        record.request_id = self.get_request_id() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON 格式日志格式器

    将日志记录格式化为 JSON 字符串，便于日志采集系统（如 ELK）解析。
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        将日志记录格式化为 JSON

        Args:
            record: 日志记录

        Returns:
            str: JSON 格式的日志字符串
        """
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 注入请求上下文
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        # 添加异常信息
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def _create_log_directory() -> Path:
    """
    创建日志目录

    Returns:
        Path: 日志目录路径
    """
    log_dir = Path(settings.LOG_DIR)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    except Exception as e:
        # 如果无法创建指定目录，使用临时目录
        import tempfile
        fallback_dir = Path(tempfile.gettempdir()) / "docdist_logs"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        # 使用控制台输出警告
        print(f"Warning: Failed to create log directory {log_dir}: {e}", file=sys.stderr)
        print(f"Using fallback directory: {fallback_dir}", file=sys.stderr)
        return fallback_dir


def _get_formatter() -> logging.Formatter:
    """
    根据配置获取日志格式器

    当 settings.LOG_FORMAT == "json" 时使用 JSONFormatter，
    否则使用标准文本格式器。

    Returns:
        logging.Formatter: 配置好的格式器
    """
    if settings.LOG_FORMAT == "json":
        return JSONFormatter()

    return logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def _get_log_level() -> int:
    """
    根据配置获取日志级别

    将 settings.LOG_LEVEL 字符串映射为 logging 模块的日志级别常量。

    Returns:
        int: 日志级别常量
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(settings.LOG_LEVEL, logging.INFO)


def _create_rotating_file_handler(
    log_dir: Path,
    filename: str,
    level: Optional[int] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> Optional[logging.Handler]:
    """
    创建轮转文件日志处理器

    使用 RotatingFileHandler 替代 FileHandler，当日志文件达到指定大小时自动轮转。

    Args:
        log_dir: 日志目录路径
        filename: 日志文件名
        level: 日志级别（None 使用全局配置）
        max_bytes: 单个日志文件最大字节数（默认 10MB）
        backup_count: 保留的备份文件数量（默认 5 个）

    Returns:
        Optional[logging.Handler]: 文件处理器，失败返回None
    """
    if level is None:
        level = _get_log_level()

    try:
        handler = logging.handlers.RotatingFileHandler(
            log_dir / filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        handler.setFormatter(_get_formatter())
        handler.setLevel(level)
        return handler
    except Exception as e:
        print(f"Error creating rotating file handler for {filename}: {e}", file=sys.stderr)
        return None


def _create_console_handler(level: Optional[int] = None) -> logging.StreamHandler:
    """
    创建控制台日志处理器

    Args:
        level: 日志级别（None 使用 DEBUG）

    Returns:
        logging.StreamHandler: 控制台处理器
    """
    if level is None:
        level = logging.DEBUG

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_get_formatter())
    handler.setLevel(level)
    return handler


def _create_access_formatter() -> logging.Formatter:
    """
    创建访问日志格式器

    Returns:
        logging.Formatter: 访问日志格式器
    """
    if settings.LOG_FORMAT == "json":
        return JSONFormatter()

    return logging.Formatter(
        '%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


# ===== 请求上下文过滤器实例 =====
request_context_filter = RequestContextFilter()


# ===== 初始化日志目录 =====
_log_dir = _create_log_directory()

# ===== 全局日志级别 =====
_global_log_level = _get_log_level()

# ===== 创建应用日志器 =====
logger = logging.getLogger("docdist")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # 防止日志重复

# 添加请求上下文过滤器
logger.addFilter(request_context_filter)

# 添加轮转文件处理器
_file_handler = _create_rotating_file_handler(_log_dir, "app.log")
if _file_handler:
    logger.addHandler(_file_handler)

# 添加控制台处理器
_console_handler = _create_console_handler()
logger.addHandler(_console_handler)

# ===== 创建访问日志器 =====
access_logger = logging.getLogger("docdist.access")
access_logger.setLevel(logging.INFO)
access_logger.propagate = False
access_logger.addFilter(request_context_filter)

# 添加访问日志文件处理器（轮转）
_access_handler = _create_rotating_file_handler(_log_dir, "access.log", level=logging.INFO)
if _access_handler:
    _access_handler.setFormatter(_create_access_formatter())
    access_logger.addHandler(_access_handler)

# 添加访问日志控制台处理器（可选，生产环境可禁用）
if settings.ENVIRONMENT == "development":
    _access_console = _create_console_handler()
    _access_console.setFormatter(_create_access_formatter())
    access_logger.addHandler(_access_console)

# ===== 创建错误日志器（专门记录错误） =====
error_logger = logging.getLogger("docdist.error")
error_logger.setLevel(logging.ERROR)
error_logger.propagate = False
error_logger.addFilter(request_context_filter)

# 添加错误日志文件处理器（轮转）
_error_handler = _create_rotating_file_handler(_log_dir, "error.log", level=logging.ERROR)
if _error_handler:
    error_logger.addHandler(_error_handler)

# 添加错误日志控制台处理器
error_logger.addHandler(_create_console_handler(logging.ERROR))

# ===== 创建审计日志器（记录敏感操作） =====
audit_logger = logging.getLogger("docdist.audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False
audit_logger.addFilter(request_context_filter)

# 添加审计日志文件处理器（轮转）
_audit_handler = _create_rotating_file_handler(_log_dir, "audit.log", level=logging.INFO)
if _audit_handler:
    _audit_handler.setFormatter(_get_formatter())
    audit_logger.addHandler(_audit_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器

    Args:
        name: 日志器名称，建议使用模块路径如 "app.services.file_service"

    Returns:
        logging.Logger: 配置好的日志器
    """
    log = logging.getLogger(f"docdist.{name}")
    # 确保新创建的日志器也添加请求上下文过滤器
    if request_context_filter not in log.filters:
        log.addFilter(request_context_filter)
    return log


def log_function_call(logger_instance: logging.Logger, func_name: str, **kwargs):
    """
    记录函数调用信息

    Args:
        logger_instance: 日志器实例
        func_name: 函数名称
        **kwargs: 参数信息（敏感信息应脱敏）
    """
    try:
        # 脱敏处理：移除敏感字段
        safe_kwargs = {k: v for k, v in kwargs.items() if k not in ['password', 'token', 'secret', 'key']}
        logger_instance.debug(f"Function call: {func_name} - Params: {safe_kwargs}")
    except Exception as e:
        logger_instance.warning(f"Failed to log function call: {e}")


def log_operation(logger_instance: logging.Logger, operation: str, status: str, details: Optional[str] = None):
    """
    记录操作日志

    Args:
        logger_instance: 日志器实例
        operation: 操作名称
        status: 操作状态 (started/success/failed)
        details: 详细信息
    """
    try:
        message = f"Operation [{operation}] - Status: {status}"
        if details:
            message += f" - Details: {details}"

        if status == "started":
            logger_instance.info(message)
        elif status == "success":
            logger_instance.info(message)
        elif status == "failed":
            logger_instance.error(message)
        else:
            logger_instance.info(message)
    except Exception as e:
        # 日志记录失败不应影响主流程
        print(f"Failed to log operation: {e}", file=sys.stderr)


def log_audit(user_id: str, action: str, resource: str, result: str, details: Optional[str] = None):
    """
    记录审计日志

    Args:
        user_id: 用户ID
        action: 操作动作
        resource: 操作资源
        result: 操作结果
        details: 详细信息
    """
    try:
        message = f"User[{user_id}] - Action[{action}] - Resource[{resource}] - Result[{result}]"
        if details:
            message += f" - Details: {details}"
        audit_logger.info(message)
    except Exception as e:
        error_logger.error(f"Failed to log audit: {e}")
