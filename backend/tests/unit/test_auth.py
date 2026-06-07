"""
认证模块单元测试

测试认证相关功能，包括登录、注册、token验证等。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from jose import jwt

from app.deps.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    get_current_admin,
)
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.exceptions import AuthenticationError, ConflictError, ValidationError
from app.config import settings


# ===== Fixtures =====

@pytest.fixture
def mock_user():
    """创建模拟用户"""
    user = Mock()
    user.id = "test-user-id-123"
    user.username = "testuser"
    user.password_hash = get_password_hash("testpassword123")
    user.role = "user"
    user.created_at = datetime.utcnow().isoformat() + "Z"
    return user


@pytest.fixture
def mock_admin_user():
    """创建模拟管理员用户"""
    user = Mock()
    user.id = "admin-user-id-456"
    user.username = "adminuser"
    user.password_hash = get_password_hash("adminpassword123")
    user.role = "admin"
    user.created_at = datetime.utcnow().isoformat() + "Z"
    return user


@pytest.fixture
def valid_token(mock_user):
    """创建有效的测试token"""
    return create_access_token(data={"sub": mock_user.username})


@pytest.fixture
def expired_token(mock_user):
    """创建已过期的测试token"""
    expire = datetime.utcnow() - timedelta(minutes=1)
    to_encode = {"sub": mock_user.username, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


# ===== 密码处理测试 =====

class TestPasswordHandling:
    """测试密码哈希和验证功能"""

    def test_get_password_hash_generates_valid_hash(self):
        """测试密码哈希生成"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        # BCrypt hash should start with $2b$
        assert hashed.startswith("$2b$")

    def test_verify_password_with_correct_password(self):
        """测试使用正确密码验证"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_with_incorrect_password(self):
        """测试使用错误密码验证"""
        password = "testpassword123"
        wrong_password = "wrongpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_with_empty_password(self):
        """测试空密码验证"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password("", hashed) is False

    def test_different_passwords_generate_different_hashes(self):
        """测试不同密码生成不同哈希"""
        password1 = "password123"
        password2 = "password456"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2

    def test_same_password_generates_different_hashes(self):
        """测试相同密码生成不同哈希（盐值不同）"""
        password = "testpassword123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # 由于使用不同的盐值，哈希值应该不同
        assert hash1 != hash2
        # 但两者都应该能验证成功
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


# ===== Token 生成和验证测试 =====

class TestTokenHandling:
    """测试 JWT Token 生成和验证"""

    def test_create_access_token_with_default_expiry(self):
        """测试使用默认过期时间创建token"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # 解码验证
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_create_access_token_with_custom_expiry(self):
        """测试使用自定义过期时间创建token"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_create_access_token_contains_expiration(self):
        """测试token包含过期时间"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        exp_timestamp = payload["exp"]
        
        # 验证过期时间是未来的时间
        assert exp_timestamp > datetime.utcnow().timestamp()

    def test_decode_valid_token(self):
        """测试解码有效token"""
        data = {"sub": "testuser", "custom_claim": "value"}
        token = create_access_token(data)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        assert payload["sub"] == "testuser"
        assert payload["custom_claim"] == "value"

    def test_decode_token_with_wrong_secret(self):
        """测试使用错误密钥解码token"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        with pytest.raises(jwt.JWTError):
            jwt.decode(token, "wrong-secret-key", algorithms=["HS256"])

    def test_decode_expired_token(self, expired_token):
        """测试解码过期token"""
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, settings.SECRET_KEY, algorithms=["HS256"])


# ===== 用户认证依赖测试 =====

class TestGetCurrentUser:
    """测试获取当前用户功能"""

    def test_get_current_user_with_valid_token(self, mock_user):
        """测试使用有效token获取用户"""
        token = create_access_token(data={"sub": mock_user.username})
        
        # 模拟 credentials
        mock_credentials = Mock()
        mock_credentials.credentials = token
        
        # 模拟数据库查询
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = get_current_user(mock_credentials, mock_db)
        
        assert result == mock_user
        mock_db.query.assert_called_once()

    def test_get_current_user_with_invalid_token(self):
        """测试使用无效token获取用户"""
        mock_credentials = Mock()
        mock_credentials.credentials = "invalid.token.here"
        
        mock_db = Mock()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials, mock_db)
        
        assert exc_info.value.status_code == 401

    def test_get_current_user_with_expired_token(self, expired_token):
        """测试使用过期token获取用户"""
        mock_credentials = Mock()
        mock_credentials.credentials = expired_token
        
        mock_db = Mock()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials, mock_db)
        
        assert exc_info.value.status_code == 401

    def test_get_current_user_with_missing_sub(self):
        """测试token缺少sub字段"""
        # 创建没有sub的token
        expire = datetime.utcnow() + timedelta(minutes=30)
        token = jwt.encode({"exp": expire}, settings.SECRET_KEY, algorithm="HS256")
        
        mock_credentials = Mock()
        mock_credentials.credentials = token
        
        mock_db = Mock()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials, mock_db)
        
        assert exc_info.value.status_code == 401

    def test_get_current_user_with_nonexistent_user(self):
        """测试token有效但用户不存在"""
        token = create_access_token(data={"sub": "nonexistentuser"})
        
        mock_credentials = Mock()
        mock_credentials.credentials = token
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials, mock_db)
        
        assert exc_info.value.status_code == 401


