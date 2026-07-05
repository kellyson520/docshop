import asyncio

import pytest

from app.services.event_bus import EventBus, format_sse, publish_config_updated


@pytest.mark.asyncio
async def test_publish_delivers_only_to_matching_topic():
    bus = EventBus(queue_size=5)

    async with bus.subscribe(topics={"config"}, user_id="u1", role="admin") as config_sub:
        async with bus.subscribe(topics={"announcements"}, user_id="u2", role="user") as other_sub:
            event = await bus.publish(
                topic="config",
                event_type="config.updated",
                payload={"changed_keys": ["LOG_LEVEL"]},
            )

            received = await asyncio.wait_for(config_sub.queue.get(), timeout=0.2)
            assert received.id == event.id
            assert received.topic == "config"
            assert received.type == "config.updated"
            assert received.payload == {"changed_keys": ["LOG_LEVEL"]}
            assert other_sub.queue.empty()


@pytest.mark.asyncio
async def test_queue_full_drops_oldest_event_for_slow_subscriber():
    bus = EventBus(queue_size=1)

    async with bus.subscribe(topics={"config"}, user_id="u1", role="admin") as sub:
        first = await bus.publish(topic="config", event_type="config.updated", payload={"n": 1})
        second = await bus.publish(topic="config", event_type="config.updated", payload={"n": 2})

        received = await asyncio.wait_for(sub.queue.get(), timeout=0.2)
        assert received.id == second.id
        assert received.id != first.id
        assert sub.queue.empty()


def test_format_sse_serializes_event_name_id_and_data():
    frame = format_sse("config.updated", "evt-1", {"ok": True})

    assert frame.startswith("event: config.updated\n")
    assert "id: evt-1\n" in frame
    assert 'data: {"ok": true}\n\n' in frame


@pytest.mark.asyncio
async def test_publish_config_updated_uses_config_topic(monkeypatch):
    bus = EventBus(queue_size=5)
    monkeypatch.setattr("app.services.event_bus.event_bus", bus)

    async with bus.subscribe(topics={"config"}, user_id="u1", role="admin") as sub:
        await publish_config_updated(["LOG_LEVEL"], source="settings-api")
        event = await asyncio.wait_for(sub.queue.get(), timeout=0.2)

    assert event.topic == "config"
    assert event.type == "config.updated"
    assert event.payload == {"changed_keys": ["LOG_LEVEL"], "source": "settings-api"}
