
import pytest
from types import SimpleNamespace


class FakeRequest:
    def __init__(self, body=None, cookies=None, headers=None, client_host="127.0.0.1"):
        self._body = body or {}
        self.cookies = cookies or {}
        self.headers = headers or {}
        self.client = SimpleNamespace(host=client_host)

    async def json(self):
        return self._body


class Query:
    def __init__(self, result):
        self.result = result
    def filter(self, *args, **kwargs):
        return self
    def order_by(self, *args, **kwargs):
        return self
    def limit(self, *args, **kwargs):
        return self
    def first(self):
        if isinstance(self.result, list):
            return self.result[0] if self.result else None
        return self.result
    def all(self):
        return self.result if isinstance(self.result, list) else ([self.result] if self.result is not None else [])


class FakeDB:
    def __init__(self, config=None, log=None, session=None):
        self.config = config
        self.log = log
        self.session = session
        self.added = []
        self.committed = False
        self.closed = False
    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "TrackingConfig":
            return Query(self.config)
        if name == "AccessLog":
            return Query(self.log)
        if name == "UserSession":
            return Query(self.session)
        return Query(None)
    def add(self, obj):
        self.added.append(obj)
    def commit(self):
        self.committed = True
    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_receive_ping_updates_latest_access_log(monkeypatch):
    from app.routers import tracking_ping

    log = SimpleNamespace(raw_data=None)
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=log)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    response = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-1",
        "device_id": "visitor-1",
        "screen_resolution": "1920x1080",
        "geo_latitude": 39.9042,
        "geo_longitude": 116.4074,
        "geo_accuracy": 8.5,
        "client_timezone": "Asia/Shanghai",
        "client_language": "zh-CN",
        "hardware_concurrency": 8,
    }))

    assert response.status_code == 204
    assert log.visitor_id == "visitor-1"
    assert log.screen_resolution == "1920x1080"
    assert log.geo_latitude == 39.9042
    assert log.geo_longitude == 116.4074
    assert log.geo_accuracy == 8.5
    assert log.client_timezone == "Asia/Shanghai"
    assert log.client_language == "zh-CN"
    assert "hardware_concurrency" in log.raw_data
    assert db.committed is True
    assert db.closed is True


@pytest.mark.asyncio
async def test_receive_ping_without_page_path_updates_session_context_only(monkeypatch):
    from app.routers import tracking_ping

    log = SimpleNamespace(raw_data=None)
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=log)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    response = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-init",
        "device_id": "visitor-init",
        "client_language": "zh-CN",
    }))

    assert response.status_code == 204
    assert log.visitor_id == "visitor-init"
    assert log.client_language == "zh-CN"
    assert db.added == []
    assert db.committed is True
    assert db.closed is True


@pytest.mark.asyncio
async def test_receive_ping_anonymizes_coordinates_when_config_enabled(monkeypatch):
    from app.routers import tracking_ping

    log = SimpleNamespace(raw_data=None)
    config = SimpleNamespace(anonymize_ip=1)
    db = FakeDB(config=config, log=log)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-2",
        "geo_latitude": 39.9042123,
        "geo_longitude": 116.4074567,
        "geo_accuracy": 8.5,
    }))

    assert log.geo_latitude == 39.904
    assert log.geo_longitude == 116.407
    assert log.geo_accuracy == 111.0


@pytest.mark.asyncio
async def test_receive_ping_stores_pending_beacon_when_log_missing(monkeypatch):
    from app.routers import tracking_ping

    session = SimpleNamespace(raw_data=None)
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=None, session=session)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    response = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-3",
        "client_timezone": "Asia/Shanghai",
    }))

    assert response.status_code == 204
    assert "pending_beacon" in session.raw_data
    assert "Asia/Shanghai" in session.raw_data
    assert db.committed is True