class TestGetCurrentAdmin:
    """测试获取当前管理员功能"""

    def test_get_current_admin_with_admin_user(self, mock_admin_user):
        """测试管理员用户通过验证"""
        result = get_current_admin(mock_admin_user)
        
        assert result == mock_admin_user

    def test_get_current_admin_with_regular_user(self, mock_user):
        """测试普通用户被拒绝访问"""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail

    def test_get_current_admin_with_missing_role(self):
        """测试用户没有role字段"""
        user = Mock()
        user.role = None
        
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(user)
        
        assert exc_info.value.status_code == 403


# ===== 登录路由测试 =====

class TestLoginRoute:
    """测试登录路由"""

    def test_login_success(self, client, test_user):
        """测试成功登录"""
        response = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "test123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "data" in data
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert "expires_in" in data["data"]

    def test_login_with_wrong_password(self, client, test_user):
        """测试密码错误"""
        response = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert data["code"] != 0
        assert "用户名或密码错误" in data["message"]

    def test_login_with_nonexistent_user(self, client):
        """测试用户不存在"""
        response = client.post("/api/v1/auth/login", json={
            "username": "nonexistentuser",
            "password": "somepassword"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert data["code"] != 0

    def test_login_with_empty_username(self, client):
        """测试空用户名"""
        response = client.post("/api/v1/auth/login", json={
            "username": "",
            "password": "test123"
        })
        
        assert response.status_code == 422  # Validation error

    def test_login_with_empty_password(self, client):
        """测试空密码"""
        response = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": ""
        })
        
        assert response.status_code == 422  # Validation error

    def test_login_with_missing_fields(self, client):
        """测试缺少字段"""
        response = client.post("/api/v1/auth/login", json={
            "username": "testuser"
            # missing password
        })
        
        assert response.status_code == 422


# ===== 注册路由测试 =====

