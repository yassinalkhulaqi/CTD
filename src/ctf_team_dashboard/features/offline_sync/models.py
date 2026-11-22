"""Domain model for the offline mutation queue and reconciliation engine.

The types in this module are deliberately pure: they carry no database or HTTP
concerns.  Every rule that decides whether a mutation conflicts with the server
and how a conflict is merged lives here so it can be exercised in isolation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ctf_team_dashboard.domain.models import ensure_utc, utcnow

_MISSING = object()


class MutationOperation(str, Enum):
    """The kind of change captured by a queued mutation."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class MutationStatus(str, Enum):
    """Lifecycle state of a mutation inside the queue."""

    PENDING = "pending"
    SYNCED = "synced"
    CONFLICT = "conflict"


class ConflictStrategy(str, Enum):
    """Policy used to reconcile a conflicting mutation."""

    LOCAL_WINS = "local_wins"
    REMOTE_WINS = "remote_wins"
    MERGE = "merge"


class VersionRelation(str, Enum):
    """Comparison of the client base version against the server version."""

    CURRENT = "current"
    REMOTE_AHEAD = "remote_ahead"
    REMOTE_BEHIND = "remote_behind"


class SyncOutcome(str, Enum):
    """Result of attempting to push a single mutation during a batch."""

    APPLIED = "applied"
    CONFLICT = "conflict"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class FieldChange:
    """Decision made for one field while reconciling a conflict."""

    field: str
    local_value: Any
    remote_value: Any
    chosen_value: Any
    contested: bool = False

    @property
    def chose_local(self) -> bool:
        """Return whether the local value survived the reconciliation."""
        return not self.contested and self.chosen_value == self.local_value

    @property
    def chose_remote(self) -> bool:
        """Return whether the remote value survived the reconciliation."""
        return self.remote_value is not _MISSING and self.chosen_value == self.remote_value

    @property
    def was_removed(self) -> bool:
        """Return whether the field is absent from the resolved payload."""
        return self.chosen_value is _MISSING

    @property
    def summary(self) -> str:
        """Return a short human readable description of the decision."""
        if self.contested:
            return f"{self.field}: both sides changed, kept local"
        if self.was_removed:
            return f"{self.field}: removed"
        if self.chose_local:
            return f"{self.field}: kept local value"
        if self.chose_remote:
            return f"{self.field}: accepted remote value"
        return f"{self.field}: unchanged"


@dataclass(frozen=True, slots=True)
class MergeResult:
    """Payload and per-field decisions produced by a merge strategy."""

    strategy: ConflictStrategy
    payload: dict[str, Any]
    changes: tuple[FieldChange, ...] = ()

    @property
    def contested_fields(self) -> tuple[str, ...]:
        """Return the names of fields both sides edited differently."""
        return tuple(change.field for change in self.changes if change.contested)

    @property
    def is_clean(self) -> bool:
        """Return whether no field needed a contested-value decision."""
        return not self.contested_fields

    @property
    def field_count(self) -> int:
        """Return the number of fields considered during the merge."""
        return len(self.changes)

    def to_json(self) -> str:
        """Serialise the field decisions for persistence on a resolution row."""
        encoded = [
            {
                "field": change.field,
                "local": _serialisable(change.local_value),
                "remote": _serialisable(change.remote_value),
                "chosen": _serialisable(change.chosen_value),
                "contested": change.contested,
            }
            for change in self.changes
        ]
        return json.dumps(encoded, separators=(",", ":"), sort_keys=True)


def _serialisable(value: Any) -> Any:
    """Convert a merge value into a JSON friendly representation."""
    if value is _MISSING:
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return json.dumps(value, separators=(",", ":"), sort_keys=True, default=str)


def _value(mapping: dict[str, Any], key: str) -> Any:
    """Return a mapping value or the missing sentinel."""
    return mapping.get(key, _MISSING)


def display_value(value: Any) -> Any:
    """Convert the internal missing sentinel into a JSON friendly ``None``."""
    return None if value is _MISSING else value


