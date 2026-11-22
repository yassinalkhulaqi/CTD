"""Tests for the notification centre feature."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.notifications.models import (
    Channel,
    DigestEntry,
    DigestPeriod,
    Notification,
    NotificationKind,
    NotificationPreference,
    NotificationQuery,
    NotificationStats,
    QuietHours,
    RetentionPolicy,
    Severity,
    build_digest,
    count_unread,
    decode_entries,
    effective_preferences,
    encode_entries,
    evaluate_delivery,
    group_digest_entries,
    lookup_preference,
    render_template,
    severity_order,
    sort_notifications,
    template_variables,
)
from ctf_team_dashboard.features.notifications.service import (
    NotificationService,
    delivery_reasons,
)
from ctf_team_dashboard.features.notifications.store import (
    DigestRepository,
    NotificationRepository,
    PreferenceRepository,
)

RECIPIENT = "member-1"


def make_notification(
    notification_id: str,
    *,
    kind: NotificationKind = NotificationKind.SOLVE,
    severity: Severity = Severity.INFO,
    channel: Channel = Channel.IN_APP,
    created_at: datetime | None = None,
    read_at: datetime | None = None,
) -> Notification:
    """Build a notification fixture with sensible defaults."""
    return Notification(
        id=notification_id,
        recipient_id=RECIPIENT,
        channel=channel,
        kind=kind,
        title=f"Title {notification_id}",
        body=f"Body {notification_id}",
        severity=severity,
        read_at=read_at,
        created_at=created_at or utcnow(),
        action_url=f"/challenges/{notification_id}",
    )


# ----------------------------------------------------------------------
# Pure domain rules
# ----------------------------------------------------------------------
def test_severity_ordering_and_urgency() -> None:
    """Severities are ordered with critical first and urgent flags set."""
    assert severity_order() == (Severity.CRITICAL, Severity.WARNING, Severity.INFO)
    assert Severity.CRITICAL.rank == 2
    assert Severity.INFO.is_urgent is False
    assert Severity.WARNING.is_urgent is True
    assert Severity.CRITICAL.accent.startswith("var(--")


def test_quiet_hours_plain_and_windows() -> None:
    """Quiet windows handle normal and overnight ranges."""
    day = QuietHours(9, 17)
    assert day.contains(datetime(2026, 1, 1, 10, tzinfo=timezone.utc))
    assert not day.contains(datetime(2026, 1, 1, 18, tzinfo=timezone.utc))
    night = QuietHours(22, 6)
    assert night.contains(datetime(2026, 1, 1, 23, tzinfo=timezone.utc))
    assert night.contains(datetime(2026, 1, 1, 2, tzinfo=timezone.utc))
    assert not night.contains(datetime(2026, 1, 1, 12, tzinfo=timezone.utc))
    assert night.next_open_hour(datetime(2026, 1, 1, 23, tzinfo=timezone.utc)) == 6
    assert QuietHours(0, 0).contains(utcnow()) is False
    assert "No quiet hours" in QuietHours(0, 0).describe()
    assert "22:00" in night.describe()


def test_template_substitution_and_variables() -> None:
    """Templates resolve nested variables and keep unknown placeholders."""
    template = "Solved {{ challenge.name }} for {{ points }} by {{ actor.name }}"
    rendered = render_template(
        template,
        {"challenge": {"name": "Warmup"}, "points": 250, "missing": "x"},
    )
    assert rendered == "Solved Warmup for 250 by {{ actor.name }}"
    assert template_variables(template) == ("challenge.name", "points", "actor.name")
    assert render_template("{{ flag }}", {"flag": None}) == ""
    assert render_template("{{ ok }}", {"ok": True}) == "yes"


def test_preference_suppression_and_critical_override() -> None:
    """Disabled channels suppress messages while critical alerts break through."""
    preference = NotificationPreference(
        recipient_id=RECIPIENT,
        channel=Channel.EMAIL,
        kind=NotificationKind.SOLVE,
        enabled=False,
    )
    notice = make_notification("a", severity=Severity.WARNING, channel=Channel.EMAIL)
    critical = make_notification("b", severity=Severity.CRITICAL, channel=Channel.EMAIL)
    assert preference.accepts(notice) is False
    assert preference.accepts(critical) is False
    assert evaluate_delivery(preference, notice).reason == "channel_disabled"
    enabled = preference.with_enabled(True).with_quiet_hours(0, 23)
    assert evaluate_delivery(enabled, critical).reason == "critical_override"
    assert preference.with_enabled(True).enabled is True
    assert preference.with_quiet_hours(22, 6).quiet_end_hour == 6


def test_preference_validation() -> None:
    """Out-of-range quiet hours are rejected with a typed error."""
    with pytest.raises(ValidationError):
        NotificationPreference(
            recipient_id=RECIPIENT,
            channel=Channel.IN_APP,
            kind=NotificationKind.SYSTEM,
            quiet_start_hour=24,
        )
    with pytest.raises(ValidationError):
        RetentionPolicy(max_age_days=0)


def test_lookup_preference_precedence() -> None:
    """Exact rules beat wildcard rules, which beat implicit defaults."""
    exact = NotificationPreference(RECIPIENT, Channel.IN_APP, NotificationKind.SOLVE, enabled=False)
    wildcard = NotificationPreference(RECIPIENT, Channel.IN_APP, NotificationKind.ANY, enabled=True)
    other = NotificationPreference("other", Channel.EMAIL, NotificationKind.SOLVE)
    assert (
        lookup_preference(
            [other, wildcard, exact],
            RECIPIENT,
            Channel.IN_APP,
            NotificationKind.SOLVE,
        )
        is exact
    )
    assert (
        lookup_preference([wildcard], RECIPIENT, Channel.IN_APP, NotificationKind.TEAM) is wildcard
    )
    fallback = lookup_preference([], RECIPIENT, Channel.EMAIL, NotificationKind.SYSTEM)
    assert fallback.enabled is True
    assert fallback.quiet_hours.active is False


def test_effective_preferences_matrix() -> None:
    """The effective matrix covers every non-wildcard channel and kind pair."""
    stored = [
        NotificationPreference(RECIPIENT, Channel.EMAIL, NotificationKind.ANY, enabled=False),
        NotificationPreference(RECIPIENT, Channel.EMAIL, NotificationKind.SECURITY, enabled=True),
    ]
    matrix = effective_preferences(stored, RECIPIENT)
    assert len(matrix) == len(Channel) * (len(NotificationKind) - 1)
    assert all(item.recipient_id == RECIPIENT for item in matrix)
    assert all(item.kind is not NotificationKind.ANY for item in matrix)
    security = [item for item in matrix if item.kind is NotificationKind.SECURITY]
    assert any(item.channel is Channel.EMAIL and item.enabled for item in security)
    email_solve = [
        item
        for item in matrix
        if item.channel is Channel.EMAIL and item.kind is NotificationKind.SOLVE
    ]
    assert email_solve[0].enabled is False


def test_notification_read_state_sorting_and_query() -> None:
    """Derived state, severity ordering and filters work without persistence."""
    older = make_notification(
        "old",
        severity=Severity.CRITICAL,
        created_at=utcnow() - timedelta(days=1),
    )
    newer = make_notification("new", severity=Severity.INFO)
    assert older.is_unread
    assert not older.is_read
    assert older.mark_read().is_read
    assert older.mark_read().read_at is not None
    assert count_unread([older, newer]) == 2
    assert sort_notifications((newer, older))[0].id == "old"
    query = NotificationQuery(
        recipient_id=RECIPIENT,
        severity=Severity.INFO,
        unread_only=True,
        search="body new",
    )
    assert [item.id for item in query.apply([older, newer])] == ["new"]
    assert "solve" in newer.label
    assert newer.age_seconds >= 0


def test_digest_grouping_and_rendering() -> None:
    """Digest entries group by kind and severity and render as markdown."""
    first = make_notification("a", severity=Severity.CRITICAL, kind=NotificationKind.SECURITY)
    second = make_notification("b", severity=Severity.CRITICAL, kind=NotificationKind.SECURITY)
    third = make_notification("c", severity=Severity.INFO, kind=NotificationKind.SOLVE)
    digest = build_digest("dgt-1", RECIPIENT, DigestPeriod.DAILY, [first, second, third])
    assert digest.total == 3
    assert [group.severity for group in digest.groups] == [
        Severity.CRITICAL,
        Severity.INFO,
    ]
    assert digest.groups[0].count == 2
    assert "Critical security" in digest.render_markdown()
    encoded = encode_entries(digest.entries)
    assert {entry.notification_id for entry in decode_entries(encoded)} == {
        "a",
        "b",
        "c",
    }
    assert decode_entries("not json") == ()
    assert digest.mark_sent().is_sent


def test_retention_pruning() -> None:
    """Only old, read notifications are pruned by default."""
    old = utcnow() - timedelta(days=40)
    expired_read = make_notification("expired", created_at=old, read_at=utcnow())
    expired_unread = make_notification("unread", created_at=old)
    fresh = make_notification("fresh")
    policy = RetentionPolicy(max_age_days=30)
    kept, removed = policy.prune([expired_read, expired_unread, fresh])
    assert [item.id for item in removed] == ["expired"]
    assert [item.id for item in kept] == ["unread", "fresh"]
    aggressive = RetentionPolicy(max_age_days=30, keep_unread=False)
    assert aggressive.is_expired(expired_unread) is True
    assert DigestPeriod.WEEKLY.window == timedelta(days=7)


def test_stats_aggregation() -> None:
    """Stats count unread and critical items by each dimension."""
    items = [
        make_notification("a", severity=Severity.CRITICAL, channel=Channel.EMAIL),
        make_notification("b", severity=Severity.INFO, read_at=utcnow()),
    ]
    aggregated = NotificationStats.from_notifications(items)
    assert aggregated.total == 2
    assert aggregated.unread == 1
    assert aggregated.critical_unread == 1
    assert aggregated.by_channel["email"] == 1
    assert aggregated.read_rate == 0.5
    assert aggregated.to_dict()["read"] == 1


# ----------------------------------------------------------------------
# Store layer
# ----------------------------------------------------------------------
def test_notification_store_crud(database: Database) -> None:
    """The store persists notifications and reports filtered counts."""
    repository = NotificationRepository(database)
    notice = repository.create(make_notification("store-1"))
    assert repository.get("store-1") is not None
    assert repository.count_filtered(recipient_id=RECIPIENT, unread_only=True) == 1
    assert repository.unread_count(RECIPIENT) == 1
    assert repository.list_filtered(severity=Severity.INFO)[0].id == notice.id
    repository.mark_read("store-1", utcnow())
    assert repository.unread_count(RECIPIENT) == 0
    assert repository.delete("store-1") is True
    assert repository.delete("store-1") is False


def test_preference_store_upsert(database: Database) -> None:
    """Preferences are keyed by recipient, channel and kind."""
    repository = PreferenceRepository(database)
    preference = NotificationPreference(
        RECIPIENT, Channel.EMAIL, NotificationKind.TEAM, enabled=False
    )
    repository.upsert(preference)
    repository.upsert(preference.with_quiet_hours(23, 7))
    rows = repository.list_for_recipient(RECIPIENT)
    assert len(rows) == 1
    assert rows[0].quiet_start_hour == 23
    assert repository.get(RECIPIENT, Channel.EMAIL, NotificationKind.TEAM) is not None
    assert repository.delete(RECIPIENT, Channel.EMAIL, NotificationKind.TEAM) is True


def test_digest_store_crud(database: Database) -> None:
    """Digests persist their encoded entries and sent timestamp."""
    repository = DigestRepository(database)
    digest = build_digest(
        "dgt-store",
        RECIPIENT,
        DigestPeriod.DAILY,
        [make_notification("entry-1")],
    )
    repository.create(digest)
    assert repository.get("dgt-store") is not None
    assert repository.list_for_recipient(RECIPIENT)[0].total == 1
    assert len(repository.list_unsent()) == 1
    repository.mark_sent("dgt-store", utcnow())
    assert repository.list_unsent() == []
    assert repository.delete("dgt-store") is True


# ----------------------------------------------------------------------
# Service layer
# ----------------------------------------------------------------------
def test_create_respects_disabled_preference(database: Database) -> None:
    """A disabled channel still stores the message but suppresses delivery."""
    service = NotificationService()
    service.upsert_preference(
        recipient_id=RECIPIENT,
        channel=Channel.EMAIL,
        kind=NotificationKind.SOLVE,
        enabled=False,
    )
    result = service.create(
        recipient_id=RECIPIENT,
        channel=Channel.EMAIL,
        kind=NotificationKind.SOLVE,
        title="Solved",
        body="Flag captured",
    )
    assert result.delivered is False
    assert result.decision.reason == "channel_disabled"
    assert service.get(result.notification.id).body == "Flag captured"
    assert delivery_reasons([result.decision])["channel_disabled"] == 1


def test_create_quiet_hours_and_critical_override(database: Database) -> None:
    """Quiet hours defer regular messages but not critical ones."""
    service = NotificationService()
    service.upsert_preference(
        recipient_id=RECIPIENT,
        channel=Channel.IN_APP,
        kind=NotificationKind.SYSTEM,
        quiet_start_hour=0,
        quiet_end_hour=23,
    )
    night = datetime(2026, 1, 1, 4, tzinfo=timezone.utc)
    normal = service.create(
        recipient_id=RECIPIENT,
        channel=Channel.IN_APP,
        kind=NotificationKind.SYSTEM,
        title="Maintenance",
        body="Scheduled work",
        moment=night,
    )
    critical = service.create(
        recipient_id=RECIPIENT,
        channel=Channel.IN_APP,
        kind=NotificationKind.SYSTEM,
        title="Breach",
        body="Investigate now",
        severity=Severity.CRITICAL,
        moment=night,
    )
    assert normal.decision.reason == "quiet_hours"
    assert normal.decision.suppressed_until_hour == 23
    assert critical.delivered is True


def test_create_templates_body(database: Database) -> None:
    """Template variables are substituted when a notification is created."""
    service = NotificationService()
    result = service.create(
        recipient_id=RECIPIENT,
        channel=Channel.IN_APP,
        kind=NotificationKind.CHALLENGE,
        title="New challenge",
        body="Challenge {{ name }} worth {{ points }} pts",
        variables={"name": "RSA Warmup", "points": 100},
    )
    assert result.notification.body == "Challenge RSA Warmup worth 100 pts"


def test_create_validation_errors(database: Database) -> None:
    """Blank content is rejected before anything is stored."""
    service = NotificationService()
    with pytest.raises(ValidationError):
        service.create(
            recipient_id="",
            channel=Channel.IN_APP,
            kind=NotificationKind.SYSTEM,
            title="x",
            body="x",
        )
    with pytest.raises(ValidationError):
        service.create(
            recipient_id=RECIPIENT,
            channel=Channel.IN_APP,
            kind=NotificationKind.SYSTEM,
            title=" ",
            body="x",
        )
    assert service.stats().total == 0


def test_mark_read_flows(database: Database) -> None:
    """Single and bulk reads are idempotent and update unread counters."""
    service = NotificationService()
    first = service.create(
        recipient_id=RECIPIENT,
        channel=Channel.IN_APP,
        kind=NotificationKind.SYSTEM,
        title="One",
        body="One",
    ).notification
    service.create(
        recipient_id=RECIPIENT,
        channel=Channel.IN_APP,
        kind=NotificationKind.SYSTEM,
        title="Two",
        body="Two",
    )
    assert service.unread_count(RECIPIENT) == 2
    assert service.mark_read(first.id).is_read
    assert service.mark_read(first.id).is_read
    assert service.unread_count(RECIPIENT) == 1
    assert service.mark_all_read(RECIPIENT) == 1
    assert service.unread_count(RECIPIENT) == 0
    with pytest.raises(NotFoundError):
        service.mark_read("missing")
    with pytest.raises(ValidationError):
        service.mark_all_read("")


def test_digest_build_and_send(database: Database) -> None:
    """Digests group recent messages and cannot be sent twice."""
    service = NotificationService()
    service.create(
        recipient_id=RECIPIENT,
        channel=Channel.IN_APP,
        kind=NotificationKind.SOLVE,
        title="Solved A",
        body="A",
        created_at=utcnow() - timedelta(hours=2),
    )
    service.create(
        recipient_id="other",
        channel=Channel.IN_APP,
        kind=NotificationKind.SYSTEM,
        title="Other",
        body="B",
    )
    preview = service.preview_digest(RECIPIENT, DigestPeriod.DAILY)
    assert preview.total == 1
    digest = service.build_digest(RECIPIENT, DigestPeriod.DAILY)
    assert digest.total == 1
    assert service.get_digest(digest.id).is_sent is False
    sent = service.send_digest(digest.id)
    assert sent.is_sent is True
    with pytest.raises(ConflictError):
        service.send_digest(digest.id)
    with pytest.raises(NotFoundError):
        service.get_digest("nope")
    assert len(service.list_digests(RECIPIENT)) == 1


def test_prune_and_stats(database: Database) -> None:
    """Pruning removes old read rows and stats aggregate the remainder."""
    service = NotificationService()
    service.create(
        recipient_id=RECIPIENT,
        channel=Channel.EMAIL,
        kind=NotificationKind.SYSTEM,
        title="Old",
        body="Old",
        created_at=utcnow() - timedelta(days=90),
    )
    service.mark_all_read(RECIPIENT)
    service.create(
        recipient_id=RECIPIENT,
        channel=Channel.IN_APP,
        kind=NotificationKind.SECURITY,
        title="New",
        body="New",
        severity=Severity.CRITICAL,
    )
    assert service.stale_count() == 1
    assert service.prune() == 1
    assert service.stats(RECIPIENT).total == 1
    assert service.stats(RECIPIENT).critical_unread == 1
    assert service.stats("nobody").total == 0


def test_preference_service_flows(database: Database) -> None:
    """Preference lookups fall back to defaults and delete restores them."""
    service = NotificationService()
    assert len(service.effective_preferences(RECIPIENT)) == 15
    assert service.lookup_preference(RECIPIENT, Channel.EMAIL, NotificationKind.SOLVE).enabled
    service.upsert_preference(
        recipient_id=RECIPIENT,
        channel=Channel.EMAIL,
        kind=NotificationKind.ANY,
        enabled=False,
    )
    assert not service.lookup_preference(RECIPIENT, Channel.EMAIL, NotificationKind.SOLVE).enabled
    service.delete_preference(RECIPIENT, Channel.EMAIL, NotificationKind.ANY)
    assert service.lookup_preference(RECIPIENT, Channel.EMAIL, NotificationKind.SOLVE).enabled
    with pytest.raises(NotFoundError):
        service.delete_preference(RECIPIENT, Channel.WEBHOOK, NotificationKind.TEAM)


# ----------------------------------------------------------------------
# Router layer
# ----------------------------------------------------------------------
def test_router_list_and_create(client: TestClient) -> None:
    """The list and create endpoints exchange typed payloads."""
    created = client.post(
        "/api/notifications",
        json={
            "recipient_id": "api-1",
            "channel": "in_app",
            "kind": "solve",
            "title": "Flag in",
            "body": "Solved {{ challenge }}",
            "variables": {"challenge": "Warmup"},
            "severity": "warning",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["delivered"] is True
    assert payload["notification"]["body"] == "Solved Warmup"
    assert payload["notification"]["severity_rank"] == 1
    listing = client.get("/api/notifications", params={"recipient_id": "api-1"})
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["unread"] == 1
    filtered = client.get(
        "/api/notifications",
        params={"recipient_id": "api-1", "severity": "critical"},
    )
    assert filtered.json()["total"] == 0


def test_router_read_endpoints(client: TestClient) -> None:
    """Single and bulk mark-read endpoints update counters."""
    first = client.post(
        "/api/notifications",
        json={
            "recipient_id": "api-2",
            "channel": "in_app",
            "kind": "system",
            "title": "A",
            "body": "A",
        },
    ).json()["notification"]["id"]
    second = client.post(
        "/api/notifications",
        json={
            "recipient_id": "api-2",
            "channel": "email",
            "kind": "team",
            "title": "B",
            "body": "B",
        },
    ).json()["notification"]["id"]
    read = client.post(f"/api/notifications/{first}/read")
    assert read.status_code == 200
    assert read.json()["is_read"] is True
    bulk = client.post("/api/notifications/read-all", json={"recipient_id": "api-2"})
    assert bulk.json()["modified"] == 1
    assert bulk.json()["unread"] == 0
    assert client.post(f"/api/notifications/{second}/read").json()["is_read"] is True
    assert client.post("/api/notifications/missing/read").status_code == 404


def test_router_preference_endpoints(client: TestClient) -> None:
    """Preference endpoints expose the complete matrix and upsert rows."""
    updated = client.put(
        "/api/notifications/preferences",
        json={
            "recipient_id": "api-3",
            "channel": "email",
            "kind": "security",
            "enabled": False,
            "quiet_start_hour": 22,
            "quiet_end_hour": 6,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["quiet_start_hour"] == 22
    listing = client.get("/api/notifications/preferences", params={"recipient_id": "api-3"})
    assert listing.status_code == 200
    assert len(listing.json()["preferences"]) == 15
    security = [
        item
        for item in listing.json()["preferences"]
        if item["channel"] == "email" and item["kind"] == "security"
    ]
    assert security[0]["enabled"] is False
    invalid = client.put(
        "/api/notifications/preferences",
        json={
            "recipient_id": "api-3",
            "channel": "email",
            "kind": "security",
            "quiet_start_hour": 48,
        },
    )
    assert invalid.status_code == 422


def test_router_digest_and_stats(client: TestClient) -> None:
    """Digest previews, sends, stats and pruning are reachable over HTTP."""
    client.post(
        "/api/notifications",
        json={
            "recipient_id": "api-4",
            "channel": "in_app",
            "kind": "challenge",
            "title": "Released",
            "body": "New challenge",
        },
    )
    preview = client.get(
        "/api/notifications/digest",
        params={"recipient_id": "api-4", "period": "daily"},
    )
    assert preview.status_code == 200
    assert preview.json()["total"] == 1
    assert preview.json()["groups"][0]["kind"] == "challenge"
    assert "# Past day digest" in preview.json()["markdown"]
    stats = client.get("/api/notifications/stats", params={"recipient_id": "api-4"})
    assert stats.json()["unread"] == 1
    assert stats.json()["by_kind"]["challenge"] == 1
    pruned = client.post(
        "/api/notifications/prune",
        json={"max_age_days": 1, "keep_unread": True},
    )
    assert pruned.status_code == 200
    assert pruned.json()["removed"] == 0


def test_router_send_digest_flow(client: TestClient) -> None:
    """A digest can be sent once through the API."""
    from ctf_team_dashboard.features.notifications.service import NotificationService

    service = NotificationService()
    service.create(
        recipient_id="api-5",
        channel=Channel.EMAIL,
        kind=NotificationKind.TEAM,
        title="Hello",
        body="Hello",
    )
    digest = service.build_digest("api-5", DigestPeriod.HOURLY)
    sent = client.post("/api/notifications/digest/send", json={"digest_id": digest.id})
    assert sent.status_code == 200
    assert sent.json()["is_sent"] is True
    again = client.post("/api/notifications/digest/send", json={"digest_id": digest.id})
    assert again.status_code == 409


def test_router_validation_errors(client: TestClient) -> None:
    """Invalid payloads produce typed four-hundred responses."""
    response = client.post(
        "/api/notifications",
        json={
            "recipient_id": "api-6",
            "channel": "carrier-pigeon",
            "kind": "solve",
            "title": "x",
            "body": "y",
        },
    )
    assert response.status_code == 422
    missing = client.get("/api/notifications/preferences")
    assert missing.status_code == 422
    bad_page = client.get("/api/notifications", params={"limit": 0})
    assert bad_page.status_code == 422


def test_digest_entry_round_trip() -> None:
    """Digest entries survive a JSON round trip."""
    entry = DigestEntry.from_notification(make_notification("entry"))
    restored = DigestEntry.from_dict(entry.to_dict())
    assert restored.notification_id == entry.notification_id
    assert restored.kind is entry.kind
    assert restored.action_url == entry.action_url
    grouped = group_digest_entries([entry])
    assert grouped[0].count == 1
