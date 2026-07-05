from app.services.share_tab_grant_service import (
    heartbeat_share_tab_grant,
    issue_share_tab_grant,
    release_share_tab_grant,
    validate_share_tab_grant,
)


def test_issue_and_validate_share_tab_grant(db_session):
    token = issue_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        ttl_seconds=45,
    )

    grant = validate_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        raw_grant=token,
    )

    assert grant is not None
    assert grant.share_token == "share-1"
    assert grant.tab_id == "tab-a"


def test_validate_share_tab_grant_rejects_different_tab(db_session):
    token = issue_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        ttl_seconds=45,
    )

    grant = validate_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-b",
        raw_grant=token,
    )

    assert grant is None


def test_release_share_tab_grant_invalidates_future_validation(db_session):
    token = issue_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        ttl_seconds=45,
    )

    released = release_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        raw_grant=token,
    )

    assert released is True
    assert validate_share_tab_grant(db_session, "share-1", "tab-a", token) is None


def test_heartbeat_extends_share_tab_grant_expiry(db_session):
    token = issue_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        ttl_seconds=5,
    )
    grant = validate_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        raw_grant=token,
    )

    assert grant is not None
    before = grant.expires_at

    refreshed = heartbeat_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        raw_grant=token,
        ttl_seconds=45,
    )

    assert refreshed is not None
    assert refreshed.expires_at > before
