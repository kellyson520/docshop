"""
文件服务扩展测试模块

补充测试文件服务的未覆盖功能，包括：
- 保存上传文件的所有分支（磁盘满、路径错误等）
- 原子写入异常处理
- 安全删除（回收站模式）
- 检查磁盘空间各种状态
- 计算文件哈希大文件处理
- 临时文件上下文管理器
- 文件复制和大小获取

作者: Test Team
创建日期: 2026-05-28
"""

import os
import sys
import unittest
import tempfile
import shutil
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.file_service import (
    get_file_extension,
    calculate_file_hash,
    calculate_file_hash_from_path,
    temp_file_context,
    temp_directory_context,
    check_disk_space,
    save_upload_file,
    read_file_content,
    delete_file,
    delete_project_files,
    get_storage_path,
    file_exists,
    get_file_size,
    copy_file,
    get_storage_usage,
)
from app.exceptions import StorageError, ValidationError, ResourceNotFound


class TestGetFileExtension(unittest.TestCase):
    """测试获取文件扩展名功能"""
    
    def test_get_extension_normal(self):
        """测试正常获取扩展名"""
        self.assertEqual(get_file_extension("test.docx"), ".docx")
        self.assertEqual(get_file_extension("test.PDF"), ".pdf")
        
    def test_get_extension_multiple_dots(self):
        """测试多个点的文件名"""
        self.assertEqual(get_file_extension("archive.tar.gz"), ".gz")
        
    def test_get_extension_no_extension(self):
        """测试无扩展名的文件"""
        self.assertEqual(get_file_extension("Makefile"), "")
        
    def test_get_extension_empty_filename(self):
        """测试空文件名"""
        self.assertEqual(get_file_extension(""), "")
        
    def test_get_extension_exception(self):
        """测试异常情况"""
        # 模拟os.path.splitext抛出异常，同时patch logger避免日志记录时再次调用
        with patch('os.path.splitext') as mock_split, \
             patch('app.services.file_service.file_logger'):
            mock_split.side_effect = Exception("分割失败")
            result = get_file_extension("test.docx")
            self.assertEqual(result, "")


class TestCalculateFileHash(unittest.TestCase):
    """测试计算文件哈希功能"""
    
    def test_calculate_hash_small_content(self):
        """测试小文件内容哈希"""
        content = b"Hello, World!"
        hash_result = calculate_file_hash(content)
        
        # 验证是有效的SHA-256哈希（64字符十六进制）
        self.assertEqual(len(hash_result), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_result))
        
    def test_calculate_hash_empty_content(self):
        """测试空内容哈希"""
        content = b""
        hash_result = calculate_file_hash(content)
        
        # 空内容的SHA-256哈希
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        self.assertEqual(hash_result, expected)
        
    def test_calculate_hash_large_content(self):
        """测试大文件内容哈希"""
        content = b"x" * 1000000  # 1MB数据
        hash_result = calculate_file_hash(content)
        
        self.assertEqual(len(hash_result), 64)
        
    def test_calculate_hash_exception(self):
        """测试哈希计算异常"""
        with patch('app.services.file_service.hashlib.sha256') as mock_sha:
            mock_sha.side_effect = Exception("哈希计算失败")
            
            with self.assertRaises(StorageError) as context:
                calculate_file_hash(b"test")
            
            self.assertIn("计算文件哈希失败", str(context.exception))


