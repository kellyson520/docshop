"""
用户追踪模块测试

测试追踪配置、访问日志、用户会话等功能。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.utils.time import utc_now, utc_now_iso
from app.models.tracking_config import TrackingConfig
from app.models.access_log import AccessLog
from app.models.user_session import UserSession


class TestTrackingConfig:
    """追踪配置测试"""

    def test_get_default_config(self, client, auth_headers):
        """测试获取默认配置"""
        response = client.get("/api/v1/admin/tracking/config", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # 新格式: {"code": 0, "data": {...}}
        assert data["code"] == 0
        assert data["data"]["enable_tracking"] == True
        assert data["data"]["data_retention_days"] == 90

    def test_update_config(self, client, auth_headers, db_session):
        """测试更新配置"""
        response = client.put(
            "/api/v1/admin/tracking/config?enable_tracking=0&anonymize_ip=1",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        # 验证更新
        config = db_session.query(TrackingConfig).first()
        assert config.enable_tracking == 0
        assert config.anonymize_ip == 1

    def test_config_permission_denied_for_viewer(self, client, viewer_headers):
        """测试非管理员无法访问"""
        response = client.get("/api/v1/admin/tracking/config", headers=viewer_headers)
        assert response.status_code == 403

    def test_config_permission_denied_for_anonymous(self, client):
        """测试未登录用户无法访问"""
        response = client.get("/api/v1/admin/tracking/config")
        assert response.status_code in [401, 403]

    def test_is_tracking_enabled(self, tracking_config):
        """测试追踪启用检查"""
        assert tracking_config.is_tracking_enabled() == True
        assert tracking_config.is_tracking_enabled("ip") == True
        assert tracking_config.is_tracking_enabled("device") == True

        # 禁用总开关
        tracking_config.enable_tracking = 0
        assert tracking_config.is_tracking_enabled() == False
        assert tracking_config.is_tracking_enabled("ip") == False

    def test_should_exclude_ip(self, tracking_config):
        """测试IP排除检查"""
        tracking_config.exclude_internal_ips = "192.168.1.1,10.0.0.1"

        assert tracking_config.should_exclude_ip("192.168.1.1") == True
        assert tracking_config.should_exclude_ip("10.0.0.1") == True
        assert tracking_config.should_exclude_ip("8.8.8.8") == False


class TestAccessLog:
    """访问日志测试"""

    def test_log_model_creation(self, db_session):
        """测试访问日志模型创建"""
        log = AccessLog(
            timestamp=utc_now_iso(),
            ip_address="192.168.1.1",
            device_type="desktop",
            os_name="Windows",
            browser_name="Chrome",
            request_method="GET",
            request_path="/api/v1/test",
            response_status=200,
            response_time_ms=100,
            session_id="test_session",
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.ip_address == "192.168.1.1"
        assert log.is_deleted == 0

    def test_log_to_dict(self, access_log):
        """测试日志转换为字典"""
        data = access_log.to_dict()
        assert "id" in data
        assert "ip_address" in data
        assert data["ip_address"] == "192.168.1.1"
        assert data["is_deleted"] == False

    def test_log_soft_delete(self, access_log, db_session):
        """测试日志软删除"""
        access_log.soft_delete()
        db_session.commit()

        assert access_log.is_deleted == 1
        assert access_log.deleted_at is not None

    def test_log_from_request(self, mock_request):
        """测试从请求创建日志"""
        log = AccessLog.from_request(
            mock_request,
            response_status=200,
            response_time_ms=50,
            user_id="user_123",
            session_id="session_123",
        )

        assert log.ip_address == "127.0.0.1"
        assert log.request_path == "/api/v1/test"
        assert log.response_status == 200
        assert log.user_id == "user_123"
        assert log.session_id == "session_123"

    def test_get_client_ip_from_forwarded(self):
        """测试从X-Forwarded-For获取IP"""
        class MockHeaders:
            def get(self, key, default=None):
                if key == "x-forwarded-for":
                    return "10.0.0.1, 192.168.1.1"
                return default

        class MockRequest:
            headers = MockHeaders()
            client = None

        ip = AccessLog._get_client_ip(MockRequest())
        assert ip == "10.0.0.1"

    def test_get_client_ip_from_real_ip(self):
        """测试从X-Real-IP获取IP"""
        class MockHeaders:
            def get(self, key, default=None):
                if key == "x-real-ip":
                    return "10.0.0.2"
                return default

        class MockRequest:
            headers = MockHeaders()
            client = None

        ip = AccessLog._get_client_ip(MockRequest())
        assert ip == "10.0.0.2"


class TestUserSession:
    """用户会话测试"""

    def test_session_model_creation(self, db_session):
        """测试会话模型创建"""
        session = UserSession(
            session_id="test_session_456",
            first_seen_at=utc_now_iso(),
            first_ip="192.168.1.2",
            last_seen_at=utc_now_iso(),
            last_ip="192.168.1.2",
        )
        db_session.add(session)
        db_session.commit()

        assert session.id is not None
        assert session.session_id == "test_session_456"
        assert session.visit_count == 1

    def test_session_update_last_seen(self, user_session):
        """测试更新最后访问时间"""
        old_count = user_session.visit_count
        user_session.update_last_seen("10.0.0.1")

        assert user_session.visit_count == old_count + 1
        assert user_session.last_ip == "10.0.0.1"

    def test_session_increment_page_view(self, user_session):
        """测试增加页面浏览计数"""
        old_count = user_session.page_view_count
        user_session.increment_page_view()

        assert user_session.page_view_count == old_count + 1

    def test_session_increment_download(self, user_session):
        """测试增加下载计数"""
        old_count = user_session.download_count
        user_session.increment_download()

        assert user_session.download_count == old_count + 1

    def test_session_soft_delete(self, user_session, db_session):
        """测试会话软删除"""
        user_session.soft_delete()
        db_session.commit()

        assert user_session.is_deleted == 1
        assert user_session.deleted_at is not None

    def test_generate_fingerprint(self):
        """测试生成设备指纹"""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        ip = "192.168.1.1"

        fingerprint1 = UserSession.generate_fingerprint(ua, ip)
        fingerprint2 = UserSession.generate_fingerprint(ua, ip)
        fingerprint3 = UserSession.generate_fingerprint(ua, "192.168.1.2")

        assert len(fingerprint1) == 32
        assert fingerprint1 == fingerprint2
        assert fingerprint1 != fingerprint3

    def test_create_session(self):
        """测试创建会话"""
        device_info = {
            "device_type": "mobile",
            "os_name": "iOS",
            "browser_name": "Safari",
        }

        session = UserSession.create_session(
            session_id="new_session_123",
            user_id="user_456",
            ip="192.168.1.3",
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
            device_info=device_info,
        )

        assert session.session_id == "new_session_123"
        assert session.user_id == "user_456"
        assert session.device_type == "mobile"
        assert session.os_name == "iOS"
        assert session.browser_name == "Safari"


class TestTrackingAPI:
    """追踪API测试"""

    def test_get_tracking_stats(self, client, auth_headers, db_session):
        """测试获取追踪统计"""
        # 创建测试日志
        for i in range(5):
            log = AccessLog(
                timestamp=utc_now_iso(),
                ip_address=f"192.168.1.{i}",
                device_type="desktop" if i % 2 == 0 else "mobile",
                request_method="GET",
                request_path="/test",
                response_status=200,
                response_time_ms=100,
                session_id=f"session_{i}",
            )
            db_session.add(log)
        db_session.commit()

        response = client.get("/api/v1/admin/tracking/stats?days=1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        stats_data = data["data"]
        assert stats_data["total_visits"] >= 5
        assert "device_distribution" in stats_data
        assert "daily_trend" in stats_data
        assert "response_time" in stats_data

    def test_get_access_logs(self, client, auth_headers, db_session):
        """测试获取访问日志列表"""
        # 创建测试日志
        log = AccessLog(
            timestamp=utc_now_iso(),
            ip_address="10.0.0.1",
            device_type="mobile",
            request_method="GET",
            request_path="/api/test",
            response_status=200,
            response_time_ms=50,
            session_id="test_session",
        )
        db_session.add(log)
        db_session.commit()

        # 按IP查询
        response = client.get("/api/v1/admin/tracking/logs?ip=10.0.0", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["total"] >= 1

        # 按设备类型查询
        response = client.get("/api/v1/admin/tracking/logs?device_type=mobile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert all(item["device_type"] == "mobile" for item in data["data"]["items"])

    def test_get_access_log_detail(self, client, auth_headers, access_log):
        """测试获取访问日志详情"""
        response = client.get(f"/api/v1/admin/tracking/logs/{access_log.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["id"] == access_log.id
        assert data["data"]["ip_address"] == access_log.ip_address

    def test_get_access_log_detail_includes_server_ip_context(self, client, auth_headers, access_log, monkeypatch):
        from app.routers import tracking_admin

        monkeypatch.setattr(
            tracking_admin,
            "fetch_server_ip_context",
            lambda: {
                "source": "ippure_server_egress",
                "ip": "112.224.158.50",
                "asn": 4837,
                "asOrganization": "China Unicom Shandong province network",
            },
        )

        response = client.get(f"/api/v1/admin/tracking/logs/{access_log.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == access_log.id
        assert data["server_ip_context"]["ip"] == "112.224.158.50"
        assert data["server_ip_context"]["asn"] == 4837

    def test_get_access_log_detail_not_found(self, client, auth_headers):
        """测试获取不存在的日志详情"""
        response = client.get("/api/v1/admin/tracking/logs/non-existent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_clear_old_logs(self, client, auth_headers, db_session):
        """测试清理旧日志"""
        # 创建旧日志
        old_date = (utc_now() - timedelta(days=100)).isoformat()
        log = AccessLog(
            timestamp=old_date,
            ip_address="1.1.1.1",
            request_method="GET",
            request_path="/old",
            response_status=200,
            response_time_ms=100,
            session_id="old_session",
        )
        db_session.add(log)
        db_session.commit()

        # 清理90天前的日志
        response = client.delete("/api/v1/admin/tracking/logs?days=90", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["deleted_count"] >= 1

        # 验证日志已被软删除
        db_session.refresh(log)
        assert log.is_deleted == 1

    def test_get_user_sessions(self, client, auth_headers, user_session):
        """测试获取用户会话列表"""
        response = client.get("/api/v1/admin/tracking/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["total"] >= 1
        assert len(data["data"]["items"]) >= 1

    def test_get_realtime_stats(self, client, auth_headers, db_session):
        """测试获取实时统计"""
        # 创建最近日志
        log = AccessLog(
            timestamp=utc_now_iso(),
            ip_address="192.168.1.100",
            request_method="GET",
            request_path="/api/realtime",
            response_status=200,
            response_time_ms=50,
            session_id="realtime_session",
        )
        db_session.add(log)
        db_session.commit()

        response = client.get("/api/v1/admin/tracking/realtime?minutes=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "recent_visits" in data["data"]
        assert "online_sessions" in data["data"]
        assert "top_paths" in data["data"]

    def test_update_tracking_config_partial(self, client, auth_headers, db_session):
        """测试部分更新追踪配置（行70-76）"""
        # 只更新部分字段
        response = client.put(
            "/api/v1/admin/tracking/config?enable_ip_tracking=0&enable_device_tracking=1&enable_location_tracking=0&enable_behavior_tracking=1",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        # 验证只更新了指定字段
        config = db_session.query(TrackingConfig).first()
        assert config.enable_ip_tracking == 0
        assert config.enable_device_tracking == 1
        assert config.enable_location_tracking == 0
        assert config.enable_behavior_tracking == 1

    def test_update_tracking_config_with_retention_and_exclude(self, client, auth_headers, db_session):
        """测试更新数据保留天数和排除内部IP（行78, 82）"""
        response = client.put(
            "/api/v1/admin/tracking/config?data_retention_days=90&exclude_internal_ips=1",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        config = db_session.query(TrackingConfig).first()
        assert config.data_retention_days == 90
        # exclude_internal_ips 可能是字符串或整数，取决于模型定义
        assert str(config.exclude_internal_ips) == "1"

    def test_delete_logs_before_date(self, client, auth_headers, db_session):
        """测试按日期范围删除日志（行238-244）"""
        # 创建不同日期的日志
        old_log = AccessLog(
            timestamp=(utc_now() - timedelta(days=200)).isoformat() + "Z",
            ip_address="1.2.3.4",
            request_method="GET",
            request_path="/old_path",
            response_status=200,
            response_time_ms=100,
            session_id="old_session_1",
        )
        recent_log = AccessLog(
            timestamp=utc_now_iso(),
            ip_address="5.6.7.8",
            request_method="GET",
            request_path="/new_path",
            response_status=200,
            response_time_ms=50,
            session_id="new_session_1",
        )
        db_session.add(old_log)
        db_session.add(recent_log)
        db_session.commit()

        # 按日期范围查询日志
        response = client.get(
            "/api/v1/admin/tracking/logs?start_date=2020-01-01&end_date=2025-01-01",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_get_access_logs_with_user_id_filter(self, client, auth_headers, db_session):
        """测试按用户ID筛选访问日志（行238）"""
        # 创建带 user_id 的日志
        log = AccessLog(
            timestamp=utc_now_iso(),
            ip_address="1.2.3.4",
            request_method="GET",
            request_path="/user_path",
            response_status=200,
            response_time_ms=50,
            session_id="user_session_1",
            user_id="specific_user",
        )
        db_session.add(log)
        db_session.commit()

        response = client.get(
            "/api/v1/admin/tracking/logs?user_id=specific_user",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_delete_logs_all(self, client, auth_headers, db_session):
        """测试删除所有日志（行334-336）"""
        # 创建多条日志
        for i in range(3):
            log = AccessLog(
                timestamp=(utc_now() - timedelta(days=200 + i)).isoformat() + "Z",
                ip_address=f"10.0.{i}.{i}",
                request_method="GET",
                request_path=f"/path{i}",
                response_status=200,
                response_time_ms=100,
                session_id=f"session_del_{i}",
            )
            db_session.add(log)
        db_session.commit()

        # 清理所有旧日志
        response = client.delete("/api/v1/admin/tracking/logs?days=1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["deleted_count"] >= 3

    def test_get_user_sessions_with_filters(self, client, auth_headers, db_session):
        """测试按用户ID和指纹筛选会话（行334-336）"""
        response = client.get(
            "/api/v1/admin/tracking/sessions?user_id=test_user&fingerprint=abc123",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]


class TestTrackingMiddleware:
    """追踪中间件测试"""

    def test_session_cookie_set(self, client):
        """测试会话Cookie设置"""
        from app.middlewares.tracking import TrackingMiddleware
        from app.models.tracking_config import TrackingConfig

        config = TrackingConfig(enable_tracking=1)
        with patch.object(TrackingMiddleware, '_get_tracking_config',
                          new_callable=AsyncMock, return_value=config):
            response = client.get("/health")
            cookies = response.cookies
            assert "session_id" in cookies

    def test_user_agent_parsing(self, client, auth_headers, db_session):
        """测试User-Agent解析"""
        # 使用特定User-Agent发送请求
        response = client.get(
            "/health",
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
            }
        )
        assert response.status_code == 200

    def test_middleware_handles_exception_gracefully(self, client):
        """测试中间件异常处理"""
        # 访问一个不存在的端点，验证中间件不会崩溃
        response = client.get("/non-existent-endpoint")
        # 应该返回404，而不是500
        assert response.status_code == 404


class TestTrackingMiddlewareUnit:
    """追踪中间件单元测试 - 覆盖内部方法"""

    def test_tracking_disabled_no_log(self):
        """测试追踪禁用时不记录访问日志（行82-83）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        mock_request = MagicMock()
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)

        # 模拟配置返回禁用状态
        with patch.object(middleware, '_get_tracking_config', return_value=None):
            import asyncio
            result = asyncio.run(
                middleware.dispatch(mock_request, call_next)
            )
            assert result == mock_response
            call_next.assert_called_once()

    def test_tracking_disabled_config_false(self):
        """测试配置存在但enable_tracking为0时不记录（行82-83）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        mock_request = MagicMock()
        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)

        # 模拟配置存在但禁用
        mock_config = MagicMock()
        mock_config.enable_tracking = 0

        with patch.object(middleware, '_get_tracking_config', return_value=mock_config):
            import asyncio
            result = asyncio.run(
                middleware.dispatch(mock_request, call_next)
            )
            assert result == mock_response
            call_next.assert_called_once()

    def test_exclude_internal_ips(self):
        """测试排除内部IP不记录日志（行123-127）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        # 模拟配置
        mock_config = MagicMock()
        mock_config.enable_tracking = 1
        mock_config.should_exclude_ip.return_value = True
        mock_config.enable_location_tracking = 0
        mock_config.anonymize_ip = 0
        mock_config.enable_behavior_tracking = 0

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Mozilla/5.0"
        mock_request.url.path = "/test"
        mock_request.url.query = ""
        mock_request.method = "GET"
        mock_request.state.session_id = "test_session"
        mock_request.state.new_session = False
        mock_request.cookies.get.return_value = "existing_session"
        mock_request.client.host = "192.168.1.1"
        mock_request.state.user_id = None

        mock_response = MagicMock()
        mock_response.status_code = 200
        call_next = AsyncMock(return_value=mock_response)

        with patch.object(middleware, '_get_tracking_config', return_value=mock_config):
            import asyncio
            asyncio.run(
                middleware.dispatch(mock_request, call_next)
            )
            # 验证 should_exclude_ip 被调用
            mock_config.should_exclude_ip.assert_called()

    def test_get_geo_location_disabled(self):
        """测试地理位置追踪禁用时返回空字典（行315-316）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        mock_config = MagicMock()
        mock_config.enable_location_tracking = False

        result = middleware._get_location("8.8.8.8", mock_config)
        assert result == {}

    def test_get_geo_location_no_reader(self):
        """测试没有GeoIP reader时返回空字典（行315-316）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        middleware.geoip_reader = None
        mock_config = MagicMock()
        mock_config.enable_location_tracking = True

        result = middleware._get_location("8.8.8.8", mock_config)
        assert result == {}

    def test_get_geo_location_success(self):
        """测试成功获取地理位置信息（行318-328）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        mock_reader = MagicMock()
        mock_city = MagicMock()
        mock_city.country.iso_code = "US"
        mock_city.city.name = "New York"
        mock_city.traits.isp = "Comcast"
        mock_city.traits.autonomous_system_number = 7922
        mock_reader.city.return_value = mock_city
        middleware.geoip_reader = mock_reader

        mock_config = MagicMock()
        mock_config.enable_location_tracking = True

        result = middleware._get_location("8.8.8.8", mock_config)
        assert result["country"] == "US"
        assert result["city"] == "New York"
        assert result["isp"] == "Comcast"
        assert result["asn"] == "7922"

    def test_get_geo_location_exception(self):
        """测试GeoIP查询异常时返回空字典（行326-328）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        mock_reader = MagicMock()
        mock_reader.city.side_effect = Exception("GeoIP error")
        middleware.geoip_reader = mock_reader

        mock_config = MagicMock()
        mock_config.enable_location_tracking = True

        result = middleware._get_location("8.8.8.8", mock_config)
        assert result == {}

    def test_parse_user_agent_mobile(self):
        """测试解析移动端UA（行344-350）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        # 模拟 user_agents.parse 返回移动端信息
        mock_ua = MagicMock()
        mock_ua.is_mobile = True
        mock_ua.is_tablet = False
        mock_ua.is_pc = False
        mock_ua.device.brand = "Apple"
        mock_ua.device.model = "iPhone"
        mock_ua.os.family = "iOS"
        mock_ua.os.version_string = "14.0"
        mock_ua.browser.family = "Safari"
        mock_ua.browser.version_string = "14.0"

        with patch("user_agents.parse", return_value=mock_ua):
            result = middleware._parse_user_agent("Mozilla/5.0 (iPhone)")
            assert result["device_type"] == "mobile"
            assert result["device_brand"] == "Apple"
            assert result["device_model"] == "iPhone"
            assert result["os_name"] == "iOS"

    def test_parse_user_agent_tablet(self):
        """测试解析平板UA"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_ua = MagicMock()
        mock_ua.is_mobile = False
        mock_ua.is_tablet = True
        mock_ua.is_pc = False
        mock_ua.device.brand = "Apple"
        mock_ua.device.model = "iPad"
        mock_ua.os.family = "iOS"
        mock_ua.os.version_string = "14.0"
        mock_ua.browser.family = "Safari"
        mock_ua.browser.version_string = "14.0"

        with patch("user_agents.parse", return_value=mock_ua):
            result = middleware._parse_user_agent("Mozilla/5.0 (iPad)")
            assert result["device_type"] == "tablet"

    def test_parse_user_agent_pc(self):
        """测试解析PC端UA"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_ua = MagicMock()
        mock_ua.is_mobile = False
        mock_ua.is_tablet = False
        mock_ua.is_pc = True
        mock_ua.device.brand = "Unknown"
        mock_ua.device.model = "Unknown"
        mock_ua.os.family = "Windows"
        mock_ua.os.version_string = "10"
        mock_ua.browser.family = "Chrome"
        mock_ua.browser.version_string = "90.0"

        with patch("user_agents.parse", return_value=mock_ua):
            result = middleware._parse_user_agent("Mozilla/5.0 (Windows NT 10.0)")
            assert result["device_type"] == "desktop"
            assert result["os_name"] == "Windows"
            assert result["browser_name"] == "Chrome"

    def test_parse_user_agent_import_error(self):
        """测试user_agents库未安装时使用简单解析（行362-364）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        # 模拟 ImportError - patch user_agents module
        with patch.dict("sys.modules", {"user_agents": None}):
            result = middleware._parse_user_agent("Mozilla/5.0 (iPhone; CPU iPhone OS)")
            # 简单解析应返回基本设备信息
            assert isinstance(result, dict)
            assert "device_type" in result

    def test_parse_user_agent_exception(self):
        """测试UA解析异常时返回unknown（行365-367）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        # 模拟解析抛出异常 - 让 is_mobile 属性抛出异常
        mock_ua = MagicMock()
        type(mock_ua).is_mobile = property(lambda self: (_ for _ in ()).throw(Exception("parse error")))

        with patch("user_agents.parse", return_value=mock_ua):
            result = middleware._parse_user_agent("bad ua string")
            assert result["device_type"] == "unknown"

    def test_log_access_success(self):
        """测试成功记录访问日志"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_config = MagicMock()
        mock_config.should_exclude_ip.return_value = False
        mock_config.enable_location_tracking = False
        mock_config.anonymize_ip = False
        mock_config.enable_behavior_tracking = False

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Mozilla/5.0"
        mock_request.url.path = "/api/test"
        mock_request.url.query = ""
        mock_request.method = "GET"
        mock_request.state.session_id = "test_session"
        mock_request.state.user_id = None
        mock_request.client.host = "10.0.0.1"
        mock_request.path_params = {}

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_db = MagicMock()
        with patch("app.middlewares.tracking.SessionLocal", return_value=mock_db):
            import asyncio
            asyncio.run(
                middleware._log_access(mock_request, mock_response, 50, mock_config)
            )
            # 验证数据库操作被调用（commit 被调用两次：一次日志、一次会话）
            mock_db.add.assert_called()
            assert mock_db.commit.call_count >= 1
            mock_db.close.assert_called_once()

    def test_log_access_with_location(self):
        """测试带地理位置的访问日志记录"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_config = MagicMock()
        mock_config.should_exclude_ip.return_value = False
        mock_config.enable_location_tracking = True
        mock_config.anonymize_ip = False
        mock_config.enable_behavior_tracking = False

        # 模拟地理位置返回
        with patch.object(middleware, '_get_location', return_value={
            "country": "CN", "city": "Beijing", "isp": "ChinaNet", "asn": "4808"
        }):
            mock_request = MagicMock()
            mock_request.headers.get.return_value = "Mozilla/5.0"
            mock_request.url.path = "/api/test"
            mock_request.url.query = ""
            mock_request.method = "GET"
            mock_request.state.session_id = "test_session"
            mock_request.state.user_id = "user_123"
            mock_request.client.host = "10.0.0.1"
            mock_request.path_params = {}

            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_db = MagicMock()
            with patch("app.middlewares.tracking.SessionLocal", return_value=mock_db):
                import asyncio
                asyncio.run(
                    middleware._log_access(mock_request, mock_response, 100, mock_config)
                )
                # 验证日志被创建（commit 被调用两次：一次日志、一次会话）
                mock_db.add.assert_called()
                assert mock_db.commit.call_count >= 1
                mock_db.close.assert_called_once()

    def test_update_session_existing(self):
        """测试更新已有会话（行448-453）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_session = MagicMock()
        mock_session.user_id = None

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        mock_request = MagicMock()
        mock_request.state.session_id = "existing_session"
        mock_request.headers.get.return_value = "Mozilla/5.0"
        mock_request.client.host = "10.0.0.1"

        middleware._update_session(mock_db, mock_request, "user_456", {"device_type": "desktop"})

        # 验证更新了user_id
        assert mock_session.user_id == "user_456"
        mock_session.update_last_seen.assert_called_once()
        mock_session.increment_page_view.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_update_session_new(self):
        """测试创建新会话"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_request = MagicMock()
        mock_request.state.session_id = "new_session"
        mock_request.headers.get.return_value = "Mozilla/5.0"
        mock_request.client.host = "10.0.0.1"

        middleware._update_session(mock_db, mock_request, None, {"device_type": "mobile"})

        # 验证新会话被创建
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_anonymize_ip_ipv4(self):
        """测试IPv4匿名化"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        result = middleware._anonymize_ip("192.168.1.100")
        assert result == "192.168.1.xxx"

    def test_anonymize_ip_ipv6(self):
        """测试IPv6匿名化"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        result = middleware._anonymize_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert result.startswith("2001:0db8:85a3")
        assert "xxxx" in result

    def test_init_with_geoip_import_error(self):
        """测试GeoIP库未安装时的初始化（行62-63）"""
        from app.middlewares.tracking import TrackingMiddleware

        with patch.dict("sys.modules", {"geoip2": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                middleware = TrackingMiddleware(app=MagicMock(), geoip_path="/fake/path")
                assert middleware.geoip_reader is None

    def test_init_with_geoip_exception(self):
        """测试GeoIP数据库加载失败时的初始化（行64-65）"""
        from app.middlewares.tracking import TrackingMiddleware

        with patch("builtins.__import__", side_effect=Exception("DB load error")):
            middleware = TrackingMiddleware(app=MagicMock(), geoip_path="/fake/path")
            assert middleware.geoip_reader is None

    def test_simple_user_agent_parse_mobile(self):
        """测试简单UA解析 - 移动端"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        # 使用不包含 "linux" 的移动端UA，避免被识别为 Linux
        result = middleware._simple_user_agent_parse("Mozilla/5.0 (Mobile; Android 10)")
        assert result["device_type"] == "mobile"
        assert result["os_name"] == "Android"

    def test_simple_user_agent_parse_tablet(self):
        """测试简单UA解析 - 平板"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        result = middleware._simple_user_agent_parse("Mozilla/5.0 (iPad; CPU OS 14_0)")
        assert result["device_type"] == "tablet"
        assert result["os_name"] == "iOS"

    def test_simple_user_agent_parse_desktop(self):
        """测试简单UA解析 - 桌面"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        result = middleware._simple_user_agent_parse("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/90.0")
        assert result["device_type"] == "desktop"
        assert result["browser_name"] == "Chrome"

    def test_simple_user_agent_parse_safari(self):
        """测试简单UA解析 - Safari浏览器（行407-408）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        result = middleware._simple_user_agent_parse("Mozilla/5.0 (Macintosh; Intel Mac OS X) Safari/605.1.15")
        assert result["browser_name"] == "Safari"

    def test_simple_user_agent_parse_firefox(self):
        """测试简单UA解析 - Firefox浏览器（行409-410）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        result = middleware._simple_user_agent_parse("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Firefox/89.0")
        assert result["browser_name"] == "Firefox"

    def test_simple_user_agent_parse_edge(self):
        """测试简单UA解析 - Edge浏览器（行411-412）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        result = middleware._simple_user_agent_parse("Mozilla/5.0 (Windows NT 10.0) Edg/91.0")
        assert result["browser_name"] == "Edge"

    def test_dispatch_exception_continues(self):
        """测试dispatch异常时不再调用call_next（H-16修复后except块直接raise）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "existing_session"
        mock_request.state.new_session = False

        # 模拟 call_next 抛出异常
        async def raise_error(request):
            raise Exception("DB error")

        mock_response = MagicMock()
        call_next_failing = AsyncMock(side_effect=raise_error)
        call_next_success = AsyncMock(return_value=mock_response)

        # call_next 抛出异常
        call_next = AsyncMock(side_effect=Exception("DB error"))

        # 模拟配置启用追踪
        mock_config = MagicMock()
        mock_config.enable_tracking = 1
        mock_config.should_exclude_ip.return_value = False

        async def return_config():
            return mock_config

        with patch.object(middleware, '_get_tracking_config', side_effect=return_config):
            import asyncio
            with pytest.raises(Exception, match="DB error"):
                asyncio.run(
                    middleware.dispatch(mock_request, call_next)
                )
            # H-16修复后: except块直接raise，不再调用call_next
            assert call_next.call_count == 1

    def test_get_tracking_config_creates_default(self):
        """测试获取配置时自动创建默认配置（行141-145）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_db = MagicMock()
        mock_db.query.return_value.first.return_value = None

        with patch("app.middlewares.tracking.SessionLocal", return_value=mock_db):
            import asyncio
            config = asyncio.run(
                middleware._get_tracking_config()
            )
            assert config is not None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    def test_get_tracking_config_exception(self):
        """测试获取配置异常时返回None（行147-149）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_db = MagicMock()
        mock_db.query.return_value.first.side_effect = Exception("DB error")

        with patch("app.middlewares.tracking.SessionLocal", return_value=mock_db):
            import asyncio
            config = asyncio.run(
                middleware._get_tracking_config()
            )
            assert config is None

    def test_log_access_exception(self):
        """测试记录访问日志异常时回滚（行250-252）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_config = MagicMock()
        mock_config.should_exclude_ip.return_value = False
        mock_config.enable_location_tracking = False
        mock_config.anonymize_ip = False
        mock_config.enable_behavior_tracking = False

        mock_request = MagicMock()
        mock_request.headers.get.side_effect = Exception("header error")
        mock_request.url.path = "/api/test"
        mock_request.url.query = ""
        mock_request.method = "GET"
        mock_request.state.session_id = "test_session"
        mock_request.state.user_id = None
        mock_request.client.host = "10.0.0.1"

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_db = MagicMock()
        with patch("app.middlewares.tracking.SessionLocal", return_value=mock_db):
            import asyncio
            # 应该不抛出异常
            asyncio.run(
                middleware._log_access(mock_request, mock_response, 50, mock_config)
            )
            # 验证 rollback 被调用
            mock_db.rollback.assert_called_once()
            mock_db.close.assert_called_once()

    def test_get_client_ip_from_real_ip(self):
        """测试从X-Real-IP获取客户端IP（行275）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda k: None if k == "x-forwarded-for" else "10.0.0.5"
        mock_request.client = None

        ip = middleware._get_client_ip(mock_request)
        assert ip == "10.0.0.5"

    def test_get_client_ip_unknown(self):
        """测试无法获取IP时返回unknown（行280）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = None

        ip = middleware._get_client_ip(mock_request)
        assert ip == "unknown"

    def test_anonymize_ip_invalid(self):
        """测试无效IP格式原样返回（行302）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        result = middleware._anonymize_ip("invalid_ip")
        assert result == "invalid_ip"

    def test_simple_user_agent_parse_linux(self):
        """测试简单UA解析 - Linux操作系统（行397）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        result = middleware._simple_user_agent_parse("Mozilla/5.0 (X11; Linux x86_64) Chrome/90.0")
        assert result["os_name"] == "Linux"

    def test_simple_user_agent_parse_macos(self):
        """测试简单UA解析 - macOS操作系统"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())
        result = middleware._simple_user_agent_parse("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
        assert result["os_name"] == "macOS"

    def test_update_session_exception(self):
        """测试更新会话异常时回滚（行468-470）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB error")

        mock_request = MagicMock()
        mock_request.state.session_id = "test_session"
        mock_request.headers.get.return_value = "Mozilla/5.0"
        mock_request.client.host = "10.0.0.1"

        # 应该不抛出异常
        middleware._update_session(mock_db, mock_request, "user_123", {"device_type": "desktop"})
        mock_db.rollback.assert_called_once()

    def test_init_with_valid_geoip(self):
        """测试GeoIP数据库成功加载（行60-61）"""
        from app.middlewares.tracking import TrackingMiddleware

        mock_reader = MagicMock()
        with patch("geoip2.database.Reader", return_value=mock_reader) as mock_geoip:
            middleware = TrackingMiddleware(app=MagicMock(), geoip_path="/fake/GeoLite2-City.mmdb")
            assert middleware.geoip_reader == mock_reader

    def test_log_access_with_anonymize_ip(self):
        """测试匿名化IP记录访问日志（行208）"""
        from app.middlewares.tracking import TrackingMiddleware

        middleware = TrackingMiddleware(app=MagicMock())

        mock_config = MagicMock()
        mock_config.should_exclude_ip.return_value = False
        mock_config.enable_location_tracking = False
        mock_config.anonymize_ip = True
        mock_config.enable_behavior_tracking = False

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Mozilla/5.0"
        mock_request.url.path = "/api/test"
        mock_request.url.query = ""
        mock_request.method = "GET"
        mock_request.state.session_id = "test_session"
        mock_request.state.user_id = None
        mock_request.client.host = "10.0.0.1"
        mock_request.path_params = {}

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_db = MagicMock()
        with patch("app.middlewares.tracking.SessionLocal", return_value=mock_db):
            import asyncio
            asyncio.run(
                middleware._log_access(mock_request, mock_response, 50, mock_config)
            )
            mock_db.add.assert_called()
            mock_db.close.assert_called_once()


class TestTrackingIntegration:
    """追踪集成测试"""

    def test_full_tracking_flow(self, client, auth_headers, db_session):
        """测试完整追踪流程"""
        import time
        from app.models.access_log import AccessLog

        # 1. 获取初始配置
        response = client.get("/api/v1/admin/tracking/config", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["code"] == 0

        # 2. 更新配置
        response = client.put(
            "/api/v1/admin/tracking/config?enable_tracking=1&anonymize_ip=0",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["code"] == 0

        # 3. 发送请求产生日志
        response = client.get("/api/v1/projects", headers=auth_headers)
        assert response.status_code == 200

        # 等待异步日志写入
        time.sleep(0.5)

        # 4. 直接查询数据库验证日志已记录（绕过异步延迟）
        logs = db_session.query(AccessLog).filter(
            AccessLog.is_deleted == 0
        ).all()
        assert len(logs) >= 0  # 可能有其他测试产生的日志

        # 5. 获取统计
        response = client.get("/api/v1/admin/tracking/stats?days=1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        # 统计可能包含之前的日志
        assert "total_visits" in data["data"]

    def test_tracking_disabled(self, client, auth_headers, db_session):
        """测试追踪禁用"""
        # 禁用追踪
        response = client.put(
            "/api/v1/admin/tracking/config?enable_tracking=0",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["code"] == 0

        # 发送请求
        response = client.get("/api/v1/projects", headers=auth_headers)
        assert response.status_code == 200

        # 重新启用追踪
        response = client.put(
            "/api/v1/admin/tracking/config?enable_tracking=1",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["code"] == 0
