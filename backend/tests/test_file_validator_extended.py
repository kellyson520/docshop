"""
文件验证器扩展测试模块

补充测试文件验证器的未覆盖功能，包括：
- 验证更多文件类型
- 各种Magic Bytes检测
- 内容完整性验证
- 压缩文件验证
- 文件名清理
- 文件信息获取

作者: Test Team
创建日期: 2026-05-28
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.validators.file_validator import (
    validate_file_type,
    _validate_extension,
    _validate_file_size,
    _validate_file_exists,
    _detect_file_type_by_signature,
    _detect_zip_content_type,
    _detect_ole_content_type,
    _validate_file_consistency,
    sanitize_filename,
    get_file_info,
    _format_file_size,
    ALLOWED_MIME_TYPES,
    FILE_TYPE_SIGNATURES,
)
from app.exceptions import FileValidationError


class TestValidateFileType(unittest.TestCase):
    """测试文件类型验证功能"""

    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_pdf_file(self):
        """测试验证PDF文件"""
        pdf_file = Path(self.temp_dir) / "test.pdf"
        # 写入PDF文件头
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")

        result = validate_file_type(pdf_file, "test.pdf")

        self.assertEqual(result, "pdf")

    def test_validate_docx_file(self):
        """测试验证DOCX文件"""
        docx_file = Path(self.temp_dir) / "test.docx"
        # DOCX是ZIP格式，需要创建有效的ZIP结构
        import zipfile
        with zipfile.ZipFile(docx_file, 'w') as zf:
            zf.writestr("word/document.xml", "<w:document></w:document>")
            zf.writestr("[Content_Types].xml", 
                       '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                       '<Default Extension="xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"/>'
                       '</Types>')

        result = validate_file_type(docx_file, "test.docx")

        self.assertEqual(result, "docx")

    def test_validate_xlsx_file(self):
        """测试验证XLSX文件"""
        xlsx_file = Path(self.temp_dir) / "test.xlsx"
        import zipfile
        with zipfile.ZipFile(xlsx_file, 'w') as zf:
            zf.writestr("xl/workbook.xml", "<workbook></workbook>")

        result = validate_file_type(xlsx_file, "test.xlsx")

        self.assertEqual(result, "xlsx")

    def test_validate_unknown_extension(self):
        """测试未知扩展名"""
        test_file = Path(self.temp_dir) / "test.xyz"
        test_file.write_bytes(b"some content")

        with self.assertRaises(FileValidationError) as context:
            validate_file_type(test_file, "test.xyz")

        self.assertIn("不支持的文件类型", str(context.exception))

    def test_validate_missing_extension(self):
        """测试缺少扩展名"""
        test_file = Path(self.temp_dir) / "testfile"
        test_file.write_bytes(b"some content")

        with self.assertRaises(FileValidationError) as context:
            validate_file_type(test_file, "testfile")

        self.assertIn("文件缺少扩展名", str(context.exception))

    def test_validate_empty_file(self):
        """测试空文件"""
        empty_file = Path(self.temp_dir) / "empty.pdf"
        empty_file.write_bytes(b"")

        with self.assertRaises(FileValidationError) as context:
            validate_file_type(empty_file, "empty.pdf")

        self.assertIn("文件不能为空", str(context.exception))

    def test_validate_file_not_found(self):
        """测试文件不存在"""
        non_existent = Path(self.temp_dir) / "not_exist.pdf"

        with self.assertRaises(FileValidationError) as context:
            validate_file_type(non_existent, "not_exist.pdf")

        self.assertIn("文件不存在", str(context.exception))

    def test_validate_type_mismatch(self):
        """测试文件头与扩展名不符"""
        # 创建一个PDF文件但命名为.docx
        fake_docx = Path(self.temp_dir) / "fake.docx"
        fake_docx.write_bytes(b"%PDF-1.4\n")

        with self.assertRaises(FileValidationError) as context:
            validate_file_type(fake_docx, "fake.docx")

        self.assertIn("文件头与扩展名不符", str(context.exception))


class TestValidateExtension(unittest.TestCase):
    """测试扩展名验证"""

    def test_validate_extension_pdf(self):
        """测试PDF扩展名"""
        result = _validate_extension("document.pdf")
        self.assertEqual(result, ".pdf")

    def test_validate_extension_uppercase(self):
        """测试大写扩展名"""
        result = _validate_extension("document.PDF")
        self.assertEqual(result, ".pdf")

    def test_validate_extension_no_extension(self):
        """测试无扩展名"""
        with self.assertRaises(FileValidationError) as context:
            _validate_extension("document")

        self.assertIn("文件缺少扩展名", str(context.exception))

    def test_validate_extension_unsupported(self):
        """测试不支持的扩展名"""
        with self.assertRaises(FileValidationError) as context:
            _validate_extension("document.exe")

        self.assertIn("不支持的文件类型", str(context.exception))


class TestValidateFileSize(unittest.TestCase):
    """测试文件大小验证"""

    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('app.validators.file_validator.settings')
    def test_validate_size_normal(self, mock_settings):
        """测试正常大小"""
        mock_settings.MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_bytes(b"x" * 1000)

        # 不应该抛出异常
        _validate_file_size(test_file)

    @patch('app.validators.file_validator.settings')
    def test_validate_size_empty(self, mock_settings):
        """测试空文件"""
        mock_settings.MAX_FILE_SIZE = 50 * 1024 * 1024

        empty_file = Path(self.temp_dir) / "empty.txt"
        empty_file.write_bytes(b"")

        with self.assertRaises(FileValidationError) as context:
            _validate_file_size(empty_file)

        self.assertIn("文件不能为空", str(context.exception))

    @patch('app.validators.file_validator.settings')
    def test_validate_size_too_large(self, mock_settings):
        """测试文件过大"""
        mock_settings.MAX_FILE_SIZE = 1024  # 1KB

        large_file = Path(self.temp_dir) / "large.txt"
        large_file.write_bytes(b"x" * 2048)

        with self.assertRaises(FileValidationError) as context:
            _validate_file_size(large_file)

        self.assertIn("文件大小超过限制", str(context.exception))


class TestValidateFileExists(unittest.TestCase):
    """测试文件存在性验证"""

    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_exists(self):
        """测试文件存在"""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_bytes(b"content")

        # 不应该抛出异常
        _validate_file_exists(test_file)

    def test_file_not_exists(self):
        """测试文件不存在"""
        non_existent = Path(self.temp_dir) / "not_exist.txt"

        with self.assertRaises(FileValidationError) as context:
            _validate_file_exists(non_existent)

        self.assertIn("文件不存在", str(context.exception))

    def test_path_is_directory(self):
        """测试路径是目录"""
        test_dir = Path(self.temp_dir) / "testdir"
        test_dir.mkdir()

        with self.assertRaises(FileValidationError) as context:
            _validate_file_exists(test_dir)

        self.assertIn("路径不是文件", str(context.exception))

    @patch('os.access')
    def test_file_not_readable(self, mock_access):
        """测试文件不可读"""
        mock_access.return_value = False

        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_bytes(b"content")

        with self.assertRaises(FileValidationError) as context:
            _validate_file_exists(test_file)

        self.assertIn("文件不可读", str(context.exception))


class TestDetectFileTypeBySignature(unittest.TestCase):
    """测试通过文件签名检测类型"""

    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_pdf(self):
        """测试检测PDF"""
        pdf_file = Path(self.temp_dir) / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\n")

        result = _detect_file_type_by_signature(pdf_file)

        self.assertEqual(result, "pdf")

    def test_detect_zip_docx(self):
        """测试检测ZIP中的DOCX"""
        import zipfile
        docx_file = Path(self.temp_dir) / "test.docx"
        with zipfile.ZipFile(docx_file, 'w') as zf:
            zf.writestr("word/document.xml", "<w:document></w:document>")

        result = _detect_file_type_by_signature(docx_file)

        self.assertEqual(result, "docx")

    def test_detect_zip_xlsx(self):
        """测试检测ZIP中的XLSX"""
        import zipfile
        xlsx_file = Path(self.temp_dir) / "test.xlsx"
        with zipfile.ZipFile(xlsx_file, 'w') as zf:
            zf.writestr("xl/workbook.xml", "<workbook></workbook>")

        result = _detect_file_type_by_signature(xlsx_file)

        self.assertEqual(result, "xlsx")

    def test_detect_ole_doc(self):
        """测试检测OLE格式的DOC"""
        doc_file = Path(self.temp_dir) / "test.doc"
        # OLE文件头
        ole_header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"WordDocument" + b"\x00" * 100
        doc_file.write_bytes(ole_header)

        result = _detect_file_type_by_signature(doc_file)

        self.assertEqual(result, "doc")

    def test_detect_ole_xls(self):
        """测试检测OLE格式的XLS"""
        xls_file = Path(self.temp_dir) / "test.xls"
        # OLE文件头 + Workbook标记
        ole_header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"Workbook" + b"\x00" * 100
        xls_file.write_bytes(ole_header)

        result = _detect_file_type_by_signature(xls_file)

        self.assertEqual(result, "xls")

    def test_detect_unknown_format(self):
        """测试未知格式"""
        unknown_file = Path(self.temp_dir) / "test.unknown"
        unknown_file.write_bytes(b"UNKNOWNFILEFORMAT12345")

        with self.assertRaises(FileValidationError) as context:
            _detect_file_type_by_signature(unknown_file)

        self.assertIn("无法识别的文件格式", str(context.exception))

    def test_detect_insufficient_header(self):
        """测试文件头信息不足"""
        small_file = Path(self.temp_dir) / "small.txt"
        small_file.write_bytes(b"AB")  # 少于4字节

        with self.assertRaises(FileValidationError) as context:
            _detect_file_type_by_signature(small_file)

        self.assertIn("文件头信息不足", str(context.exception))


class TestDetectZipContentType(unittest.TestCase):
    """测试ZIP内容类型检测"""

    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_docx_by_document_xml(self):
        """测试通过word/document.xml检测DOCX"""
        import zipfile
        zip_file = Path(self.temp_dir) / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("word/document.xml", "<w:document></w:document>")

        result = _detect_zip_content_type(zip_file)

        self.assertEqual(result, "docx")

    def test_detect_xlsx_by_workbook_xml(self):
        """测试通过xl/workbook.xml检测XLSX"""
        import zipfile
        zip_file = Path(self.temp_dir) / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("xl/workbook.xml", "<workbook></workbook>")

        result = _detect_zip_content_type(zip_file)

        self.assertEqual(result, "xlsx")

    def test_detect_docx_by_content_types(self):
        """测试通过Content_Types.xml检测DOCX"""
        import zipfile
        zip_file = Path(self.temp_dir) / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("[Content_Types].xml", 
                       '<?xml version="1.0"?><Types>'
                       '<Override PartName="/word/document.xml" '
                       'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"/>'
                       '</Types>')

        result = _detect_zip_content_type(zip_file)

        self.assertEqual(result, "docx")

    def test_detect_xlsx_by_content_types(self):
        """测试通过Content_Types.xml检测XLSX"""
        import zipfile
        zip_file = Path(self.temp_dir) / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("[Content_Types].xml", 
                       '<?xml version="1.0"?><Types>'
                       '<Override PartName="/xl/workbook.xml" '
                       'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"/>'
                       '</Types>')

        result = _detect_zip_content_type(zip_file)

        self.assertEqual(result, "xlsx")

    def test_detect_unknown_zip_content(self):
        """测试未知ZIP内容"""
        import zipfile
        zip_file = Path(self.temp_dir) / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("random.txt", "random content")

        with self.assertRaises(FileValidationError) as context:
            _detect_zip_content_type(zip_file)

        self.assertIn("无法识别的 ZIP 文件内容", str(context.exception))

    def test_detect_invalid_zip(self):
        """测试无效ZIP文件"""
        fake_zip = Path(self.temp_dir) / "fake.zip"
        fake_zip.write_bytes(b"Not a valid zip file")

        with self.assertRaises(FileValidationError) as context:
            _detect_zip_content_type(fake_zip)

        self.assertIn("文件不是有效的 ZIP 格式", str(context.exception))


class TestDetectOleContentType(unittest.TestCase):
    """测试OLE内容类型检测"""

    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_doc_by_worddocument(self):
        """测试通过WordDocument检测DOC"""
        ole_file = Path(self.temp_dir) / "test.doc"
        content = b"\xd0\xcf\x11\xe0" + b"WordDocument" + b"\x00" * 100
        ole_file.write_bytes(content)

        result = _detect_ole_content_type(ole_file)

        self.assertEqual(result, "doc")

    def test_detect_xls_by_workbook(self):
        """测试通过Workbook检测XLS"""
        ole_file = Path(self.temp_dir) / "test.xls"
        content = b"\xd0\xcf\x11\xe0" + b"Workbook" + b"\x00" * 100
        ole_file.write_bytes(content)

        result = _detect_ole_content_type(ole_file)

        self.assertEqual(result, "xls")

    def test_detect_xls_by_book(self):
        """测试通过Book检测XLS"""
        ole_file = Path(self.temp_dir) / "test.xls"
        content = b"\xd0\xcf\x11\xe0" + b"Book" + b"\x00" * 100
        ole_file.write_bytes(content)

        result = _detect_ole_content_type(ole_file)

        self.assertEqual(result, "xls")

    def test_detect_unknown_ole_defaults_to_doc(self):
        """????OLE???????????"""
        ole_file = Path(self.temp_dir) / "test.doc"
        content = b"\xd0\xcf\x11\xe0" + b"UnknownStream" + b"\x00" * 100
        ole_file.write_bytes(content)

        with self.assertRaises(FileValidationError):
            _detect_ole_content_type(ole_file)


class TestValidateFileConsistency(unittest.TestCase):
    """测试文件一致性验证"""

    def test_consistent_types(self):
        """测试类型一致"""
        result = _validate_file_consistency(
            Path("/tmp/test.pdf"),
            ".pdf",
            "pdf"
        )

        self.assertEqual(result, "pdf")

    def test_compatible_types_doc_docx(self):
        """测试兼容类型doc-docx"""
        result = _validate_file_consistency(
            Path("/tmp/test.doc"),
            ".doc",
            "docx"
        )

        self.assertEqual(result, "docx")

    def test_compatible_types_xls_xlsx(self):
        """测试兼容类型xls-xlsx"""
        result = _validate_file_consistency(
            Path("/tmp/test.xls"),
            ".xls",
            "xlsx"
        )

        self.assertEqual(result, "xlsx")

    def test_inconsistent_types(self):
        """测试类型不一致"""
        with self.assertRaises(FileValidationError) as context:
            _validate_file_consistency(
                Path("/tmp/test.pdf"),
                ".pdf",
                "docx"
            )

        self.assertIn("文件头与扩展名不符", str(context.exception))


class TestSanitizeFilename(unittest.TestCase):
    """测试文件名清理"""

    def test_sanitize_normal_filename(self):
        """测试正常文件名"""
        result = sanitize_filename("document.pdf")
        self.assertEqual(result, "document.pdf")

    def test_sanitize_dangerous_characters(self):
        """测试危险字符"""
        result = sanitize_filename("file<name>.pdf")
        self.assertEqual(result, "file_name_.pdf")

    def test_sanitize_path_traversal(self):
        """测试路径遍历攻击"""
        result = sanitize_filename("../../../etc/passwd")
        self.assertNotIn("..", result)
        self.assertNotIn("/", result)

    def test_sanitize_hidden_file(self):
        """测试隐藏文件"""
        result = sanitize_filename(".hidden_file")
        self.assertFalse(result.startswith("."))

    def test_sanitize_long_filename(self):
        """测试长文件名"""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name, max_length=200)
        self.assertLessEqual(len(result), 200)
        self.assertTrue(result.endswith(".pdf"))

    def test_sanitize_empty_filename(self):
        """测试空文件名"""
        result = sanitize_filename("")
        self.assertEqual(result, "unnamed_file")

    def test_sanitize_only_extension(self):
        """测试只有扩展名"""
        result = sanitize_filename(".pdf")
        self.assertEqual(result, "pdf")

    def test_sanitize_unicode(self):
        """测试Unicode文件名"""
        result = sanitize_filename("文档_测试.pdf")
        self.assertEqual(result, "文档_测试.pdf")


class TestGetFileInfo(unittest.TestCase):
    """测试获取文件信息"""

    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_file_info_success(self):
        """测试正常获取信息"""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_bytes(b"x" * 1000)

        result = get_file_info(test_file)

        self.assertEqual(result["path"], str(test_file))
        self.assertEqual(result["size"], 1000)
        self.assertIn("size_human", result)
        self.assertIn("created_at", result)
        self.assertIn("modified_at", result)
        self.assertIn("is_readable", result)
        self.assertIn("is_writable", result)

    def test_get_file_info_error(self):
        """测试获取信息错误"""
        non_existent = Path(self.temp_dir) / "not_exist.txt"

        result = get_file_info(non_existent)

        self.assertIn("error", result)


class TestFormatFileSize(unittest.TestCase):
    """测试文件大小格式化"""

    def test_format_bytes(self):
        """测试字节"""
        result = _format_file_size(500)
        self.assertIn("B", result)

    def test_format_kilobytes(self):
        """测试KB"""
        result = _format_file_size(1024)
        self.assertIn("KB", result)

    def test_format_megabytes(self):
        """测试MB"""
        result = _format_file_size(1024 * 1024)
        self.assertIn("MB", result)

    def test_format_gigabytes(self):
        """测试GB"""
        result = _format_file_size(1024 * 1024 * 1024)
        self.assertIn("GB", result)

    def test_format_terabytes(self):
        """测试TB"""
        result = _format_file_size(1024 * 1024 * 1024 * 1024)
        self.assertIn("TB", result)


class TestValidateFileTypeExtended(unittest.TestCase):
    """文件类型验证扩展测试 - 覆盖未覆盖代码行"""

    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_file_type_unsupported(self):
        """测试不支持的文件类型（行81-83）"""
        # 创建一个内容为纯文本但扩展名不在允许列表中的文件
        test_file = Path(self.temp_dir) / "test.exe"
        test_file.write_bytes(b"MZ\x90\x00" + b"\x00" * 100)

        with self.assertRaises(FileValidationError) as context:
            validate_file_type(test_file, "test.exe")

        self.assertIn("不支持的文件类型", str(context.exception))

    def test_validate_file_type_unknown_error(self):
        """测试文件验证过程中的未知错误（行81-83）"""
        # 创建一个有效文件但模拟验证过程出错
        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4\n" + b"\x00" * 100)

        # 模拟 _validate_extension 抛出非 FileValidationError 异常
        with patch('app.validators.file_validator._validate_extension',
                    side_effect=RuntimeError("unexpected error")):
            with self.assertRaises(FileValidationError) as context:
                validate_file_type(test_file, "test.pdf")

            self.assertIn("文件验证失败", str(context.exception))

    def test_detect_zip_content_type_via_content_types_docx(self):
        """测试通过Content_Types.xml检测DOCX（行227-229）"""
        import zipfile
        zip_file = Path(self.temp_dir) / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            # 不包含 word/document.xml 和 xl/workbook.xml
            # 只通过 Content_Types.xml 判断
            zf.writestr("[Content_Types].xml",
                       '<?xml version="1.0"?><Types>'
                       '<Override PartName="/word/document.xml" '
                       'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"/>'
                       '</Types>')

        result = _detect_zip_content_type(zip_file)
        self.assertEqual(result, "docx")

    def test_detect_zip_content_type_via_content_types_xlsx(self):
        """测试通过Content_Types.xml检测XLSX（行227-229）"""
        import zipfile
        zip_file = Path(self.temp_dir) / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.writestr("[Content_Types].xml",
                       '<?xml version="1.0"?><Types>'
                       '<Override PartName="/xl/workbook.xml" '
                       'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"/>'
                       '</Types>')

        result = _detect_zip_content_type(zip_file)
        self.assertEqual(result, "xlsx")

    def test_detect_zip_content_types_parse_error(self):
        """测试Content_Types.xml解析失败时继续（行283-284）"""
        import zipfile
        zip_file = Path(self.temp_dir) / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            # 包含 Content_Types.xml 但内容不包含任何已知类型
            zf.writestr("[Content_Types].xml", "random content")

        # 应抛出未知ZIP内容错误
        with self.assertRaises(FileValidationError):
            _detect_zip_content_type(zip_file)

    def test_detect_ole_content_type_with_olefile(self):
        """测试使用olefile库检测OLE类型（行232-233, 331-342）"""
        ole_file = Path(self.temp_dir) / "test.doc"
        # OLE文件头但不包含 WordDocument 或 Workbook 文本
        content = b"\xd0\xcf\x11\xe0" + b"\x00" * 4086
        ole_file.write_bytes(content)

        # 模拟 olefile 返回空流列表（没有已知流）
        mock_ole = MagicMock()
        mock_ole.listdir.return_value = [["UnknownStream"]]
        mock_olefile_module = MagicMock()
        mock_olefile_module.OleFileIO.return_value = mock_ole

        with patch.dict("sys.modules", {"olefile": mock_olefile_module}):
            import importlib
            import app.validators.file_validator as fv
            importlib.reload(fv)
            try:
                with self.assertRaises(fv.FileValidationError):
                    fv._detect_ole_content_type(ole_file)
                mock_ole.close.assert_called_once()
            finally:
                importlib.reload(fv)

    def test_detect_ole_content_type_olefile_workbook(self):
        """测试使用olefile库检测XLS类型（行331-342）"""
        ole_file = Path(self.temp_dir) / "test.xls"
        # OLE文件头
        ole_file.write_bytes(b"\xd0\xcf\x11\xe0" + b"\x00" * 4086)

        # 模拟 olefile 返回包含 Workbook 的流
        mock_ole = MagicMock()
        mock_ole.listdir.return_value = [["Workbook"]]
        mock_olefile_module = MagicMock()
        mock_olefile_module.OleFileIO.return_value = mock_ole

        with patch.dict("sys.modules", {"olefile": mock_olefile_module}):
            # 需要重新导入以使用 mock
            import importlib
            import app.validators.file_validator as fv
            importlib.reload(fv)
            try:
                result = fv._detect_ole_content_type(ole_file)
                self.assertEqual(result, "xls")
                mock_ole.close.assert_called_once()
            finally:
                importlib.reload(fv)

    def test_detect_ole_content_type_olefile_word(self):
        """测试使用olefile库检测DOC类型（行331-342）"""
        ole_file = Path(self.temp_dir) / "test2.doc"
        ole_file.write_bytes(b"\xd0\xcf\x11\xe0" + b"\x00" * 4086)

        # 模拟 olefile 返回包含 WordDocument 的流
        mock_ole = MagicMock()
        mock_ole.listdir.return_value = [["WordDocument"]]
        mock_olefile_module = MagicMock()
        mock_olefile_module.OleFileIO.return_value = mock_ole

        with patch.dict("sys.modules", {"olefile": mock_olefile_module}):
            import importlib
            import app.validators.file_validator as fv
            importlib.reload(fv)
            try:
                result = fv._detect_ole_content_type(ole_file)
                self.assertEqual(result, "doc")
                mock_ole.close.assert_called_once()
            finally:
                importlib.reload(fv)

    def test_detect_ole_content_type_exception(self):
        """测试OLE检测异常处理"""
        # 创建一个无法读取的文件
        ole_file = Path(self.temp_dir) / "test.doc"
        ole_file.write_bytes(b"\xd0\xcf\x11\xe0" + b"WordDocument" + b"\x00" * 100)

        # 应正常返回（因为 raw bytes 包含 WordDocument）
        result = _detect_ole_content_type(ole_file)
        self.assertEqual(result, "doc")

    def test_detect_ole_content_type_olefile_not_available(self):
        """测试olefile库不可用时回退（行344-348）"""
        ole_file = Path(self.temp_dir) / "test_fallback.doc"
        # OLE文件头但不包含 WordDocument 或 Workbook 文本
        content = b"\xd0\xcf\x11\xe0" + b"\x00" * 4086
        ole_file.write_bytes(content)

        # 模拟 olefile 不可用
        with patch.dict("sys.modules", {"olefile": None}):
            import importlib
            import app.validators.file_validator as fv
            importlib.reload(fv)
            try:
                with self.assertRaises(fv.FileValidationError):
                    fv._detect_ole_content_type(ole_file)
            finally:
                importlib.reload(fv)

    def test_validate_file_consistency_match(self):
        """测试文件一致性验证 - 匹配（行242-244）"""
        result = _validate_file_consistency(
            Path("/tmp/test.docx"),
            ".docx",
            "docx"
        )
        self.assertEqual(result, "docx")

    def test_validate_file_consistency_xls_to_xlsx(self):
        """测试文件一致性验证 - xls到xlsx兼容（行242-244）"""
        result = _validate_file_consistency(
            Path("/tmp/test.xls"),
            ".xls",
            "xlsx"
        )
        self.assertEqual(result, "xlsx")

    def test_validate_content_integrity(self):
        """测试内容完整性验证（行283-284）"""
        # 通过 validate_file_type 间接测试内容完整性
        # 创建一个有效的DOCX文件
        import zipfile
        docx_file = Path(self.temp_dir) / "integrity.docx"
        with zipfile.ZipFile(docx_file, 'w') as zf:
            zf.writestr("word/document.xml", "<w:document></w:document>")
            zf.writestr("[Content_Types].xml",
                       '<?xml version="1.0"?><Types>'
                       '<Default Extension="xml" ContentType="application/xml"/>'
                       '</Types>')

        result = validate_file_type(docx_file, "integrity.docx")
        self.assertEqual(result, "docx")

    def test_sanitize_filename_control_chars(self):
        """测试控制字符处理（行331-342）"""
        # 包含控制字符的文件名
        result = sanitize_filename("file\x00name\x01.pdf")
        self.assertNotIn("\x00", result)
        self.assertNotIn("\x01", result)
        self.assertTrue(result.endswith(".pdf"))

    def test_sanitize_filename_pipe_and_colon(self):
        """测试管道符和冒号处理"""
        result = sanitize_filename("file|name:test.pdf")
        self.assertNotIn("|", result)
        self.assertNotIn(":", result)

    def test_sanitize_filename_consecutive_dots(self):
        """测试连续点号处理"""
        result = sanitize_filename("file...name.pdf")
        self.assertNotIn("...", result)

    def test_sanitize_filename_long_extension(self):
        """测试超长扩展名处理（行447）"""
        # 扩展名很长的情况，导致 max_name_length < 1
        long_ext = ".a" * 100
        result = sanitize_filename("file" + long_ext, max_length=50)
        # max_name_length = 50 - 100 = -50 < 1，所以 sanitized = ext[:max_length]
        self.assertLessEqual(len(result), 50)

    def test_sanitize_filename_only_extension_after_strip(self):
        """测试清理后只剩扩展名的情况（行454）"""
        result = sanitize_filename(".pdf", max_length=200)
        self.assertEqual(result, "pdf")

    def test_sanitize_filename_empty_after_sanitization(self):
        """测试清理后为空的情况（行447, 454）"""
        # 文件名全是危险字符
        result = sanitize_filename("///\\:::**??", max_length=200)
        self.assertTrue(len(result) > 0)

    def test_sanitize_filename_unicode(self):
        """测试Unicode文件名处理（行344-348）"""
        # Unicode文件名应保留
        result = sanitize_filename("文档_测试_2024.pdf")
        self.assertIn("文档", result)
        self.assertIn("测试", result)
        self.assertTrue(result.endswith(".pdf"))

    def test_sanitize_filename_max_length_exact(self):
        """测试文件名长度刚好等于最大长度"""
        name = "a" * 196 + ".pdf"  # 总共200字符
        result = sanitize_filename(name, max_length=200)
        self.assertLessEqual(len(result), 200)

    def test_get_file_info_full(self):
        """测试获取完整文件信息（行447, 454）"""
        test_file = Path(self.temp_dir) / "info_test.txt"
        test_file.write_bytes(b"x" * 2048)

        result = get_file_info(test_file)

        self.assertEqual(result["size"], 2048)
        self.assertIn("size_human", result)
        self.assertIn("created_at", result)
        self.assertIn("modified_at", result)
        self.assertTrue(result["is_readable"])
        self.assertTrue(result["is_writable"])

    def test_get_file_info_nonexistent(self):
        """测试获取不存在文件的信息"""
        non_existent = Path(self.temp_dir) / "nonexistent.txt"

        result = get_file_info(non_existent)

        self.assertIn("error", result)

    def test_detect_file_type_by_signature_with_magic(self):
        """测试使用python-magic检测文件类型（行228-229）"""
        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_bytes(b"UNKNOWNFORMAT" + b"\x00" * 100)

        # 模拟 python-magic 可用并返回已知 MIME 类型
        mock_magic = MagicMock()
        mock_magic.from_file.return_value = "application/pdf"

        with patch.dict("sys.modules", {"magic": mock_magic}):
            result = _detect_file_type_by_signature(test_file)
            self.assertEqual(result, "pdf")

    def test_detect_file_type_by_signature_magic_unknown_mime(self):
        """测试python-magic返回未知MIME类型"""
        test_file = Path(self.temp_dir) / "test.unknown"
        test_file.write_bytes(b"UNKNOWNFORMAT" + b"\x00" * 100)

        mock_magic = MagicMock()
        mock_magic.from_file.return_value = "application/octet-stream"

        with patch.dict("sys.modules", {"magic": mock_magic}):
            with self.assertRaises(FileValidationError):
                _detect_file_type_by_signature(test_file)

    def test_detect_file_type_by_signature_magic_error(self):
        """测试python-magic检测失败时继续"""
        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_bytes(b"UNKNOWNFORMAT" + b"\x00" * 100)

        # 模拟 python-magic 抛出异常
        with patch.dict("sys.modules", {"magic": MagicMock()}):
            import magic as mock_magic
            mock_magic.from_file.side_effect = Exception("magic error")
            with patch.dict("sys.modules", {"magic": mock_magic}):
                with self.assertRaises(FileValidationError):
                    _detect_file_type_by_signature(test_file)

    def test_validate_file_size_check_failed(self):
        """测试文件大小检查失败（行283-284）"""
        test_file = Path(self.temp_dir) / "test.txt"

        # 模拟 stat 抛出异常
        with patch.object(Path, 'stat', side_effect=OSError("Permission denied")):
            with self.assertRaises(FileValidationError) as context:
                _validate_file_size(test_file)

            self.assertIn("无法读取文件大小", str(context.exception))

    def test_detect_file_type_signature_check_failed(self):
        """测试文件签名检测失败"""
        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4\n")

        # 模拟文件读取失败
        with patch("builtins.open", side_effect=IOError("Read error")):
            with self.assertRaises(FileValidationError) as context:
                _detect_file_type_by_signature(test_file)

            self.assertIn("文件签名检测失败", str(context.exception))


if __name__ == "__main__":
    unittest.main()