class TestCalculateFileHashFromPath(unittest.TestCase):
    """测试从路径计算文件哈希功能"""
    
    def setUp(self):
        """创建临时文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"
        self.test_file.write_bytes(b"Test content for hashing")
        
    def tearDown(self):
        """清理临时文件"""
        shutil.rmtree(self.temp_dir)
        
    def test_calculate_hash_from_path_small_file(self):
        """测试小文件哈希"""
        hash_result = calculate_file_hash_from_path(self.test_file)
        
        self.assertEqual(len(hash_result), 64)
        
    def test_calculate_hash_from_path_large_file(self):
        """测试大文件分块哈希"""
        # 创建大文件（超过8192字节）
        large_file = Path(self.temp_dir) / "large.bin"
        large_file.write_bytes(b"x" * 100000)
        
        hash_result = calculate_file_hash_from_path(large_file)
        
        self.assertEqual(len(hash_result), 64)
        
    def test_calculate_hash_from_path_not_found(self):
        """测试文件不存在"""
        non_existent = Path(self.temp_dir) / "not_exist.txt"
        
        with self.assertRaises(StorageError) as context:
            calculate_file_hash_from_path(non_existent)
        
        self.assertIn("计算文件哈希失败", str(context.exception))
        
    def test_calculate_hash_from_path_permission_error(self):
        """测试权限错误"""
        with patch('builtins.open') as mock_open:
            mock_open.side_effect = PermissionError("权限不足")
            
            with self.assertRaises(StorageError):
                calculate_file_hash_from_path(self.test_file)


class TestTempFileContext(unittest.TestCase):
    """测试临时文件上下文管理器"""
    
    @patch('app.services.file_service.settings')
    def test_temp_file_created_and_cleaned(self, mock_settings):
        """测试临时文件创建和自动清理"""
        mock_settings.TEMP_DIR = tempfile.gettempdir()
        
        temp_path = None
        with temp_file_context(suffix=".txt") as path:
            temp_path = path
            # 验证文件已创建
            self.assertTrue(path.exists())
            self.assertTrue(str(path).endswith(".txt"))
            
        # 验证文件已清理
        self.assertFalse(temp_path.exists())
        
    @patch('app.services.file_service.settings')
    def test_temp_file_cleanup_on_exception(self, mock_settings):
        """测试异常时临时文件清理"""
        mock_settings.TEMP_DIR = tempfile.gettempdir()
        
        temp_path = None
        try:
            with temp_file_context(suffix=".tmp") as path:
                temp_path = path
                self.assertTrue(path.exists())
                raise ValueError("测试异常")
        except ValueError:
            pass
            
        # 验证文件已清理
        self.assertFalse(temp_path.exists())
        
    @patch('app.services.file_service.settings')
    def test_temp_file_without_suffix(self, mock_settings):
        """测试无后缀的临时文件"""
        mock_settings.TEMP_DIR = tempfile.gettempdir()
        
        with temp_file_context() as path:
            self.assertTrue(path.exists())


class TestTempDirectoryContext(unittest.TestCase):
    """测试临时目录上下文管理器"""
    
    @patch('app.services.file_service.settings')
    def test_temp_directory_created_and_cleaned(self, mock_settings):
        """测试临时目录创建和自动清理"""
        mock_settings.TEMP_DIR = tempfile.gettempdir()
        
        temp_dir = None
        with temp_directory_context() as path:
            temp_dir = path
            # 验证目录已创建
            self.assertTrue(path.exists())
            self.assertTrue(path.is_dir())
            
            # 在目录中创建文件
            test_file = path / "test.txt"
            test_file.write_text("test")
            
        # 验证目录已清理
        self.assertFalse(temp_dir.exists())
        
    @patch('app.services.file_service.settings')
    def test_temp_directory_cleanup_on_exception(self, mock_settings):
        """测试异常时临时目录清理"""
        mock_settings.TEMP_DIR = tempfile.gettempdir()
        
        temp_dir = None
        try:
            with temp_directory_context() as path:
                temp_dir = path
                self.assertTrue(path.exists())
                raise RuntimeError("测试异常")
        except RuntimeError:
            pass
            
        # 验证目录已清理
        self.assertFalse(temp_dir.exists())


class TestCheckDiskSpace(unittest.TestCase):
    """测试检查磁盘空间功能"""
    
    def test_check_disk_space_sufficient(self):
        """测试空间充足"""
        with patch('app.services.file_service._get_disk_free', return_value=2621440 * 4096):
            result = check_disk_space(1024 * 1024, Path("/tmp"))  # 需要1MB
            self.assertTrue(result)
            
    def test_check_disk_space_insufficient(self):
        """测试空间不足"""
        with patch('app.services.file_service._get_disk_free', return_value=25600 * 4096):
            with self.assertRaises(StorageError) as context:
                check_disk_space(200 * 1024 * 1024, Path("/tmp"))  # 需要200MB
            
            self.assertIn("磁盘空间不足", str(context.exception))
            
    def test_check_disk_space_stat_error(self):
        """测试磁盘空间检查错误"""
        with patch('app.services.file_service._get_disk_free', side_effect=OSError("无法访问")):
            # 错误时默认返回True
            result = check_disk_space(1024, Path("/tmp"))
            self.assertTrue(result)


class TestSaveUploadFile(unittest.TestCase):
    """测试保存上传文件功能"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    @patch('app.services.file_service.settings')
    @patch('app.services.file_service.check_disk_space')
    def test_save_upload_file_success(self, mock_check_disk, mock_settings):
        """测试正常保存文件"""
        mock_settings.UPLOAD_DIR = self.temp_dir
        mock_check_disk.return_value = True
        
        content = b"Test file content"
        path, file_hash, file_size = save_upload_file(
            project_id="proj-1",
            file_id="file-1",
            version=1,
            filename="test.txt",
            content=content
        )
        
        self.assertTrue(Path(path).exists())
        self.assertEqual(file_size, len(content))
        self.assertEqual(len(file_hash), 64)  # SHA-256哈希长度
        
    def test_save_upload_file_invalid_project_id(self):
        """测试无效项目ID"""
        with self.assertRaises(ValidationError) as context:
            save_upload_file(
                project_id="",
                file_id="file-1",
                version=1,
                filename="test.txt",
                content=b"test"
            )
        
        self.assertIn("项目ID和文件ID不能为空", str(context.exception))
        
    def test_save_upload_file_invalid_version(self):
        """测试无效版本号"""
        with self.assertRaises(ValidationError) as context:
            save_upload_file(
                project_id="proj-1",
                file_id="file-1",
                version=0,
                filename="test.txt",
                content=b"test"
            )
        
        self.assertIn("版本号必须大于0", str(context.exception))
        
    def test_save_upload_file_empty_content(self):
        """测试空内容"""
        with self.assertRaises(ValidationError) as context:
            save_upload_file(
                project_id="proj-1",
                file_id="file-1",
                version=1,
                filename="test.txt",
                content=b""
            )
        
        self.assertIn("文件内容不能为空", str(context.exception))
        
    @patch('app.services.file_service.settings')
    @patch('app.services.file_service.check_disk_space')
    def test_save_upload_file_mkdir_error(self, mock_check_disk, mock_settings):
        """测试创建目录失败"""
        mock_settings.UPLOAD_DIR = "/nonexistent/path"
        mock_check_disk.return_value = True
        
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("权限不足")
            
            with self.assertRaises(StorageError) as context:
                save_upload_file(
                    project_id="proj-1",
                    file_id="file-1",
                    version=1,
                    filename="test.txt",
                    content=b"test"
                )
            
            self.assertIn("创建存储目录失败", str(context.exception))
            
    @patch('app.services.file_service.settings')
    @patch('app.services.file_service.check_disk_space')
    def test_save_upload_file_atomic_write_failure(self, mock_check_disk, mock_settings):
        """测试原子写入失败时清理临时文件"""
        mock_settings.UPLOAD_DIR = self.temp_dir
        mock_check_disk.return_value = True
        
        with patch('builtins.open') as mock_open:
            mock_open.side_effect = IOError("写入失败")
            
            with self.assertRaises(StorageError):
                save_upload_file(
                    project_id="proj-1",
                    file_id="file-1",
                    version=1,
                    filename="test.txt",
                    content=b"test"
                )


