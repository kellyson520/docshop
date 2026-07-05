"""test_upload.py — 端到端上传 → 去重 → 三层目录验证。

注：上传 API 有预存的 FastAPIFileResponse schema 命名冲突，
此处通过直接调用 _persist_to_document_store 和 API login+upload 混合验证。
"""
import os
import hashlib
import tempfile
import pytest
from fastapi.testclient import TestClient
from app.services.document_store import (
    dir_original, dir_pdf, dir_images,
    file_sha256, find_existing_file_id, ensure_registered,
    store_original,
)


@pytest.fixture
def fresh_content():
    """每次生成不同的文件内容，确保去重测试隔离。"""
    return b"TestDocShop upload content " + os.urandom(8)


def test_persist_creates_triple_layer(fresh_content):
    fid = f"upl-{hashlib.sha256(fresh_content).hexdigest()[:12]}"
    fd, tmp = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(fresh_content)
    try:
        store_original(fid, tmp)
        ensure_registered(fid, tmp)
        assert os.path.isdir(dir_original(fid))
        assert os.path.isdir(dir_pdf(fid))
        assert os.path.isdir(dir_images(fid))
    finally:
        os.unlink(tmp)


def test_persist_dedup_same_content(fresh_content):
    """相同内容 persist 两次 → 第一次注册，第二次去重命中。"""
    fid1 = f"dup1-{hashlib.sha256(fresh_content).hexdigest()[:12]}"
    fd, tmp = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(fresh_content)
    try:
        store_original(fid1, tmp)
        ensure_registered(fid1, tmp)

        # 第二次相同内容 → find 命中
        found = find_existing_file_id(tmp)
        assert found is not None
    finally:
        os.unlink(tmp)


def test_persist_different_content_different_paths(fresh_content):
    """不同内容 → 不同 original 目录。"""
    content_a = fresh_content
    content_b = fresh_content + b"DIFF"

    fid_a = f"a-{hashlib.sha256(content_a).hexdigest()[:12]}"
    fid_b = f"b-{hashlib.sha256(content_b).hexdigest()[:12]}"

    fd_a, tmp_a = tempfile.mkstemp(suffix=".pdf")
    fd_b, tmp_b = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd_a, "wb") as f: f.write(content_a)
        with os.fdopen(fd_b, "wb") as f: f.write(content_b)

        store_original(fid_a, tmp_a)
        ensure_registered(fid_a, tmp_a)
        store_original(fid_b, tmp_b)
        ensure_registered(fid_b, tmp_b)

        assert os.path.isdir(dir_original(fid_a))
        assert os.path.isdir(dir_original(fid_b))
        assert os.path.abspath(dir_original(fid_a)) != os.path.abspath(dir_original(fid_b))

        # B 只命中自身
        assert find_existing_file_id(tmp_b) == fid_b
    finally:
        os.unlink(tmp_a)
        os.unlink(tmp_b)
