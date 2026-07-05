"""
Rate limit middleware.

Implements in-memory sliding-window throttling without Redis and supports
route-tier policies for auth, share unlock, preview, and download traffic.
"""

import ipaddress
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.utils.logger import get_logger

rate_limit_logger = get_logger("middlewares.rate_limit")

_SHARE_UNLOCK_PATTERN = re.compile(r"^/api/v1/share/([^/]+)/unlock/?$", re.IGNORECASE)
_FILE_RESOURCE_PATTERN = re.compile(
    r"^/api/v1/files/([^/]+)/(preview(?:/pdf)?|pages/[^/]+|preview-assets/[^/]+|html-assets/.+|html|text|download(?:/.*)?)$",
    re.IGNORECASE,
)
_SHARE_FILE_RESOURCE_PATTERN = re.compile(
    r"^/api/v1/share/([^/]+)/files/([^/]+)/(preview(?:/pdf)?|pages/[^/]+|preview-assets/[^/]+|html-assets/.+|html|text|download(?:/.*)?)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    max_requests: int
    window_seconds: int


def _is_mock_value(value: Any) -> bool:
    return value.__class__.__module__.startswith("unittest.mock")


def _coerce_positive_int(value: Any, default: int) -> int:
    if _is_mock_value(value):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _coerce_ip_set(value: Any, default: Optional[set[str]] = None) -> set[str]:
    if default is None:
        default = {"127.0.0.1", "::1"}
    if _is_mock_value(value):
        return set(default)
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        raw_items = [str(item).strip() for item in value]
    else:
        return set(default)

    normalized: set[str] = set()
    for item in raw_items:
        if not item:
            continue
        try:
            normalized.add(str(ipaddress.ip_address(item)))
        except ValueError:
            continue
    return normalized or set(default)


class SlidingWindowCounter:
    def __init__(self, max_requests: int, window_seconds: int, max_keys: int = 10000):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_keys = max(max_keys, 1)
        self._requests: Dict[str, List[float]] = {}

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        now = time.time()
        window_start = now - self.window_seconds

        if key not in self._requests and len(self._requests) >= self.max_keys:
            self.cleanup()
            while self._requests and len(self._requests) >= self.max_keys:
                oldest_key = min(
                    self._requests,
                    key=lambda item: self._requests[item][-1] if self._requests[item] else 0,
                )
                del self._requests[oldest_key]

        timestamps = self._requests.get(key, [])
        self._requests[key] = [ts for ts in timestamps if ts > window_start]
        timestamps = self._requests[key]

        if self.max_requests <= 0:
            return False, self.window_seconds

        if len(timestamps) < self.max_requests:
            timestamps.append(now)
            return True, 0

        if timestamps:
            retry_after = int(timestamps[0] - window_start) + 1
            return False, max(retry_after, 1)

        return True, 0

    def cleanup(self):
        now = time.time()
        window_start = now - self.window_seconds

        expired_keys = []
        for key, timestamps in self._requests.items():
            self._requests[key] = [ts for ts in timestamps if ts > window_start]
            if not self._requests[key]:
                expired_keys.append(key)

        for key in expired_keys:
            del self._requests[key]

    def get_stats(self) -> Dict[str, int]:
        return {key: len(ts) for key, ts in self._requests.items()}


class RateLimitMiddleware(BaseHTTPMiddleware):
    SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}

    def __init__(self, app):
        super().__init__(app)
        self.enabled = settings.RATE_LIMIT_ENABLED
        max_requests = _coerce_positive_int(getattr(settings, "RATE_LIMIT_REQUESTS", 100), 100)
        window_seconds = _coerce_positive_int(getattr(settings, "RATE_LIMIT_WINDOW", 60), 60)
        max_keys = _coerce_positive_int(getattr(settings, "RATE_LIMIT_MAX_KEYS", 10000), 10000)

        self.policies: Dict[str, RateLimitPolicy] = {
            "default": RateLimitPolicy("default", max_requests, window_seconds),
            "auth": RateLimitPolicy(
                "auth",
                _coerce_positive_int(getattr(settings, "AUTH_RATE_LIMIT_REQUESTS", max_requests), max_requests),
                _coerce_positive_int(getattr(settings, "AUTH_RATE_LIMIT_WINDOW", window_seconds), window_seconds),
            ),
            "share_unlock": RateLimitPolicy(
                "share_unlock",
                _coerce_positive_int(
                    getattr(settings, "SHARE_UNLOCK_RATE_LIMIT_REQUESTS", max_requests),
                    max_requests,
                ),
                _coerce_positive_int(
                    getattr(settings, "SHARE_UNLOCK_RATE_LIMIT_WINDOW", window_seconds),
                    window_seconds,
                ),
            ),
            "preview": RateLimitPolicy(
                "preview",
                _coerce_positive_int(getattr(settings, "PREVIEW_RATE_LIMIT_REQUESTS", max_requests), max_requests),
                _coerce_positive_int(getattr(settings, "PREVIEW_RATE_LIMIT_WINDOW", window_seconds), window_seconds),
            ),
            "download": RateLimitPolicy(
                "download",
                _coerce_positive_int(
                    getattr(settings, "DOWNLOAD_RATE_LIMIT_REQUESTS", max_requests),
                    max_requests,
                ),
                _coerce_positive_int(
                    getattr(settings, "DOWNLOAD_RATE_LIMIT_WINDOW", window_seconds),
                    window_seconds,
                ),
            ),
        }
        self.counters: Dict[str, SlidingWindowCounter] = {
            policy.name: SlidingWindowCounter(
                max_requests=policy.max_requests,
                window_seconds=policy.window_seconds,
                max_keys=max_keys,
            )
            for policy in self.policies.values()
        }
        self.counter = self.counters["default"]
        self.trusted_proxy_ips = _coerce_ip_set(getattr(settings, "TRUSTED_PROXY_IPS", None))
        self._request_count = 0
        rate_limit_logger.info(
            f"限流中间件已初始化 - 启用: {self.enabled}, 最大请求数: {max_requests}/{window_seconds}s"
        )

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        policy = self._select_policy(request)
        limit_key = self._get_limit_key(request, policy)
        allowed, retry_after = self.counters[policy.name].is_allowed(limit_key)

        if not allowed:
            rate_limit_logger.warning(
                f"请求被限流 - Policy: {policy.name}, Key: {limit_key}, Path: {request.url.path}, Retry-After: {retry_after}s"
            )
            return await self._build_rate_limit_response(request, retry_after, policy)

        self._request_count += 1
        if self._request_count % 100 == 0:
            for counter in self.counters.values():
                counter.cleanup()

        return await call_next(request)

    def _select_policy(self, request: Request) -> RateLimitPolicy:
        path = (request.url.path or "").lower()

        if path == "/api/v1/auth/login":
            return self.policies["auth"]
        if _SHARE_UNLOCK_PATTERN.match(path):
            return self.policies["share_unlock"]
        if "/preview" in path or "/pages/" in path or "/preview-assets/" in path or "/html-assets/" in path or path.endswith("/html") or path.endswith("/text"):
            return self.policies["preview"]
        if "/download" in path:
            return self.policies["download"]
        return self.policies["default"]

    def _get_limit_key(self, request: Request, policy: Optional[RateLimitPolicy] = None) -> str:
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            base_key = f"user:{user.id}"
        else:
            base_key = f"ip:{self._get_client_ip(request)}"

        if policy is None or policy.name == "default":
            return base_key

        scopes = self._get_policy_scopes(request, policy)
        scoped_key = f"{policy.name}:{base_key}"
        if scopes:
            scoped_key = f"{scoped_key}:{':'.join(scopes)}"
        return scoped_key

    def _get_policy_scopes(self, request: Request, policy: RateLimitPolicy) -> list[str]:
        path = request.url.path or ""

        if policy.name == "share_unlock":
            match = _SHARE_UNLOCK_PATTERN.match(path)
            if match:
                return [f"share:{match.group(1)}"]
            return []

        if policy.name in {"preview", "download"}:
            shared_match = _SHARE_FILE_RESOURCE_PATTERN.match(path)
            if shared_match:
                share_token, file_id = shared_match.groups()[:2]
                return [f"share:{share_token}", f"file:{file_id}"]

            file_match = _FILE_RESOURCE_PATTERN.match(path)
            if file_match:
                return [f"file:{file_match.group(1)}"]

        return []

    def _get_client_ip(self, request: Request) -> str:
        client = getattr(request, "client", None)
        raw_peer_ip = getattr(client, "host", None) if client else None
        peer_ip = self._normalize_ip(raw_peer_ip)

        if self._is_trusted_proxy(peer_ip):
            forwarded_for = request.headers.get("X-Forwarded-For")
            if isinstance(forwarded_for, str) and forwarded_for:
                for candidate in forwarded_for.split(","):
                    normalized = self._normalize_ip(candidate.strip())
                    if normalized:
                        return normalized

            real_ip = request.headers.get("X-Real-IP")
            normalized = self._normalize_ip(real_ip)
            if normalized:
                return normalized

        if peer_ip:
            return peer_ip

        if isinstance(raw_peer_ip, str) and raw_peer_ip.strip():
            return raw_peer_ip.strip()

        return "unknown"

    def _is_trusted_proxy(self, ip: Optional[str]) -> bool:
        normalized = self._normalize_ip(ip)
        return bool(normalized and normalized in self.trusted_proxy_ips)

    @staticmethod
    def _normalize_ip(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            return str(ipaddress.ip_address(value.strip()))
        except (TypeError, ValueError):
            return None

    async def _build_rate_limit_response(
        self,
        request: Request,
        retry_after: int,
        policy: Optional[RateLimitPolicy] = None,
    ) -> JSONResponse:
        selected_policy = policy or self.policies["default"]
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "code": 40003,
                "message": "请求过于频繁，请稍后再试",
                "data": None,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Policy": selected_policy.name,
                "X-RateLimit-Limit": str(selected_policy.max_requests),
                "X-RateLimit-Window": str(selected_policy.window_seconds),
                "X-RateLimit-Remaining": "0",
            },
        )