class TestRegisterRoute:
    """测试注册路由"""

    def test_register_success(self, client, db_session):
        """测试成功注册"""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser123",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "data" in data
        assert data["data"]["username"] == "newuser123"
        assert "id" in data["data"]
        assert "role" in data["data"]

    def test_register_with_existing_username(self, client, test_user):
        """测试重复用户名"""
        response = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "password123"
        })
        
        assert response.status_code == 409
        data = response.json()
        assert data["code"] != 0
        assert "用户名已存在" in data["message"]

    def test_register_with_weak_password(self, client):
        """测试弱密码"""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "password": "123"  # too short
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "密码强度不足" in data["message"]

    def test_register_with_password_no_number(self, client):
        """测试密码不包含数字"""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "password": "passwordonly"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "密码强度不足" in data["message"]

    def test_register_with_password_no_letter(self, client):
        """测试密码不包含字母"""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "password": "12345678"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "密码强度不足" in data["message"]

    def test_register_first_user_becomes_admin(self, client, db_session):
        """测试第一个注册用户成为管理员"""
        # 先删除所有用户
        from app.models.user import User
        db_session.query(User).delete()
        db_session.commit()
        
        response = client.post("/api/v1/auth/register", json={
            "username": "firstuser",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["role"] == "admin"

    def test_register_subsequent_users_become_user(self, client, test_user):
        """测试后续注册用户成为普通用户"""
        response = client.post("/api/v1/auth/register", json={
            "username": "seconduser",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["role"] == "user"

    def test_register_with_empty_username(self, client):
        """测试空用户名"""
        response = client.post("/api/v1/auth/register", json={
            "username": "",
            "password": "password123"
        })
        
        assert response.status_code == 422

    def test_register_with_empty_password(self, client):
        """测试空密码"""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "password": ""
        })
        
        assert response.status_code == 422


# ===== 获取当前用户信息测试 =====

class TestGetMeRoute:
    """测试获取当前用户信息路由"""

    def test_get_me_success(self, client, auth_headers, test_user):
        """测试成功获取当前用户信息"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["username"] == test_user.username
        assert data["data"]["id"] == test_user.id
        assert data["data"]["role"] == test_user.role

    def test_get_me_without_token(self, client):
        """测试未提供token"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 403

    def test_get_me_with_invalid_token(self, client):
        """测试无效token"""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401

    def test_get_me_with_expired_token(self, client):
        """测试过期token"""
        # 创建过期token
        expire = datetime.utcnow() - timedelta(minutes=1)
        token = jwt.encode(
            {"sub": "testuser", "exp": expire},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401

    def test_get_me_with_malformed_header(self, client):
        """测试格式错误的Authorization头"""
        headers = {"Authorization": "InvalidFormat token123"}
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 403


# ===== 请求模型验证测试 =====

class TestAuthRequestModels:
    """测试认证请求模型"""

    def test_login_request_valid(self):
        """测试有效登录请求"""
        request = LoginRequest(username="testuser", password="testpass")
        assert request.username == "testuser"
        assert request.password == "testpass"

    def test_login_request_missing_username(self):
        """测试缺少用户名的登录请求"""
        with pytest.raises(ValueError):
            LoginRequest(password="testpass")

    def test_login_request_missing_password(self):
        """测试缺少密码的登录请求"""
        with pytest.raises(ValueError):
            LoginRequest(username="testuser")

    def test_register_request_valid(self):
        """测试有效注册请求"""
        request = RegisterRequest(username="newuser", password="newpass123")
        assert request.username == "newuser"
        assert request.password == "newpass123"

    def test_token_response_model(self):
        """测试Token响应模型"""
        response = TokenResponse(
            access_token="test_token_123",
            token_type="bearer",
            expires_in=1440
        )
        assert response.access_token == "test_token_123"
        assert response.token_type == "bearer"
        assert response.expires_in == 1440

    def test_user_response_model(self):
        """测试用户响应模型"""
        response = UserResponse(
            id="user-id-123",
            username="testuser",
            role="user",
            created_at="2024-01-01T00:00:00Z"
        )
        assert response.id == "user-id-123"
        assert response.username == "testuser"
        assert response.role == "user"


# ===== 集成测试 =====

class TestAuthIntegration:
    """认证集成测试"""

    def test_register_then_login(self, client):
        """测试注册后登录"""
        # 注册新用户
        register_response = client.post("/api/v1/auth/register", json={
            "username": "integrateuser",
            "password": "integrate123"
        })
        
        assert register_response.status_code == 200
        
        # 使用新用户登录
        login_response = client.post("/api/v1/auth/login", json={
            "username": "integrateuser",
            "password": "integrate123"
        })
        
        assert login_response.status_code == 200
        data = login_response.json()
        assert "access_token" in data["data"]
        
        # 使用token获取用户信息
        token = data["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["data"]["username"] == "integrateuser"

    def test_login_with_wrong_password_after_register(self, client):
        """测试注册后使用错误密码登录"""
        # 注册新用户
        client.post("/api/v1/auth/register", json={
            "username": "wrongpassuser",
            "password": "correctpassword123"
        })
        
        # 使用错误密码登录
        login_response = client.post("/api/v1/auth/login", json={
            "username": "wrongpassuser",
            "password": "wrongpassword123"
        })
        
        assert login_response.status_code == 401

    def test_token_expiration_flow(self, client):
        """测试token过期流程"""
        # 登录获取token
        login_response = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "test123"
        })
        
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # token应该有效
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200


# ===== 边界情况测试 =====

class TestAuthEdgeCases:
    """认证边界情况测试"""

    def test_login_with_very_long_username(self, client):
        """测试超长用户名"""
        response = client.post("/api/v1/auth/login", json={
            "username": "a" * 1000,
            "password": "test123"
        })
        
        # 应该返回401，而不是500
        assert response.status_code == 401

    def test_login_with_special_characters_in_username(self, client):
        """测试用户名包含特殊字符"""
        response = client.post("/api/v1/auth/login", json={
            "username": "user@#$%^&*()",
            "password": "test123"
        })
        
        # 应该正常处理，返回401
        assert response.status_code == 401

    def test_register_with_unicode_username(self, client):
        """测试Unicode用户名"""
        response = client.post("/api/v1/auth/register", json={
            "username": "用户123",
            "password": "password123"
        })
        
        # 应该成功注册
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["username"] == "用户123"

    def test_register_with_very_long_password(self, client):
        """测试超长密码"""
        response = client.post("/api/v1/auth/register", json={
            "username": "longpassuser",
            "password": "a" * 1000 + "123"
        })
        
        # 应该成功注册
        assert response.status_code == 200

    def test_concurrent_login_attempts(self, client, test_user):
        """测试并发登录尝试"""
        import concurrent.futures
        
        def login_attempt():
            return client.post("/api/v1/auth/login", json={
                "username": "testuser",
                "password": "test123"
            })
        
        # 并发执行多个登录请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(login_attempt) for _ in range(5)]
            results = [f.result() for f in futures]
        
        # 所有请求都应该成功
        for response in results:
            assert response.status_code == 200
            assert "access_token" in response.json()["data"]
