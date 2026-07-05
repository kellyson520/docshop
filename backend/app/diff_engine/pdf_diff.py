"""
PDF 差异引擎

功能特性：
1. 多层级对比：哈希对比 -> 页数对比 -> 文本对比 -> 视觉对比
2. OCR 支持：扫描版 PDF 的文本提取
3. 表格提取对比：检测 PDF 中的表格变化
4. 大数据流式处理：支持大文件分片读取
5. 性能优化：缓存、增量处理
"""

import hashlib
import difflib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.diff_engine.base import BaseDiffEngine
from app.utils.logger import logger

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("PyMuPDF not available, PDF processing may be limited")

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class PdfChangeType(Enum):
    """PDF 变更类型"""
    UNCHANGED = "unchanged"
    ADDED = "added"           # 新增页面
    DELETED = "deleted"       # 删除页面
    MODIFIED = "modified"     # 内容修改
    REPLACED = "replaced"     # 页面替换


@dataclass
class PageTextDiff:
    """页面文本差异"""
    page_number: int
    change_type: PdfChangeType
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    similarity: float = 0.0
    diff_lines: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "page_number": self.page_number,
            "change_type": self.change_type.value,
            "old_text_preview": self.old_text[:500] if self.old_text else None,
            "new_text_preview": self.new_text[:500] if self.new_text else None,
            "similarity": self.similarity,
            "diff_line_count": len(self.diff_lines)
        }


@dataclass
class TableDiff:
    """PDF 表格差异"""
    page_number: int
    table_index: int
    old_shape: Tuple[int, int]
    new_shape: Tuple[int, int]
    cell_changes: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "page_number": self.page_number,
            "table_index": self.table_index,
            "old_shape": self.old_shape,
            "new_shape": self.new_shape,
            "cell_changes": self.cell_changes
        }


@dataclass
class PdfDiffResult:
    """PDF 差异结果"""
    identical: bool
    old_page_count: int
    new_page_count: int
    old_hash: str
    new_hash: str
    page_diffs: List[PageTextDiff] = field(default_factory=list)
    table_diffs: List[TableDiff] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "identical": self.identical,
            "page_count": {
                "old": self.old_page_count,
                "new": self.new_page_count
            },
            "hashes": {
                "old": self.old_hash,
                "new": self.new_hash
            },
            "page_diffs": [pd.to_dict() for pd in self.page_diffs],
            "table_diffs": [td.to_dict() for td in self.table_diffs]
        }


