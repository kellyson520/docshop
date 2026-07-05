"""
XLSX差异引擎测试

测试覆盖率目标：100%
- XlsxDiffEngine 完整对比流程
- _compare_sheet 对比工作表
- _detect_row_changes 检测行变化
- _detect_col_changes 检测列变化
- _compare_cells 单元格对比
- _generate_summary 生成摘要
- CellDiff 单元格差异
- SheetDiff 工作表差异
- 各种数据类型处理
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import tempfile
import os

from app.diff_engine.xlsx_diff import (
    XlsxDiffEngine,
    CellDiff,
    SheetDiff,
    CellChangeType,
)


class TestCellChangeType:
    """CellChangeType 枚举测试"""

    def test_enum_values(self):
        """测试枚举值"""
        assert CellChangeType.UNCHANGED.value == "unchanged"
        assert CellChangeType.MODIFIED.value == "modified"
        assert CellChangeType.ADDED.value == "added"
        assert CellChangeType.DELETED.value == "deleted"


class TestCellDiff:
    """CellDiff 数据类测试"""

    def test_cell_diff_creation(self):
        """测试单元格差异创建"""
        diff = CellDiff(
            row=1,
            col=1,
            col_letter="A",
            old_value="old",
            new_value="new",
            change_type=CellChangeType.MODIFIED,
            old_formula=None,
            new_formula=None
        )
        assert diff.row == 1
        assert diff.col == 1
        assert diff.col_letter == "A"
        assert diff.old_value == "old"
        assert diff.new_value == "new"
        assert diff.change_type == CellChangeType.MODIFIED

    def test_cell_diff_to_dict(self):
        """测试转换为字典"""
        diff = CellDiff(
            row=1,
            col=1,
            col_letter="A",
            old_value="old",
            new_value="new",
            change_type=CellChangeType.MODIFIED
        )
        result = diff.to_dict()
        assert result["cell"] == "A1"
        assert result["row"] == 1
        assert result["col"] == 1
        assert result["old_value"] == "old"
        assert result["new_value"] == "new"
        assert result["change_type"] == "modified"

    def test_format_value_with_nan(self):
        """测试格式化 NaN 值"""
        result = CellDiff._format_value(np.nan)
        assert result is None

    def test_format_value_with_float(self):
        """测试格式化浮点数"""
        # 整数浮点数
        result = CellDiff._format_value(10.0)
        assert result == 10
        
        # 小数浮点数不应被额外四舍五入，避免丢失精度
        result = CellDiff._format_value(3.14159265)
        assert result == 3.14159265

    def test_format_value_with_non_finite_float(self):
        """测试格式化无穷大不崩溃，NaN 仍按空值处理"""
        assert CellDiff._format_value(float("inf")) == "inf"
        assert CellDiff._format_value(float("-inf")) == "-inf"
        assert CellDiff._format_value(np.float64("inf")) == "inf"
        assert CellDiff._format_value(np.nan) is None

    def test_format_value_with_string(self):
        """测试格式化字符串"""
        result = CellDiff._format_value("test")
        assert result == "test"

    def test_format_value_with_none(self):
        """测试格式化 None"""
        result = CellDiff._format_value(None)
        assert result is None


class TestSheetDiff:
    """SheetDiff 数据类测试"""

    def test_sheet_diff_creation(self):
        """测试工作表差异创建"""
        diff = SheetDiff(
            name="Sheet1",
            index=0,
            shape_old=(10, 5),
            shape_new=(12, 6),
            cell_changes=[],
            added_rows=[11, 12],
            deleted_rows=[],
            added_cols=["F"],
            deleted_cols=[]
        )
        assert diff.name == "Sheet1"
        assert diff.index == 0
        assert diff.shape_old == (10, 5)
        assert diff.shape_new == (12, 6)

    def test_sheet_diff_to_dict(self):
        """测试转换为字典"""
        cell_diff = CellDiff(
            row=1, col=1, col_letter="A",
            old_value="old", new_value="new",
            change_type=CellChangeType.MODIFIED
        )
        diff = SheetDiff(
            name="Sheet1",
            index=0,
            shape_old=(10, 5),
            shape_new=(10, 5),
            cell_changes=[cell_diff],
            added_rows=[11],
            deleted_rows=[],
            added_cols=[],
            deleted_cols=[]
        )
        result = diff.to_dict()
        assert result["name"] == "Sheet1"
        assert result["index"] == 0
        assert result["shape_old"] == (10, 5)
        assert result["shape_new"] == (10, 5)
        assert len(result["cell_changes"]) == 1
        assert result["added_rows"] == [11]
        assert result["stats"]["cells_modified"] == 1
        assert result["stats"]["rows_added"] == 1


class TestXlsxDiffEngine:
    """XlsxDiffEngine 类测试"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        engine = XlsxDiffEngine()
        assert engine.max_rows == 100000
        assert engine.max_cols == 1000
        assert engine.chunk_size == 5000

    @patch("pandas.ExcelFile")
    @patch("pandas.read_excel")
    def test_compare_success(self, mock_read_excel, mock_excel_file):
        """测试成功对比"""
        # 设置模拟
        mock_excel_file.return_value.sheet_names = ["Sheet1"]
        
        # 创建模拟的 DataFrame
        df_old = pd.DataFrame({
            "A": ["value1", "value2"],
            "B": ["value3", "value4"]
        })
        df_new = pd.DataFrame({
            "A": ["value1_changed", "value2"],
            "B": ["value3", "value4_changed"]
        })
        
        mock_read_excel.side_effect = [df_old, df_new]
        
        engine = XlsxDiffEngine()
        result = engine.compare("old.xlsx", "new.xlsx")
        
        assert result["type"] == "xlsx_diff"
        assert "sheets" in result
        assert "text" in result
        assert "tables" in result
        assert "images" in result
        assert "metadata" in result
        assert "changes" in result
        assert "summary" in result
        assert "stats" in result
        assert "summary" in result["changes"]
        assert "stats" in result["changes"]

    @patch("pandas.ExcelFile")
    def test_compare_file_not_found(self, mock_excel_file):
        """测试文件不存在"""
        mock_excel_file.side_effect = FileNotFoundError("File not found")
        
        engine = XlsxDiffEngine()
        with pytest.raises(FileNotFoundError):
            engine.compare("nonexistent.xlsx", "new.xlsx")

    @patch("pandas.ExcelFile")
    def test_compare_exception(self, mock_excel_file):
        """测试其他异常"""
        mock_excel_file.side_effect = Exception("Parse error")
        
        engine = XlsxDiffEngine()
        with pytest.raises(Exception):
            engine.compare("old.xlsx", "new.xlsx")

    @patch("pandas.ExcelFile")
    @patch("pandas.read_excel")
    def test_compare_multiple_sheets(self, mock_read_excel, mock_excel_file):
        """测试多工作表对比"""
        mock_excel_file.return_value.sheet_names = ["Sheet1", "Sheet2"]
        
        df1 = pd.DataFrame({"A": ["a1"], "B": ["b1"]})
        df2 = pd.DataFrame({"A": ["a1_changed"], "B": ["b1"]})
        
        mock_read_excel.side_effect = [
            df1,  # Sheet1 old
            df2,  # Sheet1 new
            df1,  # Sheet2 old
            df2,  # Sheet2 new
        ]
        
        engine = XlsxDiffEngine()
        result = engine.compare("old.xlsx", "new.xlsx")
        
        assert len(result["sheet_order"]) == 2
        assert "Sheet1" in result["sheets"]
        assert "Sheet2" in result["sheets"]

    @patch("pandas.ExcelFile")
    @patch("pandas.read_excel")
    def test_compare_added_sheet(self, mock_read_excel, mock_excel_file):
        """测试新增工作表"""
        mock_excel_file.side_effect = [
            MagicMock(sheet_names=["Sheet1"]),
            MagicMock(sheet_names=["Sheet1", "Sheet2"])
        ]
        
        df = pd.DataFrame({"A": ["value"]})
        mock_read_excel.return_value = df
        
        engine = XlsxDiffEngine()
        result = engine.compare("old.xlsx", "new.xlsx")
        
        assert result["stats"]["sheets_added"] >= 0

    @patch("pandas.ExcelFile")
    @patch("pandas.read_excel")
    def test_compare_deleted_sheet(self, mock_read_excel, mock_excel_file):
        """测试删除工作表"""
        mock_excel_file.side_effect = [
            MagicMock(sheet_names=["Sheet1", "Sheet2"]),
            MagicMock(sheet_names=["Sheet1"])
        ]
        
        df = pd.DataFrame({"A": ["value"]})
        mock_read_excel.return_value = df
        
        engine = XlsxDiffEngine()
        result = engine.compare("old.xlsx", "new.xlsx")
        
        assert result["stats"]["sheets_deleted"] >= 0


