
"""Tiny relevance ranker for admin search without external services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Optional


@dataclass(frozen=True)
class SearchItem:
    id: str
    name: str = ""
    display_name: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = ""
    project_name: str = ""
    updated_at: Optional[datetime] = None
    popularity: int = 0
    payload: object = None


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def _now(now: Optional[datetime]) -> datetime:
    return now or datetime.now(timezone.utc)


def _recent_score(updated_at: Optional[datetime], now: datetime) -> float:
    if not updated_at:
        return 0.0
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - updated_at).total_seconds() / 86400)
    return max(0.0, 20.0 - min(age_days, 30.0) * (20.0 / 30.0))


def _text_score(text: str, keyword: str, exact: float, prefix: float, contains: float) -> float:
    value = _norm(text)
    key = _norm(keyword)
    if not value or not key:
        return 0.0
    if value == key:
        return exact
    if value.startswith(key):
        return prefix
    if key in value:
        return contains
    return 0.0


def score_search_item(item: SearchItem, keyword: str, *, now: Optional[datetime] = None) -> float:
    key = _norm(keyword)
    if not key:
        return 0.0
    current = _now(now)
    score = 0.0
    score += _text_score(item.name, key, 100, 80, 60)
    score += _text_score(item.display_name, key, 90, 70, 50)
    score += max((_text_score(tag, key, 40, 34, 26) for tag in item.tags), default=0.0)
    score += _text_score(item.category, key, 30, 24, 18)
    score += _text_score(item.project_name, key, 30, 24, 18)
    score += _recent_score(item.updated_at, current)
    score += min(20.0, max(0, item.popularity or 0) * 2.0)
    return score


def rank_search_items(items: Iterable[SearchItem], keyword: str, *, now: Optional[datetime] = None) -> list[SearchItem]:
    current = _now(now)
    return sorted(
        list(items),
        key=lambda item: (
            -score_search_item(item, keyword, now=current),
            -(item.updated_at.timestamp() if item.updated_at else 0),
            _norm(item.name),
            item.id,
        ),
    )
