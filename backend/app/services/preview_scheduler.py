
"""Lightweight preview queue priority scoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional


@dataclass(frozen=True)
class PreviewJobContext:
    file_id: str
    project_id: Optional[str] = None
    file_size: int = 0
    updated_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    failure_count: int = 0
    queued_at: Optional[datetime] = None


def _now(now: Optional[datetime]) -> datetime:
    return now or datetime.now(timezone.utc)


def _age_hours(value: Optional[datetime], now: datetime, default: float = 24 * 30) -> float:
    if not value:
        return default
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0.0, (now - value).total_seconds() / 3600)


def score_preview_job(job: PreviewJobContext, *, now: Optional[datetime] = None, recent_project_ids: Optional[Iterable[str]] = None) -> float:
    current = _now(now)
    size_mb = max(0.0, float(job.file_size or 0) / (1024 * 1024))
    size_score = max(0.0, 45.0 - min(size_mb, 90.0) * 0.5)

    update_age = _age_hours(job.updated_at, current)
    recent_update_score = max(0.0, 28.0 - min(update_age, 24 * 14) / 12.0)

    access_age = _age_hours(job.last_accessed_at, current, default=24 * 60)
    access_score = max(0.0, 20.0 - min(access_age, 24 * 30) / 36.0)

    queued_age = _age_hours(job.queued_at, current, default=0)
    aging_score = min(20.0, queued_age / 2.0)

    failure_penalty = min(60.0, max(0, job.failure_count or 0) * 22.0)

    project_penalty = 0.0
    if job.project_id and recent_project_ids:
        project_penalty = min(30.0, list(recent_project_ids).count(job.project_id) * 12.0)

    return size_score + recent_update_score + access_score + aging_score - failure_penalty - project_penalty


def sort_preview_jobs(jobs: Iterable[PreviewJobContext], *, now: Optional[datetime] = None, recent_project_ids: Optional[Iterable[str]] = None) -> list[PreviewJobContext]:
    current = _now(now)
    recent = list(recent_project_ids or [])
    return sorted(
        list(jobs),
        key=lambda job: (
            -score_preview_job(job, now=current, recent_project_ids=recent),
            job.queued_at or datetime.min.replace(tzinfo=timezone.utc),
            job.file_id,
        ),
    )
