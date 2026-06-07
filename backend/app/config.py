"""
配置模块

提供应用配置管理，支持多环境配置、配置验证和敏感信息保护。
使用 pydantic-settings 实现配置加载和验证。
"""

import os
import json
import secrets
from pathlib import Path
from typing import List, Optional, Set, Any
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, ValidationInfo


class Settings(BaseSettings):
    """
    应用配置类
    
    管理所有应用配置项，支持从环境变量和 .env 文件加载。
    提供配置验证和默认值处理。
    
    Attributes:
        ENVIRONMENT: 运行环境 (development/production/test)
        DEBUG: 调试模式开关
        SECRET_KEY: 应用密钥（用于 JWT 签名等）
        DATABASE_URL: 数据库连接 URL
        UPLOAD_DIR: 文件上传目录
        LOG_DIR: 日志文件目录
        TEMP_DIR: 临时文件目录
        MAX_FILE_SIZE: 最大上传文件大小（字节）
        ALLOWED_FILE_TYPES: 允许上传的文件类型集合
        ACCESS_TOKEN_EXPIRE_MINUTES: 访问令牌过期时间（分钟）
        CORS_ORIGINS: 允许的跨域来源列表
    """
    
    # 模型配置
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 忽略未定义的环境变量
    )
    
    # ===== 基础配置 =====
    ENVIRONMENT: str = Field(
        default="development",
        pattern="^(development|production|test)$",
        description="运行环境"
    )
    
    DEBUG: bool = Field(
        default=False,
        description="调试模式"
    )
    
    # 根据环境自动设置 DEBUG
    @field_validator('DEBUG', mode='before')
    @classmethod
    def set_debug_by_environment(cls, v: bool, info: ValidationInfo) -> bool:
        """根据环境自动设置 DEBUG 值"""
        if v is not None:
            return v
        env = info.data.get('ENVIRONMENT', 'production')
        return env == 'development'
    
    # ===== 安全配置 =====
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        min_length=16,
        description="应用密钥（用于 JWT 签名等）"
    )

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """验证密钥强度"""
        env = info.data.get('ENVIRONMENT', 'production')
        if env == 'production' and len(v) < 32:
            raise ValueError("生产环境密钥长度必须至少 32 字符")
        return v
    
    # ===== 数据库配置 =====
    DATABASE_URL: str = Field(
        default="sqlite:///./data/docdist.db",
        description="数据库连接 URL"
    )
    
    DATABASE_POOL_SIZE: int = Field(
        default=5,
        ge=1,
        le=100,
        description="数据库连接池大小"
    )
    
    DATABASE_MAX_OVERFLOW: int = Field(
        default=10,
        ge=0,
        le=100,
        description="数据库连接池溢出大小"
    )
    
    DATABASE_POOL_RECYCLE: int = Field(
        default=3600,
        ge=300,
        description="数据库连接回收时间（秒）"
    )
    
    # ===== 存储配置 =====
    UPLOAD_DIR: str = Field(
        default="./data/uploads",
        description="文件上传目录"
    )
    
    LOG_DIR: str = Field(
        default="./data/logs",
        description="日志文件目录"
    )
    
    TEMP_DIR: str = Field(
        default="./data/temp",
        description="临时文件目录"
    )
    
    @field_validator('UPLOAD_DIR', 'LOG_DIR', 'TEMP_DIR')
    @classmethod
    def validate_directory_paths(cls, v: str) -> str:
        """验证并规范化目录路径"""
        # 转换为绝对路径
        path = Path(v).resolve()
        return str(path)
    
    # ===== 文件上传配置 =====
    MAX_FILE_SIZE: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        ge=1024,  # 最小 1KB
        le=500 * 1024 * 1024,  # 最大 500MB
        description="最大上传文件大小（字节）"
    )
    
    ALLOWED_FILE_TYPES: Set[str] = Field(
        default={".pdf", ".docx", ".xlsx", ".doc", ".xls"},
        description="允许上传的文件类型"
    )
    
    @field_validator('ALLOWED_FILE_TYPES', mode='before')
    @classmethod
    def validate_allowed_file_types(cls, v) -> Set[str]:
        """验证并规范化文件类型"""
        if isinstance(v, str):
            # 支持逗号分隔的字符串
            v = set(ext.strip().lower() for ext in v.split(',') if ext.strip())
        elif isinstance(v, (list, tuple)):
            v = set(ext.lower() for ext in v)
        
        # 确保扩展名以点开头
        return {ext if ext.startswith('.') else f'.{ext}' for ext in v}
    
    # ===== 认证配置 =====
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,  # 24小时
        ge=5,
        le=10080,  # 7天
        description="访问令牌过期时间（分钟）"
    )
    
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        le=30,
        description="刷新令牌过期时间（天）"
    )
    
    # ===== CORS 配置 =====
    CORS_ORIGINS: Any = Field(
        default="*",
        description="允许的跨域来源列表（逗号分隔或 JSON 数组）"
    )
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def validate_cors_origins(cls, v) -> List[str]:
        """验证 CORS 来源，支持 JSON 数组或逗号分隔字符串"""
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return ["*"]
        if isinstance(v, list):
            return [str(x) for x in v if x]
        if isinstance(v, str):
            v = v.strip()
            # JSON 数组格式: ["http://a","http://b"]
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(x) for x in parsed if x]
                except (json.JSONDecodeError, TypeError):
                    pass
            # 逗号分隔格式: http://a,http://b
            origins = [o.strip().strip('"').strip("'") for o in v.split(',') if o.strip()]
            return origins if origins else ["*"]
        return ["*"]
    
    # ===== 限流配置 =====
    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="是否启用请求限流"
    )
    
    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        ge=1,
        description="限流窗口内的最大请求数"
    )
    
    RATE_LIMIT_WINDOW: int = Field(
        default=60,
        ge=1,
        description="限流窗口时间（秒）"
    )
    
    # ===== 日志配置 =====
    LOG_LEVEL: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="日志级别"
    )
    
    LOG_FORMAT: str = Field(
        default="json",
        pattern="^(json|text)$",
        description="日志格式"
    )
    
    # ===== 缓存配置 =====
    CACHE_ENABLED: bool = Field(
        default=False,
        description="是否启用缓存"
    )
    
    CACHE_TTL: int = Field(
        default=300,
        ge=60,
        description="缓存过期时间（秒）"
    )
    
    CACHE_MAX_SIZE: int = Field(
        default=1000,
        ge=1,
        description="缓存最大条目数"
    )
    
    # ===== 特性开关 =====
    FEATURE_FILE_PREVIEW: bool = Field(
        default=True,
        description="启用文件预览功能"
    )
    
    FEATURE_DIFF_EXPORT: bool = Field(
        default=True,
        description="启用差异导出功能"
    )
    
    FEATURE_SHARE_LINK: bool = Field(
        default=True,
        description="启用分享链接功能"
    )
    
    # ===== 方法 =====
    
    def is_development(self) -> bool:
        """检查是否为开发环境"""
        return self.ENVIRONMENT == "development"
    
    def is_production(self) -> bool:
        """检查是否为生产环境"""
        return self.ENVIRONMENT == "production"
    
    def is_test(self) -> bool:
        """检查是否为测试环境"""
        return self.ENVIRONMENT == "test"
    
    def get_upload_path(self, *paths: str) -> Path:
        """
        获取上传目录下的文件路径
        
        Args:
            *paths: 子路径组件
            
        Returns:
            Path: 完整路径
        """
        return Path(self.UPLOAD_DIR).joinpath(*paths)
    
    def get_log_path(self, filename: str) -> Path:
        """
        获取日志文件路径
        
        Args:
            filename: 日志文件名
            
        Returns:
            Path: 完整路径
        """
        return Path(self.LOG_DIR) / filename
    
    def get_temp_path(self, filename: Optional[str] = None) -> Path:
        """
        获取临时文件路径
        
        Args:
            filename: 临时文件名（可选）
            
        Returns:
            Path: 完整路径
        """
        path = Path(self.TEMP_DIR)
        if filename:
            return path / filename
        return path
    
    def ensure_directories(self) -> None:
        """
        确保所有必要的目录存在
        
        创建上传目录、日志目录、临时目录等。
        """
        directories = [
            self.UPLOAD_DIR,
            self.LOG_DIR,
            self.TEMP_DIR,
        ]
        
        for directory in directories:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                import warnings
                warnings.warn(f"无法创建目录 {directory}: {e}")


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置实例（单例模式）
    
    使用 LRU 缓存确保配置只加载一次，提高性能。
    
    Returns:
        Settings: 配置实例
    """
    return Settings()


# 全局配置实例
settings = get_settings()


# 开发环境配置
class DevelopmentSettings(Settings):
    """开发环境专用配置"""
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时，方便开发


# 测试环境配置
class TestSettings(Settings):
    """测试环境专用配置"""
    ENVIRONMENT: str = "test"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "sqlite:///./data/test.db"
    UPLOAD_DIR: str = "./data/test_uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB


# 生产环境配置
class ProductionSettings(Settings):
    """生产环境专用配置"""
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1小时
    RATE_LIMIT_ENABLED: bool = True
    CACHE_ENABLED: bool = True


def get_settings_by_environment(environment: Optional[str] = None) -> Settings:
    """
    根据环境获取对应的配置类
    
    Args:
        environment: 环境名称，默认从环境变量获取
        
    Returns:
        Settings: 对应环境的配置实例
    """
    env = environment or os.getenv("ENVIRONMENT", "development")
    
    settings_map = {
        "development": DevelopmentSettings,
        "production": ProductionSettings,
        "test": TestSettings,
    }
    
    settings_class = settings_map.get(env, Settings)
    return settings_class()


# 配置验证函数
def validate_settings() -> List[str]:
    """
    验证当前配置
    
    检查配置是否合理，返回警告信息列表。
    
    Returns:
        List[str]: 警告信息列表
    """
    warnings = []
    
    # 检查生产环境配置
    if settings.is_production():
        if settings.DEBUG:
            warnings.append("生产环境不应启用 DEBUG 模式")
        
        if settings.SECRET_KEY == "docdist-secret-key-change-me":
            warnings.append("生产环境必须使用自定义 SECRET_KEY")
        
        if "*" in settings.CORS_ORIGINS:
            warnings.append("生产环境不应允许所有 CORS 来源")
        
        if settings.CORS_ORIGINS != ["*"] and "*" not in settings.CORS_ORIGINS:
            warnings.append("生产环境 CORS 应配置为精确域名列表，并确保 allow_credentials 行为正确")
        
        if "sqlite" in settings.DATABASE_URL.lower():
            warnings.append("生产环境建议使用 PostgreSQL 或 MySQL")
    
    # 检查目录权限
    for directory in [settings.UPLOAD_DIR, settings.LOG_DIR, settings.TEMP_DIR]:
        path = Path(directory)
        if path.exists() and not os.access(path, os.W_OK):
            warnings.append(f"目录不可写: {directory}")
    
    return warnings


# 启动时验证配置
if __name__ != "__main__":
    # 确保目录存在
    settings.ensure_directories()
    
    # 验证配置并输出警告
    config_warnings = validate_settings()
    if config_warnings:
        import warnings
        for warning in config_warnings:
            warnings.warn(f"[Config Warning] {warning}")
