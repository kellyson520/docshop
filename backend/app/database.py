"""
数据库模块

提供数据库连接管理、会话管理和连接池配置。
支持连接池优化、自动重连和会话生命周期管理。
"""

import asyncio
from contextlib import contextmanager
from typing import Generator, Optional, AsyncGenerator

from sqlalchemy import create_engine, event, text, exc as sqlalchemy_exc, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import QueuePool, NullPool

from app.config import settings
from app.utils.logger import get_logger

# 获取模块日志器
db_logger = get_logger("database")


class Base(DeclarativeBase):
    """
    SQLAlchemy 声明式基类
    
    所有模型类都应该继承此类。
    """
    pass


def _create_engine_with_pool() -> Engine:
    """
    创建带连接池的数据库引擎
    
    根据配置创建合适的连接池，支持 SQLite 和 PostgreSQL/MySQL。
    
    Returns:
        Engine: SQLAlchemy 引擎实例
    """
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    
    engine_kwargs = {
        "echo": settings.DEBUG and settings.LOG_LEVEL == "DEBUG",
        "future": True,
    }
    
    if is_sqlite:
        # SQLite 配置
        engine_kwargs["connect_args"] = {
            "check_same_thread": False,
        }
        # SQLite 使用 NullPool 避免连接池问题
        engine_kwargs["poolclass"] = NullPool
    else:
        # PostgreSQL/MySQL 配置
        engine_kwargs["poolclass"] = QueuePool
        engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
        engine_kwargs["pool_recycle"] = settings.DATABASE_POOL_RECYCLE
        engine_kwargs["pool_pre_ping"] = True  # 自动检测断开连接
    
    try:
        engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
        db_logger.info(
            f"数据库引擎创建成功 - URL: {settings.DATABASE_URL[:50]}..., "
            f"Pool: {engine_kwargs.get('poolclass', 'default').__name__}"
        )
        return engine
    except Exception as e:
        db_logger.error(f"创建数据库引擎失败: {e}")
        raise


# 创建全局引擎实例
engine = _create_engine_with_pool()

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # 提交后不过期对象
)


# ===== 事件监听器 =====

