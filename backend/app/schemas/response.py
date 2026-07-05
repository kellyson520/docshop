from typing import TypeVar, Generic, Optional, List, Any
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    items: List[T]


def success_response(data: Any = None, message: str = "success") -> ApiResponse:
    """
    创建成功响应

    Args:
        data: 响应数据
        message: 响应消息

    Returns:
        ApiResponse: 标准API响应
    """
    return ApiResponse(code=0, message=message, data=data)
