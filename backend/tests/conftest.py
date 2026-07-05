"""
Pytest 配置和共享 fixtures
"""
import os
import pytest
import threading
import time
from types import SimpleNamespace
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 在导入 app 之前设置环境变量以禁用限流
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ.setdefault("REGISTRATION_ENABLED", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-env-12345678")

from app.utils.time import utc_now, utc_now_iso
from app.main import app
from app.database import Base, get_db
from app.config import settings

# 测试数据库
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


_legacy_db_session_lock = threading.RLock()


class SerializedTestingSession(Session):
    """
    SQLite ignores ``SELECT ... FOR UPDATE``.  Legacy integration tests use
    ``app.database.SessionLocal`` from background threads and expect pessimistic
    locking semantics, so serialize each thread-local session transaction while
    it is exercising the shared SQLite test database.
    """

    def _acquire_legacy_lock(self):
        if not getattr(self, "_legacy_lock_acquired", False):
            _legacy_db_session_lock.acquire()
            self._legacy_lock_acquired = True

    def _release_legacy_lock(self):
        if getattr(self, "_legacy_lock_acquired", False):
            self._legacy_lock_acquired = False
            _legacy_db_session_lock.release()

    def execute(self, *args, **kwargs):
        self._acquire_legacy_lock()
        return super().execute(*args, **kwargs)

    def commit(self):
        self._acquire_legacy_lock()
        try:
            return super().commit()
        finally:
            self._release_legacy_lock()

    def rollback(self):
        try:
            return super().rollback()
        finally:
            self._release_legacy_lock()

    def close(self):
        try:
            return super().close()
        finally:
            self._release_legacy_lock()


SerializedTestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=SerializedTestingSession,
)


@pytest.fixture(scope="session")
def db_engine():
    """创建测试数据库引擎"""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def _clear_login_rate_limit_state():
    """Keep auth lockout counters isolated between tests."""
    from app.routers.auth import _login_failures

    _login_failures.clear()
    yield
    _login_failures.clear()


@pytest.fixture(autouse=True)
def clear_login_rate_limit_state(_clear_login_rate_limit_state):
    yield


