"""
文件服务模块测试

测试 file_service.py 中的核心功能，包括文件保存、扩展名提取、
原子写入、安全删除和磁盘空间检查等。
"""

import os
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.services.file_service import (
    save_upload_file,
    get_file_extension,
    check_disk_space,
    delete_file,
    calculate_file_hash,
)
from app.exceptions import ValidationError, StorageError, ResourceNotFound


# ===== test_save_upload_file: 测试正常文件保存 =====

class TestSaveUploadFile:
    """测试文件保存功能"""

    def test_save_upload_file(self, tmp_path):
        """测试正常文件保存：文件应被正确写入磁盘，返回路径、哈希和大小"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        content = b"Hello, this is a test file content."
        filename = "test_document.pdf"

        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(upload_dir)
            mock_settings.TEMP_DIR = str(tmp_path / "temp")

            storage_path, file_hash, file_size = save_upload_file(
                project_id="proj-001",
                file_id="file-001",
                version=1,
                filename=filename,
                content=content,
            )

        # 验证返回值
        assert isinstance(storage_path, str)
        assert file_hash == hashlib.sha256(content).hexdigest()
        assert file_size == len(content)

        # 验证文件确实存在于磁盘上
        assert Path(storage_path).exists()
        assert Path(storage_path).read_bytes() == content

    def test_save_upload_file_invalid_path(self, tmp_path):
        """测试无效路径：当上传目录无法创建时应抛出 StorageError"""
        # 使用一个不可能创建的路径来模拟目录创建失败
        content = b"test content"

        with patch("app.services.file_service.settings") as mock_settings:
            # 指向一个不存在的深层路径，且无法创建
            mock_settings.UPLOAD_DIR = "/dev/null/impossible/uploads"
            mock_settings.TEMP_DIR = str(tmp_path / "temp")

            with pytest.raises(StorageError):
                save_upload_file(
                    project_id="proj-001",
                    file_id="file-001",
                    version=1,
                    filename="test.pdf",
                    content=content,
                )

    def test_save_upload_file_empty_content(self, tmp_path):
        """测试空文件内容：应抛出 ValidationError"""
        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path / "uploads")
            mock_settings.TEMP_DIR = str(tmp_path / "temp")

            with pytest.raises(ValidationError, match="文件内容不能为空"):
                save_upload_file(
                    project_id="proj-001",
                    file_id="file-001",
                    version=1,
                    filename="test.pdf",
                    content=b"",
                )

    def test_save_upload_file_invalid_version(self, tmp_path):
        """测试无效版本号：版本号小于1时应抛出 ValidationError"""
        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path / "uploads")
            mock_settings.TEMP_DIR = str(tmp_path / "temp")

            with pytest.raises(ValidationError, match="版本号必须大于0"):
                save_upload_file(
                    project_id="proj-001",
                    file_id="file-001",
                    version=0,
                    filename="test.pdf",
                    content=b"content",
                )


# ===== test_get_file_extension: 测试各种文件扩展名提取 =====

class TestGetFileExtension:
    """测试文件扩展名提取功能"""

    def test_get_file_extension_pdf(self):
        """测试PDF文件扩展名提取"""
        assert get_file_extension("document.pdf") == ".pdf"

    def test_get_file_extension_docx(self):
        """测试DOCX文件扩展名提取"""
        assert get_file_extension("report.docx") == ".docx"

    def test_get_file_extension_xlsx(self):
        """测试XLSX文件扩展名提取"""
        assert get_file_extension("data.xlsx") == ".xlsx"

    def test_get_file_extension_uppercase(self):
        """测试大写扩展名：应被转换为小写"""
        assert get_file_extension("PHOTO.JPG") == ".jpg"
        assert get_file_extension("file.PDF") == ".pdf"

    def test_get_file_extension_double_dots(self):
        """测试多个点的文件名：应提取最后一个扩展名"""
        assert get_file_extension("archive.tar.gz") == ".gz"

    def test_get_file_extension_no_extension(self):
        """测试无扩展名文件：应返回空字符串"""
        assert get_file_extension("README") == ""
        assert get_file_extension("Makefile") == ""

    def test_get_file_extension_hidden_file(self):
        """测试隐藏文件（以点开头）"""
        # .bashrc 没有扩展名部分
        assert get_file_extension(".bashrc") == ""
        # .gitignore 也没有扩展名
        assert get_file_extension(".gitignore") == ""


# ===== test_atomic_write: 测试原子写入 =====

class TestAtomicWrite:
    """测试原子写入功能（通过 save_upload_file 间接测试）"""

    def test_atomic_write(self, tmp_path):
        """
        测试原子写入：文件应通过临时文件写入后再重命名，
        确保写入过程中不会出现不完整的文件。
        """
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        content = b"Atomic write test content " * 100
        filename = "atomic_test.docx"

        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(upload_dir)
            mock_settings.TEMP_DIR = str(tmp_path / "temp")

            storage_path, file_hash, file_size = save_upload_file(
                project_id="proj-atomic",
                file_id="file-atomic",
                version=1,
                filename=filename,
                content=content,
            )

        # 验证最终文件内容完整
        saved_content = Path(storage_path).read_bytes()
        assert saved_content == content
        assert len(saved_content) == len(content)

        # 验证没有残留的临时文件
        dir_path = Path(storage_path).parent
        temp_files = list(dir_path.glob(".tmp_*"))
        assert len(temp_files) == 0, "不应存在残留的临时文件"

    def test_atomic_write_overwrite(self, tmp_path):
        """
        测试原子写入覆盖：同一版本重新写入应覆盖旧文件
        """
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        content_v1 = b"Version 1 content"
        content_v2 = b"Version 2 content - updated"

        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(upload_dir)
            mock_settings.TEMP_DIR = str(tmp_path / "temp")

            # 第一次写入
            path1, hash1, size1 = save_upload_file(
                project_id="proj-001",
                file_id="file-001",
                version=1,
                filename="overwrite_test.pdf",
                content=content_v1,
            )

            # 第二次写入（同版本覆盖）
            path2, hash2, size2 = save_upload_file(
                project_id="proj-001",
                file_id="file-001",
                version=1,
                filename="overwrite_test.pdf",
                content=content_v2,
            )

        # 路径相同，但内容和哈希不同
        assert path1 == path2
        assert hash1 != hash2
        assert Path(path2).read_bytes() == content_v2


# ===== test_safe_delete: 测试安全删除 =====

class TestSafeDelete:
    """测试安全删除功能"""

    def test_safe_delete(self, tmp_path):
        """测试安全删除：文件应被移动到回收站目录而非直接删除"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        # 创建测试文件
        test_file = upload_dir / "test_file.txt"
        test_file.write_text("content to delete")

        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(upload_dir)

            result = delete_file(test_file, safe=True)

        assert result is True
        # 原文件不应存在
        assert not test_file.exists()
        # 回收站目录应存在
        trash_dir = upload_dir.parent / "trash"
        assert trash_dir.exists()
        # 回收站中应有文件
        trash_files = list(trash_dir.glob("*"))
        assert len(trash_files) == 1

    def test_safe_delete_nonexistent_file(self, tmp_path):
        """测试删除不存在的文件：应返回 True（不报错）"""
        nonexistent = tmp_path / "nonexistent.txt"

        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path / "uploads")

            result = delete_file(nonexistent, safe=True)

        assert result is True

    def test_safe_delete_direct(self, tmp_path):
        """测试直接删除（非安全模式）：文件应被直接删除"""
        test_file = tmp_path / "direct_delete.txt"
        test_file.write_text("delete me")

        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path / "uploads")

            result = delete_file(test_file, safe=False)

        assert result is True
        assert not test_file.exists()
        # 不应创建回收站目录
        trash_dir = tmp_path / "uploads" / ".." / "trash"
        assert not trash_dir.exists()


