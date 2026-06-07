"""
文件校验模块测试

测试 file_validator.py 中的功能，包括文件类型验证、文件名清理、
路径穿越防护和文件大小验证等。
"""

import zipfile
import io
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.validators.file_validator import (
    validate_file_type,
    sanitize_filename,
    _validate_file_size,
    _validate_extension,
)
from app.exceptions import FileValidationError


# ===== 辅助函数：创建各种类型的测试文件 =====

def _create_pdf_file(path: Path) -> Path:
    """创建一个有效的 PDF 测试文件"""
    # PDF 文件以 %PDF 开头
    content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
    path.write_bytes(content)
    return path


def _create_docx_file(path: Path) -> Path:
    """创建一个有效的 DOCX 测试文件（ZIP 格式，包含 word/document.xml）"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
        zf.writestr("word/document.xml", "<w:document></w:document>")
    path.write_bytes(buf.getvalue())
    return path


def _create_xlsx_file(path: Path) -> Path:
    """创建一个有效的 XLSX 测试文件（ZIP 格式，包含 xl/workbook.xml）"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
        zf.writestr("xl/workbook.xml", "<workbook></workbook>")
    path.write_bytes(buf.getvalue())
    return path


def _create_plain_text_file(path: Path) -> Path:
    """创建一个纯文本文件（非有效文档格式）"""
    path.write_text("This is a plain text file, not a valid document.")
    return path


# ===== test_validate_file_type_pdf: 测试PDF文件验证 =====

class TestValidateFileTypePdf:
    """测试 PDF 文件类型验证"""

    def test_validate_file_type_pdf(self, tmp_path):
        """测试PDF文件验证：有效的PDF文件应通过验证并返回 'pdf'"""
        pdf_file = _create_pdf_file(tmp_path / "document.pdf")

        result = validate_file_type(pdf_file, "document.pdf")

        assert result == "pdf"


# ===== test_validate_file_type_docx: 测试DOCX文件验证 =====

class TestValidateFileTypeDocx:
    """测试 DOCX 文件类型验证"""

    def test_validate_file_type_docx(self, tmp_path):
        """测试DOCX文件验证：有效的DOCX文件应通过验证并返回 'docx'"""
        docx_file = _create_docx_file(tmp_path / "report.docx")

        result = validate_file_type(docx_file, "report.docx")

        assert result == "docx"


# ===== test_validate_file_type_xlsx: 测试XLSX文件验证 =====

class TestValidateFileTypeXlsx:
    """测试 XLSX 文件类型验证"""

    def test_validate_file_type_xlsx(self, tmp_path):
        """测试XLSX文件验证：有效的XLSX文件应通过验证并返回 'xlsx'"""
        xlsx_file = _create_xlsx_file(tmp_path / "data.xlsx")

        result = validate_file_type(xlsx_file, "data.xlsx")

        assert result == "xlsx"


# ===== test_validate_file_type_mismatch: 测试文件类型不匹配 =====

class TestValidateFileTypeMismatch:
    """测试文件类型不匹配检测"""

    def test_validate_file_type_mismatch(self, tmp_path):
        """
        测试文件类型不匹配：文件扩展名为 .pdf 但实际内容为纯文本，
        应抛出 FileValidationError。
        """
        # 创建一个纯文本文件但命名为 .pdf
        text_file = _create_plain_text_file(tmp_path / "fake.pdf")

        with pytest.raises(FileValidationError):
            validate_file_type(text_file, "fake.pdf")

    def test_validate_file_type_docx_content_pdf_ext(self, tmp_path):
        """
        测试DOCX内容但PDF扩展名：应抛出 FileValidationError，
        因为文件头与声明的扩展名不匹配。
        """
        docx_file = _create_docx_file(tmp_path / "mismatch.pdf")

        with pytest.raises(FileValidationError, match="文件头与扩展名不符"):
            validate_file_type(docx_file, "mismatch.pdf")

    def test_validate_file_type_unsupported_extension(self, tmp_path):
        """测试不支持的文件扩展名：应抛出 FileValidationError"""
        text_file = _create_plain_text_file(tmp_path / "script.exe")

        with pytest.raises(FileValidationError, match="不支持的文件类型"):
            validate_file_type(text_file, "script.exe")

    def test_validate_file_type_missing_extension(self, tmp_path):
        """测试缺少扩展名：应抛出 FileValidationError"""
        text_file = _create_plain_text_file(tmp_path / "noextension")

        with pytest.raises(FileValidationError, match="文件缺少扩展名"):
            validate_file_type(text_file, "noextension")


