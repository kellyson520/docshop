"""
数据库模块测试

测试覆盖率目标：100%
- _create_engine_with_pool 各种数据库类型
- 事件监听器 (on_connect, on_checkout, on_checkin)
- get_db 同步会话
- get_db_async 异步会话
- get_db_context 上下文管理器
- init_db 初始化数据库
- drop_db 删除数据库
- check_database_connection 检查连接
- get_connection_info 连接信息
- transaction 事务管理器
- DatabaseRetry 重试装饰器
- health_check 健康检查
- close_all_connections 关闭连接
"""

import pytest
import asyncio
import inspect
from unittest.mock import patch, MagicMock, Mock, call
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError, DatabaseError as SQLAlchemyDatabaseError

from app.database import (
    Base,
    _create_engine_with_pool,
    _ensure_schema_updates,
    get_db,
    get_db_async,
    get_db_context,
    init_db,
    drop_db,
    check_database_connection,
    check_database_connection_sync,
    get_connection_info,
    transaction,
    DatabaseRetry,
    health_check,
    close_all_connections,
    on_connect,
    on_checkout,
    on_checkin,
)


class TestCreateEngineWithPool:
    """_create_engine_with_pool 函数测试"""

    @patch("app.database.settings")
    @patch("app.database.create_engine")
    @patch("app.database.db_logger")
    def test_create_sqlite_engine(self, mock_logger, mock_create_engine, mock_settings):
        """测试创建 SQLite 引擎"""
        mock_settings.DATABASE_URL = "sqlite:///./test.db"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        engine = _create_engine_with_pool()
        
        assert engine == mock_engine
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "sqlite:///./test.db"
        assert call_args[1]["poolclass"].__name__ == "NullPool"
        assert call_args[1]["connect_args"]["check_same_thread"] == False

    @patch("app.database.settings")
    @patch("app.database.create_engine")
    @patch("app.database.db_logger")
    def test_create_postgres_engine(self, mock_logger, mock_create_engine, mock_settings):
        """测试创建 PostgreSQL 引擎"""
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost/db"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.DATABASE_POOL_SIZE = 5
        mock_settings.DATABASE_MAX_OVERFLOW = 10
        mock_settings.DATABASE_POOL_RECYCLE = 3600
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        engine = _create_engine_with_pool()
        
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "postgresql://user:pass@localhost/db"
        assert call_args[1]["poolclass"].__name__ == "QueuePool"
        assert call_args[1]["pool_size"] == 5
        assert call_args[1]["max_overflow"] == 10
        assert call_args[1]["pool_recycle"] == 3600
        assert call_args[1]["pool_pre_ping"] == True

    @patch("app.database.settings")
    @patch("app.database.create_engine")
    @patch("app.database.db_logger")
    def test_create_mysql_engine(self, mock_logger, mock_create_engine, mock_settings):
        """测试创建 MySQL 引擎"""
        mock_settings.DATABASE_URL = "mysql://user:pass@localhost/db"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.DATABASE_POOL_SIZE = 10
        mock_settings.DATABASE_MAX_OVERFLOW = 20
        mock_settings.DATABASE_POOL_RECYCLE = 1800
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        engine = _create_engine_with_pool()
        
        call_args = mock_create_engine.call_args
        assert "mysql" in call_args[0][0]
        assert call_args[1]["poolclass"].__name__ == "QueuePool"

    @patch("app.database.settings")
    @patch("app.database.create_engine")
    @patch("app.database.db_logger")
    def test_create_engine_with_debug(self, mock_logger, mock_create_engine, mock_settings):
        """测试调试模式创建引擎"""
        mock_settings.DATABASE_URL = "sqlite:///./test.db"
        mock_settings.DEBUG = True
        mock_settings.LOG_LEVEL = "DEBUG"
        
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        engine = _create_engine_with_pool()
        
        call_args = mock_create_engine.call_args
        assert call_args[1]["echo"] == True

    @patch("app.database.settings")
    @patch("app.database.create_engine")
    @patch("app.database.db_logger")
    def test_create_engine_failure(self, mock_logger, mock_create_engine, mock_settings):
        """测试创建引擎失败"""
        mock_settings.DATABASE_URL = "sqlite:///./test.db"
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"
        
        mock_create_engine.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            _create_engine_with_pool()