# ===== test_check_disk_space: 测试磁盘空间检查 =====

class TestCheckDiskSpace:
    """测试磁盘空间检查功能"""

    def test_check_disk_space_sufficient(self, tmp_path):
        """测试磁盘空间充足：应返回 True"""
        # 只需要 1 字节，正常情况下磁盘空间充足
        result = check_disk_space(1, tmp_path)
        assert result is True

    def test_check_disk_space_insufficient(self, tmp_path):
        """测试磁盘空间不足：应抛出 StorageError"""
        # 模拟一个极大的空间需求
        huge_size = 10 * 1024 * 1024 * 1024 * 1024 * 1024  # 10 TB

        with patch("os.statvfs") as mock_statvfs:
            # 模拟返回极小的可用空间
            mock_stat = MagicMock()
            mock_stat.f_frsize = 4096
            mock_stat.f_bavail = 1  # 只有 4096 字节可用
            mock_statvfs.return_value = mock_stat

            with pytest.raises(StorageError, match="磁盘空间不足"):
                check_disk_space(huge_size, tmp_path)

    def test_check_disk_space_statvfs_error(self, tmp_path):
        """测试 statvfs 调用失败：应返回 True（容错处理）"""
        with patch("os.statvfs", side_effect=OSError("无法访问")):
            # 无法检查磁盘空间时，默认放行
            result = check_disk_space(1024, tmp_path)
            assert result is True


# ===== test_calculate_file_hash: 测试哈希计算 =====

class TestCalculateFileHash:
    """测试文件哈希计算功能"""

    def test_calculate_file_hash(self):
        """测试哈希计算：应返回正确的 SHA-256 哈希值"""
        content = b"test content for hashing"
        expected_hash = hashlib.sha256(content).hexdigest()

        result = calculate_file_hash(content)

        assert result == expected_hash
        assert len(result) == 64  # SHA-256 哈希长度为 64 个十六进制字符

    def test_calculate_file_hash_empty(self):
        """测试空内容的哈希计算"""
        content = b""
        expected_hash = hashlib.sha256(content).hexdigest()

        result = calculate_file_hash(content)

        assert result == expected_hash