def merge_payloads(
    base: dict[str, Any],
    local: dict[str, Any],
    remote: dict[str, Any],
    strategy: ConflictStrategy,
) -> MergeResult:
    """Reconcile three JSON object snapshots using the requested strategy.

    ``local_wins`` overlays every local field on the remote snapshot, while
    ``remote_wins`` does the inverse.  ``merge`` performs a three-way merge: a
    field that only one side changed keeps that side's value, and a field both
    sides changed differently keeps the local value but is reported as
    contested so the UI can surface it.

    Args:
        base: The payload the client saw when the mutation was queued.
        local: The payload captured by the queued mutation.
        remote: The payload currently held by the server.
        strategy: The reconciliation policy to apply.

    Returns:
        The resolved payload together with one decision per touched field.
    """
    keys = sorted(set(base) | set(local) | set(remote))

    if strategy is ConflictStrategy.LOCAL_WINS:
        payload = dict(remote)
        payload.update(local)
        changes = tuple(
            FieldChange(
                field=key,
                local_value=_value(local, key),
                remote_value=_value(remote, key),
                chosen_value=_value(payload, key),
                contested=False,
            )
            for key in keys
            if key in local or key in remote
        )
        return MergeResult(strategy=strategy, payload=payload, changes=changes)

    if strategy is ConflictStrategy.REMOTE_WINS:
        payload = dict(local)
        payload.update(remote)
        changes = tuple(
            FieldChange(
                field=key,
                local_value=_value(local, key),
                remote_value=_value(remote, key),
                chosen_value=_value(payload, key),
                contested=False,
            )
            for key in keys
            if key in local or key in remote
        )
        return MergeResult(strategy=strategy, payload=payload, changes=changes)

    merged_payload: dict[str, Any] = {}
    decisions: list[FieldChange] = []
    for key in keys:
        local_value = _value(local, key)
        remote_value = _value(remote, key)
        base_value = _value(base, key)

        if local_value == remote_value:
            chosen = local_value
            contested = False
        elif local_value == base_value:
            chosen = remote_value
            contested = False
        elif remote_value == base_value:
            chosen = local_value
            contested = False
        else:
            chosen = local_value
            contested = True

        if chosen is not _MISSING:
            merged_payload[key] = chosen
        decisions.append(
            FieldChange(
                field=key,
                local_value=local_value,
                remote_value=remote_value,
                chosen_value=chosen,
                contested=contested,
            )
        )
    return MergeResult(strategy=strategy, payload=merged_payload, changes=tuple(decisions))


def compare_versions(base_version: int, current_version: int) -> VersionRelation:
    """Classify how the server version compares with the client base version."""
    if current_version == base_version:
        return VersionRelation.CURRENT
    if current_version > base_version:
        return VersionRelation.REMOTE_AHEAD
    return VersionRelation.REMOTE_BEHIND


def detect_version_conflict(base_version: int, current_version: int) -> bool:
    """Return whether a mutation based on ``base_version`` is now stale."""
    return compare_versions(base_version, current_version) is not VersionRelation.CURRENT


def retry_delay_seconds(attempt: int, base: float = 2.0, cap: float = 60.0) -> float:
    """Return the exponential backoff delay after ``attempt`` failed pushes."""
    exponent = max(0, min(attempt, 10))
    return float(min(cap, base * 2**exponent))


