"""
追踪管理API（仅管理员）

提供追踪配置管理和访问日志查询功能。
"""
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, literal, case

from app.utils.time import utc_now, utc_now_iso
from app.database import get_db
from app.deps.auth import get_current_admin
from app.models.user import User
from app.models.tracking_config import TrackingConfig
from app.models.access_log import AccessLog
from app.models.user_session import UserSession
from app.services.ippure_service import build_visitor_ip_context
from app.schemas.response import ApiResponse, success_response
from app.utils.logger import log_audit

router = APIRouter(prefix="/admin/tracking", tags=["tracking-admin"])


def _build_log_payload(log: AccessLog, include_raw: bool = False) -> dict:
    payload = log.to_dict(include_raw=include_raw)
    payload["visitor_ip_context"] = build_visitor_ip_context(
        log.ip_address,
        {
            "country": log.ip_country,
            "countryCode": log.ip_country,
            "city": log.ip_city,
            "asn": log.ip_asn,
            "isp": log.ip_isp,
        },
    )
    return payload


def _stats_window(days: int, timezone_offset_minutes: int = 0):
    now = utc_now().replace(microsecond=0)
    offset = timedelta(minutes=timezone_offset_minutes)
    local_now = now + offset
    if days <= 1:
        local_start = local_now.replace(hour=0, minute=0, second=0)
    else:
        local_start = (local_now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0)
    start_time = local_start - offset
    return start_time, now, local_start, local_now


def _resolve_granularity(days: int, granularity: str) -> str:
    if granularity == "auto":
        return "hour" if days <= 1 else "day"
    if granularity in {"hour", "day"}:
        return granularity
    return "day"


def _bucket_key(dt: datetime, granularity: str) -> str:
    if granularity == "hour":
        return dt.strftime("%Y-%m-%dT%H")
    return dt.strftime("%Y-%m-%d")


def _bucket_label(key: str, granularity: str) -> str:
    if granularity == "hour":
        return key.replace("T", " ") + ":00"
    return key


def _empty_trend_buckets(start_time: datetime, end_time: datetime, granularity: str):
    if granularity == "hour":
        cursor = start_time.replace(minute=0, second=0, microsecond=0)
        step = timedelta(hours=1)
    else:
        cursor = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        step = timedelta(days=1)

    buckets = []
    while cursor <= end_time:
        key = _bucket_key(cursor, granularity)
        buckets.append({
            "bucket": key,
            "label": _bucket_label(key, granularity),
            "date": _bucket_label(key, granularity),
            "visits": 0,
            "visitors": 0,
            "avg_response_time_ms": 0,
            "min_response_time_ms": 0,
            "max_response_time_ms": 0,
            "error_count": 0,
            "error_rate": 0,
        })
        cursor += step
    return buckets


def _localized_bucket_expr(granularity: str, timezone_offset_minutes: int):
    timestamp_expr = func.replace(func.replace(AccessLog.timestamp, "T", " "), "Z", "")
    modifier = literal(f"{timezone_offset_minutes:+d} minutes")
    if granularity == "hour":
        return func.strftime("%Y-%m-%dT%H", timestamp_expr, modifier).label("bucket")
    return func.strftime("%Y-%m-%d", timestamp_expr, modifier).label("bucket")


