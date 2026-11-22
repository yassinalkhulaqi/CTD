"""Domain entities and pure calculations for the activity timeline feature.

All of the timeline maths lives in this module so it can be tested without a
database: relative time formatting, day/hour grouping, importance ranking,
consecutive-event deduplication and aggregation counters. Persistence and
orchestration are deliberately kept in ``store`` and ``service``.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, TypeVar

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import ensure_utc, utcnow
from ctf_team_dashboard.repositories.base import parse_payload

MAX_SUMMARY_LENGTH = 300
MAX_ACTOR_NAME_LENGTH = 120
MAX_IDENTIFIER_LENGTH = 120
MAX_PAYLOAD_BYTES = 4096
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
DEFAULT_MAX_AGE_DAYS = 30
DEFAULT_DEDUPE_WINDOW_SECONDS = 120
MAX_DEDUPE_WINDOW_SECONDS = 86_400

_DAY_FORMAT = "%Y-%m-%d"
_HOUR_FORMAT = "%Y-%m-%dT%H:00"
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")

_T = TypeVar("_T")
_K = TypeVar("_K")


class TimelineKind(StrEnum):
    """The category of activity recorded by a timeline event."""

    SOLVE = "solve"
    CHALLENGE = "challenge"
    MEMBER = "member"
    TEAM = "team"
    NOTE = "note"
    HINT = "hint"
    SUBMISSION = "submission"
    ACHIEVEMENT = "achievement"
    SYSTEM = "system"

    @property
    def label(self) -> str:
        """Return a human readable label for the kind."""
        return {
            TimelineKind.SOLVE: "Solve",
            TimelineKind.CHALLENGE: "Challenge",
            TimelineKind.MEMBER: "Member",
            TimelineKind.TEAM: "Team",
            TimelineKind.NOTE: "Note",
            TimelineKind.HINT: "Hint",
            TimelineKind.SUBMISSION: "Submission",
            TimelineKind.ACHIEVEMENT: "Achievement",
            TimelineKind.SYSTEM: "System",
        }[self]

    @property
    def icon(self) -> str:
        """Return the name of the icon used by the UI for this kind."""
        return {
            TimelineKind.SOLVE: "flag",
            TimelineKind.CHALLENGE: "target",
            TimelineKind.MEMBER: "user",
            TimelineKind.TEAM: "users",
            TimelineKind.NOTE: "file-text",
            TimelineKind.HINT: "lightbulb",
            TimelineKind.SUBMISSION: "send",
            TimelineKind.ACHIEVEMENT: "award",
            TimelineKind.SYSTEM: "settings",
        }[self]

    @property
    def color(self) -> str:
        """Return the accent colour associated with the kind."""
        return {
            TimelineKind.SOLVE: "#34d399",
            TimelineKind.CHALLENGE: "#38bdf8",
            TimelineKind.MEMBER: "#a78bfa",
            TimelineKind.TEAM: "#6366f1",
            TimelineKind.NOTE: "#fbbf24",
            TimelineKind.HINT: "#f472b6",
            TimelineKind.SUBMISSION: "#fb923c",
            TimelineKind.ACHIEVEMENT: "#facc15",
            TimelineKind.SYSTEM: "#94a3b8",
        }[self]

    @property
    def is_high_signal(self) -> bool:
        """Return whether the kind represents a notable team milestone."""
        return self in (
            TimelineKind.SOLVE,
            TimelineKind.ACHIEVEMENT,
            TimelineKind.TEAM,
        )


class Importance(StrEnum):
    """The importance tier attached to a timeline event."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """Return a numeric rank where higher values are more important."""
        return {
            Importance.LOW: 0,
            Importance.NORMAL: 1,
            Importance.HIGH: 2,
            Importance.CRITICAL: 3,
        }[self]

    @property
    def label(self) -> str:
        """Return a human readable label for the tier."""
        return {
            Importance.LOW: "Low",
            Importance.NORMAL: "Normal",
            Importance.HIGH: "High",
            Importance.CRITICAL: "Critical",
        }[self]

    @property
    def tone(self) -> str:
        """Return the semantic badge tone used by the frontend."""
        return {
            Importance.LOW: "neutral",
            Importance.NORMAL: "info",
            Importance.HIGH: "warning",
            Importance.CRITICAL: "danger",
        }[self]

    @classmethod
    def from_rank(cls, rank: int) -> Importance:
        """Return the tier for a numeric rank, clamped to the legal range.

        Args:
            rank: The rank to convert.

        Returns:
            The closest matching importance tier.
        """
        bounded = max(0, min(rank, len(cls) - 1))
        return tuple(cls)[bounded]

    @property
    def is_urgent(self) -> bool:
        """Return whether the tier deserves prominent treatment in the UI."""
        return self in (Importance.HIGH, Importance.CRITICAL)


class BucketLevel(StrEnum):
    """The temporal granularity of a timeline bucket."""

    DAY = "day"
    HOUR = "hour"

    @property
    def label(self) -> str:
        """Return a human readable granularity label."""
        return "Day" if self is BucketLevel.DAY else "Hour"


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """A single immutable activity record."""

    id: str
    team_id: str
    kind: str
    actor_id: str
    actor_name: str
    summary: str
    payload_json: str = "{}"
    importance: str = str(Importance.NORMAL)
    occurred_at: datetime = field(default_factory=utcnow)

    @property
    def timeline_kind(self) -> TimelineKind:
        """Return the parsed kind, falling back to ``system``."""
        return TimelineKind.parse(self.kind, TimelineKind.SYSTEM)

    @property
    def importance_level(self) -> Importance:
        """Return the parsed importance tier, falling back to ``normal``."""
        return Importance.parse(self.importance, Importance.NORMAL)

    @property
    def payload(self) -> dict[str, Any]:
        """Return the decoded JSON payload, or an empty object."""
        return parse_payload(self.payload_json)

    @property
    def date_key(self) -> str:
        """Return the ``YYYY-MM-DD`` bucket key for the event."""
        return day_key(self.occurred_at)

    @property
    def hour_key(self) -> str:
        """Return the ``YYYY-MM-DDTHH:00`` bucket key for the event."""
        return hour_key(self.occurred_at)

    @property
    def hour_of_day(self) -> int:
        """Return the hour of day in UTC, from 0 to 23."""
        return ensure_utc(self.occurred_at).hour

    @property
    def importance_rank(self) -> int:
        """Return the numeric importance rank used for ordering."""
        return self.importance_level.rank

    @property
    def is_critical(self) -> bool:
        """Return whether the event uses the critical importance tier."""
        return self.importance_level is Importance.CRITICAL

    @property
    def actor_initials(self) -> str:
        """Return up to two initials derived from the actor name."""
        parts = [part for part in self.actor_name.split() if part]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def relative_label(self, now: datetime | None = None) -> str:
        """Return a human friendly relative timestamp.

        Args:
            now: Reference time, defaulting to the current UTC time.

        Returns:
            A compact label such as ``just now`` or ``3h ago``.
        """
        return relative_time(self.occurred_at, now)

    def age_seconds(self, now: datetime | None = None) -> float:
        """Return how many seconds have elapsed since the event occurred."""
        reference = utcnow() if now is None else ensure_utc(now)
        return max(0.0, (reference - ensure_utc(self.occurred_at)).total_seconds())


@dataclass(frozen=True, slots=True)
class EventCluster:
    """One or more consecutive events collapsed into a single display item."""

    event: TimelineEvent
    count: int = 1
    first_at: datetime | None = None
    last_at: datetime | None = None

    @property
    def id(self) -> str:
        """Return the identifier of the representative event."""
        return self.event.id

    @property
    def kind(self) -> str:
        """Return the representative event kind."""
        return self.event.kind

    @property
    def actor_id(self) -> str:
        """Return the representative actor identifier."""
        return self.event.actor_id

    @property
    def occurred_at(self) -> datetime:
        """Return the timestamp of the representative (newest) event."""
        return self.first_at or self.event.occurred_at

    @property
    def is_merged(self) -> bool:
        """Return whether more than one event was collapsed into this item."""
        return self.count > 1

    @property
    def count_label(self) -> str:
        """Return a compact repeat indicator, or an empty string."""
        return f"×{self.count}" if self.is_merged else ""

    @property
    def importance_rank(self) -> int:
        """Return the importance rank of the representative event."""
        return self.event.importance_rank


@dataclass(frozen=True, slots=True)
class TimelineBucket:
    """A day or hour group of clustered timeline events."""

    key: str
    label: str
    events: tuple[EventCluster, ...] = ()
    level: BucketLevel = BucketLevel.DAY
    children: tuple[TimelineBucket, ...] = ()

    @property
    def count(self) -> int:
        """Return the number of raw events in this bucket and its children."""
        own = sum(cluster.count for cluster in self.events)
        return own + sum(child.count for child in self.children)

    @property
    def item_count(self) -> int:
        """Return the number of visible items directly in the bucket."""
        return len(self.events)

    @property
    def critical_count(self) -> int:
        """Return the number of critical events in the whole bucket."""
        own = sum(1 for cluster in self.events if cluster.event.is_critical)
        return own + sum(child.critical_count for child in self.children)

    @property
    def peak_importance(self) -> Importance:
        """Return the highest importance tier present in the bucket."""
        candidates = [cluster.event.importance_level for cluster in self.events]
        for child in self.children:
            candidates.append(child.peak_importance)
        if not candidates:
            return Importance.LOW
        return max(candidates, key=lambda item: item.rank)

    @property
    def hour_of_day(self) -> int | None:
        """Return the bucket hour when this is an hourly bucket."""
        if self.level is not BucketLevel.HOUR:
            return None
        try:
            return datetime.fromisoformat(self.key).hour
        except ValueError:
            return None

    @classmethod
    def from_clusters(
        cls,
        key: str,
        label: str,
        clusters: Sequence[EventCluster],
        *,
        level: BucketLevel = BucketLevel.DAY,
    ) -> TimelineBucket:
        """Build a flat bucket from a sequence of clusters.

        Args:
            key: Stable bucket key.
            label: Display label.
            clusters: Events belonging to the bucket.
            level: The temporal granularity of the bucket.

        Returns:
            The populated bucket.
        """
        return cls(key=key, label=label, events=tuple(clusters), level=level)


@dataclass(frozen=True, slots=True)
class ActorSummary:
    """Aggregated activity for one actor."""

    actor_id: str
    actor_name: str
    event_count: int = 0
    critical_count: int = 0
    last_seen: datetime | None = None
    kinds: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        """Return the actor display name with a stable fallback."""
        return self.actor_name.strip() or self.actor_id

    @property
    def initials(self) -> str:
        """Return up to two initials derived from the actor label."""
        parts = [part for part in self.label.split() if part]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def first_kind(self) -> TimelineKind:
        """Return the most characteristic kind for this actor."""
        if not self.kinds:
            return TimelineKind.SYSTEM
        return TimelineKind.parse(self.kinds[0], TimelineKind.SYSTEM)


@dataclass(frozen=True, slots=True)
class TimelineStats:
    """Aggregated counters for an entire timeline view."""

    total: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    by_hour: dict[str, int] = field(default_factory=dict)
    by_importance: dict[str, int] = field(default_factory=dict)
    unique_actors: int = 0
    critical_count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    generated_at: datetime = field(default_factory=utcnow)

    @property
    def busiest_kind(self) -> str | None:
        """Return the kind with the highest event count."""
        return leading_key(self.by_kind)

    @property
    def busiest_hour(self) -> str | None:
        """Return the hour key with the highest event count."""
        return leading_key(self.by_hour)

    @property
    def critical_ratio(self) -> float:
        """Return the fraction of events marked critical."""
        if self.total == 0:
            return 0.0
        return round(self.critical_count / self.total, 3)

    @property
    def average_per_hour(self) -> float:
        """Return the average number of events per occupied hour."""
        if not self.by_hour:
            return 0.0
        return round(self.total / len(self.by_hour), 1)

    def top_kinds(self, limit: int = 5) -> tuple[tuple[str, int], ...]:
        """Return the most frequent kinds in descending order.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            Pairs of kind value and count.
        """
        ranked = sorted(self.by_kind.items(), key=lambda item: (-item[1], item[0]))
        return tuple(ranked[: max(0, limit)])


@dataclass(frozen=True, slots=True)
class TimelinePage:
    """A paginated result of deduplicated timeline events."""

    clusters: tuple[EventCluster, ...] = ()
    total: int = 0
    limit: int = DEFAULT_LIMIT
    offset: int = 0

    @property
    def events(self) -> tuple[TimelineEvent, ...]:
        """Return the representative event of every cluster."""
        return tuple(cluster.event for cluster in self.clusters)

    @property
    def has_more(self) -> bool:
        """Return whether another raw-event page follows this one."""
        return self.offset + self.limit < self.total

    @property
    def next_offset(self) -> int | None:
        """Return the raw-event offset of the next page, when one exists."""
        return self.offset + self.limit if self.has_more else None

    @property
    def page_number(self) -> int:
        """Return the one-based page index for this result."""
        return self.offset // self.limit + 1 if self.limit > 0 else 1


@dataclass(frozen=True, slots=True)
class PruneResult:
    """The outcome of an age based timeline prune."""

    cutoff: datetime
    deleted: int
    max_age_days: int
    retained: int = 0

    @property
    def description(self) -> str:
        """Return a compact human readable summary of the prune."""
        return f"Removed {self.deleted} event(s) older than {self.max_age_days} day(s)"


@dataclass(frozen=True, slots=True)
class TimelineFilter:
    """The complete set of filters accepted by timeline queries."""

    kinds: tuple[str, ...] = ()
    actors: tuple[str, ...] = ()
    importance: tuple[str, ...] = ()
    team_id: str | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None
    limit: int = DEFAULT_LIMIT
    offset: int = 0

    @property
    def is_empty(self) -> bool:
        """Return whether no selection filters are active."""
        return not (
            self.kinds
            or self.actors
            or self.importance
            or self.team_id
            or self.from_at
            or self.to_at
        )

    @property
    def is_paginated(self) -> bool:
        """Return whether the filter narrows the result to a single page."""
        return self.limit < MAX_LIMIT or self.offset > 0

    @property
    def normalised_kinds(self) -> tuple[TimelineKind, ...]:
        """Return kinds parsed into enum members, ignoring unknown values."""
        result: list[TimelineKind] = []
        for kind in self.kinds:
            try:
                parsed = TimelineKind.parse(kind)
            except ValueError:
                continue
            if parsed not in result:
                result.append(parsed)
        return tuple(result)

    def matches(self, event: TimelineEvent) -> bool:
        """Return whether an event satisfies every selection filter.

        Args:
            event: The candidate event.

        Returns:
            ``True`` when the event should be included in the result.
        """
        if self.team_id and event.team_id != self.team_id:
            return False
        if self.kinds and event.kind not in self.kinds:
            return False
        if self.actors and event.actor_id not in self.actors:
            return False
        if self.importance and event.importance not in self.importance:
            return False
        occurred = ensure_utc(event.occurred_at)
        if self.from_at and occurred < ensure_utc(self.from_at):
            return False
        return not (self.to_at and occurred > ensure_utc(self.to_at))

    def with_offset(self, offset: int) -> TimelineFilter:
        """Return a copy of the filter with a new pagination offset."""
        return TimelineFilter(
            kinds=self.kinds,
            actors=self.actors,
            importance=self.importance,
            team_id=self.team_id,
            from_at=self.from_at,
            to_at=self.to_at,
            limit=self.limit,
            offset=max(0, offset),
        )


def relative_time(when: datetime, now: datetime | None = None) -> str:
    """Format a timestamp as a compact relative label.

    Args:
        when: The event timestamp.
        now: Reference time, defaulting to the current UTC time.

    Returns:
        ``just now``, a value in minutes/hours/days, or an absolute date.
    """
    reference = utcnow() if now is None else ensure_utc(now)
    moment = ensure_utc(when)
    seconds = max(0.0, (reference - moment).total_seconds())
    if seconds < 45:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{max(1, minutes)}m ago"
    hours = int(seconds // 3600)
    if hours < 24:
        return f"{hours}h ago"
    days = int(seconds // 86_400)
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days}d ago"
    return moment.strftime("%b %d")


def day_key(when: datetime) -> str:
    """Return the stable day bucket key for a timestamp."""
    return ensure_utc(when).strftime(_DAY_FORMAT)


def hour_key(when: datetime) -> str:
    """Return the stable hour bucket key for a timestamp."""
    return ensure_utc(when).strftime(_HOUR_FORMAT)


def day_label(when: datetime, now: datetime | None = None) -> str:
    """Return a human readable label for a day bucket.

    Args:
        when: Any timestamp inside the day.
        now: Reference time used for ``Today`` and ``Yesterday`` labels.

    Returns:
        A relative day label, or a formatted calendar date.
    """
    reference = utcnow() if now is None else ensure_utc(now)
    moment = ensure_utc(when)
    if moment.date() == reference.date():
        return "Today"
    if moment.date() == (reference - timedelta(days=1)).date():
        return "Yesterday"
    return moment.strftime("%a, %b %d")


def hour_label(when: datetime) -> str:
    """Return the display label for an hourly bucket."""
    return f"{ensure_utc(when).strftime('%H')}:00"


def parse_kind(raw: str, default: TimelineKind = TimelineKind.SYSTEM) -> TimelineKind:
    """Parse a raw kind, falling back to ``system`` when it is unknown."""
    return TimelineKind.parse(raw, default)


def parse_importance(raw: str, default: Importance = Importance.NORMAL) -> Importance:
    """Parse a raw importance value with a safe default."""
    return Importance.parse(raw, default)


def normalise_summary(value: str) -> str:
    """Collapse whitespace in a summary string."""
    return " ".join(value.split())


def slugify(value: str) -> str:
    """Convert a label into a lowercase slug with hyphens."""
    slug = _SLUG_PATTERN.sub("-", value.strip().lower()).strip("-")
    return slug or "timeline"


def encode_payload(payload: Mapping[str, Any] | None) -> str:
    """Serialise a payload mapping to compact, stable JSON.

    Args:
        payload: The payload mapping, or ``None`` for an empty object.

    Returns:
        The JSON string stored on the event.
    """
    if not payload:
        return "{}"
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def validate_payload_size(payload_json: str) -> None:
    """Reject payloads that exceed the configured storage budget.

    Args:
        payload_json: The encoded payload.

    Raises:
        ValueError: When the payload is too large.
    """
    if len(payload_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValueError(f"payload must not exceed {MAX_PAYLOAD_BYTES} bytes")


def leading_key(counter: Mapping[str, int]) -> str | None:
    """Return the key with the highest value, breaking ties alphabetically."""
    if not counter:
        return None
    return max(counter.items(), key=lambda item: (item[1], item[0]))[0]


def count_by(events: Iterable[TimelineEvent], key: Callable[[TimelineEvent], _K]) -> dict[_K, int]:
    """Count events keyed by an arbitrary pure function."""
    counter: Counter[_K] = Counter()
    for event in events:
        counter[key(event)] += 1
    return dict(counter)


def counts_by_kind(events: Iterable[TimelineEvent]) -> dict[str, int]:
    """Count events grouped by their kind value."""
    return count_by(events, lambda event: event.kind)


def counts_by_hour(events: Iterable[TimelineEvent]) -> dict[str, int]:
    """Count events grouped by their hour bucket key."""
    return count_by(events, lambda event: event.hour_key)


def counts_by_importance(events: Iterable[TimelineEvent]) -> dict[str, int]:
    """Count events grouped by their importance tier."""
    return count_by(events, lambda event: event.importance)


def rank_events(events: Iterable[TimelineEvent]) -> list[TimelineEvent]:
    """Order events by importance, then recency, then identifier.

    Args:
        events: The events to rank.

    Returns:
        A new list ordered from most to least important.
    """
    return sorted(
        events,
        key=lambda event: (
            -event.importance_rank,
            -ensure_utc(event.occurred_at).timestamp(),
            event.id,
        ),
    )


def sort_clusters(clusters: Iterable[EventCluster]) -> tuple[EventCluster, ...]:
    """Order clusters chronologically with importance as a tie breaker."""
    return tuple(
        sorted(
            clusters,
            key=lambda cluster: (
                -ensure_utc(cluster.occurred_at).timestamp(),
                -cluster.importance_rank,
                cluster.id,
            ),
        )
    )


def deduplicate_events(
    events: Sequence[TimelineEvent],
    *,
    window_seconds: int = DEFAULT_DEDUPE_WINDOW_SECONDS,
) -> tuple[EventCluster, ...]:
    """Collapse consecutive, identical events into display clusters.

    Two events are considered duplicates when they share a kind, actor and
    summary and fall within ``window_seconds`` of each other. The most
    important event in a cluster becomes its representative, so aggregation
    never loses a critical signal when a burst of activity is collapsed.

    Args:
        events: Events ordered from newest to oldest.
        window_seconds: Maximum separation for two events to be merged.

    Returns:
        The deduplicated event clusters in their original order.
    """
    if not events:
        return ()
    window = max(0, window_seconds)
    clusters: list[EventCluster] = []
    for event in events:
        moment = ensure_utc(event.occurred_at)
        if clusters:
            current = clusters[-1]
            representative = current.event
            same = (
                representative.kind == event.kind
                and representative.actor_id == event.actor_id
                and representative.summary == event.summary
            )
            reference = ensure_utc(current.occurred_at)
            within_window = abs((reference - moment).total_seconds()) <= window
            if same and within_window:
                winner = (
                    event
                    if event.importance_rank > representative.importance_rank
                    else representative
                )
                clusters[-1] = EventCluster(
                    event=winner,
                    count=current.count + 1,
                    first_at=max(reference, moment),
                    last_at=min(reference, moment),
                )
                continue
        clusters.append(EventCluster(event=event, count=1, first_at=moment, last_at=moment))
    return tuple(clusters)


def group_by_day(clusters: Sequence[EventCluster]) -> tuple[TimelineBucket, ...]:
    """Group clusters into day buckets.

    Args:
        clusters: Deduplicated, chronologically ordered clusters.

    Returns:
        Day buckets ordered by date descending.
    """
    grouped: dict[str, list[EventCluster]] = {}
    for cluster in clusters:
        grouped.setdefault(day_key(cluster.occurred_at), []).append(cluster)
    buckets: list[TimelineBucket] = []
    for key, items in grouped.items():
        moment = ensure_utc(items[0].occurred_at)
        buckets.append(TimelineBucket.from_clusters(key, day_label(moment), sort_clusters(items)))
    buckets.sort(key=lambda bucket: bucket.key, reverse=True)
    return tuple(buckets)


def group_by_hour(clusters: Sequence[EventCluster]) -> tuple[TimelineBucket, ...]:
    """Group clusters into hourly buckets.

    Args:
        clusters: Deduplicated, chronologically ordered clusters.

    Returns:
        Hour buckets ordered by time descending.
    """
    grouped: dict[str, list[EventCluster]] = {}
    for cluster in clusters:
        grouped.setdefault(hour_key(cluster.occurred_at), []).append(cluster)
    buckets: list[TimelineBucket] = []
    for key, items in grouped.items():
        moment = ensure_utc(items[0].occurred_at)
        buckets.append(
            TimelineBucket.from_clusters(
                key,
                hour_label(moment),
                sort_clusters(items),
                level=BucketLevel.HOUR,
            )
        )
    buckets.sort(key=lambda bucket: bucket.key, reverse=True)
    return tuple(buckets)


def build_timeline_groups(
    clusters: Sequence[EventCluster], *, now: datetime | None = None
) -> tuple[TimelineBucket, ...]:
    """Build a two-level day/hour hierarchy for a timeline.

    Args:
        clusters: Deduplicated, chronologically ordered clusters.
        now: Reference time used for relative day labels.

    Returns:
        Day buckets, each containing its hourly children.
    """
    reference = utcnow() if now is None else ensure_utc(now)
    days: dict[str, list[EventCluster]] = {}
    for cluster in clusters:
        days.setdefault(day_key(cluster.occurred_at), []).append(cluster)
    result: list[TimelineBucket] = []
    for key, items in sorted(days.items(), reverse=True):
        moment = ensure_utc(items[0].occurred_at)
        hours: dict[str, list[EventCluster]] = {}
        for cluster in items:
            hours.setdefault(hour_key(cluster.occurred_at), []).append(cluster)
        children = tuple(
            TimelineBucket.from_clusters(
                hour,
                hour_label(ensure_utc(group[0].occurred_at)),
                sort_clusters(group),
                level=BucketLevel.HOUR,
            )
            for hour, group in sorted(hours.items(), reverse=True)
        )
        result.append(
            TimelineBucket(
                key=key,
                label=day_label(moment, reference),
                level=BucketLevel.DAY,
                children=children,
            )
        )
    return tuple(result)


def cutoff_for_age(days: int, *, now: datetime | None = None) -> datetime:
    """Return the timestamp before which events are considered stale.

    Args:
        days: The maximum age in days.
        now: Reference time, defaulting to the current UTC time.

    Returns:
        The UTC cutoff timestamp.
    """
    reference = utcnow() if now is None else ensure_utc(now)
    return reference - timedelta(days=max(0, days))


def is_stale(event: TimelineEvent, cutoff: datetime) -> bool:
    """Return whether an event occurred strictly before the cutoff."""
    return ensure_utc(event.occurred_at) < ensure_utc(cutoff)


def build_stats(
    events: Iterable[TimelineEvent], *, generated_at: datetime | None = None
) -> TimelineStats:
    """Aggregate a collection of events into timeline statistics.

    Args:
        events: The events to aggregate.
        generated_at: Optional timestamp recorded on the result.

    Returns:
        The aggregated statistics.
    """
    materialised = tuple(events)
    moments = [ensure_utc(event.occurred_at) for event in materialised]
    critical = sum(1 for event in materialised if event.is_critical)
    return TimelineStats(
        total=len(materialised),
        by_kind=counts_by_kind(materialised),
        by_hour=counts_by_hour(materialised),
        by_importance=counts_by_importance(materialised),
        unique_actors=len({event.actor_id for event in materialised}),
        critical_count=critical,
        first_seen=min(moments) if moments else None,
        last_seen=max(moments) if moments else None,
        generated_at=generated_at or utcnow(),
    )


def take_unique(values: Iterable[_T]) -> tuple[_T, ...]:
    """Return distinct values in first appearance order."""
    seen: list[_T] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return tuple(seen)
