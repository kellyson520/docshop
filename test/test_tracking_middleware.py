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


def test_parse_user_agent_normalizes_android_brand_and_model_on_real_path(monkeypatch):
    install_fake_user_agents(monkeypatch)
    middleware = TrackingMiddleware(app=None)

    parsed = middleware._parse_user_agent(SAMPLE_ANDROID_UA)

    assert parsed["device_type"] == "mobile"
    assert parsed["device_brand"] == "Xiaomi"
    assert parsed["device_model"] == "Xiaomi 14"
    assert parsed["os_name"] == "Android"


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
