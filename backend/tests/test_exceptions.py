"""
异常类测试模块

测试所有自定义异常类的功能，包括：
- 基础异常类 DocShopException
- 所有异常子类的 to_dict 方法
- get_http_status 函数的所有错误码分支
- 异常类的各种初始化方式

作者: Test Team
创建日期: 2026-05-28
"""

import os
import sys
import unittest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import status

from app.exceptions import (
    DocShopException,
    ValidationError,
    AuthenticationError,
    PermissionDenied,
    ResourceNotFound,
    FileValidationError,
    DiffCalculationError,
    DatabaseError,
    StorageError,
    RateLimitExceeded,
    ConflictError,
    ExternalServiceError,
    get_http_status,
)


class TestDocShopException(unittest.TestCase):
    """测试基础异常类"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = DocShopException("测试错误")
        
        self.assertEqual(exc.message, "测试错误")
        self.assertEqual(exc.code, 50000)
        self.assertEqual(exc.details, {})

    def test_init_with_code(self):
        """测试带错误码初始化"""
        exc = DocShopException("测试错误", code=40001)
        
        self.assertEqual(exc.code, 40001)

    def test_init_with_details(self):
        """测试带详情初始化"""
        exc = DocShopException("测试错误", details={"field": "username"})
        
        self.assertEqual(exc.details, {"field": "username"})

    def test_to_dict_basic(self):
        """测试基础to_dict"""
        exc = DocShopException("测试错误", code=40001)
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 40001)
        self.assertEqual(result["message"], "测试错误")
        self.assertIsNone(result["data"])

    def test_to_dict_with_details(self):
        """测试带详情的to_dict"""
        exc = DocShopException("测试错误", code=40001, details={"field": "username"})
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 40001)
        self.assertEqual(result["message"], "测试错误")
        self.assertEqual(result["details"], {"field": "username"})
        self.assertIsNone(result["data"])

    def test_to_dict_empty_details(self):
        """测试空详情的to_dict"""
        exc = DocShopException("测试错误", code=40001, details={})
        result = exc.to_dict()
        
        # 空details不应该出现在结果中
        self.assertNotIn("details", result)

    def test_str_representation(self):
        """测试字符串表示"""
        exc = DocShopException("测试错误")
        
        self.assertEqual(str(exc), "测试错误")


class TestValidationError(unittest.TestCase):
    """测试参数校验错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = ValidationError()
        
        self.assertEqual(exc.message, "参数校验失败")
        self.assertEqual(exc.code, 40001)

    def test_init_with_field(self):
        """测试带字段初始化"""
        exc = ValidationError(message="用户名不能为空", field="username")
        
        self.assertEqual(exc.message, "用户名不能为空")
        self.assertEqual(exc.details["field"], "username")

    def test_init_with_details(self):
        """测试带详情初始化"""
        exc = ValidationError(
            message="参数错误",
            field="email",
            details={"reason": "invalid_format"}
        )
        
        self.assertEqual(exc.details["field"], "email")
        self.assertEqual(exc.details["reason"], "invalid_format")

    def test_to_dict(self):
        """测试to_dict"""
        exc = ValidationError(message="用户名不能为空", field="username")
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 40001)
        self.assertEqual(result["message"], "用户名不能为空")
        self.assertEqual(result["details"]["field"], "username")


class TestAuthenticationError(unittest.TestCase):
    """测试认证错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = AuthenticationError()
        
        self.assertEqual(exc.message, "认证失败")
        self.assertEqual(exc.code, 20001)

    def test_init_with_auth_type(self):
        """测试带认证类型初始化"""
        exc = AuthenticationError(message="Token已过期", auth_type="token")
        
        self.assertEqual(exc.details["auth_type"], "token")

    def test_to_dict(self):
        """测试to_dict"""
        exc = AuthenticationError(message="密码错误", auth_type="password")
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 20001)
        self.assertEqual(result["details"]["auth_type"], "password")


class TestPermissionDenied(unittest.TestCase):
    """测试权限不足错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = PermissionDenied()
        
        self.assertEqual(exc.message, "权限不足")
        self.assertEqual(exc.code, 20004)

    def test_init_with_required_permission(self):
        """测试带所需权限初始化"""
        exc = PermissionDenied(
            message="需要管理员权限",
            required_permission="admin"
        )
        
        self.assertEqual(exc.details["required_permission"], "admin")

    def test_to_dict(self):
        """测试to_dict"""
        exc = PermissionDenied(required_permission="write")
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 20004)
        self.assertEqual(result["details"]["required_permission"], "write")