@router.get("/config", response_model=ApiResponse)
def get_tracking_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    获取追踪配置

    返回当前追踪系统的配置信息。
    """
    config = db.query(TrackingConfig).first()
    if not config:
        config = TrackingConfig()
        db.add(config)
        db.commit()
        db.refresh(config)

    return success_response(config.to_dict())


@router.put("/config", response_model=ApiResponse)
def update_tracking_config(
    enable_tracking: Optional[int] = Query(None, ge=0, le=1),
    enable_ip_tracking: Optional[int] = Query(None, ge=0, le=1),
    enable_device_tracking: Optional[int] = Query(None, ge=0, le=1),
    enable_location_tracking: Optional[int] = Query(None, ge=0, le=1),
    enable_behavior_tracking: Optional[int] = Query(None, ge=0, le=1),
    data_retention_days: Optional[int] = Query(None, ge=1, le=3650),
    anonymize_ip: Optional[int] = Query(None, ge=0, le=1),
    exclude_internal_ips: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    更新追踪配置

    支持更新各项追踪开关和隐私设置。
    """
    config = db.query(TrackingConfig).first()
    if not config:
        config = TrackingConfig()
        db.add(config)

    if enable_tracking is not None:
        config.enable_tracking = enable_tracking
    if enable_ip_tracking is not None:
        config.enable_ip_tracking = enable_ip_tracking
    if enable_device_tracking is not None:
        config.enable_device_tracking = enable_device_tracking
    if enable_location_tracking is not None:
        config.enable_location_tracking = enable_location_tracking
    if enable_behavior_tracking is not None:
        config.enable_behavior_tracking = enable_behavior_tracking
    if data_retention_days is not None:
        config.data_retention_days = data_retention_days
    if anonymize_ip is not None:
        config.anonymize_ip = anonymize_ip
    if exclude_internal_ips is not None:
        config.exclude_internal_ips = exclude_internal_ips

    # 更新时间戳
    config.updated_at = utc_now_iso()

    db.commit()
    db.refresh(config)

    # 审计日志
    log_audit(
        user_id=current_user.id,
        action="update_tracking_config",
        resource="tracking_config",
        result="success",
    )

    return success_response({"message": "配置已更新", "config": config.to_dict()})


