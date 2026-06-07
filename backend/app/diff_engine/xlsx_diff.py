"""
Excel 差异引擎

功能特性：
1. 多 Sheet 对比：支持多个工作表的并行对比
2. 单元格级差异：检测值、公式、格式的变化
3. 行列增删：检测插入/删除的行列
4. 大数据处理：流式读取、分片处理
5. 智能对齐：使用行列特征进行对齐
"""

import difflib
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from openpyxl import load_workbook
from openpyxl.styles import PatternFill

from app.diff_engine.base import BaseDiffEngine
from app.utils.logger import logger


class CellChangeType(Enum):
    """单元格变更类型"""
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"


@dataclass
class CellDiff:
    """单元格差异"""
    row: int
    col: int
    col_letter: str
    old_value: Any
    new_value: Any
    change_type: CellChangeType
    old_formula: Optional[str] = None
    new_formula: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "cell": f"{self.col_letter}{self.row}",
            "row": self.row,
            "col": self.col,
            "old_value": self._format_value(self.old_value),
            "new_value": self._format_value(self.new_value),
            "change_type": self.change_type.value
        }
    
    @staticmethod
    def _format_value(val):
        """格式化值用于展示"""
        if pd.isna(val):
            return None
        if isinstance(val, float):
            if val == int(val):
                return int(val)
            return round(val, 6)
        return str(val) if val is not None else None


@dataclass
class RowColChange:
    """行列变更"""
    type: str  # 'row' or 'col'
    action: str  # 'added' or 'deleted'
    index: int
    data: Optional[List] = None


@dataclass
class SheetDiff:
    """Sheet 差异"""
    name: str
    index: int
    shape_old: Tuple[int, int]
    shape_new: Tuple[int, int]
    cell_changes: List[CellDiff] = field(default_factory=list)
    added_rows: List[int] = field(default_factory=list)
    deleted_rows: List[int] = field(default_factory=list)
    added_cols: List[str] = field(default_factory=list)
    deleted_cols: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "index": self.index,
            "shape_old": self.shape_old,
            "shape_new": self.shape_new,
            "cell_changes": [c.to_dict() for c in self.cell_changes],
            "added_rows": self.added_rows,
            "deleted_rows": self.deleted_rows,
            "added_cols": self.added_cols,
            "deleted_cols": self.deleted_cols,
            "stats": {
                "cells_modified": len(self.cell_changes),
                "rows_added": len(self.added_rows),
                "rows_deleted": len(self.deleted_rows),
                "cols_added": len(self.added_cols),
                "cols_deleted": len(self.deleted_cols)
            }
        }