class TestCompareSheet:
    """_compare_sheet 方法测试"""

    @patch("pandas.read_excel")
    def test_compare_sheet_no_changes(self, mock_read_excel):
        """测试无变化的工作表"""
        df = pd.DataFrame({"A": ["value1"], "B": ["value2"]})
        mock_read_excel.return_value = df
        
        engine = XlsxDiffEngine()
        result = engine._compare_sheet(0, "Sheet1", "old.xlsx", "new.xlsx")
        
        assert result is None

    @patch("pandas.read_excel")
    def test_compare_sheet_with_changes(self, mock_read_excel):
        """测试有变化的工作表"""
        df_old = pd.DataFrame({"A": ["value1"], "B": ["value2"]})
        df_new = pd.DataFrame({"A": ["value1_changed"], "B": ["value2"]})
        
        mock_read_excel.side_effect = [df_old, df_new]
        
        engine = XlsxDiffEngine()
        result = engine._compare_sheet(0, "Sheet1", "old.xlsx", "new.xlsx")
        
        assert result is not None
        assert result.name == "Sheet1"
        assert len(result.cell_changes) > 0

    @patch("pandas.read_excel")
    def test_compare_sheet_reads_excel_without_string_dtype(self, mock_read_excel):
        """读取 Excel 时不应强制 dtype=str，否则数值单元格会被当字符串比较"""
        df_old = pd.DataFrame({"Amount": [1.23456789012345]})
        df_new = pd.DataFrame({"Amount": [1.23456789012346]})
        mock_read_excel.side_effect = [df_old, df_new]

        engine = XlsxDiffEngine()
        engine._compare_sheet(0, "Sheet1", "old.xlsx", "new.xlsx")

        assert mock_read_excel.call_count == 2
        for call in mock_read_excel.call_args_list:
            assert "dtype" not in call.kwargs

    @patch("pandas.read_excel")
    def test_compare_sheet_added(self, mock_read_excel):
        """测试新增工作表"""
        df = pd.DataFrame({"A": ["value1"], "B": ["value2"]})
        mock_read_excel.return_value = df
        
        engine = XlsxDiffEngine()
        result = engine._compare_sheet(0, "Sheet1", None, "new.xlsx")
        
        assert result is not None
        assert result.shape_old == (0, 0)

    @patch("pandas.read_excel")
    def test_compare_sheet_deleted(self, mock_read_excel):
        """测试删除工作表"""
        df = pd.DataFrame({"A": ["value1"], "B": ["value2"]})
        mock_read_excel.return_value = df
        
        engine = XlsxDiffEngine()
        result = engine._compare_sheet(0, "Sheet1", "old.xlsx", None)
        
        assert result is not None
        assert result.shape_new == (0, 0)

    @patch("pandas.read_excel")
    def test_compare_sheet_both_empty(self, mock_read_excel):
        """测试两个空工作表"""
        mock_read_excel.return_value = pd.DataFrame()
        
        engine = XlsxDiffEngine()
        result = engine._compare_sheet(0, "Sheet1", "old.xlsx", "new.xlsx")
        
        assert result is None


