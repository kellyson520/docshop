from app.database import _access_log_additive_statements
from app.models.access_log import AccessLog
import warnings
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.routers import tracking_admin
from app.routers.tracking_admin import get_access_logs


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
    assert "ALTER TABLE access_logs ADD COLUMN referer VARCHAR(255)" not in statements


def test_access_log_additive_statements_skip_existing_referer_columns():
    statements = _access_log_additive_statements(
        {
            "id", "timestamp", "referer", "referer_host", "referer_domain", "referer_type",
            "visitor_id", "is_page_view", "geo_latitude", "geo_longitude", "geo_accuracy",
            "client_timezone", "client_language",
            "device_model_code", "device_model_name", "device_brand_name", "device_display_name",
        }
    )

    assert statements == []


def test_access_log_from_request_persists_normalized_referer_fields():
    request = SimpleNamespace(
        headers={
            "referer": "https://www.limestart.cn/path?q=1",
            "x-forwarded-for": "127.0.0.1",
        },
        url=SimpleNamespace(path="/docs", query="q=1"),
        method="GET",
        client=SimpleNamespace(host="127.0.0.1"),
    )

    log = AccessLog.from_request(
        request,
        referer_info={
            "referer_host": "www.limestart.cn",
            "referer_domain": "limestart.cn",
            "referer_type": "external",
        },
    )

    assert log.referer == "https://www.limestart.cn/path?q=1"
    assert log.referer_host == "www.limestart.cn"
    assert log.referer_domain == "limestart.cn"
    assert log.referer_type == "external"


