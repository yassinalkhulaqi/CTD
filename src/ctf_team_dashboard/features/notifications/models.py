"""Domain entities and pure rules for the notification centre.

The module deliberately keeps all decision logic free of persistence concerns:
preference lookup, quiet-hours suppression, templating, digest grouping,
severity ordering and retention pruning are plain functions over immutable
values. The service layer composes them with repositories, and the router only
translates results into typed API payloads.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import ensure_utc, utcnow
from ctf_team_dashboard.errors import ValidationError

_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}")


class Channel(StrEnum):
    """Delivery channel available to a notification."""

    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationKind(StrEnum):
    """Category of event that produced a notification."""

    SOLVE = "solve"
    CHALLENGE = "challenge"
    TEAM = "team"
    SYSTEM = "system"
    SECURITY = "security"
    ANY = "*"


class Severity(StrEnum):
    """Urgency of a notification, ordered from least to most important."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """Return a monotonically increasing urgency rank."""
        return {
            Severity.INFO: 0,
            Severity.WARNING: 1,
            Severity.CRITICAL: 2,
        }[self]

    @property
    def is_urgent(self) -> bool:
        """Return whether the severity warrants interrupting the recipient."""
        return self in (Severity.WARNING, Severity.CRITICAL)

    @property
    def accent(self) -> str:
        """Return the CSS custom property used to colour this severity."""
        return {
            Severity.INFO: "var(--info-base)",
            Severity.WARNING: "var(--warning-base)",
            Severity.CRITICAL: "var(--danger-base)",
        }[self]


class DigestPeriod(StrEnum):
    """Time window used to group notifications into a digest."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"

    @property
    def window(self) -> timedelta:
        """Return the length of the period."""
        return {
            DigestPeriod.HOURLY: timedelta(hours=1),
            DigestPeriod.DAILY: timedelta(days=1),
            DigestPeriod.WEEKLY: timedelta(days=7),
        }[self]

    @property
    def label(self) -> str:
        """Return a human readable label for the period."""
        return {
            DigestPeriod.HOURLY: "Past hour",
            DigestPeriod.DAILY: "Past day",
            DigestPeriod.WEEKLY: "Past week",
        }[self]


def severity_order() -> tuple[Severity, ...]:
    """Return every severity ordered from most to least urgent."""
    return tuple(sorted(Severity, key=lambda severity: severity.rank, reverse=True))


def render_template(template: str, variables: Mapping[str, Any]) -> str:
    """Substitute ``{{ name }}`` placeholders using ``variables``.

    Dotted paths traverse nested mappings, so ``{{ challenge.name }}`` resolves
    against ``{"challenge": {"name": ...}}``. Unknown placeholders are kept
    verbatim, which makes a missing variable obvious rather than silently
    shipping a truncated message.
    """

    def substitute(match: re.Match[str]) -> str:
        path = match.group(1)
        current: Any = variables
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return match.group(0)
            current = current[part]
        if current is None:
            return ""
        if isinstance(current, bool):
            return "yes" if current else "no"
        return str(current)

    return _TEMPLATE_PATTERN.sub(substitute, template)


def template_variables(template: str) -> tuple[str, ...]:
    """Return the distinct placeholder names referenced by ``template``."""
    seen: list[str] = []
    for match in _TEMPLATE_PATTERN.finditer(template):
        name = match.group(1)
        if name not in seen:
            seen.append(name)
    return tuple(seen)


@dataclass(frozen=True, slots=True)
class QuietHours:
    """An hour-of-day interval during which delivery is suppressed."""

    start_hour: int
    end_hour: int

    @property
    def active(self) -> bool:
        """Return whether a quiet window is configured."""
        return self.start_hour != self.end_hour

    def contains(self, moment: datetime) -> bool:
        """Return whether ``moment`` falls inside the quiet window."""
        if not self.active:
            return False
        hour = ensure_utc(moment).hour
        if self.start_hour < self.end_hour:
            return self.start_hour <= hour < self.end_hour
        return hour >= self.start_hour or hour < self.end_hour

    def next_open_hour(self, moment: datetime) -> int:
        """Return the hour at which delivery resumes after ``moment``."""
        if not self.active:
            return ensure_utc(moment).hour
        hour = ensure_utc(moment).hour
        if self.start_hour < self.end_hour:
            return self.end_hour if hour < self.end_hour else self.start_hour
        if hour >= self.start_hour or hour < self.end_hour:
            return self.end_hour
        return self.start_hour

    def describe(self) -> str:
        """Return a compact human readable description of the window."""
        if not self.active:
            return "No quiet hours"
        return f"{self.start_hour:02d}:00–{self.end_hour:02d}:00 UTC"


