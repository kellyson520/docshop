from __future__ import annotations

from typing import Any

import requests

from app.services.cache_service import CacheService
from app.utils.logger import get_logger


IPPURE_INFO_URL = "https://my.ippure.com/v1/info"
IPPURE_CACHE_KEY = "tracking:server_ip_context"
IPPURE_CACHE_TTL_SECONDS = 300

ippure_logger = get_logger("services.ippure_service")
ippure_cache = CacheService(enabled=True, ttl=IPPURE_CACHE_TTL_SECONDS, max_size=8)


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