class TestReadFileContent(unittest.TestCase):
    """测试读取文件内容功能"""
    
    def setUp(self):
        """创建临时文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"
        self.test_file.write_bytes(b"Test content")
        
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir)
        
    def test_read_file_content_full(self):
        """测试完整读取"""
        content = read_file_content(self.test_file)
        self.assertEqual(content, b"Test content")
        
    def test_read_file_content_chunked(self):
        """测试分块读取"""
        content = read_file_content(self.test_file, chunk_size=4)
        self.assertEqual(content, b"Test content")
        
    def test_read_file_content_not_found(self):
        """测试文件不存在"""
        non_existent = Path(self.temp_dir) / "not_exist.txt"
        
        with self.assertRaises(ResourceNotFound) as context:
            read_file_content(non_existent)
        
        self.assertIn("文件", str(context.exception))
        
    def test_read_file_content_error(self):
        """测试读取错误"""
        with patch('builtins.open') as mock_open:
            mock_open.side_effect = IOError("读取失败")
            
            with self.assertRaises(StorageError):
                read_file_content(self.test_file)


class TestDeleteFile(unittest.TestCase):
    """测试删除文件功能"""
    
    def setUp(self):
        """创建临时文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"
        self.test_file.write_text("test")
        
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    @patch('app.services.file_service.settings')
    def test_delete_file_safe_mode(self, mock_settings):
        """测试安全删除（移动到回收站）"""
        trash_dir = Path(self.temp_dir) / "canonical-data" / "trash"
        mock_settings.UPLOAD_DIR = self.temp_dir
        mock_settings.trash_dir = trash_dir
        
        # 清理回收站目录以确保测试独立
        if trash_dir.exists():
            shutil.rmtree(trash_dir)
        
        result = delete_file(self.test_file, safe=True)
        
        self.assertTrue(result)
        self.assertFalse(self.test_file.exists())
        # 验证文件移动到回收站
        trash_files = list(trash_dir.glob("*")) if trash_dir.exists() else []
        self.assertEqual(len(trash_files), 1)
        
    def test_delete_file_unsafe_mode(self):
        """测试直接删除"""
        result = delete_file(self.test_file, safe=False)
        
        self.assertTrue(result)
        self.assertFalse(self.test_file.exists())
        
    def test_delete_file_not_exist(self):
        """测试删除不存在的文件"""
        non_existent = Path(self.temp_dir) / "not_exist.txt"
        
        result = delete_file(non_existent, safe=False)
        
        self.assertTrue(result)
        
    def test_delete_file_error(self):
        """测试删除错误"""
        with patch('pathlib.Path.unlink') as mock_unlink:
            mock_unlink.side_effect = PermissionError("权限不足")
            
            with self.assertRaises(StorageError):
                delete_file(self.test_file, safe=False)


