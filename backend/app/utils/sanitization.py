import html
import re
from typing import Optional


_DANGEROUS_BLOCK_RE = re.compile(
    r"<\s*(script|iframe|object|embed|style|svg)\b[^>]*>.*?<\s*/\s*\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]*>")
_EVENT_HANDLER_RE = re.compile(
    r"\s+on[a-zA-Z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)",
    flags=re.IGNORECASE,
)
_JS_SCHEME_RE = re.compile(r"javascript\s*:", flags=re.IGNORECASE)
_ALERT_CALL_RE = re.compile(r"alert\s*\([^)]*\)", flags=re.IGNORECASE)


def sanitize_user_text(value: Optional[str]) -> Optional[str]:
    """Strip active HTML/JS from short user-facing text fields."""
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return cleaned

    # First, unescape any pre-existing HTML entities to normalize the input
    # and prevent double-escaping. e.g. "&lt;script&gt;" becomes "<script>"
    cleaned = html.unescape(cleaned)

    # Then apply regex cleanup to remove dangerous patterns from normalized text
    cleaned = _DANGEROUS_BLOCK_RE.sub("", cleaned)
    cleaned = _EVENT_HANDLER_RE.sub("", cleaned)
    cleaned = _JS_SCHEME_RE.sub("", cleaned)
    cleaned = _ALERT_CALL_RE.sub("", cleaned)
    cleaned = _TAG_RE.sub("", cleaned)

    # Finally, escape any remaining special characters for safe text output
    cleaned = html.escape(cleaned, quote=True)
    return cleaned.strip()
