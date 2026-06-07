"""
PDF差异引擎测试模块

测试PDF文档差异引擎的所有功能，包括：
- 对比两个PDF文件
- 文件哈希对比
- 文本提取和对比
- 表格提取和对比
- 大PDF文件处理

作者: Test Team
创建日期: 2026-05-28
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.diff_engine.pdf_diff import (
    PdfDiffEngine,
    PdfChangeType,
    PageTextDiff,
    TableDiff,
    PdfDiffResult,
)


class TestPdfChangeType(unittest.TestCase):
    """测试PDF变更类型枚举"""
    
    def test_change_type_values(self):
        """测试变更类型值"""
        self.assertEqual(PdfChangeType.UNCHANGED.value, "unchanged")
        self.assertEqual(PdfChangeType.ADDED.value, "added")
        self.assertEqual(PdfChangeType.DELETED.value, "deleted")
        self.assertEqual(PdfChangeType.MODIFIED.value, "modified")
        self.assertEqual(PdfChangeType.REPLACED.value, "replaced")


class TestPageTextDiff(unittest.TestCase):
    """测试页面文本差异类"""
    
    def test_to_dict_unchanged(self):
        """测试未变化页面"""
        page_diff = PageTextDiff(
            page_number=1,
            change_type=PdfChangeType.UNCHANGED
        )
        result = page_diff.to_dict()
        
        self.assertEqual(result["page_number"], 1)
        self.assertEqual(result["change_type"], "unchanged")
        self.assertIsNone(result["old_text_preview"])
        self.assertIsNone(result["new_text_preview"])
        
    def test_to_dict_added(self):
        """测试新增页面"""
        page_diff = PageTextDiff(
            page_number=2,
            change_type=PdfChangeType.ADDED,
            new_text="新增页面内容"
        )
        result = page_diff.to_dict()
        
        self.assertEqual(result["change_type"], "added")
        self.assertIsNone(result["old_text_preview"])
        self.assertEqual(result["new_text_preview"], "新增页面内容")
        
    def test_to_dict_modified(self):
        """测试修改页面"""
        page_diff = PageTextDiff(
            page_number=3,
            change_type=PdfChangeType.MODIFIED,
            old_text="旧内容",
            new_text="新内容",
            similarity=0.75,
            diff_lines=["- 删除行", "+ 新增行"]
        )
        result = page_diff.to_dict()
        
        self.assertEqual(result["change_type"], "modified")
        self.assertEqual(result["old_text_preview"], "旧内容")
        self.assertEqual(result["new_text_preview"], "新内容")
        self.assertEqual(result["similarity"], 0.75)
        self.assertEqual(result["diff_line_count"], 2)
        
    def test_to_dict_long_text_truncated(self):
        """测试长文本截断"""
        long_text = "x" * 1000
        page_diff = PageTextDiff(
            page_number=1,
            change_type=PdfChangeType.MODIFIED,
            old_text=long_text,
            new_text=long_text
        )
        result = page_diff.to_dict()
        
        # 应该被截断到500字符
        self.assertEqual(len(result["old_text_preview"]), 500)
        self.assertEqual(len(result["new_text_preview"]), 500)


class TestTableDiff(unittest.TestCase):
    """测试表格差异类"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        table_diff = TableDiff(
            page_number=1,
            table_index=0,
            old_shape=(3, 4),
            new_shape=(3, 5),
            cell_changes=[
                {"row": 0, "col": 4, "old_value": None, "new_value": "新增"}
            ]
        )
        result = table_diff.to_dict()
        
        self.assertEqual(result["page_number"], 1)
        self.assertEqual(result["table_index"], 0)
        self.assertEqual(result["old_shape"], (3, 4))
        self.assertEqual(result["new_shape"], (3, 5))
        self.assertEqual(len(result["cell_changes"]), 1)


