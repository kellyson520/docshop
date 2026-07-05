"""Server-sent event routes."""

from __future__ import annotations

import asyncio
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.deps.auth import get_current_user
from app.models.user import User
from app.services.event_bus import event_bus, format_sse

router = APIRouter(prefix="/api/v1/events", tags=["events"])

ALLOWED_TOPICS = {"config", "announcements", "tracking", "tasks"}
ADMIN_TOPICS = {"config", "tracking"}
HEARTBEAT_SECONDS = 15.0


def parse_topics(value: str | None) -> set[str]:
    topics = {part.strip() for part in (value or "config").split(",") if part.strip()}
    return topics or {"config"}


def authorize_topics(topics: Iterable[str], current_user: User) -> set[str]:
    requested = set(topics)
    invalid = requested - ALLOWED_TOPICS
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported event topics: {', '.join(sorted(invalid))}",
        )
    if ADMIN_TOPICS.intersection(requested) and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for requested event topics",
        )
    return requested


@router.get("/stream")
async def stream_events(
    request: Request,
    topics: str = Query("config"),
    current_user: User = Depends(get_current_user),
):
    subscribed_topics = authorize_topics(parse_topics(topics), current_user)

    async def event_generator():
        async with event_bus.subscribe(
            topics=subscribed_topics,
            user_id=str(current_user.id),
            role=current_user.role,
        ) as subscriber:
            yield format_sse(
                "ready",
                None,
                {
                    "topics": sorted(subscribed_topics),
                    "user_id": str(current_user.id),
                },
            )
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(subscriber.queue.get(), timeout=HEARTBEAT_SECONDS)
                except asyncio.TimeoutError:
                    yield format_sse("heartbeat", None, {"ok": True})
                    continue
                yield format_sse(event.type, event.id, event.to_dict())

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
