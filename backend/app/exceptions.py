"""
异常处理模块

定义系统中使用的所有自定义异常类，提供统一的错误处理机制。
每个异常类包含错误码和错误消息，便于前端识别和处理。
"""

from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class DocShopException(Exception):
    """
    基础异常类
    
    所有自定义异常的基类，提供统一的错误码和消息格式。
    
    Attributes:
        message: 错误消息
        code: 错误码，用于前端识别错误类型
        details: 额外的错误详情
    """
    
    def __init__(
        self, 
        message: str, 
        code: int = 50000,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化异常
        
        Args:
            message: 错误消息
            code: 错误码
            details: 额外的错误详情
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将异常转换为字典格式
        
        Returns:
            Dict: 包含错误信息的字典
        """
        result = {
            "code": self.code,
            "message": self.message,
            "data": None
        }
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(DocShopException):
    """
    参数校验错误
    
    当请求参数不符合要求时抛出，如缺少必填字段、格式错误等。
    
    Error Code: 40001
    HTTP Status: 400 Bad Request
    """
    
    def __init__(
        self, 
        message: str = "参数校验失败",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化参数校验错误
        
        Args:
            message: 错误消息
            field: 出错的字段名
            details: 额外的错误详情
        """
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(message, code=40001, details=error_details)


class AuthenticationError(DocShopException):
    """
    认证错误
    
    当用户认证失败时抛出，如token无效、过期、用户名密码错误等。
    
    Error Code: 20001
    HTTP Status: 401 Unauthorized
    """
    
    def __init__(
        self, 
        message: str = "认证失败",
        auth_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化认证错误
        
        Args:
            message: 错误消息
            auth_type: 认证类型（如 token, password 等）
            details: 额外的错误详情
        """
        error_details = details or {}
        if auth_type:
            error_details["auth_type"] = auth_type
        super().__init__(message, code=20001, details=error_details)


class PermissionDenied(DocShopException):
    """
    权限不足
    
    当用户没有权限执行某项操作时抛出。
    
    Error Code: 20004
    HTTP Status: 403 Forbidden
    """
    
    def __init__(
        self, 
        message: str = "权限不足",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化权限错误
        
        Args:
            message: 错误消息
            required_permission: 需要的权限
            details: 额外的错误详情
        """
        error_details = details or {}
        if required_permission:
            error_details["required_permission"] = required_permission
        super().__init__(message, code=20004, details=error_details)


class ResourceNotFound(DocShopException):
    """
    资源不存在
    
    当请求的资源不存在时抛出，如项目、文件、用户等。
    
    Error Code: 30001
    HTTP Status: 404 Not Found
    """
    
    def __init__(
        self, 
        resource: str = "资源",
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化资源不存在错误
        
        Args:
            resource: 资源类型名称
            resource_id: 资源ID
            details: 额外的错误详情
        """
        message = f"{resource}不存在"
        if resource_id:
            message = f"{resource}不存在: {resource_id}"
        error_details = details or {}
        if resource_id:
            error_details["resource_id"] = resource_id
        super().__init__(message, code=30001, details=error_details)


class FileValidationError(DocShopException):
    """
    文件校验错误
    
    当上传的文件不符合要求时抛出，如格式不支持、大小超限等。
    
    Error Code: 40002
    HTTP Status: 400 Bad Request
    """
    
    def __init__(
        self, 
        message: str = "文件校验失败",
        filename: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化文件校验错误
        
        Args:
            message: 错误消息
            filename: 文件名
            reason: 具体原因
            details: 额外的错误详情
        """
        error_details = details or {}
        if filename:
            error_details["filename"] = filename
        if reason:
            error_details["reason"] = reason
        super().__init__(message, code=40002, details=error_details)


class DiffCalculationError(DocShopException):
    """
    Diff 计算错误
    
    当文档差异计算失败时抛出。
    
    Error Code: 50001
    HTTP Status: 500 Internal Server Error
    """
    
    def __init__(
        self, 
        message: str = "差异计算失败",
        file_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 Diff 计算错误
        
        Args:
            message: 错误消息
            file_type: 文件类型
            details: 额外的错误详情
        """
        error_details = details or {}
        if file_type:
            error_details["file_type"] = file_type
        super().__init__(message, code=50001, details=error_details)


class DatabaseError(DocShopException):
    """
    数据库错误
    
    当数据库操作失败时抛出。
    
    Error Code: 50002
    HTTP Status: 500 Internal Server Error
    """
    
    def __init__(
        self, 
        message: str = "数据库操作失败",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化数据库错误
        
        Args:
            message: 错误消息
            operation: 数据库操作类型
            details: 额外的错误详情
        """
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        super().__init__(message, code=50002, details=error_details)


class StorageError(DocShopException):
    """
    存储错误
    
    当文件存储操作失败时抛出，如磁盘满、权限不足等。
    
    Error Code: 50003
    HTTP Status: 500 Internal Server Error
    """
    
    def __init__(
        self, 
        message: str = "文件存储失败",
        storage_type: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化存储错误
        
        Args:
            message: 错误消息
            storage_type: 存储类型（如 local, s3 等）
            operation: 操作名称（如 save_upload_file, read_file 等）
            details: 额外的错误详情
        """
        error_details = details or {}
        if storage_type:
            error_details["storage_type"] = storage_type
        if operation:
            error_details["operation"] = operation
        super().__init__(message, code=50003, details=error_details)


class RateLimitExceeded(DocShopException):
    """
    请求频率超限
    
    当用户请求频率超过限制时抛出。
    
    Error Code: 40003
    HTTP Status: 429 Too Many Requests
    """
    
    def __init__(
        self, 
        message: str = "请求过于频繁",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化频率限制错误
        
        Args:
            message: 错误消息
            retry_after: 建议重试等待时间（秒）
            details: 额外的错误详情
        """
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        super().__init__(message, code=40003, details=error_details)


class ConflictError(DocShopException):
    """
    资源冲突
    
    当操作会导致资源冲突时抛出，如重复创建、版本冲突等。
    
    Error Code: 40004
    HTTP Status: 409 Conflict
    """
    
    def __init__(
        self, 
        message: str = "资源冲突",
        conflict_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化资源冲突错误
        
        Args:
            message: 错误消息
            conflict_type: 冲突类型
            details: 额外的错误详情
        """
        error_details = details or {}
        if conflict_type:
            error_details["conflict_type"] = conflict_type
        super().__init__(message, code=40004, details=error_details)


class ExternalServiceError(DocShopException):
    """
    外部服务错误
    
    当调用外部服务失败时抛出。
    
    Error Code: 50004
    HTTP Status: 502 Bad Gateway
    """
    
    def __init__(
        self, 
        message: str = "外部服务调用失败",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化外部服务错误
        
        Args:
            message: 错误消息
            service_name: 服务名称
            details: 额外的错误详情
        """
        error_details = details or {}
        if service_name:
            error_details["service_name"] = service_name
        super().__init__(message, code=50004, details=error_details)


def get_http_status(code: int) -> int:
    """
    根据错误码获取 HTTP 状态码
    
    Args:
        code: 错误码
        
    Returns:
        int: HTTP 状态码
    """
    # 错误码映射到 HTTP 状态码
    status_map = {
        20001: status.HTTP_401_UNAUTHORIZED,  # 认证错误
        20004: status.HTTP_403_FORBIDDEN,      # 权限不足
        30001: status.HTTP_404_NOT_FOUND,      # 资源不存在
        40001: status.HTTP_400_BAD_REQUEST,    # 参数校验错误
        40002: status.HTTP_400_BAD_REQUEST,    # 文件校验错误
        40003: status.HTTP_429_TOO_MANY_REQUESTS,  # 频率限制
        40004: status.HTTP_409_CONFLICT,       # 资源冲突
        50001: status.HTTP_500_INTERNAL_SERVER_ERROR,  # Diff计算错误
        50002: status.HTTP_500_INTERNAL_SERVER_ERROR,  # 数据库错误
        50003: status.HTTP_500_INTERNAL_SERVER_ERROR,  # 存储错误
        50004: status.HTTP_502_BAD_GATEWAY,    # 外部服务错误
    }
    
    # 根据错误码前缀判断
    prefix = code // 10000
    if prefix == 2:
        return status_map.get(code, status.HTTP_401_UNAUTHORIZED)
    elif prefix == 3:
        return status_map.get(code, status.HTTP_404_NOT_FOUND)
    elif prefix == 4:
        return status_map.get(code, status.HTTP_400_BAD_REQUEST)
    elif prefix == 5:
        return status_map.get(code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return status.HTTP_500_INTERNAL_SERVER_ERROR


class ConversionError(DocShopException):
    """文档转换失败，携带具体原因供前端展示。"""
    def __init__(self, message: str, reason: str = "unknown"):
        self.reason = reason
        super().__init__(message, code=60001, details={"reason": reason})
