import asyncio
import sys
from types import ModuleType, SimpleNamespace

import app.middlewares.tracking as tracking_module
from app.middlewares.tracking import TrackingMiddleware


SAMPLE_ANDROID_UA = (
    "Mozilla/5.0 (Linux; Android 14; Xiaomi 14 Build/UKQ1.230917.001; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.0.0 Mobile Safari/537.36"
)


class DummyDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class DummyConfig:
    enable_location_tracking = False
    enable_behavior_tracking = True
    anonymize_ip = False

    def should_exclude_ip(self, ip):
        return False


class CaptureAccessLog:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeParsedUA:
    is_mobile = True
    is_tablet = False
    is_pc = False
    device = SimpleNamespace(brand="xiaomi", model="xiaomi 14")
    os = SimpleNamespace(family="Android", version_string="14")
    browser = SimpleNamespace(family="Chrome Mobile WebView", version_string="124.0.0.0")


class FakeUserAgentsModule(ModuleType):
    def parse(self, user_agent):
        return FakeParsedUA()


def install_fake_user_agents(monkeypatch):
    monkeypatch.setitem(sys.modules, "user_agents", FakeUserAgentsModule("user_agents"))


def test_parse_client_hints_prefers_edge_on_windows():
    middleware = TrackingMiddleware(app=None)
    headers = {
        "sec-ch-ua": '"Microsoft Edge";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0"
        ),
    }

    hints = middleware._parse_client_hints(headers)

    assert hints["browser_name"] == "Edge"
    assert hints["browser_version"] == "149"
    assert hints["os_name"] == "Windows"
    assert hints["device_type"] == "desktop"


def test_parse_client_hints_does_not_use_user_agent_for_browser_classification():
    middleware = TrackingMiddleware(app=None)
    headers = {
        "sec-ch-ua": '"Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0"
        ),
    }

    hints = middleware._parse_client_hints(headers)

    assert hints["browser_name"] == "Chromium"
    assert hints["browser_version"] == "149"


def test_parse_referer_normalizes_external_domain():
    middleware = TrackingMiddleware(app=None)

    referer = middleware._parse_referer(
        "https://www.limestart.cn/",
        request_host="docshop.local",
    )

    assert referer["referer_host"] == "www.limestart.cn"
    assert referer["referer_domain"] == "limestart.cn"
    assert referer["referer_type"] == "external"


def test_parse_referer_classifies_direct_internal_and_unknown():
    middleware = TrackingMiddleware(app=None)

    direct = middleware._parse_referer(None, request_host="docshop.local")
    internal = middleware._parse_referer(
        "https://app.docshop.local/path",
        request_host="docshop.local",
    )
    unknown = middleware._parse_referer("not-a-url", request_host="docshop.local")

    assert direct["referer_type"] == "direct"
    assert internal["referer_type"] == "internal"
    assert internal["referer_host"] == "app.docshop.local"
    assert unknown["referer_type"] == "unknown"


def test_parse_referer_treats_sibling_subdomains_as_internal():
    middleware = TrackingMiddleware(app=None)

    referer = middleware._parse_referer(
        "https://www.docshop.local/path",
        request_host="app.docshop.local",
    )

    assert referer["referer_type"] == "internal"
    assert referer["referer_domain"] == "docshop.local"


def test_parse_referer_handles_multi_part_public_suffix_as_internal():
    middleware = TrackingMiddleware(app=None)

    referer = middleware._parse_referer(
        "https://www.docshop.co.uk/path",
        request_host="app.docshop.co.uk",
    )

    assert referer["referer_type"] == "internal"
    assert referer["referer_domain"] == "docshop.co.uk"


def test_parse_user_agent_normalizes_android_brand_and_model_on_real_path(monkeypatch):
    install_fake_user_agents(monkeypatch)
    middleware = TrackingMiddleware(app=None)

    parsed = middleware._parse_user_agent(SAMPLE_ANDROID_UA)

    assert parsed["device_type"] == "mobile"
    assert parsed["device_brand"] == "Xiaomi"
    assert parsed["device_model"] == "Xiaomi 14"
    assert parsed["os_name"] == "Android"


