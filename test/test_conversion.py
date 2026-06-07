"""test_conversion.py — 验证 DOCX/PDF → images HTML 转换流水线。"""

import os
import re
import pytest
from app.services.conversion_service import convert_to_images_html

@pytest.mark.slow
def test_convert_docx_to_images_html(tmp_doc_root, sample_docx):
    """DOCX → PDF（MS Word COM）→ JPEG 页面 → HTML。"""
    import time
    fid = "conv-docx-0000-0000-0000-000000000001"

    t0 = time.time()
    html = convert_to_images_html(fid, sample_docx, "docx")
    elapsed = time.time() - t0

    assert html is not None
    assert "<!DOCTYPE html>" in html
    assert "data:image/jpeg;base64," in html
    pages = len(re.findall(r'data:image/jpeg;base64,', html))
    assert pages >= 1
    print(f"\n  DOCX {pages} pages, {len(html) // 1024}KB, {elapsed:.1f}s")

def test_convert_pdf_to_images_html(tmp_doc_root, sample_pdf):
    """PDF → JPEG → HTML（跳过 Word→PDF）。"""
    import time
    fid = "conv-pdf-0000-0000-0000-000000000002"

    t0 = time.time()
    html = convert_to_images_html(fid, sample_pdf, "pdf")
    elapsed = time.time() - t0

    assert html is not None
    assert "data:image/jpeg;base64," in html
    pages = len(re.findall(r'data:image/jpeg;base64,', html))
    assert pages == 1

    # 缓存命中应该 < 2s
    t0 = time.time()
    html2 = convert_to_images_html(fid, sample_pdf, "pdf")
    cached = time.time() - t0
    assert html2 is not None
    assert cached < 2.0
    print(f"\n  PDF 1 page, cache hit {cached:.2f}s")

def test_convert_unsupported_type_returns_none(tmp_doc_root, sample_pdf):
    fid = "conv-bad-0000-0000-0000-000000000003"
    html = convert_to_images_html(fid, sample_pdf, "txt")
    assert html is None