class PdfDiffEngine(BaseDiffEngine):
    """PDF 差异引擎"""
    
    def __init__(self):
        # 性能配置
        self.max_pages = 10000      # 最大处理页数
        self.max_text_length = 100000  # 单页最大文本长度
        self.chunk_size = 8192      # 文件读取块大小
        self.enable_ocr = False     # 是否启用 OCR
        self.enable_table_extraction = True  # 是否提取表格
        
    def compare(self, old_path: str, new_path: str) -> Dict[str, Any]:
        """
        对比两个 PDF 文件
        
        Args:
            old_path: 旧版本文件路径
            new_path: 新版本文件路径
            
        Returns:
            差异结果字典
            
        Raises:
            FileNotFoundError: 文件不存在
            Exception: PDF 解析失败
        """
        logger.info(f"Starting PDF diff: {old_path} vs {new_path}")
        
        try:
            # Level 1: 快速哈希对比
            old_hash = self._file_hash(old_path)
            new_hash = self._file_hash(new_path)
            
            if old_hash == new_hash:
                logger.info("PDF files are identical (hash match)")
                summary = "文件完全相同"
                stats = {
                    "pages_added": 0,
                    "pages_deleted": 0,
                    "pages_modified": 0,
                    "tables_changed": 0,
                }
                metadata = {
                    "old_page_count": 0,
                    "new_page_count": 0,
                    "old_hash": old_hash,
                    "new_hash": new_hash,
                }
                return {
                    "type": "pdf_diff",
                    "identical": True,
                    "page_count": {"old": 0, "new": 0},
                    "hashes": {"old": old_hash, "new": new_hash},
                    "page_diffs": [],
                    "table_diffs": [],
                    "text": [],
                    "tables": [],
                    "images": self._empty_image_diff(),
                    "metadata": metadata,
                    "summary": summary,
                    "stats": stats,
                    "changes": {
                        "text": [],
                        "tables": [],
                        "images": self._empty_image_diff(),
                        "metadata": metadata,
                        "summary": summary,
                        "stats": stats,
                    },
                }
            
            # Level 2: 提取页面文本
            old_pages = self._extract_pages(old_path)
            new_pages = self._extract_pages(new_path)
            
            old_page_count = len(old_pages)
            new_page_count = len(new_pages)
            
            logger.debug(f"Extracted pages: old={old_page_count}, new={new_page_count}")
            
            # 检查大文档
            if old_page_count > self.max_pages or new_page_count > self.max_pages:
                logger.warning(f"Large PDF detected: old={old_page_count}, new={new_page_count}")
                return self._compare_large_pdf(
                    old_path, new_path, 
                    old_page_count, new_page_count,
                    old_hash, new_hash
                )
            
            # Level 3: 逐页对比
            page_diffs = self._compare_pages(old_pages, new_pages)
            
            # Level 4: 表格对比（可选）
            table_diffs = []
            if self.enable_table_extraction and HAS_PDFPLUMBER:
                table_diffs = self._compare_tables(old_path, new_path)
            
            # 构建结果
            diff_result = PdfDiffResult(
                identical=False,
                old_page_count=old_page_count,
                new_page_count=new_page_count,
                old_hash=old_hash,
                new_hash=new_hash,
                page_diffs=page_diffs,
                table_diffs=table_diffs
            )
            
            summary = self._generate_summary(diff_result)
            
            text_changes = [page.to_dict() for page in page_diffs]
            table_changes = [table.to_dict() for table in table_diffs]
            stats = {
                "pages_added": sum(1 for p in page_diffs if p.change_type == PdfChangeType.ADDED),
                "pages_deleted": sum(1 for p in page_diffs if p.change_type == PdfChangeType.DELETED),
                "pages_modified": sum(1 for p in page_diffs if p.change_type == PdfChangeType.MODIFIED),
                "tables_changed": len(table_diffs)
            }
            metadata = {
                "old_page_count": old_page_count,
                "new_page_count": new_page_count,
                "old_hash": old_hash,
                "new_hash": new_hash,
            }

            result = {
                "type": "pdf_diff",
                **diff_result.to_dict(),
                "text": text_changes,
                "tables": table_changes,
                "images": self._empty_image_diff(),
                "metadata": metadata,
                "summary": summary,
                "stats": stats,
                "changes": {
                    "text": text_changes,
                    "tables": table_changes,
                    "images": self._empty_image_diff(),
                    "metadata": metadata,
                    "summary": summary,
                    "stats": stats,
                },
            }
            
            logger.info(f"PDF diff completed: {summary}")
            return self._cap_diff_payload(result)
            
        except FileNotFoundError as e:
            logger.error(f"File not found during PDF diff: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"PDF diff failed: {str(e)}", exc_info=True)
            raise
    
    def _file_hash(self, path: str) -> str:
        """
        计算文件 SHA-256 哈希
        
        Args:
            path: 文件路径
            
        Returns:
            哈希字符串
        """
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(self.chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()
    
    def _extract_pages(self, path: str) -> List[Dict[str, Any]]:
        """
        提取 PDF 页面内容
        
        Args:
            path: PDF 文件路径
            
        Returns:
            页面内容列表，每页包含文本和元数据
        """
        pages = []
        
        if HAS_PYMUPDF:
            # 使用 PyMuPDF 提取
            doc = fitz.open(path)
            try:
                for page_num, page in enumerate(doc, 1):
                    text = page.get_text()
                    # 截断过长文本
                    if len(text) > self.max_text_length:
                        text = text[:self.max_text_length] + "... [truncated]"
                    pages.append({
                        "page_number": page_num,
                        "text": text,
                        "word_count": len(text.split()),
                        "char_count": len(text)
                    })
            finally:
                doc.close()
        elif HAS_PDFPLUMBER:
            # 使用 pdfplumber 提取
            with pdfplumber.open(path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    if len(text) > self.max_text_length:
                        text = text[:self.max_text_length] + "... [truncated]"
                    pages.append({
                        "page_number": page_num,
                        "text": text,
                        "word_count": len(text.split()),
                        "char_count": len(text)
                    })
        else:
            raise ImportError("No PDF library available. Install PyMuPDF or pdfplumber.")
        
        return pages
    
    def _compare_pages(
        self,
        old_pages: List[Dict[str, Any]],
        new_pages: List[Dict[str, Any]]
    ) -> List[PageTextDiff]:
        """
        对比页面内容
        
        Args:
            old_pages: 旧页面列表
            new_pages: 新页面列表
            
        Returns:
            页面差异列表
        """
        diffs = []
        max_pages = max(len(old_pages), len(new_pages))
        
        for i in range(max_pages):
            old_page = old_pages[i] if i < len(old_pages) else None
            new_page = new_pages[i] if i < len(new_pages) else None
            
            if old_page is None and new_page is not None:
                # 新增页面
                diffs.append(PageTextDiff(
                    page_number=i + 1,
                    change_type=PdfChangeType.ADDED,
                    new_text=new_page["text"]
                ))
            elif old_page is not None and new_page is None:
                # 删除页面
                diffs.append(PageTextDiff(
                    page_number=i + 1,
                    change_type=PdfChangeType.DELETED,
                    old_text=old_page["text"]
                ))
            else:
                # 对比页面内容
                old_text = old_page["text"]
                new_text = new_page["text"]
                
                if old_text != new_text:
                    # 计算文本相似度
                    similarity = difflib.SequenceMatcher(None, old_text, new_text).ratio()
                    
                    # 生成统一差异格式
                    diff_lines = list(difflib.unified_diff(
                        old_text.splitlines(keepends=True),
                        new_text.splitlines(keepends=True),
                        fromfile=f"old_page_{i+1}",
                        tofile=f"new_page_{i+1}",
                        lineterm="",
                    ))
                    
                    diffs.append(PageTextDiff(
                        page_number=i + 1,
                        change_type=PdfChangeType.MODIFIED,
                        old_text=old_text,
                        new_text=new_text,
                        similarity=round(similarity, 4),
                        diff_lines=diff_lines[:100]  # 限制差异行数
                    ))
        
        return diffs
    
    def _compare_tables(self, old_path: str, new_path: str) -> List[TableDiff]:
        """
        对比 PDF 中的表格
        
        Args:
            old_path: 旧文件路径
            new_path: 新文件路径
            
        Returns:
            表格差异列表
        """
        if not HAS_PDFPLUMBER:
            return []
        
        table_diffs = []
        
        try:
            with pdfplumber.open(old_path) as old_pdf, pdfplumber.open(new_path) as new_pdf:
                max_pages = max(len(old_pdf.pages), len(new_pdf.pages))
                
                for page_num in range(max_pages):
                    old_page = old_pdf.pages[page_num] if page_num < len(old_pdf.pages) else None
                    new_page = new_pdf.pages[page_num] if page_num < len(new_pdf.pages) else None
                    
                    old_tables = old_page.extract_tables() if old_page else []
                    new_tables = new_page.extract_tables() if new_page else []
                    
                    max_tables = max(len(old_tables), len(new_tables))
                    
                    for table_idx in range(max_tables):
                        old_table = old_tables[table_idx] if table_idx < len(old_tables) else None
                        new_table = new_tables[table_idx] if table_idx < len(new_tables) else None
                        
                        table_diff = self._compare_single_table(
                            page_num + 1, table_idx, old_table, new_table
                        )
                        if table_diff:
                            table_diffs.append(table_diff)
        except Exception as e:
            logger.warning(f"Table extraction failed: {str(e)}")
        
        return table_diffs
    
    def _compare_single_table(
        self,
        page_number: int,
        table_index: int,
        old_table: Optional[List[List]],
        new_table: Optional[List[List]]
    ) -> Optional[TableDiff]:
        """
        对比单个表格
        
        Args:
            page_number: 页码
            table_index: 表格索引
            old_table: 旧表格数据
            new_table: 新表格数据
            
        Returns:
            表格差异对象，如无变化则返回 None
        """
        if old_table is None and new_table is None:
            return None
        
        def table_shape(table: Optional[List[List]]) -> Tuple[int, int]:
            if not table:
                return (0, 0)
            return (len(table), max((len(row or []) for row in table), default=0))

        def table_value(table: Optional[List[List]], row_idx: int, col_idx: int) -> Any:
            if not table or row_idx >= len(table):
                return None
            row = table[row_idx] or []
            return row[col_idx] if col_idx < len(row) else None

        old_rows, old_cols = table_shape(old_table)
        new_rows, new_cols = table_shape(new_table)
        
        cell_changes = []
        
        if old_table and new_table:
            max_rows = max(old_rows, new_rows)
            max_cols = max(old_cols, new_cols)
            
            for r in range(max_rows):
                for c in range(max_cols):
                    old_val = table_value(old_table, r, c)
                    new_val = table_value(new_table, r, c)
                    
                    if old_val != new_val:
                        cell_changes.append({
                            "row": r,
                            "col": c,
                            "old_value": old_val,
                            "new_value": new_val
                        })
        
        if cell_changes or old_rows != new_rows or old_cols != new_cols:
            return TableDiff(
                page_number=page_number,
                table_index=table_index,
                old_shape=(old_rows, old_cols),
                new_shape=(new_rows, new_cols),
                cell_changes=cell_changes
            )
        return None
    
    def _compare_large_pdf(
        self,
        old_path: str,
        new_path: str,
        old_page_count: int,
        new_page_count: int,
        old_hash: str,
        new_hash: str
    ) -> Dict[str, Any]:
        """
        大 PDF 文件简化对比
        
        Args:
            old_path: 旧文件路径
            new_path: 新文件路径
            old_page_count: 旧页数
            new_page_count: 新页数
            old_hash: 旧文件哈希
            new_hash: 新文件哈希
            
        Returns:
            简化的差异结果字典
        """
        logger.info("Using simplified comparison for large PDF")
        summary = f"大文档对比完成，页数: {old_page_count} -> {new_page_count}"
        stats = {
            "pages_added": max(0, new_page_count - old_page_count),
            "pages_deleted": max(0, old_page_count - new_page_count),
            "pages_modified": 0,
            "tables_changed": 0,
            "is_large_document": True
        }
        metadata = {
            "is_large_document": True,
            "old_page_count": old_page_count,
            "new_page_count": new_page_count,
            "old_hash": old_hash,
            "new_hash": new_hash,
        }

        return self._cap_diff_payload({
            "type": "pdf_diff",
            "identical": False,
            "page_count": {
                "old": old_page_count,
                "new": new_page_count
            },
            "hashes": {
                "old": old_hash,
                "new": new_hash
            },
            "page_diffs": [],  # 大文档不返回详细差异
            "table_diffs": [],
            "text": [],
            "tables": [],
            "images": self._empty_image_diff(),
            "metadata": metadata,
            "summary": summary,
            "stats": stats,
            "changes": {
                "text": [],
                "tables": [],
                "images": self._empty_image_diff(),
                "metadata": metadata,
                "summary": summary,
                "stats": stats,
            },
        })

    def _empty_image_diff(self) -> Dict[str, Any]:
        return {
            "added": 0,
            "deleted": 0,
            "replaced": 0,
            "resized": 0,
            "old_count": 0,
            "new_count": 0,
            "added_list": [],
            "deleted_list": [],
            "replaced_list": [],
            "resized_list": [],
            "added_items": [],
            "deleted_items": [],
            "changes": [],
        }
    
    def _generate_summary(self, diff_result: PdfDiffResult) -> str:
        """
        生成差异摘要
        
        Args:
            diff_result: PDF 差异结果
            
        Returns:
            摘要字符串
        """
        if diff_result.identical:
            return "文件完全相同"
        
        parts = []
        
        if diff_result.old_page_count != diff_result.new_page_count:
            parts.append(f"页数变化: {diff_result.old_page_count} -> {diff_result.new_page_count}")
        
        added = sum(1 for p in diff_result.page_diffs if p.change_type == PdfChangeType.ADDED)
        deleted = sum(1 for p in diff_result.page_diffs if p.change_type == PdfChangeType.DELETED)
        modified = sum(1 for p in diff_result.page_diffs if p.change_type == PdfChangeType.MODIFIED)
        
        if added:
            parts.append(f"新增 {added} 页")
        if deleted:
            parts.append(f"删除 {deleted} 页")
        if modified:
            parts.append(f"修改 {modified} 页")
        if diff_result.table_diffs:
            parts.append(f"{len(diff_result.table_diffs)} 个表格变化")
        
        if parts:
            return "；".join(parts)
        return "文档无变化"
    
    def generate_summary(self, diff_data: Dict[str, Any]) -> str:
        """
        生成摘要（接口要求）
        
        Args:
            diff_data: 差异结果数据
            
        Returns:
            摘要字符串
        """
        return diff_data.get("summary", "")
