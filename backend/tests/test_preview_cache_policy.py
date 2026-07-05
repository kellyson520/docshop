
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.preview_cache_policy import (
    PreviewCacheCandidate,
    is_safe_cache_path,
    score_cleanup_candidate,
    sort_cleanup_candidates,
)


def test_preview_cache_policy_prefers_old_large_failed_items():
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    hot_recent = PreviewCacheCandidate(
        file_id="hot",
        storage_bytes=5 * 1024 * 1024,
        status="ready",
        last_accessed_at=now - timedelta(hours=1),
        finished_at=now - timedelta(hours=2),
    )
    old_failed = PreviewCacheCandidate(
        file_id="old",
        storage_bytes=80 * 1024 * 1024,
        status="failed",
        last_accessed_at=now - timedelta(days=90),
        finished_at=now - timedelta(days=90),
    )

    assert score_cleanup_candidate(old_failed, now=now) > score_cleanup_candidate(hot_recent, now=now)
    assert sort_cleanup_candidates([hot_recent, old_failed], now=now)[0].file_id == "old"


def test_preview_cache_policy_safe_path_guard(tmp_path):
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    inside = cache_root / "file-a"
    outside = tmp_path / "uploads" / "file-a"
    outside.parent.mkdir()

    assert is_safe_cache_path(inside, [cache_root]) is True
    assert is_safe_cache_path(outside, [cache_root]) is False
