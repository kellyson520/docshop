
from datetime import datetime, timedelta
import io
from pathlib import Path
import zipfile

from app.deps.auth import get_password_hash
from app.deps.auth import verify_password
from app.models.document_file import DocumentFile
from app.models.file_analysis_record import FileAnalysisRecord
from app.models.file_preview_asset import FilePreviewAsset
from app.models.file_version import FileVersion
from app.models.project import Project
from app.models.project_folder import ProjectFolder
from app.models.share_token import ShareToken
from app.models.user import User
from app.config import settings


def _make_user(db, username='owner', role='user'):
    u = User(username=username, password_hash=get_password_hash('test123'), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client, username):
    res = client.post('/api/v1/auth/login', json={'username': username, 'password': 'test123'})
    assert res.status_code == 200
    return {'Authorization': f"Bearer {res.json()['data']['access_token']}"}


def _make_project_file_version(db, owner):
    p = Project(name='Private Project', description='private', owner_id=owner.id, is_public=0, share_token='legacy-private-token')
    db.add(p)
    db.commit()
    db.refresh(p)
    f = DocumentFile(project_id=p.id, filename='secret.docx', display_name='Secret', file_type='docx', current_version=1)
    db.add(f)
    db.commit()
    db.refresh(f)
    v = FileVersion(file_id=f.id, version=1, sort_order=1, storage_path='C:/tmp/secret.docx', file_hash='abc', file_size=12)
    db.add(v)
    db.commit()
    db.refresh(v)
    return p, f, v


def test_user_can_create_file_share_token_for_owned_private_file(client, db_session):
    owner = _make_user(db_session, 'share-owner', 'user')
    _, doc, _ = _make_project_file_version(db_session, owner)
    headers = _login(client, 'share-owner')

    response = client.post('/api/v1/share-tokens', headers=headers, json={
        'name': 'private file link',
        'resource_type': 'file',
        'resource_id': doc.id,
        'max_views': 2,
        'max_downloads': 1,
        'allow_download': 1,
    })

    assert response.status_code == 200
    data = response.json()['data']
    assert data['token']
    assert data['resource_type'] == 'file'
    assert data['resource_id'] == doc.id
    assert data['max_views'] == 2
    assert data['max_downloads'] == 1


def test_create_share_token_default_name_is_readable(client, db_session):
    owner = _make_user(db_session, 'share-owner-default-name', 'user')
    _, doc, _ = _make_project_file_version(db_session, owner)
    headers = _login(client, 'share-owner-default-name')

    response = client.post('/api/v1/share-tokens', headers=headers, json={
        'resource_type': 'file',
        'resource_id': doc.id,
    })

    assert response.status_code == 200
    name = response.json()['data']['name']
    assert name == '分享链接'
    assert '??' not in name


def test_user_cannot_share_other_users_file(client, db_session):
    owner = _make_user(db_session, 'share-owner-2', 'user')
    other = _make_user(db_session, 'share-other', 'user')
    _, doc, _ = _make_project_file_version(db_session, other)
    headers = _login(client, 'share-owner-2')

    response = client.post('/api/v1/share-tokens', headers=headers, json={
        'name': 'bad link',
        'resource_type': 'file',
        'resource_id': doc.id,
    })

    assert response.status_code == 403


def test_share_token_view_limit_is_consumed_only_on_root_entry(client, db_session):
    owner = _make_user(db_session, 'share-owner-3', 'user')
    _, doc, _ = _make_project_file_version(db_session, owner)
    st = ShareToken(token='limited-root-share', name='limited', resource_type='file', resource_id=doc.id, max_views=1, created_by=owner.id)
    db_session.add(st)
    db_session.commit()

    first = client.get('/api/v1/share/limited-root-share')
    second = client.get('/api/v1/share/limited-root-share')

    assert first.status_code == 200
    assert first.json()['data']['share']['view_count'] == 1
    assert second.status_code == 403


