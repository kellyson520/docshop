from pathlib import Path

from app.models.document_file import DocumentFile
from app.models.file_version import FileVersion
from app.models.project import Project


def _create_file(db_session, project_id, tmp_path, filename="doc.pdf", file_type="pdf"):
    doc_path = tmp_path / filename
    doc_path.write_bytes(b"%PDF-1.4\n")
    doc = DocumentFile(
        project_id=project_id,
        filename=filename,
        file_type=file_type,
        current_version=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    version = FileVersion(
        file_id=doc.id,
        version=1,
        storage_path=str(doc_path),
        file_hash="hash",
        file_size=doc_path.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()
    return doc


def test_admin_preview_status_endpoint_returns_file_rows_and_summary(
    monkeypatch, tmp_path, client, auth_headers, db_session, test_user
):
    from app.services import document_store

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    project = Project(name="preview ops", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    ready_file = _create_file(db_session, project.id, tmp_path, "ready.pdf", "pdf")
    failed_file = _create_file(db_session, project.id, tmp_path, "failed.docx", "docx")

    document_store.update_preview_meta(
        ready_file.id,
        status="ready",
        progress=100,
        page_count=2,
        storage_bytes=4096,
    )
    document_store.update_preview_meta(
        failed_file.id,
        status="failed",
        progress=44,
        error="conversion exploded",
    )

    response = client.get(
        f"/api/v1/admin/files/previews?project_id={project.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["ready"] == 1
    assert data["summary"]["failed"] == 1
    assert data["summary"]["storage_bytes"] == 4096
    rows = {row["file_id"]: row for row in data["files"]}
    assert rows[ready_file.id]["status"] == "ready"
    assert rows[ready_file.id]["progress"] == 100
    assert rows[failed_file.id]["status"] == "failed"
    assert rows[failed_file.id]["error"] == "conversion exploded"


def test_admin_cleanup_endpoint_clears_matching_preview_caches(
    monkeypatch, tmp_path, client, auth_headers, db_session, test_user
):
    from app.services import document_store

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    project = Project(name="preview cleanup", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    failed_file = _create_file(db_session, project.id, tmp_path, "failed.pdf", "pdf")

    original_dir = Path(document_store.dir_original(failed_file.id))
    pdf_dir = Path(document_store.dir_pdf(failed_file.id))
    images_dir = Path(document_store.dir_images(failed_file.id))
    original_dir.mkdir(parents=True)
    pdf_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)
    original = original_dir / "original.pdf"
    pdf = pdf_dir / "document.pdf"
    image = images_dir / "page_0001.jpg"
    original.write_bytes(b"original")
    pdf.write_bytes(b"pdf")
    image.write_bytes(b"jpg")
    document_store.update_preview_meta(failed_file.id, status="failed", error="boom", progress=12)
    meta = document_store._read_meta(failed_file.id)
    meta["pdf_conversion_failed_hash"] = "stale-failed-hash"
    meta["pdf_conversion_failed_at"] = 123
    document_store._write_meta(failed_file.id, meta)

    response = client.post(
        "/api/v1/admin/files/preview-cache/cleanup",
        headers=auth_headers,
        json={"statuses": ["failed"]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["cleared"] == 1
    assert data["removed_bytes"] == 6
    assert original.exists()
    assert not pdf.exists()
    assert not image.exists()
    meta = document_store._read_meta(failed_file.id)
    assert meta["preview"]["status"] == "missing"
    assert "pdf_conversion_failed_hash" not in meta
    assert "pdf_conversion_failed_at" not in meta


def test_admin_preconvert_resolves_legacy_project_root_relative_storage_path(
    monkeypatch, tmp_path, client, auth_headers, db_session, test_user
):
    from app.services import preview_queue

    project = Project(name="legacy paths", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename="legacy.pdf",
        file_type="pdf",
        current_version=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    project_root = tmp_path
    backend_cwd = project_root / "backend"
    backend_cwd.mkdir()
    actual_file = project_root / "data" / "uploads" / project.id / doc.id / "v1_legacy.pdf"
    actual_file.parent.mkdir(parents=True)
    actual_file.write_bytes(b"%PDF-1.4\n")
    legacy_relative_path = str(Path("data") / "uploads" / project.id / doc.id / "v1_legacy.pdf")
    monkeypatch.chdir(backend_cwd)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        storage_path=legacy_relative_path,
        file_hash="hash",
        file_size=actual_file.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()

    calls = []

    def fake_enqueue(file_id, storage_path, file_type, *, force=False):
        calls.append((file_id, storage_path, file_type, force))
        return {"file_id": file_id, "status": "queued", "progress": 0}

    monkeypatch.setattr(preview_queue, "enqueue_preview_generation", fake_enqueue)

    response = client.post(
        "/api/v1/admin/files/preconvert",
        headers=auth_headers,
        json={"file_ids": [doc.id]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["queued"] == 1
    assert data["skipped"] == 0
    assert calls == [(doc.id, str(actual_file), "pdf", False)]


def test_admin_preconvert_skips_storage_path_outside_allowed_roots(
    monkeypatch, tmp_path, client, auth_headers, db_session, test_user
):
    from app.config import settings
    from app.services import document_store, preview_queue, storage_path_policy

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(storage_path_policy, "_is_testing_env", lambda: False)

    project = Project(name="blocked preconvert", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    outside_file = tmp_path / "outside" / "blocked.pdf"
    outside_file.parent.mkdir(parents=True, exist_ok=True)
    outside_file.write_bytes(b"%PDF-1.4\n")

    doc = DocumentFile(
        project_id=project.id,
        filename="blocked.pdf",
        file_type="pdf",
        current_version=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        storage_path=str(outside_file),
        file_hash="blocked-preconvert-hash",
        file_size=outside_file.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()

    calls = []

    def fake_enqueue(file_id, storage_path, file_type, *, force=False):
        calls.append((file_id, storage_path, file_type, force))
        return {"file_id": file_id, "status": "queued", "progress": 0}

    monkeypatch.setattr(preview_queue, "enqueue_preview_generation", fake_enqueue)

    response = client.post(
        "/api/v1/admin/files/preconvert",
        headers=auth_headers,
        json={"file_ids": [doc.id]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["queued"] == 0
    assert data["skipped"] == 1
    assert data["results"][0]["file_id"] == doc.id
    assert data["results"][0]["reason"] == "blocked_storage_root"
    assert calls == []



def test_admin_preview_summary_includes_queue_storage_breakdown_and_largest_files(
    monkeypatch, tmp_path, client, auth_headers, db_session, test_user
):
    from app.services import document_store, preview_queue

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))
    project = Project(name="preview summary", description="", owner_id=test_user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    pdf_file = _create_file(db_session, project.id, tmp_path, "big.pdf", "pdf")
    docx_file = _create_file(db_session, project.id, tmp_path, "queued.docx", "docx")

    pdf_dir = Path(document_store.dir_pdf(pdf_file.id))
    images_dir = Path(document_store.dir_images(pdf_file.id))
    pdf_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)
    (pdf_dir / "document.pdf").write_bytes(b"p" * 17)
    (images_dir / "page_0001.jpg").write_bytes(b"i" * 23)
    document_store.update_preview_meta(pdf_file.id, status="ready", progress=100)
    document_store.update_preview_meta(docx_file.id, status="queued", progress=0)
    monkeypatch.setattr(preview_queue, "get_queue_state", lambda: {"queued": 1, "running": 0})

    response = client.get(
        f"/api/v1/admin/files/previews?project_id={project.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    summary = response.json()["data"]["summary"]
    assert summary["queue_state"] == {"queued": 1, "running": 0}
    assert summary["storage_breakdown"]["pdf_bytes"] == 17
    assert summary["storage_breakdown"]["image_bytes"] == 23
    assert summary["by_file_type"]["pdf"] == 1
    assert summary["by_file_type"]["docx"] == 1
    assert summary["largest_files"][0]["file_id"] == pdf_file.id
    assert summary["largest_files"][0]["storage_bytes"] == 40
