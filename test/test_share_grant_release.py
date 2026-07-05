import json
from types import SimpleNamespace


def test_release_share_access_accepts_beacon_body_when_headers_are_unavailable(monkeypatch):
    from app.routers import share

    captured = {}
    token_model = SimpleNamespace(token="share-token", password_hash="hashed-password")

    monkeypatch.setattr(
        share,
        "_resolve_share_context",
        lambda share_token, db, action="view", consume=False: {"share_token": token_model},
    )

    def fake_release_share_tab_grant(db, *, share_token, tab_id, raw_grant):
      captured.update({
          "share_token": share_token,
          "tab_id": tab_id,
          "raw_grant": raw_grant,
      })
      return True

    monkeypatch.setattr(share, "release_share_tab_grant", fake_release_share_tab_grant)

    response = share.release_share_access(
        "share-token",
        request=SimpleNamespace(headers={}),
        body={
            "tab_id": "share-tab-1",
            "grant_token": "grant-1",
        },
        db=object(),
        x_share_tab_id=None,
        x_share_grant=None,
    )

    assert captured == {
        "share_token": "share-token",
        "tab_id": "share-tab-1",
        "raw_grant": "grant-1",
    }
    payload = json.loads(response.body.decode("utf-8"))
    assert payload["data"]["released"] is True