@dataclass(frozen=True, slots=True)
class PendingMutation:
    """A change recorded locally while the dashboard was offline."""

    id: str
    client_id: str
    entity: str
    operation: MutationOperation
    payload_json: str
    base_version: int
    created_at: datetime
    status: MutationStatus = MutationStatus.PENDING
    attempts: int = 0
    last_error: str = ""
    resolved_version: int | None = None

    @property
    def payload(self) -> dict[str, Any]:
        """Return the decoded JSON payload of the mutation."""
        decoded = json.loads(self.payload_json)
        if not isinstance(decoded, dict):
            return {}
        return {str(key): value for key, value in decoded.items()}

    @property
    def is_pending(self) -> bool:
        """Return whether the mutation still waits to be pushed."""
        return self.status is MutationStatus.PENDING

    @property
    def is_synced(self) -> bool:
        """Return whether the mutation reached the server."""
        return self.status is MutationStatus.SYNCED

    @property
    def is_conflicted(self) -> bool:
        """Return whether the mutation needs a conflict decision."""
        return self.status is MutationStatus.CONFLICT

    @property
    def is_retryable(self) -> bool:
        """Return whether another push attempt is allowed."""
        return self.is_pending and self.attempts < 5

    @property
    def next_retry_delay(self) -> float:
        """Return the backoff in seconds before the next push attempt."""
        return retry_delay_seconds(self.attempts)

    @property
    def entity_label(self) -> str:
        """Return a human friendly label for the mutated entity."""
        return self.entity.replace("_", " ").replace("-", " ").title()

    @property
    def queue_key(self) -> tuple[str, str]:
        """Return the stable FIFO ordering key of the mutation."""
        return (ensure_utc(self.created_at).isoformat(), self.id)

    def age_seconds(self, now: datetime | None = None) -> float:
        """Return how long the mutation has waited in the queue."""
        reference = ensure_utc(now if now is not None else utcnow())
        return max(0.0, (reference - ensure_utc(self.created_at)).total_seconds())

    def mark_attempt(self, error: str = "") -> PendingMutation:
        """Return a copy with one more push attempt recorded."""
        return replace(
            self,
            status=MutationStatus.PENDING,
            attempts=self.attempts + 1,
            last_error=error,
        )

    def mark_synced(self, version: int) -> PendingMutation:
        """Return a copy marked as successfully synchronised."""
        return replace(
            self,
            status=MutationStatus.SYNCED,
            last_error="",
            resolved_version=version,
        )

    def mark_conflict(self, version: int, detail: str) -> PendingMutation:
        """Return a copy paused at a version conflict."""
        return replace(
            self,
            status=MutationStatus.CONFLICT,
            last_error=detail,
            resolved_version=version,
        )

    def with_payload(self, payload: dict[str, Any]) -> PendingMutation:
        """Return a copy carrying a reconciled payload."""
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return replace(self, payload_json=encoded)

    def requeue(self) -> PendingMutation:
        """Return a copy returned to the pending queue after a decision."""
        return replace(self, status=MutationStatus.PENDING, last_error="")


@dataclass(frozen=True, slots=True)
class SyncSnapshot:
    """A record of one completed batch of synchronisation work."""

    id: str
    client_id: str
    synced_at: datetime
    version: int
    mutation_count: int = 0
    conflict_count: int = 0
    note: str = ""

    @property
    def total_count(self) -> int:
        """Return the number of mutations considered in the batch."""
        return self.mutation_count + self.conflict_count

    @property
    def success_rate(self) -> float:
        """Return the fraction of mutations that were applied cleanly."""
        if self.total_count == 0:
            return 1.0
        return self.mutation_count / self.total_count

    def age_seconds(self, now: datetime | None = None) -> float:
        """Return how long ago the snapshot was taken."""
        reference = ensure_utc(now if now is not None else utcnow())
        return max(0.0, (reference - ensure_utc(self.synced_at)).total_seconds())

    def is_fresh(self, max_age_seconds: float, now: datetime | None = None) -> bool:
        """Return whether the snapshot is within the freshness window."""
        return self.age_seconds(now) <= max_age_seconds

    @property
    def label(self) -> str:
        """Return a concise summary of the snapshot."""
        return f"v{self.version} · {self.mutation_count} applied"


@dataclass(frozen=True, slots=True)
class ConflictResolution:
    """The Choice a user made to settle a conflicting mutation."""

    id: str
    mutation_id: str
    strategy: ConflictStrategy
    resolved_at: datetime
    local_version: int
    remote_version: int
    field_changes_json: str = "[]"
    notes: str = ""

    @property
    def changes(self) -> tuple[FieldChange, ...]:
        """Return the decoded per-field decisions."""
        try:
            raw = json.loads(self.field_changes_json)
        except json.JSONDecodeError:
            return ()
        if not isinstance(raw, list):
            return ()
        decoded: list[FieldChange] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            decoded.append(
                FieldChange(
                    field=str(item.get("field", "")),
                    local_value=item.get("local"),
                    remote_value=item.get("remote"),
                    chosen_value=item.get("chosen"),
                    contested=bool(item.get("contested", False)),
                )
            )
        return tuple(decoded)

    @property
    def was_merged(self) -> bool:
        """Return whether the resolution used field level merging."""
        return self.strategy is ConflictStrategy.MERGE

    @property
    def version_gap(self) -> int:
        """Return the distance between the local and remote versions."""
        return abs(self.remote_version - self.local_version)

    @property
    def strategy_label(self) -> str:
        """Return the human friendly name of the chosen strategy."""
        return self.strategy.value.replace("_", " ").title()

    @property
    def summary(self) -> str:
        """Return a short description suitable for a list row."""
        base = f"{self.strategy_label} across {self.version_gap} version(s)"
        return f"{base} · {len(self.changes)} field(s)"


