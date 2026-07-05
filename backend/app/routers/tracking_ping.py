
"""Browser-side tracking beacon endpoint."""

from __future__ import annotations

import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import desc

from app.config import settings
from app.database import SessionLocal
from app.models.access_log import AccessLog
from app.models.tracking_config import TrackingConfig
from app.models.user_session import UserSession
from app.services.mobile_model_resolver import (
    resolve_mobile_model_code,
    resolve_mobile_model_from_user_agent,
)
from app.schemas.response import success_response
from app.utils.logger import get_logger

logger = get_logger("tracking-ping")
router = APIRouter(prefix="/tracking", tags=["tracking"])

_RATE_LIMIT_SECONDS = 10
_rate_limit_cache: dict[str, float] = {}

_DIRECT_FIELDS = {
    "visitor_id",
    "screen_resolution",
    "geo_latitude",
    "geo_longitude",
    "geo_accuracy",
    "client_timezone",
    "client_language",
    "device_brand",
    "device_model",
    "device_model_code",
    "device_model_name",
    "device_brand_name",
    "device_display_name",
}
_ALIAS_FIELDS = {
    "device_id": "visitor_id",
    "timezone": "client_timezone",
    "language": "client_language",
}
_EXTRA_FIELDS = {
    "screen_avail",
    "screen_color_depth",
    "screen_pixel_ratio",
    "screen_orientation",
    "platform",
    "hardware_concurrency",
    "device_memory",
    "max_touch_points",
    "touch_support",
    "pointer_coarse",
    "pointer_fine",
    "hover_hover",
    "any_pointer_coarse",
    "any_pointer_fine",
    "network_type",
    "network_downlink",
    "network_rtt",
    "network_save_data",
    "cpu_architecture",
    "cpu_bitness",
    "platform_version",
    "browser_full_version",
    "storage_quota_gb",
}


def _check_rate_limit(identity: str) -> bool:
    now = time.time()
    last = _rate_limit_cache.get(identity, 0)
    if now - last < _RATE_LIMIT_SECONDS:
        return False
    _rate_limit_cache[identity] = now
    return True


def _rate_limit_identity(identity: str, page_path: str = "") -> str:
    normalized_page_path = str(page_path or "").strip()
    if normalized_page_path:
        return f"{identity}|page|{normalized_page_path}"
    return identity


def _anonymize_coordinates(lat: Any, lng: Any, accuracy: Any) -> tuple[Any, Any, Any]:
    if lat is not None:
        lat = round(float(lat), 3)
    if lng is not None:
        lng = round(float(lng), 3)
    if accuracy is not None:
        accuracy = max(float(accuracy), 111.0)
    return lat, lng, accuracy