@router.get("/stats", response_model=ApiResponse)
def get_tracking_stats(
    days: int = Query(7, ge=1, le=365),
    granularity: str = Query("auto"),
    timezone_offset_minutes: int = Query(0, ge=-840, le=840),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    获取追踪统计

    返回指定时间范围内的访问统计数据，包括：
    - 总访问量和独立访客数
    - 设备分布
    - 浏览器分布
    - 操作系统分布
    - 地理位置分布
    - 趋势数据（今天默认按小时，其它周期默认按天）
    """
    start_time, end_time, local_start_time, local_end_time = _stats_window(days, timezone_offset_minutes)
    resolved_granularity = _resolve_granularity(days, granularity)
    start_date = start_time.isoformat() + "Z"
    end_date = end_time.isoformat() + "Z"

    # 总访问量
    total_visits = db.query(AccessLog).filter(
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.is_deleted == 0
    ).count()

    # 独立访客（按session）
    unique_visitors = db.query(AccessLog.session_id).filter(
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.is_deleted == 0
    ).distinct().count()

    # 设备分布
    device_stats = db.query(
        AccessLog.device_type,
        func.count(AccessLog.id).label("count")
    ).filter(
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.is_deleted == 0
    ).group_by(AccessLog.device_type).all()

    # 浏览器分布
    browser_stats = db.query(
        AccessLog.browser_name,
        func.count(AccessLog.id).label("count")
    ).filter(
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.is_deleted == 0
    ).group_by(AccessLog.browser_name).all()

    # 操作系统分布
    os_stats = db.query(
        AccessLog.os_name,
        func.count(AccessLog.id).label("count")
    ).filter(
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.is_deleted == 0
    ).group_by(AccessLog.os_name).all()

    # 地理位置分布（Top 10）
    country_stats = db.query(
        AccessLog.ip_country,
        func.count(AccessLog.id).label("count")
    ).filter(
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.ip_country.isnot(None),
        AccessLog.is_deleted == 0
    ).group_by(AccessLog.ip_country).order_by(desc("count")).limit(10).all()

    # 趋势数据
    bucket_expr = _localized_bucket_expr(resolved_granularity, timezone_offset_minutes)

    trend_stats_query = db.query(
        bucket_expr,
        func.count(AccessLog.id).label("visits"),
        func.count(func.distinct(AccessLog.session_id)).label("visitors"),
        func.avg(AccessLog.response_time_ms).label("avg_response_time_ms"),
        func.min(AccessLog.response_time_ms).label("min_response_time_ms"),
        func.max(AccessLog.response_time_ms).label("max_response_time_ms"),
        func.sum(
            case((AccessLog.response_status >= 400, 1), else_=0)
        ).label("error_count"),
    ).filter(
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.is_deleted == 0
    ).group_by("bucket").order_by("bucket").all()

    trend_map = {
        item.bucket: {
            "visits": item.visits,
            "visitors": item.visitors,
            "avg_response_time_ms": round(item.avg_response_time_ms or 0, 2),
            "min_response_time_ms": item.min_response_time_ms or 0,
            "max_response_time_ms": item.max_response_time_ms or 0,
            "error_count": item.error_count or 0,
            "error_rate": round(((item.error_count or 0) / item.visits) * 100, 2) if item.visits else 0,
        }
        for item in trend_stats_query
    }
    trend = _empty_trend_buckets(local_start_time, local_end_time, resolved_granularity)
    for bucket in trend:
        values = trend_map.get(bucket["bucket"])
        if values:
            bucket["visits"] = values["visits"]
            bucket["visitors"] = values["visitors"]
            bucket["avg_response_time_ms"] = values["avg_response_time_ms"]
            bucket["min_response_time_ms"] = values["min_response_time_ms"]
            bucket["max_response_time_ms"] = values["max_response_time_ms"]
            bucket["error_count"] = values["error_count"]
            bucket["error_rate"] = values["error_rate"]

    # 响应时间统计
    response_time_stats = db.query(
        func.avg(AccessLog.response_time_ms).label("avg_time"),
        func.min(AccessLog.response_time_ms).label("min_time"),
        func.max(AccessLog.response_time_ms).label("max_time")
    ).filter(
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.is_deleted == 0
    ).first()

    # 状态码分布
    status_stats = db.query(
        AccessLog.response_status,
        func.count(AccessLog.id).label("count")
    ).filter(
        AccessLog.timestamp >= start_date,
        AccessLog.timestamp <= end_date,
        AccessLog.is_deleted == 0
    ).group_by(AccessLog.response_status).all()

    return success_response({
        "period_days": days,
        "granularity": resolved_granularity,
        "requested_granularity": granularity,
        "timezone_offset_minutes": timezone_offset_minutes,
        "start_time": start_date,
        "end_time": end_date,
        "local_start_time": local_start_time.isoformat(),
        "local_end_time": local_end_time.isoformat(),
        "total_visits": total_visits,
        "unique_visitors": unique_visitors,
        "device_distribution": [{"type": d.device_type or "unknown", "count": d.count} for d in device_stats],
        "browser_distribution": [{"name": b.browser_name or "unknown", "count": b.count} for b in browser_stats],
        "os_distribution": [{"name": o.os_name or "unknown", "count": o.count} for o in os_stats],
        "country_distribution": [{"country": c.ip_country, "count": c.count} for c in country_stats],
        "trend": trend,
        "daily_trend": trend,
        "response_time": {
            "avg_ms": round(response_time_stats.avg_time, 2) if response_time_stats.avg_time else 0,
            "min_ms": response_time_stats.min_time or 0,
            "max_ms": response_time_stats.max_time or 0,
        },
        "status_distribution": [{"status": s.response_status, "count": s.count} for s in status_stats],
    })


@router.get("/logs", response_model=ApiResponse)
def get_access_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    ip: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    page_views_only: Optional[int] = Query(None, ge=0, le=1),
    visitor_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    获取访问日志列表

    支持分页和多种筛选条件。
    """
    query = db.query(AccessLog).filter(AccessLog.is_deleted == 0)

    if ip:
        safe_ip = ip.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(AccessLog.ip_address.like(f"%{safe_ip}%", escape="\\"))
    if user_id:
        query = query.filter(AccessLog.user_id == user_id)
    if device_type:
        query = query.filter(AccessLog.device_type == device_type)
    if page_views_only:
        query = query.filter(AccessLog.is_page_view == 1)
    if visitor_id:
        query = query.filter(AccessLog.visitor_id == visitor_id)
    if start_date:
        query = query.filter(AccessLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AccessLog.timestamp <= end_date)

    total = query.count()
    logs = query.order_by(AccessLog.timestamp.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return success_response({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_build_log_payload(log) for log in logs],
    })


@router.get("/logs/{log_id}", response_model=ApiResponse)
def get_access_log_detail(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    获取访问日志详情

    返回单条日志的详细信息，包括原始数据。
    """
    log = db.query(AccessLog).filter(
        AccessLog.id == log_id,
        AccessLog.is_deleted == 0
    ).first()

    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="日志不存在")

    payload = _build_log_payload(log, include_raw=True)
    return success_response(payload)


@router.delete("/logs", response_model=ApiResponse)
def clear_old_logs(
    days: int = Query(90, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    清理旧日志

    软删除指定天数之前的访问日志。
    """
    cutoff_date = (utc_now() - timedelta(days=days)).isoformat()

    # 软删除
    from sqlalchemy import update
    result = db.execute(
        update(AccessLog)
        .where(AccessLog.timestamp < cutoff_date, AccessLog.is_deleted == 0)
        .values(is_deleted=1)
    )
    count = result.rowcount

    db.commit()

    # 审计日志
    log_audit(
        user_id=current_user.id,
        action="clear_old_logs",
        resource="access_logs",
        result="success",
        details=f"days={days}, count={count}",
    )

    return success_response({
        "deleted_count": count,
        "message": f"已清理 {count} 条记录"
    })


@router.get("/sessions", response_model=ApiResponse)
def get_user_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = Query(None),
    fingerprint: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    获取用户会话列表

    支持分页和筛选条件。
    """
    query = db.query(UserSession).filter(UserSession.is_deleted == 0)

    if user_id:
        query = query.filter(UserSession.user_id == user_id)
    if fingerprint:
        query = query.filter(UserSession.device_fingerprint.like(f"%{fingerprint}%"))

    total = query.count()
    sessions = query.order_by(UserSession.last_seen_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return success_response({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [session.to_dict() for session in sessions]
    })


@router.get("/realtime", response_model=ApiResponse)
def get_realtime_stats(
    minutes: int = Query(5, ge=1, le=60),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    获取实时统计

    返回最近指定分钟内的访问统计。
    """
    start_time = (utc_now() - timedelta(minutes=minutes)).isoformat()

    # 最近访问数
    recent_visits = db.query(AccessLog).filter(
        AccessLog.timestamp >= start_time,
        AccessLog.is_deleted == 0
    ).count()

    # 在线会话数（有最近活动的会话）
    online_sessions = db.query(UserSession).filter(
        UserSession.last_seen_at >= start_time,
        UserSession.is_deleted == 0
    ).count()

    # 最近访问路径
    recent_paths = db.query(
        AccessLog.request_path,
        func.count(AccessLog.id).label("count")
    ).filter(
        AccessLog.timestamp >= start_time,
        AccessLog.is_deleted == 0
    ).group_by(AccessLog.request_path).order_by(desc("count")).limit(10).all()

    # 最近活跃用户
    recent_users = db.query(
        AccessLog.user_id,
        func.count(AccessLog.id).label("count")
    ).filter(
        AccessLog.timestamp >= start_time,
        AccessLog.is_deleted == 0,
        AccessLog.user_id.isnot(None)
    ).group_by(AccessLog.user_id).order_by(desc("count")).limit(10).all()

    return success_response({
        "period_minutes": minutes,
        "recent_visits": recent_visits,
        "online_sessions": online_sessions,
        "top_paths": [{"path": p.request_path, "count": p.count} for p in recent_paths],
        "active_users": [{"user_id": u.user_id, "count": u.count} for u in recent_users],
    })
