from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[int] = Field(0, ge=0, le=1)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[int] = Field(None, ge=0, le=1)


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    share_token: str
    is_public: int
    file_count: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ProjectResponse]
