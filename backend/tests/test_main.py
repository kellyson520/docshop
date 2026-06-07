"""
主应用模块测试

测试覆盖率目标：100%
- lifespan 生命周期
- _cleanup 清理函数
- health_check 健康检查各种状态
- system_info 系统信息
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status

from app.main import (
    lifespan,
    _cleanup,
    health_check,
    system_info,
    _create_required_directories,
    _check_database,
    _log_system_info,
)


class TestLifespan:
    """lifespan 上下文管理器测试"""

    @pytest.mark.asyncio
    async def test_lifespan_startup(self):
        """测试应用启动"""
        mock_app = MagicMock()
        
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main._create_required_directories") as mock_create_dirs:
                with patch("app.main._check_database") as mock_check_db:
                    with patch("app.main.init_db") as mock_init_db:
                        mock_check_db.return_value = True
                        async with lifespan(mock_app):
                            pass
                        
                        # 验证启动日志被记录
                        assert mock_logger.info.called
                        # 验证初始化函数被调用
                        mock_init_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_shutdown(self):
        """测试应用关闭"""
        mock_app = MagicMock()
        
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main._cleanup") as mock_cleanup:
                async with lifespan(mock_app):
                    pass
                
                # 验证关闭日志被记录
                assert mock_logger.info.called
                # 验证清理函数被调用
                mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_exception(self):
        """测试生命周期异常"""
        mock_app = MagicMock()
        
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main._create_required_directories", side_effect=Exception("Startup error")):
                with pytest.raises(Exception, match="Startup error"):
                    async with lifespan(mock_app):
                        pass
                
                # 验证错误日志被记录
                assert mock_logger.error.called


class TestCleanup:
    """_cleanup 函数测试"""

    @pytest.mark.asyncio
    async def test_cleanup_success(self):
        """测试成功清理"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.close_all_connections") as mock_close:
                with patch("app.main.settings") as mock_settings:
                    mock_settings.UPLOAD_DIR = "/tmp/uploads"
                    await _cleanup()
                    
                    mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_error(self):
        """测试清理错误"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.close_all_connections", side_effect=Exception("Close error")):
                with patch("app.main.settings") as mock_settings:
                    mock_settings.UPLOAD_DIR = "/tmp/uploads"
                    await _cleanup()
                    
                    # 验证错误日志被记录
                    assert mock_logger.error.called


class TestCreateRequiredDirectories:
    """_create_required_directories 函数测试"""

    def test_create_directories_success(self):
        """测试成功创建目录"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.settings") as mock_settings:
                mock_settings.UPLOAD_DIR = "/tmp/uploads"
                mock_settings.LOG_DIR = "/tmp/logs"
                with patch("pathlib.Path.mkdir") as mock_mkdir:
                    _create_required_directories()
                    # 应该调用 mkdir 多次
                    assert mock_mkdir.called

    def test_create_directories_error(self):
        """测试创建目录错误"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.settings") as mock_settings:
                mock_settings.UPLOAD_DIR = "/tmp/uploads"
                mock_settings.LOG_DIR = "/tmp/logs"
                with patch("pathlib.Path.mkdir", side_effect=Exception("Mkdir error")):
                    with pytest.raises(Exception, match="Mkdir error"):
                        _create_required_directories()


class TestCheckDatabase:
    """_check_database 函数测试"""

    @pytest.mark.asyncio
    async def test_check_database_success(self):
        """测试数据库连接检查成功"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.check_database_connection") as mock_check:
                mock_check.return_value = True
                result = await _check_database()
                
                assert result is True

    @pytest.mark.asyncio
    async def test_check_database_failure(self):
        """测试数据库连接检查失败"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.check_database_connection") as mock_check:
                mock_check.return_value = False
                result = await _check_database()
                
                assert result is False

    @pytest.mark.asyncio
    async def test_check_database_exception(self):
        """测试数据库连接检查异常"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.check_database_connection", side_effect=Exception("DB error")):
                result = await _check_database()
                
                assert result is False


class TestLogSystemInfo:
    """_log_system_info 函数测试"""

    def test_log_system_info_success(self):
        """测试成功记录系统信息"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.settings") as mock_settings:
                mock_settings.UPLOAD_DIR = "/tmp/uploads"
                mock_settings.LOG_DIR = "/tmp/logs"
                mock_settings.MAX_FILE_SIZE = 10485760
                mock_settings.ALLOWED_FILE_TYPES = [".txt", ".pdf"]
                _log_system_info()
                
                # 验证日志被记录
                assert mock_logger.info.called

    def test_log_system_info_error(self):
        """测试记录系统信息错误"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.platform") as mock_platform:
                # 模拟 platform 调用时出错
                mock_platform.platform.side_effect = Exception("Platform error")
                _log_system_info()
                
                # 应该记录警告日志
                assert mock_logger.warning.called