def _normalized_payload(body: dict[str, Any], *, anonymize: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    updates: dict[str, Any] = {}
    extras: dict[str, Any] = {}

    for key, value in body.items():
        if value is None:
            continue
        target = _ALIAS_FIELDS.get(key, key)
        if target in _DIRECT_FIELDS:
            updates[target] = value
        elif target in _EXTRA_FIELDS:
            extras[target] = value

    if anonymize and (updates.get("geo_latitude") is not None or updates.get("geo_longitude") is not None):
        lat, lng, accuracy = _anonymize_coordinates(
            updates.get("geo_latitude"),
            updates.get("geo_longitude"),
            updates.get("geo_accuracy"),
        )
        updates["geo_latitude"] = lat
        updates["geo_longitude"] = lng
        updates["geo_accuracy"] = accuracy

    return updates, extras


def _merge_raw_data(raw_data: str | None, extras: dict[str, Any]) -> str | None:
    if not extras:
        return raw_data
    data: dict[str, Any] = {}
    if raw_data:
        try:
            parsed = json.loads(raw_data)
            if isinstance(parsed, dict):
                data = parsed
        except (TypeError, json.JSONDecodeError):
            data = {"raw": raw_data}
    client_extra = data.get("client_extra") if isinstance(data.get("client_extra"), dict) else {}
    client_extra.update(extras)
    data["client_extra"] = client_extra
    return json.dumps(data, ensure_ascii=False)


def _parse_screen_size(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, str) or "x" not in value.lower():
        return None
    left, right = value.lower().split("x", 1)
    try:
        width = float(left.strip())
        height = float(right.strip())
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def _physical_screen_signature(profile: dict[str, Any]) -> tuple[int, int] | None:
    size = _parse_screen_size(profile.get("screen_avail"))
    ratio = profile.get("screen_pixel_ratio")
    try:
        pixel_ratio = float(ratio)
    except (TypeError, ValueError):
        return None
    if not size or pixel_ratio <= 0:
        return None
    width, height = size
    physical = sorted((int(round(width * pixel_ratio)), int(round(height * pixel_ratio))))
    return physical[0], physical[1]


def _hardware_profiles_match(known: dict[str, Any], current: dict[str, Any]) -> bool:
    """Match same-device browser profiles conservatively across viewport scaling."""
    known_screen = _physical_screen_signature(known)
    current_screen = _physical_screen_signature(current)
    if not known_screen or not current_screen:
        return False

    screen_close = (
        abs(known_screen[0] - current_screen[0]) <= 8
        and abs(known_screen[1] - current_screen[1]) <= 8
    )
    if not screen_close:
        return False

    for key in ("platform", "hardware_concurrency", "max_touch_points"):
        known_value = known.get(key)
        current_value = current.get(key)
        if known_value is not None and current_value is not None and str(known_value) != str(current_value):
            return False

    return True


def _extract_client_extra(raw_data: str | None) -> dict[str, Any]:
    if not raw_data:
        return {}
    try:
        parsed = json.loads(raw_data)
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    extra = parsed.get("client_extra")
    return extra if isinstance(extra, dict) else {}


def _enrich_updates_with_resolved_mobile_model(updates: dict[str, Any]) -> dict[str, Any]:
    model_code = str(updates.get("device_model") or updates.get("device_model_code") or "").strip()
    if not model_code or updates.get("device_display_name"):
        return updates

    try:
        cache_path = Path(settings.MOBILE_MODEL_CACHE_DIR) / "mobile_models.json"
        resolved = resolve_mobile_model_code(model_code, cache_path=cache_path)
    except Exception as exc:
        logger.debug("resolve client-hint mobile model failed: %s", exc)
        return updates

    if resolved:
        updates.update(resolved)
    return updates


def _looks_like_reduced_android_model(value: Any) -> bool:
    return str(value or "").strip().upper() in {"", "K"}


def _resolved_fields_from_log(log: Any) -> dict[str, Any]:
    display_name = getattr(log, "device_display_name", None)
    model_name = getattr(log, "device_model_name", None)
    if not display_name and not model_name:
        return {}
    return {
        "device_model_code": getattr(log, "device_model_code", None),
        "device_model_name": model_name,
        "device_brand_name": getattr(log, "device_brand_name", None),
        "device_display_name": display_name,
    }


def _find_unique_hardware_profile_match(db, extras: dict[str, Any], source_log: Any | None) -> dict[str, Any]:
    if not extras:
        return {}
    source_resolved = _resolved_fields_from_log(source_log)
    if source_resolved:
        return source_resolved

    try:
        candidates = (
            db.query(AccessLog)
            .filter(AccessLog.device_display_name.isnot(None))
            .order_by(desc(AccessLog.timestamp))
            .limit(200)
            .all()
        )
    except Exception as exc:
        logger.debug("hardware profile lookup failed: %s", exc)
        return {}

    matches: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for candidate in candidates:
        resolved = _resolved_fields_from_log(candidate)
        display_name = resolved.get("device_display_name")
        if not display_name or display_name in seen_names:
            continue
        known_extra = _extract_client_extra(getattr(candidate, "raw_data", None))
        if _hardware_profiles_match(known_extra, extras):
            seen_names.add(display_name)
            matches.append(resolved)

    return matches[0] if len(matches) == 1 else {}


def _client_ip_from_request(request: Request) -> str:
    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    return host or "0.0.0.0"


def _parse_client_hints(headers: dict[str, Any]) -> dict[str, Any]:
    sec_ch_ua = str(headers.get("sec-ch-ua", ""))
    mobile = str(headers.get("sec-ch-ua-mobile", "")).strip()
    platform = str(headers.get("sec-ch-ua-platform", "")).strip().strip('"')

    browser_name = None
    browser_version = None
    for brand, version in re.findall(r'"([^"]+)";v="([^"]+)"', sec_ch_ua):
        if brand == "Not)A;Brand":
            continue
        if brand == "Microsoft Edge":
            browser_name = "Edge"
            browser_version = version.split(".")[0]
            break
        if brand == "Chromium" and browser_name is None:
            browser_name = "Chromium"
            browser_version = version.split(".")[0]

    os_name = platform or None
    device_type = None
    if mobile == "?1":
        device_type = "mobile"
    elif mobile == "?0":
        device_type = "desktop"

    return {
        "browser_name": browser_name,
        "browser_version": browser_version,
        "os_name": os_name,
        "device_type": device_type,
    }


def _simple_user_agent_parse(user_agent_str: str) -> dict[str, Any]:
    ua_lower = user_agent_str.lower()

    device_type = "unknown"
    if "mobile" in ua_lower or ("android" in ua_lower and "tablet" not in ua_lower):
        device_type = "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device_type = "tablet"
    elif "windows" in ua_lower or "macintosh" in ua_lower or "linux" in ua_lower:
        device_type = "desktop"

    os_name = "unknown"
    if "android" in ua_lower:
        os_name = "Android"
    elif "windows" in ua_lower:
        os_name = "Windows"
    elif "macintosh" in ua_lower or "mac os" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower:
        os_name = "Linux"
    elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"

    browser_name = "unknown"
    browser_version = None
    if "edga/" in ua_lower or "edg/" in ua_lower:
        browser_name = "Edge"
        match = re.search(r"edg(?:a|ios)?/([\d.]+)", ua_lower)
        browser_version = match.group(1).split(".")[0] if match else None
    elif "chrome" in ua_lower and "edg" not in ua_lower:
        browser_name = "Chrome"
        match = re.search(r"chrome/([\d.]+)", ua_lower)
        browser_version = match.group(1).split(".")[0] if match else None
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser_name = "Safari"
    elif "firefox" in ua_lower:
        browser_name = "Firefox"

    device_model = None
    if "iphone" in ua_lower:
        device_brand = "Apple"
        match = re.search(r"iphone(\d+),?(\d+)?", ua_lower)
        device_model = f"iPhone{match.group(1)}" if match else "iPhone"
    elif "ipad" in ua_lower:
        device_brand = "Apple"
        device_model = "iPad"
    elif "android" in ua_lower:
        match = re.search(r"Android [^;]+;\s*([^;]+?)\s*Build/", user_agent_str, re.IGNORECASE)
        device_model = match.group(1).strip() if match else None
        fallback_match = re.search(r";\s*([a-zA-Z0-9\s\-]+?)\)", user_agent_str)
        if not device_model and fallback_match:
            device_model = fallback_match.group(1).strip()
        device_brand = device_model.split()[0].title() if device_model else None
    elif "windows" in ua_lower:
        device_brand = "Microsoft"
        device_model = "PC"
    elif "mac" in ua_lower:
        device_brand = "Apple"
        device_model = "Mac"
    else:
        device_brand = None

    return {
        "device_type": device_type,
        "device_brand": device_brand,
        "device_model": device_model,
        "os_name": os_name,
        "os_version": None,
        "browser_name": browser_name,
        "browser_version": browser_version,
    }


def _parse_user_agent(user_agent_str: str) -> dict[str, Any]:
    try:
        from user_agents import parse

        ua = parse(user_agent_str)
        device_type = "unknown"
        if ua.is_mobile:
            device_type = "mobile"
        elif ua.is_tablet:
            device_type = "tablet"
        elif ua.is_pc:
            device_type = "desktop"

        return {
            "device_type": device_type,
            "device_brand": str(ua.device.brand or "").strip().title() or None,
            "device_model": str(ua.device.model or "").strip() or None,
            "os_name": ua.os.family,
            "os_version": ua.os.version_string,
            "browser_name": ua.browser.family,
            "browser_version": ua.browser.version_string,
        }
    except ImportError:
        logger.debug("user_agents not installed; using simplified parser")
        return _simple_user_agent_parse(user_agent_str)
    except Exception as exc:
        logger.debug("user agent parsing failed; using simplified parser: %s", exc)
        return _simple_user_agent_parse(user_agent_str)


def _merge_device_signals(client_hints: dict[str, Any], ua_info: dict[str, Any]) -> dict[str, Any]:
    merged = dict(ua_info or {})
    for key, value in (client_hints or {}).items():
        if value is not None:
            merged[key] = value
    return merged


def _build_request_device_context(request: Request, updates: dict[str, Any]) -> dict[str, Any]:
    headers = dict(getattr(request, "headers", {}) or {})
    user_agent = str(headers.get("user-agent", "") or "").strip()
    device_info = _merge_device_signals(
        _parse_client_hints(headers),
        _parse_user_agent(user_agent) if user_agent else {},
    )

    if user_agent:
        device_info["user_agent"] = user_agent[:500]
        try:
            cache_path = Path(settings.MOBILE_MODEL_CACHE_DIR) / "mobile_models.json"
            resolved_model = resolve_mobile_model_from_user_agent(user_agent, cache_path=cache_path)
        except Exception as exc:
            logger.debug("resolve user-agent mobile model failed: %s", exc)
        else:
            if resolved_model:
                device_info.update(resolved_model)

    for field in (
        "device_brand",
        "device_model",
        "device_model_code",
        "device_model_name",
        "device_brand_name",
        "device_display_name",
    ):
        value = updates.get(field)
        if value:
            device_info[field] = value

    return device_info


def _create_page_view_log_from_source(
    *,
    source_log: Any | None,
    session: Any | None,
    session_id: str | None,
    device_id: str | None,
    page_path: str,
    updates: dict[str, Any],
    extras: dict[str, Any],
    request_device_info: dict[str, Any],
    request: Request,
) -> AccessLog:
    user_id = getattr(source_log, "user_id", None) or getattr(session, "user_id", None)
    visitor_id = device_id or getattr(source_log, "visitor_id", None) or getattr(session, "visitor_id", None)
    ip_address = getattr(source_log, "ip_address", None) or getattr(session, "last_ip", None) or _client_ip_from_request(request)
    source_device_model = (
        updates.get("device_model")
        or getattr(source_log, "device_model", None)
        or request_device_info.get("device_model")
    )

    log = AccessLog(
        timestamp=datetime.now(timezone.utc).isoformat(),
        user_id=user_id,
        is_authenticated=1 if user_id else 0,
        visitor_id=visitor_id,
        is_page_view=1,
        ip_address=ip_address,
        ip_country=getattr(source_log, "ip_country", None),
        ip_city=getattr(source_log, "ip_city", None),
        ip_isp=getattr(source_log, "ip_isp", None),
        ip_asn=getattr(source_log, "ip_asn", None),
        user_agent=(
            getattr(source_log, "user_agent", None)
            or getattr(session, "first_user_agent", None)
            or request_device_info.get("user_agent")
        ),
        device_type=(
            getattr(source_log, "device_type", None)
            or getattr(session, "device_type", None)
            or request_device_info.get("device_type")
        ),
        device_brand=(
            updates.get("device_brand")
            or getattr(source_log, "device_brand", None)
            or request_device_info.get("device_brand")
        ),
        device_model=source_device_model,
        device_model_code=(
            updates.get("device_model_code")
            or getattr(source_log, "device_model_code", None)
            or request_device_info.get("device_model_code")
        ),
        device_model_name=(
            updates.get("device_model_name")
            or getattr(source_log, "device_model_name", None)
            or request_device_info.get("device_model_name")
        ),
        device_brand_name=(
            updates.get("device_brand_name")
            or getattr(source_log, "device_brand_name", None)
            or request_device_info.get("device_brand_name")
        ),
        device_display_name=(
            updates.get("device_display_name")
            or getattr(source_log, "device_display_name", None)
            or request_device_info.get("device_display_name")
        ),
        os_name=(
            getattr(source_log, "os_name", None)
            or getattr(session, "os_name", None)
            or request_device_info.get("os_name")
        ),
        os_version=getattr(source_log, "os_version", None) or request_device_info.get("os_version"),
        browser_name=(
            getattr(source_log, "browser_name", None)
            or getattr(session, "browser_name", None)
            or request_device_info.get("browser_name")
        ),
        browser_version=getattr(source_log, "browser_version", None) or request_device_info.get("browser_version"),
        screen_resolution=updates.get("screen_resolution", getattr(source_log, "screen_resolution", None)),
        geo_latitude=updates.get("geo_latitude", getattr(source_log, "geo_latitude", None)),
        geo_longitude=updates.get("geo_longitude", getattr(source_log, "geo_longitude", None)),
        geo_accuracy=updates.get("geo_accuracy", getattr(source_log, "geo_accuracy", None)),
        client_timezone=updates.get("client_timezone", getattr(source_log, "client_timezone", None)),
        client_language=updates.get("client_language", getattr(source_log, "client_language", None)),
        request_method="GET",
        request_path=page_path,
        response_status=200,
        response_time_ms=0,
        session_id=session_id,
        raw_data=_merge_raw_data(None, extras),
    )
    return log




@router.get("/config")
def get_public_tracking_config(request: Request):
    db = SessionLocal()
    try:
        config = db.query(TrackingConfig).first()
        if not config:
            config = TrackingConfig()
            db.add(config)
            db.commit()
        return success_response({
            "enable_tracking": bool(getattr(config, "enable_tracking", 1)),
            "enable_device_tracking": bool(getattr(config, "enable_device_tracking", 1)),
            "enable_location_tracking": bool(getattr(config, "enable_location_tracking", 0)),
            "anonymize_ip": bool(getattr(config, "anonymize_ip", 0)),
            "device_id": getattr(request.state, "device_id", None) or request.cookies.get("device_id"),
            "session_id": getattr(request.state, "session_id", None) or request.cookies.get("session_id"),
        })
    finally:
        db.close()


@router.post("/ping", status_code=204)
async def receive_ping(request: Request):
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid json") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid payload")

    session_id = body.get("session_id") or request.cookies.get("session_id")
    device_id = body.get("device_id") or request.cookies.get("device_id")
    page_path = str(body.get("page_path") or "").strip()
    identity = session_id or device_id
    if not identity:
        raise HTTPException(status_code=400, detail="missing session_id or device_id")
    if not _check_rate_limit(_rate_limit_identity(str(identity), page_path)):
        raise HTTPException(status_code=429, detail="too many pings")

    db = SessionLocal()
    try:
        config = db.query(TrackingConfig).first()
        anonymize = bool(config and getattr(config, "anonymize_ip", 0))
        updates, extras = _normalized_payload(body, anonymize=anonymize)
        updates = _enrich_updates_with_resolved_mobile_model(updates)
        request_device_info = _build_request_device_context(request, updates)

        log = None
        session = None
        if session_id:
            log = db.query(AccessLog).filter(
                AccessLog.session_id == session_id,
                AccessLog.is_deleted == 0,
            ).order_by(desc(AccessLog.timestamp)).first()
        if log is None and device_id:
            log = db.query(AccessLog).filter(
                AccessLog.visitor_id == device_id,
                AccessLog.is_deleted == 0,
            ).order_by(desc(AccessLog.timestamp)).first()

        if session_id:
            session = db.query(UserSession).filter(UserSession.session_id == session_id).first()

        if page_path:
            if log is not None and getattr(log, "is_page_view", 0) == 1 and getattr(log, "request_path", None) == page_path:
                for field, value in updates.items():
                    setattr(log, field, value)
                log.raw_data = _merge_raw_data(getattr(log, "raw_data", None), extras)
                db.commit()
                return Response(status_code=204)

            source_model = updates.get("device_model", getattr(log, "device_model", None))
            if not updates.get("device_display_name") and _looks_like_reduced_android_model(source_model):
                matched_model = _find_unique_hardware_profile_match(db, extras, log)
                if matched_model:
                    updates.update(matched_model)
                    if log is not None:
                        for field, value in matched_model.items():
                            setattr(log, field, value)

            page_view_log = _create_page_view_log_from_source(
                source_log=log,
                session=session,
                session_id=session_id,
                device_id=device_id,
                page_path=page_path,
                updates=updates,
                extras=extras,
                request_device_info=request_device_info,
                request=request,
            )
            db.add(page_view_log)
            db.commit()
            return Response(status_code=204)

        if log is not None:
            for field, value in updates.items():
                setattr(log, field, value)
            log.raw_data = _merge_raw_data(getattr(log, "raw_data", None), extras)
            db.commit()
        elif session_id:
            if session is not None:
                pending = {**updates, **extras}
                existing: dict[str, Any] = {}
                raw_data = getattr(session, "raw_data", None)
                if raw_data:
                    try:
                        parsed = json.loads(raw_data)
                        if isinstance(parsed, dict):
                            existing = parsed
                    except (TypeError, json.JSONDecodeError):
                        existing = {}
                existing["pending_beacon"] = pending
                session.raw_data = json.dumps(existing, ensure_ascii=False)
                db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("tracking ping failed")
        raise HTTPException(status_code=500, detail="tracking ping failed") from exc
    finally:
        db.close()

    return Response(status_code=204)
