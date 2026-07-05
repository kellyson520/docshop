"""In-process event bus for server-sent application events."""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timezone
from typing import Any, AsyncIterator, Iterable

from app.utils.time import utc_now


@dataclass(frozen=True)
class EventEnvelope:
    id: str
    topic: str
    type: str
    scope: str = "global"
    ts: str = field(default_factory=lambda: utc_now().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"))
    version: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "type": self.type,
            "scope": self.scope,
            "ts": self.ts,
            "version": self.version,
            "payload": self.payload,
        }


@dataclass(eq=False)
class EventSubscriber:
    topics: set[str]
    user_id: str | None = None
    role: str | None = None
    queue_size: int = 100
    queue: asyncio.Queue[EventEnvelope] = field(init=False)
    loop: asyncio.AbstractEventLoop = field(init=False)

    def __post_init__(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.Queue(maxsize=max(1, self.queue_size))

    def accepts(self, event: EventEnvelope) -> bool:
        return event.topic in self.topics

    def _enqueue_nowait(self, event: EventEnvelope) -> None:
        if self.queue.full():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self.queue.put_nowait(event)

    def enqueue(self, event: EventEnvelope) -> None:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is self.loop:
            self._enqueue_nowait(event)
        else:
            self.loop.call_soon_threadsafe(self._enqueue_nowait, event)


class EventBus:
    def __init__(self, queue_size: int = 100) -> None:
        self.queue_size = queue_size
        self._subscribers: set[EventSubscriber] = set()
        self._lock = threading.RLock()
        self._version = 0

    @asynccontextmanager
    async def subscribe(
        self,
        topics: Iterable[str],
        user_id: str | None = None,
        role: str | None = None,
        queue_size: int | None = None,
    ) -> AsyncIterator[EventSubscriber]:
        subscriber = EventSubscriber(
            topics={topic for topic in topics if topic},
            user_id=user_id,
            role=role,
            queue_size=queue_size or self.queue_size,
        )
        with self._lock:
            self._subscribers.add(subscriber)
        try:
            yield subscriber
        finally:
            with self._lock:
                self._subscribers.discard(subscriber)

    async def publish(
        self,
        topic: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        scope: str = "global",
        version: str | None = None,
        event_id: str | None = None,
    ) -> EventEnvelope:
        with self._lock:
            self._version += 1
            resolved_version = version or f"{topic}:{self._version}"
            subscribers = list(self._subscribers)
        envelope = EventEnvelope(
            id=event_id or f"evt_{uuid.uuid4().hex}",
            topic=topic,
            type=event_type,
            scope=scope,
            version=resolved_version,
            payload=payload or {},
        )
        for subscriber in subscribers:
            if subscriber.accepts(envelope):
                subscriber.enqueue(envelope)
        return envelope


def format_sse(event_name: str, event_id: str | None, data: Any) -> str:
    lines: list[str] = []
    if event_name:
        lines.append(f"event: {event_name}")
    if event_id:
        lines.append(f"id: {event_id}")
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


event_bus = EventBus()


async def publish_config_updated(changed_keys: Iterable[str] | None = None, source: str = "unknown") -> EventEnvelope:
    return await event_bus.publish(
        topic="config",
        event_type="config.updated",
        payload={
            "changed_keys": list(changed_keys or []),
            "source": source,
        },
    )


async def publish_announcement_event(
    event_type: str,
    announcement_id: str,
    *,
    scope: str = "global",
) -> EventEnvelope:
    return await event_bus.publish(
        topic="announcements",
        event_type=event_type,
        scope=scope,
        payload={
            "announcement_id": announcement_id,
        },
    )