class TestPdfDiffResult(unittest.TestCase):
    """测试PDF差异结果类"""
    
    def test_to_dict_identical(self):
        """测试相同文件结果"""
        result = PdfDiffResult(
            identical=True,
            old_page_count=5,
            new_page_count=5,
            old_hash="abc123",
            new_hash="abc123"
        )
        result_dict = result.to_dict()
        
        self.assertTrue(result_dict["identical"])
        self.assertEqual(result_dict["page_count"]["old"], 5)
        self.assertEqual(result_dict["page_count"]["new"], 5)
        self.assertEqual(result_dict["hashes"]["old"], "abc123")
        self.assertEqual(result_dict["hashes"]["new"], "abc123")
        
    def test_to_dict_with_diffs(self):
        """测试包含差异的结果"""
        page_diffs = [
            PageTextDiff(1, PdfChangeType.MODIFIED, "旧", "新")
        ]
        table_diffs = [
            TableDiff(1, 0, (2, 2), (2, 2))
        ]
        result = PdfDiffResult(
            identical=False,
            old_page_count=3,
            new_page_count=3,
            old_hash="hash1",
            new_hash="hash2",
            page_diffs=page_diffs,
            table_diffs=table_diffs
        )
        result_dict = result.to_dict()
        
        self.assertFalse(result_dict["identical"])
        self.assertEqual(len(result_dict["page_diffs"]), 1)
        self.assertEqual(len(result_dict["table_diffs"]), 1)


class TestPdfDiffEngineInit(unittest.TestCase):
    """测试PDF差异引擎初始化"""
    
    def test_init_default(self):
        """测试默认初始化"""
        engine = PdfDiffEngine()
        
        self.assertEqual(engine.max_pages, 10000)
        self.assertEqual(engine.max_text_length, 100000)
        self.assertEqual(engine.chunk_size, 8192)
        self.assertFalse(engine.enable_ocr)
        self.assertTrue(engine.enable_table_extraction)