@dataclass(frozen=True, slots=True)
class MutationOutcome:
    """The result of pushing one mutation during a batch."""

    mutation_id: str
    entity: str
    operation: MutationOperation
    result: SyncOutcome
    detail: str = ""

    @property
    def succeeded(self) -> bool:
        """Return whether the mutation was applied to the server."""
        return self.result is SyncOutcome.APPLIED

    @property
    def needs_attention(self) -> bool:
        """Return whether the user must intervene after this outcome."""
        return self.result in (SyncOutcome.CONFLICT, SyncOutcome.FAILED)


@dataclass(frozen=True, slots=True)
class SyncStats:
    """Aggregated queue health used by the status card."""

    pending: int = 0
    synced: int = 0
    conflict: int = 0
    total: int = 0
    attempts: int = 0
    oldest_pending: datetime | None = None
    newest_synced: datetime | None = None

    @property
    def has_conflicts(self) -> bool:
        """Return whether any mutation is blocked by a conflict."""
        return self.conflict > 0

    @property
    def backlog(self) -> int:
        """Return the number of mutations still requiring work."""
        return self.pending + self.conflict

    @property
    def completion_rate(self) -> float:
        """Return the fraction of all mutations already synchronised."""
        if self.total <= 0:
            return 1.0
        return self.synced / self.total

    @property
    def average_attempts(self) -> float:
        """Return the mean number of push attempts per mutation."""
        if self.total <= 0:
            return 0.0
        return self.attempts / self.total

    @property
    def health_label(self) -> str:
        """Return a coarse health label for display in the UI."""
        if self.has_conflicts:
            return "attention"
        if self.pending > 0:
            return "syncing"
        if self.total == 0:
            return "idle"
        return "healthy"

    def stalled_for(self, threshold: timedelta, now: datetime | None = None) -> bool:
        """Return whether the oldest pending mutation exceeds a threshold."""
        if self.oldest_pending is None:
            return False
        reference = ensure_utc(now if now is not None else utcnow())
        return reference - ensure_utc(self.oldest_pending) > threshold


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Summary returned after processing a batch of queued mutations."""

    outcomes: tuple[MutationOutcome, ...] = ()
    applied: int = 0
    conflicts: int = 0
    skipped: int = 0
    failed: int = 0
    snapshot: SyncSnapshot | None = None
    started_at: datetime = field(default_factory=utcnow)
    finished_at: datetime = field(default_factory=utcnow)

    @property
    def processed(self) -> int:
        """Return the number of mutations examined in the batch."""
        return len(self.outcomes)

    @property
    def duration_seconds(self) -> float:
        """Return the wall clock duration of the batch."""
        delta = ensure_utc(self.finished_at) - ensure_utc(self.started_at)
        return max(0.0, delta.total_seconds())

    @property
    def success_rate(self) -> float:
        """Return the fraction of examined mutations that were applied."""
        if self.processed <= 0:
            return 1.0
        return self.applied / self.processed

    @property
    def had_failures(self) -> bool:
        """Return whether any mutation failed or conflicted."""
        return self.failed > 0 or self.conflicts > 0

    @property
    def attention_ids(self) -> tuple[str, ...]:
        """Return identifiers of mutations the user must review."""
        return tuple(item.mutation_id for item in self.outcomes if item.needs_attention)


def fifo_order(mutations: list[PendingMutation]) -> list[PendingMutation]:
    """Sort mutations by creation time and identifier, oldest first."""
    return sorted(mutations, key=lambda mutation: mutation.queue_key)


def summarise_mutations(mutations: list[PendingMutation]) -> SyncStats:
    """Build queue statistics from a collection of mutations."""
    pending = 0
    synced = 0
    conflict = 0
    attempts = 0
    oldest: datetime | None = None
    newest: datetime | None = None

    for mutation in mutations:
        attempts += mutation.attempts
        if mutation.status is MutationStatus.PENDING:
            pending += 1
            if oldest is None or mutation.created_at < oldest:
                oldest = mutation.created_at
        elif mutation.status is MutationStatus.SYNCED:
            synced += 1
            if newest is None or mutation.created_at > newest:
                newest = mutation.created_at
        else:
            conflict += 1

    return SyncStats(
        pending=pending,
        synced=synced,
        conflict=conflict,
        total=len(mutations),
        attempts=attempts,
        oldest_pending=oldest,
        newest_synced=newest,
    )
