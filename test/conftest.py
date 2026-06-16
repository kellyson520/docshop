"""
Pytest 配置 — 文档存储和转换的共享 fixtures。

所有测试文件在 /test 目录下统一管理。
"""
import os
import sys
import pytest
import tempfile
from pathlib import Path

# 确保 backend 在 sys.path 中
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# 设置测试环境变量
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("UPLOAD_DIR", str(backend_dir / "data" / "uploads"))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-characters-ok")

from app.services.document_store import (
    ROOT, doc_root, dir_original, dir_pdf, dir_images, meta_path,
    file_sha256, store_original, store_pdf, generate_images,
    get_cached_pdf, get_cached_images,
    register_hash, _lookup_hash, find_existing_file_id, ensure_registered,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def sample_pdf():
    """有效的 1 页 PDF 文件。"""
    return str(FIXTURES / "sample.pdf")


@pytest.fixture
def sample_docx():
    """有效的 1 页 DOCX 文件。"""
    return str(FIXTURES / "sample.docx")


@pytest.fixture
def tmp_doc_root(monkeypatch, tmp_path):
    """隔离的 document_store 根目录。"""
    test_root = str(tmp_path / "documents")
    import app.services.document_store as ds
    monkeypatch.setattr(ds, "ROOT", test_root)
    return test_root


@pytest.fixture
def fid():
    """固定的测试 file_id。"""
    return "test-00000000-0000-0000-0000-000000000001"