# ===== test_sanitize_filename: 测试文件名清理 =====

class TestSanitizeFilename:
    """测试文件名清理功能"""

    def test_sanitize_filename(self):
        """测试正常文件名清理：正常文件名应保持不变"""
        assert sanitize_filename("report.pdf") == "report.pdf"
        assert sanitize_filename("data_2024.xlsx") == "data_2024.xlsx"
        assert sanitize_filename("my document.docx") == "my document.docx"

    def test_sanitize_filename_path_traversal(self):
        """
        测试路径穿越防护：包含路径分隔符的文件名应被清理，
        防止目录遍历攻击。路径分隔符被替换为下划线，
        使得路径穿越序列（如 ../）失效。
        """
        # 路径分隔符应被替换为下划线，使路径穿越失效
        result1 = sanitize_filename("../../../etc/passwd")
        assert "/" not in result1
        assert "\\" not in result1

        result2 = sanitize_filename("..\\..\\windows\\system32")
        assert "\\" not in result2

        result3 = sanitize_filename("../../secret/file.pdf")
        assert "/" not in result3
        # 路径分隔符被移除后，.. 也被替换为 ____
        assert result3 == "____secret_file.pdf"

        # 普通路径中的分隔符也应被替换
        assert "/" not in sanitize_filename("path/to/file.pdf")
        assert "\\" not in sanitize_filename("path\\to\\file.pdf")

    def test_sanitize_filename_special_chars(self):
        """测试特殊字符处理：危险字符应被替换为下划线"""
        # Windows/Linux 不允许的字符
        assert sanitize_filename('file<name>.pdf') == "file_name_.pdf"
        assert sanitize_filename('file>name>.pdf') == "file_name_.pdf"
        assert sanitize_filename('file:name:.pdf') == "file_name_.pdf"
        assert sanitize_filename('file"name".pdf') == "file_name_.pdf"
        assert sanitize_filename('file?name?.pdf') == "file_name_.pdf"
        assert sanitize_filename('file*name*.pdf') == "file_name_.pdf"
        assert sanitize_filename('file|name|.pdf') == "file_name_.pdf"

    def test_sanitize_filename_empty(self):
        """测试空文件名：应返回默认文件名"""
        assert sanitize_filename("") == "unnamed_file"
        assert sanitize_filename(None) == "unnamed_file"

    def test_sanitize_filename_hidden_file(self):
        """测试隐藏文件名：开头的点应被移除"""
        result = sanitize_filename(".hidden_file.txt")
        assert not result.startswith(".")
        assert result == "hidden_file.txt"

    def test_sanitize_filename_too_long(self):
        """测试超长文件名：应被截断"""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name, max_length=200)
        assert len(result) <= 200
        assert result.endswith(".pdf")

    def test_sanitize_filename_control_chars(self):
        """测试控制字符：应被替换为下划线"""
        result = sanitize_filename("file\x00\x01\x1f\x7f.pdf")
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x1f" not in result
        assert "\x7f" not in result


# ===== test_validate_file_size: 测试文件大小验证 =====

class TestValidateFileSize:
    """测试文件大小验证功能"""

    def test_validate_file_size_normal(self, tmp_path):
        """测试正常文件大小：应在限制范围内通过验证"""
        normal_file = tmp_path / "normal.pdf"
        normal_file.write_bytes(b"%" * 1024)  # 1KB 文件

        # 不应抛出异常
        _validate_file_size(normal_file)

    def test_validate_file_size_empty(self, tmp_path):
        """测试空文件：应抛出 FileValidationError"""
        empty_file = tmp_path / "empty.pdf"
        empty_file.write_bytes(b"")

        with pytest.raises(FileValidationError, match="文件不能为空"):
            _validate_file_size(empty_file)

    def test_validate_file_size_too_large(self, tmp_path):
        """测试超大文件：应抛出 FileValidationError"""
        large_file = tmp_path / "large.pdf"
        large_file.write_bytes(b"%" * 100)  # 先写入一些内容

        with patch("app.validators.file_validator.settings") as mock_settings:
            # 设置极小的文件大小限制（小于当前文件）
            mock_settings.MAX_FILE_SIZE = 50  # 50 字节

            with pytest.raises(FileValidationError, match="文件大小超过限制"):
                _validate_file_size(large_file)

    def test_validate_file_size_nonexistent(self, tmp_path):
        """测试不存在的文件：应抛出 FileValidationError"""
        nonexistent = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileValidationError):
            _validate_file_size(nonexistent)
