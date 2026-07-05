from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class DiffResponse(BaseModel):
    id: str
    old_version_id: Optional[str] = None
    new_version_id: Optional[str] = None
    old_version: int
    new_version: int
    diff_type: str
    diff_data: str
    summary: Optional[str]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class DiffListResponse(BaseModel):
    diffs: List[DiffResponse]
