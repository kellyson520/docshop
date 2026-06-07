"""
考试安排模式模块

提供考试相关的 Pydantic 模式定义。
包含请求模型、响应模型和字段校验。
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.models.exam_schedule import ExamStatus


class ExamCreate(BaseModel):
    """
    考试创建请求模型

    用于创建新的考试安排。
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="考试名称"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="考试描述"
    )
    start_time: str = Field(
        ...,
        description="开始时间（ISO 8601格式）"
    )
    end_time: str = Field(
        ...,
        description="结束时间（ISO 8601格式）"
    )
    project_id: str = Field(
        ...,
        min_length=1,
        max_length=36,
        description="关联项目ID"
    )
    reminder_15min: Optional[int] = Field(
        1,
        ge=0,
        le=1,
        description="15分钟前提醒（0=关闭，1=启用）"
    )
    reminder_5min: Optional[int] = Field(
        1,
        ge=0,
        le=1,
        description="5分钟前提醒（0=关闭，1=启用）"
    )
    reminder_start: Optional[int] = Field(
        1,
        ge=0,
        le=1,
        description="开始时提醒（0=关闭，1=启用）"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证考试名称"""
        v = v.strip()
        if not v:
            raise ValueError("考试名称不能为空")
        if not v.replace(' ', '').replace('\t', ''):
            raise ValueError("考试名称不能只包含空白字符")
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """验证描述长度"""
        if v is not None:
            v = v.strip()
            if len(v) > 500:
                raise ValueError("考试描述不能超过500字符")
        return v

    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """验证时间格式"""
        try:
            # 支持 ISO 8601 格式（带或不带Z后缀）
            if v.endswith('Z'):
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            else:
                datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("时间格式不正确，请使用 ISO 8601 格式（如：2024-01-01T09:00:00Z）")

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: str, info) -> str:
        """验证结束时间晚于开始时间"""
        values = info.data
        if 'start_time' in values:
            start_str = values['start_time']
            try:
                start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end = datetime.fromisoformat(v.replace('Z', '+00:00'))
                if end <= start:
                    raise ValueError("结束时间必须晚于开始时间")
            except ValueError as e:
                if "结束时间必须晚于开始时间" in str(e):
                    raise
                # 忽略时间解析错误，由其他验证器处理
        return v


class ExamUpdate(BaseModel):
    """
    考试更新请求模型

    用于更新现有考试安排。
    """
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="考试名称"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="考试描述"
    )
    start_time: Optional[str] = Field(
        None,
        description="开始时间（ISO 8601格式）"
    )
    end_time: Optional[str] = Field(
        None,
        description="结束时间（ISO 8601格式）"
    )
    project_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=36,
        description="关联项目ID"
    )
    reminder_15min: Optional[int] = Field(
        None,
        ge=0,
        le=1,
        description="15分钟前提醒（0=关闭，1=启用）"
    )
    reminder_5min: Optional[int] = Field(
        None,
        ge=0,
        le=1,
        description="5分钟前提醒（0=关闭，1=启用）"
    )
    reminder_start: Optional[int] = Field(
        None,
        ge=0,
        le=1,
        description="开始时提醒（0=关闭，1=启用）"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """验证考试名称"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("考试名称不能为空")
            if not v.replace(' ', '').replace('\t', ''):
                raise ValueError("考试名称不能只包含空白字符")
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """验证描述长度"""
        if v is not None:
            v = v.strip()
            if len(v) > 500:
                raise ValueError("考试描述不能超过500字符")
        return v

    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        """验证时间格式"""
        if v is not None:
            try:
                if v.endswith('Z'):
                    datetime.fromisoformat(v.replace('Z', '+00:00'))
                else:
                    datetime.fromisoformat(v)
                return v
            except ValueError:
                raise ValueError("时间格式不正确，请使用 ISO 8601 格式")
        return v


class ExamResponse(BaseModel):
    """
    考试详情响应模型

    返回单个考试的详细信息。
    """
    id: str
    name: str
    description: Optional[str]
    start_time: str
    end_time: str
    project_id: str
    project_name: Optional[str]
    status: str
    reminder_15min: int
    reminder_5min: int
    reminder_start: int
    created_by: str
    created_at: str
    updated_at: str
    # 计算字段
    time_until_start: Optional[float] = None  # 距离开始的分钟数
    time_until_end: Optional[float] = None    # 距离结束的分钟数
    is_expired: bool = False
    is_upcoming: bool = False
    is_ongoing: bool = False

    class Config:
        from_attributes = True


class ExamListItem(BaseModel):
    """
    考试列表项模型

    用于列表展示，字段精简。
    """
    id: str
    name: str
    description: Optional[str]
    start_time: str
    end_time: str
    project_id: str
    project_name: Optional[str]
    status: str
    reminder_15min: int
    reminder_5min: int
    reminder_start: int
    created_at: str

    class Config:
        from_attributes = True


class ExamListResponse(BaseModel):
    """
    考试列表响应模型

    包含分页信息和考试列表。
    """
    total: int
    page: int
    page_size: int
    items: List[ExamListItem]


class ExamReminderResponse(BaseModel):
    """
    考试提醒响应模型

    返回提醒的详细信息。
    """
    id: str
    exam_id: str
    exam_name: str
    user_id: str
    reminder_type: str
    is_triggered: int
    is_dismissed: int
    triggered_at: Optional[str]
    dismissed_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class UpcomingExamItem(BaseModel):
    """
    即将开始的考试项模型

    用于提醒展示。
    """
    exam_id: str
    exam_name: str
    description: Optional[str]
    start_time: str
    end_time: str
    project_id: str
    project_name: Optional[str]
    minutes_until_start: float
    reminder_type: str  # 15min, 5min, start
    reminder_id: str

    class Config:
        from_attributes = True


class UpcomingExamsResponse(BaseModel):
    """
    即将开始的考试列表响应模型

    用于提醒中心展示。
    """
    total: int
    items: List[UpcomingExamItem]


class ExamDismissRequest(BaseModel):
    """
    关闭提醒请求模型
    """
    reminder_type: Optional[str] = Field(
        None,
        description="提醒类型（15min/5min/start），不指定则关闭所有"
    )

    @field_validator('reminder_type')
    @classmethod
    def validate_reminder_type(cls, v: Optional[str]) -> Optional[str]:
        """验证提醒类型"""
        if v is not None and v not in ['15min', '5min', 'start']:
            raise ValueError("提醒类型必须是 15min、5min 或 start")
        return v


class ExamFilterParams(BaseModel):
    """
    考试筛选参数模型

    用于列表查询的筛选条件。
    """
    status: Optional[str] = Field(
        None,
        description="考试状态（upcoming/ongoing/expired）"
    )
    project_id: Optional[str] = Field(
        None,
        description="项目ID"
    )
    keyword: Optional[str] = Field(
        None,
        max_length=100,
        description="搜索关键词（考试名称）"
    )
    start_from: Optional[str] = Field(
        None,
        description="开始时间范围（从）"
    )
    start_to: Optional[str] = Field(
        None,
        description="开始时间范围（到）"
    )

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """验证状态值"""
        if v is not None and v not in [s.value for s in ExamStatus]:
            raise ValueError(f"无效的状态值，可选: {[s.value for s in ExamStatus]}")
        return v