class TestSaveUploadFileExtended:
    """文件保存扩展测试 - 覆盖未覆盖行"""

    def test_save_upload_file_version_exists(self, tmp_path):
        """测试版本目录已存在（行122-123: 目录已存在时 mkdir 不报错）"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        content = b"Version exists test content."
        filename = "test_document.pdf"

        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(upload_dir)
            mock_settings.TEMP_DIR = str(tmp_path / "temp")

            # 第一次保存
            storage_path1, file_hash1, file_size1 = save_upload_file(
                project_id="proj-001",
                file_id="file-001",
                version=1,
                filename=filename,
                content=content,
            )

            # 第二次保存（版本目录已存在，行122-123: mkdir exist_ok=True）
            storage_path2, file_hash2, file_size2 = save_upload_file(
                project_id="proj-001",
                file_id="file-001",
                version=2,
                filename=filename,
                content=content,
            )

            # 验证两个版本都成功保存
            assert Path(storage_path1).exists()
            assert Path(storage_path2).exists()
            assert file_hash1 == file_hash2


class TestAtomicWriteExtended:
    """原子写入扩展测试 - 覆盖未覆盖行"""

    def test_atomic_write_existing_file(self, tmp_path):
        """测试覆盖已存在的文件（行148-149: 原子写入覆盖）"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        content_v1 = b"Original content"
        content_v2 = b"Updated content"

        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(upload_dir)
            mock_settings.TEMP_DIR = str(tmp_path / "temp")

            # 第一次写入
            path1, _, _ = save_upload_file(
                project_id="proj-001",
                file_id="file-001",
                version=1,
                filename="test.pdf",
                content=content_v1,
            )

            # 第二次写入同版本（覆盖）
            path2, _, _ = save_upload_file(
                project_id="proj-001",
                file_id="file-001",
                version=1,
                filename="test.pdf",
                content=content_v2,
            )

            # 路径相同但内容已更新
            assert path1 == path2
            assert Path(path2).read_bytes() == content_v2


class TestReadFileContentExtended:
    """读取文件内容扩展测试 - 覆盖未覆盖行"""

    def test_read_file_content_not_found(self, tmp_path):
        """测试读取不存在的文件（行279-282: ResourceNotFound 异常）"""
        from app.services.file_service import read_file_content

        nonexistent = tmp_path / "nonexistent" / "file.txt"

        with pytest.raises(ResourceNotFound, match="文件"):
            read_file_content(nonexistent)

    def test_read_file_content_chunked(self, tmp_path):
        """测试分块读取文件"""
        from app.services.file_service import read_file_content

        test_file = tmp_path / "chunked_test.txt"
        content = b"A" * 10000 + b"B" * 10000
        test_file.write_bytes(content)

        result = read_file_content(test_file, chunk_size=4096)
        assert result == content


class TestCalculateFileHashExtended:
    """哈希计算扩展测试 - 覆盖未覆盖行"""

    def test_calculate_file_hash_large(self):
        """测试大文件哈希计算（行534-536: 正常哈希计算）"""
        # 创建较大的内容（1MB）
        content = b"Large file content for hash testing " * 5000
        expected_hash = hashlib.sha256(content).hexdigest()

        result = calculate_file_hash(content)

        assert result == expected_hash
        assert len(result) == 64


class TestGetStorageUsageExtended:
    """存储使用量扩展测试 - 覆盖未覆盖行"""

    def test_get_storage_usage_with_files(self, tmp_path):
        """测试有文件时的存储使用量（行588-590: 有文件时遍历计算）"""
        from app.services.file_service import get_storage_usage

        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        # 创建项目目录和文件
        project_dir = upload_dir / "proj-001"
        project_dir.mkdir()
        (project_dir / "file1.txt").write_bytes(b"Hello")
        (project_dir / "file2.txt").write_bytes(b"World")

        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(upload_dir)
            result = get_storage_usage()

        assert result["total_size"] == 10  # "Hello" + "World"
        assert result["file_count"] == 2
        assert result["project_count"] == 1
        assert "size_human" in result

    def test_get_storage_usage_error(self):
        """测试获取存储使用量异常（行588-590: 异常处理）"""
        from app.services.file_service import get_storage_usage

        with patch("app.services.file_service.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = "/tmp/uploads"
            with patch("pathlib.Path") as mock_path_cls:
                mock_upload_dir = MagicMock()
                mock_upload_dir.exists.return_value = True
                # 模拟 iterdir 抛出异常
                mock_upload_dir.iterdir.side_effect = PermissionError("权限不足")
                mock_path_cls.return_value = mock_upload_dir

                result = get_storage_usage()

        # 异常时应返回默认值
        assert result["total_size"] == 0
        assert result["file_count"] == 0
        assert result["project_count"] == 0
        assert "error" in result
