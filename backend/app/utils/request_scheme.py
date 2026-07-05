from __future__ import annotations

from fastapi import Request


def is_https_request(request: Request | None) -> bool:
    if request is None:
        return False

    forwarded = str(request.headers.get("x-forwarded-proto", "")).split(",")[0].strip().lower()
    if forwarded in {"http", "https"}:
        return forwarded == "https"

    return str(getattr(request.url, "scheme", "") or "").lower() == "https"
