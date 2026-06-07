"""
考试安排路由模块

提供考试相关的 API 端点，包括考试的增删改查、提醒管理等。
包含完善的参数校验、权限检查、日志记录和事务处理。
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.exam_schedule import ExamSchedule, ExamReminder, ExamStatus
from app.schemas.exam import (
    ExamCreate,
    ExamUpdate,
    ExamResponse,
    ExamListItem,
    ExamListResponse,
    ExamReminderResponse,
    UpcomingExamItem,
    UpcomingExamsResponse,
    ExamDismissRequest,
)
from app.deps.auth import get_current_user, get_current_admin
from app.utils.response import success_response
from app.utils.logger import get_logger, log_audit, log_operation
from app.exceptions import (
    ResourceNotFound,
    ValidationError,
    PermissionDenied,
    DatabaseError
)

# 获取模块日志器
exam_logger = get_logger("routers.exams")

router = APIRouter(prefix="/api/v1/exams", tags=["exams"])


# ===== 辅助函数 =====

def _get_exam_or_404(db: Session, exam_id: str) -> ExamSchedule:
    """
    获取考试或抛出 404 错误

    Args:
        db: 数据库会话
        exam_id: 考试ID

    Returns:
        ExamSchedule: 考试对象

    Raises:
        ResourceNotFound: 考试不存在时抛出
    """
    exam = db.query(ExamSchedule).filter(ExamSchedule.id == exam_id).first()
    if not exam:
        raise ResourceNotFound(resource="考试", resource_id=exam_id)
    return exam


def _check_project_exists(db: Session, project_id: str) -> Project:
    """
    检查项目是否存在

    Args:
        db: 数据库会话
        project_id: 项目ID

    Returns:
        Project: 项目对象

    Raises:
        ResourceNotFound: 项目不存在时抛出
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ResourceNotFound(resource="项目", resource_id=project_id)
    return project


def _update_exam_status(exam: ExamSchedule) -> ExamSchedule:
    """
    更新考试状态

    根据当前时间自动更新考试状态。

    Args:
        exam: 考试对象

    Returns:
        ExamSchedule: 更新后的考试对象
    """
    exam.update_status()
    return exam


def _exam_to_response(exam: ExamSchedule, db: Session) -> dict:
    """
    将考试对象转换为响应字典

    Args:
        exam: 考试对象
        db: 数据库会话

    Returns:
        dict: 响应字典
    """
    # 获取项目名称
    project_name = None
    if exam.project:
        project_name = exam.project.name

    # 更新状态
    _update_exam_status(exam)

    return {
        "id": exam.id,
        "name": exam.name,
        "description": exam.description,
        "start_time": exam.start_time,
        "end_time": exam.end_time,
        "project_id": exam.project_id,
        "project_name": project_name,
        "status": exam.status,
        "reminder_15min": exam.reminder_15min,
        "reminder_5min": exam.reminder_5min,
        "reminder_start": exam.reminder_start,
        "created_by": exam.created_by,
        "created_at": exam.created_at,
        "updated_at": exam.updated_at,
        "time_until_start": exam.get_time_until_start(),
        "time_until_end": exam.get_time_until_end(),
        "is_expired": exam.is_expired(),
        "is_upcoming": exam.is_upcoming(),
        "is_ongoing": exam.is_ongoing(),
    }


def _exam_to_list_item(exam: ExamSchedule) -> dict:
    """
    将考试对象转换为列表项字典

    Args:
        exam: 考试对象

    Returns:
        dict: 列表项字典
    """
    project_name = None
    if exam.project:
        project_name = exam.project.name

    return {
        "id": exam.id,
        "name": exam.name,
        "description": exam.description,
        "start_time": exam.start_time,
        "end_time": exam.end_time,
        "project_id": exam.project_id,
        "project_name": project_name,
        "status": exam.status,
        "reminder_15min": exam.reminder_15min,
        "reminder_5min": exam.reminder_5min,
        "reminder_start": exam.reminder_start,
        "created_at": exam.created_at,
    }