@pytest.mark.asyncio
async def test_receive_ping_creates_page_view_log_when_page_path_is_provided(monkeypatch):
    from app.routers import tracking_ping

    api_log = SimpleNamespace(
        raw_data=None,
        session_id="session-page",
        visitor_id="visitor-page",
        request_path="/api/v1/tracking/config",
        is_page_view=0,
        user_id=None,
        ip_address="203.0.113.10",
        ip_country=None,
        ip_city=None,
        ip_isp=None,
        ip_asn=None,
        user_agent="pytest-agent",
        device_type="desktop",
        device_brand="Microsoft",
        device_model="PC",
        os_name="Windows",
        os_version="11",
        browser_name="Edge",
        browser_version="149",
    )
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=api_log)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    response = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-page",
        "device_id": "visitor-page",
        "page_path": "/admin/tracking",
        "client_timezone": "Asia/Shanghai",
    }))

    assert response.status_code == 204
    assert len(db.added) == 1
    page_view_log = db.added[0]
    assert page_view_log.session_id == "session-page"
    assert page_view_log.visitor_id == "visitor-page"
    assert page_view_log.request_path == "/admin/tracking"
    assert page_view_log.is_page_view == 1
    assert page_view_log.client_timezone == "Asia/Shanghai"
    assert db.committed is True


@pytest.mark.asyncio
async def test_receive_ping_creates_page_view_log_with_request_device_context_when_source_log_missing(monkeypatch):
    from app.routers import tracking_ping

    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=None, session=None)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    response = await tracking_ping.receive_ping(FakeRequest(
        {
            "session_id": "session-fallback",
            "device_id": "visitor-fallback",
            "page_path": "/s/demo",
            "screen_resolution": "393x873",
            "client_timezone": "Asia/Shanghai",
            "client_language": "zh-CN",
        },
        headers={
            "user-agent": (
                "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36 EdgA/144.0.0.0"
            ),
            "sec-ch-ua": '"Microsoft Edge";v="144", "Chromium";v="144", "Not)A;Brand";v="99"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
        },
        client_host="198.51.100.25",
    ))

    assert response.status_code == 204
    assert len(db.added) == 1
    page_view_log = db.added[0]
    assert page_view_log.user_agent.startswith("Mozilla/5.0")
    assert page_view_log.device_type == "mobile"
    assert page_view_log.os_name == "Android"
    assert page_view_log.browser_name == "Edge"
    assert page_view_log.browser_version == "144"
    assert page_view_log.screen_resolution == "393x873"
    assert page_view_log.client_timezone == "Asia/Shanghai"
    assert page_view_log.client_language == "zh-CN"
    assert page_view_log.ip_address == "198.51.100.25"






@pytest.mark.asyncio
async def test_receive_ping_resolves_client_hint_device_model_for_page_view(monkeypatch):
    from app.routers import tracking_ping

    api_log = SimpleNamespace(
        raw_data=None,
        session_id="session-chrome",
        visitor_id="visitor-chrome",
        request_path="/api/v1/tracking/config",
        is_page_view=0,
        user_id=None,
        ip_address="203.0.113.10",
        ip_country=None,
        ip_city=None,
        ip_isp=None,
        ip_asn=None,
        user_agent="Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 Chrome/126.0.0.0 Mobile Safari/537.36",
        device_type="mobile",
        device_brand="K",
        device_model="K",
        os_name="Android",
        os_version="16",
        browser_name="Chrome",
        browser_version="126",
    )
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=api_log)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    monkeypatch.setattr(tracking_ping, "resolve_mobile_model_code", lambda code, cache_path=None: {
        "device_model_code": "V2243A",
        "device_model_name": "iQOO 11",
        "device_brand_name": "vivo",
        "device_display_name": "vivo iQOO 11 / V2243A",
    })
    tracking_ping._rate_limit_cache.clear()

    response = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-chrome",
        "device_id": "visitor-chrome",
        "page_path": "/s/demo",
        "device_model": "V2243A",
        "platform": "Android",
    }))

    assert response.status_code == 204
    assert len(db.added) == 1
    page_view_log = db.added[0]
    assert page_view_log.device_model == "V2243A"
    assert page_view_log.device_model_code == "V2243A"
    assert page_view_log.device_model_name == "iQOO 11"
    assert page_view_log.device_display_name == "vivo iQOO 11 / V2243A"