class TestDeleteProjectFiles(unittest.TestCase):
    """测试删除项目文件功能"""
    
    def setUp(self):
        """创建临时项目目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "project-1"
        self.project_dir.mkdir()
        
        # 创建一些测试文件
        (self.project_dir / "file1.txt").write_text("content1")
        (self.project_dir / "file2.txt").write_text("content2")
        subdir = self.project_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")
        
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    @patch('app.services.file_service.settings')
    def test_delete_project_files_success(self, mock_settings):
        """测试正常删除项目文件"""
        mock_settings.UPLOAD_DIR = self.temp_dir
        mock_settings.trash_dir = Path(self.temp_dir) / "canonical-data" / "trash"
        
        count = delete_project_files("project-1")
        
        self.assertEqual(count, 3)  # 3个文件
        self.assertFalse(self.project_dir.exists())
        
    @patch('app.services.file_service.settings')
    def test_delete_project_files_not_exist(self, mock_settings):
        """测试项目目录不存在"""
        mock_settings.UPLOAD_DIR = self.temp_dir
        
        count = delete_project_files("non-existent-project")
        
        self.assertEqual(count, 0)
        
    @patch('app.services.file_service.settings')
    def test_delete_project_files_error(self, mock_settings):
        """测试删除错误"""
        mock_settings.UPLOAD_DIR = self.temp_dir
        
        with patch('shutil.move') as mock_move:
            mock_move.side_effect = OSError("移动失败")
            
            with self.assertRaises(StorageError):
                delete_project_files("project-1")


    @patch('app.services.file_service.settings')
    def test_delete_project_files_rejects_path_traversal(self, mock_settings):
        """娴嬭瘯 project_id traversal 不会删除 UPLOAD_DIR 外目录"""
        upload_dir = Path(self.temp_dir) / "uploads"
        upload_dir.mkdir()
        outside_project = Path(self.temp_dir) / "outside-project"
        outside_project.mkdir()
        (outside_project / "secret.txt").write_text("keep me")

        mock_settings.UPLOAD_DIR = str(upload_dir)
        mock_settings.trash_dir = Path(self.temp_dir) / "canonical-data" / "trash"

        with patch('app.services.file_service.shutil.move') as mock_move:
            with self.assertRaises(StorageError):
                delete_project_files("../outside-project")

        mock_move.assert_not_called()
        self.assertTrue(outside_project.exists())
        self.assertTrue((outside_project / "secret.txt").exists())


class TestGetStoragePath(unittest.TestCase):
    """测试获取存储路径功能"""
    
    @patch('app.services.file_service.settings')
    def test_get_storage_path(self, mock_settings):
        """测试获取存储路径"""
        mock_settings.UPLOAD_DIR = "/uploads"
        
        path = get_storage_path("proj-1", "file-1", 1, "test.docx")
        
        self.assertIn("proj-1", str(path))
        self.assertIn("file-1", str(path))
        self.assertIn("v1_test.docx", str(path))
        
    @patch('app.services.file_service.settings')
    def test_get_storage_path_sanitizes_filename(self, mock_settings):
        """测试文件名清理"""
        mock_settings.UPLOAD_DIR = "/uploads"
        
        path = get_storage_path("proj-1", "file-1", 1, "../../../etc/passwd")
        
        # 验证路径遍历攻击被阻止
        self.assertNotIn("..", str(path))


class TestFileExists(unittest.TestCase):
    """测试检查文件存在功能"""
    
    def setUp(self):
        """创建临时文件"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir)
        
    @patch('app.services.file_service.settings')
    def test_file_exists_true(self, mock_settings):
        """测试文件存在"""
        mock_settings.UPLOAD_DIR = self.temp_dir
        
        # 创建测试文件
        project_dir = Path(self.temp_dir) / "proj-1" / "file-1"
        project_dir.mkdir(parents=True)
        test_file = project_dir / "v1_test.txt"
        test_file.write_text("test")
        
        result = file_exists("proj-1", "file-1", 1, "test.txt")
        self.assertTrue(result)
        
    @patch('app.services.file_service.settings')
    def test_file_exists_false(self, mock_settings):
        """测试文件不存在"""
        mock_settings.UPLOAD_DIR = self.temp_dir
        
        result = file_exists("proj-1", "file-1", 1, "test.txt")
        self.assertFalse(result)


