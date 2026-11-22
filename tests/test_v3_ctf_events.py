"""Tests for the CTF event lifecycle, registration and API surface."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.ctf_events.models import (
    CtfEvent,
    EventFormat,
    EventRegistration,
    EventStatus,
    RegistrationStatus,
    derive_event_status,
    format_countdown,
    intervals_overlap,
    normalise_tags,
    overlap_seconds,
    slugify,
)
from ctf_team_dashboard.features.ctf_events.service import EventFilters, EventService
from ctf_team_dashboard.repositories import Repositories


@pytest.fixture
def service(database: object) -> EventService:
    """Return an event service bound to the isolated test database."""
    return EventService()


@pytest.fixture
def window() -> tuple[datetime, datetime]:
    """Return an upcoming, two-day competition window."""
    start = datetime.now(timezone.utc) + timedelta(days=1)
    return start, start + timedelta(days=2)


def make_event(
    service: EventService,
    window: tuple[datetime, datetime],
    name: str = "Cyber Arena",
    **kwargs: object,
) -> CtfEvent:
    """Create an event through the service with sensible defaults."""
    return service.create_event(name, window[0], window[1], **kwargs)  # type: ignore[arg-type]


def team_ids(seeded: Repositories, count: int = 3) -> list[str]:
    """Return the first ``count`` seeded team identifiers."""
    return [team.id for team in seeded.teams.list_all()[:count]]


def test_slugify_and_normalise_tags() -> None:
    assert slugify("  Héllo CTF — Finals!  ") == "hello-ctf-finals"
    assert slugify("***") == "event"
    assert slugify("A" * 200) == "a" * 80
    assert normalise_tags([" Web ", "web", "", "CRYPTO"]) == ("web", "crypto")


def test_format_countdown() -> None:
    assert format_countdown(-5) == "00m 00s"
    assert format_countdown(0) == "00m 00s"
    assert format_countdown(9) == "00m 09s"
    assert format_countdown(729) == "12m 09s"
    assert format_countdown(3_600 * 5 + 60 * 32) == "05h 32m"
    assert format_countdown(86_400 * 2 + 3_600 * 4) == "02d 04h"


def test_derive_event_status_from_timestamps() -> None:
    start = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)
    end = datetime(2026, 6, 2, 12, tzinfo=timezone.utc)
    assert derive_event_status(EventStatus.DRAFT, start, end, start) is EventStatus.DRAFT
    assert derive_event_status(EventStatus.ARCHIVED, start, end, start) is EventStatus.ARCHIVED
    assert (
        derive_event_status(EventStatus.UPCOMING, start, end, start - timedelta(seconds=1))
        is EventStatus.UPCOMING
    )
    assert derive_event_status(EventStatus.UPCOMING, start, end, start) is EventStatus.LIVE
    assert (
        derive_event_status(EventStatus.UPCOMING, start, end, end - timedelta(seconds=1))
        is EventStatus.LIVE
    )
    assert derive_event_status(EventStatus.UPCOMING, start, end, end) is EventStatus.ARCHIVED


def test_event_countdown_and_progress() -> None:
    start = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)
    end = datetime(2026, 6, 2, 12, tzinfo=timezone.utc)
    event = CtfEvent(
        id="event-1",
        name="Window Test",
        slug="window-test",
        description="",
        format=EventFormat.JEOPARDY,
        starts_at=start,
        ends_at=end,
        status=EventStatus.UPCOMING,
    )
    assert event.status_at(start - timedelta(hours=1)) is EventStatus.UPCOMING
    assert event.countdown_seconds(start - timedelta(hours=1)) == 3_600
    assert event.countdown_label(start - timedelta(hours=1)) == "01h 00m"
    assert event.status_at(start + timedelta(hours=6)) is EventStatus.LIVE
    assert event.countdown_seconds(start + timedelta(hours=6)) == 64_800
    assert event.progress(start + timedelta(hours=6)) == 0.25
    assert event.countdown_seconds(end + timedelta(hours=1)) == 0
    assert event.status_at(end + timedelta(hours=1)) is EventStatus.ARCHIVED
    assert event.with_status(EventStatus.DRAFT).countdown_seconds(start) == 0
    assert event.overlaps_with(event) is True


def test_interval_overlap_helpers() -> None:
    first = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)
    first_end = datetime(2026, 6, 1, 18, tzinfo=timezone.utc)
    second = datetime(2026, 6, 1, 17, tzinfo=timezone.utc)
    second_end = datetime(2026, 6, 1, 20, tzinfo=timezone.utc)
    assert intervals_overlap(first, first_end, second, second_end) is True
    assert overlap_seconds(first, first_end, second, second_end) == 3_600
    assert intervals_overlap(first, first_end, first_end, second_end) is False
    assert overlap_seconds(first, first_end, first_end, second_end) == 0.0


def test_service_validates_name_window_status_and_capacity(
    service: EventService, window: tuple[datetime, datetime]
) -> None:
    with pytest.raises(ValidationError, match="at least 3 characters"):
        service.create_event("ab", window[0], window[1])
    with pytest.raises(ValidationError, match="end after it starts"):
        service.create_event("Bad Window", window[1], window[0])
    with pytest.raises(ValidationError, match="derived"):
        service.create_event("Bad Status", window[0], window[1], status=EventStatus.LIVE)
    with pytest.raises(ValidationError, match="Team capacity"):
        service.create_event("Bad Capacity", window[0], window[1], max_team_size=0)
    with pytest.raises(ValidationError, match="http"):
        service.create_event("Bad URL", window[0], window[1], website_url="example.com")
    assert service.validate_task_title("  Buy   flags ") == "Buy flags"
    with pytest.raises(ValidationError, match="must not be empty"):
        service.validate_task_title("   ")


def test_create_event_generates_unique_slugs(
    service: EventService, window: tuple[datetime, datetime]
) -> None:
    first = make_event(service, window, "Café CTF Finals")
    second = make_event(service, window, "Café CTF Finals")
    third = make_event(service, window, "Other", slug="cafe-ctf-finals")  # type: ignore[arg-type]
    assert first.slug == "cafe-ctf-finals"
    assert second.slug == "cafe-ctf-finals-2"
    assert third.slug == "cafe-ctf-finals-3"
    assert service.get_event_by_slug(first.slug).id == first.id
    with pytest.raises(NotFoundError, match="does not exist"):
        service.get_event("missing-id")


def test_store_crud_and_filtered_listing(
    service: EventService, window: tuple[datetime, datetime]
) -> None:
    jeopardy = make_event(
        service, window, "Jeopardy Cup", tags=["web", "crypto"], registration_open=True
    )
    attack = make_event(
        service,
        window,
        "Attack Shield",
        event_format=EventFormat.ATTACK_DEFENCE,
        registration_open=False,
    )
    draft = make_event(service, window, "Hidden Draft", status=EventStatus.DRAFT)
    assert len(service.list_events()) == 3
    attack_filter = EventFilters(format=EventFormat.ATTACK_DEFENCE)
    assert [event.id for event in service.list_events(attack_filter)] == [attack.id]
    assert [event.id for event in service.list_events(EventFilters(tag="web"))] == [jeopardy.id]
    assert [event.id for event in service.list_events(EventFilters(search="shield"))] == [attack.id]
    assert [event.id for event in service.list_events(EventFilters(window="draft"))] == [draft.id]
    assert [event.id for event in service.list_events(EventFilters(registration_open=False))] == [
        attack.id
    ]
    assert service._events.count_events(window="all") == 3

    updated = service.update_event(jeopardy.id, name="Renamed Cup", max_team_size=12)
    assert updated.name == "Renamed Cup"
    assert updated.slug == "renamed-cup"
    assert updated.max_team_size == 12
    archived = service.archive_event(attack.id)
    assert archived.status is EventStatus.ARCHIVED
    assert archived.derived_status is EventStatus.ARCHIVED
    service.delete_event(draft.id)
    with pytest.raises(NotFoundError):
        service.get_event(draft.id)


def test_registration_capacity_and_waitlist(
    service: EventService, seeded: Repositories, window: tuple[datetime, datetime]
) -> None:
    teams = team_ids(seeded)
    event = make_event(service, window, "Small Final", max_team_size=1)
    first = service.register(event.id, teams[0])
    second = service.register(event.id, teams[1])
    assert first.status is RegistrationStatus.CONFIRMED
    assert second.status is RegistrationStatus.WAITLISTED
    with pytest.raises(ConflictError, match="already registered"):
        service.register(event.id, teams[0])
    stats = service.stats(event.id)
    assert stats.confirmed == 1
    assert stats.waitlisted == 1
    assert stats.capacity_ratio == 1.0
    assert stats.is_full is True
    assert stats.available_slots == 0
    assert len(service.registrations(event.id)) == 2


def test_cancel_promotes_oldest_waitlisted_team(
    service: EventService, seeded: Repositories, window: tuple[datetime, datetime]
) -> None:
    teams = team_ids(seeded)
    event = make_event(service, window, "Promotion Final", max_team_size=1)
    service.register(event.id, teams[0])
    service.register(event.id, teams[1])
    service.register(event.id, teams[2])
    result = service.cancel(event.id, teams[0])
    assert result.registration.status is RegistrationStatus.CANCELLED
    assert result.promoted is not None
    assert result.promoted.team_id == teams[1]
    assert result.promoted.status is RegistrationStatus.CONFIRMED
    stats = service.stats(event.id)
    assert stats.confirmed == 1
    assert stats.cancelled == 1
    assert stats.promotions == 1
    again = service.cancel(event.id, teams[2])
    assert again.promoted is None
    assert again.promoted_team_id is None


def test_registration_rejects_closed_events_and_unknown_teams(
    service: EventService, seeded: Repositories, window: tuple[datetime, datetime]
) -> None:
    team = team_ids(seeded)[0]
    event = make_event(service, window, "Closed Doors", registration_open=False)
    with pytest.raises(ConflictError, match="closed"):
        service.register(event.id, team)
    with pytest.raises(NotFoundError, match="Team"):
        service.register(event.id, "missing-team")
    with pytest.raises(NotFoundError, match="no active registration"):
        service.cancel(event.id, team)
    open_event = make_event(service, window, "Open Doors")
    registration = service.register(open_event.id, team)
    service.cancel(open_event.id, team)
    assert registration.id
    re_registered = service.register(open_event.id, team)
    assert re_registered.status is RegistrationStatus.CONFIRMED


def test_overlap_detection_for_live_events(service: EventService, seeded: Repositories) -> None:
    now = datetime.now(timezone.utc)
    first = service.create_event("Live One", now - timedelta(hours=2), now + timedelta(hours=2))
    second = service.create_event("Live Two", now - timedelta(hours=1), now + timedelta(hours=3))
    detached = service.create_event("Later One", now + timedelta(days=2), now + timedelta(days=3))
    team = team_ids(seeded)[0]
    service.register(first.id, team)
    with pytest.raises(ConflictError, match="overlapping live event"):
        service.register(second.id, team)
    service.register(detached.id, team)
    overlaps = service.find_overlaps(team)
    assert len(overlaps) == 0
    service.register(second.id, team_ids(seeded)[1])
    assert service.find_overlaps(team_ids(seeded)[1]) == []
    service._registrations.create(
        EventRegistration(
            id="reg-forced",
            event_id=second.id,
            team_id=team,
            status=RegistrationStatus.CONFIRMED,
        )
    )
    assert len(service.find_overlaps(team)) == 1
    assert len(service.live_events()) >= 2


def test_registration_stats_and_waitlist_pressure(
    service: EventService, seeded: Repositories, window: tuple[datetime, datetime]
) -> None:
    teams = team_ids(seeded)
    event = make_event(service, window, "Stats Final", max_team_size=2)
    service.register(event.id, teams[0])
    service.register(event.id, teams[1])
    service.register(event.id, teams[2])
    stats = service.stats(event.id)
    assert stats.capacity == 2
    assert stats.confirmed == 2
    assert stats.waitlisted == 1
    assert stats.total == 3
    assert stats.capacity_ratio == 1.0
    assert stats.fill_percentage == 100
    assert stats.waitlist_pressure == 0.5


def test_task_lifecycle(service: EventService, window: tuple[datetime, datetime]) -> None:
    event = make_event(service, window, "Checklist Final")
    due = datetime.now(timezone.utc) - timedelta(hours=1)
    task = service.add_task(event.id, "  Book the room  ", due_at=due)
    assert task.title == "Book the room"
    assert task.is_overdue() is True
    second = service.add_task(event.id, "Print badges")
    toggled = service.toggle_task(event.id, task.id)
    assert toggled.done is True
    assert toggled.is_overdue() is False
    assert service.task_progress(event.id) == (1, 2)
    assert [item.id for item in service.tasks(event.id)] == [second.id, task.id]
    service.delete_task(event.id, second.id)
    with pytest.raises(NotFoundError, match="does not belong"):
        service.toggle_task(event.id, second.id)


def test_router_event_crud(client: TestClient, window: tuple[datetime, datetime]) -> None:
    payload = {
        "name": "Router Arena",
        "starts_at": window[0].isoformat(),
        "ends_at": window[1].isoformat(),
        "description": "A routed event",
        "tags": ["web", "misc"],
        "max_team_size": 6,
    }
    created = client.post("/api/events", json=payload)
    assert created.status_code == 201
    body = created.json()
    event_id = body["id"]
    assert body["slug"] == "router-arena"
    assert body["status"] == "upcoming"
    assert body["countdown_seconds"] > 0

    listed = client.get("/api/events")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    detail = client.get(f"/api/events/{event_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Router Arena"

    patched = client.patch(f"/api/events/{event_id}", json={"name": "Renamed Arena"})
    assert patched.status_code == 200
    assert patched.json()["slug"] == "renamed-arena"

    filtered = client.get("/api/events", params={"tag": "web", "window": "upcoming"})
    assert filtered.status_code == 200
    assert any(item["id"] == event_id for item in filtered.json()["events"])

    deleted = client.delete(f"/api/events/{event_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/events/{event_id}").status_code == 404


def test_router_registration_flow(
    client: TestClient, seeded: Repositories, window: tuple[datetime, datetime]
) -> None:
    teams = team_ids(seeded)
    event = client.post(
        "/api/events",
        json={
            "name": "Router Final",
            "starts_at": window[0].isoformat(),
            "ends_at": window[1].isoformat(),
            "max_team_size": 1,
        },
    ).json()
    event_id = event["id"]

    first = client.post(f"/api/events/{event_id}/register", json={"team_id": teams[0]})
    assert first.status_code == 201
    assert first.json()["status"] == "confirmed"
    second = client.post(f"/api/events/{event_id}/register", json={"team_id": teams[1]})
    assert second.json()["status"] == "waitlisted"

    ledger = client.get(f"/api/events/{event_id}/registrations")
    assert ledger.status_code == 200
    assert ledger.json()["confirmed"] == 1
    assert len(ledger.json()["registrations"]) == 2

    stats = client.get(f"/api/events/{event_id}/stats")
    assert stats.status_code == 200
    assert stats.json()["capacity_ratio"] == 1.0

    cancelled = client.post(f"/api/events/{event_id}/cancel", json={"team_id": teams[0]})
    assert cancelled.status_code == 200
    assert cancelled.json()["promoted_team_id"] == teams[1]
    assert cancelled.json()["promotion"]["status"] == "confirmed"
    assert client.get(f"/api/events/{event_id}/stats").json()["promotions"] == 1


def test_router_upcoming_live_and_filters(
    client: TestClient, window: tuple[datetime, datetime]
) -> None:
    now = datetime.now(timezone.utc)
    client.post(
        "/api/events",
        json={
            "name": "Future Cup",
            "starts_at": window[0].isoformat(),
            "ends_at": window[1].isoformat(),
        },
    )
    client.post(
        "/api/events",
        json={
            "name": "Current Cup",
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    upcoming = client.get("/api/events/upcoming")
    assert upcoming.status_code == 200
    assert upcoming.json()["window"] == "upcoming"
    assert any(item["name"] == "Future Cup" for item in upcoming.json()["events"])
    live = client.get("/api/events/live")
    assert any(item["name"] == "Current Cup" for item in live.json()["events"])
    filtered = client.get("/api/events", params={"status": "upcoming"})
    assert filtered.status_code == 200
    assert all(item["stored_status"] == "upcoming" for item in filtered.json()["events"])
    assert client.get("/api/events", params={"window": "bogus"}).status_code == 422


def test_router_tasks_and_team_overlaps(
    client: TestClient, seeded: Repositories, window: tuple[datetime, datetime]
) -> None:
    event = client.post(
        "/api/events",
        json={
            "name": "Task Final",
            "starts_at": window[0].isoformat(),
            "ends_at": window[1].isoformat(),
        },
    ).json()
    event_id = event["id"]
    created = client.post(f"/api/events/{event_id}/tasks", json={"title": "Pack gear"})
    assert created.status_code == 201
    task_id = created.json()["id"]
    tasks = client.get(f"/api/events/{event_id}/tasks")
    assert len(tasks.json()) == 1
    toggled = client.post(f"/api/events/{event_id}/tasks/{task_id}/toggle")
    assert toggled.json()["done"] is True
    overlaps = client.get("/api/events/overlaps", params={"team_id": team_ids(seeded)[0]})
    assert overlaps.status_code == 200
    assert overlaps.json()["overlaps"] == []


def test_router_validation_and_error_paths(
    client: TestClient, seeded: Repositories, window: tuple[datetime, datetime]
) -> None:
    bad = client.post(
        "/api/events",
        json={
            "name": "Broken Window",
            "starts_at": window[1].isoformat(),
            "ends_at": window[0].isoformat(),
        },
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "validation_error"

    live = client.post(
        "/api/events",
        json={
            "name": "Forced Live",
            "starts_at": window[0].isoformat(),
            "ends_at": window[1].isoformat(),
            "status": "live",
        },
    )
    assert live.status_code == 422

    missing = client.get("/api/events/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"

    event = client.post(
        "/api/events",
        json={
            "name": "Conflict Final",
            "starts_at": window[0].isoformat(),
            "ends_at": window[1].isoformat(),
        },
    ).json()
    team = team_ids(seeded)[0]
    assert (
        client.post(f"/api/events/{event['id']}/register", json={"team_id": team}).status_code
        == 201
    )
    duplicate = client.post(f"/api/events/{event['id']}/register", json={"team_id": team})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"
