from app.services.resource_access_grant_service import (
    heartbeat_resource_access_grant,
    issue_resource_access_grant,
    release_resource_access_grant,
    validate_resource_access_grant,
)


def test_issue_validate_heartbeat_and_release_resource_access_grant(db_session):
    token = issue_resource_access_grant(
        db_session,
        share_token="legacy-public-token",
        resource_type="file",
        resource_id="file-1",
        tab_id="tab-a",
        ttl_seconds=45,
    )

    grant = validate_resource_access_grant(
        db_session,
        share_token="legacy-public-token",
        resource_type="file",
        resource_id="file-1",
        tab_id="tab-a",
        raw_grant=token,
    )

    assert grant is not None
    original_expiry = grant.expires_at

    refreshed = heartbeat_resource_access_grant(
        db_session,
        share_token="legacy-public-token",
        resource_type="file",
        resource_id="file-1",
        tab_id="tab-a",
        raw_grant=token,
        ttl_seconds=90,
    )

    assert refreshed is not None
    assert refreshed.expires_at > original_expiry

    released = release_resource_access_grant(
        db_session,
        share_token="legacy-public-token",
        resource_type="file",
        resource_id="file-1",
        tab_id="tab-a",
        raw_grant=token,
    )

    assert released is True
    assert validate_resource_access_grant(
        db_session,
        share_token="legacy-public-token",
        resource_type="file",
        resource_id="file-1",
        tab_id="tab-a",
        raw_grant=token,
    ) is None


def test_resource_access_grant_rejects_wrong_resource_or_tab(db_session):
    token = issue_resource_access_grant(
        db_session,
        share_token="legacy-public-token",
        resource_type="project",
        resource_id="project-1",
        tab_id="tab-a",
        ttl_seconds=45,
    )

    assert validate_resource_access_grant(
        db_session,
        share_token="legacy-public-token",
        resource_type="project",
        resource_id="project-1",
        tab_id="tab-b",
        raw_grant=token,
    ) is None

    assert validate_resource_access_grant(
        db_session,
        share_token="legacy-public-token",
        resource_type="file",
        resource_id="project-1",
        tab_id="tab-a",
        raw_grant=token,
    ) is None

    assert validate_resource_access_grant(
        db_session,
        share_token="legacy-public-token",
        resource_type="project",
        resource_id="project-2",
        tab_id="tab-a",
        raw_grant=token,
    ) is None