@dataclass(frozen=True, slots=True)
class Notification:
    """A single message addressed to one recipient."""

    id: str
    recipient_id: str
    channel: Channel
    kind: NotificationKind
    title: str
    body: str
    severity: Severity = Severity.INFO
    read_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    action_url: str = ""

    @property
    def is_read(self) -> bool:
        """Return whether the notification has been acknowledged."""
        return self.read_at is not None

    @property
    def is_unread(self) -> bool:
        """Return whether the notification still needs attention."""
        return self.read_at is None

    @property
    def age_seconds(self) -> float:
        """Return the age of the notification in seconds."""
        return max(0.0, (utcnow() - ensure_utc(self.created_at)).total_seconds())

    @property
    def label(self) -> str:
        """Return a short label combining kind and severity."""
        return f"{self.kind.value} · {self.severity.value}"

    def mark_read(self, when: datetime | None = None) -> Notification:
        """Return a copy of the notification marked as read."""
        if self.is_read:
            return self
        return replace(self, read_at=ensure_utc(when if when is not None else utcnow()))

    def sort_key(self) -> tuple[int, float, str]:
        """Return a key ordering by severity, recency and identifier."""
        return (
            -self.severity.rank,
            -ensure_utc(self.created_at).timestamp(),
            self.id,
        )

    def matches(self, query: NotificationQuery) -> bool:
        """Return whether the notification satisfies every query filter."""
        if query.recipient_id is not None and self.recipient_id != query.recipient_id:
            return False
        if query.channel is not None and self.channel is not query.channel:
            return False
        if query.kind is not None and self.kind is not query.kind:
            return False
        if query.severity is not None and self.severity is not query.severity:
            return False
        if query.unread_only and self.is_read:
            return False
        if query.search:
            needle = query.search.strip().lower()
            if needle and needle not in self.title.lower() and needle not in self.body.lower():
                return False
        return True


@dataclass(frozen=True, slots=True)
class NotificationQuery:
    """Filters accepted by the notification listing endpoints."""

    recipient_id: str | None = None
    channel: Channel | None = None
    kind: NotificationKind | None = None
    severity: Severity | None = None
    unread_only: bool = False
    search: str = ""
    limit: int = 100
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 500:
            raise ValidationError("limit must be between 1 and 500", details={"limit": self.limit})
        if self.offset < 0:
            raise ValidationError("offset cannot be negative", details={"offset": self.offset})

    def apply(self, items: Iterable[Notification]) -> list[Notification]:
        """Filter, order and paginate ``items``."""
        matching = sorted(
            (item for item in items if item.matches(self)),
            key=Notification.sort_key,
        )
        return matching[self.offset : self.offset + self.limit]


def count_unread(items: Iterable[Notification]) -> int:
    """Return the number of unread notifications in ``items``."""
    return sum(1 for item in items if item.is_unread)


def sort_notifications(items: Iterable[Notification]) -> tuple[Notification, ...]:
    """Return notifications ordered by severity then by descending time."""
    return tuple(sorted(items, key=Notification.sort_key))