class TestPdfDiffEngineFileHash(unittest.TestCase):
    """测试文件哈希计算"""
    
    def setUp(self):
        """创建临时文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.pdf"
        self.test_file.write_bytes(b"PDF test content")
        
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_file_hash_small_file(self):
        """测试小文件哈希"""
        engine = PdfDiffEngine()
        
        hash_result = engine._file_hash(str(self.test_file))
        
        self.assertEqual(len(hash_result), 64)  # SHA-256长度
        
    def test_file_hash_large_file(self):
        """测试大文件分块哈希"""
        engine = PdfDiffEngine()
        engine.chunk_size = 8  # 设置小块大小
        
        # 创建大文件
        large_file = Path(self.temp_dir) / "large.pdf"
        large_file.write_bytes(b"x" * 1000)
        
        hash_result = engine._file_hash(str(large_file))
        
        self.assertEqual(len(hash_result), 64)


class TestPdfDiffEngineComparePages(unittest.TestCase):
    """测试页面对比功能"""
    
    def test_compare_equal_pages(self):
        """测试相同页面"""
        engine = PdfDiffEngine()
        
        old_pages = [
            {"page_number": 1, "text": "内容相同", "word_count": 2, "char_count": 4}
        ]
        new_pages = [
            {"page_number": 1, "text": "内容相同", "word_count": 2, "char_count": 4}
        ]
        
        result = engine._compare_pages(old_pages, new_pages)
        
        # 相同页面不产生差异记录
        self.assertEqual(len(result), 0)
        
    def test_compare_added_page(self):
        """测试新增页面"""
        engine = PdfDiffEngine()
        
        old_pages = [
            {"page_number": 1, "text": "第一页", "word_count": 1, "char_count": 3}
        ]
        new_pages = [
            {"page_number": 1, "text": "第一页", "word_count": 1, "char_count": 3},
            {"page_number": 2, "text": "第二页", "word_count": 1, "char_count": 3}
        ]
        
        result = engine._compare_pages(old_pages, new_pages)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].change_type, PdfChangeType.ADDED)
        self.assertEqual(result[0].page_number, 2)
        
    def test_compare_deleted_page(self):
        """测试删除页面"""
        engine = PdfDiffEngine()
        
        old_pages = [
            {"page_number": 1, "text": "第一页", "word_count": 1, "char_count": 3},
            {"page_number": 2, "text": "第二页", "word_count": 1, "char_count": 3}
        ]
        new_pages = [
            {"page_number": 1, "text": "第一页", "word_count": 1, "char_count": 3}
        ]
        
        result = engine._compare_pages(old_pages, new_pages)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].change_type, PdfChangeType.DELETED)
        self.assertEqual(result[0].page_number, 2)
        
    def test_compare_modified_page(self):
        """测试修改页面"""
        engine = PdfDiffEngine()
        
        old_pages = [
            {"page_number": 1, "text": "旧内容", "word_count": 1, "char_count": 3}
        ]
        new_pages = [
            {"page_number": 1, "text": "新内容", "word_count": 1, "char_count": 3}
        ]
        
        result = engine._compare_pages(old_pages, new_pages)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].change_type, PdfChangeType.MODIFIED)
        self.assertIn("old_text", result[0].__dict__)
        self.assertIn("new_text", result[0].__dict__)
        self.assertIn("similarity", result[0].__dict__)
        
    def test_compare_multiple_changes(self):
        """测试多种变化"""
        engine = PdfDiffEngine()
        
        old_pages = [
            {"page_number": 1, "text": "第一页", "word_count": 1, "char_count": 3},
            {"page_number": 2, "text": "删除页", "word_count": 1, "char_count": 3}
        ]
        new_pages = [
            {"page_number": 1, "text": "第一页修改", "word_count": 1, "char_count": 5},
            {"page_number": 2, "text": "新增页", "word_count": 1, "char_count": 3}
        ]
        
        result = engine._compare_pages(old_pages, new_pages)
        
        self.assertEqual(len(result), 2)
        change_types = [r.change_type for r in result]
        self.assertIn(PdfChangeType.MODIFIED, change_types)


class TestPdfDiffEngineCompareSingleTable(unittest.TestCase):
    """测试单个表格对比"""
    
    def test_compare_both_none(self):
        """测试两个都为空"""
        engine = PdfDiffEngine()
        
        result = engine._compare_single_table(1, 0, None, None)
        
        self.assertIsNone(result)
        
    def test_compare_old_none(self):
        """测试旧表格为空"""
        engine = PdfDiffEngine()
        
        new_table = [["A1", "B1"], ["A2", "B2"]]
        result = engine._compare_single_table(1, 0, None, new_table)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.page_number, 1)
        self.assertEqual(result.table_index, 0)
        self.assertEqual(result.old_shape, (0, 0))
        self.assertEqual(result.new_shape, (2, 2))
        
    def test_compare_new_none(self):
        """测试新表格为空"""
        engine = PdfDiffEngine()
        
        old_table = [["A1", "B1"], ["A2", "B2"]]
        result = engine._compare_single_table(1, 0, old_table, None)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.old_shape, (2, 2))
        self.assertEqual(result.new_shape, (0, 0))
        
    def test_compare_no_change(self):
        """测试无变化"""
        engine = PdfDiffEngine()
        
        old_table = [["A1", "B1"], ["A2", "B2"]]
        new_table = [["A1", "B1"], ["A2", "B2"]]
        
        result = engine._compare_single_table(1, 0, old_table, new_table)
        
        self.assertIsNone(result)
        
    def test_compare_cell_change(self):
        """测试单元格变化"""
        engine = PdfDiffEngine()
        
        old_table = [["A1", "B1"], ["A2", "B2"]]
        new_table = [["A1", "B1"], ["A2", "修改"]]
        
        result = engine._compare_single_table(1, 0, old_table, new_table)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result.cell_changes), 1)
        self.assertEqual(result.cell_changes[0]["old_value"], "B2")
        self.assertEqual(result.cell_changes[0]["new_value"], "修改")
        
    def test_compare_structure_change(self):
        """测试结构变化"""
        engine = PdfDiffEngine()
        
        old_table = [["A1", "B1"]]
        new_table = [["A1", "B1"], ["A2", "B2"]]
        
        result = engine._compare_single_table(1, 0, old_table, new_table)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.old_shape, (1, 2))
        self.assertEqual(result.new_shape, (2, 2))


class TestPdfDiffEngineCompareLargePdf(unittest.TestCase):
    """测试大PDF对比"""
    
    def test_compare_large_pdf(self):
        """测试大PDF简化对比"""
        engine = PdfDiffEngine()
        
        result = engine._compare_large_pdf(
            old_path="/path/old.pdf",
            new_path="/path/new.pdf",
            old_page_count=1000,
            new_page_count=1200,
            old_hash="hash1",
            new_hash="hash2"
        )
        
        self.assertEqual(result["type"], "pdf_diff")
        self.assertFalse(result["identical"])
        self.assertEqual(result["page_count"]["old"], 1000)
        self.assertEqual(result["page_count"]["new"], 1200)
        self.assertEqual(result["hashes"]["old"], "hash1")
        self.assertEqual(result["hashes"]["new"], "hash2")
        self.assertTrue(result["stats"]["is_large_document"])
        self.assertIn("text", result)
        self.assertIn("tables", result)
        self.assertIn("images", result)
        self.assertIn("metadata", result)
        self.assertIn("changes", result)
        self.assertIn("summary", result["changes"])
        self.assertIn("stats", result["changes"])
        self.assertEqual(len(result["page_diffs"]), 0)  # 大文档不返回详细差异


class TestPdfDiffEngineGenerateSummary(unittest.TestCase):
    """测试生成摘要功能"""
    
    def test_generate_summary_identical(self):
        """测试相同文件摘要"""
        engine = PdfDiffEngine()
        
        diff_result = PdfDiffResult(
            identical=True,
            old_page_count=5,
            new_page_count=5,
            old_hash="hash",
            new_hash="hash"
        )
        
        result = engine._generate_summary(diff_result)
        
        self.assertEqual(result, "文件完全相同")
        
    def test_generate_summary_page_count_change(self):
        """测试页数变化摘要"""
        engine = PdfDiffEngine()
        
        diff_result = PdfDiffResult(
            identical=False,
            old_page_count=5,
            new_page_count=8,
            old_hash="hash1",
            new_hash="hash2"
        )
        
        result = engine._generate_summary(diff_result)
        
        self.assertIn("页数变化", result)
        self.assertIn("5", result)
        self.assertIn("8", result)
        
    def test_generate_summary_with_changes(self):
        """测试包含各种变化的摘要"""
        engine = PdfDiffEngine()
        
        page_diffs = [
            PageTextDiff(1, PdfChangeType.ADDED, new_text="新增页"),
            PageTextDiff(2, PdfChangeType.DELETED, old_text="删除页"),
            PageTextDiff(3, PdfChangeType.MODIFIED, old_text="旧", new_text="新"),
        ]
        table_diffs = [TableDiff(1, 0, (2, 2), (2, 2))]
        
        diff_result = PdfDiffResult(
            identical=False,
            old_page_count=5,
            new_page_count=5,
            old_hash="hash1",
            new_hash="hash2",
            page_diffs=page_diffs,
            table_diffs=table_diffs
        )
        
        result = engine._generate_summary(diff_result)
        
        self.assertIn("新增", result)
        self.assertIn("删除", result)
        self.assertIn("修改", result)
        self.assertIn("表格", result)
        
    def test_generate_summary_interface(self):
        """测试接口要求的generate_summary方法"""
        engine = PdfDiffEngine()
        
        diff_data = {"summary": "测试摘要"}
        result = engine.generate_summary(diff_data)
        
        self.assertEqual(result, "测试摘要")
        
    def test_generate_summary_interface_empty(self):
        """测试无摘要时的接口方法"""
        engine = PdfDiffEngine()
        
        diff_data = {}
        result = engine.generate_summary(diff_data)
        
        self.assertEqual(result, "")


class TestPdfDiffEngineCompare(unittest.TestCase):
    """测试主对比功能"""
    
    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    @patch('app.diff_engine.pdf_diff.HAS_PYMUPDF', True)
    @patch('app.diff_engine.pdf_diff.fitz')
    def test_compare_identical_files(self, mock_fitz):
        """测试相同文件对比"""
        engine = PdfDiffEngine()
        
        # 创建相同内容的文件
        old_path = Path(self.temp_dir) / "old.pdf"
        new_path = Path(self.temp_dir) / "new.pdf"
        old_path.write_bytes(b"same content")
        new_path.write_bytes(b"same content")
        
        result = engine.compare(str(old_path), str(new_path))
        
        self.assertTrue(result["identical"])
        self.assertEqual(result["summary"], "文件完全相同")
        self.assertIn("text", result)
        self.assertIn("tables", result)
        self.assertIn("images", result)
        self.assertIn("metadata", result)
        self.assertIn("changes", result)
        self.assertIn("summary", result["changes"])
        self.assertIn("stats", result["changes"])
        
    @patch('app.diff_engine.pdf_diff.HAS_PYMUPDF', True)
    @patch('app.diff_engine.pdf_diff.fitz')
    def test_compare_different_files(self, mock_fitz):
        """测试不同文件对比"""
        engine = PdfDiffEngine()
        
        # 模拟PDF文档
        mock_doc = Mock()
        mock_page = Mock()
        mock_page.get_text.return_value = "测试文本"
        mock_doc.__iter__ = Mock(return_value=iter([mock_page]))
        mock_doc.close = Mock()
        mock_fitz.open.return_value = mock_doc
        
        # 创建不同内容的文件
        old_path = Path(self.temp_dir) / "old.pdf"
        new_path = Path(self.temp_dir) / "new.pdf"
        old_path.write_bytes(b"content 1")
        new_path.write_bytes(b"content 2")
        
        result = engine.compare(str(old_path), str(new_path))
        
        self.assertFalse(result["identical"])
        self.assertIn("page_count", result)
        
    @patch('app.diff_engine.pdf_diff.HAS_PYMUPDF', True)
    @patch('app.diff_engine.pdf_diff.HAS_PDFPLUMBER', False)
    @patch('app.diff_engine.pdf_diff.fitz')
    def test_compare_large_document(self, mock_fitz):
        """测试大文档对比"""
        engine = PdfDiffEngine()
        engine.max_pages = 5  # 设置较小阈值
        
        # 模拟PDF文档（超过阈值）
        mock_doc = Mock()
        mock_pages = [Mock() for _ in range(10)]
        for mock_page in mock_pages:
            mock_page.get_text.return_value = "测试文本"
        mock_doc.__iter__ = Mock(return_value=iter(mock_pages))
        mock_doc.close = Mock()
        mock_fitz.open.return_value = mock_doc
        
        old_path = Path(self.temp_dir) / "old.pdf"
        new_path = Path(self.temp_dir) / "new.pdf"
        old_path.write_bytes(b"content 1")
        new_path.write_bytes(b"content 2")
        
        result = engine.compare(str(old_path), str(new_path))
        
        self.assertTrue(result["stats"]["is_large_document"])
        
    def test_compare_file_not_found(self):
        """测试文件不存在"""
        engine = PdfDiffEngine()
        
        with self.assertRaises(FileNotFoundError):
            engine.compare("/nonexistent/old.pdf", "/nonexistent/new.pdf")
            
    @patch('app.diff_engine.pdf_diff.HAS_PYMUPDF', False)
    @patch('app.diff_engine.pdf_diff.HAS_PDFPLUMBER', False)
    def test_compare_no_library(self):
        """测试无PDF库可用"""
        engine = PdfDiffEngine()
        
        old_path = Path(self.temp_dir) / "old.pdf"
        new_path = Path(self.temp_dir) / "new.pdf"
        old_path.write_bytes(b"content 1")
        new_path.write_bytes(b"content 2")
        
        with self.assertRaises(ImportError):
            engine.compare(str(old_path), str(new_path))


if __name__ == "__main__":
    unittest.main()
