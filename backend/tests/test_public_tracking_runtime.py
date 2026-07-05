from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.routers.tracking_ping import get_public_tracking_config


def _build_config(**overrides):
    return SimpleNamespace(
        enable_tracking=True,
        enable_device_tracking=True,
        enable_location_tracking=False,
        anonymize_ip=False,
        **overrides,
    )


def _build_request(*, device_id=None, session_id=None, cookies=None):
    return SimpleNamespace(
        state=SimpleNamespace(device_id=device_id, session_id=session_id),
        cookies=cookies or {},
    )


def test_tracking_config_returns_request_state_identifiers():
    request = _build_request(device_id="device-state", session_id="session-state")
    mock_db = MagicMock()
    mock_db.query.return_value.first.return_value = _build_config()

    with patch("app.routers.tracking_ping.SessionLocal", return_value=mock_db):
        response = get_public_tracking_config(request)

    payload = response.data
    assert payload["device_id"] == "device-state"
    assert payload["session_id"] == "session-state"


def test_tracking_config_reuses_existing_cookie_identifiers():
    request = _build_request(
        cookies={
            "device_id": "device-cookie",
            "session_id": "session-cookie",
        }
    )
    mock_db = MagicMock()
    mock_db.query.return_value.first.return_value = _build_config()

    with patch("app.routers.tracking_ping.SessionLocal", return_value=mock_db):
        response = get_public_tracking_config(request)

    payload = response.data
    assert payload["device_id"] == "device-cookie"
    assert payload["session_id"] == "session-cookie"