def test_download_disabled_share_token_blocks_download(client, db_session, monkeypatch):
    owner = _make_user(db_session, 'share-owner-4', 'user')
    _, doc, ver = _make_project_file_version(db_session, owner)
    st = ShareToken(token='no-download-share', name='no download', resource_type='file', resource_id=doc.id, allow_download=0, created_by=owner.id)
    db_session.add(st)
    db_session.commit()

    response = client.get(f'/api/v1/share/no-download-share/files/{doc.id}/versions/{ver.id}/download')

    assert response.status_code == 403
    payload = response.json()
    assert 'download disabled' in payload.get('message', '') or 'download disabled' in payload.get('detail', '')


def test_share_project_folder_bundle_downloads_zip_when_allowed(client, db_session, tmp_path, monkeypatch):
    owner = _make_user(db_session, 'share-owner-folder-zip', 'user')
    project = Project(
        name='Folder Share Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-folder-share',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    folder = ProjectFolder(project_id=project.id, name='Contracts')
    db_session.add(folder)
    db_session.commit()
    db_session.refresh(folder)

    upload_root = tmp_path / 'uploads'
    upload_root.mkdir()
    monkeypatch.setattr(settings, 'UPLOAD_DIR', str(upload_root))

    stored_file = upload_root / 'nda.pdf'
    stored_file.write_bytes(b'shared folder pdf')

    doc = DocumentFile(
        project_id=project.id,
        filename='nda.pdf',
        display_name='NDA.pdf',
        file_type='pdf',
        current_version=1,
        folder_id=folder.id,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path=str(stored_file),
        file_hash='folder-share-pdf',
        file_size=stored_file.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    token = ShareToken(
        token='project-folder-download-share',
        name='folder share',
        resource_type='project',
        resource_id=project.id,
        allow_download=1,
        created_by=owner.id,
    )
    db_session.add(token)
    db_session.commit()

    response = client.get(f'/api/v1/share/{token.token}/folders/{folder.id}/download')

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/zip')

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert archive.namelist() == ['Contracts/nda.pdf']
    assert archive.read('Contracts/nda.pdf') == b'shared folder pdf'


def test_share_project_folder_bundle_allows_document_store_root(client, db_session, tmp_path, monkeypatch):
    from app.services import document_store
    from app.services import storage_path_policy

    owner = _make_user(db_session, 'share-owner-folder-docstore', 'user')
    project = Project(
        name='Folder Share DocStore Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-folder-docstore-share',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    folder = ProjectFolder(project_id=project.id, name='Archives')
    db_session.add(folder)
    db_session.commit()
    db_session.refresh(folder)

    documents_root = tmp_path / 'documents'
    monkeypatch.setattr(document_store, 'ROOT', str(documents_root))
    monkeypatch.setattr(storage_path_policy, '_is_testing_env', lambda: False)

    stored_file = documents_root / 'bundle-file' / 'original' / 'archive.pdf'
    stored_file.parent.mkdir(parents=True, exist_ok=True)
    stored_file.write_bytes(b'shared folder doc-store pdf')

    doc = DocumentFile(
        project_id=project.id,
        filename='archive.pdf',
        display_name='Archive.pdf',
        file_type='pdf',
        current_version=1,
        folder_id=folder.id,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path=str(stored_file),
        file_hash='folder-docstore-pdf',
        file_size=stored_file.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    token = ShareToken(
        token='project-folder-download-docstore-share',
        name='folder docstore share',
        resource_type='project',
        resource_id=project.id,
        allow_download=1,
        created_by=owner.id,
    )
    db_session.add(token)
    db_session.commit()

    response = client.get(f'/api/v1/share/{token.token}/folders/{folder.id}/download')

    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert archive.namelist() == ['Archives/archive.pdf']
    assert archive.read('Archives/archive.pdf') == b'shared folder doc-store pdf'


def test_shared_file_detail_includes_preview_manifest_and_analysis_summary(client, db_session):
    owner = _make_user(db_session, 'share-owner-rich-file', 'user')
    project = Project(
        name='Archive Share Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-archive-token',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename='bundle.zip',
        display_name='Bundle',
        file_type='zip',
        file_category='archive',
        mime_type='application/zip',
        current_version=1,
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path='C:/tmp/bundle.zip',
        file_hash='def',
        file_size=128,
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    db_session.add(
        FileAnalysisRecord(
            file_id=doc.id,
            version_id=version.id,
            analysis_type='archive_manifest',
            payload_json='{"entry_count": 2, "root_nodes": ["docs"]}',
            status='ready',
        )
    )
    db_session.commit()

    share_token = ShareToken(
        token='rich-preview-share',
        name='rich preview share',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}')

    assert response.status_code == 200
    data = response.json()['data']
    assert data['preview_manifest']['type'] == 'archive_structure'
    assert data['analysis_summary']['entry_count'] == 2
    assert data['analysis_summary']['root_nodes'] == ['docs']
    assert data['download_formats'] == ['zip']
    assert data['original_download_format'] == 'zip'
    assert data['has_alternate_downloads'] is False


def test_shared_file_detail_exposes_download_formats_for_docx(client, db_session):
    owner = _make_user(db_session, 'share-owner-docx-formats', 'user')
    project, doc, version = _make_project_file_version(db_session, owner)
    project.share_token = 'legacy-docx-formats-token'
    db_session.add(project)
    db_session.commit()

    share_token = ShareToken(
        token='docx-formats-share',
        name='docx formats share',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    detail_response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}')
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()['data']
    assert detail_payload['download_formats'] == ['docx', 'pdf']
    assert detail_payload['original_download_format'] == 'docx'
    assert detail_payload['has_alternate_downloads'] is True

    versions_response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/versions')
    assert versions_response.status_code == 200
    versions_payload = versions_response.json()['data']['versions']
    assert versions_payload[0]['download_formats'] == ['docx', 'pdf']
    assert versions_payload[0]['original_download_format'] == 'docx'
    assert versions_payload[0]['has_alternate_downloads'] is True


def test_shared_project_list_exposes_top_level_and_latest_version_download_formats(client, db_session):
    owner = _make_user(db_session, 'share-owner-project-formats', 'user')
    project, doc, version = _make_project_file_version(db_session, owner)
    project.share_token = 'legacy-project-formats-token'
    db_session.add(project)
    db_session.commit()

    share_token = ShareToken(
        token='project-formats-share',
        name='project formats share',
        resource_type='project',
        resource_id=project.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    response = client.get(f'/api/v1/share/{share_token.token}')

    assert response.status_code == 200
    files_payload = response.json()['data']['files']
    assert len(files_payload) == 1
    assert files_payload[0]['download_formats'] == ['docx', 'pdf']
    assert files_payload[0]['original_download_format'] == 'docx'
    assert files_payload[0]['has_alternate_downloads'] is True
    assert files_payload[0]['versions'][0]['download_formats'] == ['docx', 'pdf']
    assert files_payload[0]['versions'][0]['original_download_format'] == 'docx'
    assert files_payload[0]['versions'][0]['has_alternate_downloads'] is True


def test_shared_preview_asset_streams_poster_image(client, db_session, tmp_path, monkeypatch):
    from app.services import document_store

    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))

    owner = _make_user(db_session, 'share-owner-video-poster', 'user')
    project = Project(
        name='Video Share Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-video-poster-token',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename='demo.mp4',
        display_name='Demo Video',
        file_type='mp4',
        file_category='video',
        mime_type='video/mp4',
        current_version=1,
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path='C:/tmp/demo.mp4',
        file_hash='poster-share',
        file_size=1024,
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    poster_path = Path(document_store.dir_images(doc.id)) / 'video-poster.jpg'
    poster_path.parent.mkdir(parents=True, exist_ok=True)
    poster_path.write_bytes(b'shared-poster')

    asset = FilePreviewAsset(
        file_id=doc.id,
        version_id=version.id,
        asset_type='poster',
        storage_path=str(poster_path),
        sort_order=0,
        status='ready',
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    share_token = ShareToken(
        token='video-poster-share',
        name='video poster share',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/preview-assets/{asset.id}')

    assert response.status_code == 200
    assert response.content == b'shared-poster'
    assert response.headers['content-type'].startswith('image/jpeg')


def test_shared_version_download_allows_document_store_root(client, db_session, tmp_path, monkeypatch):
    from app.services import document_store
    from app.services import storage_path_policy

    owner = _make_user(db_session, 'share-owner-docstore-download', 'user')
    project = Project(
        name='Share DocStore Download Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-docstore-download-token',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename='shared-docstore.pdf',
        display_name='Shared DocStore PDF',
        file_type='pdf',
        current_version=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    documents_root = tmp_path / 'documents'
    monkeypatch.setattr(document_store, 'ROOT', str(documents_root))
    monkeypatch.setattr(storage_path_policy, '_is_testing_env', lambda: False)
    stored_file = documents_root / doc.id / 'original' / 'shared-docstore.pdf'
    stored_file.parent.mkdir(parents=True, exist_ok=True)
    stored_file.write_bytes(b'shared-docstore-download')

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path=str(stored_file),
        file_hash='shared-docstore-download',
        file_size=stored_file.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    share_token = ShareToken(
        token='shared-docstore-download-token',
        name='shared docstore download',
        resource_type='file',
        resource_id=doc.id,
        allow_download=1,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/versions/{version.id}/download')

    assert response.status_code == 200
    assert response.content == b'shared-docstore-download'


def test_shared_page_image_allows_document_store_root(client, db_session, tmp_path, monkeypatch):
    from app.services import document_store
    from app.services import storage_path_policy

    documents_root = tmp_path / 'documents'
    monkeypatch.setattr(document_store, 'ROOT', str(documents_root))
    monkeypatch.setattr(storage_path_policy, '_is_testing_env', lambda: False)

    owner = _make_user(db_session, 'share-owner-docstore-pages', 'user')
    project = Project(
        name='Share DocStore Pages Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-docstore-pages-token',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename='paged.pdf',
        display_name='Paged PDF',
        file_type='pdf',
        current_version=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    stored_file = documents_root / doc.id / 'original' / 'paged.pdf'
    stored_file.parent.mkdir(parents=True, exist_ok=True)
    stored_file.write_bytes(b'%PDF-1.4 fake shared pdf')

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path=str(stored_file),
        file_hash='shared-docstore-pages',
        file_size=stored_file.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    share_token = ShareToken(
        token='shared-docstore-pages-token',
        name='shared docstore pages',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    class FakeDoc:
        def __len__(self):
            return 3

        def close(self):
            pass

    def fake_render_single_page(file_id, pdf_path, page_num, page_count, pdf_hash, quality=75):
        out = Path(document_store.dir_page_images(file_id, pdf_hash)) / f'page_{page_num:04d}.jpg'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b'shared-page-image')
        return str(out)

    monkeypatch.setattr('fitz.open', lambda path: FakeDoc())
    monkeypatch.setattr('app.services.document_store.render_single_page', fake_render_single_page)
    monkeypatch.setattr('app.services.conversion_service._source_hash', lambda path: 'shared-docstore-pages-hash')

    response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/pages/2')

    assert response.status_code == 200
    assert response.content == b'shared-page-image'
    assert response.headers['content-type'].startswith('image/jpeg')


def test_shared_pdf_preview_rejects_storage_path_outside_allowed_roots(client, db_session, tmp_path, monkeypatch):
    from app.config import settings
    from app.services import document_store
    from app.services import storage_path_policy

    documents_root = tmp_path / 'documents'
    upload_root = tmp_path / 'uploads'
    monkeypatch.setattr(document_store, 'ROOT', str(documents_root))
    monkeypatch.setattr(settings, 'UPLOAD_DIR', str(upload_root))
    monkeypatch.setattr(storage_path_policy, '_is_testing_env', lambda: False)

    owner = _make_user(db_session, 'share-owner-outside-pdf-preview', 'user')
    project = Project(
        name='Share Outside PDF Preview Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-outside-pdf-preview-token',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename='outside-preview.pdf',
        display_name='Outside Preview PDF',
        file_type='pdf',
        current_version=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    outside_pdf = tmp_path / 'outside' / 'outside-preview.pdf'
    outside_pdf.parent.mkdir(parents=True, exist_ok=True)
    outside_pdf.write_bytes(b'%PDF-1.4 blocked shared preview')

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path=str(outside_pdf),
        file_hash='outside-shared-preview',
        file_size=outside_pdf.stat().st_size,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    share_token = ShareToken(
        token='outside-pdf-preview-share',
        name='outside pdf preview share',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/preview/pdf')

    assert response.status_code == 404
    assert response.json()['detail'] == 'File not found'

def test_shared_preview_streams_mp4_inline_for_video_files(client, db_session, tmp_path, monkeypatch):
    from app.config import settings

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    video_path = upload_dir / "shared-demo.mp4"
    video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 32
    video_path.write_bytes(video_bytes)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    owner = _make_user(db_session, 'share-owner-inline-video', 'user')
    project = Project(
        name='Shared Inline Video Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-inline-video-token',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename='shared-demo.mp4',
        display_name='Shared Demo Video',
        file_type='mp4',
        file_category='video',
        mime_type='video/mp4',
        current_version=1,
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path=str(video_path),
        file_hash='shared-inline-video',
        file_size=len(video_bytes),
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(version)
    db_session.commit()

    share_token = ShareToken(
        token='inline-video-share',
        name='inline video share',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/preview')

    assert response.status_code == 200
    assert response.content == video_bytes
    assert response.headers['content-type'].startswith('video/mp4')
    assert 'inline;' in response.headers['content-disposition']


def test_shared_preview_prefers_compatible_preview_video_asset(client, db_session, tmp_path, monkeypatch):
    from app.services import document_store

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    video_path = upload_dir / "shared-compatible-demo.mp4"
    video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 32
    video_path.write_bytes(video_bytes)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(document_store, "ROOT", str(tmp_path / "documents"))

    compatible_path = Path(document_store.dir_original("share-compatible-video")) / "preview-video.mp4"
    compatible_path.parent.mkdir(parents=True, exist_ok=True)
    compatible_bytes = b"compatible-video"
    compatible_path.write_bytes(compatible_bytes)

    owner = _make_user(db_session, 'share-owner-compatible-video', 'user')
    project = Project(
        name='Shared Compatible Video Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-compatible-video-token',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename='shared-compatible-demo.mp4',
        display_name='Shared Compatible Demo Video',
        file_type='mp4',
        file_category='video',
        mime_type='video/mp4',
        current_version=1,
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path=str(video_path),
        file_hash='shared-compatible-video',
        file_size=len(video_bytes),
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    db_session.add(
        FilePreviewAsset(
            file_id=doc.id,
            version_id=version.id,
            asset_type='preview_video',
            storage_path=str(compatible_path),
            sort_order=1,
            status='ready',
        )
    )
    db_session.commit()

    share_token = ShareToken(
        token='compatible-video-share',
        name='compatible video share',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/preview')

    assert response.status_code == 200
    assert response.content == compatible_bytes
    assert response.headers['content-type'].startswith('video/mp4')


def test_shared_preview_streams_png_inline_for_image_files(client, db_session, tmp_path, monkeypatch):
    from app.config import settings

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = upload_dir / "shared-poster.png"
    image_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
        b"\xe2!\xbc3"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    image_path.write_bytes(image_bytes)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    owner = _make_user(db_session, 'share-owner-inline-image', 'user')
    project = Project(
        name='Shared Inline Image Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-inline-image-token',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename='shared-poster.png',
        display_name='Shared Poster',
        file_type='png',
        file_category='image',
        mime_type='image/png',
        current_version=1,
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path=str(image_path),
        file_hash='shared-inline-image',
        file_size=len(image_bytes),
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(version)
    db_session.commit()

    share_token = ShareToken(
        token='inline-image-share',
        name='inline image share',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/preview')

    assert response.status_code == 200
    assert response.content == image_bytes
    assert response.headers['content-type'].startswith('image/png')
    assert 'inline;' in response.headers['content-disposition']


def test_shared_preview_streams_direct_html_document_for_html_files(client, db_session, tmp_path, monkeypatch):
    from app.config import settings

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    html_path = upload_dir / "shared-report.html"
    css_path = upload_dir / "styles.css"
    css_content = "body { background: rgb(250, 250, 250); }"
    css_path.write_text(css_content, encoding="utf-8")
    html_content = (
        '<!DOCTYPE html><html><head><link rel="stylesheet" href="styles.css"></head>'
        '<body><h1>Shared HTML Preview</h1></body></html>'
    )
    html_path.write_text(html_content, encoding="utf-8")
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    owner = _make_user(db_session, 'share-owner-inline-html', 'user')
    project = Project(
        name='Shared Inline HTML Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-inline-html-token',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename='shared-report.html',
        display_name='Shared HTML Report',
        file_type='html',
        file_category='binary',
        mime_type='text/html',
        current_version=1,
        preview_status='not_supported',
        analysis_status='pending',
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path=str(html_path),
        file_hash='shared-inline-html',
        file_size=len(html_content.encode("utf-8")),
        preview_status='not_supported',
        analysis_status='pending',
    )
    db_session.add(version)
    db_session.commit()

    share_token = ShareToken(
        token='inline-html-share',
        name='inline html share',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    detail_response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}')
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()['data']
    assert detail_payload['file_category'] == 'html'
    assert detail_payload['preview_status'] == 'ready'
    assert detail_payload['preview_manifest']['type'] == 'html_runtime'
    assert detail_payload['preview_manifest']['primary_asset']['url'].endswith('/preview?version=1')

    response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/preview')

    assert response.status_code == 200
    assert f'href="/api/v1/share/{share_token.token}/files/{doc.id}/html-assets/styles.css?version=1"' in response.text
    assert '<h1>Shared HTML Preview</h1>' in response.text
    assert 'location.replace(' not in response.text
    assert response.headers['content-type'].startswith('text/html')

    asset_response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/html-assets/styles.css?version=1')

    assert asset_response.status_code == 200
    assert asset_response.text == css_content
    assert asset_response.headers['content-type'].startswith('text/css')


def test_shared_preview_redacts_internal_conversion_error(client, db_session, tmp_path, monkeypatch):
    from unittest.mock import patch

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    docx_path = upload_dir / "shared-preview.docx"
    docx_path.write_bytes(b"fake docx bytes")
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))

    owner = _make_user(db_session, 'share-owner-preview-redaction', 'user')
    project = Project(
        name='Shared Preview Redaction Project',
        description='private',
        owner_id=owner.id,
        is_public=0,
        share_token='legacy-shared-preview-redaction',
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    doc = DocumentFile(
        project_id=project.id,
        filename='shared-preview.docx',
        file_type='docx',
        current_version=1,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    version = FileVersion(
        file_id=doc.id,
        version=1,
        sort_order=1,
        storage_path=str(docx_path),
        file_hash='shared-preview-redaction',
        file_size=docx_path.stat().st_size,
        preview_status='ready',
        analysis_status='ready',
    )
    db_session.add(version)
    db_session.commit()

    share_token = ShareToken(
        token='shared-preview-redaction-token',
        name='shared preview redaction',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
    )
    db_session.add(share_token)
    db_session.commit()

    with patch("app.services.conversion_service.trigger_preconversion"), patch(
        "app.services.conversion_service.convert_to_html",
        side_effect=RuntimeError("secret path C:/sensitive/shared-preview.docx"),
    ):
        response = client.get(f'/api/v1/share/{share_token.token}/files/{doc.id}/preview')

    assert response.status_code == 500
    assert response.json()["detail"] == "Preview failed"
    assert "secret path" not in response.text


def test_admin_can_manage_policy(client, db_session, test_user, auth_headers):
    get_response = client.get('/api/v1/share-tokens/policy', headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()['data']['allowed_resource_types'] == ['project', 'file', 'version']

    put_response = client.put('/api/v1/share-tokens/policy', headers=auth_headers, json={
        'allow_user_creation': False,
        'default_max_views': 5,
        'allowed_resource_types': ['project', 'file'],
    })

    assert put_response.status_code == 200
    data = put_response.json()['data']
    assert data['allow_user_creation'] is False
    assert data['default_max_views'] == 5
    assert data['allowed_resource_types'] == ['project', 'file']


def test_create_share_token_persists_phase1_access_fields(client, db_session):
    owner = _make_user(db_session, 'share-owner-phase1', 'user')
    _, doc, _ = _make_project_file_version(db_session, owner)
    headers = _login(client, 'share-owner-phase1')

    response = client.post('/api/v1/share-tokens', headers=headers, json={
        'name': 'phase1 gated link',
        'resource_type': 'file',
        'resource_id': doc.id,
        'require_login': True,
        'password': 'OpenSesame!1',
        'password_hint': 'common phrase',
        'allow_preview': False,
        'allow_diff': False,
        'allow_versions': False,
        'policy_mode': 'inherit_resource_policy',
    })

    assert response.status_code == 200
    data = response.json()['data']
    assert data['require_login'] is True
    assert data['password_hint'] == 'common phrase'
    assert data['allow_preview'] is False
    assert data['allow_diff'] is False
    assert data['allow_versions'] is False
    assert data['policy_mode'] == 'override_with_token_policy'

    saved = db_session.query(ShareToken).filter(ShareToken.id == data['id']).first()
    assert saved is not None
    assert saved.require_login == 1
    assert saved.password_hash
    assert verify_password('OpenSesame!1', saved.password_hash) is True
    assert saved.policy_mode == 'override_with_token_policy'


def test_update_share_token_can_clear_password_policy(client, db_session):
    owner = _make_user(db_session, 'share-owner-phase1-update', 'user')
    _, doc, _ = _make_project_file_version(db_session, owner)
    headers = _login(client, 'share-owner-phase1-update')

    token = ShareToken(
        token='phase1-update-share',
        name='phase1 update',
        resource_type='file',
        resource_id=doc.id,
        created_by=owner.id,
        require_login=1,
        password_hash=get_password_hash('OpenSesame!1'),
        password_hint='old hint',
        allow_preview=0,
        allow_diff=0,
        allow_versions=0,
        policy_mode='override_with_token_policy',
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)

    response = client.put(f'/api/v1/share-tokens/{token.id}', headers=headers, json={
        'require_login': False,
        'password': '',
        'password_hint': '',
        'allow_preview': True,
        'allow_diff': True,
        'allow_versions': True,
        'policy_mode': 'inherit_resource_policy',
    })

    assert response.status_code == 200
    data = response.json()['data']
    assert data['require_login'] is False
    assert data['password_hint'] is None
    assert data['allow_preview'] is True
    assert data['allow_diff'] is True
    assert data['allow_versions'] is True
    assert data['policy_mode'] == 'override_with_token_policy'

    db_session.refresh(token)
    assert token.require_login == 0
    assert token.password_hash is None
    assert token.password_hint is None
    assert token.policy_mode == 'override_with_token_policy'