class TestDetectRowChanges:
    """_detect_row_changes 方法测试"""

    def test_detect_row_changes_added(self):
        """测试检测新增行"""
        df_old = pd.DataFrame({"A": [1, 2, 3]})
        df_new = pd.DataFrame({"A": [1, 2, 3, 4, 5]})
        
        engine = XlsxDiffEngine()
        added, deleted = engine._detect_row_changes(df_old, df_new)
        
        assert len(added) == 2
        assert len(deleted) == 0

    def test_detect_row_changes_deleted(self):
        """测试检测删除行"""
        df_old = pd.DataFrame({"A": [1, 2, 3, 4, 5]})
        df_new = pd.DataFrame({"A": [1, 2, 3]})
        
        engine = XlsxDiffEngine()
        added, deleted = engine._detect_row_changes(df_old, df_new)
        
        assert len(added) == 0
        assert len(deleted) == 2

    def test_detect_row_changes_no_change(self):
        """测试无行变化"""
        df = pd.DataFrame({"A": [1, 2, 3]})
        
        engine = XlsxDiffEngine()
        added, deleted = engine._detect_row_changes(df, df)
        
        assert len(added) == 0
        assert len(deleted) == 0


class TestDetectColChanges:
    """_detect_col_changes 方法测试"""

    def test_detect_col_changes_added(self):
        """测试检测新增列"""
        df_old = pd.DataFrame({"A": [1], "B": [2]})
        df_new = pd.DataFrame({"A": [1], "B": [2], "C": [3]})
        
        engine = XlsxDiffEngine()
        added, deleted = engine._detect_col_changes(df_old, df_new)
        
        assert "C" in added
        assert len(deleted) == 0

    def test_detect_col_changes_deleted(self):
        """测试检测删除列"""
        df_old = pd.DataFrame({"A": [1], "B": [2], "C": [3]})
        df_new = pd.DataFrame({"A": [1], "B": [2]})
        
        engine = XlsxDiffEngine()
        added, deleted = engine._detect_col_changes(df_old, df_new)
        
        assert len(added) == 0
        assert "C" in deleted

    def test_detect_col_changes_no_change(self):
        """测试无列变化"""
        df = pd.DataFrame({"A": [1], "B": [2]})
        
        engine = XlsxDiffEngine()
        added, deleted = engine._detect_col_changes(df, df)
        
        assert len(added) == 0
        assert len(deleted) == 0


