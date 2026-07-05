
"""????????????"""

from pathlib import Path

import pytest


def test_large_preview_skeleton_does_not_generate_all_images(monkeypatch, tmp_path):
    """?????????????? skeleton??????????????"""
    from app.services import conversion_service as svc

    source = tmp_path / "large.docx"
    source.write_bytes(b"fake-docx")
    pdf = tmp_path / "large.pdf"
    pdf.write_bytes(b"fake-pdf")

    class FakeDoc:
        def __len__(self):
            return svc.LARGE_FILE_THRESHOLD + 1

        def close(self):
            pass

    def fail_generate(*args, **kwargs):
        raise AssertionError("large skeleton preview must not batch-generate all page images")

    monkeypatch.setattr(svc, "_detect_engine", lambda: "docx2pdf")
    monkeypatch.setattr("app.services.document_store.store_original", lambda file_id, input_path: None)
    monkeypatch.setattr(svc, "_source_hash", lambda path: "hash-" + Path(path).suffix)
    monkeypatch.setattr(svc, "_ensure_pdf", lambda file_id, input_path, source_hash: str(pdf))
    monkeypatch.setattr("fitz.open", lambda path: FakeDoc())
    monkeypatch.setattr(svc, "_ensure_images", fail_generate)

    html = svc.convert_to_images_html("file-large", str(source), "docx", return_skeleton=True)

    assert "/api/v1/files/file-large/pages/1" in html
    assert f"/api/v1/files/file-large/pages/{svc.LARGE_FILE_THRESHOLD + 1}" in html


def test_small_preview_still_generates_images(monkeypatch, tmp_path):
    """?????????? HTML ????????????"""
    from app.services import conversion_service as svc

    source = tmp_path / "small.docx"
    source.write_bytes(b"fake-docx")
    pdf = tmp_path / "small.pdf"
    pdf.write_bytes(b"fake-pdf")
    image = tmp_path / "page_0001.jpg"
    image.write_bytes(b"jpg")
    calls = {"ensure_images": 0}

    class FakeDoc:
        def __len__(self):
            return 1

        def close(self):
            pass

    monkeypatch.setattr(svc, "_detect_engine", lambda: "docx2pdf")
    monkeypatch.setattr("app.services.document_store.store_original", lambda file_id, input_path: None)
    monkeypatch.setattr(svc, "_source_hash", lambda path: "hash-" + Path(path).suffix)
    monkeypatch.setattr(svc, "_ensure_pdf", lambda file_id, input_path, source_hash: str(pdf))
    monkeypatch.setattr("fitz.open", lambda path: FakeDoc())

    def fake_ensure_images(*args, **kwargs):
        calls["ensure_images"] += 1
        return [str(image)]

    monkeypatch.setattr(svc, "_ensure_images", fake_ensure_images)

    html = svc.convert_to_images_html("file-small", str(source), "docx", return_skeleton=True)

    assert calls["ensure_images"] == 1
    assert "data:image/jpeg;base64" in html