def test_merge_device_signals_prefers_client_hints_for_browser_platform_and_device_type():
    middleware = TrackingMiddleware(app=None)

    merged = middleware._merge_device_signals(
        {
            "browser_name": "Edge",
            "browser_version": "149",
            "os_name": "Windows",
            "device_type": "desktop",
        },
        {
            "browser_name": "Chrome",
            "browser_version": "124",
            "os_name": "Android",
            "os_version": "14",
            "device_type": "mobile",
            "device_brand": "Xiaomi",
            "device_model": "Xiaomi 14",
            "screen_resolution": None,
        },
    )

    assert merged["browser_name"] == "Edge"
    assert merged["browser_version"] == "149"
    assert merged["os_name"] == "Windows"
    assert merged["device_type"] == "desktop"
    assert merged["device_brand"] == "Xiaomi"
    assert merged["device_model"] == "Xiaomi 14"


def test_simple_user_agent_parse_cleans_android_model_noise():
    middleware = TrackingMiddleware(app=None)

    parsed = middleware._simple_user_agent_parse(SAMPLE_ANDROID_UA)

    assert parsed["device_type"] == "mobile"
    assert parsed["device_brand"] == "Xiaomi"
    assert parsed["device_model"] == "Xiaomi 14"
    assert parsed["os_name"] == "Android"


