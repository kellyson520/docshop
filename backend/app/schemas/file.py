from typing import Optional, List
from pydantic import BaseModel


class FileResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_type: str
    current_version: int
    created_at: str

    class Config:
        from_attributes = True


class VersionResponse(BaseModel):
    id: str
    version: int
    file_size: int
    changelog: Optional[str]
    has_diff: bool
    storage_mode: str = "full"
    created_at: str

    class Config:
        from_attributes = True


class VersionListResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str = ""
    current_version: int
    versions: List[VersionResponse]
