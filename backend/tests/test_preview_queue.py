import io
import json
from pathlib import Path
import tarfile
import uuid
import zipfile

from PIL import Image

from app.models.document_file import DocumentFile
from app.models.file_analysis_record import FileAnalysisRecord
from app.models.file_preview_asset import FilePreviewAsset
from app.models.file_version import FileVersion
from app.models.project import Project
from app.models.user import User


def test_enqueue_preview_generation_marks_file_queued_and_deduplicates(monkeypatch, tmp_path):
    from app.services import document_store
    from app.services import preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    preview_queue.reset_queue_for_tests()

    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4\n")

    first = preview_queue.enqueue_preview_generation(
        "file-1",
        str(source),
        "pdf",
        autostart=False,
    )
    second = preview_queue.enqueue_preview_generation(
        "file-1",
        str(source),
        "pdf",
        autostart=False,
    )

    meta = document_store._read_meta("file-1")
    assert first["status"] == "queued"
    assert first["deduplicated"] is False
    assert second["status"] == "queued"
    assert second["deduplicated"] is True
    assert preview_queue.get_queue_state()["queued"] == 1
    assert meta["preview"]["status"] == "queued"
    assert meta["preview"]["progress"] == 0
    assert meta["preview"]["source_hash"]


def test_preview_cache_cleanup_removes_generated_artifacts_but_keeps_original(monkeypatch, tmp_path):
    from app.services import document_store

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    file_id = "file-clean"
    original_dir = Path(document_store.dir_original(file_id))
    pdf_dir = Path(document_store.dir_pdf(file_id))
    images_dir = Path(document_store.dir_images(file_id))
    original_dir.mkdir(parents=True)
    pdf_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)

    original = original_dir / "original.pdf"
    pdf = pdf_dir / "document.pdf"
    image = images_dir / "page_0001.jpg"
    original.write_bytes(b"original")
    pdf.write_bytes(b"generated-pdf")
    image.write_bytes(b"generated-image")
    document_store.update_preview_meta(file_id, status="failed", error="boom", progress=33)

    result = document_store.clear_preview_cache(file_id)

    assert result["removed_bytes"] == len(b"generated-pdf") + len(b"generated-image")
    assert original.exists()
    assert not pdf.exists()
    assert not image.exists()
    assert document_store._read_meta(file_id)["preview"]["status"] == "missing"


def test_generate_images_reports_incremental_progress(monkeypatch, tmp_path):
    from app.services import document_store

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"fake pdf")

    def fake_render_page(args):
        i, _pdf_path, img_dir, _dpi, _quality = args
        out = Path(img_dir) / f"page_{i + 1:04d}.jpg"
        out.write_bytes(f"page-{i + 1}".encode())
        return str(out)

    progress = []
    monkeypatch.setattr(document_store, "_render_page", fake_render_page)

    paths = document_store.generate_images(
        "file-progress",
        str(pdf),
        page_count=3,
        pdf_hash="pdf-hash",
        max_workers=2,
        progress_callback=lambda rendered, total: progress.append((rendered, total)),
    )

    assert len(paths) == 3
    assert progress == [(1, 3), (2, 3), (3, 3)]


def test_worker_marks_missing_source_failed_and_continues_queue(monkeypatch, tmp_path):
    from app.services import document_store
    from app.services import preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    preview_queue.reset_queue_for_tests()

    missing = tmp_path / "missing.docx"
    pdf = tmp_path / "ok.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    calls = []

    def fake_run_job(job):
        calls.append(job.file_id)
        if not Path(job.storage_path).exists():
            raise FileNotFoundError(job.storage_path)
        document_store.update_preview_meta(job.file_id, status="ready", progress=100)

    monkeypatch.setattr(preview_queue, "_run_job", fake_run_job)

    preview_queue.enqueue_preview_generation("missing-file", str(missing), "docx", autostart=False)
    preview_queue.enqueue_preview_generation("ok-file", str(pdf), "pdf", autostart=False)

    preview_queue._worker_loop()

    missing_preview = document_store._read_meta("missing-file")["preview"]
    ok_preview = document_store._read_meta("ok-file")["preview"]

    assert calls == ["missing-file", "ok-file"]
    assert missing_preview["status"] == "failed"
    assert "missing.docx" in missing_preview["error"]
    assert ok_preview["status"] == "ready"
    assert preview_queue.get_queue_state() == {"queued": 0, "running": 0}


