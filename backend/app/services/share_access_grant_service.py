import base64
import hashlib
import hmac
import json
import time

from app.config import settings

COOKIE_NAME = "share_access_grant"
DEFAULT_TTL_SECONDS = 900


def _encode_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_payload(encoded_payload: str) -> dict:
    padding = "=" * (-len(encoded_payload) % 4)
    raw = base64.urlsafe_b64decode(f"{encoded_payload}{padding}".encode("ascii"))
    payload = json.loads(raw.decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _sign_payload(encoded_payload: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def issue_share_access_grant(share_token: str, expires_in_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    payload = {
        "share_token": str(share_token),
        "exp": int(time.time()) + max(1, int(expires_in_seconds)),
    }
    encoded_payload = _encode_payload(payload)
    signature = _sign_payload(encoded_payload)
    return f"{encoded_payload}.{signature}"


def validate_share_access_grant(raw_cookie: str | None, share_token: str) -> bool:
    if not raw_cookie or "." not in raw_cookie:
        return False

    try:
        encoded_payload, signature = raw_cookie.split(".", 1)
        if not hmac.compare_digest(signature, _sign_payload(encoded_payload)):
            return False

        payload = _decode_payload(encoded_payload)
        if str(payload.get("share_token") or "") != str(share_token):
            return False

        expires_at = int(payload.get("exp") or 0)
        if expires_at <= int(time.time()):
            return False
    except (TypeError, ValueError, json.JSONDecodeError, base64.binascii.Error):
        return False

    return True
