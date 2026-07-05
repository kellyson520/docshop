
"""Low-cost preview cache cleanup scoring and safety helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class PreviewCacheCandidate:
    file_id: str
    storage_bytes: int = 0
    status: str = "missing"
    last_accessed_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


def _now(now: Optional[datetime]) -> datetime:
    return now or datetime.now(timezone.utc)


def _age_days(value: Optional[datetime], now: datetime, default: float = 365.0) -> float:
    if not value:
        return default
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0.0, (now - value).total_seconds() / 86400)


def score_cleanup_candidate(candidate: PreviewCacheCandidate, *, now: Optional[datetime] = None) -> float:
    current = _now(now)
    access_age = _age_days(candidate.last_accessed_at or candidate.finished_at, current)
    finish_age = _age_days(candidate.finished_at, current)
    size_mb = max(0.0, float(candidate.storage_bytes or 0) / (1024 * 1024))

    age_score = min(90.0, access_age * 1.2) + min(30.0, finish_age * 0.2)
    size_score = min(80.0, size_mb * 0.9)
    status_score = 45.0 if candidate.status in {"failed", "interrupted"} else 0.0
    hot_penalty = 50.0 if access_age < 1 else 20.0 if access_age < 7 else 0.0
    return age_score + size_score + status_score - hot_penalty


def sort_cleanup_candidates(candidates: Iterable[PreviewCacheCandidate], *, now: Optional[datetime] = None) -> list[PreviewCacheCandidate]:
    current = _now(now)
    return sorted(
        list(candidates),
        key=lambda item: (-score_cleanup_candidate(item, now=current), -int(item.storage_bytes or 0), item.file_id),
    )


def is_safe_cache_path(path: str | Path, allowed_roots: Iterable[str | Path]) -> bool:
    try:
        target = Path(path).resolve()
        for root in allowed_roots:
            resolved_root = Path(root).resolve()
            if target == resolved_root or resolved_root in target.parents:
                return True
        return False
    except OSError:
        return False