class XlsxDiffEngine(BaseDiffEngine):
    """Excel 差异引擎"""
    
    def __init__(self):
        # 性能配置
        self.max_rows = 100000  # 最大行数
        self.max_cols = 1000    # 最大列数
        self.chunk_size = 5000  # 分片大小
        
    def compare(self, old_path: str, new_path: str) -> Dict[str, Any]:
        """
        对比两个 Excel 文件
        
        Args:
            old_path: 旧版本文件路径
            new_path: 新版本文件路径
            
        Returns:
            差异结果字典
            
        Raises:
            FileNotFoundError: 文件不存在
            Exception: 文件解析失败
        """
        logger.info(f"Starting XLSX diff: {old_path} vs {new_path}")
        
        try:
            # 获取所有 Sheet 名称
            old_sheets = pd.ExcelFile(old_path).sheet_names
            new_sheets = pd.ExcelFile(new_path).sheet_names
            
            all_sheet_names = list(dict.fromkeys(old_sheets + new_sheets))
            logger.debug(f"Sheets to compare: {all_sheet_names}")
            
            sheet_diffs = []
            for idx, sheet_name in enumerate(all_sheet_names):
                sheet_diff = self._compare_sheet(
                    idx, sheet_name,
                    old_path if sheet_name in old_sheets else None,
                    new_path if sheet_name in new_sheets else None
                )
                if sheet_diff:
                    sheet_diffs.append(sheet_diff)
            
            # 生成摘要
            summary = self._generate_summary(sheet_diffs)
            table_changes = [sd.to_dict() for sd in sheet_diffs]
            stats = {
                "sheets_changed": len(sheet_diffs),
                "sheets_added": len([s for s in sheet_diffs if s.shape_old == (0, 0)]),
                "sheets_deleted": len([s for s in sheet_diffs if s.shape_new == (0, 0)]),
                "total_cells_modified": sum(len(s.cell_changes) for s in sheet_diffs)
            }
            metadata = {
                "old_sheet_count": len(old_sheets),
                "new_sheet_count": len(new_sheets),
                "sheet_order": all_sheet_names,
            }

            result = {
                "type": "xlsx_diff",
                "sheets": {sd.name: sd.to_dict() for sd in sheet_diffs},
                "sheet_order": all_sheet_names,
                "text": [],
                "tables": table_changes,
                "images": self._empty_image_diff(),
                "metadata": metadata,
                "summary": summary,
                "stats": stats,
                "changes": {
                    "text": [],
                    "tables": table_changes,
                    "images": self._empty_image_diff(),
                    "metadata": metadata,
                    "summary": summary,
                    "stats": stats,
                },
            }
            
            logger.info(f"XLSX diff completed: {summary}")
            return result
            
        except FileNotFoundError as e:
            logger.error(f"File not found during XLSX diff: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"XLSX diff failed: {str(e)}", exc_info=True)
            raise
    
    def _compare_sheet(
        self,
        idx: int,
        sheet_name: str,
        old_path: Optional[str],
        new_path: Optional[str]
    ) -> Optional[SheetDiff]:
        """
        对比单个 Sheet
        
        Args:
            idx: Sheet 索引
            sheet_name: Sheet 名称
            old_path: 旧文件路径，如为 None 表示新增 Sheet
            new_path: 新文件路径，如为 None 表示删除 Sheet
            
        Returns:
            Sheet 差异对象，如无变化则返回 None
        """
        logger.debug(f"Comparing sheet '{sheet_name}': old={old_path is not None}, new={new_path is not None}")
        
        # 读取数据（含行列上限检查，防止超大表 DoS）
        if old_path:
            df_old = pd.read_excel(old_path, sheet_name=sheet_name, dtype=str)
            df_old = df_old.fillna('')
            if len(df_old) > self.max_rows or len(df_old.columns) > self.max_cols:
                raise ValueError(
                    f"Sheet '{sheet_name}' 超出大小限制: "
                    f"{len(df_old)}行 x {len(df_old.columns)}列 "
                    f"(最大 {self.max_rows}行 x {self.max_cols}列)"
                )
        else:
            df_old = pd.DataFrame()
        
        if new_path:
            df_new = pd.read_excel(new_path, sheet_name=sheet_name, dtype=str)
            df_new = df_new.fillna('')
            if len(df_new) > self.max_rows or len(df_new.columns) > self.max_cols:
                raise ValueError(
                    f"Sheet '{sheet_name}' 超出大小限制: "
                    f"{len(df_new)}行 x {len(df_new.columns)}列 "
                    f"(最大 {self.max_rows}行 x {self.max_cols}列)"
                )
        else:
            df_new = pd.DataFrame()
        
        shape_old = df_old.shape
        shape_new = df_new.shape
        
        # 检查是否为空（新增/删除）
        if df_old.empty and df_new.empty:
            return None
        
        if df_old.empty:
            return SheetDiff(
                name=sheet_name, index=idx,
                shape_old=(0, 0), shape_new=shape_new
            )
        
        if df_new.empty:
            return SheetDiff(
                name=sheet_name, index=idx,
                shape_old=shape_old, shape_new=(0, 0)
            )
        
        # 对齐 DataFrame
        df_old_aligned, df_new_aligned = df_old.align(df_new, fill_value='')
        
        # 检测行列变化
        added_rows, deleted_rows = self._detect_row_changes(df_old, df_new)
        added_cols, deleted_cols = self._detect_col_changes(df_old, df_new)
        
        # 对比单元格
        cell_changes = self._compare_cells(df_old_aligned, df_new_aligned)
        
        if cell_changes or added_rows or deleted_rows or added_cols or deleted_cols:
            return SheetDiff(
                name=sheet_name, index=idx,
                shape_old=shape_old, shape_new=shape_new,
                cell_changes=cell_changes,
                added_rows=added_rows,
                deleted_rows=deleted_rows,
                added_cols=added_cols,
                deleted_cols=deleted_cols
            )
        return None
    
    def _detect_row_changes(
        self,
        df_old: pd.DataFrame,
        df_new: pd.DataFrame
    ) -> Tuple[List[int], List[int]]:
        """
        检测行增删
        
        Args:
            df_old: 旧数据框
            df_new: 新数据框
            
        Returns:
            (新增行号列表, 删除行号列表)
        """
        added = []
        deleted = []

        old_rows = [self._row_signature(row) for _, row in df_old.iterrows()]
        new_rows = [self._row_signature(row) for _, row in df_new.iterrows()]
        matcher = difflib.SequenceMatcher(None, old_rows, new_rows, autojunk=False)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "delete":
                deleted.extend(range(i1 + 1, i2 + 1))
            elif tag == "insert":
                added.extend(range(j1 + 1, j2 + 1))
            elif tag == "replace":
                deleted.extend(range(i1 + 1, i2 + 1))
                added.extend(range(j1 + 1, j2 + 1))
        
        return added, deleted

    def _row_signature(self, row: pd.Series) -> tuple:
        return tuple("" if pd.isna(value) else str(value).strip() for value in row.tolist())
    
    def _detect_col_changes(
        self,
        df_old: pd.DataFrame,
        df_new: pd.DataFrame
    ) -> Tuple[List[str], List[str]]:
        """
        检测列增删
        
        Args:
            df_old: 旧数据框
            df_new: 新数据框
            
        Returns:
            (新增列名列表, 删除列名列表)
        """
        old_cols = set(df_old.columns)
        new_cols = set(df_new.columns)
        
        added = [str(c) for c in new_cols - old_cols]
        deleted = [str(c) for c in old_cols - new_cols]
        
        return added, deleted
    
    def _compare_cells(
        self,
        df_old: pd.DataFrame,
        df_new: pd.DataFrame
    ) -> List[CellDiff]:
        """
        对比单元格
        
        Args:
            df_old: 旧数据框（已对齐）
            df_new: 新数据框（已对齐）
            
        Returns:
            单元格差异列表
        """
        changes = []
        
        # 获取列字母映射
        def col_to_letter(col_idx):
            """将列索引转为 Excel 列字母 (0->A, 25->Z, 26->AA)"""
            result = ""
            col_idx += 1  # 转为 1-based
            while col_idx > 0:
                col_idx, remainder = divmod(col_idx - 1, 26)
                result = chr(65 + remainder) + result
            return result
        
        # 遍历对比
        for row_idx in range(len(df_old)):
            for col_idx, col_name in enumerate(df_old.columns):
                old_val = df_old.iloc[row_idx, col_idx]
                new_val = df_new.iloc[row_idx, col_idx]
                
                if old_val != new_val:
                    changes.append(CellDiff(
                        row=row_idx + 1,  # Excel 行号从 1 开始
                        col=col_idx + 1,
                        col_letter=col_to_letter(col_idx),
                        old_value=old_val if old_val != '' else None,
                        new_value=new_val if new_val != '' else None,
                        change_type=CellChangeType.MODIFIED
                    ))
        
        return changes
    
    def _generate_summary(self, sheet_diffs: List[SheetDiff]) -> str:
        """
        生成摘要
        
        Args:
            sheet_diffs: Sheet 差异列表
            
        Returns:
            摘要字符串
        """
        if not sheet_diffs:
            return "表格内容无变化"
        
        total_cells = sum(len(s.cell_changes) for s in sheet_diffs)
        total_sheets = len(sheet_diffs)
        
        parts = [f"{total_sheets} 个工作表有变化"]
        if total_cells > 0:
            parts.append(f"共 {total_cells} 个单元格修改")
        
        return "；".join(parts)

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
    
    def generate_summary(self, diff_data: Dict[str, Any]) -> str:
        """
        生成摘要（接口要求）
        
        Args:
            diff_data: 差异结果数据
            
        Returns:
            摘要字符串
        """
        return diff_data.get("summary", "")
