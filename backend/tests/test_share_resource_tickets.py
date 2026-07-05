from app.services.share_tab_grant_service import issue_share_tab_grant, release_share_tab_grant
from app.services.resource_access_grant_service import issue_resource_access_grant


def test_issue_and_validate_share_resource_ticket(db_session):
    from app.services.share_resource_ticket_service import (
        issue_share_resource_ticket,
        validate_share_resource_ticket,
    )

    grant_token = issue_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        ttl_seconds=45,
    )

    ticket = issue_share_resource_ticket(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        raw_grant=grant_token,
        kind="preview",
        file_id="file-1",
        ttl_seconds=60,
    )

    claims = validate_share_resource_ticket(
        db_session,
        ticket,
        share_token="share-1",
        kind="preview",
        file_id="file-1",
    )

    assert claims is not None
    assert claims["share_token"] == "share-1"
    assert claims["tab_id"] == "tab-a"
    assert claims["grant_id"]
    assert claims["kind"] == "preview"
    assert claims["file_id"] == "file-1"


def test_share_resource_ticket_rejects_wrong_asset(db_session):
    from app.services.share_resource_ticket_service import (
        issue_share_resource_ticket,
        validate_share_resource_ticket,
    )

    grant_token = issue_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        ttl_seconds=45,
    )

    ticket = issue_share_resource_ticket(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        raw_grant=grant_token,
        kind="preview_asset",
        file_id="file-1",
        asset_id="asset-1",
        ttl_seconds=60,
    )

    claims = validate_share_resource_ticket(
        db_session,
        ticket,
        share_token="share-1",
        kind="preview_asset",
        file_id="file-1",
        asset_id="asset-2",
    )

    assert claims is None


def test_released_share_tab_grant_invalidates_existing_resource_ticket(db_session):
    from app.services.share_resource_ticket_service import (
        issue_share_resource_ticket,
        validate_share_resource_ticket,
    )

    grant_token = issue_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        ttl_seconds=45,
    )

    ticket = issue_share_resource_ticket(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        raw_grant=grant_token,
        kind="download_original",
        file_id="file-1",
        version_id="version-1",
        ttl_seconds=60,
    )

    released = release_share_tab_grant(
        db_session,
        share_token="share-1",
        tab_id="tab-a",
        raw_grant=grant_token,
    )

    claims = validate_share_resource_ticket(
        db_session,
        ticket,
        share_token="share-1",
        kind="download_original",
        file_id="file-1",
        version_id="version-1",
    )

    assert released is True
    assert claims is None


def test_issue_and_validate_share_resource_ticket_from_resource_access_grant(db_session):
    from app.services.share_resource_ticket_service import (
        issue_share_resource_ticket,
        validate_share_resource_ticket,
    )

    grant_token = issue_resource_access_grant(
        db_session,
        share_token="legacy-public-share",
        resource_type="file",
        resource_id="file-1",
        tab_id="tab-a",
        ttl_seconds=45,
    )

    ticket = issue_share_resource_ticket(
        db_session,
        share_token="legacy-public-share",
        tab_id="tab-a",
        raw_grant=grant_token,
        kind="preview",
        file_id="file-1",
        access_resource_type="file",
        access_resource_id="file-1",
        ttl_seconds=60,
    )

    claims = validate_share_resource_ticket(
        db_session,
        ticket,
        share_token="legacy-public-share",
        kind="preview",
        file_id="file-1",
    )

    assert claims is not None
    assert claims["share_token"] == "legacy-public-share"
    assert claims["tab_id"] == "tab-a"
    assert claims["grant_id"]
    assert claims["grant_kind"] == "resource_access"
    assert claims["access_resource_type"] == "file"
    assert claims["access_resource_id"] == "file-1"
