
from fastapi import HTTPException, status

from app.models.share_token import ShareToken
from app.services.share_token_service import assert_share_token_allowed, consume_share_token


def test_share_token_blocks_after_view_limit():
    token = ShareToken(
        token='limited-view-token',
        resource_type='project',
        resource_id='project-1',
        max_views=1,
        view_count=1,
        max_downloads=0,
        download_count=0,
        allow_download=1,
        is_active=1,
        created_by='user-1',
    )

    try:
        assert_share_token_allowed(token, action='view')
    except HTTPException as exc:
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert 'view limit' in exc.detail
    else:
        raise AssertionError('expected view limit rejection')


def test_share_token_blocks_download_when_download_disabled():
    token = ShareToken(
        token='no-download-token',
        resource_type='file',
        resource_id='file-1',
        allow_download=0,
        is_active=1,
        created_by='user-1',
    )

    try:
        assert_share_token_allowed(token, action='download')
    except HTTPException as exc:
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert 'download disabled' in exc.detail
    else:
        raise AssertionError('expected download disabled rejection')


def test_consume_share_token_increments_only_relevant_counter():
    token = ShareToken(
        token='count-token',
        resource_type='project',
        resource_id='project-1',
        view_count=0,
        download_count=0,
        is_active=1,
        created_by='user-1',
    )

    consume_share_token(token, action='view')
    assert token.view_count == 1
    assert token.download_count == 0

    consume_share_token(token, action='download')
    assert token.view_count == 1
    assert token.download_count == 1
