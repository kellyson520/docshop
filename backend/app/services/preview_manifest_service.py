from __future__ import annotations

import json
from typing import Any


def _get_value(item: Any, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def load_analysis_summary(payload: str | dict | None) -> dict:
    if not payload:
        return {}
    if isinstance(payload, dict):
        return payload
    try:
        data = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _base_file_path(file_id: str, share_token: str | None = None) -> str:
    if share_token:
        return f"/api/v1/share/{share_token}/files/{file_id}"
    return f"/api/v1/files/{file_id}"


def _preview_url(file_id: str, version_number: int, share_token: str | None = None) -> str:
    return f"{_base_file_path(file_id, share_token)}/preview?version={version_number}"


def _page_url(file_id: str, version_number: int, page_number: int, share_token: str | None = None) -> str:
    return f"{_base_file_path(file_id, share_token)}/pages/{page_number}?version={version_number}"


def _preview_asset_url(file_id: str, asset_id: str, share_token: str | None = None) -> str:
    return f"{_base_file_path(file_id, share_token)}/preview-assets/{asset_id}"


def _download_url(file_id: str, version_id: str, share_token: str | None = None) -> str:
    return f"{_base_file_path(file_id, share_token)}/versions/{version_id}/download"


def build_preview_asset_payloads(
    *,
    file_id: str,
    version_id: str,
    version_number: int,
    preview_assets: list[Any] | None,
    share_token: str | None = None,
) -> list[dict]:
    payloads = []
    for asset in preview_assets or []:
        asset_id = _get_value(asset, "id")
        asset_type = _get_value(asset, "asset_type")
        page_number = _get_value(asset, "page_number")

        if asset_type in {"thumbnail", "page_image"} and page_number:
            url = _page_url(file_id, version_number, page_number, share_token)
        elif asset_type in {"pdf", "video", "html", "html_runtime_entry"}:
            url = _preview_url(file_id, version_number, share_token)
        elif asset_type in {"poster", "preview_video"} and asset_id:
            url = _preview_asset_url(file_id, asset_id, share_token)
        else:
            url = _download_url(file_id, version_id, share_token)

        if asset_type == "html":
            asset_type = "html_runtime_entry"

        payloads.append(
            {
                "asset_id": asset_id,
                "asset_type": asset_type,
                "page_number": page_number,
                "url": url,
                "status": _get_value(asset, "status", "ready"),
            }
        )
    return payloads


def _native_preview_status(file_profile: dict) -> str:
    category = file_profile.get("category")
    preview_mode = file_profile.get("preview_mode")
    status = file_profile.get("preview_status") or "not_supported"
    if preview_mode == "native" and category in {"image", "video", "pdf", "html"}:
        return "ready"
    return status


def build_preview_manifest(file_profile: dict, preview_assets: list[dict], analysis_summary: dict | None) -> dict:
    category = file_profile["category"]
    preview_status = _native_preview_status(file_profile)
    analysis_status = file_profile.get("analysis_status") or preview_status

    if category == "office":
        primary_asset = next((asset for asset in preview_assets if asset["asset_type"] == "pdf"), None)
        thumbnails = [
            {"page": asset["page_number"], "url": asset["url"]}
            for asset in preview_assets
            if asset["asset_type"] == "thumbnail"
        ]
        status = "ready" if primary_asset else (file_profile.get("preview_status") or "pending")
        return {
            "type": "office_pdf",
            "status": status if status else "failed",
            "primary_asset": primary_asset,
            "thumbnails": thumbnails,
            "summary": analysis_summary or {},
        }

    if category == "archive":
        status = "ready" if analysis_summary else analysis_status
        return {
            "type": "archive_structure",
            "status": status if status else "failed",
            "primary_asset": None,
            "thumbnails": [],
            "summary": analysis_summary or {},
        }

    if category == "video":
        preview_video_asset = next((asset for asset in preview_assets if asset["asset_type"] == "preview_video"), None)
        video_asset = next((asset for asset in preview_assets if asset["asset_type"] == "video"), None)
        poster_asset = next((asset for asset in preview_assets if asset["asset_type"] == "poster"), None)
        primary_asset = preview_video_asset or video_asset or poster_asset
        return {
            "type": "video_native",
            "status": "ready" if primary_asset else preview_status,
            "primary_asset": primary_asset,
            "poster_asset": poster_asset,
            "original_asset": video_asset if preview_video_asset else None,
            "thumbnails": [],
            "summary": analysis_summary or {},
        }

    if category == "image":
        primary_asset = next((asset for asset in preview_assets if asset["asset_type"] in {"image", "original"}), None)
        return {
            "type": "image_native",
            "status": "ready" if primary_asset else preview_status,
            "primary_asset": primary_asset,
            "thumbnails": [],
            "summary": analysis_summary or {},
        }

    if category == "pdf":
        primary_asset = next((asset for asset in preview_assets if asset["asset_type"] == "pdf"), None)
        return {
            "type": "pdf_native",
            "status": "ready" if primary_asset else preview_status,
            "primary_asset": primary_asset,
            "thumbnails": [],
            "summary": analysis_summary or {},
        }

    if category == "html":
        primary_asset = next((asset for asset in preview_assets if asset["asset_type"] == "html_runtime_entry"), None)
        return {
            "type": "html_runtime",
            "status": "ready" if primary_asset else preview_status,
            "primary_asset": primary_asset,
            "thumbnails": [],
            "summary": analysis_summary or {},
        }

    return {
        "type": "fallback",
        "status": file_profile.get("preview_status", "not_supported"),
        "primary_asset": None,
        "thumbnails": [],
        "summary": analysis_summary or {},
    }


def build_preview_manifest_payload(
    file_profile: dict,
    *,
    file_id: str,
    version_id: str,
    version_number: int,
    preview_assets: list[Any] | None,
    analysis_summary: dict | None,
    share_token: str | None = None,
) -> dict:
    payload_assets = build_preview_asset_payloads(
        file_id=file_id,
        version_id=version_id,
        version_number=version_number,
        preview_assets=preview_assets,
        share_token=share_token,
    )

    category = file_profile.get("category")
    if category == "office" and not any(asset["asset_type"] == "pdf" for asset in payload_assets):
        payload_assets.insert(
            0,
            {
                "asset_type": "pdf",
                "page_number": None,
                "url": _preview_url(file_id, version_number, share_token),
                "status": file_profile.get("preview_status", "pending"),
            },
        )
    elif category == "image" and not payload_assets:
        payload_assets.append(
            {
                "asset_type": "image",
                "page_number": None,
                "url": _download_url(file_id, version_id, share_token),
                "status": "ready",
            }
        )
    elif category == "pdf" and not payload_assets:
        payload_assets.append(
            {
                "asset_type": "pdf",
                "page_number": None,
                "url": _preview_url(file_id, version_number, share_token),
                "status": "ready",
            }
        )
    elif category == "video" and not any(asset["asset_type"] in {"video", "preview_video"} for asset in payload_assets):
        payload_assets.insert(
            0,
            {
                "asset_type": "video",
                "page_number": None,
                "url": _preview_url(file_id, version_number, share_token),
                "status": "ready",
            }
        )
    elif category == "html" and not payload_assets:
        payload_assets.append(
            {
                "asset_type": "html_runtime_entry",
                "page_number": None,
                "url": _preview_url(file_id, version_number, share_token),
                "status": file_profile.get("preview_status", "ready"),
            }
        )

    return build_preview_manifest(file_profile, payload_assets, analysis_summary)