@pytest.mark.asyncio
async def test_receive_ping_page_view_log_preserves_resolved_mobile_model_fields(monkeypatch):
    from app.routers import tracking_ping

    api_log = SimpleNamespace(
        raw_data=None,
        session_id="session-mobile",
        visitor_id="visitor-mobile",
        request_path="/api/v1/share/demo",
        is_page_view=0,
        user_id=None,
        ip_address="203.0.113.10",
        ip_country=None,
        ip_city=None,
        ip_isp=None,
        ip_asn=None,
        user_agent="Mozilla/5.0 (Linux; Android 16; V2243A Build/BP2A.250605.031.A3; wv) Mobile",
        device_type="mobile",
        device_brand="V2243A",
        device_model="V2243A",
        device_model_code="V2243A",
        device_model_name="iQOO 11",
        device_brand_name="vivo",
        device_display_name="vivo iQOO 11 / V2243A",
        os_name="Android",
        os_version="16",
        browser_name="Chrome",
        browser_version="116",
    )
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=api_log)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    response = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-mobile",
        "device_id": "visitor-mobile",
        "page_path": "/s/demo",
    }))

    assert response.status_code == 204
    assert len(db.added) == 1
    page_view_log = db.added[0]
    assert page_view_log.device_model_code == "V2243A"
    assert page_view_log.device_model_name == "iQOO 11"
    assert page_view_log.device_brand_name == "vivo"
    assert page_view_log.device_display_name == "vivo iQOO 11 / V2243A"


@pytest.mark.asyncio
async def test_receive_ping_page_view_log_inherits_environment_and_geo_from_source_log(monkeypatch):
    from app.routers import tracking_ping

    api_log = SimpleNamespace(
        raw_data=None,
        session_id="session-env",
        visitor_id="visitor-env",
        request_path="/api/v1/tracking/config",
        is_page_view=0,
        user_id=None,
        ip_address="203.0.113.10",
        ip_country="CN",
        ip_city="Beijing",
        ip_isp="Example ISP",
        ip_asn="64500",
        user_agent="pytest-agent",
        device_type="desktop",
        device_brand="Microsoft",
        device_model="PC",
        os_name="Windows",
        os_version="11",
        browser_name="Edge",
        browser_version="149",
        geo_latitude=39.9042,
        geo_longitude=116.4074,
        geo_accuracy=18.0,
        client_timezone="Asia/Shanghai",
        client_language="zh-CN",
    )
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=api_log)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    response = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-env",
        "device_id": "visitor-env",
        "page_path": "/admin/tracking",
    }))

    assert response.status_code == 204
    assert len(db.added) == 1
    page_view_log = db.added[0]
    assert page_view_log.geo_latitude == 39.9042
    assert page_view_log.geo_longitude == 116.4074
    assert page_view_log.geo_accuracy == 18.0
    assert page_view_log.client_timezone == "Asia/Shanghai"
    assert page_view_log.client_language == "zh-CN"

@pytest.mark.asyncio
async def test_receive_ping_rate_limits_by_session(monkeypatch):
    from fastapi import HTTPException
    from app.routers import tracking_ping

    log = SimpleNamespace(raw_data=None)
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=log)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    await tracking_ping.receive_ping(FakeRequest({"session_id": "session-rate", "client_language": "zh-CN"}))

    with pytest.raises(HTTPException) as exc:
        await tracking_ping.receive_ping(FakeRequest({"session_id": "session-rate", "client_language": "en-US"}))

    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_receive_ping_allows_distinct_page_paths_with_same_session(monkeypatch):
    from app.routers import tracking_ping

    log = SimpleNamespace(raw_data=None)
    config = SimpleNamespace(anonymize_ip=0)
    db = FakeDB(config=config, log=log)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    first = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-pages",
        "device_id": "visitor-pages",
        "page_path": "/admin/dashboard",
    }))
    second = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-pages",
        "device_id": "visitor-pages",
        "page_path": "/admin/tracking",
    }))

    assert first.status_code == 204
    assert second.status_code == 204
    assert len(db.added) == 2
    assert db.added[0].request_path == "/admin/dashboard"
    assert db.added[1].request_path == "/admin/tracking"


@pytest.mark.asyncio
async def test_receive_ping_requires_session_or_device():
    from fastapi import HTTPException
    from app.routers import tracking_ping

    with pytest.raises(HTTPException) as exc:
        await tracking_ping.receive_ping(FakeRequest({"client_language": "zh-CN"}))

    assert exc.value.status_code == 400



