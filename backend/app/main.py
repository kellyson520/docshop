"""
DocDist API 主应用模块

文档版本管理和分发系统的后端 API 服务。
提供项目、文件、版本、差异比较等核心功能。
"""

import os
import platform
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, check_database_connection, close_all_connections
from app.middlewares import (
    ErrorHandlerMiddleware,
    LoggingMiddleware,
    TrackingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.routers import auth, projects, files, diffs, share, cards, tracking_admin, exams, notices, announcements, access_tokens, users, categories
from app.routers import settings as settings_router
from app.schemas.response import ApiResponse
from app.utils.logger import logger, get_logger
from app.deps.auth import get_current_admin
from app.models.user import User

# 获取主日志器
main_logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    处理应用启动和关闭时的初始化/清理工作。
    
    Args:
        app: FastAPI 应用实例
        
    Yields:
        None
    """
    # ===== 启动阶段 =====
    main_logger.info("=" * 50)
    main_logger.info("DocDist API 正在启动...")
    main_logger.info(f"环境: {settings.ENVIRONMENT}")
    main_logger.info(f"调试模式: {settings.DEBUG}")
    
    try:
        # 创建必要的目录
        _create_required_directories()
        
        # 检查数据库连接
        if not await _check_database():
            main_logger.error("数据库连接检查失败，应用可能无法正常工作")
        
        # 初始化数据库表
        init_db()
        main_logger.info("数据库初始化完成")
        
        # 记录系统信息
        _log_system_info()
        
        main_logger.info("DocDist API 启动成功")
        main_logger.info("=" * 50)
        
    except Exception as e:
        main_logger.error(f"启动过程中发生错误: {e}", exc_info=True)
        raise
    
    yield
    
    # ===== 关闭阶段 =====
    main_logger.info("=" * 50)
    main_logger.info("DocDist API 正在关闭...")
    
    try:
        # 执行清理工作
        await _cleanup()
        main_logger.info("清理工作完成")
        
    except Exception as e:
        main_logger.error(f"关闭过程中发生错误: {e}", exc_info=True)
    
    main_logger.info("DocDist API 已关闭")
    main_logger.info("=" * 50)


def _create_required_directories():
    """
    创建应用所需的目录结构
    
    创建上传目录、日志目录等必要的文件夹。
    """
    directories = [
        settings.UPLOAD_DIR,
        settings.LOG_DIR,
        Path(settings.UPLOAD_DIR).parent / "temp",
        Path(settings.UPLOAD_DIR).parent / "cache",
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            main_logger.debug(f"目录已创建/确认: {directory}")
        except Exception as e:
            main_logger.error(f"创建目录失败 {directory}: {e}")
            raise


async def _check_database() -> bool:
    """
    检查数据库连接状态
    
    Returns:
        bool: 连接成功返回 True，否则返回 False
    """
    try:
        is_connected = await check_database_connection()
        if is_connected:
            main_logger.info("数据库连接正常")
        else:
            main_logger.error("数据库连接失败")
        return is_connected
    except Exception as e:
        main_logger.error(f"数据库连接检查异常: {e}")
        return False


def _log_system_info():
    """
    记录系统信息
    
    记录 Python 版本、操作系统、CPU 信息等。
    """
    try:
        main_logger.info(f"Python 版本: {sys.version}")
        main_logger.info(f"操作系统: {platform.platform()}")
        main_logger.info(f"处理器: {platform.processor()}")
        main_logger.info(f"机器类型: {platform.machine()}")
        
        # 记录配置信息（脱敏）
        main_logger.info(f"上传目录: {settings.UPLOAD_DIR}")
        main_logger.info(f"日志目录: {settings.LOG_DIR}")
        main_logger.info(f"最大文件大小: {settings.MAX_FILE_SIZE / 1024 / 1024}MB")
        main_logger.info(f"允许的文件类型: {settings.ALLOWED_FILE_TYPES}")
        
    except Exception as e:
        main_logger.warning(f"记录系统信息时出错: {e}")


async def _cleanup():
    """
    应用关闭时的清理工作
    
    清理临时文件、关闭数据库连接等。
    """
    try:
        # 关闭所有数据库连接
        close_all_connections()
        main_logger.info("数据库连接已关闭")

        # 清理临时文件
        temp_dir = Path(settings.UPLOAD_DIR).parent / "temp"
        if temp_dir.exists():
            import shutil
            for item in temp_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    main_logger.warning(f"清理临时文件失败 {item}: {e}")
        
        main_logger.info("临时文件清理完成")
        
    except Exception as e:
        main_logger.error(f"清理工作出错: {e}")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="DocDist API",
    description="文档版本管理和分发系统 - 提供文档上传、版本控制、差异比较等功能",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ===== 中间件配置 =====
# 注意：中间件按添加顺序的逆序执行，最后添加的最先执行

# 1. GZip 压缩（最外层）
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # 只压缩大于 1KB 的响应
)

# 2. CORS 配置
_cors_origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"]
# CORS: 不允许 credentials + 通配符 origin 的组合（安全风险）
_cors_allow_credentials = "*" not in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
    max_age=600,  # 预检请求缓存 10 分钟
)

# 3. 错误处理中间件
app.add_middleware(
    ErrorHandlerMiddleware,
    include_traceback=settings.DEBUG
)

# 4. 日志记录中间件
app.add_middleware(
    LoggingMiddleware,
    log_request_body=False,  # 不记录请求体（可能包含敏感信息）
    log_headers=settings.DEBUG  # 调试模式记录请求头
)

# 5. 用户追踪中间件（最内层，最先执行请求，最后执行响应）
app.add_middleware(
    TrackingMiddleware,
    geoip_path=None  # 可选：配置GeoIP数据库路径
)

# 6. 限流中间件
app.add_middleware(
    RateLimitMiddleware,
)

# 7. 安全头中间件
app.add_middleware(
    SecurityHeadersMiddleware,
)

# ===== 路由注册 =====
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(files.router)
app.include_router(diffs.router)
app.include_router(share.router)
app.include_router(cards.router)
app.include_router(tracking_admin.router, prefix="/api/v1")
app.include_router(exams.router)
app.include_router(settings_router.router)
app.include_router(notices.router)
app.include_router(announcements.router)
app.include_router(access_tokens.router)
app.include_router(users.router)
app.include_router(categories.categories_router)
app.include_router(categories.tags_router)

# 封面图片静态文件服务
covers_dir = Path(settings.UPLOAD_DIR).parent / "covers"
covers_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/v1/covers", StaticFiles(directory=str(covers_dir)), name="covers")

avatars_dir = Path(settings.UPLOAD_DIR).parent / "avatars"
avatars_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/v1/avatars", StaticFiles(directory=str(avatars_dir)), name="avatars")

# ===== 健康检查和系统信息端点 =====

@app.get("/health", tags=["system"])
async def health_check() -> Dict[str, Any]:
    """
    健康检查端点
    
    用于负载均衡和健康监测，检查应用和依赖服务的状态。
    
    Returns:
        Dict: 包含健康状态的字典
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "checks": {}
    }
    
    # 检查数据库
    try:
        db_healthy = await check_database_connection()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "message": "数据库连接正常" if db_healthy else "数据库连接失败"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": str(e)
        }
    
    # 检查上传目录
    try:
        upload_path = Path(settings.UPLOAD_DIR)
        if upload_path.exists() and os.access(upload_path, os.W_OK):
            health_status["checks"]["storage"] = {
                "status": "healthy",
                "message": "存储目录可读写"
            }
        else:
            health_status["checks"]["storage"] = {
                "status": "unhealthy",
                "message": "存储目录不可写"
            }
    except Exception as e:
        health_status["checks"]["storage"] = {
            "status": "unhealthy",
            "message": str(e)
        }
    
    # 如果任何检查失败，整体状态为不健康
    if any(check["status"] == "unhealthy" for check in health_status["checks"].values()):
        health_status["status"] = "unhealthy"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ApiResponse(
                code=50000,
                message="服务不健康",
                data=health_status
            ).model_dump()
        )
    
    return ApiResponse(
        code=0,
        message="服务健康",
        data=health_status
    ).model_dump()