def test_access_log_timestamp_helpers_do_not_emit_utcnow_deprecation_warning():
    request = SimpleNamespace(
        headers={"x-forwarded-for": "127.0.0.1"},
        url=SimpleNamespace(path="/docs", query=""),
        method="GET",
        client=SimpleNamespace(host="127.0.0.1"),
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        log = AccessLog.from_request(request)
        log.soft_delete()

    utcnow_warnings = [
        warning for warning in caught
        if issubclass(warning.category, DeprecationWarning) and "utcnow" in str(warning.message)
    ]

    assert log.timestamp.endswith("Z")
    assert log.deleted_at.endswith("Z")
    assert utcnow_warnings == []



def test_access_log_to_dict_includes_precise_tracking_fields():
    log = AccessLog(
        id="log-geo-1",
        timestamp="2026-06-23T10:00:00Z",
        ip_address="127.0.0.1",
        visitor_id="visitor-123",
        is_page_view=1,
        geo_latitude=39.9042,
        geo_longitude=116.4074,
        geo_accuracy=8.5,
        client_timezone="Asia/Shanghai",
        client_language="zh-CN",
    )

    data = log.to_dict()

    assert data["visitor_id"] == "visitor-123"
    assert data["is_page_view"] is True
    assert data["geo_latitude"] == 39.9042
    assert data["geo_longitude"] == 116.4074
    assert data["geo_accuracy"] == 8.5
    assert data["client_timezone"] == "Asia/Shanghai"
    assert data["client_language"] == "zh-CN"


def test_access_log_additive_statements_include_precise_tracking_columns():
    statements = _access_log_additive_statements({"id", "timestamp"})
    joined = "\n".join(statements)

    assert "ADD COLUMN visitor_id" in joined
    assert "ADD COLUMN is_page_view" in joined
    assert "ADD COLUMN geo_latitude" in joined
    assert "ADD COLUMN geo_longitude" in joined
    assert "ADD COLUMN geo_accuracy" in joined
    assert "ADD COLUMN client_timezone" in joined
    assert "ADD COLUMN client_language" in joined


def test_access_log_from_request_accepts_visitor_and_page_view_fields():
    request = SimpleNamespace(
        headers={"x-forwarded-for": "127.0.0.1", "user-agent": "pytest"},
        url=SimpleNamespace(path="/docs", query=""),
        method="GET",
        client=SimpleNamespace(host="127.0.0.1"),
    )

    log = AccessLog.from_request(
        request,
        session_id="session-123",
        visitor_id="visitor-123",
        is_page_view=True,
        client_info={"client_timezone": "Asia/Shanghai", "client_language": "zh-CN"},
    )

    assert log.visitor_id == "visitor-123"
    assert log.is_page_view == 1
    assert log.client_timezone == "Asia/Shanghai"
    assert log.client_language == "zh-CN"


def test_admin_access_logs_can_filter_page_views_and_visitor_id():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        db.add_all([
            AccessLog(
                id="page-view-log",
                timestamp="2026-06-23T10:00:00Z",
                ip_address="127.0.0.1",
                visitor_id="visitor-a",
                is_page_view=1,
                request_path="/share/demo",
                response_status=200,
                response_time_ms=12,
            ),
            AccessLog(
                id="api-log",
                timestamp="2026-06-23T10:00:01Z",
                ip_address="127.0.0.1",
                visitor_id="visitor-a",
                is_page_view=0,
                request_path="/api/v1/projects",
                response_status=200,
                response_time_ms=8,
            ),
            AccessLog(
                id="other-visitor-log",
                timestamp="2026-06-23T10:00:02Z",
                ip_address="127.0.0.1",
                visitor_id="visitor-b",
                is_page_view=1,
                request_path="/",
                response_status=200,
                response_time_ms=9,
            ),
        ])
        db.commit()

        result = get_access_logs(
            page=1,
            page_size=50,
            ip=None,
            user_id=None,
            device_type=None,
            page_views_only=1,
            visitor_id="visitor-a",
            start_date=None,
            end_date=None,
            db=db,
            current_user=SimpleNamespace(id="admin"),
        )

        data = result.data
        assert data["total"] == 1
        assert [item["id"] for item in data["items"]] == ["page-view-log"]
        assert data["items"][0]["is_page_view"] is True
    finally:
        db.close()


def test_admin_access_logs_include_per_row_visitor_ip_context():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        db.add(
            AccessLog(
                id="page-view-log",
                timestamp="2026-06-23T10:00:00Z",
                ip_address="127.0.0.1",
                visitor_id="visitor-a",
                is_page_view=1,
                request_path="/share/demo",
                response_status=200,
                response_time_ms=12,
                session_id="session-a",
            )
        )
        db.commit()

        result = get_access_logs(
            page=1,
            page_size=50,
            ip=None,
            user_id=None,
            device_type=None,
            page_views_only=1,
            visitor_id="visitor-a",
            start_date=None,
            end_date=None,
            db=db,
            current_user=SimpleNamespace(id="admin"),
        )

        data = result.data
        assert data["items"][0]["id"] == "page-view-log"
        assert data["items"][0]["visitor_ip_context"]["source"] == "access_log_visitor_ip"
        assert data["items"][0]["visitor_ip_context"]["ip"] == "127.0.0.1"
        assert data["items"][0]["visitor_ip_context"]["scope"] == "loopback"
        assert "server_ip_context" not in data
    finally:
        db.close()


def test_access_log_to_dict_includes_resolved_mobile_model_fields():
    log = AccessLog(
        id="log-mobile-model-1",
        timestamp="2026-06-23T11:00:00Z",
        ip_address="127.0.0.1",
        device_model_code="ANA-AL00",
        device_model_name="P40",
        device_brand_name="Huawei",
        device_display_name="Huawei P40 / ANA-AL00",
    )

    data = log.to_dict()

    assert data["device_model_code"] == "ANA-AL00"
    assert data["device_model_name"] == "P40"
    assert data["device_brand_name"] == "Huawei"
    assert data["device_display_name"] == "Huawei P40 / ANA-AL00"


def test_access_log_additive_statements_include_resolved_mobile_model_columns():
    statements = _access_log_additive_statements({"id", "timestamp"})
    joined = "\n".join(statements)

    assert "ADD COLUMN device_model_code" in joined
    assert "ADD COLUMN device_model_name" in joined
    assert "ADD COLUMN device_brand_name" in joined
    assert "ADD COLUMN device_display_name" in joined


def test_access_log_from_request_accepts_resolved_mobile_model_fields():
    request = SimpleNamespace(
        headers={"x-forwarded-for": "127.0.0.1", "user-agent": "pytest"},
        url=SimpleNamespace(path="/docs", query=""),
        method="GET",
        client=SimpleNamespace(host="127.0.0.1"),
    )

    log = AccessLog.from_request(
        request,
        device_info={
            "device_type": "mobile",
            "device_brand": "Huawei",
            "device_model": "ANA-AL00",
            "device_model_code": "ANA-AL00",
            "device_model_name": "P40",
            "device_brand_name": "Huawei",
            "device_display_name": "Huawei P40 / ANA-AL00",
        },
    )

    assert log.device_model_code == "ANA-AL00"
    assert log.device_model_name == "P40"
    assert log.device_brand_name == "Huawei"
    assert log.device_display_name == "Huawei P40 / ANA-AL00"

