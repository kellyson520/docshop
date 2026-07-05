from __future__ import annotations

import io
import os
import zipfile
from urllib.parse import quote

from fastapi import HTTPException, status
from fastapi.responses import Response
from app.services.storage_path_policy import is_allowed_storage_path


def _sanitize_zip_segment(value: str | None, fallback: str) -> str:
    text = str(value or "").strip().replace("\\", "_").replace("/", "_")
    return text or fallback


def build_folder_bundle_response(
    *,
    folder_name: str,
    download_name: str,
    entries: list[tuple[str, str]],
) -> Response:
    folder_segment = _sanitize_zip_segment(folder_name, "folder")
    buffer = io.BytesIO()
    written = 0

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, storage_path in entries:
            if not filename or not storage_path:
                continue
            if not os.path.exists(storage_path):
                continue
            if not is_allowed_storage_path(storage_path):
                continue
            file_segment = _sanitize_zip_segment(os.path.basename(filename), "file")
            archive.write(os.path.realpath(storage_path), f"{folder_segment}/{file_segment}")
            written += 1

    if written == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder files not found",
        )

    payload = buffer.getvalue()
    safe_name = quote(_sanitize_zip_segment(download_name, "folder.zip"))
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )
