
from datetime import datetime, timedelta, timezone

from app.services.search_ranker import SearchItem, rank_search_items, score_search_item


def test_search_ranker_weights_exact_prefix_contains_and_metadata():
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    exact = SearchItem(id="exact", name="budget", display_name="budget", updated_at=now)
    prefix = SearchItem(id="prefix", name="budget-june", updated_at=now)
    contains = SearchItem(id="contains", name="june-budget", updated_at=now)
    tag_hit = SearchItem(id="tag", name="other", tags=["budget"], updated_at=now)

    assert score_search_item(exact, "budget", now=now) > score_search_item(prefix, "budget", now=now)
    assert score_search_item(prefix, "budget", now=now) > score_search_item(contains, "budget", now=now)
    assert score_search_item(contains, "budget", now=now) > score_search_item(tag_hit, "budget", now=now)


def test_search_ranker_orders_by_score_then_recent_then_name():
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    items = [
        SearchItem(id="old", name="exam schedule", updated_at=now - timedelta(days=10)),
        SearchItem(id="new", name="exam schedule", updated_at=now - timedelta(hours=1)),
        SearchItem(id="prefix", name="exam schedule new", updated_at=now - timedelta(days=1)),
    ]

    ordered = rank_search_items(items, "exam schedule", now=now)

    assert [item.id for item in ordered] == ["new", "old", "prefix"]
