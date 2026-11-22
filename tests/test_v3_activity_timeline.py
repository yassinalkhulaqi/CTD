"""Tests for the V3 activity timeline feature.

The module exercises the pure domain helpers, the SQLite store, the service
rules and the mounted HTTP API against isolated databases.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import NotFoundError, ValidationError
from ctf_team_dashboard.features.activity_timeline import SCHEMA_SQL
from ctf_team_dashboard.features.activity_timeline.models import (
    DEFAULT_DEDUPE_WINDOW_SECONDS,
    Importance,
    TimelineEvent,
    TimelineFilter,
    TimelineKind,
    build_stats,
    build_timeline_groups,
    counts_by_hour,
    counts_by_importance,
    counts_by_kind,
    cutoff_for_age,
    day_key,
    day_label,
    deduplicate_events,
    encode_payload,
    group_by_day,
    group_by_hour,
    hour_key,
    hour_label,
    is_stale,
    relative_time,
    sort_clusters,
)
from ctf_team_dashboard.features.activity_timeline.service import TimelineService
from ctf_team_dashboard.features.activity_timeline.store import TimelineStore

TEAM_ID = "team-0001"
NOW = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)


def _event(
    event_id: str = "evt-0001",
    *,
    kind: str = "solve",
    actor_id: str = "member-0001",
    actor_name: str = "Ada Lovelace",
    summary: str = "Solved RSA challenge",
    importance: str = "normal",
    occurred_at: datetime | None = None,
    team_id: str = TEAM_ID,
    payload_json: str = '{"points":100}',
) -> TimelineEvent:
    """Build a timeline event with sensible defaults for tests."""
    return TimelineEvent(
        id=event_id,
        team_id=team_id,
        kind=kind,
        actor_id=actor_id,
        actor_name=actor_name,
        summary=summary,
        payload_json=payload_json,
        importance=importance,
        occurred_at=occurred_at or NOW,
    )


def _record(
    service: TimelineService,
    *,
    event_id: str = "",
    offset_minutes: int = 0,
    **overrides: object,
) -> TimelineEvent:
    """Persist a test event through the store with an explicit identifier."""
    template = _event(occurred_at=NOW - timedelta(minutes=offset_minutes))
    values: dict[str, object] = {
        "team_id": template.team_id,
        "kind": template.kind,
        "actor_id": template.actor_id,
        "actor_name": template.actor_name,
        "summary": template.summary,
        "importance": template.importance,
        "occurred_at": template.occurred_at,
    }
    values.update(overrides)
    event = TimelineEvent(
        id=event_id or f"evt-{offset_minutes:04d}",
        team_id=str(values["team_id"]),
        kind=str(values["kind"]),
        actor_id=str(values["actor_id"]),
        actor_name=str(values["actor_name"]),
        summary=str(values["summary"]),
        importance=str(values["importance"]),
        payload_json=encode_payload({"offset": offset_minutes}),
        occurred_at=values["occurred_at"],  # type: ignore[arg-type]
    )
    return service.store.events.insert(event)


# ----------------------------------------------------------------------
# Pure domain helpers
# ----------------------------------------------------------------------
def test_relative_time_formats_ranges() -> None:
    """Relative labels progress from seconds to absolute dates."""
    assert relative_time(NOW, NOW) == "just now"
    assert relative_time(NOW - timedelta(seconds=30), NOW) == "just now"
    assert relative_time(NOW - timedelta(minutes=3), NOW) == "3m ago"
    assert relative_time(NOW - timedelta(hours=4), NOW) == "4h ago"
    assert relative_time(NOW - timedelta(days=1), NOW) == "yesterday"
    assert relative_time(NOW - timedelta(days=3), NOW) == "3d ago"
    assert relative_time(NOW - timedelta(days=12), NOW) == "Dec 24"


def test_day_and_hour_bucket_helpers() -> None:
    """Keys and labels are stable and timezone aware."""
    moment = datetime(2026, 1, 5, 14, 37, tzinfo=timezone.utc)
    assert day_key(moment) == "2026-01-05"
    assert hour_key(moment) == "2026-01-05T14:00"
    assert hour_label(moment) == "14:00"
    assert day_label(moment, NOW) == "Today"
    assert day_label(moment - timedelta(days=1), NOW) == "Yesterday"
    assert day_label(moment - timedelta(days=5), NOW) == "Wed, Dec 31"


def test_enums_expose_labels_ranks_and_metadata() -> None:
    """Importance ranks and kind metadata support sorting and display."""
    assert [tier.rank for tier in Importance] == [0, 1, 2, 3]
    assert Importance.from_rank(99) is Importance.CRITICAL
    assert Importance.from_rank(-4) is Importance.LOW
    assert Importance.CRITICAL.tone == "danger"
    assert Importance.HIGH.is_urgent is True
    assert Importance.LOW.is_urgent is False
    assert TimelineKind.SOLVE.label == "Solve"
    assert TimelineKind.SOLVE.is_high_signal is True
    assert TimelineKind.SYSTEM.icon == "settings"
    assert len(TimelineKind.values()) == 9


def test_event_derived_properties() -> None:
    """Events expose parsed, display-ready metadata."""
    event = _event(importance="critical")
    assert event.timeline_kind is TimelineKind.SOLVE
    assert event.importance_level is Importance.CRITICAL
    assert event.importance_rank == 3
    assert event.is_critical is True
    assert event.payload == {"points": 100}
    assert event.actor_initials == "AL"
    assert event.date_key == "2026-01-05"
    assert event.hour_key == "2026-01-05T12:00"
    assert event.relative_label(NOW) == "just now"
    assert event.age_seconds(NOW) == 0.0
    assert encode_payload(None) == "{}"


def test_deduplicate_events_collapses_consecutive_matches() -> None:
    """Identical neighbouring events merge within the configured window."""
    first = _event("evt-1", occurred_at=NOW)
    second = _event("evt-2", occurred_at=NOW - timedelta(seconds=30))
    third = _event("evt-3", occurred_at=NOW - timedelta(minutes=10))
    different = _event("evt-4", summary="Another action", occurred_at=NOW - timedelta(minutes=12))
    clusters = deduplicate_events([first, second, third, different])
    assert [cluster.id for cluster in clusters] == ["evt-1", "evt-3", "evt-4"]
    assert [cluster.count for cluster in clusters] == [2, 1, 1]
    assert clusters[0].is_merged is True
    assert clusters[0].count_label == "×2"
    assert clusters[0].last_at == second.occurred_at
    narrow = deduplicate_events([first, second], window_seconds=5)
    assert [cluster.count for cluster in narrow] == [1, 1]
    assert deduplicate_events([], window_seconds=DEFAULT_DEDUPE_WINDOW_SECONDS) == ()
    assert [cluster.id for cluster in sort_clusters(clusters)] == [
        "evt-1",
        "evt-3",
        "evt-4",
    ]


def test_group_by_day_hour_and_hierarchy() -> None:
    """Events group into day buckets containing hourly children."""
    morning = _event("evt-1", occurred_at=NOW - timedelta(hours=2))
    same_hour = _event("evt-2", occurred_at=NOW - timedelta(minutes=30))
    other_day = _event("evt-3", occurred_at=NOW - timedelta(days=1))
    clusters = deduplicate_events([morning, same_hour, other_day])
    days = group_by_day(clusters)
    hours = group_by_hour(clusters)
    groups = build_timeline_groups(clusters, now=NOW)
    assert [day.key for day in days] == ["2026-01-05", "2026-01-04"]
    assert [hour.key for hour in hours] == [
        "2026-01-05T11:00",
        "2026-01-05T10:00",
        "2026-01-04T12:00",
    ]
    assert [group.key for group in groups] == ["2026-01-05", "2026-01-04"]
    assert [child.hour_of_day for child in groups[0].children] == [11, 10]
    assert groups[0].count == 2
    assert groups[0].label == "Today"
    assert groups[0].peak_importance is Importance.NORMAL
    assert groups[0].item_count == 0
    assert groups[1].children[0].item_count == 1


def test_aggregation_counts_and_prune_helpers() -> None:
    """Counters, rankings and cutoffs are pure and deterministic."""
    events = [
        _event("evt-1", kind="solve", importance="critical", occurred_at=NOW),
        _event("evt-2", kind="note", importance="low", occurred_at=NOW - timedelta(hours=1)),
        _event("evt-3", kind="solve", importance="normal", occurred_at=NOW - timedelta(hours=2)),
    ]
    assert counts_by_kind(events) == {"solve": 2, "note": 1}
    assert counts_by_importance(events) == {"critical": 1, "low": 1, "normal": 1}
    assert len(counts_by_hour(events)) == 3
    stats = build_stats(events, generated_at=NOW)
    assert stats.total == 3
    assert stats.unique_actors == 1
    assert stats.critical_count == 1
    assert stats.critical_ratio == 0.333
    assert stats.busiest_kind == "solve"
    assert stats.top_kinds(1) == (("solve", 2),)
    assert stats.average_per_hour == 1.0
    assert stats.last_seen == NOW
    cutoff = cutoff_for_age(7, now=NOW)
    assert cutoff == datetime(2025, 12, 29, 12, tzinfo=timezone.utc)
    assert is_stale(events[-1], cutoff) is False
    assert is_stale(events[-1], NOW) is True


def test_filter_matches_all_selection_criteria() -> None:
    """A filter applies kind, actor, team, importance and time constraints."""
    event = _event()
    assert TimelineFilter().matches(event) is True
    assert TimelineFilter(kinds=("solve",)).matches(event) is True
    assert TimelineFilter(kinds=("note",)).matches(event) is False
    assert TimelineFilter(actors=("member-0001",)).matches(event) is True
    assert TimelineFilter(actors=("member-0002",)).matches(event) is False
    assert TimelineFilter(team_id="team-0002").matches(event) is False
    assert TimelineFilter(importance=("critical",)).matches(event) is False
    assert TimelineFilter(from_at=NOW + timedelta(minutes=1)).matches(event) is False
    assert TimelineFilter(to_at=NOW - timedelta(minutes=1)).matches(event) is False
    assert TimelineFilter(team_id=TEAM_ID).is_empty is False
    assert TimelineFilter(limit=10).is_paginated is True
    assert TimelineFilter().with_offset(20).offset == 20
    assert TimelineFilter(kinds=("solve",)).normalised_kinds == (TimelineKind.SOLVE,)


# ----------------------------------------------------------------------
# Store layer
# ----------------------------------------------------------------------
def test_store_insert_query_count_and_delete(database: Database) -> None:
    """Events persist, filter by SQL and can be deleted by identifier."""
    store = TimelineStore(database)
    assert SCHEMA_SQL.count("CREATE TABLE") == 1
    first = _event("evt-a", occurred_at=NOW)
    second = _event(
        "evt-b", kind="note", actor_id="member-0002", occurred_at=NOW - timedelta(hours=1)
    )
    store.events.insert(first)
    store.events.insert(second)
    assert store.events.get("evt-a") == first
    assert store.events.get("missing") is None
    assert store.events.count_matching(TimelineFilter()) == 2
    assert store.events.count_matching(TimelineFilter(kinds=("note",))) == 1
    assert [item.id for item in store.events.matching(TimelineFilter(kinds=("solve",)))] == [
        "evt-a"
    ]
    assert [item.id for item in store.events.matching(TimelineFilter(), limit=1, offset=1)] == [
        "evt-b"
    ]
    assert [item.id for item in store.events.matching(TimelineFilter(team_id="other"))] == []
    assert store.events.delete("evt-a") is True
    assert store.events.delete("evt-a") is False
    assert store.events.count_matching(TimelineFilter()) == 1


def test_store_recent_prune_and_actor_aggregation(database: Database) -> None:
    """Store helpers support recency, age pruning and grouped actor stats."""
    store = TimelineStore(database)
    old = _event("evt-old", occurred_at=NOW - timedelta(days=40), importance="critical")
    recent = _event(
        "evt-new",
        occurred_at=NOW - timedelta(minutes=5),
        actor_id="member-0002",
        actor_name="Grace Hopper",
        kind="note",
    )
    store.events.insert(old)
    store.events.insert(recent)
    assert [item.id for item in store.events.recent(1)] == ["evt-new"]
    assert [item.id for item in store.events.list_since(NOW - timedelta(hours=1))] == ["evt-new"]
    assert store.events.count_since(NOW - timedelta(hours=1)) == 1
    assert store.events.distinct_kinds() == ("note", "solve")
    assert store.events.payload_fields("evt-new") == {"points": 100}
    assert store.events.payload_fields("missing") == {}
    actors = store.events.actor_summaries()
    assert [actor.actor_id for actor in actors] == ["member-0001", "member-0002"]
    assert actors[0].critical_count == 1
    assert actors[1].label == "Grace Hopper"
    assert actors[0].initials == "AL"
    assert store.events.delete_before(cutoff_for_age(30, now=NOW)) == 1
    assert store.events.count_matching(TimelineFilter()) == 1


# ----------------------------------------------------------------------
# Service layer
# ----------------------------------------------------------------------
def test_service_record_event_validates_input(database: Database) -> None:
    """The service rejects malformed events with typed validation errors."""
    service = TimelineService(TimelineStore(database))
    event = service.record_event(
        team_id=TEAM_ID,
        kind="solve",
        actor_id="member-0001",
        actor_name="Ada Lovelace",
        summary="  Solved   the  challenge  ",
        payload={"points": 250, "category": "crypto"},
        importance="high",
        occurred_at=NOW,
    )
    assert event.summary == "Solved the challenge"
    assert event.importance == "high"
    assert event.payload == {"category": "crypto", "points": 250}
    assert event.id.startswith("evt-")
    with pytest.raises(ValidationError, match="summary must not be empty"):
        service.record_event(
            team_id=TEAM_ID, kind="solve", actor_id="a", actor_name="A", summary="   "
        )
    with pytest.raises(ValidationError, match="Unknown timeline kind"):
        service.record_event(
            team_id=TEAM_ID, kind="unknown", actor_id="a", actor_name="A", summary="x"
        )
    with pytest.raises(ValidationError, match="Unknown importance"):
        service.record_event(
            team_id=TEAM_ID,
            kind="solve",
            actor_id="a",
            actor_name="A",
            summary="x",
            importance="urgent",
        )
    with pytest.raises(ValidationError, match="payload must be a JSON object"):
        service.record_event(
            team_id=TEAM_ID,
            kind="solve",
            actor_id="a",
            actor_name="A",
            summary="x",
            payload=["not", "a", "mapping"],  # type: ignore[arg-type]
        )


def test_service_query_filters_pagination_and_dedupe(database: Database) -> None:
    """Querying validates bounds, filters rows and paginates the result."""
    service = TimelineService(TimelineStore(database))
    for minute in (0, 1, 9):
        _record(service, event_id=f"evt-{minute}", offset_minutes=minute)
    _record(
        service,
        event_id="evt-note",
        offset_minutes=12,
        kind="note",
        actor_id="member-0002",
        importance="critical",
    )
    page = service.query(TimelineFilter(limit=2))
    assert len(page.clusters) == 1
    assert page.total == 4
    assert page.has_more is True
    assert page.next_offset == 2
    assert page.page_number == 1
    deduped = service.query(TimelineFilter(limit=10))
    assert deduped.total == 4
    assert len(deduped.clusters) == 3
    assert deduped.clusters[0].count == 2
    assert service.query(TimelineFilter(kinds=("note",))).total == 1
    assert service.query(TimelineFilter(actors=("member-0002",))).total == 1
    assert service.query(TimelineFilter(importance=("critical",))).total == 1
    assert service.query(TimelineFilter(team_id="other")).total == 0
    with pytest.raises(ValidationError, match="limit must be between"):
        service.query(TimelineFilter(limit=0))
    with pytest.raises(ValidationError, match="offset must not be negative"):
        service.query(TimelineFilter(offset=-1))
    with pytest.raises(ValidationError, match="from must not be later"):
        service.query(TimelineFilter(from_at=NOW, to_at=NOW - timedelta(hours=1)))


def test_service_groups_stats_actors_and_recent(database: Database) -> None:
    """Grouping, aggregation and actor listing agree on the stored events."""
    service = TimelineService(TimelineStore(database))
    _record(service, event_id="evt-1", offset_minutes=0, importance="critical")
    _record(service, event_id="evt-2", offset_minutes=1)
    _record(
        service,
        event_id="evt-3",
        offset_minutes=90,
        kind="note",
        actor_id="member-0002",
        actor_name="Grace Hopper",
    )
    groups = service.groups(now=NOW)
    assert [group.key for group in groups] == ["2026-01-05"]
    assert len(groups[0].children) == 2
    assert groups[0].critical_count == 1
    assert groups[0].peak_importance is Importance.CRITICAL
    stats = service.stats()
    assert stats.total == 3
    assert stats.by_kind == {"solve": 2, "note": 1}
    assert stats.critical_count == 1
    assert stats.unique_actors == 2
    assert stats.by_importance["critical"] == 1
    actors = service.list_actors()
    assert [actor.actor_id for actor in actors] == ["member-0001", "member-0002"]
    assert actors[0].event_count == 2
    assert service.list_kinds() == ("note", "solve")
    assert len(service.list_recent(3)) == 2
    assert len(service.list_recent(3, deduplicate=False)) == 3
    assert service.get_event("evt-1").id == "evt-1"


def test_service_prune_and_missing_events(database: Database) -> None:
    """Age based prune removes old rows and missing events raise errors."""
    service = TimelineService(TimelineStore(database))
    _record(service, event_id="evt-old", occurred_at=utcnow() - timedelta(days=60))
    _record(service, event_id="evt-new", occurred_at=utcnow() - timedelta(days=2))
    result = service.prune(30)
    assert result.deleted == 1
    assert result.retained == 1
    assert result.max_age_days == 30
    assert "Removed 1 event" in result.description
    with pytest.raises(ValidationError, match="max_age_days must be at least 1"):
        service.prune(0)
    preview = service.prune_for_team(TEAM_ID, 30)
    assert preview.deleted == 0
    assert preview.retained == 1
    with pytest.raises(NotFoundError, match="does not exist"):
        service.get_event("evt-old")
    with pytest.raises(NotFoundError, match="does not exist"):
        service.delete_event("evt-old")
    service.delete_event("evt-new")
    assert service.stats().total == 0


# ----------------------------------------------------------------------
# Router layer
# ----------------------------------------------------------------------
def test_router_create_and_list_events(client: TestClient) -> None:
    """The API creates events and returns typed derived fields."""
    created = client.post(
        "/api/timeline",
        json={
            "team_id": TEAM_ID,
            "kind": "solve",
            "actor_id": "member-0001",
            "actor_name": "Ada Lovelace",
            "summary": "Solved the RSA challenge",
            "payload": {"points": 100},
            "importance": "critical",
            "occurred_at": NOW.isoformat(),
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["id"].startswith("evt-")
    assert body["kind_label"] == "Solve"
    assert body["importance_tone"] == "danger"
    assert body["importance_rank"] == 3
    assert body["actor_initials"] == "AL"
    assert body["date_key"] == "2026-01-05"
    assert body["relative_label"] == "Jan 05"

    listing = client.get("/api/timeline")
    assert listing.status_code == 200
    page = listing.json()
    assert page["total"] == 1
    assert page["clusters"][0]["event"]["id"] == body["id"]
    assert page["has_more"] is False
    assert page["page_number"] == 1


def test_router_groups_stats_actors_and_kinds(client: TestClient) -> None:
    """Group, stats, actor and kind endpoints return the aggregated shapes."""
    for kind, importance in (("solve", "critical"), ("solve", "normal"), ("note", "low")):
        response = client.post(
            "/api/timeline",
            json={
                "team_id": TEAM_ID,
                "kind": kind,
                "actor_id": "member-0001",
                "actor_name": "Ada Lovelace",
                "summary": f"Recorded {kind}",
                "importance": importance,
                "occurred_at": NOW.isoformat(),
            },
        )
        assert response.status_code == 201

    groups = client.get("/api/timeline/groups")
    assert groups.status_code == 200
    payload = groups.json()
    assert len(payload) == 1
    assert payload[0]["level"] == "day"
    assert payload[0]["count"] == 3
    assert payload[0]["children"][0]["level"] == "hour"
    assert payload[0]["critical_count"] == 1
    assert payload[0]["children"][0]["events"][0]["count"] == 2

    stats = client.get("/api/timeline/stats").json()
    assert stats["total"] == 3
    assert stats["by_kind"] == {"solve": 2, "note": 1}
    assert stats["busiest_kind"] == "solve"
    assert stats["critical_count"] == 1
    assert stats["top_kinds"][0] == ["solve", 2]

    actors = client.get("/api/timeline/actors").json()
    assert len(actors) == 1
    assert actors[0]["label"] == "Ada Lovelace"
    assert actors[0]["event_count"] == 3
    assert actors[0]["first_kind"] == "solve"
    assert client.get("/api/timeline/kinds").json() == {
        "kinds": ["note", "solve"],
        "count": 2,
    }


def test_router_filters_pagination_get_and_delete(client: TestClient) -> None:
    """Query parameters narrow results and deletes remove individual events."""
    identifiers: list[str] = []
    for minute in (0, 1, 2, 3):
        response = client.post(
            "/api/timeline",
            json={
                "team_id": TEAM_ID,
                "kind": "solve" if minute < 3 else "note",
                "actor_id": "member-0001" if minute < 3 else "member-0002",
                "actor_name": "Ada Lovelace" if minute < 3 else "Grace Hopper",
                "summary": "Repeated action",
                "occurred_at": (NOW - timedelta(minutes=minute)).isoformat(),
            },
        )
        identifiers.append(response.json()["id"])

    page = client.get("/api/timeline", params={"limit": 2}).json()
    assert page["total"] == 4
    assert page["has_more"] is True
    assert page["next_offset"] == 2
    second = client.get("/api/timeline", params={"limit": 2, "offset": 2}).json()
    assert second["page_number"] == 2
    assert second["clusters"][0]["event"]["id"] != page["clusters"][0]["event"]["id"]

    by_kind = client.get("/api/timeline", params={"kinds": "note"}).json()
    assert by_kind["total"] == 1
    by_actor = client.get("/api/timeline", params={"actors": "member-0002"}).json()
    assert by_actor["total"] == 1
    by_team = client.get("/api/timeline", params={"team_id": "other"}).json()
    assert by_team["total"] == 0
    by_time = client.get(
        "/api/timeline",
        params={"from": NOW.isoformat(), "to": NOW.isoformat()},
    ).json()
    assert by_time["total"] == 1

    fetched = client.get(f"/api/timeline/{identifiers[0]}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == identifiers[0]
    deleted = client.delete(f"/api/timeline/{identifiers[0]}")
    assert deleted.status_code == 200
    assert deleted.json() == {"id": identifiers[0], "deleted": True}
    assert client.get(f"/api/timeline/{identifiers[0]}").status_code == 404
    assert client.get("/api/timeline").json()["total"] == 3


def test_router_validation_error_paths(client: TestClient) -> None:
    """Invalid requests map to the shared HTTP error envelope."""
    bad_kind = client.post(
        "/api/timeline",
        json={
            "team_id": TEAM_ID,
            "kind": "unknown",
            "actor_id": "member-0001",
            "actor_name": "Ada",
            "summary": "x",
        },
    )
    assert bad_kind.status_code == 422
    assert bad_kind.json()["error"]["code"] == "validation_error"

    empty_summary = client.post(
        "/api/timeline",
        json={
            "team_id": TEAM_ID,
            "kind": "solve",
            "actor_id": "member-0001",
            "actor_name": "Ada",
            "summary": "   ",
        },
    )
    assert empty_summary.status_code == 422
    assert empty_summary.json()["error"]["details"]["field"] == "summary"

    assert client.get("/api/timeline", params={"limit": 0}).status_code == 422
    assert client.get("/api/timeline", params={"offset": -1}).status_code == 422
    assert client.post("/api/timeline/prune", params={"max_age_days": 0}).status_code == 422
    window = client.get(
        "/api/timeline",
        params={"from": NOW.isoformat(), "to": (NOW - timedelta(days=1)).isoformat()},
    )
    assert window.status_code == 422
    assert window.json()["error"]["code"] == "validation_error"
    assert client.delete("/api/timeline/missing").status_code == 404


def test_router_prune_endpoint(client: TestClient) -> None:
    """The prune endpoint deletes stale events and reports the cutoff."""
    old = client.post(
        "/api/timeline",
        json={
            "team_id": TEAM_ID,
            "kind": "system",
            "actor_id": "system",
            "actor_name": "System",
            "summary": "Old activity",
            "occurred_at": (utcnow() - timedelta(days=90)).isoformat(),
        },
    )
    fresh = client.post(
        "/api/timeline",
        json={
            "team_id": TEAM_ID,
            "kind": "system",
            "actor_id": "system",
            "actor_name": "System",
            "summary": "Recent activity",
            "occurred_at": utcnow().isoformat(),
        },
    )
    result = client.post("/api/timeline/prune", params={"max_age_days": 30})
    assert result.status_code == 200
    body = result.json()
    assert body["deleted"] == 1
    assert body["retained"] == 1
    assert body["max_age_days"] == 30
    assert client.get(f"/api/timeline/{old.json()['id']}").status_code == 404
    assert client.get(f"/api/timeline/{fresh.json()['id']}").status_code == 200