class TestEventListeners:
    """事件监听器测试"""

    @patch("app.database.db_logger")
    def test_on_connect(self, mock_logger):
        """测试连接建立事件"""
        mock_conn = MagicMock()
        mock_record = MagicMock()
        
        on_connect(mock_conn, mock_record)
        
        mock_logger.debug.assert_called_once_with("新数据库连接已建立")

    @patch("app.database.db_logger")
    def test_on_checkout(self, mock_logger):
        """测试连接取出事件"""
        mock_conn = MagicMock()
        mock_record = MagicMock()
        mock_proxy = MagicMock()
        
        on_checkout(mock_conn, mock_record, mock_proxy)
        
        mock_logger.debug.assert_called_once_with("从连接池取出连接")

    @patch("app.database.db_logger")
    def test_on_checkin(self, mock_logger):
        """测试连接归还事件"""
        mock_conn = MagicMock()
        mock_record = MagicMock()
        
        on_checkin(mock_conn, mock_record)
        
        mock_logger.debug.assert_called_once_with("连接归还到连接池")


class TestGetDb:
    """get_db 函数测试"""

    @patch("app.database.SessionLocal")
    @patch("app.database.db_logger")
    def test_get_db_success(self, mock_logger, mock_session_local):
        """测试正常获取会话"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        gen = get_db()
        db = next(gen)
        
        assert db == mock_db
        mock_logger.debug.assert_called_with("数据库会话已创建")
        
        # 清理
        try:
            next(gen)
        except StopIteration:
            pass

    @patch("app.database.SessionLocal")
    @patch("app.database.db_logger")
    def test_get_db_exception_rollback(self, mock_logger, mock_session_local):
        """测试异常时回滚"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        gen = get_db()
        db = next(gen)
        
        # 模拟异常
        try:
            gen.throw(Exception, "Test error")
        except Exception:
            pass
        
        mock_db.rollback.assert_called_once()
        mock_logger.error.assert_called()

    @patch("app.database.SessionLocal")
    @patch("app.database.db_logger")
    def test_get_db_close(self, mock_logger, mock_session_local):
        """测试会话关闭"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        gen = get_db()
        db = next(gen)
        
        # 正常结束
        try:
            next(gen)
        except StopIteration:
            pass
        
        mock_db.close.assert_called_once()


class TestGetDbAsync:
    """get_db_async 函数测试"""

    @patch("app.database.SessionLocal")
    @patch("app.database.db_logger")
    def test_get_db_async_is_explicit_sync_compatibility_wrapper(self, mock_logger, mock_session_local):
        """get_db_async 不应是假 async dependency，而应是明确同步兼容包装。"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        assert not inspect.isasyncgenfunction(get_db_async)
        gen = get_db_async()
        db = next(gen)
        
        assert db == mock_db
        mock_logger.debug.assert_called_with("数据库会话已创建")
        
        # 清理
        try:
            next(gen)
        except StopIteration:
            pass

    @patch("app.database.SessionLocal")
    @patch("app.database.db_logger")
    def test_get_db_async_exception(self, mock_logger, mock_session_local):
        """同步兼容包装异常时仍应回滚"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        gen = get_db_async()
        db = next(gen)
        
        try:
            gen.throw(Exception("Test error"))
        except Exception:
            pass
        
        mock_db.rollback.assert_called_once()


class TestGetDbContext:
    """get_db_context 上下文管理器测试"""

    @patch("app.database.SessionLocal")
    @patch("app.database.db_logger")
    def test_context_manager_success(self, mock_logger, mock_session_local):
        """测试上下文管理器正常执行"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        with get_db_context() as db:
            assert db == mock_db
        
        mock_db.close.assert_called_once()

    @patch("app.database.SessionLocal")
    @patch("app.database.db_logger")
    def test_context_manager_exception(self, mock_logger, mock_session_local):
        """测试上下文管理器异常处理"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        with pytest.raises(Exception, match="Test error"):
            with get_db_context() as db:
                raise Exception("Test error")
        
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()


class TestInitDb:
    """init_db 函数测试"""

    @patch("app.database.engine")
    @patch("app.database.Base.metadata")
    @patch("app.database.db_logger")
    def test_init_db_success(self, mock_logger, mock_metadata, mock_engine):
        """测试成功初始化数据库"""
        init_db()
        
        mock_metadata.create_all.assert_called_once_with(bind=mock_engine)
        mock_logger.info.assert_any_call("开始初始化数据库...")
        mock_logger.info.assert_any_call("数据库初始化完成")

    @patch("app.database.engine")
    @patch("app.database.Base.metadata")
    @patch("app.database.db_logger")
    def test_init_db_failure(self, mock_logger, mock_metadata, mock_engine):
        """测试初始化失败"""
        mock_metadata.create_all.side_effect = Exception("Create failed")
        
        with pytest.raises(Exception, match="Create failed"):
            init_db()
        
        mock_logger.error.assert_called_once()

    def test_phase1_access_control_tables_are_registered_in_metadata(self):
        """Phase 1 新增访问控制表应注册到 metadata。"""
        tables = set(Base.metadata.tables.keys())
        assert "user_groups" in tables
        assert "user_group_members" in tables
        assert "resource_access_policies" in tables
        assert "resource_access_groups" in tables

    @patch("app.database.engine")
    @patch("app.database.inspect")
    def test_phase1_share_token_columns_get_additive_schema_updates(self, mock_inspect, mock_engine):
        """旧 share_tokens 表应补齐 Phase 1 所需列。"""
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn

        inspector = MagicMock()
        inspector.has_table.side_effect = lambda table_name: table_name == "share_tokens"
        inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "token"},
            {"name": "resource_type"},
            {"name": "resource_id"},
            {"name": "allow_download"},
        ]
        mock_inspect.return_value = inspector

        _ensure_schema_updates()

        executed_sql = [str(call.args[0]) for call in mock_conn.execute.call_args_list]
        assert any("ALTER TABLE share_tokens ADD COLUMN require_login" in sql for sql in executed_sql)
        assert any("ALTER TABLE share_tokens ADD COLUMN password_hash" in sql for sql in executed_sql)
        assert any("ALTER TABLE share_tokens ADD COLUMN allow_preview" in sql for sql in executed_sql)
        assert any("ALTER TABLE share_tokens ADD COLUMN allow_diff" in sql for sql in executed_sql)
        assert any("ALTER TABLE share_tokens ADD COLUMN allow_versions" in sql for sql in executed_sql)
        assert any("ALTER TABLE share_tokens ADD COLUMN policy_mode" in sql for sql in executed_sql)

    @patch("app.database.engine")
    @patch("app.database.inspect")
    def test_user_columns_get_additive_schema_updates_for_legacy_databases(self, mock_inspect, mock_engine):
        """旧 users 表升级时应补齐当前登录必需列，避免 VPS 升级后 admin 创建失败。"""
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn

        inspector = MagicMock()
        inspector.has_table.side_effect = lambda table_name: table_name == "users"
        inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "username"},
            {"name": "password_hash"},
            {"name": "role"},
            {"name": "created_at"},
            {"name": "updated_at"},
        ]
        mock_inspect.return_value = inspector

        _ensure_schema_updates()

        executed_sql = [str(call.args[0]) for call in mock_conn.execute.call_args_list]
        assert any("ALTER TABLE users ADD COLUMN email" in sql for sql in executed_sql)
        assert any("ALTER TABLE users ADD COLUMN is_active" in sql for sql in executed_sql)
        assert any("ALTER TABLE users ADD COLUMN avatar_url" in sql for sql in executed_sql)


class TestDropDb:
    """drop_db 函数测试"""

    @patch("app.database.settings")
    @patch("app.database.engine")
    @patch("app.database.Base.metadata")
    @patch("app.database.db_logger")
    def test_drop_db_success(self, mock_logger, mock_metadata, mock_engine, mock_settings):
        """测试成功删除数据库"""
        mock_settings.is_production.return_value = False
        
        drop_db()
        
        mock_metadata.drop_all.assert_called_once_with(bind=mock_engine)
        mock_logger.warning.assert_any_call("正在删除所有数据库表...")

    @patch("app.database.settings")
    def test_drop_db_production(self, mock_settings):
        """测试生产环境禁止删除"""
        mock_settings.is_production.return_value = True
        
        with pytest.raises(RuntimeError, match="生产环境不允许删除数据库"):
            drop_db()

    @patch("app.database.settings")
    @patch("app.database.engine")
    @patch("app.database.Base.metadata")
    @patch("app.database.db_logger")
    def test_drop_db_failure(self, mock_logger, mock_metadata, mock_engine, mock_settings):
        """测试删除失败"""
        mock_settings.is_production.return_value = False
        mock_metadata.drop_all.side_effect = Exception("Drop failed")
        
        with pytest.raises(Exception, match="Drop failed"):
            drop_db()


class TestCheckDatabaseConnection:
    """检查数据库连接测试"""

    @pytest.mark.asyncio
    @patch("app.database._check_connection_sync")
    async def test_check_connection_success(self, mock_check_sync):
        """测试连接成功"""
        mock_check_sync.return_value = True
        
        result = await check_database_connection()
        
        assert result is True

    @pytest.mark.asyncio
    @patch("app.database._check_connection_sync")
    @patch("app.database.db_logger")
    async def test_check_connection_failure(self, mock_logger, mock_check_sync):
        """测试连接失败"""
        mock_check_sync.side_effect = Exception("Connection error")
        
        result = await check_database_connection()
        
        assert result is False
        mock_logger.error.assert_called_once()


class TestCheckConnectionSync:
    """同步检查连接测试"""

    @patch("app.database.engine")
    def test_check_connection_sync_success(self, mock_engine):
        """测试同步检查成功"""
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        
        result = check_database_connection_sync()
        
        assert result is True
        mock_conn.execute.assert_called_once()

    @patch("app.database.engine")
    @patch("app.database.db_logger")
    def test_check_connection_sync_failure(self, mock_logger, mock_engine):
        """测试同步检查失败"""
        mock_engine.connect.side_effect = Exception("Connection error")
        
        result = check_database_connection_sync()
        
        assert result is False


class TestGetConnectionInfo:
    """get_connection_info 函数测试"""

    @patch("app.database.engine")
    @patch("app.database.settings")
    def test_get_sqlite_info(self, mock_settings, mock_engine):
        """测试获取 SQLite 连接信息"""
        mock_settings.DATABASE_URL = "sqlite:///./test.db"
        
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = "3.35.0"
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        
        result = get_connection_info()
        
        assert result["type"] == "SQLite"
        assert result["version"] == "3.35.0"
        assert result["status"] == "connected"

    @patch("app.database.engine")
    @patch("app.database.settings")
    def test_get_postgres_info(self, mock_settings, mock_engine):
        """测试获取 PostgreSQL 连接信息"""
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost/db"
        mock_settings.DATABASE_POOL_SIZE = 5
        
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = "PostgreSQL 13.0"
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        
        result = get_connection_info()
        
        assert result["type"] == "PostgreSQL"
        assert result["version"] == "PostgreSQL 13.0"
        assert result["pool_size"] == 5

    @patch("app.database.engine")
    @patch("app.database.settings")
    def test_get_mysql_info(self, mock_settings, mock_engine):
        """测试获取 MySQL 连接信息"""
        mock_settings.DATABASE_URL = "mysql://user:pass@localhost/db"
        mock_settings.DATABASE_POOL_SIZE = 10
        
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = "8.0.0"
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        
        result = get_connection_info()
        
        assert result["type"] == "MySQL"
        assert result["version"] == "8.0.0"

    @patch("app.database.engine")
    @patch("app.database.settings")
    @patch("app.database.db_logger")
    def test_get_connection_info_failure(self, mock_logger, mock_settings, mock_engine):
        """测试获取连接信息失败"""
        mock_settings.DATABASE_URL = "sqlite:///./test.db"
        mock_engine.connect.side_effect = Exception("Connection error")
        
        result = get_connection_info()
        
        assert result["status"] == "error"
        assert "error" in result


class TestTransaction:
    """transaction 上下文管理器测试"""

    @patch("app.database.db_logger")
    def test_transaction_success(self, mock_logger):
        """测试事务成功提交"""
        mock_db = MagicMock()
        
        with transaction(mock_db) as tx:
            assert tx == mock_db
        
        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()
        mock_logger.debug.assert_called_with("事务已提交")

    @patch("app.database.db_logger")
    def test_transaction_rollback(self, mock_logger):
        """测试事务回滚"""
        mock_db = MagicMock()
        
        with pytest.raises(Exception, match="Test error"):
            with transaction(mock_db) as tx:
                raise Exception("Test error")
        
        mock_db.commit.assert_not_called()
        mock_db.rollback.assert_called_once()
        mock_logger.error.assert_called_with("事务回滚: Test error")


class TestDatabaseRetry:
    """DatabaseRetry 装饰器测试"""

    def test_retry_success_first_attempt(self):
        """测试第一次尝试成功"""
        retry = DatabaseRetry(max_retries=3, delay=0.1)
        
        @retry
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"

    def test_retry_success_after_failures(self):
        """测试失败后重试成功"""
        retry = DatabaseRetry(max_retries=3, delay=0.01)
        
        call_count = 0
        
        @retry
        def sometimes_fail():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OperationalError("Connection lost", None, None)
            return "success"
        
        result = sometimes_fail()
        assert result == "success"
        assert call_count == 3

    def test_retry_all_attempts_fail(self):
        """测试所有重试都失败"""
        retry = DatabaseRetry(max_retries=3, delay=0.01)
        
        @retry
        def always_fail():
            raise OperationalError("Connection lost", None, None)
        
        with pytest.raises(OperationalError):
            always_fail()

    def test_retry_non_retryable_exception(self):
        """测试非重试异常直接抛出"""
        retry = DatabaseRetry(max_retries=3, delay=0.1)
        
        @retry
        def raise_value_error():
            raise ValueError("Not retryable")
        
        with pytest.raises(ValueError):
            raise_value_error()

    def test_retry_does_not_retry_non_transient_database_errors(self):
        """IntegrityError 等非瞬时数据库异常不应被默认重试。"""
        retry = DatabaseRetry(max_retries=3, delay=0.01)
        call_count = 0

        @retry
        def raise_integrity_error():
            nonlocal call_count
            call_count += 1
            raise IntegrityError("duplicate", None, None)

        with pytest.raises(IntegrityError):
            raise_integrity_error()

        assert call_count == 1

    @patch("app.database.db_logger")
    def test_retry_logs_warning(self, mock_logger):
        """测试重试记录警告日志"""
        retry = DatabaseRetry(max_retries=2, delay=0.01)
        
        @retry
        def fail_once():
            raise OperationalError("Connection lost", None, None)
        
        try:
            fail_once()
        except OperationalError:
            pass
        
        assert mock_logger.warning.called
        assert mock_logger.error.called


class TestHealthCheck:
    """health_check 函数测试"""

    @patch("app.database.check_database_connection_sync")
    @patch("app.database.get_connection_info")
    def test_health_check_healthy(self, mock_get_info, mock_check):
        """测试健康检查通过"""
        mock_check.return_value = True
        mock_get_info.return_value = {"type": "SQLite", "version": "3.35.0"}
        
        result = health_check()
        
        assert result["connected"] is True
        assert result["connection_info"] is not None
        assert result["error"] is None

    @patch("app.database.check_database_connection_sync")
    def test_health_check_unhealthy(self, mock_check):
        """测试健康检查失败"""
        mock_check.return_value = False
        
        result = health_check()
        
        assert result["connected"] is False
        assert result["error"] == "无法连接到数据库"

    @patch("app.database.check_database_connection_sync")
    def test_health_check_exception(self, mock_check):
        """测试健康检查异常"""
        mock_check.side_effect = Exception("Check error")
        
        result = health_check()
        
        assert result["connected"] is False
        assert "Check error" in result["error"]


class TestCloseAllConnections:
    """close_all_connections 函数测试"""

    @patch("app.database.engine")
    @patch("app.database.db_logger")
    def test_close_connections_success(self, mock_logger, mock_engine):
        """测试成功关闭连接"""
        close_all_connections()
        
        mock_engine.dispose.assert_called_once()
        mock_logger.info.assert_any_call("正在关闭所有数据库连接...")
        mock_logger.info.assert_any_call("所有数据库连接已关闭")

    @patch("app.database.engine")
    @patch("app.database.db_logger")
    def test_close_connections_failure(self, mock_logger, mock_engine):
        """测试关闭连接失败"""
        mock_engine.dispose.side_effect = Exception("Dispose error")
        
        close_all_connections()
        
        mock_logger.error.assert_called_once()