class TestResourceNotFound(unittest.TestCase):
    """测试资源不存在错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = ResourceNotFound()
        
        self.assertEqual(exc.message, "资源不存在")
        self.assertEqual(exc.code, 30001)

    def test_init_with_resource(self):
        """测试带资源类型初始化"""
        exc = ResourceNotFound(resource="用户")
        
        self.assertEqual(exc.message, "用户不存在")

    def test_init_with_resource_id(self):
        """测试带资源ID初始化"""
        exc = ResourceNotFound(resource="文件", resource_id="file-123")
        
        self.assertEqual(exc.message, "文件不存在: file-123")
        self.assertEqual(exc.details["resource_id"], "file-123")

    def test_to_dict(self):
        """测试to_dict"""
        exc = ResourceNotFound(resource="项目", resource_id="proj-456")
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 30001)
        self.assertEqual(result["message"], "项目不存在: proj-456")
        self.assertEqual(result["details"]["resource_id"], "proj-456")


class TestFileValidationError(unittest.TestCase):
    """测试文件校验错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = FileValidationError()
        
        self.assertEqual(exc.message, "文件校验失败")
        self.assertEqual(exc.code, 40002)

    def test_init_with_filename(self):
        """测试带文件名初始化"""
        exc = FileValidationError(filename="test.exe")
        
        self.assertEqual(exc.details["filename"], "test.exe")

    def test_init_with_reason(self):
        """测试带原因初始化"""
        exc = FileValidationError(reason="unsupported_type")
        
        self.assertEqual(exc.details["reason"], "unsupported_type")

    def test_init_full(self):
        """测试完整初始化"""
        exc = FileValidationError(
            message="文件类型不支持",
            filename="test.exe",
            reason="unsupported_type"
        )
        
        self.assertEqual(exc.details["filename"], "test.exe")
        self.assertEqual(exc.details["reason"], "unsupported_type")

    def test_to_dict(self):
        """测试to_dict"""
        exc = FileValidationError(
            message="文件过大",
            filename="large.pdf",
            reason="file_too_large"
        )
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 40002)
        self.assertEqual(result["details"]["filename"], "large.pdf")
        self.assertEqual(result["details"]["reason"], "file_too_large")


class TestDiffCalculationError(unittest.TestCase):
    """测试Diff计算错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = DiffCalculationError()
        
        self.assertEqual(exc.message, "差异计算失败")
        self.assertEqual(exc.code, 50001)

    def test_init_with_file_type(self):
        """测试带文件类型初始化"""
        exc = DiffCalculationError(file_type="docx")
        
        self.assertEqual(exc.details["file_type"], "docx")

    def test_to_dict(self):
        """测试to_dict"""
        exc = DiffCalculationError(
            message="无法解析文档",
            file_type="pdf"
        )
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 50001)
        self.assertEqual(result["details"]["file_type"], "pdf")


class TestDatabaseError(unittest.TestCase):
    """测试数据库错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = DatabaseError()
        
        self.assertEqual(exc.message, "数据库操作失败")
        self.assertEqual(exc.code, 50002)

    def test_init_with_operation(self):
        """测试带操作类型初始化"""
        exc = DatabaseError(operation="insert")
        
        self.assertEqual(exc.details["operation"], "insert")

    def test_to_dict(self):
        """测试to_dict"""
        exc = DatabaseError(
            message="连接超时",
            operation="query"
        )
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 50002)
        self.assertEqual(result["details"]["operation"], "query")


