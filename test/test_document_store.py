"""test_document_store.py — 验证三层存储布局、哈希索引、缓存。"""

import os
import pytest
from app.services.document_store import (
    file_sha256, store_original, store_pdf, generate_images,
    get_cached_pdf, get_cached_images,
    register_hash, _lookup_hash, find_existing_file_id, ensure_registered,
    dir_original, dir_pdf, dir_images,
)

def test_file_sha256_consistent(sample_pdf):
    h1 = file_sha256(sample_pdf)
    h2 = file_sha256(sample_pdf)
    assert h1 == h2
    assert len(h1) == 64

def test_file_sha256_different(sample_pdf, sample_docx):
    assert file_sha256(sample_pdf) != file_sha256(sample_docx)

def test_triple_layer_created(tmp_doc_root, fid, sample_pdf):
    store_original(fid, sample_pdf)
    assert os.path.isdir(dir_original(fid))
    assert os.path.isfile(os.path.join(dir_original(fid), "original.pdf"))

def test_store_pdf_creates_file(tmp_doc_root, fid, sample_pdf):
    dest = store_pdf(fid, sample_pdf, file_sha256(sample_pdf))
    assert os.path.isfile(dest)

def test_hash_index_register_lookup(tmp_doc_root, fid, sample_pdf):
    h = file_sha256(sample_pdf)
    register_hash(h, fid)
    assert _lookup_hash(h) == fid

def test_find_existing_hit(tmp_doc_root, fid, sample_pdf):
    ensure_registered(fid, sample_pdf)
    assert find_existing_file_id(sample_pdf) == fid

def test_find_existing_miss(tmp_doc_root, tmp_path):
    # 全新随机内容的文件 — 绝无可能被注册过
    p = tmp_path / "never_registered.bin"
    p.write_bytes(b'\x00' * 64)
    assert find_existing_file_id(str(p)) is None

def test_generate_images_from_pdf(tmp_doc_root, fid, sample_pdf):
    import fitz
    pdf_dest = store_pdf(fid, sample_pdf, file_sha256(sample_pdf))
    doc = fitz.open(pdf_dest)
    pages = len(doc)
    doc.close()
    paths = generate_images(fid, pdf_dest, pages, file_sha256(pdf_dest),
                            dpi=72, quality=85, max_workers=1)
    assert len(paths) == pages
    for p in paths:
        assert os.path.isfile(p)
        assert os.path.getsize(p) > 500

def test_pdf_cache_hit(tmp_doc_root, fid, sample_pdf):
    h = file_sha256(sample_pdf)
    store_pdf(fid, sample_pdf, h)
    assert get_cached_pdf(fid, h) is not None

def test_pdf_cache_miss(tmp_doc_root, fid):
    assert get_cached_pdf(fid, "a" * 64) is None
