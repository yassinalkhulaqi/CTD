"""Business rules and orchestration for the activity timeline.

The service validates every caller supplied value, rejects malformed filters
with the shared typed errors and owns the decisions about deduplication,
grouping, aggregation and age based pruning.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import ensure_utc, utcnow
from ctf_team_dashboard.errors import NotFoundError, ValidationError
from ctf_team_dashboard.features.activity_timeline.models import (
    DEFAULT_DEDUPE_WINDOW_SECONDS,
    DEFAULT_LIMIT,
    DEFAULT_MAX_AGE_DAYS,
    MAX_ACTOR_NAME_LENGTH,
    MAX_IDENTIFIER_LENGTH,
    MAX_LIMIT,
    MAX_PAYLOAD_BYTES,
    MAX_SUMMARY_LENGTH,
    ActorSummary,
    EventCluster,
    Importance,
    PruneResult,
    TimelineBucket,
    TimelineEvent,
    TimelineFilter,
    TimelineKind,
    TimelinePage,
    TimelineStats,
    build_stats,
    build_timeline_groups,
    cutoff_for_age,
    deduplicate_events,
    encode_payload,
    normalise_summary,
    sort_clusters,
    validate_payload_size,
)
from ctf_team_dashboard.features.activity_timeline.store import TimelineStore


def _identifier(prefix: str) -> str:
    """Generate a short, readable unique identifier."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _clean_required(value: str, label: str, maximum: int) -> str:
    """Trim and validate a required text value.

    Args:
        value: The raw value.
        label: The field name used in error messages.
        maximum: The maximum accepted length.

    Returns:
        The trimmed value.

    Raises:
        ValidationError: When the value is empty or too long.
    """
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{label} must not be empty", details={"field": label})
    if len(cleaned) > maximum:
        raise ValidationError(
            f"{label} must not exceed {maximum} characters",
            details={"field": label, "maximum": maximum},
        )
    return cleaned


def _clean_kind(raw: str) -> str:
    """Validate and normalise an event kind.

    Args:
        raw: The kind supplied by the caller.

    Returns:
        The canonical kind value.

    Raises:
        ValidationError: When the kind is not recognised.
    """
    try:
        return str(TimelineKind.parse(raw))
    except ValueError as error:
        allowed = list(TimelineKind.values())
        raise ValidationError(
            f"Unknown timeline kind {raw!r}",
            details={"field": "kind", "allowed": allowed},
        ) from error


def _clean_importance(raw: str) -> str:
    """Validate and normalise an importance tier.

    Args:
        raw: The tier supplied by the caller.

    Returns:
        The canonical tier value.

    Raises:
        ValidationError: When the tier is not recognised.
    """
    try:
        return str(Importance.parse(raw))
    except ValueError as error:
        allowed = list(Importance.values())
        raise ValidationError(
            f"Unknown importance {raw!r}",
            details={"field": "importance", "allowed": allowed},
        ) from error


def _clean_payload(payload: Mapping[str, Any] | None) -> str:
    """Validate and encode a JSON payload mapping.

    Args:
        payload: The payload supplied by the caller.

    Returns:
        The compact JSON representation.

    Raises:
        ValidationError: When the payload is not a mapping or is too large.
    """
    if payload is None:
        return encode_payload(None)
    if not isinstance(payload, Mapping):
        raise ValidationError("payload must be a JSON object", details={"field": "payload"})
    encoded = encode_payload(payload)
    try:
        validate_payload_size(encoded)
    except ValueError as error:
        raise ValidationError(
            f"payload must not exceed {MAX_PAYLOAD_BYTES} bytes",
            details={"field": "payload", "maximum": MAX_PAYLOAD_BYTES},
        ) from error
    return encoded


def _clean_filter(timeline_filter: TimelineFilter) -> TimelineFilter:
    """Validate bounds and normalise the values of a query filter.

    Args:
        timeline_filter: The filter supplied by the caller.

    Returns:
        A validated filter with trimmed values.

    Raises:
        ValidationError: When pagination or the time window is invalid.
    """
    if timeline_filter.limit < 1 or timeline_filter.limit > MAX_LIMIT:
        raise ValidationError(
            f"limit must be between 1 and {MAX_LIMIT}",
            details={"field": "limit", "minimum": 1, "maximum": MAX_LIMIT},
        )
    if timeline_filter.offset < 0:
        raise ValidationError("offset must not be negative", details={"field": "offset"})
    if (
        timeline_filter.from_at is not None
        and timeline_filter.to_at is not None
        and ensure_utc(timeline_filter.from_at) > ensure_utc(timeline_filter.to_at)
    ):
        raise ValidationError("from must not be later than to", details={"field": "from"})
    clean_kinds = tuple(
        dict.fromkeys(_clean_kind(kind) for kind in timeline_filter.kinds if str(kind).strip())
    )
    clean_importance = tuple(
        dict.fromkeys(
            _clean_importance(value) for value in timeline_filter.importance if str(value).strip()
        )
    )
    clean_actors = tuple(
        dict.fromkeys(actor.strip() for actor in timeline_filter.actors if actor and actor.strip())
    )
    return TimelineFilter(
        kinds=clean_kinds,
        actors=clean_actors,
        importance=clean_importance,
        team_id=(timeline_filter.team_id.strip() if timeline_filter.team_id else None),
        from_at=timeline_filter.from_at,
        to_at=timeline_filter.to_at,
        limit=timeline_filter.limit,
        offset=timeline_filter.offset,
    )


