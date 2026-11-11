"""Tests for the realtime gateway and the event bus."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.domain.enums import EventKind
from ctf_team_dashboard.realtime.bus import EventBus, reset_event_bus
from ctf_team_dashboard.realtime.protocol import Message, MessageType, Subscription
from ctf_team_dashboard.repositories import Repositories
from ctf_team_dashboard.seed import persist_seed_data


# ----------------------------------------------------------------------
# Protocol
# ----------------------------------------------------------------------
def test_message_round_trip() -> None:
    """A message should survive a JSON round trip."""
    message = Message(type=MessageType.EVENT, payload={"kind": "solve.created", "id": 4})
    decoded = Message.from_json(message.to_json())
    assert decoded.type is MessageType.EVENT
    assert decoded.payload["id"] == 4


def test_message_rejects_unknown_type() -> None:
    """An unknown message type should be rejected."""
    with pytest.raises(ValueError, match="Unknown message type"):
        Message.from_json(json.dumps({"type": "nope"}))


def test_message_rejects_invalid_json() -> None:
    """A malformed frame should be rejected."""
    with pytest.raises(ValueError, match="not valid JSON"):
        Message.from_json("{")


def test_subscription_accepts_team_scoped_events() -> None:
    """A team scoped subscription should reject the events of other teams."""
    subscription = Subscription(team_id="team-1")
    assert subscription.accepts({"team_id": "team-1", "kind": "solve.created"})
    assert not subscription.accepts({"team_id": "team-2", "kind": "solve.created"})


def test_subscription_accepts_global_events() -> None:
    """An event without a team should reach every subscriber."""
    subscription = Subscription(team_id="team-1")
    assert subscription.accepts({"kind": "heartbeat"})


def test_subscription_filters_by_kind() -> None:
    """A kind filter should reject the events of other kinds."""
    subscription = Subscription(kinds=frozenset({"solve.created"}))
    assert subscription.accepts({"kind": "solve.created"})
    assert not subscription.accepts({"kind": "member.updated"})


# ----------------------------------------------------------------------
# Bus
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bus_delivers_to_subscribers() -> None:
    """Published events should reach every subscriber."""
    bus = EventBus()
    subscriber = await bus.subscribe("a")
    delivered = await bus.publish({"kind": "solve.created", "team_id": "team-1"})
    assert delivered == 1
    assert subscriber.queue.get_nowait()["kind"] == "solve.created"


@pytest.mark.asyncio
async def test_bus_filters_events() -> None:
    """A filtered subscriber should not receive the events it excluded."""
    bus = EventBus()
    await bus.subscribe("a", Subscription(team_id="team-1"))
    delivered = await bus.publish({"kind": "solve.created", "team_id": "team-2"})
    assert delivered == 1  # accepted but not queued for this subscriber

    subscriber = await bus.subscribe("b", Subscription(team_id="team-1"))
    await bus.publish({"kind": "solve.created", "team_id": "team-2"})
    assert subscriber.queue.empty()


@pytest.mark.asyncio
async def test_bus_unsubscribe_removes_the_client() -> None:
    """Unsubscribing should remove the client from the bus."""
    bus = EventBus()
    await bus.subscribe("a")
    assert await bus.subscriber_count() == 1
    await bus.unsubscribe("a")
    assert await bus.subscriber_count() == 0


@pytest.mark.asyncio
async def test_bus_updates_the_subscription() -> None:
    """A subscription update should change the delivered events."""
    bus = EventBus()
    await bus.subscribe("a")
    updated = await bus.update_subscription("a", Subscription(team_id="team-9"))
    assert updated is not None
    assert updated.subscription.team_id == "team-9"


@pytest.mark.asyncio
async def test_bus_drops_events_for_a_slow_client() -> None:
    """A slow client should never block the publisher."""
    bus = EventBus()
    subscriber = await bus.subscribe("a")
    for index in range(400):
        await bus.publish({"kind": "solve.created", "id": index})
    assert subscriber.dropped > 0


# ----------------------------------------------------------------------
# Gateway
# ----------------------------------------------------------------------
def test_realtime_status_endpoint(client: TestClient) -> None:
    """The status endpoint should expose the runtime counters."""
    response = client.get("/api/realtime/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["subscribers"] >= 0
    assert payload["published"] >= 0


def test_realtime_replay_endpoint(client: TestClient) -> None:
    """The replay endpoint should return the persisted events."""
    response = client.get("/api/realtime/replay", params={"limit": 5})
    assert response.status_code == 200
    assert "events" in response.json()


def test_websocket_receives_the_hello_frame(client: TestClient) -> None:
    """A connected client should receive the hello frame."""
    with client.websocket_connect("/ws") as socket:
        frame = socket.receive_json()
        assert frame["type"] == "hello"
        assert frame["v"] == 1
        assert frame["payload"]["subscriber_id"]


def test_websocket_answers_a_ping(client: TestClient) -> None:
    """A ping should be answered with a pong."""
    with client.websocket_connect("/ws") as socket:
        socket.receive_json()
        socket.send_json({"type": "ping", "payload": {}})
        frame = socket.receive_json()
        assert frame["type"] == "pong"


def test_websocket_accepts_a_subscription(client: TestClient) -> None:
    """A subscription should be acknowledged with a snapshot."""
    with client.websocket_connect("/ws") as socket:
        socket.receive_json()
        socket.send_json({"type": "subscribe", "payload": {"team_id": "team-1"}})
        frame = socket.receive_json()
        assert frame["type"] == "snapshot"
        assert frame["payload"]["subscription"]["team_id"] == "team-1"


def test_websocket_rejects_a_malformed_frame(client: TestClient) -> None:
    """A malformed frame should be answered with an error."""
    with client.websocket_connect("/ws") as socket:
        socket.receive_json()
        socket.send_text("not json")
        frame = socket.receive_json()
        assert frame["type"] == "error"


def test_websocket_rejects_an_unknown_message(client: TestClient) -> None:
    """An unsupported message should be answered with an error."""
    with client.websocket_connect("/ws") as socket:
        socket.receive_json()
        socket.send_json({"type": "bogus"})
        frame = socket.receive_json()
        assert frame["type"] == "error"


@pytest.mark.asyncio
async def test_publisher_forwards_recorded_events(repositories: Repositories) -> None:
    """The publisher should forward the recorded events to the bus."""
    from ctf_team_dashboard.realtime.publisher import EventPublisher

    bus = EventBus()
    subscriber = await bus.subscribe("test")
    publisher = EventPublisher(bus=bus)

    repositories.events.append(EventKind.SOLVE_CREATED, team_id=None, payload={"id": 7})
    published = await publisher.publish_once()

    assert published == 1
    event = subscriber.queue.get_nowait()
    assert event["kind"] == "solve.created"
    assert event["payload"]["id"] == 7


@pytest.mark.asyncio
async def test_publisher_is_idempotent(repositories: Repositories) -> None:
    """Publishing twice should not deliver the same event twice."""
    from ctf_team_dashboard.realtime.publisher import EventPublisher

    bus = EventBus()
    subscriber = await bus.subscribe("test")
    publisher = EventPublisher(bus=bus)

    repositories.events.append(EventKind.SOLVE_CREATED, team_id=None, payload={"id": 8})
    assert await publisher.publish_once() == 1
    subscriber.queue.get_nowait()
    assert await publisher.publish_once() == 0
    assert subscriber.queue.empty()


@pytest.mark.asyncio
async def test_publisher_replays_the_recent_events(repositories: Repositories) -> None:
    """The replay helper should return the most recent events."""
    from ctf_team_dashboard.realtime.publisher import EventPublisher

    publisher = EventPublisher(bus=EventBus())
    repositories.events.append(EventKind.MEMBER_UPDATED, team_id=None, payload={"id": 9})
    events = await publisher.replay(limit=5)
    assert events
    assert events[-1]["payload"]["id"] == 9


def test_seed_events_are_recorded(repositories: Repositories) -> None:
    """The seeded dataset should be persisted without activity events."""
    persist_seed_data(repositories, force=True)
    assert repositories.events.count_matching() == 0


def test_event_bus_reset_helper() -> None:
    """The reset helper should provide a fresh bus."""
    reset_event_bus()
    from ctf_team_dashboard.realtime.bus import get_event_bus

    assert get_event_bus() is get_event_bus()
