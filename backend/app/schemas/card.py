"""
卡片式文档管理 Schema 模块

提供卡片相关的数据模型定义，包括卡片列表、卡片详情、版本信息等。
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class CardListItem(BaseModel):
    """卡片列表项
    
    用于展示卡片列表的基本信息，包含文件的核心元数据。
    """
    id: str = Field(..., description="卡片ID（即文件ID）")
    display_name: str = Field(..., description="显示名称")
    cover_image: Optional[str] = Field(None, description="封面图片路径")
    version_count: int = Field(..., description="版本数量")
    updated_at: str = Field(..., description="最后更新时间")
    description: Optional[str] = Field(None, description="文件介绍")
    file_type: str = Field(..., description="文件类型（pdf/docx/xlsx）")
    
    class Config:
        from_attributes = True


class CardVersionItem(BaseModel):
    """卡片版本项
    
    用于展示卡片下的单个版本信息。
    """
    id: str = Field(..., description="版本ID")
    version: int = Field(..., description="版本号")
    created_at: str = Field(..., description="版本创建时间")
    changelog: Optional[str] = Field(None, description="版本变更说明")
    file_size: int = Field(..., description="文件大小（字节）")
    
    class Config:
        from_attributes = True


class CardDetail(BaseModel):
    """卡片详情
    
    包含卡片的完整信息，包括文件元数据和所有版本列表。
    """
    id: str = Field(..., description="卡片ID")
    display_name: str = Field(..., description="显示名称")
    filename: str = Field(..., description="原始文件名")
    cover_image: Optional[str] = Field(None, description="封面图片路径")
    description: Optional[str] = Field(None, description="文件介绍")
    file_type: str = Field(..., description="文件类型")
    project_id: str = Field(..., description="所属项目ID")
    versions: List[CardVersionItem] = Field(default=[], description="版本列表")
    
    class Config:
        from_attributes = True


class CardUpdateRequest(BaseModel):
    """卡片更新请求
    
    用于更新卡片的基本信息。
    """
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="文件介绍")


class MultiVersionCompareRequest(BaseModel):
    """多版本对比请求
    
    用于请求对比多个版本之间的差异。
    """
    version_ids: List[str] = Field(..., description="要对比的版本ID列表")


class VersionCompareResult(BaseModel):
    """版本对比结果项
    
    表示两个版本之间的对比结果。
    """
    version_a_id: str = Field(..., description="版本A的ID")
    version_a_number: int = Field(..., description="版本A的编号")
    version_b_id: str = Field(..., description="版本B的ID")
    version_b_number: int = Field(..., description="版本B的编号")
    has_diff: bool = Field(..., description="是否存在差异")
    diff_summary: Optional[str] = Field(None, description="差异摘要")
    diff_stats: Optional[dict] = Field(None, description="差异统计信息")


class MultiVersionCompareResponse(BaseModel):
    """多版本对比响应
    
    包含多个版本之间的对比结果矩阵。
    """
    card_id: str = Field(..., description="卡片ID")
    compared_versions: List[CardVersionItem] = Field(..., description="参与对比的版本列表")
    compare_results: List[VersionCompareResult] = Field(..., description="对比结果列表")


class CardListResponse(BaseModel):
    """卡片列表响应
    
    分页返回卡片列表数据。
    """
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    items: List[CardListItem] = Field(..., description="卡片列表")


class CoverUploadResponse(BaseModel):
    """封面上传响应
    
    返回封面上传后的信息。
    """
    card_id: str = Field(..., description="卡片ID")
    cover_image: str = Field(..., description="封面图片路径")
    thumbnail_image: Optional[str] = Field(None, description="缩略图路径")
    original_filename: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小")