def test_log_access_merges_client_hints_with_real_user_agent_path_before_building_access_log(monkeypatch):
    install_fake_user_agents(monkeypatch)
    middleware = TrackingMiddleware(app=None)
    db = DummyDB()
    captured = {}

    monkeypatch.setattr(tracking_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(tracking_module, "AccessLog", CaptureAccessLog)
    monkeypatch.setattr(middleware, "_get_client_ip", lambda request: "203.0.113.10")
    monkeypatch.setattr(middleware, "_parse_client_hints", lambda headers: {
        "browser_name": "Edge",
        "browser_version": "149",
        "os_name": "Windows",
        "device_type": "desktop",
    })
    monkeypatch.setattr(middleware, "_extract_business_context", lambda request: {})

    def capture_update_session(db_session, request, user_id, device_info):
        captured["device_info"] = device_info

    monkeypatch.setattr(middleware, "_update_session", capture_update_session)

    request = SimpleNamespace(
        headers={
            "user-agent": SAMPLE_ANDROID_UA,
            "referer": "https://www.limestart.cn/",
        },
        url=SimpleNamespace(path="/docs", query="", hostname="docshop.local"),
        method="GET",
        state=SimpleNamespace(session_id="session-1", user_id=None, device_id="device-1", device_fingerprint="fp-1"),
        path_params={},
        client=SimpleNamespace(host="203.0.113.10"),
    )
    response = SimpleNamespace(status_code=200)

    asyncio.run(middleware._log_access(request, response, 12, DummyConfig()))

    assert db.committed is True
    assert len(db.added) == 1
    log_entry = db.added[0]
    assert log_entry.browser_name == "Edge"
    assert log_entry.browser_version == "149"
    assert log_entry.os_name == "Windows"
    assert log_entry.device_type == "desktop"
    assert log_entry.device_brand == "Xiaomi"
    assert log_entry.device_model == "Xiaomi 14"
    assert captured["device_info"]["browser_name"] == "Edge"
    assert captured["device_info"]["os_name"] == "Windows"
    assert captured["device_info"]["device_type"] == "desktop"
    assert captured["device_info"]["device_brand"] == "Xiaomi"
    assert captured["device_info"]["device_model"] == "Xiaomi 14"



def make_request(path="/docs", accept="text/html", method="GET"):
    return SimpleNamespace(
        headers={"accept": accept, "user-agent": SAMPLE_ANDROID_UA},
        url=SimpleNamespace(path=path, query="", hostname="docshop.local"),
        method=method,
        state=SimpleNamespace(session_id="session-1", user_id=None, device_id="visitor-1", device_fingerprint="fp-1"),
        path_params={},
        cookies={},
        client=SimpleNamespace(host="203.0.113.10"),
    )


def test_is_page_view_true_for_html_navigation():
    middleware = TrackingMiddleware(app=None)

    assert middleware._is_page_view(make_request("/admin/tracking", "text/html,application/xhtml+xml")) is True


def test_is_page_view_false_for_api_and_assets():
    middleware = TrackingMiddleware(app=None)

    assert middleware._is_page_view(make_request("/api/v1/projects", "application/json")) is False
    assert middleware._is_page_view(make_request("/assets/index.js", "*/*")) is False
    assert middleware._is_page_view(make_request("/favicon.ico", "image/x-icon")) is False


def test_should_skip_tracking_ping_path():
    middleware = TrackingMiddleware(app=None)

    assert middleware._should_skip_tracking(make_request("/api/v1/tracking/ping", "application/json", method="POST")) is True
    assert middleware._should_skip_tracking(make_request("/api/v1/projects", "application/json")) is False


def test_log_access_persists_visitor_id_and_page_view(monkeypatch):
    install_fake_user_agents(monkeypatch)
    middleware = TrackingMiddleware(app=None)
    db = DummyDB()

    monkeypatch.setattr(tracking_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(tracking_module, "AccessLog", CaptureAccessLog)
    monkeypatch.setattr(middleware, "_get_client_ip", lambda request: "203.0.113.10")
    monkeypatch.setattr(middleware, "_extract_business_context", lambda request: {})
    monkeypatch.setattr(middleware, "_update_session", lambda *args, **kwargs: None)

    request = make_request("/admin/tracking", "text/html")
    response = SimpleNamespace(status_code=200)

    asyncio.run(middleware._log_access(request, response, 15, DummyConfig()))

    assert len(db.added) == 1
    log_entry = db.added[0]
    assert log_entry.visitor_id == "visitor-1"
    assert log_entry.is_page_view == 1


def test_update_session_stores_visitor_id_and_only_counts_page_views(monkeypatch):
    middleware = TrackingMiddleware(app=None)
    created_sessions = []

    class Query:
        def filter(self, *args, **kwargs):
            return self
        def first(self):
            return None

    class SessionDB(DummyDB):
        def query(self, model):
            return Query()
        def add(self, obj):
            created_sessions.append(obj)
            super().add(obj)

    db = SessionDB()
    request = make_request("/api/v1/projects", "application/json")
    request.state.is_page_view = False

    middleware._update_session(db, request, None, {"device_type": "desktop"})

    assert created_sessions
    assert created_sessions[0].visitor_id == "visitor-1"
    assert created_sessions[0].page_view_count == 0


def test_log_access_stores_resolved_mobile_model_fields(monkeypatch):
    install_fake_user_agents(monkeypatch)
    middleware = TrackingMiddleware(app=None)
    db = DummyDB()

    monkeypatch.setattr(tracking_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(tracking_module, "AccessLog", CaptureAccessLog)
    monkeypatch.setattr(middleware, "_get_client_ip", lambda request: "203.0.113.10")
    monkeypatch.setattr(middleware, "_extract_business_context", lambda request: {})
    monkeypatch.setattr(middleware, "_update_session", lambda *args, **kwargs: None)
    monkeypatch.setattr(tracking_module, "resolve_mobile_model_from_user_agent", lambda ua, cache_path=None: {
        "device_model_code": "ANA-AL00",
        "device_model_name": "P40",
        "device_brand_name": "Huawei",
        "device_display_name": "Huawei P40 / ANA-AL00",
    }, raising=False)

    request = make_request("/docs", "text/html")
    request.headers["user-agent"] = "Mozilla/5.0 (Linux; Android 10; ANA-AL00 Build/HUAWEIANA-AL00) Mobile"

    asyncio.run(middleware._log_access(request, SimpleNamespace(status_code=200), 10, DummyConfig()))

    assert len(db.added) == 1
    log_entry = db.added[0]
    assert log_entry.device_model_code == "ANA-AL00"
    assert log_entry.device_model_name == "P40"
    assert log_entry.device_brand_name == "Huawei"
    assert log_entry.device_display_name == "Huawei P40 / ANA-AL00"


def test_log_access_calls_resolver_and_leaves_unknown_mobile_model_empty(monkeypatch):
    install_fake_user_agents(monkeypatch)
    middleware = TrackingMiddleware(app=None)
    db = DummyDB()
    calls = []

    monkeypatch.setattr(tracking_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(tracking_module, "AccessLog", CaptureAccessLog)
    monkeypatch.setattr(middleware, "_get_client_ip", lambda request: "203.0.113.10")
    monkeypatch.setattr(middleware, "_extract_business_context", lambda request: {})
    monkeypatch.setattr(middleware, "_update_session", lambda *args, **kwargs: None)
    monkeypatch.setattr(tracking_module, "resolve_mobile_model_from_user_agent", lambda ua, cache_path=None: calls.append(ua) or {}, raising=False)

    asyncio.run(middleware._log_access(make_request("/docs", "text/html"), SimpleNamespace(status_code=200), 10, DummyConfig()))

    assert calls
    log_entry = db.added[0]
    assert getattr(log_entry, "device_model_code", None) is None
    assert getattr(log_entry, "device_display_name", None) is None


def test_log_access_resolver_errors_do_not_prevent_access_log_creation(monkeypatch):
    install_fake_user_agents(monkeypatch)
    middleware = TrackingMiddleware(app=None)
    db = DummyDB()
    calls = []

    monkeypatch.setattr(tracking_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(tracking_module, "AccessLog", CaptureAccessLog)
    monkeypatch.setattr(middleware, "_get_client_ip", lambda request: "203.0.113.10")
    monkeypatch.setattr(middleware, "_extract_business_context", lambda request: {})
    monkeypatch.setattr(middleware, "_update_session", lambda *args, **kwargs: None)

    def broken_resolver(ua, cache_path=None):
        calls.append(ua)
        raise RuntimeError("cache broken")

    monkeypatch.setattr(tracking_module, "resolve_mobile_model_from_user_agent", broken_resolver, raising=False)

    asyncio.run(middleware._log_access(make_request("/docs", "text/html"), SimpleNamespace(status_code=200), 10, DummyConfig()))

    assert calls
    assert len(db.added) == 1
    assert db.committed is True


def test_mobile_model_cache_refresh_schedules_once_when_stale(monkeypatch):
    middleware = TrackingMiddleware(app=None)
    scheduled = []

    monkeypatch.setattr(tracking_module, "settings", SimpleNamespace(
        MOBILE_MODEL_SYNC_ENABLED=True,
        MOBILE_MODEL_SYNC_INTERVAL_HOURS=168,
        MOBILE_MODEL_CACHE_DIR="./data/cache",
    ))
    monkeypatch.setattr(tracking_module, "is_cache_stale", lambda meta_path, interval_hours: True, raising=False)

    async def fake_refresh(settings_obj):
        return {"updated": True, "row_count": 1, "error": None}

    def fake_create_logged_task(coro, *, name):
        scheduled.append((coro, name))
        return SimpleNamespace(done=lambda: False)

    monkeypatch.setattr(tracking_module, "refresh_mobile_model_cache_async", fake_refresh, raising=False)
    monkeypatch.setattr(tracking_module, "create_logged_task", fake_create_logged_task)

    middleware._maybe_schedule_mobile_model_cache_refresh()
    middleware._maybe_schedule_mobile_model_cache_refresh()

    assert len(scheduled) == 1
    assert scheduled[0][1] == "mobile-model-cache-refresh"
    scheduled[0][0].close()


def test_mobile_model_cache_refresh_skips_when_disabled(monkeypatch):
    middleware = TrackingMiddleware(app=None)
    scheduled = []

    monkeypatch.setattr(tracking_module, "settings", SimpleNamespace(
        MOBILE_MODEL_SYNC_ENABLED=False,
        MOBILE_MODEL_SYNC_INTERVAL_HOURS=168,
        MOBILE_MODEL_CACHE_DIR="./data/cache",
    ))
    monkeypatch.setattr(tracking_module, "is_cache_stale", lambda meta_path, interval_hours: True, raising=False)
    monkeypatch.setattr(tracking_module, "create_logged_task", lambda coro, *, name: scheduled.append((coro, name)))

    middleware._maybe_schedule_mobile_model_cache_refresh()

    assert scheduled == []