@dataclass(frozen=True, slots=True)
class NotificationPreference:
    """Per-recipient delivery settings for one channel and kind."""

    recipient_id: str
    channel: Channel
    kind: NotificationKind
    enabled: bool = True
    quiet_start_hour: int = 0
    quiet_end_hour: int = 0

    def __post_init__(self) -> None:
        for value, name in (
            (self.quiet_start_hour, "quiet_start_hour"),
            (self.quiet_end_hour, "quiet_end_hour"),
        ):
            if not 0 <= value <= 23:
                raise ValidationError(
                    f"{name} must be an hour between 0 and 23",
                    details={name: value},
                )

    @property
    def quiet_hours(self) -> QuietHours:
        """Return the quiet window described by this preference."""
        return QuietHours(self.quiet_start_hour, self.quiet_end_hour)

    def accepts(self, notification: Notification, moment: datetime | None = None) -> bool:
        """Return whether this preference allows delivery of ``notification``."""
        if not self.enabled:
            return False
        if notification.severity is Severity.CRITICAL:
            return True
        now = moment if moment is not None else utcnow()
        return not self.quiet_hours.contains(now)

    def with_enabled(self, enabled: bool) -> NotificationPreference:
        """Return a copy with a different enabled flag."""
        return replace(self, enabled=enabled)

    def with_quiet_hours(self, start: int, end: int) -> NotificationPreference:
        """Return a copy with a different quiet window."""
        return replace(self, quiet_start_hour=start, quiet_end_hour=end)


def default_preference(
    recipient_id: str,
    channel: Channel,
    kind: NotificationKind,
) -> NotificationPreference:
    """Return the implicit preference used when no row is stored."""
    return NotificationPreference(recipient_id=recipient_id, channel=channel, kind=kind)


def lookup_preference(
    preferences: Sequence[NotificationPreference],
    recipient_id: str,
    channel: Channel,
    kind: NotificationKind,
) -> NotificationPreference:
    """Find the most specific preference for a recipient and event.

    An exact ``(channel, kind)`` row wins, followed by a channel-wide rule
    recorded with ``kind = "*"``. When nothing is stored, an enabled default
    without quiet hours is returned so notifications are never lost silently.
    """
    wildcard = default_preference(recipient_id, channel, NotificationKind.ANY)
    for preference in preferences:
        if (
            preference.recipient_id == recipient_id
            and preference.channel is channel
            and preference.kind is kind
        ):
            return preference
    for preference in preferences:
        if (
            preference.recipient_id == recipient_id
            and preference.channel is channel
            and preference.kind is NotificationKind.ANY
        ):
            return preference
    return wildcard


def effective_preferences(
    preferences: Sequence[NotificationPreference],
    recipient_id: str,
) -> tuple[NotificationPreference, ...]:
    """Return the full preference matrix for ``recipient_id``.

    Every channel/kind pair is represented. Explicit rows (including wildcards)
    override the defaults so the UI can render a complete, stable grid.
    """
    result: list[NotificationPreference] = []
    explicit = {
        (preference.channel, preference.kind): preference
        for preference in preferences
        if preference.recipient_id == recipient_id
    }
    wildcard = explicit.get((Channel.IN_APP, NotificationKind.ANY))
    for channel in Channel:
        for kind in NotificationKind:
            if kind is NotificationKind.ANY:
                continue
            override = explicit.get((channel, kind)) or explicit.get(
                (channel, NotificationKind.ANY)
            )
            if override is None:
                override = wildcard
            if override is None or override.channel is not channel:
                result.append(default_preference(recipient_id, channel, kind))
            else:
                result.append(replace(override, kind=kind))
    return tuple(result)


@dataclass(frozen=True, slots=True)
class DeliveryDecision:
    """Outcome of evaluating preferences for a newly created notification."""

    channel: Channel
    delivered: bool
    reason: str
    suppressed_until_hour: int | None = None

    @property
    def suppressed(self) -> bool:
        """Return whether delivery was held back."""
        return not self.delivered

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "channel": self.channel.value,
            "delivered": self.delivered,
            "reason": self.reason,
            "suppressed_until_hour": self.suppressed_until_hour,
        }


def evaluate_delivery(
    preference: NotificationPreference,
    notification: Notification,
    moment: datetime | None = None,
) -> DeliveryDecision:
    """Decide whether a notification should be delivered right now."""
    now = moment if moment is not None else utcnow()
    if not preference.enabled:
        return DeliveryDecision(notification.channel, False, "channel_disabled")
    if notification.severity is Severity.CRITICAL:
        return DeliveryDecision(notification.channel, True, "critical_override")
    if preference.quiet_hours.contains(now):
        return DeliveryDecision(
            notification.channel,
            False,
            "quiet_hours",
            preference.quiet_hours.next_open_hour(now),
        )
    return DeliveryDecision(notification.channel, True, "delivered")