class TestGetFileSize(unittest.TestCase):
    """测试获取文件大小功能"""
    
    def setUp(self):
        """创建临时文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.txt"
        self.test_file.write_bytes(b"x" * 100)
        
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir)
        
    def test_get_file_size_success(self):
        """测试正常获取大小"""
        size = get_file_size(self.test_file)
        self.assertEqual(size, 100)
        
    def test_get_file_size_not_found(self):
        """测试文件不存在"""
        non_existent = Path(self.temp_dir) / "not_exist.txt"
        
        with self.assertRaises(ResourceNotFound):
            get_file_size(non_existent)
            
    def test_get_file_size_error(self):
        """测试获取大小错误"""
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.side_effect = OSError("统计失败")
            
            with self.assertRaises(StorageError):
                get_file_size(self.test_file)


class TestCopyFile(unittest.TestCase):
    """测试复制文件功能"""
    
    def setUp(self):
        """创建临时文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.src_file = Path(self.temp_dir) / "source.txt"
        self.src_file.write_text("source content")
        self.dst_file = Path(self.temp_dir) / "dest.txt"
        
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir)
        
    def test_copy_file_success(self):
        """测试正常复制"""
        result = copy_file(self.src_file, self.dst_file)
        
        self.assertEqual(result, self.dst_file)
        self.assertTrue(self.dst_file.exists())
        self.assertEqual(self.dst_file.read_text(), "source content")
        
    def test_copy_file_src_not_exist(self):
        """测试源文件不存在"""
        non_existent = Path(self.temp_dir) / "not_exist.txt"
        
        with self.assertRaises(ResourceNotFound):
            copy_file(non_existent, self.dst_file)
            
    def test_copy_file_dst_exists_no_overwrite(self):
        """测试目标文件存在且不覆盖"""
        self.dst_file.write_text("existing")
        
        with self.assertRaises(StorageError) as context:
            copy_file(self.src_file, self.dst_file, overwrite=False)
        
        self.assertIn("目标文件已存在", str(context.exception))
        
    def test_copy_file_dst_exists_with_overwrite(self):
        """测试目标文件存在且覆盖"""
        self.dst_file.write_text("existing")
        
        result = copy_file(self.src_file, self.dst_file, overwrite=True)
        
        self.assertEqual(self.dst_file.read_text(), "source content")


class TestGetStorageUsage(unittest.TestCase):
    """测试获取存储使用情况功能"""
    
    def setUp(self):
        """创建临时目录结构"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建项目目录和文件
        for i in range(3):
            project_dir = Path(self.temp_dir) / f"project-{i}"
            project_dir.mkdir()
            for j in range(2):
                (project_dir / f"file-{j}.txt").write_text("x" * 1000)
                
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir)
        
    @patch('app.services.file_service.settings')
    def test_get_storage_usage_success(self, mock_settings):
        """测试正常获取使用情况"""
        mock_settings.UPLOAD_DIR = self.temp_dir
        
        usage = get_storage_usage()
        
        self.assertEqual(usage["file_count"], 6)  # 3项目 x 2文件
        self.assertEqual(usage["project_count"], 3)
        self.assertEqual(usage["total_size"], 6000)  # 6 x 1000字节
        self.assertIn("size_human", usage)
        
    @patch('app.services.file_service.settings')
    def test_get_storage_usage_empty(self, mock_settings):
        """测试空存储"""
        empty_dir = tempfile.mkdtemp()
        mock_settings.UPLOAD_DIR = empty_dir
        
        usage = get_storage_usage()
        
        self.assertEqual(usage["file_count"], 0)
        self.assertEqual(usage["project_count"], 0)
        self.assertEqual(usage["total_size"], 0)
        
        shutil.rmtree(empty_dir)
        
    @patch('app.services.file_service.settings')
    def test_get_storage_usage_not_exist(self, mock_settings):
        """测试目录不存在"""
        mock_settings.UPLOAD_DIR = "/nonexistent/path"
        
        usage = get_storage_usage()
        
        self.assertEqual(usage["file_count"], 0)
        self.assertEqual(usage["total_size"], 0)
        self.assertEqual(usage["size_human"], "0 B")


if __name__ == "__main__":
    unittest.main()
