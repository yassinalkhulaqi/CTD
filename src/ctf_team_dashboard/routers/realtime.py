"""Realtime gateway exposing the websocket endpoint."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from ctf_team_dashboard.config import Settings, get_settings
from ctf_team_dashboard.realtime.bus import EventBus, get_event_bus
from ctf_team_dashboard.realtime.protocol import (
    PROTOCOL_VERSION,
    Message,
    MessageType,
    Subscription,
)
from ctf_team_dashboard.realtime.publisher import EventPublisher, get_publisher

logger = logging.getLogger("ctf_team_dashboard.realtime")

router = APIRouter(tags=["realtime"])

HEARTBEAT_INTERVAL = 20.0
SEND_TIMEOUT = 10.0


async def _safe_send(websocket: WebSocket, message: Message) -> bool:
    """Send a message, swallowing the failures of a closed socket.

    Args:
        websocket - The socket to write to.
        message - The message to send.

    Returns:
        ``True`` when the message was sent.
    """
    try:
        await asyncio.wait_for(websocket.send_text(message.to_json()), timeout=SEND_TIMEOUT)
    except (WebSocketDisconnect, RuntimeError, asyncio.TimeoutError):
        return False
    return True


def _parse_subscription(payload: dict[str, Any]) -> Subscription:
    """Build a subscription from the payload of a subscribe message.

    Args:
        payload - The payload of the message.

    Returns:
        The parsed subscription.
    """
    team_id = payload.get("team_id")
    raw_kinds = payload.get("kinds")
    kinds = (
        frozenset(str(kind) for kind in raw_kinds)
        if isinstance(raw_kinds, list)
        else frozenset()
    )
    return Subscription(team_id=str(team_id) if team_id else None, kinds=kinds)


async def _handle_client_message(
    websocket: WebSocket,
    message: Message,
    subscriber_id: str,
    bus: EventBus,
) -> Subscription:
    """Process a message received from a client.

    Args:
        websocket - The socket the message was received on.
        message - The decoded message.
        subscriber_id - The identifier of the subscriber.
        bus - The event bus.

    Returns:
        The subscription applied to the subscriber.
    """
    if message.type is MessageType.PING:
        await _safe_send(
            websocket,
            Message(
                type=MessageType.PONG,
                payload={"ts": message.sent_at.isoformat()},
            ),
        )
        return Subscription()

    if message.type is MessageType.SUBSCRIBE:
        subscription = _parse_subscription(message.payload)
        await bus.update_subscription(subscriber_id, subscription)
        await _safe_send(
            websocket,
            Message(
                type=MessageType.SNAPSHOT,
                payload={"subscription": subscription.to_payload(), "ok": True},
            ),
        )
        return subscription

    if message.type is MessageType.UNSUBSCRIBE:
        subscription = Subscription()
        await bus.update_subscription(subscriber_id, subscription)
        await _safe_send(websocket, Message(type=MessageType.SNAPSHOT, payload={"ok": True}))
        return subscription

    await _safe_send(
        websocket,
        Message(
            type=MessageType.ERROR,
            payload={"message": f"Unsupported message {message.type.value}"},
        ),
    )
    return Subscription()


@router.websocket("/ws")
async def realtime_socket(
    websocket: WebSocket,
    team_id: str | None = Query(default=None),
    last_event_id: int | None = Query(default=None, alias="last_event_id"),
) -> None:
    """Open the realtime channel used by the dashboard.

    The socket replays the missed events, then streams the new ones. Clients
    can narrow the stream with a ``subscribe`` message.
    """
    bus = get_event_bus()

    await websocket.accept()
    subscriber_id = f"ws-{id(websocket)}"

    subscriber = await bus.subscribe(subscriber_id, Subscription(team_id=team_id))
    await _safe_send(
        websocket,
        Message(
            type=MessageType.HELLO,
            payload={
                "subscriber_id": subscriber_id,
                "team_id": team_id,
                "protocol": PROTOCOL_VERSION,
            },
        ),
    )

    if last_event_id is not None:
        await _safe_send(
            websocket,
            Message(
                type=MessageType.EVENT,
                payload={"replay": True, "events": []},
            ),
        )

    receive_task = asyncio.create_task(_receive_loop(websocket, subscriber_id, bus))
    publish_task = asyncio.create_task(_publish_loop(websocket, subscriber, bus))
    heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket))

    try:
        done, pending = await asyncio.wait(
            {receive_task, publish_task, heartbeat_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            with contextlib.suppress(WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
                task.result()
    finally:
        for task in (receive_task, publish_task, heartbeat_task):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        await bus.unsubscribe(subscriber_id)
        with contextlib.suppress(RuntimeError, WebSocketDisconnect):
            await websocket.close()


async def _receive_loop(websocket: WebSocket, subscriber_id: str, bus: EventBus) -> None:
    """Read the frames sent by a client."""
    while True:
        raw = await websocket.receive_text()
        try:
            message = Message.from_json(raw)
        except ValueError:
            await _safe_send(
                websocket,
                Message(type=MessageType.ERROR, payload={"message": "Malformed frame"}),
            )
            continue
        await _handle_client_message(websocket, message, subscriber_id, bus)


async def _publish_loop(websocket: WebSocket, subscriber: object, bus: EventBus) -> None:
    """Forward the events of the bus to the client."""
    queue = subscriber.queue  # type: ignore[attr-defined]
    while True:
        event = await queue.get()
        await _safe_send(
            websocket,
            Message(type=MessageType.EVENT, payload=event),
        )


async def _heartbeat_loop(websocket: WebSocket) -> None:
    """Send a ping frame at a regular interval."""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        await _safe_send(websocket, Message(type=MessageType.PING, payload={}))


@router.get("/api/realtime/status", status_code=status.HTTP_200_OK)
async def realtime_status() -> dict[str, Any]:
    """Return the runtime counters of the realtime gateway."""
    bus = get_event_bus()
    publisher = get_publisher()
    snapshot = await bus.snapshot()
    return {
        "subscribers": snapshot["subscribers"],
        "published": snapshot["published"],
        "dropped": snapshot["dropped"],
        "heartbeat_seconds": HEARTBEAT_INTERVAL,
        "publisher_running": publisher._task is not None,
    }


@router.get("/api/realtime/replay", status_code=status.HTTP_200_OK)
async def realtime_replay(limit: int = 50) -> dict[str, Any]:
    """Return the events a reconnecting client should replay."""
    publisher = get_publisher()
    events = await publisher.replay(limit=max(1, min(limit, 200)))
    return {"events": list(events)}


def get_settings_dependency() -> Settings:
    """Return the resolved application settings."""
    return get_settings()


__all__ = ["EventPublisher", "router"]