def test_preview_word_generation_uses_short_pdf_timeout(monkeypatch, tmp_path):
    from app.services import document_store
    from app.services import preview_queue
    from app.services import conversion_service

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    monkeypatch.setenv("PREVIEW_PDF_TIMEOUT_SECONDS", "7")
    preview_queue.reset_queue_for_tests()

    source = tmp_path / "sample.docx"
    source.write_bytes(b"fake docx")
    generated_pdf = tmp_path / "generated.pdf"
    generated_pdf.write_bytes(b"%PDF-1.4\n")

    seen = {}

    def fake_ensure_pdf(file_id, source_path, source_hash, *, timeout_seconds):
        seen["timeout_seconds"] = timeout_seconds
        return str(generated_pdf)

    class FakeDoc:
        def __len__(self):
            return 1

        def close(self):
            pass

    class FakeFitz:
        @staticmethod
        def open(_path):
            return FakeDoc()

    monkeypatch.setattr(conversion_service, "_ensure_pdf", fake_ensure_pdf)
    monkeypatch.setattr(conversion_service, "_source_hash", lambda path: f"hash:{Path(path).name}")
    monkeypatch.setitem(__import__("sys").modules, "fitz", FakeFitz)
    monkeypatch.setattr(document_store, "get_cached_images", lambda *args, **kwargs: ["page_0001.jpg"])

    preview_queue.enqueue_preview_generation("word-file", str(source), "docx", autostart=False)
    preview_queue._worker_loop()

    assert seen["timeout_seconds"] == 7
    assert document_store._read_meta("word-file")["preview"]["status"] == "ready"


def test_preview_snapshot_normalizes_unknown_status_and_reports_details(monkeypatch, tmp_path):
    from app.services import document_store
    from app.services import preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    preview_queue.reset_queue_for_tests()

    file_id = "file-unknown"
    pdf_dir = Path(document_store.dir_pdf(file_id))
    img_dir = Path(document_store.dir_images(file_id))
    pdf_dir.mkdir(parents=True)
    img_dir.mkdir(parents=True)
    (pdf_dir / "document.pdf").write_bytes(b"pdf-bytes")
    (img_dir / "page_0001.jpg").write_bytes(b"image-1")
    (img_dir / "page_0002.jpg").write_bytes(b"image-2")

    document_store.update_preview_meta(
        file_id,
        status="unknown",
        progress=37,
        stage=None,
        page_count=5,
        rendered_pages=2,
        source_hash="a" * 64,
        pdf_hash="b" * 64,
    )

    snapshot = preview_queue.get_preview_snapshot(file_id, "docx", filename="sample.docx", project_id="p1")

    assert snapshot["status"] == "missing"
    assert snapshot["status"] != "unknown"
    assert snapshot["stage"] == "预览状态未知，需重新生成"
    assert snapshot["rendered_pages"] == 2
    assert snapshot["page_count"] == 5
    assert snapshot["pdf_bytes"] == len(b"pdf-bytes")
    assert snapshot["image_bytes"] == len(b"image-1") + len(b"image-2")
    assert snapshot["storage_bytes"] == snapshot["pdf_bytes"] + snapshot["image_bytes"]
    assert snapshot["source_hash_short"] == "aaaaaaaa"
    assert snapshot["pdf_hash_short"] == "bbbbbbbb"


