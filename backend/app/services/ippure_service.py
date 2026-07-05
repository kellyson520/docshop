from __future__ import annotations

import ipaddress
from typing import Any

import requests

from app.services.cache_service import CacheService
from app.utils.logger import get_logger


IPPURE_INFO_URL = "https://my.ippure.com/v1/info"
IPPURE_CACHE_KEY = "tracking:server_ip_context"
IPPURE_CACHE_TTL_SECONDS = 300

ippure_logger = get_logger("services.ippure_service")
ippure_cache = CacheService(enabled=True, ttl=IPPURE_CACHE_TTL_SECONDS, max_size=8)


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _classify_ip_scope(parsed_ip: ipaddress._BaseAddress) -> tuple[str, str]:
    if parsed_ip.is_loopback:
        return "loopback", "本机回环"
    if parsed_ip.is_private:
        return "private", "局域网"
    if parsed_ip.is_link_local:
        return "link_local", "链路本地"
    if parsed_ip.is_multicast:
        return "multicast", "组播"
    if parsed_ip.is_reserved:
        return "reserved", "保留地址"
    if parsed_ip.is_unspecified:
        return "unspecified", "未指定"
    if parsed_ip.is_global:
        return "public", "公网"
    return "special", "特殊地址"


def _normalize_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    ip = payload.get("ip")
    if ip is None or str(ip).strip() == "":
        return None

    return {
        "source": "ippure_server_egress",
        "ip": ip,
        "asn": payload.get("asn"),
        "asOrganization": payload.get("asOrganization"),
        "country": payload.get("country"),
        "countryCode": payload.get("countryCode"),
        "region": payload.get("region"),
        "regionCode": payload.get("regionCode"),
        "city": payload.get("city"),
        "timezone": payload.get("timezone"),
        "longitude": payload.get("longitude"),
        "latitude": payload.get("latitude"),
        "postalCode": payload.get("postalCode"),
        "fraudScore": payload.get("fraudScore"),
        "isResidential": payload.get("isResidential"),
        "isBroadcast": payload.get("isBroadcast"),
    }


def build_visitor_ip_context(
    ip_address: str | None,
    location: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    normalized_ip = _normalize_text(ip_address)
    if not normalized_ip:
        return None

    parsed_ip = None
    version = None
    scope = "invalid"
    scope_label = "格式异常"
    is_private = None
    is_loopback = None
    is_global = None

    try:
        parsed_ip = ipaddress.ip_address(normalized_ip)
    except ValueError:
        if ":" in normalized_ip:
            version = "IPv6"
        elif "." in normalized_ip:
            version = "IPv4"
    else:
        version = f"IPv{parsed_ip.version}"
        scope, scope_label = _classify_ip_scope(parsed_ip)
        is_loopback = parsed_ip.is_loopback
        is_private = parsed_ip.is_private and not is_loopback
        is_global = parsed_ip.is_global

    location = location or {}
    country = _normalize_text(location.get("country"))
    country_code = _normalize_text(location.get("countryCode")) or country

    return {
        "source": "access_log_visitor_ip",
        "ip": normalized_ip,
        "version": version,
        "scope": scope,
        "scopeLabel": scope_label,
        "country": country,
        "countryCode": country_code,
        "region": _normalize_text(location.get("region")),
        "city": _normalize_text(location.get("city")),
        "timezone": _normalize_text(location.get("timezone")),
        "asn": _normalize_text(location.get("asn")),
        "asOrganization": _normalize_text(location.get("isp") or location.get("asOrganization")),
        "isPrivate": is_private,
        "isLoopback": is_loopback,
        "isGlobal": is_global,
    }


def fetch_server_ip_context(force_refresh: bool = False) -> dict[str, Any] | None:
    cached = None if force_refresh else ippure_cache.get(IPPURE_CACHE_KEY)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            IPPURE_INFO_URL,
            timeout=(1.0, 3.0),
            headers={"User-Agent": "DocShopTracking/1.0"},
        )
        response.raise_for_status()
        normalized = _normalize_payload(response.json())
        if normalized is not None:
            ippure_cache.set(IPPURE_CACHE_KEY, normalized, ttl=IPPURE_CACHE_TTL_SECONDS)
        return normalized
    except Exception as exc:
        ippure_logger.warning("fetch_server_ip_context failed: %s", exc)
        return ippure_cache.get(IPPURE_CACHE_KEY)
