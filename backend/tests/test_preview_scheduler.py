
from datetime import datetime, timedelta, timezone

from app.services.preview_scheduler import PreviewJobContext, score_preview_job, sort_preview_jobs


def test_preview_scheduler_prioritizes_small_recent_files_over_large_old_files():
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    large_old = PreviewJobContext(file_id="large", file_size=80 * 1024 * 1024, updated_at=now - timedelta(days=20))
    small_new = PreviewJobContext(file_id="small", file_size=300 * 1024, updated_at=now - timedelta(minutes=5))

    assert score_preview_job(small_new, now=now) > score_preview_job(large_old, now=now)
    assert [j.file_id for j in sort_preview_jobs([large_old, small_new], now=now)] == ["small", "large"]


def test_preview_scheduler_penalizes_failed_jobs_and_improves_recent_access():
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    failed = PreviewJobContext(file_id="failed", file_size=1024, failure_count=3, last_accessed_at=now - timedelta(minutes=1))
    clean = PreviewJobContext(file_id="clean", file_size=1024, failure_count=0, last_accessed_at=now - timedelta(days=3))

    assert score_preview_job(clean, now=now) > score_preview_job(failed, now=now)


def test_preview_scheduler_keeps_same_project_from_monopolizing_queue():
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    jobs = [
        PreviewJobContext(file_id="a1", project_id="A", file_size=1024),
        PreviewJobContext(file_id="a2", project_id="A", file_size=1024),
        PreviewJobContext(file_id="b1", project_id="B", file_size=1024),
    ]

    ordered = sort_preview_jobs(jobs, recent_project_ids=["A", "A"], now=now)

    assert ordered[0].file_id == "b1"
