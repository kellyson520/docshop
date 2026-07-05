from app.services import ippure_service


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status={self.status_code}")

    def json(self):
        return self._payload


def test_fetch_server_ip_context_normalizes_payload_and_populates_cache(monkeypatch):
    ippure_service.ippure_cache.delete(ippure_service.IPPURE_CACHE_KEY)

    def fake_get(url, timeout, headers):
        assert url == ippure_service.IPPURE_INFO_URL
        assert timeout == (1.0, 3.0)
        assert headers["User-Agent"] == "DocShopTracking/1.0"
        return DummyResponse(
            {
                "ip": "112.224.158.50",
                "asn": 4837,
                "asOrganization": "China Unicom Shandong province network",
                "country": "China",
                "countryCode": "CN",
                "region": "Shandong",
                "regionCode": "SD",
                "city": "Qingdao",
                "timezone": "Asia/Shanghai",
                "longitude": "120.38042",
                "latitude": "36.06488",
                "postalCode": "266000",
                "fraudScore": 0,
                "isResidential": True,
                "isBroadcast": False,
            }
        )

    monkeypatch.setattr(ippure_service.requests, "get", fake_get)

    payload = ippure_service.fetch_server_ip_context(force_refresh=True)

    assert payload == {
        "source": "ippure_server_egress",
        "ip": "112.224.158.50",
        "asn": 4837,
        "asOrganization": "China Unicom Shandong province network",
        "country": "China",
        "countryCode": "CN",
        "region": "Shandong",
        "regionCode": "SD",
        "city": "Qingdao",
        "timezone": "Asia/Shanghai",
        "longitude": "120.38042",
        "latitude": "36.06488",
        "postalCode": "266000",
        "fraudScore": 0,
        "isResidential": True,
        "isBroadcast": False,
    }
    assert ippure_service.ippure_cache.get(ippure_service.IPPURE_CACHE_KEY)["ip"] == "112.224.158.50"


def test_fetch_server_ip_context_returns_stale_cache_when_remote_fetch_fails(monkeypatch):
    stale_payload = {
        "source": "ippure_server_egress",
        "ip": "112.224.158.50",
        "asn": 4837,
        "asOrganization": "China Unicom Shandong province network",
        "country": "China",
        "countryCode": "CN",
        "region": "Shandong",
        "regionCode": "SD",
        "city": "Qingdao",
        "timezone": "Asia/Shanghai",
        "longitude": "120.38042",
        "latitude": "36.06488",
        "postalCode": "266000",
        "fraudScore": 0,
        "isResidential": True,
        "isBroadcast": False,
    }
    ippure_service.ippure_cache.set(ippure_service.IPPURE_CACHE_KEY, stale_payload, ttl=60)

    def fake_get(url, timeout, headers):
        raise RuntimeError("ippure unavailable")

    monkeypatch.setattr(ippure_service.requests, "get", fake_get)

    payload = ippure_service.fetch_server_ip_context(force_refresh=True)

    assert payload == stale_payload


def test_build_visitor_ip_context_uses_log_ip_and_location_fields():
    payload = ippure_service.build_visitor_ip_context(
        "112.224.158.50",
        {
            "country": "CN",
            "city": "Qingdao",
            "asn": "4837",
            "isp": "China Unicom Shandong province network",
        },
    )

    assert payload == {
        "source": "access_log_visitor_ip",
        "ip": "112.224.158.50",
        "version": "IPv4",
        "scope": "public",
        "scopeLabel": "公网",
        "country": "CN",
        "countryCode": "CN",
        "region": None,
        "city": "Qingdao",
        "timezone": None,
        "asn": "4837",
        "asOrganization": "China Unicom Shandong province network",
        "isPrivate": False,
        "isLoopback": False,
        "isGlobal": True,
    }


def test_build_visitor_ip_context_classifies_private_and_loopback_addresses():
    private_payload = ippure_service.build_visitor_ip_context("10.0.0.8")
    loopback_payload = ippure_service.build_visitor_ip_context("127.0.0.1")

    assert private_payload["scope"] == "private"
    assert private_payload["scopeLabel"] == "局域网"
    assert private_payload["version"] == "IPv4"
    assert private_payload["isPrivate"] is True
    assert private_payload["isLoopback"] is False
    assert private_payload["isGlobal"] is False

    assert loopback_payload["scope"] == "loopback"
    assert loopback_payload["scopeLabel"] == "本机回环"
    assert loopback_payload["version"] == "IPv4"
    assert loopback_payload["isPrivate"] is False
    assert loopback_payload["isLoopback"] is True
    assert loopback_payload["isGlobal"] is False