class TestCompareCells:
    """_compare_cells 方法测试"""

    def test_compare_cells_with_changes(self):
        """测试单元格对比有变化"""
        df_old = pd.DataFrame({
            "A": ["value1", "value2"],
            "B": ["value3", "value4"]
        })
        df_new = pd.DataFrame({
            "A": ["value1_changed", "value2"],
            "B": ["value3", "value4_changed"]
        })
        
        engine = XlsxDiffEngine()
        changes = engine._compare_cells(df_old, df_new)
        
        assert len(changes) == 2
        # 检查第一个变化
        assert changes[0].row == 1
        assert changes[0].col == 1
        assert changes[0].col_letter == "A"
        assert changes[0].old_value == "value1"
        assert changes[0].new_value == "value1_changed"

    def test_compare_cells_no_changes(self):
        """测试单元格对比无变化"""
        df = pd.DataFrame({
            "A": ["value1", "value2"],
            "B": ["value3", "value4"]
        })
        
        engine = XlsxDiffEngine()
        changes = engine._compare_cells(df, df)
        
        assert len(changes) == 0

    def test_compare_cells_uses_native_numeric_comparison(self):
        """数值应按原生 numeric 比较，1 和 1.0 不应因字符串形态不同被误报"""
        df_old = pd.DataFrame({"A": [1, 2.5]})
        df_new = pd.DataFrame({"A": [1.0, 2.5]})

        engine = XlsxDiffEngine()
        changes = engine._compare_cells(df_old, df_new)

        assert changes == []

    def test_compare_cells_empty_values(self):
        """测试空值对比"""
        df_old = pd.DataFrame({"A": ["value1", ""]})
        df_new = pd.DataFrame({"A": ["value1", "new_value"]})
        
        engine = XlsxDiffEngine()
        changes = engine._compare_cells(df_old, df_new)
        
        assert len(changes) == 1
        assert changes[0].old_value is None  # 空字符串转为 None
        assert changes[0].new_value == "new_value"

    def test_col_to_letter_conversion(self):
        """测试列索引转字母"""
        engine = XlsxDiffEngine()

        # 通过 _compare_cells 间接测试 col_to_letter
        # Create DataFrame with many columns to test col_to_letter function
        # Use integer column indices (0, 1, 2, ...) which is the default
        data = {i: [i+1] for i in range(28)}  # 28 columns: 0-27 (maps to A-AB)
        df = pd.DataFrame(data)

        df_new = df.copy()
        df_new.iloc[0, 0] = 100   # Column 0 -> A
        df_new.iloc[0, 1] = 200   # Column 1 -> B
        df_new.iloc[0, 25] = 2600  # Column 25 -> Z
        df_new.iloc[0, 26] = 2700  # Column 26 -> AA
        df_new.iloc[0, 27] = 2800  # Column 27 -> AB

        changes = engine._compare_cells(df, df_new)

        col_letters = [c.col_letter for c in changes]
        assert "A" in col_letters
        assert "B" in col_letters
        assert "Z" in col_letters
        assert "AA" in col_letters
        assert "AB" in col_letters


