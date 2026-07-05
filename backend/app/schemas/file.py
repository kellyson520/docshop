from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class FileCapabilityResponse(BaseModel):
    can_preview: bool = False
    can_play: bool = False
    can_diff_visual: bool = False
    can_diff_structural: bool = False
    can_download: bool = True
    can_extract_metadata: bool = True
    can_generate_thumbnail: bool = False


class FileResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_type: str
    file_category: str = "binary"
    mime_type: Optional[str] = None
    current_version: int
    created_at: str
    preview_status: str = "pending"
    analysis_status: str = "pending"
    capabilities: FileCapabilityResponse = Field(default_factory=FileCapabilityResponse)
    preview_manifest: Optional[dict] = None
    analysis_summary: Optional[dict] = None
    download_formats: Optional[List[str]] = None
    original_download_format: Optional[str] = None
    has_alternate_downloads: Optional[bool] = None
    preview_error: Optional[str] = None
    analysis_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VersionResponse(BaseModel):
    id: str
    version: int
    file_size: int
    changelog: Optional[str]
    has_diff: bool
    storage_mode: str = "full"
    created_at: str
    preview_status: Optional[str] = "pending"
    analysis_status: Optional[str] = "pending"
    preview_error: Optional[str] = None
    analysis_error: Optional[str] = None
    preview_manifest: Optional[dict] = None
    analysis_summary: Optional[dict] = None
    download_formats: Optional[List[str]] = None
    original_download_format: Optional[str] = None
    has_alternate_downloads: Optional[bool] = None
    preview_refresh_token: Optional[str] = None
    derived_asset_version: int = 1

    model_config = ConfigDict(from_attributes=True)


class VersionListResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str = ""
    current_version: int
    versions: List[VersionResponse]
