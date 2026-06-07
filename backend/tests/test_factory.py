"""
Diff 引擎工厂模块测试

测试 factory.py 中的核心功能，包括：
- 引擎注册和注销
- 支持类型检查
- 引擎信息获取
- 无效引擎类校验

作者: Test Team
创建日期: 2026-05-28
"""

import pytest
from unittest.mock import patch, MagicMock

from app.diff_engine.factory import (
    get_diff_engine,
    register_engine,
    unregister_engine,
    get_supported_types,
    is_supported,
    get_engine_info,
    ENGINE_REGISTRY,
    ValidationError,
)
from app.diff_engine.base import BaseDiffEngine
from app.diff_engine.docx_diff import DocxDiffEngine
from app.diff_engine.xlsx_diff import XlsxDiffEngine
from app.diff_engine.pdf_diff import PdfDiffEngine


class TestRegisterEngine:
    """测试引擎注册功能"""

    def test_register_engine_success(self):
        """测试成功注册引擎（行71-79: 正常注册流程）"""
        # 创建一个自定义引擎类
        class CustomEngine(BaseDiffEngine):
            """自定义引擎"""
            pass

        # 注册前不应该存在
        assert "custom" not in ENGINE_REGISTRY

        # 执行注册
        register_engine("custom", CustomEngine)

        # 验证注册成功
        assert "custom" in ENGINE_REGISTRY
        assert ENGINE_REGISTRY["custom"] == CustomEngine

        # 清理：注销自定义引擎
        unregister_engine("custom")

    def test_register_engine_invalid(self):
        """测试注册无效引擎类（行73-76: issubclass 校验失败）"""
        # 使用一个不继承 BaseDiffEngine 的类
        class InvalidEngine:
            pass

        with pytest.raises(ValidationError, match="引擎类必须继承 BaseDiffEngine"):
            register_engine("invalid", InvalidEngine)

    def test_register_engine_with_dot_prefix(self):
        """测试注册带点号前缀的文件类型（行71: lstrip('.') 处理）"""
        class CustomEngine(BaseDiffEngine):
            """自定义引擎"""
            pass

        # 使用带点号前缀的类型名
        register_engine(".custom_dot", CustomEngine)

        # 验证注册成功（点号前缀被移除）
        assert "custom_dot" in ENGINE_REGISTRY

        # 清理
        unregister_engine("custom_dot")

    def test_register_engine_uppercase(self):
        """测试注册大写文件类型（行71: lower() 处理）"""
        class CustomEngine(BaseDiffEngine):
            """自定义引擎"""
            pass

        # 使用大写类型名
        register_engine("CUSTOM", CustomEngine)

        # 验证注册成功（大写被转换为小写）
        assert "custom" in ENGINE_REGISTRY

        # 清理
        unregister_engine("custom")


class TestUnregisterEngine:
    """测试引擎注销功能"""

    def test_unregister_engine_success(self):
        """测试成功注销引擎（行92-100: 正常注销流程）"""
        # 先注册一个引擎
        class TempEngine(BaseDiffEngine):
            """临时引擎"""
            pass

        register_engine("temp", TempEngine)
        assert "temp" in ENGINE_REGISTRY

        # 执行注销
        result = unregister_engine("temp")

        # 验证注销成功
        assert result == TempEngine
        assert "temp" not in ENGINE_REGISTRY

    def test_unregister_engine_not_found(self):
        """测试注销不存在的引擎（行99-100: 返回 None）"""
        result = unregister_engine("nonexistent_type")

        # 不存在的引擎应返回 None
        assert result is None

    def test_unregister_engine_with_dot_prefix(self):
        """测试注销带点号前缀的引擎（行92: lstrip('.') 处理）"""
        result = unregister_engine(".docx")

        # 应该注销成功（点号前缀被移除）
        assert result == DocxDiffEngine

        # 重新注册以避免影响其他测试
        ENGINE_REGISTRY["docx"] = DocxDiffEngine