def _create_versioned_file(
    db,
    source_path: Path,
    *,
    filename: str,
    file_type: str,
    file_category: str,
    mime_type: str,
):
    user = User(
        username=f"preview-{uuid.uuid4().hex[:8]}",
        password_hash="test-hash",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    project = Project(name="preview pipeline", description="", owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)

    doc_file = DocumentFile(
        project_id=project.id,
        filename=filename,
        file_type=file_type,
        file_category=file_category,
        mime_type=mime_type,
        current_version=1,
        preview_status="pending",
        analysis_status="pending",
    )
    db.add(doc_file)
    db.commit()
    db.refresh(doc_file)

    version = FileVersion(
        file_id=doc_file.id,
        version=1,
        sort_order=1.0,
        storage_path=str(source_path),
        file_hash="a" * 64,
        file_size=source_path.stat().st_size,
        storage_mode="full",
        preview_status="pending",
        analysis_status="pending",
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return doc_file, version


def test_run_job_persists_office_preview_assets_and_analysis_state(monkeypatch, tmp_path, db):
    from app.services import conversion_service, document_store, preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    preview_queue.reset_queue_for_tests()

    source = tmp_path / "sample.docx"
    source.write_bytes(b"fake docx bytes")
    doc_file, version = _create_versioned_file(
        db,
        source,
        filename="sample.docx",
        file_type="docx",
        file_category="office",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    generated_pdf = tmp_path / "generated.pdf"
    generated_pdf.write_bytes(b"%PDF-1.4\n")

    def fake_ensure_pdf(file_id, source_path, source_hash, *, timeout_seconds):
        return document_store.store_pdf(file_id, str(generated_pdf), source_hash)

    def fake_generate_images(file_id, pdf_path, page_count, pdf_hash, **_kwargs):
        image_paths = []
        for page in range(1, page_count + 1):
            image_path = Path(document_store.dir_images(file_id)) / f"page_{page:04d}.jpg"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(f"page-{page}".encode())
            image_paths.append(str(image_path))
        return image_paths

    class FakeDoc:
        def __len__(self):
            return 2

        def close(self):
            pass

    class FakeFitz:
        @staticmethod
        def open(_path):
            return FakeDoc()

    monkeypatch.setattr(conversion_service, "_ensure_pdf", fake_ensure_pdf)
    monkeypatch.setattr(conversion_service, "_source_hash", lambda path: f"hash:{Path(path).name}")
    monkeypatch.setitem(__import__("sys").modules, "fitz", FakeFitz)
    monkeypatch.setattr(document_store, "get_cached_images", lambda *args, **kwargs: None)
    monkeypatch.setattr(document_store, "generate_images", fake_generate_images)

    preview_queue._run_job(
        preview_queue.PreviewJob(
            file_id=doc_file.id,
            storage_path=str(source),
            file_type="docx",
            force=False,
            project_id=doc_file.project_id,
            file_size=source.stat().st_size,
            updated_at=doc_file.updated_at,
        )
    )

    db.expire_all()
    refreshed_doc = db.query(DocumentFile).filter(DocumentFile.id == doc_file.id).first()
    refreshed_version = db.query(FileVersion).filter(FileVersion.id == version.id).first()
    assets = (
        db.query(FilePreviewAsset)
        .filter(FilePreviewAsset.version_id == version.id)
        .order_by(FilePreviewAsset.asset_type.asc(), FilePreviewAsset.page_number.asc())
        .all()
    )
    analysis = (
        db.query(FileAnalysisRecord)
        .filter(FileAnalysisRecord.version_id == version.id)
        .first()
    )

    assert refreshed_doc.preview_status == "ready"
    assert refreshed_doc.analysis_status == "ready"
    assert refreshed_doc.preview_error is None
    assert refreshed_version.preview_status == "ready"
    assert refreshed_version.analysis_status == "ready"
    assert refreshed_version.preview_error is None
    assert refreshed_version.analysis_error is None
    assert refreshed_version.preview_refresh_token
    assert [asset.asset_type for asset in assets].count("pdf") == 1
    assert [asset.asset_type for asset in assets].count("thumbnail") == 2
    assert [asset.asset_type for asset in assets].count("page_image") == 2
    assert analysis.analysis_type == "office_summary"
    assert json.loads(analysis.payload_json)["page_count"] == 2


def test_force_rebuild_replaces_old_derived_assets_and_bumps_refresh_token(monkeypatch, tmp_path, db):
    from app.services import document_store, preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    preview_queue.reset_queue_for_tests()

    source = tmp_path / "rebuild.pdf"
    source.write_bytes(b"%PDF-1.4\n")
    doc_file, version = _create_versioned_file(
        db,
        source,
        filename="rebuild.pdf",
        file_type="pdf",
        file_category="pdf",
        mime_type="application/pdf",
    )

    version.preview_refresh_token = "stale-token"
    version.derived_asset_version = 3
    db.add_all(
        [
            FilePreviewAsset(
                file_id=doc_file.id,
                version_id=version.id,
                asset_type="pdf",
                storage_path="C:/stale/old.pdf",
                sort_order=0,
                status="ready",
            ),
            FileAnalysisRecord(
                file_id=doc_file.id,
                version_id=version.id,
                analysis_type="office_summary",
                payload_json=json.dumps({"page_count": 99}),
                status="ready",
            ),
        ]
    )
    db.commit()

    pdf_dest = Path(document_store.dir_pdf(doc_file.id)) / "document.pdf"
    image_dest = Path(document_store.dir_images(doc_file.id)) / "page_0001.jpg"
    image_dest.parent.mkdir(parents=True, exist_ok=True)
    image_dest.write_bytes(b"fresh-image")

    class FakeDoc:
        def __len__(self):
            return 1

        def close(self):
            pass

    class FakeFitz:
        @staticmethod
        def open(_path):
            return FakeDoc()

    monkeypatch.setitem(__import__("sys").modules, "fitz", FakeFitz)
    monkeypatch.setattr(document_store, "get_cached_images", lambda *args, **kwargs: [str(image_dest)])

    preview_queue._run_job(
        preview_queue.PreviewJob(
            file_id=doc_file.id,
            storage_path=str(source),
            file_type="pdf",
            force=True,
            project_id=doc_file.project_id,
            file_size=source.stat().st_size,
            updated_at=doc_file.updated_at,
        )
    )

    db.expire_all()
    refreshed_version = db.query(FileVersion).filter(FileVersion.id == version.id).first()
    assets = db.query(FilePreviewAsset).filter(FilePreviewAsset.version_id == version.id).all()
    analysis = db.query(FileAnalysisRecord).filter(FileAnalysisRecord.version_id == version.id).all()

    assert refreshed_version.derived_asset_version == 4
    assert refreshed_version.preview_refresh_token
    assert refreshed_version.preview_refresh_token != "stale-token"
    assert all(asset.storage_path != "C:/stale/old.pdf" for asset in assets)
    assert len([asset for asset in assets if asset.asset_type == "pdf"]) == 1
    assert len(analysis) == 1
    assert json.loads(analysis[0].payload_json)["page_count"] == 1
    assert str(pdf_dest) in {asset.storage_path for asset in assets}


def test_archive_enqueue_and_worker_persist_manifest_analysis(monkeypatch, tmp_path, db):
    from app.services import document_store, preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    preview_queue.reset_queue_for_tests()

    source = tmp_path / "bundle.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("docs/readme.txt", "hello")
        archive.writestr("assets/logo.png", "png")

    doc_file, version = _create_versioned_file(
        db,
        source,
        filename="bundle.zip",
        file_type="zip",
        file_category="archive",
        mime_type="application/zip",
    )

    queued = preview_queue.enqueue_preview_generation(
        doc_file.id,
        str(source),
        "zip",
        autostart=False,
        project_id=doc_file.project_id,
        file_size=source.stat().st_size,
        updated_at=doc_file.updated_at,
    )
    preview_queue._worker_loop()

    db.expire_all()
    refreshed_doc = db.query(DocumentFile).filter(DocumentFile.id == doc_file.id).first()
    refreshed_version = db.query(FileVersion).filter(FileVersion.id == version.id).first()
    analysis = db.query(FileAnalysisRecord).filter(FileAnalysisRecord.version_id == version.id).first()

    assert queued["status"] == "queued"
    assert refreshed_doc.preview_status == "ready"
    assert refreshed_version.analysis_status == "ready"
    assert analysis.analysis_type == "archive_manifest"
    payload = json.loads(analysis.payload_json)
    assert payload["entry_count"] == 2
    assert payload["root_nodes"] == ["assets", "docs"]


def test_tar_gz_enqueue_uses_storage_filename_and_persists_manifest_analysis(monkeypatch, tmp_path, db):
    from app.services import document_store, preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    preview_queue.reset_queue_for_tests()

    source = tmp_path / "bundle.tar.gz"
    with tarfile.open(source, "w:gz") as archive:
        readme = b"hello"
        logo = b"png"

        readme_info = tarfile.TarInfo("docs/readme.txt")
        readme_info.size = len(readme)
        archive.addfile(readme_info, io.BytesIO(readme))

        logo_info = tarfile.TarInfo("assets/logo.png")
        logo_info.size = len(logo)
        archive.addfile(logo_info, io.BytesIO(logo))

    doc_file, version = _create_versioned_file(
        db,
        source,
        filename="bundle.tar.gz",
        file_type="gz",
        file_category="archive",
        mime_type="application/gzip",
    )

    queued = preview_queue.enqueue_preview_generation(
        doc_file.id,
        str(source),
        "gz",
        autostart=False,
        project_id=doc_file.project_id,
        file_size=source.stat().st_size,
        updated_at=doc_file.updated_at,
    )
    preview_queue._worker_loop()

    db.expire_all()
    refreshed_doc = db.query(DocumentFile).filter(DocumentFile.id == doc_file.id).first()
    refreshed_version = db.query(FileVersion).filter(FileVersion.id == version.id).first()
    analysis = db.query(FileAnalysisRecord).filter(FileAnalysisRecord.version_id == version.id).first()

    assert queued["status"] == "queued"
    assert refreshed_doc.preview_status == "ready"
    assert refreshed_version.analysis_status == "ready"
    assert analysis.analysis_type == "archive_manifest"
    payload = json.loads(analysis.payload_json)
    assert payload["entry_count"] == 2
    assert payload["root_nodes"] == ["assets", "docs"]


def test_video_enqueue_and_worker_persist_native_asset(monkeypatch, tmp_path, db):
    from app.services import document_store, preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    preview_queue.reset_queue_for_tests()

    source = tmp_path / "demo.mp4"
    source.write_bytes(b"fake mp4 bytes")
    poster = tmp_path / "poster.jpg"
    poster.write_bytes(b"poster")
    compatible = tmp_path / "preview-video.mp4"
    compatible.write_bytes(b"compatible-video")
    doc_file, version = _create_versioned_file(
        db,
        source,
        filename="demo.mp4",
        file_type="mp4",
        file_category="video",
        mime_type="video/mp4",
    )
    monkeypatch.setattr(
        preview_queue,
        "extract_video_poster_frame",
        lambda _source_path, _output_path: {"path": str(poster), "generated": True},
        raising=False,
    )
    monkeypatch.setattr(
        preview_queue,
        "extract_video_metadata",
        lambda _source_path: {
            "duration_seconds": 42.5,
            "dimensions": {"width": 1920, "height": 1080},
            "codec": "h264",
            "bit_rate": 512000,
            "format": "MP4",
            "color_mode": None,
            "has_alpha": None,
            "orientation": None,
            "aspect_ratio": "16:9",
        },
        raising=False,
    )
    monkeypatch.setattr(
        preview_queue,
        "generate_compatible_video_preview",
        lambda _source_path, _output_path: {"path": str(compatible), "generated": True},
        raising=False,
    )

    queued = preview_queue.enqueue_preview_generation(
        doc_file.id,
        str(source),
        "mp4",
        autostart=False,
        project_id=doc_file.project_id,
        file_size=source.stat().st_size,
        updated_at=doc_file.updated_at,
    )
    preview_queue._worker_loop()

    db.expire_all()
    refreshed_doc = db.query(DocumentFile).filter(DocumentFile.id == doc_file.id).first()
    refreshed_version = db.query(FileVersion).filter(FileVersion.id == version.id).first()
    assets = db.query(FilePreviewAsset).filter(FilePreviewAsset.version_id == version.id).all()
    analysis = db.query(FileAnalysisRecord).filter(FileAnalysisRecord.version_id == version.id).first()

    assert queued["status"] == "queued"
    assert refreshed_doc.preview_status == "ready"
    assert refreshed_version.preview_status == "ready"
    assert [asset.asset_type for asset in assets] == ["poster", "preview_video", "video"]
    assert assets[0].storage_path == str(poster)
    assert assets[1].storage_path == str(compatible)
    assert assets[1].width == 1920
    assert assets[1].height == 1080
    assert assets[2].storage_path == str(source)
    assert assets[2].width == 1920
    assert assets[2].height == 1080
    assert analysis.analysis_type == "media_metadata"
    payload = json.loads(analysis.payload_json)
    assert payload["duration_seconds"] == 42.5
    assert payload["dimensions"] == {"width": 1920, "height": 1080}
    assert payload["codec"] == "h264"
    assert payload["bit_rate"] == 512000


def test_image_enqueue_and_worker_persist_native_asset(monkeypatch, tmp_path, db):
    from app.services import document_store, preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    preview_queue.reset_queue_for_tests()
    bind = db.get_bind()
    for table in (
        User.__table__,
        Project.__table__,
        DocumentFile.__table__,
        FileVersion.__table__,
        FilePreviewAsset.__table__,
        FileAnalysisRecord.__table__,
    ):
        table.create(bind=bind, checkfirst=True)

    source = tmp_path / "diagram.png"
    Image.new("RGBA", (120, 80), (32, 112, 224, 180)).save(source, format="PNG")
    doc_file, version = _create_versioned_file(
        db,
        source,
        filename="diagram.png",
        file_type="png",
        file_category="image",
        mime_type="image/png",
    )

    queued = preview_queue.enqueue_preview_generation(
        doc_file.id,
        str(source),
        "png",
        autostart=False,
        project_id=doc_file.project_id,
        file_size=source.stat().st_size,
        updated_at=doc_file.updated_at,
    )
    preview_queue._worker_loop()

    db.expire_all()
    refreshed_doc = db.query(DocumentFile).filter(DocumentFile.id == doc_file.id).first()
    refreshed_version = db.query(FileVersion).filter(FileVersion.id == version.id).first()
    assets = db.query(FilePreviewAsset).filter(FilePreviewAsset.version_id == version.id).all()
    analysis = db.query(FileAnalysisRecord).filter(FileAnalysisRecord.version_id == version.id).first()

    assert queued["status"] == "queued"
    assert refreshed_doc.preview_status == "ready"
    assert refreshed_version.preview_status == "ready"
    assert refreshed_version.analysis_status == "ready"
    assert refreshed_version.preview_refresh_token
    assert len(assets) == 1
    assert assets[0].asset_type == "image"
    assert assets[0].storage_path == str(source)
    assert analysis.analysis_type == "media_metadata"
    payload = json.loads(analysis.payload_json)
    assert payload["format"] == "PNG"
    assert payload["dimensions"] == {"width": 120, "height": 80}
    assert payload["color_mode"] == "RGBA"
    assert payload["has_alpha"] is True
    assert payload["aspect_ratio"] == "3:2"
