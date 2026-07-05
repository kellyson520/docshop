from __future__ import annotations

import html as html_lib
import re
from pathlib import Path
from typing import Callable

RUNTIME_HTML_PREVIEW_MARKER = "docshop-runtime-preview"

_RESOURCE_ATTR_RE = re.compile(
    r'(?P<prefix>\b(?:src|href|poster|action)\s*=\s*)(?P<quote>["\'])(?P<value>.*?)(?P=quote)',
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_RE = re.compile(r"<html\b(?P<attrs>[^>]*)>", re.IGNORECASE)
_HEAD_TAG_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
_TITLE_TAG_RE = re.compile(r"<title\b[^>]*>.*?</title>", re.IGNORECASE | re.DOTALL)
_BODY_TAG_RE = re.compile(r"<body\b(?P<attrs>[^>]*)>", re.IGNORECASE)
_SOURCE_MAP_RE = re.compile(
    r"<!--\s*#?\s*sourceMappingURL=.*?-->|/\*#\s*sourceMappingURL=.*?\*/|//[@#]\s*source(?:Mapping)?URL=.*?(?=\r?\n|$)",
    re.IGNORECASE | re.DOTALL,
)
_DEBUG_HTML_COMMENT_RE = re.compile(
    r"<!--\s*(?:debug|sourceurl|sourcemappingurl|vite|webpack).*?-->",
    re.IGNORECASE | re.DOTALL,
)
_SKIP_RESOURCE_PREFIXES = (
    "#",
    "/",
    "http://",
    "https://",
    "data:",
    "blob:",
    "mailto:",
    "tel:",
    "javascript:",
)


def runtime_html_response_headers() -> dict[str, str]:
    return {
        "Cache-Control": "private, no-store, max-age=0",
        "Content-Security-Policy": (
            "default-src 'self' data: blob: http: https:; "
            "img-src * data: blob:; "
            "media-src * data: blob:; "
            "font-src * data: blob:; "
            "style-src 'self' 'unsafe-inline' data: blob: http: https:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: http: https:; "
            "connect-src * data: blob:; "
            "frame-src * data: blob: http: https:; "
            "worker-src 'self' data: blob:; "
            "form-action *; "
            "base-uri 'self'; "
            "frame-ancestors 'self';"
        ),
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    }


def build_runtime_html_preview(
    *,
    storage_path: str,
    title: str,
    asset_url_resolver: Callable[[str], str],
) -> str:
    raw_html = Path(storage_path).read_text(encoding="utf-8", errors="replace")
    return _prepare_runtime_html(
        raw_html,
        title=title,
        asset_url_resolver=asset_url_resolver,
    )


def _prepare_runtime_html(
    raw_html: str,
    *,
    title: str,
    asset_url_resolver: Callable[[str], str],
) -> str:
    cleaned_html = _strip_debug_traces(raw_html)
    rewritten_html = _rewrite_resource_urls(cleaned_html, asset_url_resolver)
    return _ensure_runtime_markers(rewritten_html, title=title)


def _strip_debug_traces(raw_html: str) -> str:
    stripped_html = _SOURCE_MAP_RE.sub("", raw_html)
    return _DEBUG_HTML_COMMENT_RE.sub("", stripped_html)


def _rewrite_resource_urls(raw_html: str, asset_url_resolver: Callable[[str], str]) -> str:
    def replace_attr(match: re.Match[str]) -> str:
        raw_value = (match.group("value") or "").strip()
        if not raw_value or raw_value.lower().startswith(_SKIP_RESOURCE_PREFIXES):
            resolved_value = raw_value
        else:
            resolved_value = asset_url_resolver(raw_value)
        return f'{match.group("prefix")}{match.group("quote")}{resolved_value}{match.group("quote")}'

    return _RESOURCE_ATTR_RE.sub(replace_attr, raw_html)


def _ensure_runtime_markers(raw_html: str, *, title: str) -> str:
    head_injection = [f'<meta name="{RUNTIME_HTML_PREVIEW_MARKER}" content="1" />']
    if title and not _TITLE_TAG_RE.search(raw_html):
        head_injection.append(f"<title>{html_lib.escape(title)}</title>")
    head_markup = "\n    ".join(head_injection)

    if not (_HTML_TAG_RE.search(raw_html) and _BODY_TAG_RE.search(raw_html)):
        safe_title = f"<title>{html_lib.escape(title)}</title>\n    " if title else ""
        return (
            "<!DOCTYPE html>\n"
            f'<html data-{RUNTIME_HTML_PREVIEW_MARKER}="1">\n'
            "  <head>\n"
            f"    {safe_title}<meta name=\"{RUNTIME_HTML_PREVIEW_MARKER}\" content=\"1\" />\n"
            "  </head>\n"
            f'  <body class="{RUNTIME_HTML_PREVIEW_MARKER}__content">\n'
            f"{raw_html}\n"
            "  </body>\n"
            "</html>"
        )

    runtime_html = _HTML_TAG_RE.sub(_inject_html_marker, raw_html, count=1)
    runtime_html = _HEAD_TAG_RE.sub(lambda match: f"{match.group(0)}\n    {head_markup}", runtime_html, count=1)
    runtime_html = _BODY_TAG_RE.sub(_inject_body_marker, runtime_html, count=1)
    return runtime_html


def _inject_html_marker(match: re.Match[str]) -> str:
    attrs = match.group("attrs") or ""
    if f'data-{RUNTIME_HTML_PREVIEW_MARKER}' in attrs:
        return match.group(0)
    return f'<html{attrs} data-{RUNTIME_HTML_PREVIEW_MARKER}="1">'


def _inject_body_marker(match: re.Match[str]) -> str:
    attrs = match.group("attrs") or ""
    if 'class="' in attrs or "class='" in attrs:
        replaced = re.sub(
            r'class=(["\'])(?P<value>.*?)\1',
            lambda class_match: (
                f'class={class_match.group(1)}'
                f'{class_match.group("value")} {RUNTIME_HTML_PREVIEW_MARKER}__content'
                f'{class_match.group(1)}'
            ),
            attrs,
            count=1,
        )
        return f"<body{replaced}>"
    return f'<body{attrs} class="{RUNTIME_HTML_PREVIEW_MARKER}__content">'