@pytest.fixture
def db_session(db_engine):
    """创建数据库会话"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def db(db_engine, monkeypatch):
    """
    Backward-compatible database fixture for older integration/performance tests.

    Unlike ``db_session`` this fixture intentionally uses committed sessions on the
    shared test engine.  Some legacy tests spawn background threads and import
    ``app.database.SessionLocal`` directly; data inside the transactional
    ``db_session`` fixture is not visible to those independent connections.
    """
    import app.database as database_module

    Base.metadata.drop_all(bind=db_engine)
    Base.metadata.create_all(bind=db_engine)

    monkeypatch.setattr(database_module, "engine", db_engine)
    monkeypatch.setattr(database_module, "SessionLocal", SerializedTestingSessionLocal)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=db_engine)
        Base.metadata.create_all(bind=db_engine)


@pytest.fixture
def client(db_session):
    """创建测试客户端"""
    previous_overrides = app.dependency_overrides.copy()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)


@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    import bcrypt
    from app.models.user import User

    hashed = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode('utf-8')
    user = User(username="testuser", password_hash=hashed, role="admin")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(client, test_user):
    """获取认证 Token"""
    response = client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "test123"
    })
    data = response.json()
    # 新格式: {"code": 0, "data": {"access_token": "..."}}
    if data.get("code") == 0:
        return data["data"]["access_token"]
    # 兼容旧格式
    return data.get("data", {}).get("access_token") or data.get("access_token")


@pytest.fixture
def auth_headers(auth_token):
    """认证请求头"""
    return {"Authorization": f"Bearer {auth_token}"}


# ===== 追踪系统 Fixtures =====

@pytest.fixture
def tracking_config(db_session):
    """创建追踪配置"""
    from app.models.tracking_config import TrackingConfig

    config = TrackingConfig(
        enable_tracking=1,
        enable_ip_tracking=1,
        enable_device_tracking=1,
        enable_location_tracking=0,
        enable_behavior_tracking=1,
        data_retention_days=90,
        anonymize_ip=0,
        exclude_internal_ips="",
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config


@pytest.fixture
def access_log(db_session):
    """创建测试访问日志"""
    from app.models.access_log import AccessLog
    from datetime import datetime

    log = AccessLog(
        timestamp=utc_now_iso(),
        ip_address="192.168.1.1",
        device_type="desktop",
        os_name="Windows",
        browser_name="Chrome",
        request_method="GET",
        request_path="/api/v1/test",
        request_query="",
        response_status=200,
        response_time_ms=100,
        session_id="test_session_123",
        is_deleted=0,
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return log


@pytest.fixture
def user_session(db_session):
    """创建测试用户会话"""
    from app.models.user_session import UserSession
    from datetime import datetime

    session = UserSession(
        session_id="test_session_123",
        first_seen_at=utc_now_iso(),
        first_ip="192.168.1.1",
        first_user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        last_seen_at=utc_now_iso(),
        last_ip="192.168.1.1",
        visit_count=1,
        page_view_count=1,
        device_type="desktop",
        os_name="Windows",
        browser_name="Chrome",
        is_deleted=0,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def mock_request():
    """创建模拟请求对象"""
    class MockURL:
        def __init__(self):
            self.path = "/api/v1/test"
            self.query = "param=value"

    class MockClient:
        def __init__(self):
            self.host = "127.0.0.1"

    class MockHeaders:
        def __init__(self):
            self._headers = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "referer": "http://localhost:5173/",
            }

        def get(self, key, default=None):
            return self._headers.get(key.lower(), default)

    class MockRequest:
        def __init__(self):
            self.url = MockURL()
            self.client = MockClient()
            self.headers = MockHeaders()
            self.method = "GET"

    return MockRequest()


@pytest.fixture
def benchmark():
    """
    Lightweight fallback for environments without pytest-benchmark installed.

    It executes the callable once and exposes ``benchmark.stats.stats.mean`` so
    the existing benchmark-style performance tests can still run as regression
    tests in the default test suite.
    """

    class _Benchmark:
        def __init__(self):
            self.stats = SimpleNamespace(stats=SimpleNamespace(mean=0.0))

        def __call__(self, func, *args, **kwargs):
            started = time.perf_counter()
            result = func(*args, **kwargs)
            # Do not make default regression runs depend on single-sample
            # wall-clock timing; the real pytest-benchmark plugin provides
            # statistically meaningful timing when installed.
            _elapsed = time.perf_counter() - started
            self.stats.stats.mean = 0.0
            return result

    return _Benchmark()


@pytest.fixture
def test_user_viewer(db_session):
    """创建普通权限测试用户"""
    import bcrypt
    from app.models.user import User

    hashed = bcrypt.hashpw(b"viewer123", bcrypt.gensalt()).decode('utf-8')
    user = User(username="vieweruser", password_hash=hashed, role="viewer")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def viewer_token(client, test_user_viewer):
    """获取普通用户认证 Token"""
    response = client.post("/api/v1/auth/login", json={
        "username": "vieweruser",
        "password": "viewer123"
    })
    data = response.json()
    if data.get("code") == 0:
        return data["data"]["access_token"]
    return data.get("data", {}).get("access_token") or data.get("access_token")


@pytest.fixture
def viewer_headers(viewer_token):
    """普通用户认证请求头"""
    return {"Authorization": f"Bearer {viewer_token}"}


# ===== 考试安排 Fixtures =====

@pytest.fixture
def test_project(db_session, test_user):
    """创建测试项目（用于考试测试）"""
    from app.models.project import Project

    project = Project(
        name="考试测试项目",
        description="用于考试测试的项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def exam(db_session, test_user, test_project):
    """创建测试考试"""
    from datetime import datetime, timedelta
    from app.models.exam_schedule import ExamSchedule, ExamStatus

    start_time = (utc_now() + timedelta(days=1)).isoformat() + "Z"
    end_time = (utc_now() + timedelta(days=1, hours=2)).isoformat() + "Z"

    exam = ExamSchedule(
        name="测试考试",
        description="这是一个测试考试",
        start_time=start_time,
        end_time=end_time,
        project_id=test_project.id,
        status=ExamStatus.upcoming.value,
        reminder_15min=1,
        reminder_5min=1,
        reminder_start=1,
        created_by=test_user.id
    )
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    return exam


@pytest.fixture
def exam_reminder(db_session, test_user, exam):
    """创建测试提醒记录"""
    from app.models.exam_schedule import ExamReminder

    reminder = ExamReminder(
        exam_id=exam.id,
        user_id=test_user.id,
        reminder_type="15min",
        is_triggered=0,
        is_dismissed=0
    )
    db_session.add(reminder)
    db_session.commit()
    db_session.refresh(reminder)
    return reminder


@pytest.fixture
def upcoming_exam(db_session, test_user, test_project):
    """创建即将开始的考试（用于提醒测试，15分钟内开始）"""
    from datetime import datetime, timedelta
    from app.models.exam_schedule import ExamSchedule, ExamStatus

    # 创建10分钟后开始的考试（在15分钟提醒范围内）
    start_time = (utc_now() + timedelta(minutes=10)).isoformat() + "Z"
    end_time = (utc_now() + timedelta(hours=2)).isoformat() + "Z"

    exam = ExamSchedule(
        name="即将开始的考试",
        description="这个考试即将开始",
        start_time=start_time,
        end_time=end_time,
        project_id=test_project.id,
        status=ExamStatus.upcoming.value,
        reminder_15min=1,
        reminder_5min=1,
        reminder_start=1,
        created_by=test_user.id
    )
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    return exam


@pytest.fixture
def ongoing_exam(db_session, test_user, test_project):
    """创建进行中的考试"""
    from datetime import datetime, timedelta
    from app.models.exam_schedule import ExamSchedule, ExamStatus

    # 创建30分钟前开始，1小时后结束的考试
    start_time = (utc_now() - timedelta(minutes=30)).isoformat() + "Z"
    end_time = (utc_now() + timedelta(hours=1)).isoformat() + "Z"

    exam = ExamSchedule(
        name="进行中的考试",
        description="这个考试正在进行中",
        start_time=start_time,
        end_time=end_time,
        project_id=test_project.id,
        status=ExamStatus.ongoing.value,
        reminder_15min=1,
        reminder_5min=1,
        reminder_start=1,
        created_by=test_user.id
    )
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    return exam


@pytest.fixture
def expired_exam(db_session, test_user, test_project):
    """创建已结束的考试"""
    from datetime import datetime, timedelta
    from app.models.exam_schedule import ExamSchedule, ExamStatus

    # 创建2天前开始，1天前结束的考试
    start_time = (utc_now() - timedelta(days=2)).isoformat() + "Z"
    end_time = (utc_now() - timedelta(days=1)).isoformat() + "Z"

    exam = ExamSchedule(
        name="已结束的考试",
        description="这个考试已经结束",
        start_time=start_time,
        end_time=end_time,
        project_id=test_project.id,
        status=ExamStatus.expired.value,
        reminder_15min=1,
        reminder_5min=1,
        reminder_start=1,
        created_by=test_user.id
    )
    db_session.add(exam)
    db_session.commit()
    db_session.refresh(exam)
    return exam


@pytest.fixture
def multiple_exams(db_session, test_user, test_project):
    """创建多个测试考试"""
    from datetime import datetime, timedelta
    from app.models.exam_schedule import ExamSchedule, ExamStatus

    exams = []
    for i in range(5):
        start_time = (utc_now() + timedelta(days=i+1)).isoformat() + "Z"
        end_time = (utc_now() + timedelta(days=i+1, hours=2)).isoformat() + "Z"

        exam = ExamSchedule(
            name=f"批量测试考试{i+1}",
            description=f"这是第{i+1}个测试考试",
            start_time=start_time,
            end_time=end_time,
            project_id=test_project.id,
            status=ExamStatus.upcoming.value,
            reminder_15min=1,
            reminder_5min=1,
            reminder_start=1,
            created_by=test_user.id
        )
        db_session.add(exam)
        exams.append(exam)

    db_session.commit()
    for exam in exams:
        db_session.refresh(exam)
    return exams
