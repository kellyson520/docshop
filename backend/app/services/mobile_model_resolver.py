"""Resolve Android model codes to readable device names from a local cache."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import settings

DEFAULT_CACHE_PATH = Path(settings.MOBILE_MODEL_CACHE_DIR) / "mobile_models.json"
_GENERIC_TOKENS = {
    "ANDROID",
    "APPLEWEBKIT",
    "BUILD",
    "CHROME",
    "KHTML",
    "LIKE",
    "LINUX",
    "MOBILE",
    "MOZILLA",
    "SAFARI",
    "VERSION",
    "WV",
}


def normalize_model_code(value: str) -> str:
    """Normalize a model code for exact cache matching."""
    return re.sub(r"\s+", "", value or "").strip().upper()


def extract_model_codes(user_agent: str) -> list[str]:
    """Extract conservative Android model-code candidates from a User-Agent."""
    if not user_agent or "android" not in user_agent.lower():
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    def add_token(token: str) -> None:
        token = re.sub(r"\s+", "", token.strip(" ()[]{};,"))
        if not token:
            return
        upper = token.upper()
        if upper in _GENERIC_TOKENS:
            return
        if upper.startswith(("ANDROID", "CHROME", "SAFARI", "VERSION")):
            return
        if not re.search(r"[A-Za-z]", token) or not re.search(r"\d", token):
            return
        if not re.fullmatch(r"[A-Za-z0-9._+-]+", token):
            return
        if token not in seen:
            seen.add(token)
            candidates.append(token)

    for group in re.findall(r"\(([^)]*)\)", user_agent):
        if "android" not in group.lower():
            continue
        for segment in group.split(";"):
            segment = segment.strip()
            if not segment:
                continue
            if " build/" in segment.lower():
                before_build, after_build = re.split(r"\s+[Bb]uild/", segment, maxsplit=1)
                add_token(before_build)
                add_token(after_build)
                continue
            add_token(segment)

    for token in re.findall(r"\b[A-Za-z][A-Za-z0-9._+-]*\d[A-Za-z0-9._+-]*\b", user_agent):
        add_token(token)

    return candidates


class MobileModelResolver:
    """Lazy, mtime-aware resolver for the local MobileModels JSON cache."""

    def __init__(self, cache_path: str | Path | None = None) -> None:
        self.cache_path = Path(cache_path or DEFAULT_CACHE_PATH)
        self._mtime_ns: int | None = None
        self._mapping: dict[str, dict[str, Any]] = {}

    def _load_mapping(self) -> dict[str, dict[str, Any]]:
        try:
            stat = self.cache_path.stat()
        except OSError:
            self._mtime_ns = None
            self._mapping = {}
            return self._mapping

        if self._mtime_ns == stat.st_mtime_ns:
            return self._mapping

        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._mtime_ns = stat.st_mtime_ns
            self._mapping = {}
            return self._mapping

        mapping: dict[str, dict[str, Any]] = {}
        if isinstance(raw, dict):
            for code, item in raw.items():
                normalized = normalize_model_code(str(code))
                if normalized and isinstance(item, dict):
                    mapping[normalized] = item

        self._mtime_ns = stat.st_mtime_ns
        self._mapping = mapping
        return self._mapping

    def resolve(self, user_agent: str) -> dict[str, str]:
        mapping = self._load_mapping()
        if not mapping:
            return {}

        for candidate in extract_model_codes(user_agent):
            item = mapping.get(normalize_model_code(candidate))
            if not item:
                continue

            code = str(item.get("model") or candidate).strip()
            brand = str(item.get("brand_title") or "").strip()
            model = str(item.get("model_name") or "").strip()
            display_parts = " ".join(part for part in (brand, model) if part).strip()
            display = f"{display_parts} / {code}" if display_parts and code else display_parts or code
            if not display:
                return {}

            return {
                "device_model_code": code,
                "device_model_name": model,
                "device_brand_name": brand,
                "device_display_name": display,
            }

        return {}

    def resolve_code(self, model_code: str) -> dict[str, str]:
        """Resolve one exact model code from Client Hints or other trusted client data."""
        mapping = self._load_mapping()
        if not mapping:
            return {}

        candidate = normalize_model_code(model_code)
        item = mapping.get(candidate)
        if not item:
            return {}

        code = str(item.get("model") or model_code).strip()
        brand = str(item.get("brand_title") or "").strip()
        model = str(item.get("model_name") or "").strip()
        display_parts = " ".join(part for part in (brand, model) if part).strip()
        display = f"{display_parts} / {code}" if display_parts and code else display_parts or code
        if not display:
            return {}

        return {
            "device_model_code": code,
            "device_model_name": model,
            "device_brand_name": brand,
            "device_display_name": display,
        }


def resolve_mobile_model_from_user_agent(
    user_agent: str,
    cache_path: str | Path | None = None,
) -> dict[str, str]:
    return MobileModelResolver(cache_path).resolve(user_agent)


def resolve_mobile_model_code(
    model_code: str,
    cache_path: str | Path | None = None,
) -> dict[str, str]:
    return MobileModelResolver(cache_path).resolve_code(model_code)