def _create_reminder_records(db: Session, exam: ExamSchedule, user_id: str):
    """
    为考试创建提醒记录

    Args:
        db: 数据库会话
        exam: 考试对象
        user_id: 用户ID
    """
    reminder_types = []
    if exam.reminder_15min:
        reminder_types.append("15min")
    if exam.reminder_5min:
        reminder_types.append("5min")
    if exam.reminder_start:
        reminder_types.append("start")

    for reminder_type in reminder_types:
        reminder = ExamReminder(
            exam_id=exam.id,
            user_id=user_id,
            reminder_type=reminder_type,
            is_triggered=0,
            is_dismissed=0,
        )
        db.add(reminder)


def _get_upcoming_reminders(
    db: Session,
    user_id: str,
    minutes_ahead: float = 20
) -> List[UpcomingExamItem]:
    """
    获取即将开始的考试提醒

    Args:
        db: 数据库会话
        user_id: 用户ID
        minutes_ahead: 提前分钟数

    Returns:
        List[UpcomingExamItem]: 即将开始的考试列表
    """
    now = datetime.utcnow()
    upcoming_exams = []

    # 获取用户所有的提醒记录
    reminders = db.query(ExamReminder).filter(
        ExamReminder.user_id == user_id,
        ExamReminder.is_dismissed == 0
    ).all()

    for reminder in reminders:
        exam = reminder.exam
        if not exam:
            continue

        # 更新考试状态
        _update_exam_status(exam)

        minutes_until = exam.get_time_until_start()

        # 检查是否需要触发提醒
        should_trigger = False
        if reminder.reminder_type == "15min" and exam.reminder_15min:
            # 15分钟提醒只处理即将开始的考试
            if exam.status == ExamStatus.upcoming.value and 0 < minutes_until <= 15:
                should_trigger = True
        elif reminder.reminder_type == "5min" and exam.reminder_5min:
            # 5分钟提醒只处理即将开始的考试
            if exam.status == ExamStatus.upcoming.value and 0 < minutes_until <= 5:
                should_trigger = True
        elif reminder.reminder_type == "start" and exam.reminder_start:
            # 开始提醒可以处理即将开始或进行中的考试（考试开始后的短时间内）
            if exam.status == ExamStatus.upcoming.value and minutes_until <= 0:
                should_trigger = True
            elif exam.status == ExamStatus.ongoing.value and minutes_until <= 0:
                should_trigger = True

        if should_trigger:
            project_name = exam.project.name if exam.project else None

            upcoming_exams.append(UpcomingExamItem(
                exam_id=exam.id,
                exam_name=exam.name,
                description=exam.description,
                start_time=exam.start_time,
                end_time=exam.end_time,
                project_id=exam.project_id,
                project_name=project_name,
                minutes_until_start=minutes_until,
                reminder_type=reminder.reminder_type,
                reminder_id=reminder.id,
            ))

    return upcoming_exams


# ===== API 端点 =====

