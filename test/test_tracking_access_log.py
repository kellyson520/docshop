from app.database import _access_log_additive_statements
from app.models.access_log import AccessLog


def test_access_log_to_dict_includes_normalized_referer_fields():
    log = AccessLog(
        id="log-1",
        timestamp="2026-06-16T12:00:00Z",
        ip_address="127.0.0.1",
        referer="https://www.limestart.cn/",
        referer_host="www.limestart.cn",
        referer_domain="limestart.cn",
        referer_type="external",
    )

    data = log.to_dict()

    assert data["referer"] == "https://www.limestart.cn/"
    assert data["referer_host"] == "www.limestart.cn"
    assert data["referer_domain"] == "limestart.cn"
    assert data["referer_type"] == "external"


def test_access_log_additive_statements_only_add_missing_columns():
    statements = _access_log_additive_statements({"id", "timestamp", "referer"})

    assert "ALTER TABLE access_logs ADD COLUMN referer_host VARCHAR(255)" in statements
    assert "ALTER TABLE access_logs ADD COLUMN referer_domain VARCHAR(255)" in statements
    assert "ALTER TABLE access_logs ADD COLUMN referer_type VARCHAR(32)" in statements