@event.listens_for(Engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """
    数据库连接建立时的回调
    
    用于设置连接参数。
    """
    db_logger.debug("新数据库连接已建立")


@event.listens_for(Engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """
    从连接池取出连接时的回调
    
    用于检测连接是否有效。
    """
    db_logger.debug("从连接池取出连接")


@event.listens_for(Engine, "checkin")
def on_checkin(dbapi_conn, connection_record):
    """
    连接归还到连接池时的回调
    """
    db_logger.debug("连接归还到连接池")


# ===== 会话管理 =====

def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（生成器）
    
    用于 FastAPI Depends，确保会话正确关闭。
    
    Yields:
        Session: 数据库会话
        
    Example:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        db_logger.debug("数据库会话已创建")
        yield db
    except Exception as e:
        db_logger.error(f"数据库会话出错: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        db_logger.debug("数据库会话已关闭")


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    获取数据库会话（上下文管理器）
    
    用于非 FastAPI 场景，如后台任务。
    
    Yields:
        Session: 数据库会话
        
    Example:
        with get_db_context() as db:
            db.query(Item).all()
    """
    db = SessionLocal()
    try:
        db_logger.debug("数据库会话已创建（上下文管理器）")
        yield db
    except Exception as e:
        db_logger.error(f"数据库会话出错: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        db_logger.debug("数据库会话已关闭（上下文管理器）")


async def get_db_async() -> AsyncGenerator[Session, None]:
    """
    异步获取数据库会话
    
    用于异步场景。
    
    Yields:
        Session: 数据库会话
    """
    db = SessionLocal()
    try:
        db_logger.debug("异步数据库会话已创建")
        yield db
    except Exception as e:
        db_logger.error(f"异步数据库会话出错: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        db_logger.debug("异步数据库会话已关闭")


# ===== 数据库操作 =====

def init_db() -> None:
    """
    初始化数据库
    
    创建所有定义的表结构。
    """
    try:
        db_logger.info("开始初始化数据库...")
        Base.metadata.create_all(bind=engine)
        _ensure_schema_updates()
        db_logger.info("数据库初始化完成")
    except Exception as e:
        db_logger.error(f"数据库初始化失败: {e}")
        raise


def _ensure_schema_updates() -> None:
    """Apply additive schema updates for existing databases."""
    try:
        with engine.begin() as conn:
            inspector = inspect(conn)
            if not inspector.has_table("users"):
                return
            columns = {column["name"] for column in inspector.get_columns("users")}
            if "avatar_url" not in columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512)"))
                db_logger.info("Added users.avatar_url column")
    except sqlalchemy_exc.NoInspectionAvailable:
        db_logger.warning("Skipped schema update because the database engine cannot be inspected")


def drop_db() -> None:
    """
    删除所有表（危险操作）
    
    仅用于测试环境或数据重置。
    """
    if settings.is_production():
        raise RuntimeError("生产环境不允许删除数据库")
    
    try:
        db_logger.warning("正在删除所有数据库表...")
        Base.metadata.drop_all(bind=engine)
        db_logger.warning("数据库表已删除")
    except Exception as e:
        db_logger.error(f"删除数据库表失败: {e}")
        raise


async def check_database_connection() -> bool:
    """
    检查数据库连接状态
    
    执行简单查询验证连接是否正常。
    
    Returns:
        bool: 连接正常返回 True
    """
    try:
        # 使用 run_in_executor 在同步引擎上执行异步检查
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check_connection_sync)
    except Exception as e:
        db_logger.error(f"数据库连接检查失败: {e}")
        return False


def _check_connection_sync() -> bool:
    """
    同步方式检查数据库连接
    
    Returns:
        bool: 连接正常返回 True
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        db_logger.error(f"数据库连接检查失败: {e}")
        return False


def check_database_connection_sync() -> bool:
    """
    同步检查数据库连接（供同步代码使用）
    
    Returns:
        bool: 连接正常返回 True
    """
    return _check_connection_sync()


def get_connection_info() -> dict:
    """
    获取数据库连接信息
    
    Returns:
        dict: 包含连接信息的字典
    """
    try:
        with engine.connect() as conn:
            # 获取数据库版本信息
            if settings.DATABASE_URL.startswith("sqlite"):
                result = conn.execute(text("SELECT sqlite_version()"))
                version = result.scalar()
                db_type = "SQLite"
            elif settings.DATABASE_URL.startswith("postgresql"):
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                db_type = "PostgreSQL"
            elif settings.DATABASE_URL.startswith("mysql"):
                result = conn.execute(text("SELECT VERSION()"))
                version = result.scalar()
                db_type = "MySQL"
            else:
                version = "Unknown"
                db_type = "Unknown"
        
        return {
            "type": db_type,
            "version": version,
            "url": settings.DATABASE_URL[:50] + "..." if len(settings.DATABASE_URL) > 50 else settings.DATABASE_URL,
            "pool_size": settings.DATABASE_POOL_SIZE if not settings.DATABASE_URL.startswith("sqlite") else None,
            "status": "connected"
        }
    except Exception as e:
        db_logger.error(f"获取数据库连接信息失败: {e}")
        return {
            "type": "Unknown",
            "version": "Unknown",
            "url": settings.DATABASE_URL[:50] + "...",
            "status": "error",
            "error": str(e)
        }


# ===== 事务管理 =====

@contextmanager
def transaction(db: Session) -> Generator[Session, None, None]:
    """
    事务上下文管理器
    
    自动处理提交和回滚。
    
    Args:
        db: 数据库会话
        
    Yields:
        Session: 数据库会话
        
    Example:
        with transaction(db) as tx:
            tx.add(item)
            # 自动提交或回滚
    """
    try:
        yield db
        db.commit()
        db_logger.debug("事务已提交")
    except Exception as e:
        db.rollback()
        db_logger.error(f"事务回滚: {e}")
        raise


class DatabaseRetry:
    """
    数据库重试装饰器
    
    在数据库操作失败时自动重试。
    
    Attributes:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        exceptions: 需要重试的异常类型
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 0.5,
        exceptions: tuple = (sqlalchemy_exc.OperationalError, sqlalchemy_exc.DatabaseError)
    ):
        self.max_retries = max_retries
        self.delay = delay
        self.exceptions = exceptions
    
    def __call__(self, func):
        """
        装饰器实现
        
        Args:
            func: 要装饰的函数
            
        Returns:
            function: 包装后的函数
        """
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    last_exception = e
                    db_logger.warning(
                        f"数据库操作失败，第 {attempt + 1}/{self.max_retries} 次重试: {e}"
                    )
                    if attempt < self.max_retries - 1:
                        import time
                        time.sleep(self.delay * (attempt + 1))  # 指数退避
            
            # 所有重试都失败了
            db_logger.error(f"数据库操作在 {self.max_retries} 次尝试后仍然失败")
            raise last_exception
        
        return wrapper


# ===== 健康检查 =====

def health_check() -> dict:
    """
    数据库健康检查
    
    Returns:
        dict: 包含健康状态的字典
    """
    status = {
        "connected": False,
        "connection_info": None,
        "error": None
    }
    
    try:
        if check_database_connection_sync():
            status["connected"] = True
            status["connection_info"] = get_connection_info()
        else:
            status["error"] = "无法连接到数据库"
    except Exception as e:
        status["error"] = str(e)
    
    return status


# ===== 清理函数 =====

def close_all_connections() -> None:
    """
    关闭所有数据库连接
    
    用于应用关闭时清理资源。
    """
    try:
        db_logger.info("正在关闭所有数据库连接...")
        engine.dispose()
        db_logger.info("所有数据库连接已关闭")
    except Exception as e:
        db_logger.error(f"关闭数据库连接时出错: {e}")
