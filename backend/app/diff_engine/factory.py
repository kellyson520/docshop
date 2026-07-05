"""
Diff 引擎工厂

提供统一的 Diff 引擎创建和管理接口
"""

from typing import Dict, Type, Optional

from app.diff_engine.base import BaseDiffEngine
from app.diff_engine.docx_diff import DocxDiffEngine
from app.diff_engine.xlsx_diff import XlsxDiffEngine
from app.diff_engine.pdf_diff import PdfDiffEngine
from app.diff_engine.html_diff import HtmlDiffEngine
from app.utils.logger import logger


class ValidationError(Exception):
    """验证错误异常"""
    pass


# 引擎注册表
ENGINE_REGISTRY: Dict[str, Type[BaseDiffEngine]] = {
    'docx': DocxDiffEngine,
    'xlsx': XlsxDiffEngine,
    'pdf': PdfDiffEngine,
    'html': HtmlDiffEngine,
    'htm': HtmlDiffEngine,
}


def get_diff_engine(file_type: str) -> BaseDiffEngine:
    """
    获取对应文件类型的 Diff 引擎
    
    Args:
        file_type: 文件类型 ('docx', 'xlsx', 'pdf')
        
    Returns:
        BaseDiffEngine 实例
        
    Raises:
        ValidationError: 不支持的文件类型
    """
    # 标准化文件类型
    file_type = file_type.lower().lstrip('.')
    
    logger.debug(f"Getting diff engine for file type: {file_type}")
    
    if file_type not in ENGINE_REGISTRY:
        supported = ', '.join(ENGINE_REGISTRY.keys())
        error_msg = f"不支持的文件类型: {file_type}，仅支持 {supported}"
        logger.error(error_msg)
        raise ValidationError(error_msg)
    
    engine_class = ENGINE_REGISTRY[file_type]
    engine = engine_class()
    
    logger.info(f"Created diff engine: {engine_class.__name__}")
    return engine


def register_engine(file_type: str, engine_class: Type[BaseDiffEngine]) -> None:
    """
    注册新的 Diff 引擎（扩展用）
    
    Args:
        file_type: 文件类型标识
        engine_class: Diff 引擎类，必须继承 BaseDiffEngine
        
    Raises:
        ValidationError: 引擎类无效
    """
    file_type = file_type.lower().lstrip('.')
    
    if not issubclass(engine_class, BaseDiffEngine):
        error_msg = f"引擎类必须继承 BaseDiffEngine: {engine_class.__name__}"
        logger.error(error_msg)
        raise ValidationError(error_msg)
    
    ENGINE_REGISTRY[file_type] = engine_class
    logger.info(f"Registered diff engine: {file_type} -> {engine_class.__name__}")


def unregister_engine(file_type: str) -> Optional[Type[BaseDiffEngine]]:
    """
    注销 Diff 引擎
    
    Args:
        file_type: 文件类型标识
        
    Returns:
        被移除的引擎类，如不存在返回 None
    """
    file_type = file_type.lower().lstrip('.')
    
    if file_type in ENGINE_REGISTRY:
        engine_class = ENGINE_REGISTRY.pop(file_type)
        logger.info(f"Unregistered diff engine: {file_type}")
        return engine_class
    
    logger.warning(f"Attempted to unregister non-existent engine: {file_type}")
    return None


def get_supported_types() -> list:
    """
    获取支持的文件类型列表
    
    Returns:
        支持的文件类型列表
    """
    return list(ENGINE_REGISTRY.keys())


def is_supported(file_type: str) -> bool:
    """
    检查文件类型是否支持
    
    Args:
        file_type: 文件类型
        
    Returns:
        是否支持
    """
    file_type = file_type.lower().lstrip('.')
    return file_type in ENGINE_REGISTRY


def get_engine_info(file_type: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """
    获取引擎信息
    
    Args:
        file_type: 文件类型，为 None 则返回所有引擎信息
        
    Returns:
        引擎信息字典
    """
    def _get_info(ft: str, engine_class: Type[BaseDiffEngine]) -> Dict[str, str]:
        return {
            "file_type": ft,
            "engine_class": engine_class.__name__,
            "module": engine_class.__module__,
            "doc": engine_class.__doc__ or "No documentation"
        }
    
    if file_type:
        file_type = file_type.lower().lstrip('.')
        if file_type in ENGINE_REGISTRY:
            return {file_type: _get_info(file_type, ENGINE_REGISTRY[file_type])}
        return {}
    
    return {
        ft: _get_info(ft, engine_class)
        for ft, engine_class in ENGINE_REGISTRY.items()
    }