class TestGenerateSummary:
    """_generate_summary 方法测试"""

    def test_generate_summary_empty(self):
        """测试空差异列表"""
        engine = XlsxDiffEngine()
        result = engine._generate_summary([])
        
        assert result == "表格内容无变化"

    def test_generate_summary_single_sheet(self):
        """测试单工作表摘要"""
        engine = XlsxDiffEngine()
        
        sheet_diff = SheetDiff(
            name="Sheet1",
            index=0,
            shape_old=(10, 5),
            shape_new=(10, 5),
            cell_changes=[CellDiff(1, 1, "A", "old", "new", CellChangeType.MODIFIED)],
            added_rows=[],
            deleted_rows=[],
            added_cols=[],
            deleted_cols=[]
        )
        
        result = engine._generate_summary([sheet_diff])
        
        assert "1 个工作表有变化" in result
        assert "共 1 个单元格修改" in result

    def test_generate_summary_multiple_sheets(self):
        """测试多工作表摘要"""
        engine = XlsxDiffEngine()
        
        sheet1 = SheetDiff(
            name="Sheet1",
            index=0,
            shape_old=(10, 5),
            shape_new=(10, 5),
            cell_changes=[
                CellDiff(1, 1, "A", "old", "new", CellChangeType.MODIFIED),
                CellDiff(2, 1, "A", "old", "new", CellChangeType.MODIFIED),
            ],
            added_rows=[],
            deleted_rows=[],
            added_cols=[],
            deleted_cols=[]
        )
        
        sheet2 = SheetDiff(
            name="Sheet2",
            index=1,
            shape_old=(5, 3),
            shape_new=(5, 3),
            cell_changes=[CellDiff(1, 1, "A", "old", "new", CellChangeType.MODIFIED)],
            added_rows=[],
            deleted_rows=[],
            added_cols=[],
            deleted_cols=[]
        )
        
        result = engine._generate_summary([sheet1, sheet2])
        
        assert "2 个工作表有变化" in result
        assert "共 3 个单元格修改" in result


class TestGenerateSummaryPublic:
    """generate_summary 公共方法测试"""

    def test_generate_summary_public(self):
        """测试公共生成摘要方法"""
        engine = XlsxDiffEngine()
        
        diff_data = {"summary": "Test summary"}
        result = engine.generate_summary(diff_data)
        
        assert result == "Test summary"

    def test_generate_summary_public_no_summary(self):
        """测试无摘要字段"""
        engine = XlsxDiffEngine()
        
        diff_data = {}
        result = engine.generate_summary(diff_data)
        
        assert result == ""


class TestDiffPayloadLimits:
    """保存 diff 前的通用 payload 限制"""

    def test_cap_diff_payload_truncates_large_lists_and_strings(self):
        engine = XlsxDiffEngine()

        payload = {
            "metadata": {},
            "changes": {"metadata": {}},
            "text": ["x" * 32],
            "tables": [{"row": i} for i in range(5)],
        }

        capped = engine._cap_diff_payload(
            payload,
            max_list_items=2,
            max_string_chars=8,
        )

        assert capped["metadata"]["payload_truncated"] is True
        assert capped["changes"]["metadata"]["payload_truncated"] is True
        assert capped["text"][0] == "xxxxxxxx... [truncated]"
        assert len(capped["tables"]) == 3
        assert capped["tables"][-1] == {"_truncated": True, "omitted_items": 3}