@app.get("/info", tags=["system"])
async def system_info(
    _admin: User = Depends(get_current_admin),
) -> Dict[str, Any]:
    """
    系统信息端点（仅管理员可访问）
    
    返回应用和系统的详细信息，用于调试和监控。
    需要管理员权限才能访问。
    
    Returns:
        Dict: 包含系统信息的字典
    """
    from app.models.user import User as UserModel
    info = {
        "application": {
            "name": "DocDist API",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
        },
        "system": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "machine": platform.machine(),
        },
        "configuration": {
            "max_file_size_mb": settings.MAX_FILE_SIZE / 1024 / 1024,
            "allowed_file_types": list(settings.ALLOWED_FILE_TYPES),
            "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    return ApiResponse(
        code=0,
        message="success",
        data=info
    ).model_dump()


@app.get("/api/v1/health", tags=["system"])
async def legacy_health_check():
    """
    兼容旧版本的健康检查端点
    
    保留旧版本 API 路径的兼容性。
    """
    return await health_check()


# 全局异常处理器（作为后备）
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器（后备）
    
    当 ErrorHandlerMiddleware 未能捕获异常时使用。
    
    Args:
        request: HTTP 请求对象
        exc: 异常实例
        
    Returns:
        JSONResponse: 错误响应
    """
    logger.error(f"Unhandled exception in global handler: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse(
            code=99999,
            message="服务器内部错误",
            data=None
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    
    # 开发服务器配置
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        access_log=False  # 使用自定义日志中间件
    )
