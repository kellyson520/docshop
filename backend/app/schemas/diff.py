from typing import Optional, List
from pydantic import BaseModel


class DiffResponse(BaseModel):
    id: str
    old_version: int
    new_version: int
    diff_type: str
    diff_data: str
    summary: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class DiffListResponse(BaseModel):
    diffs: List[DiffResponse]
