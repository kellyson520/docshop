"""
卡片服务测试模块

测试卡片服务的所有功能，包括：
- 获取卡片列表（支持各种筛选条件）
- 获取卡片详情
- 更新卡片封面
- 更新卡片信息
- 多版本对比
- 删除卡片封面
- 图片文件验证

作者: Test Team
创建日期: 2026-05-28
"""

import os
import sys
import unittest
from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.services.card_service import (
    get_cards_list,
    get_card_detail,
    update_card_cover,
    update_card_info,
    compare_versions,
    delete_card_cover,
    validate_image_file,
    ALLOWED_IMAGE_TYPES,
    MAX_IMAGE_SIZE,
)
from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.diff_record import DiffRecord


class MockUploadFile:
    """模拟上传文件对象"""
    def __init__(self, filename, content, content_type="image/jpeg"):
        self.filename = filename
        self.content = content
        self.content_type = content_type
        self.file = BytesIO(content)
    
    def read(self):
        return self.content


class TestGetCardsList(unittest.TestCase):
    """测试获取卡片列表功能"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query
        
    def test_get_cards_list_success(self):
        """测试正常获取卡片列表"""
        # 准备模拟数据
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.display_name = "测试文档"
        mock_file.cover_image = "/covers/test.jpg"
        mock_file.updated_at = "2026-05-28T10:00:00Z"
        mock_file.description = "测试描述"
        mock_file.file_type = "docx"
        
        # 配置mock链
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.count.return_value = 1
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.offset.return_value = self.mock_query
        self.mock_query.limit.return_value = self.mock_query
        self.mock_query.all.return_value = [mock_file]
        
        # 执行测试
        cards, total = get_cards_list(self.mock_db, page=1, page_size=20)
        
        # 验证结果
        self.assertEqual(total, 1)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["id"], "test-file-id")
        self.assertEqual(cards[0]["display_name"], "测试文档")
        
    def test_get_cards_list_with_project_id(self):
        """测试按项目ID筛选"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.display_name = None  # 测试使用filename的情况
        mock_file.filename = "test.docx"
        mock_file.cover_image = None
        mock_file.updated_at = None  # 测试使用created_at的情况
        mock_file.created_at = "2026-05-28T09:00:00Z"
        mock_file.description = None
        mock_file.file_type = "docx"
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.count.return_value = 1
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.offset.return_value = self.mock_query
        self.mock_query.limit.return_value = self.mock_query
        self.mock_query.all.return_value = [mock_file]
        
        cards, total = get_cards_list(
            self.mock_db, 
            project_id="test-project",
            page=1, 
            page_size=20
        )
        
        self.assertEqual(total, 1)
        self.assertEqual(cards[0]["display_name"], "test.docx")  # 使用filename
        self.assertEqual(cards[0]["updated_at"], "2026-05-28T09:00:00Z")  # 使用created_at
        
    def test_get_cards_list_with_keyword(self):
        """测试关键词搜索"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.display_name = "搜索关键词文档"
        mock_file.filename = "search.docx"
        mock_file.cover_image = None
        mock_file.updated_at = "2026-05-28T10:00:00Z"
        mock_file.description = "包含关键词的描述"
        mock_file.file_type = "docx"
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.count.return_value = 1
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.offset.return_value = self.mock_query
        self.mock_query.limit.return_value = self.mock_query
        self.mock_query.all.return_value = [mock_file]
        
        cards, total = get_cards_list(
            self.mock_db,
            keyword="关键词",
            page=1,
            page_size=20
        )
        
        self.assertEqual(total, 1)
        
    def test_get_cards_list_invalid_page(self):
        """测试无效页码"""
        with self.assertRaises(HTTPException) as context:
            get_cards_list(self.mock_db, page=0, page_size=20)
        
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("页码必须大于0", context.exception.detail)
        
    def test_get_cards_list_invalid_page_size(self):
        """测试无效每页数量"""
        # 测试page_size为0
        with self.assertRaises(HTTPException) as context:
            get_cards_list(self.mock_db, page=1, page_size=0)
        
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        
        # 测试page_size超过100
        with self.assertRaises(HTTPException) as context:
            get_cards_list(self.mock_db, page=1, page_size=101)
        
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_get_cards_list_empty_result(self):
        """测试空结果"""
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.count.return_value = 0
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.offset.return_value = self.mock_query
        self.mock_query.limit.return_value = self.mock_query
        self.mock_query.all.return_value = []
        
        cards, total = get_cards_list(self.mock_db, page=1, page_size=20)
        
        self.assertEqual(total, 0)
        self.assertEqual(len(cards), 0)
        
    def test_get_cards_list_database_error(self):
        """测试数据库错误处理"""
        self.mock_db.query.side_effect = Exception("数据库连接失败")
        
        with self.assertRaises(HTTPException) as context:
            get_cards_list(self.mock_db, page=1, page_size=20)
        
        self.assertEqual(context.exception.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestGetCardDetail(unittest.TestCase):
    """测试获取卡片详情功能"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query
        
    def test_get_card_detail_success(self):
        """测试正常获取卡片详情"""
        # 准备模拟文档
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.display_name = "测试文档"
        mock_file.filename = "test.docx"
        mock_file.cover_image = "/covers/test.jpg"
        mock_file.description = "测试描述"
        mock_file.file_type = "docx"
        mock_file.project_id = "test-project"
        
        # 准备模拟版本
        mock_version = Mock(spec=FileVersion)
        mock_version.id = "version-1"
        mock_version.version = 1
        mock_version.created_at = "2026-05-28T10:00:00Z"
        mock_version.changelog = "初始版本"
        mock_version.file_size = 1024
        
        # 配置mock - 第一个query返回文件，第二个query返回版本列表
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = [mock_version]
        
        detail = get_card_detail(self.mock_db, "test-file-id")
        
        self.assertEqual(detail["id"], "test-file-id")
        self.assertEqual(detail["display_name"], "测试文档")
        self.assertEqual(len(detail["versions"]), 1)
        
    def test_get_card_detail_not_found(self):
        """测试卡片不存在"""
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = None
        
        with self.assertRaises(HTTPException) as context:
            get_card_detail(self.mock_db, "non-existent-id")
        
        self.assertEqual(context.exception.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("卡片不存在", context.exception.detail)
        
    def test_get_card_detail_without_display_name(self):
        """测试没有display_name时使用filename"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.display_name = None  # 无显示名称
        mock_file.filename = "fallback.docx"
        mock_file.cover_image = None
        mock_file.description = None
        mock_file.file_type = "docx"
        mock_file.project_id = "test-project"
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = []  # 空版本列表
        
        detail = get_card_detail(self.mock_db, "test-file-id")
        
        self.assertEqual(detail["display_name"], "fallback.docx")
        
    def test_get_card_detail_database_error(self):
        """测试数据库错误"""
        self.mock_db.query.side_effect = Exception("数据库错误")
        
        with self.assertRaises(HTTPException) as context:
            get_card_detail(self.mock_db, "test-file-id")
        
        self.assertEqual(context.exception.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestValidateImageFile(unittest.TestCase):
    """测试图片文件验证功能"""
    
    def test_validate_jpeg(self):
        """测试验证JPEG图片"""
        # JPEG文件头
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        mock_file = MockUploadFile("test.jpg", jpeg_header)
        
        ext = validate_image_file(mock_file, jpeg_header)
        self.assertEqual(ext, "jpg")
        
    def test_validate_png(self):
        """测试验证PNG图片"""
        # PNG文件头
        png_header = b'\x89PNG\r\n\x1a\n'
        mock_file = MockUploadFile("test.png", png_header)
        
        ext = validate_image_file(mock_file, png_header)
        self.assertEqual(ext, "png")
        
    def test_validate_gif(self):
        """测试验证GIF图片"""
        # GIF文件头
        gif_header = b'GIF89a'
        mock_file = MockUploadFile("test.gif", gif_header)
        
        ext = validate_image_file(mock_file, gif_header)
        self.assertEqual(ext, "gif")
        
    def test_validate_webp(self):
        """测试验证WEBP图片"""
        # WEBP文件头 (RIFF....WEBP)
        webp_header = b'RIFF\x00\x00\x00\x00WEBP'
        mock_file = MockUploadFile("test.webp", webp_header)
        
        ext = validate_image_file(mock_file, webp_header)
        self.assertEqual(ext, "webp")
        
    def test_validate_image_too_large(self):
        """测试图片过大"""
        # 创建超过5MB的内容
        large_content = b'\xff\xd8\xff\xe0' + b'0' * (MAX_IMAGE_SIZE + 100)
        mock_file = MockUploadFile("test.jpg", large_content)
        
        with self.assertRaises(HTTPException) as context:
            validate_image_file(mock_file, large_content)
        
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("图片大小超过限制", context.exception.detail)
        
    def test_validate_unknown_format(self):
        """测试未知图片格式"""
        unknown_content = b'UNKNOWNFILEFORMAT'
        mock_file = MockUploadFile("test.unknown", unknown_content)
        
        with self.assertRaises(HTTPException) as context:
            validate_image_file(mock_file, unknown_content)
        
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("无法识别的图片格式", context.exception.detail)
        
    def test_validate_unsupported_format(self):
        """测试不支持的图片格式（如BMP）"""
        # BMP文件头
        bmp_header = b'BM\x00\x00\x00\x00\x00\x00\x00\x00'
        mock_file = MockUploadFile("test.bmp", bmp_header)
        
        with self.assertRaises(HTTPException) as context:
            validate_image_file(mock_file, bmp_header)
        
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("不支持的图片格式", context.exception.detail)


class TestUpdateCardCover(unittest.TestCase):
    """测试更新卡片封面功能"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query
        
    @patch('app.services.card_service.Path')
    @patch('app.services.card_service.settings')
    @patch('app.services.card_service.datetime')
    def test_update_card_cover_success(self, mock_datetime, mock_settings, mock_path):
        """测试正常更新封面"""
        # 准备模拟数据
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.cover_image = None
        mock_file.updated_at = None
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        
        # 模拟datetime
        mock_datetime.utcnow.return_value = datetime(2026, 5, 28, 10, 0, 0)
        
        # 模拟路径
        mock_settings.UPLOAD_DIR = "/uploads"
        mock_cover_dir = Mock()
        mock_cover_dir.parent = Mock()
        mock_cover_dir.parent.__truediv__ = Mock(return_value=mock_cover_dir)
        mock_cover_dir.mkdir = Mock()
        mock_cover_dir.__truediv__ = Mock(return_value=mock_cover_dir)
        mock_cover_dir.exists.return_value = False
        mock_cover_dir.relative_to.return_value = Path("covers/test-file-id/cover_20260528_100000.jpg")
        
        mock_path.return_value = mock_cover_dir
        mock_path.side_effect = lambda x: Path(x)
        
        # 准备图片数据
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        mock_upload = MockUploadFile("test.jpg", jpeg_header)
        
        # 执行测试
        with patch('builtins.open', unittest.mock.mock_open()) as mock_file_open:
            result = update_card_cover(self.mock_db, "test-file-id", mock_upload)
        
        # 验证结果
        self.assertEqual(result["card_id"], "test-file-id")
        self.assertIn("cover_image", result)
        self.mock_db.commit.assert_called_once()
        
    def test_update_card_cover_card_not_found(self):
        """测试卡片不存在"""
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = None
        
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        mock_upload = MockUploadFile("test.jpg", jpeg_header)
        
        with self.assertRaises(HTTPException) as context:
            update_card_cover(self.mock_db, "non-existent-id", mock_upload)
        
        self.assertEqual(context.exception.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_update_card_cover_invalid_image(self):
        """测试无效图片格式"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        
        # 使用无效的图片格式
        invalid_content = b'INVALIDIMAGE'
        mock_upload = MockUploadFile("test.txt", invalid_content)
        
        with self.assertRaises(HTTPException) as context:
            update_card_cover(self.mock_db, "test-file-id", mock_upload)
        
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)


class TestUpdateCardInfo(unittest.TestCase):
    """测试更新卡片信息功能"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query
        
    @patch('app.services.card_service.datetime')
    def test_update_card_info_success(self, mock_datetime):
        """测试正常更新卡片信息"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.display_name = "旧名称"
        mock_file.description = "旧描述"
        mock_file.filename = "test.docx"
        mock_file.updated_at = None
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        
        mock_datetime.utcnow.return_value = datetime(2026, 5, 28, 10, 0, 0)
        
        result = update_card_info(
            self.mock_db,
            "test-file-id",
            display_name="新名称",
            description="新描述"
        )
        
        self.assertEqual(result["display_name"], "新名称")
        self.assertEqual(result["description"], "新描述")
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_file)
        
    def test_update_card_info_only_display_name(self):
        """测试只更新显示名称"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.display_name = "旧名称"
        mock_file.description = "旧描述"
        mock_file.filename = "test.docx"
        mock_file.updated_at = None
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        
        result = update_card_info(
            self.mock_db,
            "test-file-id",
            display_name="新名称"
        )
        
        self.assertEqual(result["display_name"], "新名称")
        # description应该保持不变
        self.assertEqual(mock_file.description, "旧描述")
        
    def test_update_card_info_only_description(self):
        """测试只更新描述"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.display_name = "名称"
        mock_file.description = "旧描述"
        mock_file.filename = "test.docx"
        mock_file.updated_at = None
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        
        result = update_card_info(
            self.mock_db,
            "test-file-id",
            description="新描述"
        )
        
        self.assertEqual(result["description"], "新描述")
        # display_name应该保持不变
        self.assertEqual(mock_file.display_name, "名称")
        
    def test_update_card_info_display_name_too_long(self):
        """测试显示名称过长"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        
        with self.assertRaises(HTTPException) as context:
            update_card_info(
                self.mock_db,
                "test-file-id",
                display_name="x" * 256  # 超过255字符
            )
        
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("显示名称长度不能超过255个字符", context.exception.detail)
        
    def test_update_card_info_not_found(self):
        """测试卡片不存在"""
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = None
        
        with self.assertRaises(HTTPException) as context:
            update_card_info(self.mock_db, "non-existent-id", display_name="新名称")
        
        self.assertEqual(context.exception.status_code, status.HTTP_404_NOT_FOUND)


class TestCompareVersions(unittest.TestCase):
    """测试多版本对比功能"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query
        
    @patch('app.services.card_service.compute_diff')
    def test_compare_versions_success(self, mock_compute_diff):
        """测试正常版本对比"""
        # 准备模拟文档
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "card-id"
        
        # 准备模拟版本
        mock_version1 = Mock(spec=FileVersion)
        mock_version1.id = "version-1"
        mock_version1.version = 1
        mock_version1.created_at = "2026-05-28T09:00:00Z"
        mock_version1.changelog = "版本1"
        mock_version1.file_size = 1024
        
        mock_version2 = Mock(spec=FileVersion)
        mock_version2.id = "version-2"
        mock_version2.version = 2
        mock_version2.created_at = "2026-05-28T10:00:00Z"
        mock_version2.changelog = "版本2"
        mock_version2.file_size = 2048
        
        # 准备模拟差异记录
        mock_diff = Mock(spec=DiffRecord)
        mock_diff.summary = "测试差异摘要"
        
        # 配置mock
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        self.mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_version1, mock_version2
        ]
        self.mock_query.filter.return_value.filter.return_value.first.return_value = mock_diff
        
        mock_compute_diff.return_value = mock_diff
        
        result = compare_versions(self.mock_db, "card-id", ["version-1", "version-2"])
        
        self.assertEqual(result["card_id"], "card-id")
        self.assertEqual(len(result["compared_versions"]), 2)
        self.assertEqual(len(result["compare_results"]), 1)  # C(2,2) = 1对
        
    def test_compare_versions_less_than_two(self):
        """测试版本数少于2个"""
        with self.assertRaises(HTTPException) as context:
            compare_versions(self.mock_db, "card-id", ["version-1"])
        
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("至少需要选择2个版本进行对比", context.exception.detail)
        
    def test_compare_versions_more_than_five(self):
        """测试版本数超过5个"""
        with self.assertRaises(HTTPException) as context:
            compare_versions(
                self.mock_db, 
                "card-id", 
                ["v1", "v2", "v3", "v4", "v5", "v6"]
            )
        
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("最多支持同时对比5个版本", context.exception.detail)
        
    def test_compare_versions_card_not_found(self):
        """测试卡片不存在"""
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = None
        
        with self.assertRaises(HTTPException) as context:
            compare_versions(self.mock_db, "non-existent-id", ["v1", "v2"])
        
        self.assertEqual(context.exception.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_compare_versions_version_not_found(self):
        """测试版本不存在"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "card-id"
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        self.mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        with self.assertRaises(HTTPException) as context:
            compare_versions(self.mock_db, "card-id", ["v1", "v2"])
        
        self.assertEqual(context.exception.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("以下版本不存在", context.exception.detail)


class TestDeleteCardCover(unittest.TestCase):
    """测试删除卡片封面功能"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query
        
    @patch('app.services.card_service.Path')
    @patch('app.services.card_service.settings')
    def test_delete_card_cover_success(self, mock_settings, mock_path):
        """测试正常删除封面"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.cover_image = "covers/test-file-id/cover.jpg"
        mock_file.updated_at = None
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        
        mock_settings.UPLOAD_DIR = "/uploads"
        
        # 模拟路径存在
        mock_cover_path = Mock()
        mock_cover_path.exists.return_value = True
        mock_cover_path.unlink = Mock()
        
        mock_path.return_value = mock_cover_path
        mock_path.side_effect = lambda x: Path(x)
        
        result = delete_card_cover(self.mock_db, "test-file-id")
        
        self.assertTrue(result)
        self.assertIsNone(mock_file.cover_image)
        self.mock_db.commit.assert_called_once()
        
    def test_delete_card_cover_no_cover(self):
        """测试没有封面时删除"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.cover_image = None
        
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        
        result = delete_card_cover(self.mock_db, "test-file-id")
        
        self.assertTrue(result)
        # 不应该调用commit，因为没有需要更新的内容
        
    def test_delete_card_cover_not_found(self):
        """测试卡片不存在"""
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = None

        with self.assertRaises(HTTPException) as context:
            delete_card_cover(self.mock_db, "non-existent-id")

        self.assertEqual(context.exception.status_code, status.HTTP_404_NOT_FOUND)


class TestUpdateCardInfoExtended(unittest.TestCase):
    """测试更新卡片信息扩展 - 覆盖未覆盖行"""

    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query

    def test_update_card_info_not_found(self):
        """测试卡片不存在（行306-312: 404 分支）"""
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = None

        with self.assertRaises(HTTPException) as context:
            update_card_info(self.mock_db, "non-existent-id", display_name="新名称")

        self.assertEqual(context.exception.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("卡片不存在", context.exception.detail)

    def test_update_card_info_general_exception(self):
        """测试更新卡片信息时的一般异常（行405-407: 通用异常处理）"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.display_name = "旧名称"
        mock_file.description = "旧描述"
        mock_file.filename = "test.docx"
        mock_file.updated_at = None

        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        # 模拟 commit 抛出异常
        self.mock_db.commit.side_effect = Exception("数据库连接断开")

        with self.assertRaises(HTTPException) as context:
            update_card_info(self.mock_db, "test-file-id", display_name="新名称")

        self.assertEqual(context.exception.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("更新卡片信息失败", context.exception.detail)


class TestUpdateCardCoverExtended(unittest.TestCase):
    """测试更新卡片封面扩展 - 覆盖未覆盖行"""

    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query

    def test_update_card_cover_not_found(self):
        """测试卡片不存在（行331-333: 404 分支）"""
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = None

        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        mock_upload = MockUploadFile("test.jpg", jpeg_header)

        with self.assertRaises(HTTPException) as context:
            update_card_cover(self.mock_db, "non-existent-id", mock_upload)

        self.assertEqual(context.exception.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("卡片不存在", context.exception.detail)

    def test_update_card_cover_general_exception(self):
        """测试更新封面时的一般异常"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.cover_image = None

        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file
        # 模拟读取文件内容时出错
        mock_file_read = Mock()
        mock_file_read.read.side_effect = Exception("读取文件失败")
        mock_upload = MockUploadFile("test.jpg", b'\xff\xd8\xff\xe0\x00\x10JFIF')
        mock_upload.file = mock_file_read

        with self.assertRaises(HTTPException) as context:
            update_card_cover(self.mock_db, "test-file-id", mock_upload)

        self.assertEqual(context.exception.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestGetCardDetailExtended(unittest.TestCase):
    """测试获取卡片详情扩展 - 覆盖未覆盖行"""

    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query

    def test_get_card_detail_not_found(self):
        """测试卡片不存在（行405-407: 404 分支）"""
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = None

        with self.assertRaises(HTTPException) as context:
            get_card_detail(self.mock_db, "non-existent-id")

        self.assertEqual(context.exception.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("卡片不存在", context.exception.detail)


class TestCompareVersionsExtended(unittest.TestCase):
    """测试版本对比扩展 - 覆盖未覆盖行"""

    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query

    @patch('app.services.card_service.compute_diff')
    def test_compare_versions_diff_error(self, mock_compute_diff):
        """测试 diff 计算错误（行505-512: compute_diff 异常处理）"""
        # 准备模拟文档
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "card-id"

        # 准备模拟版本
        mock_version1 = Mock(spec=FileVersion)
        mock_version1.id = "version-1"
        mock_version1.version = 1
        mock_version1.created_at = "2026-05-28T09:00:00Z"
        mock_version1.changelog = "版本1"
        mock_version1.file_size = 1024

        mock_version2 = Mock(spec=FileVersion)
        mock_version2.id = "version-2"
        mock_version2.version = 2
        mock_version2.created_at = "2026-05-28T10:00:00Z"
        mock_version2.changelog = "版本2"
        mock_version2.file_size = 2048

        # 配置mock - 为三次不同的 db.query() 调用返回不同的 mock
        mock_query_file = Mock()  # 第一次查询：DocumentFile
        mock_query_version = Mock()  # 第二次查询：FileVersion
        mock_query_diff = Mock()  # 第三次查询：DiffRecord

        # 第一次查询：查找卡片
        mock_query_file.filter.return_value = mock_query_file
        mock_query_file.first.return_value = mock_file

        # 第二次查询：查找版本
        mock_query_version.filter.return_value = mock_query_version
        mock_query_version.filter.return_value.order_by.return_value = mock_query_version
        mock_query_version.order_by.return_value.all.return_value = [
            mock_version1, mock_version2
        ]

        # 第三次查询：查找差异记录（返回 None，需要计算）
        mock_query_diff.filter.return_value = mock_query_diff
        mock_query_diff.first.return_value = None

        self.mock_db.query.side_effect = [mock_query_file, mock_query_version, mock_query_diff]

        # 模拟 compute_diff 抛出异常
        mock_compute_diff.side_effect = Exception("Diff calculation failed")

        # 执行测试 - 不应该抛出异常，而是设置 diff_record = None
        result = compare_versions(self.mock_db, "card-id", ["version-1", "version-2"])

        # 验证结果中 diff 计算失败的处理
        self.assertEqual(result["card_id"], "card-id")
        self.assertEqual(len(result["compare_results"]), 1)
        # diff_record 为 None，所以 has_diff 应该是 False
        self.assertFalse(result["compare_results"][0]["has_diff"])


class TestDeleteCardCoverExtended(unittest.TestCase):
    """测试删除卡片封面扩展 - 覆盖未覆盖行"""

    def setUp(self):
        """测试前准备"""
        self.mock_db = Mock(spec=Session)
        self.mock_query = Mock()
        self.mock_db.query.return_value = self.mock_query

    def test_delete_card_cover_not_found(self):
        """测试卡片不存在（行537-539: 404 分支）"""
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = None

        with self.assertRaises(HTTPException) as context:
            delete_card_cover(self.mock_db, "non-existent-id")

        self.assertEqual(context.exception.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("卡片不存在", context.exception.detail)

    @patch('app.services.card_service.settings')
    def test_delete_card_cover_no_cover(self, mock_settings):
        """测试没有封面时删除（行575-579: cover_image 为 None）"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.cover_image = None  # 没有封面

        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file

        mock_settings.UPLOAD_DIR = "/uploads"

        result = delete_card_cover(self.mock_db, "test-file-id")

        self.assertTrue(result)
        # 不应该调用 commit（因为没有需要更新的内容）
        self.mock_db.commit.assert_not_called()

    @patch('app.services.card_service.settings')
    def test_delete_card_cover_file_delete_fails(self, mock_settings):
        """测试删除封面文件失败（行578-579: unlink 异常处理）"""
        mock_file = Mock(spec=DocumentFile)
        mock_file.id = "test-file-id"
        mock_file.cover_image = "covers/test-file-id/cover.jpg"
        mock_file.updated_at = None

        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.first.return_value = mock_file

        mock_settings.UPLOAD_DIR = "/uploads"

        # 使用真实的 Path 对象，但模拟 unlink 抛出异常
        with patch('app.services.card_service.Path') as mock_path_cls:
            mock_upload_path = MagicMock()
            mock_upload_path.parent = mock_upload_path
            mock_upload_path.__truediv__ = MagicMock(return_value=mock_upload_path)
            mock_upload_path.exists.return_value = True
            mock_upload_path.unlink.side_effect = Exception("权限不足")
            mock_path_cls.return_value = mock_upload_path

            result = delete_card_cover(self.mock_db, "test-file-id")

        # 即使删除文件失败，函数也应该成功返回
        self.assertTrue(result)


class TestValidateImageFileExtended(unittest.TestCase):
    """测试图片文件验证扩展 - 覆盖未覆盖行"""

    def test_validate_image_file_invalid(self):
        """测试无效图片文件（行591-593: 通用异常处理）"""
        # 创建一个看起来像图片但实际上无法被 imghdr 识别的内容
        unknown_content = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        mock_file = MockUploadFile("test.dat", unknown_content)

        with self.assertRaises(HTTPException) as context:
            validate_image_file(mock_file, unknown_content)

        # 应该是 "无法识别的图片格式" 或 "不支持的图片格式"
        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)


if __name__ == "__main__":
    unittest.main()