class TestStorageError(unittest.TestCase):
    """测试存储错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = StorageError()
        
        self.assertEqual(exc.message, "文件存储失败")
        self.assertEqual(exc.code, 50003)

    def test_init_with_storage_type(self):
        """测试带存储类型初始化"""
        exc = StorageError(storage_type="s3")
        
        self.assertEqual(exc.details["storage_type"], "s3")

    def test_init_with_operation(self):
        """测试带操作初始化"""
        exc = StorageError(operation="upload")
        
        self.assertEqual(exc.details["operation"], "upload")

    def test_init_full(self):
        """测试完整初始化"""
        exc = StorageError(
            message="磁盘空间不足",
            storage_type="local",
            operation="save"
        )
        
        self.assertEqual(exc.details["storage_type"], "local")
        self.assertEqual(exc.details["operation"], "save")

    def test_to_dict(self):
        """测试to_dict"""
        exc = StorageError(
            message="上传失败",
            storage_type="s3",
            operation="upload"
        )
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 50003)
        self.assertEqual(result["details"]["storage_type"], "s3")
        self.assertEqual(result["details"]["operation"], "upload")


class TestRateLimitExceeded(unittest.TestCase):
    """测试频率超限错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = RateLimitExceeded()
        
        self.assertEqual(exc.message, "请求过于频繁")
        self.assertEqual(exc.code, 40003)

    def test_init_with_retry_after(self):
        """测试带重试时间初始化"""
        exc = RateLimitExceeded(retry_after=60)
        
        self.assertEqual(exc.details["retry_after"], 60)

    def test_to_dict(self):
        """测试to_dict"""
        exc = RateLimitExceeded(retry_after=30)
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 40003)
        self.assertEqual(result["details"]["retry_after"], 30)