class TestGetSupportedTypes:
    """测试获取支持的类型列表"""

    def test_get_supported_types(self):
        """测试获取支持的类型列表（行110: 返回引擎注册表的键列表）"""
        types = get_supported_types()

        # 验证返回的是列表
        assert isinstance(types, list)

        # 验证包含默认引擎类型
        assert "docx" in types
        assert "xlsx" in types
        assert "pdf" in types

    def test_get_supported_types_after_register(self):
        """测试注册新引擎后类型列表更新"""
        class NewEngine(BaseDiffEngine):
            """新引擎"""
            pass

        register_engine("new_type", NewEngine)
        types = get_supported_types()

        assert "new_type" in types

        # 清理
        unregister_engine("new_type")


class TestIsSupported:
    """测试文件类型支持检查"""

    def test_is_supported_true(self):
        """测试支持的文件类型（行123-124: 返回 True）"""
        assert is_supported("docx") is True
        assert is_supported("xlsx") is True
        assert is_supported("pdf") is True

    def test_is_supported_false(self):
        """测试不支持的文件类型"""
        assert is_supported("exe") is False
        assert is_supported("zip") is False
        assert is_supported("unknown") is False

    def test_is_supported_with_dot_prefix(self):
        """测试带点号前缀的类型（行123: lstrip('.') 处理）"""
        assert is_supported(".docx") is True
        assert is_supported(".pdf") is True
        assert is_supported(".exe") is False

    def test_is_supported_uppercase(self):
        """测试大写文件类型（行123: lower() 处理）"""
        assert is_supported("DOCX") is True
        assert is_supported("PDF") is True
        assert is_supported("XLSX") is True


class TestGetEngineInfo:
    """测试获取引擎信息"""

    def test_get_engine_info_single(self):
        """测试获取单个引擎信息（行137-151: 指定 file_type）"""
        info = get_engine_info("docx")

        # 验证返回的是字典
        assert isinstance(info, dict)
        assert "docx" in info

        # 验证信息结构
        docx_info = info["docx"]
        assert docx_info["file_type"] == "docx"
        assert docx_info["engine_class"] == "DocxDiffEngine"
        assert "module" in docx_info
        assert "doc" in docx_info

    def test_get_engine_info_all(self):
        """测试获取所有引擎信息（行151-154: file_type 为 None）"""
        info = get_engine_info()

        # 验证返回的是字典
        assert isinstance(info, dict)

        # 验证包含所有默认引擎
        assert "docx" in info
        assert "xlsx" in info
        assert "pdf" in info

        # 验证每个引擎的信息结构
        for file_type, engine_info in info.items():
            assert "file_type" in engine_info
            assert "engine_class" in engine_info
            assert "module" in engine_info
            assert "doc" in engine_info

    def test_get_engine_info_not_found(self):
        """测试获取不存在的引擎信息（行148-149: 返回空字典）"""
        info = get_engine_info("nonexistent_type")

        # 不存在的引擎应返回空字典
        assert info == {}

    def test_get_engine_info_with_dot_prefix(self):
        """测试带点号前缀的类型（行146: lstrip('.') 处理）"""
        info = get_engine_info(".pdf")

        # 应该返回 pdf 引擎信息
        assert "pdf" in info
        assert info["pdf"]["engine_class"] == "PdfDiffEngine"


class TestGetDiffEngine:
    """测试获取 Diff 引擎实例"""

    def test_get_diff_engine_docx(self):
        """测试获取 DOCX 引擎"""
        engine = get_diff_engine("docx")
        assert isinstance(engine, DocxDiffEngine)

    def test_get_diff_engine_xlsx(self):
        """测试获取 XLSX 引擎"""
        engine = get_diff_engine("xlsx")
        assert isinstance(engine, XlsxDiffEngine)

    def test_get_diff_engine_pdf(self):
        """测试获取 PDF 引擎"""
        engine = get_diff_engine("pdf")
        assert isinstance(engine, PdfDiffEngine)

    def test_get_diff_engine_with_dot_prefix(self):
        """测试带点号前缀的类型"""
        engine = get_diff_engine(".docx")
        assert isinstance(engine, DocxDiffEngine)

    def test_get_diff_engine_uppercase(self):
        """测试大写文件类型"""
        engine = get_diff_engine("DOCX")
        assert isinstance(engine, DocxDiffEngine)

    def test_get_diff_engine_unsupported(self):
        """测试不支持的文件类型"""
        with pytest.raises(ValidationError, match="不支持的文件类型"):
            get_diff_engine("exe")