def test_public_tracking_config_exposes_safe_switches_and_runtime_identifiers(monkeypatch):
    from app.routers import tracking_ping

    config = SimpleNamespace(
        enable_tracking=1,
        enable_device_tracking=1,
        enable_location_tracking=0,
        anonymize_ip=1,
        exclude_internal_ips="10.0.0.1",
    )
    db = FakeDB(config=config)
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    request = SimpleNamespace(
        state=SimpleNamespace(device_id="device-1", session_id="session-1"),
        cookies={},
    )

    response = tracking_ping.get_public_tracking_config(request)
    data = response.data

    assert data == {
        "enable_tracking": True,
        "enable_device_tracking": True,
        "enable_location_tracking": False,
        "anonymize_ip": True,
        "device_id": "device-1",
        "session_id": "session-1",
    }


def test_hardware_profile_match_handles_browser_viewport_scaling():
    from app.routers.tracking_ping import _hardware_profiles_match

    wechat_profile = {
        "screen_avail": "400x889",
        "screen_pixel_ratio": 2.700000047683716,
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "max_touch_points": 5,
    }
    edge_profile = {
        "screen_avail": "360x800",
        "screen_pixel_ratio": 3,
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "max_touch_points": 5,
    }

    assert _hardware_profiles_match(wechat_profile, edge_profile) is True


def test_hardware_profile_match_rejects_different_physical_screen():
    from app.routers.tracking_ping import _hardware_profiles_match

    known_profile = {
        "screen_avail": "400x889",
        "screen_pixel_ratio": 2.700000047683716,
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "max_touch_points": 5,
    }
    other_profile = {
        "screen_avail": "393x873",
        "screen_pixel_ratio": 3,
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "max_touch_points": 5,
    }

    assert _hardware_profiles_match(known_profile, other_profile) is False


@pytest.mark.asyncio
async def test_receive_ping_backfills_k_model_from_unique_hardware_profile_match(monkeypatch):
    from app.routers import tracking_ping

    source_log = SimpleNamespace(
        raw_data=None,
        session_id="session-edge",
        visitor_id="visitor-edge",
        request_path="/api/v1/share/demo",
        is_page_view=0,
        user_id=None,
        ip_address="127.0.0.1",
        ip_country=None,
        ip_city=None,
        ip_isp=None,
        ip_asn=None,
        user_agent="Mozilla/5.0 (Linux; Android 10; K) Chrome/144.0.0.0 Mobile Safari/537.36 EdgA/144.0.0.0",
        device_type="mobile",
        device_brand="K",
        device_model="K",
        os_name="Android",
        os_version="10",
        browser_name="Edge",
        browser_version="144",
    )
    known_log = SimpleNamespace(
        raw_data=(
            '{"client_extra":{"screen_avail":"400x889","screen_pixel_ratio":2.700000047683716,'
            '"platform":"Linux armv81","hardware_concurrency":8,"max_touch_points":5}}'
        ),
        device_model_code="V2243A",
        device_model_name="iQOO 11",
        device_brand_name="vivo",
        device_display_name="vivo iQOO 11 / V2243A",
    )

    class ProfileDB(FakeDB):
        def query(self, model):
            name = getattr(model, "__name__", "")
            if name == "TrackingConfig":
                return Query(SimpleNamespace(anonymize_ip=0))
            if name == "AccessLog":
                return Query([source_log, known_log])
            return Query(None)

    db = ProfileDB()
    monkeypatch.setattr(tracking_ping, "SessionLocal", lambda: db)
    tracking_ping._rate_limit_cache.clear()

    response = await tracking_ping.receive_ping(FakeRequest({
        "session_id": "session-edge",
        "device_id": "visitor-edge",
        "page_path": "/s/demo",
        "screen_avail": "360x800",
        "screen_pixel_ratio": 3,
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "max_touch_points": 5,
    }))

    assert response.status_code == 204
    assert len(db.added) == 1
    page_view_log = db.added[0]
    assert page_view_log.device_model_code == "V2243A"
    assert page_view_log.device_model_name == "iQOO 11"
    assert page_view_log.device_display_name == "vivo iQOO 11 / V2243A"
    assert source_log.device_model_code == "V2243A"
    assert source_log.device_model_name == "iQOO 11"
    assert source_log.device_display_name == "vivo iQOO 11 / V2243A"