class TestConflictError(unittest.TestCase):
    """测试资源冲突错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = ConflictError()
        
        self.assertEqual(exc.message, "资源冲突")
        self.assertEqual(exc.code, 40004)

    def test_init_with_conflict_type(self):
        """测试带冲突类型初始化"""
        exc = ConflictError(conflict_type="duplicate")
        
        self.assertEqual(exc.details["conflict_type"], "duplicate")

    def test_to_dict(self):
        """测试to_dict"""
        exc = ConflictError(
            message="资源已存在",
            conflict_type="duplicate"
        )
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 40004)
        self.assertEqual(result["details"]["conflict_type"], "duplicate")


class TestExternalServiceError(unittest.TestCase):
    """测试外部服务错误"""

    def test_init_default(self):
        """测试默认初始化"""
        exc = ExternalServiceError()
        
        self.assertEqual(exc.message, "外部服务调用失败")
        self.assertEqual(exc.code, 50004)

    def test_init_with_service_name(self):
        """测试带服务名初始化"""
        exc = ExternalServiceError(service_name="email_service")
        
        self.assertEqual(exc.details["service_name"], "email_service")

    def test_to_dict(self):
        """测试to_dict"""
        exc = ExternalServiceError(
            message="邮件服务不可用",
            service_name="smtp"
        )
        result = exc.to_dict()
        
        self.assertEqual(result["code"], 50004)
        self.assertEqual(result["details"]["service_name"], "smtp")


class TestGetHttpStatus(unittest.TestCase):
    """测试获取HTTP状态码函数"""

    def test_auth_error_20001(self):
        """测试认证错误"""
        status_code = get_http_status(20001)
        self.assertEqual(status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_error_20004(self):
        """测试权限错误"""
        status_code = get_http_status(20004)
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)

    def test_not_found_30001(self):
        """测试资源不存在"""
        status_code = get_http_status(30001)
        self.assertEqual(status_code, status.HTTP_404_NOT_FOUND)

    def test_validation_error_40001(self):
        """测试参数校验错误"""
        status_code = get_http_status(40001)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)

    def test_file_validation_error_40002(self):
        """测试文件校验错误"""
        status_code = get_http_status(40002)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)

    def test_rate_limit_error_40003(self):
        """测试频率限制错误"""
        status_code = get_http_status(40003)
        self.assertEqual(status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_conflict_error_40004(self):
        """测试资源冲突错误"""
        status_code = get_http_status(40004)
        self.assertEqual(status_code, status.HTTP_409_CONFLICT)

    def test_diff_error_50001(self):
        """测试Diff计算错误"""
        status_code = get_http_status(50001)
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_database_error_50002(self):
        """测试数据库错误"""
        status_code = get_http_status(50002)
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_storage_error_50003(self):
        """测试存储错误"""
        status_code = get_http_status(50003)
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_external_service_error_50004(self):
        """测试外部服务错误"""
        status_code = get_http_status(50004)
        self.assertEqual(status_code, status.HTTP_502_BAD_GATEWAY)

    def test_unknown_2xxx_error(self):
        """测试未知2开头错误"""
        status_code = get_http_status(29999)
        self.assertEqual(status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_3xxx_error(self):
        """测试未知3开头错误"""
        status_code = get_http_status(39999)
        self.assertEqual(status_code, status.HTTP_404_NOT_FOUND)

    def test_unknown_4xxx_error(self):
        """测试未知4开头错误"""
        status_code = get_http_status(49999)
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_5xxx_error(self):
        """测试未知5开头错误"""
        status_code = get_http_status(59999)
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_unknown_prefix_error(self):
        """测试未知前缀错误"""
        status_code = get_http_status(99999)
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_zero_code(self):
        """测试零错误码"""
        status_code = get_http_status(0)
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_negative_code(self):
        """测试负错误码"""
        status_code = get_http_status(-1)
        self.assertEqual(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestExceptionInheritance(unittest.TestCase):
    """测试异常继承关系"""

    def test_all_inherit_from_base(self):
        """测试所有异常继承自基础异常"""
        exceptions = [
            ValidationError(),
            AuthenticationError(),
            PermissionDenied(),
            ResourceNotFound(),
            FileValidationError(),
            DiffCalculationError(),
            DatabaseError(),
            StorageError(),
            RateLimitExceeded(),
            ConflictError(),
            ExternalServiceError(),
        ]
        
        for exc in exceptions:
            self.assertIsInstance(exc, DocShopException)

    def test_all_have_correct_codes(self):
        """测试所有异常有正确的错误码"""
        test_cases = [
            (ValidationError(), 40001),
            (AuthenticationError(), 20001),
            (PermissionDenied(), 20004),
            (ResourceNotFound(), 30001),
            (FileValidationError(), 40002),
            (DiffCalculationError(), 50001),
            (DatabaseError(), 50002),
            (StorageError(), 50003),
            (RateLimitExceeded(), 40003),
            (ConflictError(), 40004),
            (ExternalServiceError(), 50004),
        ]
        
        for exc, expected_code in test_cases:
            self.assertEqual(exc.code, expected_code)


class TestExceptionEdgeCases(unittest.TestCase):
    """测试异常边界情况"""

    def test_empty_message(self):
        """测试空消息"""
        exc = DocShopException("")
        self.assertEqual(exc.message, "")
        result = exc.to_dict()
        self.assertEqual(result["message"], "")

    def test_none_in_details(self):
        """测试详情中的None值"""
        exc = ValidationError(field=None)
        result = exc.to_dict()
        # None值不会被添加到details中（这是预期行为）
        # 如果details为空，则不会包含details字段
        self.assertNotIn("details", result)

    def test_unicode_message(self):
        """测试Unicode消息"""
        exc = DocShopException("中文错误消息: 测试")
        result = exc.to_dict()
        self.assertEqual(result["message"], "中文错误消息: 测试")

    def test_long_message(self):
        """测试长消息"""
        long_msg = "错误" * 1000
        exc = DocShopException(long_msg)
        result = exc.to_dict()
        self.assertEqual(result["message"], long_msg)

    def test_nested_details(self):
        """测试嵌套详情"""
        nested_details = {
            "user": {"id": 1, "name": "test"},
            "errors": ["error1", "error2"]
        }
        exc = ValidationError(details=nested_details)
        result = exc.to_dict()
        self.assertEqual(result["details"]["user"]["id"], 1)
        self.assertEqual(len(result["details"]["errors"]), 2)


if __name__ == "__main__":
    unittest.main()