def test_page_endpoint_renders_only_requested_page_when_cache_misses(monkeypatch, tmp_path, client, auth_headers, db_session, test_user):
    """???????????????????????? 50+ ??"""
    from app.config import settings
    from app.models.project import Project
    from app.models.document_file import DocumentFile
    from app.models.file_version import FileVersion
    from app.services import document_store
    from app.services import conversion_service as svc

    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    source = upload_root / "large.docx"
    source.write_bytes(b"fake-docx")
    pdf = tmp_path / "large.pdf"
    pdf.write_bytes(b"fake-pdf")

    project = Project(name="preview", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(project_id=project.id, filename="large.docx", file_type="docx", current_version=1)
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(file_id=doc_file.id, version=1, storage_path=str(source), file_hash="hash", file_size=1)
    db_session.add(version)
    db_session.commit()

    class FakeDoc:
        def __len__(self):
            return 80

        def close(self):
            pass

    rendered = []

    def fake_render_page(args):
        page_idx, _pdf_path, img_dir, _dpi, _quality = args
        rendered.append(page_idx)
        Path(img_dir).mkdir(parents=True, exist_ok=True)
        out = Path(img_dir) / f"page_{page_idx + 1:04d}.jpg"
        out.write_bytes(b"jpg")
        return str(out)

    def fail_generate_images(*args, **kwargs):
        raise AssertionError("page endpoint must not batch-generate all images")

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr(svc, "_source_hash", lambda path: "hash")
    monkeypatch.setattr(svc, "_ensure_pdf", lambda file_id, path, source_hash: str(pdf))
    monkeypatch.setattr("fitz.open", lambda path: FakeDoc())
    monkeypatch.setattr(document_store, "_render_page", fake_render_page)
    monkeypatch.setattr(document_store, "generate_images", fail_generate_images)

    response = client.get(f"/api/v1/files/{doc_file.id}/pages/7", headers=auth_headers)

    assert response.status_code == 200
    assert response.content == b"jpg"
    assert rendered == [6]


def test_page_endpoint_allows_document_store_root(
    monkeypatch, tmp_path, client, auth_headers, db_session, test_user
):
    from app.models.project import Project
    from app.models.document_file import DocumentFile
    from app.models.file_version import FileVersion
    from app.services import document_store
    from app.services import conversion_service as svc
    from app.services import storage_path_policy

    documents_root = tmp_path / "documents"
    monkeypatch.setattr(document_store, "ROOT", str(documents_root))
    monkeypatch.setattr(storage_path_policy, "_is_testing_env", lambda: False)

    source = documents_root / "file-pages-docstore" / "original" / "large.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"%PDF-1.4 fake docstore pdf")

    project = Project(name="docstore-preview", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(project_id=project.id, filename="large.pdf", file_type="pdf", current_version=1)
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(file_id=doc_file.id, version=1, storage_path=str(source), file_hash="docstore-hash", file_size=source.stat().st_size)
    db_session.add(version)
    db_session.commit()

    class FakeDoc:
        def __len__(self):
            return 5

        def close(self):
            pass

    rendered = []

    def fake_render_single_page(file_id, pdf_path, page_num, page_count, pdf_hash, quality=75):
        rendered.append(page_num)
        out = Path(document_store.dir_page_images(file_id, pdf_hash)) / f"page_{page_num:04d}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"docstore-jpg")
        return str(out)

    monkeypatch.setattr(svc, "_source_hash", lambda path: "docstore-page-hash")
    monkeypatch.setattr("fitz.open", lambda path: FakeDoc())
    monkeypatch.setattr(document_store, "render_single_page", fake_render_single_page)

    response = client.get(f"/api/v1/files/{doc_file.id}/pages/3", headers=auth_headers)

    assert response.status_code == 200
    assert response.content == b"docstore-jpg"
    assert rendered == [3]


def test_page_endpoint_rejects_storage_path_outside_allowed_roots(
    monkeypatch, tmp_path, client, auth_headers, db_session, test_user
):
    from app.config import settings
    from app.models.project import Project
    from app.models.document_file import DocumentFile
    from app.models.file_version import FileVersion
    from app.services import document_store
    from app.services import storage_path_policy

    documents_root = tmp_path / "documents"
    upload_root = tmp_path / "uploads"
    monkeypatch.setattr(document_store, "ROOT", str(documents_root))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr(storage_path_policy, "_is_testing_env", lambda: False)

    outside_pdf = tmp_path / "outside" / "blocked.pdf"
    outside_pdf.parent.mkdir(parents=True, exist_ok=True)
    outside_pdf.write_bytes(b"%PDF-1.4 blocked")

    project = Project(name="outside-root-preview", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(project_id=project.id, filename="blocked.pdf", file_type="pdf", current_version=1)
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        storage_path=str(outside_pdf),
        file_hash="outside-root-preview",
        file_size=outside_pdf.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()

    class FakeDoc:
        def __len__(self):
            return 2

        def close(self):
            pass

    def fake_render_single_page(file_id, pdf_path, page_num, page_count, pdf_hash, quality=75):
        out = Path(document_store.dir_page_images(file_id, pdf_hash)) / f"page_{page_num:04d}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"blocked-jpg")
        return str(out)

    monkeypatch.setattr("fitz.open", lambda path: FakeDoc())
    monkeypatch.setattr(document_store, "render_single_page", fake_render_single_page)
    monkeypatch.setattr("app.services.conversion_service._source_hash", lambda path: "outside-root-preview-hash")

    response = client.get(f"/api/v1/files/{doc_file.id}/pages/1", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_large_preview_threshold_is_over_50_pages():
    """???? 50 ????????????? 51 ????"""
    from app.services.conversion_service import LARGE_FILE_THRESHOLD

    assert LARGE_FILE_THRESHOLD == 50


def test_docx_line_spacing_length_is_rendered_as_pt_not_huge_unitless_value():
    """Word fixed line spacing must not become CSS like line-height:406400."""
    from docx.shared import Pt
    from app.services.conversion_service import _format_docx_line_height

    assert _format_docx_line_height(Pt(32)) == "32pt"
    assert _format_docx_line_height(1.5) == "1.5"
    assert _format_docx_line_height(406400) == "32pt"
    assert _format_docx_line_height(406400) != "406400"


def test_skeleton_html_uses_custom_page_url_prefix_for_share_preview():
    """?????????????????????????????????"""
    from app.services.conversion_service import build_skeleton_html

    html = build_skeleton_html(
        "file-id",
        2,
        2,
        page_url_prefix="/api/v1/share/share-token/files/file-id/pages",
    )

    assert "/api/v1/share/share-token/files/file-id/pages/1" in html
    assert "/api/v1/files/file-id/pages/1" not in html


def test_skeleton_html_uses_fullscreen_immersive_layout_instead_of_fixed_container():
    from app.services.conversion_service import build_skeleton_html

    html = build_skeleton_html("file-id", 1, 1)

    assert "max-width:860px" not in html
    assert "width:min(100%,1180px)" not in html
    assert '<div class="wrap">' not in html
    assert ".page img{display:block;max-width:100%;width:auto;height:auto;margin:0 auto}" in html


def test_inline_images_html_drops_wrap_title_and_card_shell_for_immersive_preview(tmp_path):
    from app.services.conversion_service import _build_images_html

    image = tmp_path / "page_0001.jpg"
    image.write_bytes(b"jpg")

    html = _build_images_html("file-id", [str(image)], 1, title="Inline Preview · v1")

    assert '<div class="wrap">' not in html
    assert "<h2>Inline Preview · v1</h2>" not in html
    assert "max-width:860px" not in html
    assert "background:#e8e8e8" not in html
    assert "box-shadow:0 1px 4px rgba(0,0,0,.08)" not in html


def test_skeleton_html_drops_inner_wrap_title_and_card_shell_for_immersive_preview():
    from app.services.conversion_service import build_skeleton_html

    html = build_skeleton_html("file-id", 2, 2, title="Doc Preview · v3")

    assert '<div class="wrap">' not in html
    assert "<h2>Doc Preview · v3</h2>" not in html
    assert "width:min(100%,1180px)" not in html
    assert "background:#e8e8e8" not in html
    assert "box-shadow:0 1px 4px rgba(0,0,0,.08)" not in html


def test_inline_images_html_keeps_visible_bold_centered_title(tmp_path):
    from app.services.conversion_service import _build_images_html

    image = tmp_path / "page_0001.jpg"
    image.write_bytes(b"jpg")

    html = _build_images_html("file-id", [str(image)], 1, title="汽车服务 - protable.docx · v3")

    assert '<div class="preview-shell">' in html
    assert '<h1 class="preview-title">汽车服务 - protable.docx · v3</h1>' in html
    assert '.preview-title{text-align:center;' in html
    assert 'font-weight:700' in html
    assert 'max-width:min(100%,980px)' in html


def test_skeleton_html_keeps_visible_bold_centered_title():
    from app.services.conversion_service import build_skeleton_html

    html = build_skeleton_html("file-id", 2, 2, title="汽车服务 - protable.docx · v3")

    assert '<div class="preview-shell">' in html
    assert '<h1 class="preview-title">汽车服务 - protable.docx · v3</h1>' in html
    assert '.preview-title{text-align:center;' in html
    assert 'font-weight:700' in html
    assert 'max-width:min(100%,980px)' in html


def test_docx_html_preview_uses_readable_default_title():
    from app.services.conversion_service import _convert_docx_to_html

    html_constants = "\n".join(
        str(item) for item in _convert_docx_to_html.__code__.co_consts
        if isinstance(item, str)
    )

    assert "<title>文档预览</title>" in html_constants
    assert "<title>????</title>" not in html_constants


def test_docx_html_preview_drops_page_wrap_shell_styles():
    from app.services.conversion_service import _convert_docx_to_html

    html_constants = "\n".join(
        str(item) for item in _convert_docx_to_html.__code__.co_consts
        if isinstance(item, str)
    )

    assert ".page-wrap{max-width:210mm" not in html_constants
    assert "body{margin:0;padding:40px" not in html_constants


def test_word_export_wrapper_drops_docx_page_shell_styles():
    from app.services.conversion_service import _wrap_word_html

    html_constants = "\n".join(
        str(item) for item in _wrap_word_html.__code__.co_consts
        if isinstance(item, str)
    )

    assert ".docx-page {" not in html_constants
    assert "padding: 20px;" not in html_constants
    assert "box-shadow: 0 2px 20px rgba(0,0,0,.12);" not in html_constants


def test_docx_math_fallback_placeholder_is_readable():
    source = (Path(__file__).resolve().parents[1] / "app/services/conversion_service.py").read_text(encoding="utf-8")

    assert "[公式]" in source
    assert "[??]" not in source



def test_page_endpoint_rerenders_stale_cached_page_for_new_file_hash(monkeypatch, tmp_path, client, auth_headers, db_session, test_user):
    """?????????????????/PDF hash ??????????????????"""
    from app.config import settings
    from app.models.project import Project
    from app.models.document_file import DocumentFile
    from app.models.file_version import FileVersion
    from app.services import document_store
    from app.services import conversion_service as svc

    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    source = upload_root / "large-v2.docx"
    source.write_bytes(b"fake-docx-v2")
    pdf = tmp_path / "large-v2.pdf"
    pdf.write_bytes(b"fake-pdf-v2")

    project = Project(name="preview-stale", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(project_id=project.id, filename="large.docx", file_type="docx", current_version=2)
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(file_id=doc_file.id, version=2, storage_path=str(source), file_hash="hash-v2", file_size=1)
    db_session.add(version)
    db_session.commit()

    stale_dir = Path(document_store.dir_images(doc_file.id))
    stale_dir.mkdir(parents=True, exist_ok=True)
    stale_img = stale_dir / "page_0003.jpg"
    stale_img.write_bytes(b"old-image")

    class FakeDoc:
        def __len__(self):
            return 80

        def close(self):
            pass

    rendered = []

    def fake_render_page(args):
        page_idx, _pdf_path, img_dir, _dpi, _quality = args
        rendered.append(page_idx)
        out = Path(img_dir) / f"page_{page_idx + 1:04d}.jpg"
        out.write_bytes(b"new-image")
        return str(out)

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr(svc, "_source_hash", lambda path: "source-v2" if str(path).endswith("docx") else "pdf-v2")
    monkeypatch.setattr(svc, "_ensure_pdf", lambda file_id, path, source_hash: str(pdf))
    monkeypatch.setattr("fitz.open", lambda path: FakeDoc())
    monkeypatch.setattr(document_store, "_render_page", fake_render_page)

    response = client.get(f"/api/v1/files/{doc_file.id}/pages/3", headers=auth_headers)

    assert response.status_code == 200
    assert response.content == b"new-image"
    assert rendered == [2]


def test_convert_preview_skeleton_preserves_requested_version(monkeypatch, tmp_path):
    """??????????? URL ???? version?????????????"""
    from app.services import conversion_service as svc

    source = tmp_path / "large-v1.docx"
    source.write_bytes(b"fake-docx-v1")
    pdf = tmp_path / "large-v1.pdf"
    pdf.write_bytes(b"fake-pdf-v1")

    class FakeDoc:
        def __len__(self):
            return svc.LARGE_FILE_THRESHOLD + 1

        def close(self):
            pass

    monkeypatch.setattr(svc, "_detect_engine", lambda: "docx2pdf")
    monkeypatch.setattr("app.services.document_store.store_original", lambda file_id, input_path: None)
    monkeypatch.setattr(svc, "_source_hash", lambda path: "hash")
    monkeypatch.setattr(svc, "_ensure_pdf", lambda file_id, input_path, source_hash: str(pdf))
    monkeypatch.setattr("fitz.open", lambda path: FakeDoc())

    html = svc.convert_to_images_html("file-versioned", str(source), "docx", return_skeleton=True, version=1)

    assert "/api/v1/files/file-versioned/pages/1?version=1" in html


def test_cached_docx_preview_skeleton_uses_display_name_and_version(
    monkeypatch, tmp_path, client, auth_headers, db_session, test_user
):
    """缓存图片预览页标题应使用文件显示名称和实际版本，而不是固定“文档预览”。"""
    from app.config import settings
    from app.models.project import Project
    from app.models.document_file import DocumentFile
    from app.models.file_version import FileVersion
    from app.services import conversion_service as svc

    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    source = upload_root / "original.docx"
    source.write_bytes(b"fake-docx")
    pdf = tmp_path / "cached.pdf"
    pdf.write_bytes(b"fake-pdf")
    image = tmp_path / "page_0001.jpg"
    image.write_bytes(b"jpg")

    project = Project(name="preview-title", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename="original.docx",
        display_name="后台显示名.docx",
        file_type="docx",
        current_version=3,
    )
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=3,
        storage_path=str(source),
        file_hash="hash-v3",
        file_size=source.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()

    class FakeDoc:
        def __len__(self):
            return 1

        def close(self):
            pass

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr(svc, "_source_hash", lambda path: "source-hash" if str(path).endswith(".docx") else "pdf-hash")
    monkeypatch.setattr("app.services.document_store.get_cached_pdf", lambda file_id, source_hash: str(pdf))
    monkeypatch.setattr("app.services.document_store.get_cached_images", lambda file_id, pdf_hash, page_count: [str(image)])
    monkeypatch.setattr("fitz.open", lambda path: FakeDoc())

    response = client.get(f"/api/v1/files/{doc_file.id}/preview?version=3", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert "后台显示名.docx · v3" in response.text
    assert "<h2>文档预览</h2>" not in response.text



def test_docx2pdf_timeout_returns_none_and_terminates_worker(monkeypatch, tmp_path):
    """Word COM ???????????? None?????? worker?????????????"""
    import time
    from app.services import conversion_service as svc

    source = tmp_path / "stuck.docx"
    source.write_bytes(b"fake-docx")

    class FakeQueue:
        def get_nowait(self):
            raise Exception("empty")

    class FakeProcess:
        def __init__(self):
            self.terminated = False
            self.join_calls = []

        def join(self, timeout=None):
            self.join_calls.append(timeout)
            time.sleep(0.01)

        def is_alive(self):
            return not self.terminated

        def terminate(self):
            self.terminated = True

    fake_process = FakeProcess()

    def fake_start_worker(input_path, output_dir):
        return fake_process, FakeQueue()

    monkeypatch.setattr(svc, "_start_docx2pdf_worker", fake_start_worker)

    begin = time.time()
    result = svc._convert_via_docx2pdf(str(source), timeout_seconds=0.05)
    elapsed = time.time() - begin

    assert result is None
    assert fake_process.terminated is True
    assert fake_process.join_calls[0] == 0.05
    assert elapsed < 1


def test_docx2pdf_sanitizes_external_image_links_before_word_conversion(monkeypatch, tmp_path):
    """Word COM 转换前应把 DOCX 外链图片改成本地占位图，避免打开文档时联网卡死。"""
    import zipfile
    from pathlib import Path
    from app.services import conversion_service as svc

    source = tmp_path / "external-images.docx"
    rel_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
    Target="http://example.test/slow.png"
    TargetMode="External"/>
</Relationships>
"""
    with zipfile.ZipFile(source, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<w:document/>")
        zf.writestr("word/_rels/document.xml.rels", rel_xml)

    captured = {}

    class FakeProcess:
        def join(self, timeout=None):
            return None

        def is_alive(self):
            return False

    class FakeQueue:
        def __init__(self, pdf_path):
            self.pdf_path = pdf_path

        def get_nowait(self):
            return {"ok": True, "path": self.pdf_path}

    def fake_start_worker(input_path, output_dir):
        captured["input_path"] = input_path
        with zipfile.ZipFile(input_path) as zf:
            captured["rels"] = zf.read("word/_rels/document.xml.rels").decode("utf-8")
            captured["content_types"] = zf.read("[Content_Types].xml").decode("utf-8")
            captured["names"] = set(zf.namelist())
        pdf_path = Path(output_dir) / "external-images.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n")
        return FakeProcess(), FakeQueue(str(pdf_path))

    monkeypatch.setattr(svc, "_start_docx2pdf_worker", fake_start_worker)

    result = svc._convert_via_docx2pdf(str(source), timeout_seconds=5)

    assert result is not None
    assert captured["input_path"] != str(source)
    assert 'TargetMode="External"' not in captured["rels"]
    assert 'Target="media/external_image_placeholder.png"' in captured["rels"]
    assert "word/media/external_image_placeholder.png" in captured["names"]
    assert 'Extension="png"' in captured["content_types"]



def test_ensure_pdf_failure_is_cached_to_avoid_repeated_word_timeouts(monkeypatch, tmp_path):
    """???? Word ? PDF ????????????????? fallback ???? Word?"""
    from app.services import conversion_service as svc

    source = tmp_path / "bad.docx"
    source.write_bytes(b"bad-docx")
    calls = {"convert": 0}
    meta = {}

    def fake_convert(path):
        calls["convert"] += 1
        return None

    monkeypatch.setattr(svc, "_read_meta_internal", lambda file_id: dict(meta))
    monkeypatch.setattr(svc, "_write_meta_internal", lambda file_id, data: meta.update(data))
    monkeypatch.setattr("app.services.document_store.get_cached_pdf", lambda file_id, source_hash: None)
    monkeypatch.setattr(svc, "_convert_via_docx2pdf", fake_convert)

    first = svc._ensure_pdf("file-fail-cache", str(source), "source-hash")
    second = svc._ensure_pdf("file-fail-cache", str(source), "source-hash")

    assert first is None
    assert second is None
    assert calls["convert"] == 1
    assert meta["pdf_conversion_failed_hash"] == "source-hash"



def test_docx_preview_does_not_retry_word_pdf_fallback_after_image_preview_failure(monkeypatch, tmp_path, client, auth_headers, db_session, test_user):
    """DOCX ???????????? HTML????? convert_to_pdf ?? Word?"""
    from app.config import settings
    from app.models.project import Project
    from app.models.document_file import DocumentFile
    from app.models.file_version import FileVersion
    from app.routers import files as files_router

    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    source = upload_root / "slow.docx"
    source.write_bytes(b"fake-docx")

    project = Project(name="preview-fallback", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(project_id=project.id, filename="slow.docx", file_type="docx", current_version=1)
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(file_id=doc_file.id, version=1, storage_path=str(source), file_hash="hash", file_size=1)
    db_session.add(version)
    db_session.commit()

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr(files_router, "convert_to_images_html", lambda *args, **kwargs: None, raising=False)

    def fail_convert_to_pdf(*args, **kwargs):
        raise AssertionError("preview must not retry Word PDF conversion after image preview failure")

    monkeypatch.setattr("app.services.conversion_service.convert_to_pdf", fail_convert_to_pdf)
    monkeypatch.setattr("app.services.conversion_service.convert_to_html", lambda *args, **kwargs: ("<html>fallback</html>", "text/html; charset=utf-8", False))

    response = client.get(f"/api/v1/files/{doc_file.id}/preview", headers=auth_headers)

    assert response.status_code == 200
    assert b"fallback" in response.content



def test_preview_and_page_endpoints_accept_query_auth_token(monkeypatch, tmp_path, client, auth_token, db_session, test_user):
    """iframe/PDF/img ???????????? Authorization?????????? JWT?"""
    from app.config import settings
    from app.models.project import Project
    from app.models.document_file import DocumentFile
    from app.models.file_version import FileVersion
    from app.services import document_store

    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    source = upload_root / "large.pdf"
    source.write_bytes(b"fake-pdf")

    project = Project(name="query-token-preview", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(project_id=project.id, filename="large.pdf", file_type="pdf", current_version=1)
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(file_id=doc_file.id, version=1, storage_path=str(source), file_hash="hash", file_size=len(b"fake-pdf"))
    db_session.add(version)
    db_session.commit()

    class FakeDoc:
        def __len__(self):
            return 3

        def close(self):
            pass

    def fake_render_page(file_id, pdf_path, page_num, page_count, pdf_hash, quality=75):
        out = tmp_path / f"page_{page_num:04d}.jpg"
        out.write_bytes(b"jpg")
        return str(out)

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr("fitz.open", lambda path: FakeDoc())
    monkeypatch.setattr(document_store, "render_single_page", fake_render_page)

    preview = client.get(f"/api/v1/files/{doc_file.id}/preview?auth_token={auth_token}")
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("application/pdf")
    assert "inline" in preview.headers.get("content-disposition", "").lower()
    assert "attachment" not in preview.headers.get("content-disposition", "").lower()

    page = client.get(f"/api/v1/files/{doc_file.id}/pages/2?auth_token={auth_token}")
    assert page.status_code == 200
    assert page.content == b"jpg"



def test_docx_preview_does_not_trigger_background_word_preconversion(monkeypatch, tmp_path, client, auth_headers, db_session, test_user):
    """DOCX ????????? HTML?????????? Word COM ????"""
    from app.config import settings
    from app.models.project import Project
    from app.models.document_file import DocumentFile
    from app.models.file_version import FileVersion

    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    source = upload_root / "large.docx"
    source.write_bytes(b"fake-docx")

    project = Project(name="no-bg-word", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc_file = DocumentFile(project_id=project.id, filename="large.docx", file_type="docx", current_version=1)
    db_session.add(doc_file)
    db_session.commit()
    db_session.refresh(doc_file)

    version = FileVersion(file_id=doc_file.id, version=1, storage_path=str(source), file_hash="hash", file_size=1)
    db_session.add(version)
    db_session.commit()

    calls = {"trigger": 0}

    def fake_trigger_preconversion(*args, **kwargs):
        calls["trigger"] += 1

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr("app.services.conversion_service.convert_to_html", lambda *args, **kwargs: ("<html>docx html</html>", "text/html; charset=utf-8", False))
    monkeypatch.setattr("app.services.conversion_service.trigger_preconversion", fake_trigger_preconversion)

    response = client.get(f"/api/v1/files/{doc_file.id}/preview", headers=auth_headers)

    assert response.status_code == 200
    assert b"docx html" in response.content
    assert calls["trigger"] == 0