@dataclass(frozen=True, slots=True)
class DigestEntry:
    """One notification condensed into a digest."""

    notification_id: str
    kind: NotificationKind
    severity: Severity
    title: str
    body: str
    created_at: datetime
    action_url: str = ""

    def to_dict(self) -> dict[str, str]:
        """Return the JSON-compatible representation stored in the database."""
        return {
            "notification_id": self.notification_id,
            "kind": self.kind.value,
            "severity": self.severity.value,
            "title": self.title,
            "body": self.body,
            "created_at": ensure_utc(self.created_at).isoformat(),
            "action_url": self.action_url,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> DigestEntry:
        """Rebuild an entry from its stored representation."""
        created = parse_iso(str(raw.get("created_at", "")))
        return cls(
            notification_id=str(raw.get("notification_id", "")),
            kind=NotificationKind.parse(str(raw.get("kind", "system")), NotificationKind.SYSTEM),
            severity=Severity.parse(str(raw.get("severity", "info")), Severity.INFO),
            title=str(raw.get("title", "")),
            body=str(raw.get("body", "")),
            created_at=created if created is not None else utcnow(),
            action_url=str(raw.get("action_url", "")),
        )

    @classmethod
    def from_notification(cls, notification: Notification) -> DigestEntry:
        """Condense a notification into a digest entry."""
        return cls(
            notification_id=notification.id,
            kind=notification.kind,
            severity=notification.severity,
            title=notification.title,
            body=notification.body,
            created_at=notification.created_at,
            action_url=notification.action_url,
        )


@dataclass(frozen=True, slots=True)
class DigestGroup:
    """Digest entries sharing a kind and severity."""

    kind: NotificationKind
    severity: Severity
    entries: tuple[DigestEntry, ...] = ()

    @property
    def count(self) -> int:
        """Return the number of entries in the group."""
        return len(self.entries)

    @property
    def headline(self) -> str:
        """Return a summary line for the group."""
        return f"{self.severity.value.title()} {self.kind.value} · {self.count}"


def group_digest_entries(entries: Iterable[DigestEntry]) -> tuple[DigestGroup, ...]:
    """Group digest entries by kind and severity in a stable order."""
    buckets: dict[tuple[NotificationKind, Severity], list[DigestEntry]] = {}
    for entry in entries:
        buckets.setdefault((entry.kind, entry.severity), []).append(entry)
    keys = sorted(
        buckets,
        key=lambda key: (-key[1].rank, key[0].value),
    )
    return tuple(
        DigestGroup(kind=kind, severity=severity, entries=tuple(buckets[(kind, severity)]))
        for kind, severity in keys
    )


def parse_iso(raw: str) -> datetime | None:
    """Parse an ISO timestamp, returning ``None`` for empty or invalid input."""
    if not raw:
        return None
    try:
        return ensure_utc(datetime.fromisoformat(raw))
    except ValueError:
        return None


def encode_entries(entries: Iterable[DigestEntry]) -> str:
    """Serialise digest entries into the stored JSON column."""
    payload = [entry.to_dict() for entry in entries]
    return json.dumps(payload, separators=(",", ":"))


def decode_entries(raw: str) -> tuple[DigestEntry, ...]:
    """Decode a stored JSON payload, tolerating corrupt data."""
    if not raw:
        return ()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    if not isinstance(decoded, list):
        return ()
    return tuple(DigestEntry.from_dict(item) for item in decoded if isinstance(item, dict))


@dataclass(frozen=True, slots=True)
class Digest:
    """A persisted digest of notifications for one recipient."""

    id: str
    recipient_id: str
    period: DigestPeriod
    entries_json: str = "[]"
    sent_at: datetime | None = None

    @property
    def entries(self) -> tuple[DigestEntry, ...]:
        """Return the decoded entries."""
        return decode_entries(self.entries_json)

    @property
    def groups(self) -> tuple[DigestGroup, ...]:
        """Return entries grouped by kind and severity."""
        return group_digest_entries(self.entries)

    @property
    def total(self) -> int:
        """Return the number of notifications in the digest."""
        return len(self.entries)

    @property
    def is_sent(self) -> bool:
        """Return whether the digest has been dispatched."""
        return self.sent_at is not None

    def mark_sent(self, when: datetime | None = None) -> Digest:
        """Return a copy of the digest marked as sent."""
        if self.is_sent:
            return self
        return replace(self, sent_at=ensure_utc(when if when is not None else utcnow()))

    def render_markdown(self) -> str:
        """Render a human readable digest body."""
        lines = [f"# {self.period.label} digest", ""]
        if not self.groups:
            lines.append("Nothing to report.")
            return "\n".join(lines)
        for group in self.groups:
            lines.append(f"## {group.headline}")
            for entry in group.entries:
                lines.append(f"- {entry.title}: {entry.body}")
            lines.append("")
        return "\n".join(lines).rstrip()


def build_digest(
    digest_id: str,
    recipient_id: str,
    period: DigestPeriod,
    notifications: Sequence[Notification],
    sent_at: datetime | None = None,
) -> Digest:
    """Create a digest from the notifications collected for a period."""
    ordered = sort_notifications(notifications)
    entries = [DigestEntry.from_notification(item) for item in ordered]
    return Digest(
        id=digest_id,
        recipient_id=recipient_id,
        period=period,
        entries_json=encode_entries(entries),
        sent_at=sent_at,
    )


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Rules governing how long read notifications are kept."""

    max_age_days: int = 30
    keep_unread: bool = True

    def __post_init__(self) -> None:
        if self.max_age_days < 1:
            raise ValidationError(
                "max_age_days must be at least 1",
                details={"max_age_days": self.max_age_days},
            )

    @property
    def cutoff(self) -> timedelta:
        """Return the maximum age as a timedelta."""
        return timedelta(days=self.max_age_days)

    def is_expired(self, notification: Notification, now: datetime | None = None) -> bool:
        """Return whether a notification may be pruned."""
        if self.keep_unread and notification.is_unread:
            return False
        reference = now if now is not None else utcnow()
        return ensure_utc(notification.created_at) < ensure_utc(reference) - self.cutoff

    def prune(
        self,
        notifications: Iterable[Notification],
        now: datetime | None = None,
    ) -> tuple[tuple[Notification, ...], tuple[Notification, ...]]:
        """Split notifications into those to keep and those to remove."""
        kept: list[Notification] = []
        removed: list[Notification] = []
        for notification in notifications:
            if self.is_expired(notification, now):
                removed.append(notification)
            else:
                kept.append(notification)
        return tuple(kept), tuple(removed)


@dataclass(frozen=True, slots=True)
class NotificationStats:
    """Aggregated counters used by the notification centre header."""

    total: int = 0
    unread: int = 0
    critical_unread: int = 0
    by_channel: dict[str, int] = field(default_factory=dict)
    by_kind: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)

    @property
    def read(self) -> int:
        """Return the number of acknowledged notifications."""
        return max(0, self.total - self.unread)

    @property
    def read_rate(self) -> float:
        """Return the fraction of notifications already read."""
        if self.total == 0:
            return 0.0
        return self.read / self.total

    @classmethod
    def from_notifications(cls, notifications: Iterable[Notification]) -> NotificationStats:
        """Aggregate a collection of notifications into headline counters."""
        items = tuple(notifications)
        channels = Counter(item.channel.value for item in items)
        kinds = Counter(item.kind.value for item in items)
        severities = Counter(item.severity.value for item in items)
        return cls(
            total=len(items),
            unread=sum(1 for item in items if item.is_unread),
            critical_unread=sum(
                1 for item in items if item.is_unread and item.severity is Severity.CRITICAL
            ),
            by_channel=dict(channels),
            by_kind=dict(kinds),
            by_severity=dict(severities),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation."""
        return {
            "total": self.total,
            "unread": self.unread,
            "read": self.read,
            "critical_unread": self.critical_unread,
            "read_rate": self.read_rate,
            "by_channel": dict(self.by_channel),
            "by_kind": dict(self.by_kind),
            "by_severity": dict(self.by_severity),
        }


@dataclass(frozen=True, slots=True)
class CreateResult:
    """A stored notification together with its delivery decision."""

    notification: Notification
    decision: DeliveryDecision

    @property
    def delivered(self) -> bool:
        """Return whether the notification passed the channel checks."""
        return self.decision.delivered