@router.get("", response_model=dict)
def list_exams(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="考试状态过滤"),
    project_id: Optional[str] = Query(None, description="项目ID过滤"),
    keyword: Optional[str] = Query(None, max_length=100, description="搜索关键词"),
    sort_by: str = Query("start_time", pattern="^(start_time|end_time|created_at|name)$", description="排序字段"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="排序方向"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取考试列表

    支持分页、状态过滤、项目过滤和搜索功能。
    """
    operation_id = f"list_exams_page{page}_size{page_size}"
    log_operation(exam_logger, "list_exams", "started", f"User: {current_user.id}")

    try:
        # 构建查询
        query = db.query(ExamSchedule)

        # 项目过滤
        if project_id:
            query = query.filter(ExamSchedule.project_id == project_id)

        # 关键词搜索
        if keyword:
            search_pattern = f"%{keyword.strip()}%"
            query = query.filter(ExamSchedule.name.ilike(search_pattern))

        exams = query.all()

        for exam in exams:
            _update_exam_status(exam)

        if status:
            exams = [exam for exam in exams if exam.status == status]

        reverse = sort_order == "desc"
        exams.sort(key=lambda exam: getattr(exam, sort_by, "") or "", reverse=reverse)

        total = len(exams)
        offset = (page - 1) * page_size
        paged_exams = exams[offset:offset + page_size]
        items = [_exam_to_list_item(exam) for exam in paged_exams]

        db.commit()

        result = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }

        log_operation(exam_logger, "list_exams", "success",
                     f"User: {current_user.id}, Count: {len(items)}")

        return success_response(data=result)

    except Exception as e:
        db.rollback()
        log_operation(exam_logger, "list_exams", "failed",
                     f"User: {current_user.id}, Error: {e}")
        raise DatabaseError(
            message="获取考试列表失败",
            operation="list_exams"
        )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
def create_exam(
    request: Request,
    exam_data: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    创建新考试

    仅管理员可创建考试。自动创建关联的提醒记录。
    """
    log_operation(exam_logger, "create_exam", "started",
                 f"User: {current_user.id}, Name: {exam_data.name}")

    try:
        # 检查项目是否存在
        project = _check_project_exists(db, exam_data.project_id)

        # 检查考试名称是否在同一项目中已存在
        existing = db.query(ExamSchedule).filter(
            ExamSchedule.project_id == exam_data.project_id,
            ExamSchedule.name == exam_data.name
        ).first()

        if existing:
            raise ValidationError(
                message="该项目下已存在同名考试",
                field="name"
            )

        # 创建考试
        exam = ExamSchedule(
            name=exam_data.name,
            description=exam_data.description,
            start_time=exam_data.start_time,
            end_time=exam_data.end_time,
            project_id=exam_data.project_id,
            status=ExamStatus.upcoming.value,
            reminder_15min=exam_data.reminder_15min if exam_data.reminder_15min is not None else 1,
            reminder_5min=exam_data.reminder_5min if exam_data.reminder_5min is not None else 1,
            reminder_start=exam_data.reminder_start if exam_data.reminder_start is not None else 1,
            created_by=current_user.id,
        )

        db.add(exam)
        db.flush()  # 获取 exam.id

        # 创建提醒记录
        _create_reminder_records(db, exam, current_user.id)

        db.commit()
        db.refresh(exam)

        # 记录审计日志
        log_audit(
            user_id=str(current_user.id),
            action="create_exam",
            resource=f"exam:{exam.id}",
            result="success",
            details=f"name={exam_data.name}, project={exam_data.project_id}"
        )

        log_operation(exam_logger, "create_exam", "success",
                     f"User: {current_user.id}, Exam: {exam.id}")

        return success_response(data=_exam_to_response(exam, db))

    except ValidationError:
        raise
    except ResourceNotFound:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        exam_logger.error(f"数据库错误 - 创建考试: {e}")
        raise DatabaseError(
            message="创建考试失败",
            operation="create_exam"
        )
    except Exception as e:
        db.rollback()
        user_id = getattr(current_user, 'id', 'unknown')
        log_operation(exam_logger, "create_exam", "failed",
                     f"User: {user_id}, Error: {e}")
        raise DatabaseError(
            message=f"创建考试失败: {str(e)}",
            operation="create_exam"
        )


@router.get("/upcoming", response_model=dict)
def get_upcoming_exams(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取即将开始的考试提醒

    返回当前用户需要接收提醒的即将开始的考试列表。
    """
    log_operation(exam_logger, "get_upcoming_exams", "started",
                 f"User: {current_user.id}")

    try:
        upcoming = _get_upcoming_reminders(db, current_user.id)

        # 标记提醒为已触发
        for item in upcoming:
            reminder = db.query(ExamReminder).filter(
                ExamReminder.id == item.reminder_id
            ).first()
            if reminder and not reminder.is_triggered:
                reminder.mark_triggered()

        db.commit()

        result = {
            "total": len(upcoming),
            "items": [item.model_dump() for item in upcoming]
        }

        log_operation(exam_logger, "get_upcoming_exams", "success",
                     f"User: {current_user.id}, Count: {len(upcoming)}")

        return success_response(data=result)

    except Exception as e:
        db.rollback()
        log_operation(exam_logger, "get_upcoming_exams", "failed",
                     f"User: {current_user.id}, Error: {e}")
        raise DatabaseError(
            message="获取即将开始的考试失败",
            operation="get_upcoming_exams"
        )


@router.post("/{exam_id}/dismiss", response_model=dict)
def dismiss_reminder(
    request: Request,
    exam_id: str,
    dismiss_data: ExamDismissRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    关闭考试提醒

    关闭指定考试的提醒。可以指定提醒类型，不指定则关闭所有提醒。
    """
    log_operation(exam_logger, "dismiss_reminder", "started",
                 f"User: {current_user.id}, Exam: {exam_id}")

    try:
        # 检查考试是否存在
        exam = _get_exam_or_404(db, exam_id)

        # 构建查询条件
        query = db.query(ExamReminder).filter(
            ExamReminder.exam_id == exam_id,
            ExamReminder.user_id == current_user.id,
            ExamReminder.is_dismissed == 0
        )

        if dismiss_data.reminder_type:
            query = query.filter(ExamReminder.reminder_type == dismiss_data.reminder_type)

        reminders = query.all()

        if not reminders:
            raise ResourceNotFound(resource="活动提醒", resource_id=exam_id)

        # 标记为已关闭
        dismissed_count = 0
        for reminder in reminders:
            reminder.mark_dismissed()
            dismissed_count += 1

        db.commit()

        # 记录审计日志
        log_audit(
            user_id=str(current_user.id),
            action="dismiss_reminder",
            resource=f"exam:{exam_id}",
            result="success",
            details=f"type={dismiss_data.reminder_type or 'all'}, count={dismissed_count}"
        )

        log_operation(exam_logger, "dismiss_reminder", "success",
                     f"User: {current_user.id}, Exam: {exam_id}, Count: {dismissed_count}")

        return success_response(
            data={"dismissed_count": dismissed_count},
            message=f"成功关闭 {dismissed_count} 个提醒"
        )

    except ResourceNotFound:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        exam_logger.error(f"数据库错误 - 关闭提醒: {e}")
        raise DatabaseError(
            message="关闭提醒失败",
            operation="dismiss_reminder"
        )
    except Exception as e:
        db.rollback()
        log_operation(exam_logger, "dismiss_reminder", "failed",
                     f"User: {current_user.id}, Exam: {exam_id}, Error: {e}")
        raise DatabaseError(
            message=f"关闭提醒失败: {str(e)}",
            operation="dismiss_reminder"
        )


@router.get("/{exam_id}", response_model=dict)
def get_exam(
    request: Request,
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取考试详情

    获取指定考试的详细信息，包括计算字段。
    """
    log_operation(exam_logger, "get_exam", "started",
                 f"User: {current_user.id}, Exam: {exam_id}")

    try:
        exam = _get_exam_or_404(db, exam_id)

        # 更新状态
        _update_exam_status(exam)
        db.commit()

        log_operation(exam_logger, "get_exam", "success",
                     f"User: {current_user.id}, Exam: {exam_id}")

        return success_response(data=_exam_to_response(exam, db))

    except ResourceNotFound:
        raise
    except Exception as e:
        db.rollback()
        log_operation(exam_logger, "get_exam", "failed",
                     f"User: {current_user.id}, Exam: {exam_id}, Error: {e}")
        raise DatabaseError(
            message="获取考试详情失败",
            operation="get_exam"
        )


@router.put("/{exam_id}", response_model=dict)
def update_exam(
    request: Request,
    exam_id: str,
    exam_data: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    更新考试信息

    仅管理员可更新考试。支持部分更新。
    """
    log_operation(exam_logger, "update_exam", "started",
                 f"User: {current_user.id}, Exam: {exam_id}")

    try:
        exam = _get_exam_or_404(db, exam_id)

        # 检查新名称是否冲突
        target_project_id = exam_data.project_id or exam.project_id
        target_name = exam_data.name if exam_data.name is not None else exam.name

        if exam_data.project_id is not None:
            _check_project_exists(db, exam_data.project_id)

        if target_name != exam.name or target_project_id != exam.project_id:
            existing = db.query(ExamSchedule).filter(
                ExamSchedule.project_id == target_project_id,
                ExamSchedule.name == target_name,
                ExamSchedule.id != exam_id
            ).first()

            if existing:
                raise ValidationError(
                    message="该项目下已存在同名考试",
                    field="name"
                )

        # 更新字段
        update_fields = []

        if exam_data.name is not None:
            exam.name = exam_data.name
            update_fields.append("name")

        if exam_data.description is not None:
            exam.description = exam_data.description
            update_fields.append("description")

        if exam_data.start_time is not None:
            exam.start_time = exam_data.start_time
            update_fields.append("start_time")

        if exam_data.end_time is not None:
            exam.end_time = exam_data.end_time
            update_fields.append("end_time")

        if exam_data.project_id is not None:
            exam.project_id = exam_data.project_id
            update_fields.append("project_id")

        if exam_data.reminder_15min is not None:
            exam.reminder_15min = exam_data.reminder_15min
            update_fields.append("reminder_15min")

        if exam_data.reminder_5min is not None:
            exam.reminder_5min = exam_data.reminder_5min
            update_fields.append("reminder_5min")

        if exam_data.reminder_start is not None:
            exam.reminder_start = exam_data.reminder_start
            update_fields.append("reminder_start")

        # 只有有更新时才提交
        if update_fields:
            exam.updated_at = datetime.utcnow().isoformat() + "Z"
            _update_exam_status(exam)
            if any(field in update_fields for field in ["reminder_15min", "reminder_5min", "reminder_start"]):
                db.query(ExamReminder).filter(
                    ExamReminder.exam_id == exam.id,
                    ExamReminder.user_id == current_user.id
                ).delete(synchronize_session=False)
                _create_reminder_records(db, exam, current_user.id)
            db.commit()
            db.refresh(exam)

            # 记录审计日志
            log_audit(
                user_id=str(current_user.id),
                action="update_exam",
                resource=f"exam:{exam_id}",
                result="success",
                details=f"fields={','.join(update_fields)}"
            )

        log_operation(exam_logger, "update_exam", "success",
                     f"User: {current_user.id}, Exam: {exam_id}, Fields: {update_fields}")

        return success_response(data=_exam_to_response(exam, db))

    except (ResourceNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        db.rollback()
        exam_logger.error(f"数据库错误 - 更新考试: {e}")
        raise DatabaseError(
            message="更新考试失败",
            operation="update_exam"
        )
    except Exception as e:
        db.rollback()
        log_operation(exam_logger, "update_exam", "failed",
                     f"User: {current_user.id}, Exam: {exam_id}, Error: {e}")
        raise DatabaseError(
            message=f"更新考试失败: {str(e)}",
            operation="update_exam"
        )


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    request: Request,
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    删除考试

    仅管理员可删除考试。级联删除关联的提醒记录。
    此操作不可恢复。
    """
    log_operation(exam_logger, "delete_exam", "started",
                 f"User: {current_user.id}, Exam: {exam_id}")

    try:
        exam = _get_exam_or_404(db, exam_id)

        # 删除考试（级联删除关联的提醒记录）
        db.delete(exam)
        db.commit()

        # 记录审计日志
        log_audit(
            user_id=str(current_user.id),
            action="delete_exam",
            resource=f"exam:{exam_id}",
            result="success"
        )

        log_operation(exam_logger, "delete_exam", "success",
                     f"User: {current_user.id}, Exam: {exam_id}")

        return None

    except ResourceNotFound:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        exam_logger.error(f"数据库错误 - 删除考试: {e}")
        raise DatabaseError(
            message="删除考试失败",
            operation="delete_exam"
        )
    except Exception as e:
        db.rollback()
        log_operation(exam_logger, "delete_exam", "failed",
                     f"User: {current_user.id}, Exam: {exam_id}, Error: {e}")
        raise DatabaseError(
            message=f"删除考试失败: {str(e)}",
            operation="delete_exam"
        )