class TimelineService:
    """Application rules for recording and reading team activity."""

    def __init__(self, store: TimelineStore | None = None) -> None:
        self.store = store or TimelineStore()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def record_event(
        self,
        *,
        team_id: str,
        kind: str,
        actor_id: str,
        actor_name: str,
        summary: str,
        payload: Mapping[str, Any] | None = None,
        importance: str = str(Importance.NORMAL),
        occurred_at: datetime | None = None,
    ) -> TimelineEvent:
        """Validate and persist a new timeline event.

        Args:
            team_id: The team the activity belongs to.
            kind: One of the recognised :class:`TimelineKind` values.
            actor_id: The identifier of the member or system causing it.
            actor_name: Display name of the actor.
            summary: A one line description of the activity.
            payload: Optional structured details.
            importance: The importance tier.
            occurred_at: Optional event time, defaulting to now.

        Returns:
            The persisted event.

        Raises:
            ValidationError: When any supplied field is invalid.
        """
        event = TimelineEvent(
            id=_identifier("evt"),
            team_id=_clean_required(team_id, "team_id", MAX_IDENTIFIER_LENGTH),
            kind=_clean_kind(kind),
            actor_id=_clean_required(actor_id, "actor_id", MAX_IDENTIFIER_LENGTH),
            actor_name=_clean_required(actor_name, "actor_name", MAX_ACTOR_NAME_LENGTH),
            summary=normalise_summary(_clean_required(summary, "summary", MAX_SUMMARY_LENGTH)),
            payload_json=_clean_payload(payload),
            importance=_clean_importance(importance),
            occurred_at=occurred_at or utcnow(),
        )
        return self.store.events.insert(event)

    def record_many(self, entries: Iterable[Mapping[str, Any]]) -> list[TimelineEvent]:
        """Record several events using the same validation rules.

        Args:
            entries: Mappings containing the keyword arguments of
                :meth:`record_event`.

        Returns:
            The persisted events in input order.
        """
        return [self.record_event(**dict(entry)) for entry in entries]

    def get_event(self, event_id: str) -> TimelineEvent:
        """Return a single event or raise :class:`NotFoundError`."""
        event = self.store.events.get(event_id)
        if event is None:
            raise NotFoundError(f"Timeline event {event_id!r} does not exist")
        return event

    def delete_event(self, event_id: str) -> None:
        """Delete an event, raising :class:`NotFoundError` when it is missing."""
        if not self.store.events.delete(event_id):
            raise NotFoundError(f"Timeline event {event_id!r} does not exist")

    # ------------------------------------------------------------------
    # Reading and grouping
    # ------------------------------------------------------------------
    def query(
        self,
        timeline_filter: TimelineFilter | None = None,
        *,
        deduplicate: bool = True,
        window_seconds: int = DEFAULT_DEDUPE_WINDOW_SECONDS,
    ) -> TimelinePage:
        """Return a validated, deduplicated and paginated timeline page.

        Args:
            timeline_filter: Optional filter, defaulting to the first page.
            deduplicate: Whether consecutive identical events should collapse.
            window_seconds: Maximum separation for deduplication.

        Returns:
            The page of clusters plus pagination metadata.
        """
        clean = _clean_filter(timeline_filter or TimelineFilter())
        events = self.store.events.matching(clean, limit=clean.limit, offset=clean.offset)
        total = self.store.events.count_matching(clean)
        clusters = self._cluster(events, deduplicate, window_seconds)
        return TimelinePage(clusters=clusters, total=total, limit=clean.limit, offset=clean.offset)

    def list_clusters(
        self,
        timeline_filter: TimelineFilter | None = None,
        *,
        deduplicate: bool = True,
        window_seconds: int = DEFAULT_DEDUPE_WINDOW_SECONDS,
    ) -> tuple[EventCluster, ...]:
        """Return clusters without pagination metadata."""
        return self.query(
            timeline_filter,
            deduplicate=deduplicate,
            window_seconds=window_seconds,
        ).clusters

    def groups(
        self,
        timeline_filter: TimelineFilter | None = None,
        *,
        now: datetime | None = None,
    ) -> tuple[TimelineBucket, ...]:
        """Return the timeline grouped into day and hour buckets.

        Args:
            timeline_filter: Optional filter applied before grouping.
            now: Reference time used for relative day labels.

        Returns:
            Day buckets with nested hourly children.
        """
        clusters = self.list_clusters(timeline_filter)
        return build_timeline_groups(clusters, now=now)

    def list_recent(
        self,
        limit: int = DEFAULT_LIMIT,
        team_id: str | None = None,
        *,
        deduplicate: bool = True,
    ) -> tuple[TimelineEvent, ...]:
        """Return the most recent events with optional deduplication.

        Args:
            limit: Maximum number of raw events to read.
            team_id: Optional team restriction.
            deduplicate: Whether to collapse consecutive duplicates.

        Returns:
            The most recent representative events.
        """
        bounded = max(1, min(limit, MAX_LIMIT))
        events = self.store.events.recent(bounded, team_id)
        clusters = self._cluster(events, deduplicate, DEFAULT_DEDUPE_WINDOW_SECONDS)
        return tuple(cluster.event for cluster in clusters)

    def stats(self, timeline_filter: TimelineFilter | None = None) -> TimelineStats:
        """Aggregate counts for all events matching a filter.

        Args:
            timeline_filter: Optional filter; pagination is ignored.

        Returns:
            The aggregated timeline statistics.
        """
        clean = _clean_filter(timeline_filter or TimelineFilter())
        unfiltered = TimelineFilter(
            kinds=clean.kinds,
            actors=clean.actors,
            importance=clean.importance,
            team_id=clean.team_id,
            from_at=clean.from_at,
            to_at=clean.to_at,
            limit=MAX_LIMIT,
            offset=0,
        )
        events = self.store.events.matching(unfiltered)
        return build_stats(events)

    def list_actors(self, team_id: str | None = None) -> tuple[ActorSummary, ...]:
        """Return actors ordered by activity for an optional team."""
        return tuple(self.store.events.actor_summaries(team_id))

    def list_kinds(self) -> tuple[str, ...]:
        """Return every kind currently stored, in stable order."""
        return self.store.events.distinct_kinds()

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    def prune(self, max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> PruneResult:
        """Delete events older than the configured maximum age.

        Args:
            max_age_days: Maximum age in days; must be positive.

        Returns:
            The number of deleted and retained events.

        Raises:
            ValidationError: When ``max_age_days`` is not positive.
        """
        if max_age_days < 1:
            raise ValidationError(
                "max_age_days must be at least 1",
                details={"field": "max_age_days", "minimum": 1},
            )
        now = utcnow()
        cutoff = cutoff_for_age(max_age_days, now=now)
        deleted = self.store.events.delete_before(cutoff)
        retained = self.store.events.count_matching(TimelineFilter(limit=MAX_LIMIT))
        return PruneResult(
            cutoff=cutoff, deleted=deleted, max_age_days=max_age_days, retained=retained
        )

    def prune_for_team(self, team_id: str, max_age_days: int) -> PruneResult:
        """Preview pruning for a team by counting stale events without deleting.

        Args:
            team_id: The team to inspect.
            max_age_days: The age threshold in days.

        Returns:
            A result whose ``deleted`` field holds the number of stale rows.
        """
        if max_age_days < 1:
            raise ValidationError(
                "max_age_days must be at least 1",
                details={"field": "max_age_days", "minimum": 1},
            )
        cutoff = cutoff_for_age(max_age_days)
        team_filter = TimelineFilter(
            team_id=_clean_required(team_id, "team_id", MAX_IDENTIFIER_LENGTH),
            to_at=cutoff,
        )
        stale = self.store.events.count_matching(team_filter)
        retained = self.store.events.count_matching(
            TimelineFilter(team_id=team_filter.team_id, limit=MAX_LIMIT)
        )
        return PruneResult(
            cutoff=cutoff,
            deleted=stale,
            max_age_days=max_age_days,
            retained=retained,
        )

    @staticmethod
    def _cluster(
        events: Iterable[TimelineEvent],
        deduplicate: bool,
        window_seconds: int,
    ) -> tuple[EventCluster, ...]:
        """Apply deduplication then stable display ordering to raw events."""
        materialised = tuple(events)
        if not deduplicate:
            return tuple(
                sort_clusters(
                    [
                        EventCluster(
                            event=event,
                            count=1,
                            first_at=event.occurred_at,
                            last_at=event.occurred_at,
                        )
                        for event in materialised
                    ]
                )
            )
        return sort_clusters(
            deduplicate_events(
                materialised,
                window_seconds=max(0, min(window_seconds, 86_400)),
            )
        )