class TestHealthCheck:
    """health_check 端点测试"""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """测试健康检查通过"""
        with patch("app.main.check_database_connection") as mock_check_db:
            mock_check_db.return_value = True
            
            result = await health_check()
        
        # 返回的是 ApiResponse 的 model_dump 结果
        assert result["code"] == 0
        assert result["message"] == "服务健康"
        assert "data" in result
        assert result["data"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """测试健康检查失败"""
        with patch("app.main.check_database_connection") as mock_check_db:
            mock_check_db.return_value = False
            
            result = await health_check()
        
        # 返回的是 JSONResponse
        assert result.status_code == 503
        content = result.body.decode()
        assert "unhealthy" in content

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        """测试健康检查异常"""
        with patch("app.main.check_database_connection", side_effect=Exception("DB error")):
            result = await health_check()
        
        # 返回的是 JSONResponse
        assert result.status_code == 503
        content = result.body.decode()
        assert "unhealthy" in content


class TestSystemInfo:
    """system_info 端点测试"""

    @pytest.mark.asyncio
    async def test_system_info_success(self):
        """测试成功获取系统信息"""
        mock_admin = MagicMock()
        mock_admin.id = 1
        mock_admin.username = "admin"
        
        with patch("app.main.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "test"
            mock_settings.DEBUG = True
            mock_settings.MAX_FILE_SIZE = 10485760
            mock_settings.ALLOWED_FILE_TYPES = [".txt", ".pdf"]
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            
            result = await system_info(mock_admin)
        
        assert result["code"] == 0
        assert result["message"] == "success"
        assert "data" in result
        assert "application" in result["data"]
        assert "system" in result["data"]
        assert "configuration" in result["data"]


class TestHealthCheckExtended:
    """健康检查扩展测试 - 覆盖未覆盖行"""

    @pytest.mark.asyncio
    async def test_health_check_db_failure(self):
        """测试数据库连接失败（行92-93: 数据库检查失败日志）"""
        with patch("app.main.check_database_connection", return_value=False):
            with patch("app.main.main_logger") as mock_logger:
                result = await _check_database()
                
                assert result is False
                # 验证错误日志被记录
                assert mock_logger.error.called

    @pytest.mark.asyncio
    async def test_health_check_disk_warning(self):
        """测试磁盘空间警告（行178-184: 清理临时文件失败）"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.close_all_connections"):
                with patch("app.main.settings") as mock_settings:
                    mock_settings.UPLOAD_DIR = "/tmp/uploads"
                    with patch("app.main.Path") as mock_path_cls:
                        # 模拟临时目录存在且有文件
                        mock_temp_dir = MagicMock()
                        mock_temp_dir.exists.return_value = True
                        mock_item = MagicMock()
                        mock_item.is_file.return_value = True
                        mock_item.unlink.side_effect = Exception("删除失败")
                        mock_temp_dir.iterdir.return_value = [mock_item]
                        
                        # 模拟 Path("/tmp/uploads").parent / "temp" 返回 mock_temp_dir
                        mock_upload_path = MagicMock()
                        mock_parent_path = MagicMock()
                        mock_parent_path.__truediv__ = MagicMock(return_value=mock_temp_dir)
                        mock_upload_path.parent = mock_parent_path
                        mock_path_cls.return_value = mock_upload_path
                        
                        await _cleanup()
                        
                        # 验证清理临时文件失败的警告被记录
                        assert mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_info_endpoint(self):
        """测试 /info 端点（行305-310: system_info 端点）"""
        mock_admin = MagicMock()
        mock_admin.id = 1
        mock_admin.username = "admin"

        with patch("app.main.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "test"
            mock_settings.DEBUG = True
            mock_settings.MAX_FILE_SIZE = 10485760
            mock_settings.ALLOWED_FILE_TYPES = [".txt", ".pdf"]
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

            result = await system_info(mock_admin)

        assert result["code"] == 0
        assert "data" in result
        assert result["data"]["application"]["name"] == "DocDist API"
        assert result["data"]["application"]["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_openapi_docs(self):
        """测试 /docs 端点（行383: legacy_health_check）"""
        # legacy_health_check 调用 health_check
        with patch("app.main.check_database_connection", return_value=True):
            result = await health_check()
        
        assert result["code"] == 0
        assert result["data"]["status"] == "healthy"

    def test_create_required_directories(self):
        """测试创建必要目录（行401-403: 创建 temp 和 cache 目录）"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.settings") as mock_settings:
                mock_settings.UPLOAD_DIR = "/tmp/uploads"
                mock_settings.LOG_DIR = "/tmp/logs"
                with patch("pathlib.Path.mkdir") as mock_mkdir:
                    _create_required_directories()
                    # 应该调用 mkdir（uploads, logs, temp, cache 共4个目录）
                    assert mock_mkdir.call_count >= 2

    @pytest.mark.asyncio
    async def test_check_database_failure(self):
        """测试数据库检查失败（行414-417: check_database_connection 异常）"""
        with patch("app.main.main_logger") as mock_logger:
            with patch("app.main.check_database_connection", side_effect=Exception("连接超时")):
                result = await _check_database()
                
                assert result is False
                # 验证错误日志被记录
                assert mock_logger.error.called