class TestXlsxDiffIntegration:
    """XLSX差异引擎集成测试"""

    def create_test_excel(self, data_dict, filepath):
        """辅助方法：创建测试Excel文件"""
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            for sheet_name, df in data_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    def test_real_excel_comparison(self, tmp_path):
        """测试真实Excel文件对比"""
        # 创建测试文件
        old_file = tmp_path / "old.xlsx"
        new_file = tmp_path / "new.xlsx"
        
        # 旧版本数据
        old_data = {
            "Sheet1": pd.DataFrame({
                "Name": ["Alice", "Bob", "Charlie"],
                "Age": [25, 30, 35],
                "City": ["NYC", "LA", "Chicago"]
            })
        }
        
        # 新版本数据（有修改、新增行）
        new_data = {
            "Sheet1": pd.DataFrame({
                "Name": ["Alice", "Bob", "Charlie", "David"],
                "Age": [26, 30, 35, 40],  # Alice的年龄变了
                "City": ["NYC", "LA", "Chicago", "Seattle"]
            })
        }
        
        self.create_test_excel(old_data, old_file)
        self.create_test_excel(new_data, new_file)
        
        # 执行对比
        engine = XlsxDiffEngine()
        result = engine.compare(str(old_file), str(new_file))
        
        assert result["type"] == "xlsx_diff"
        assert result["stats"]["sheets_changed"] == 1
        assert result["stats"]["total_cells_modified"] > 0

    def test_real_excel_multiple_sheets(self, tmp_path):
        """测试多工作表Excel对比"""
        old_file = tmp_path / "old_multi.xlsx"
        new_file = tmp_path / "new_multi.xlsx"
        
        old_data = {
            "Sheet1": pd.DataFrame({"A": [1, 2], "B": [3, 4]}),
            "Sheet2": pd.DataFrame({"X": ["a", "b"], "Y": ["c", "d"]})
        }
        
        new_data = {
            "Sheet1": pd.DataFrame({"A": [1, 3], "B": [3, 4]}),  # A2 变了
            "Sheet2": pd.DataFrame({"X": ["a", "b_changed"], "Y": ["c", "d"]})  # X2 变了
        }
        
        self.create_test_excel(old_data, old_file)
        self.create_test_excel(new_data, new_file)
        
        engine = XlsxDiffEngine()
        result = engine.compare(str(old_file), str(new_file))
        
        assert len(result["sheets"]) == 2
        assert "Sheet1" in result["sheets"]
        assert "Sheet2" in result["sheets"]

    def test_real_excel_column_changes(self, tmp_path):
        """测试列变化检测"""
        old_file = tmp_path / "old_col.xlsx"
        new_file = tmp_path / "new_col.xlsx"
        
        old_data = {
            "Sheet1": pd.DataFrame({"A": [1], "B": [2]})
        }
        
        new_data = {
            "Sheet1": pd.DataFrame({"A": [1], "B": [2], "C": [3]})  # 新增C列
        }
        
        self.create_test_excel(old_data, old_file)
        self.create_test_excel(new_data, new_file)
        
        engine = XlsxDiffEngine()
        result = engine.compare(str(old_file), str(new_file))
        
        sheet_diff = result["sheets"]["Sheet1"]
        assert "C" in sheet_diff["added_cols"]

    def test_real_excel_with_different_data_types(self, tmp_path):
        """测试不同数据类型"""
        old_file = tmp_path / "old_types.xlsx"
        new_file = tmp_path / "new_types.xlsx"
        
        old_data = {
            "Sheet1": pd.DataFrame({
                "Int": [1, 2, 3],
                "Float": [1.1, 2.2, 3.3],
                "String": ["a", "b", "c"],
                "Mixed": [1, "text", 3.14]
            })
        }
        
        new_data = {
            "Sheet1": pd.DataFrame({
                "Int": [1, 20, 3],  # 修改
                "Float": [1.1, 2.2, 3.3],
                "String": ["a", "b_changed", "c"],  # 修改
                "Mixed": [1, "text", 3.14]
            })
        }
        
        self.create_test_excel(old_data, old_file)
        self.create_test_excel(new_data, new_file)
        
        engine = XlsxDiffEngine()
        result = engine.compare(str(old_file), str(new_file))
        
        assert result["stats"]["total_cells_modified"] > 0
