"""Tests for the V3 offline mutation queue and synchronisation feature."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.offline_sync import SCHEMA_SQL
from ctf_team_dashboard.features.offline_sync.models import (
    BatchResult,
    ConflictStrategy,
    MutationOperation,
    MutationOutcome,
    MutationStatus,
    PendingMutation,
    SyncOutcome,
    SyncStats,
    compare_versions,
    detect_version_conflict,
    fifo_order,
    merge_payloads,
    retry_delay_seconds,
    summarise_mutations,
)
from ctf_team_dashboard.features.offline_sync.service import OfflineSyncService
from ctf_team_dashboard.features.offline_sync.store import SyncStore

START = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def fixed_clock(start: datetime = START) -> Callable[[], datetime]:
    """Return a clock that advances one second on every read."""
    current = start

    def clock() -> datetime:
        nonlocal current
        current += timedelta(seconds=1)
        return current

    return clock


def make_mutation(
    identifier: str,
    created_at: datetime,
    **overrides: Any,
) -> PendingMutation:
    """Build a deterministic mutation for pure domain tests."""
    mutation = PendingMutation(
        id=identifier,
        client_id="client-a",
        entity="note",
        operation=MutationOperation.UPDATE,
        payload_json='{"title":"local"}',
        base_version=1,
        created_at=created_at,
    )
    return replace(mutation, **overrides)


@pytest.fixture
def service(database: Database) -> OfflineSyncService:
    """Return a sync service bound to the isolated test database."""
    return OfflineSyncService(clock=fixed_clock())


class TestDomainRules:
    """Pure rules that need no database."""

    def test_enums_serialize_as_lowercase_strings(self) -> None:
        assert MutationOperation.CREATE.value == "create"
        assert MutationStatus.CONFLICT.value == "conflict"
        assert ConflictStrategy.LOCAL_WINS.value == "local_wins"

    @pytest.mark.parametrize(
        ("base", "current", "expected"),
        [
            (1, 1, "current"),
            (1, 4, "remote_ahead"),
            (4, 1, "remote_behind"),
        ],
    )
    def test_compare_versions_classifies_relations(
        self, base: int, current: int, expected: str
    ) -> None:
        assert compare_versions(base, current).value == expected
        assert detect_version_conflict(base, current) is (expected != "current")

    def test_merge_local_wins_overlays_every_local_field(self) -> None:
        result = merge_payloads(
            {"title": "old", "body": "shared"},
            {"title": "local", "extra": 1},
            {"title": "remote", "body": "changed"},
            ConflictStrategy.LOCAL_WINS,
        )
        assert result.payload == {
            "title": "local",
            "body": "changed",
            "extra": 1,
        }
        assert result.is_clean
        assert result.field_count == 3

    def test_merge_remote_wins_overlays_every_remote_field(self) -> None:
        result = merge_payloads(
            {"title": "old", "body": "shared"},
            {"title": "local", "extra": 1},
            {"title": "remote", "body": "changed"},
            ConflictStrategy.REMOTE_WINS,
        )
        assert result.payload["title"] == "remote"
        assert result.payload["body"] == "changed"
        assert result.payload["extra"] == 1
        assert all(not change.contested for change in result.changes)

    def test_merge_three_way_keeps_single_side_changes(self) -> None:
        result = merge_payloads(
            {"title": "old", "body": "shared", "tags": "a"},
            {"title": "local", "body": "shared", "tags": "a"},
            {"title": "old", "body": "remote", "tags": "a"},
            ConflictStrategy.MERGE,
        )
        assert result.payload == {"title": "local", "body": "remote", "tags": "a"}
        assert result.is_clean
        assert [change.field for change in result.changes] == ["body", "tags", "title"]

    def test_merge_three_way_marks_contested_fields(self) -> None:
        result = merge_payloads(
            {"title": "old", "body": "shared"},
            {"title": "local", "body": "local-only"},
            {"title": "remote", "body": "shared"},
            ConflictStrategy.MERGE,
        )
        assert result.contested_fields == ("title",)
        assert not result.is_clean
        assert result.payload["title"] == "local"
        assert "both sides changed" in result.changes[-1].summary
        assert "title" in result.to_json()

    def test_retry_delay_uses_bounded_exponential_backoff(self) -> None:
        assert retry_delay_seconds(0) == 2.0
        assert retry_delay_seconds(1) == 4.0
        assert retry_delay_seconds(3) == 16.0
        assert retry_delay_seconds(20, cap=30.0) == 30.0

    def test_fifo_order_uses_time_then_identifier(self) -> None:
        older = make_mutation("b", START)
        newer = make_mutation("a", START + timedelta(seconds=1))
        same_time = make_mutation("c", START)
        ordered = fifo_order([newer, older, same_time])
        assert [item.id for item in ordered] == ["b", "c", "a"]

    def test_summarise_mutations_counts_every_status(self) -> None:
        mutations = [
            make_mutation("a", START),
            make_mutation("b", START + timedelta(seconds=1), attempts=2),
            make_mutation(
                "c",
                START + timedelta(seconds=2),
                status=MutationStatus.SYNCED,
            ),
            make_mutation(
                "d",
                START + timedelta(seconds=3),
                status=MutationStatus.CONFLICT,
            ),
        ]
        stats = summarise_mutations(mutations)
        assert stats.pending == 2
        assert stats.synced == 1
        assert stats.conflict == 1
        assert stats.total == 4
        assert stats.attempts == 2
        assert stats.has_conflicts
        assert stats.backlog == 3
        assert stats.health_label == "attention"
        assert stats.completion_rate == 0.25
        assert stats.oldest_pending is not None

    def test_mutation_transition_helpers_are_pure(self) -> None:
        mutation = make_mutation("a", START)
        attempted = mutation.mark_attempt("network down")
        assert mutation.attempts == 0
        assert attempted.attempts == 1
        assert attempted.last_error == "network down"
        assert attempted.is_retryable

        synced = attempted.mark_synced(7)
        assert synced.is_synced
        assert synced.resolved_version == 7
        assert synced.last_error == ""

        conflicted = attempted.mark_conflict(9, "stale")
        assert conflicted.is_conflicted
        assert conflicted.resolved_version == 9
        assert conflicted.requeue().is_pending

        changed = mutation.with_payload({"title": "reconciled"})
        assert changed.payload == {"title": "reconciled"}
        assert mutation.payload == {"title": "local"}
        assert mutation.entity_label == "Note"
        assert mutation.age_seconds(START + timedelta(minutes=1)) == 60.0

    def test_batch_and_stats_derived_properties(self) -> None:
        batch = BatchResult(
            outcomes=(
                MutationOutcome(
                    "a",
                    "note",
                    MutationOperation.UPDATE,
                    SyncOutcome.APPLIED,
                ),
                MutationOutcome(
                    "b",
                    "note",
                    MutationOperation.DELETE,
                    SyncOutcome.CONFLICT,
                    "stale",
                ),
            ),
            applied=1,
            conflicts=1,
        )
        assert batch.processed == 2
        assert batch.success_rate == 0.5
        assert batch.had_failures
        assert batch.attention_ids == ("b",)
        assert batch.outcomes[0].succeeded
        assert batch.outcomes[1].needs_attention

        empty = SyncStats()
        assert empty.completion_rate == 1.0
        assert empty.average_attempts == 0.0
        assert empty.health_label == "idle"
        assert not empty.stalled_for(timedelta(seconds=1))


class TestStoreAndService:
    """Persistence and orchestration rules against a real SQLite database."""

    def test_migrate_creates_all_feature_tables(
        self, database: Database, service: OfflineSyncService
    ) -> None:
        names = database.table_names()
        assert {"v3_pending_mutations", "v3_sync_snapshots", "v3_conflict_resolutions"} <= names
        assert "v3_pending_mutations" in SCHEMA_SQL

    def test_enqueue_persists_mutation_and_rejects_duplicates(
        self, service: OfflineSyncService
    ) -> None:
        mutation = service.enqueue(
            client_id="phone",
            entity="note",
            operation=MutationOperation.CREATE,
            payload={"title": "Draft", "tags": ["crypto"]},
            base_version=0,
            mutation_id="mut-1",
        )
        assert mutation.id == "mut-1"
        assert mutation.is_pending
        assert service.get_mutation("mut-1").payload["title"] == "Draft"

        with pytest.raises(ConflictError) as exc:
            service.enqueue(
                client_id="phone",
                entity="note",
                operation=MutationOperation.UPDATE,
                payload={},
                mutation_id="mut-1",
            )
        assert exc.value.status_code == 409

    @pytest.mark.parametrize(
        ("client_id", "entity", "base_version"),
        [
            ("", "note", 0),
            ("phone", "", 0),
            ("phone", "note", -1),
        ],
    )
    def test_enqueue_validates_inputs(
        self,
        service: OfflineSyncService,
        client_id: str,
        entity: str,
        base_version: int,
    ) -> None:
        with pytest.raises(ValidationError):
            service.enqueue(
                client_id=client_id,
                entity=entity,
                operation=MutationOperation.UPDATE,
                payload={},
                base_version=base_version,
            )

    def test_list_queue_is_fifo_and_filterable(self, service: OfflineSyncService) -> None:
        for index in range(3):
            service.enqueue(
                client_id="phone",
                entity="note" if index != 1 else "challenge",
                operation=MutationOperation.UPDATE,
                payload={"index": index},
                mutation_id=f"mut-{index}",
            )
        service.enqueue(
            client_id="laptop",
            entity="note",
            operation=MutationOperation.DELETE,
            payload={},
            mutation_id="mut-laptop",
        )
        queue = service.list_queue(client_id="phone")
        assert [item.id for item in queue] == ["mut-0", "mut-1", "mut-2"]
        assert [item.id for item in service.list_queue(entity="challenge")] == ["mut-1"]
        assert len(service.list_queue(limit=2)) == 2
        assert service.stats(client_id="phone").total == 3

    def test_process_batch_applies_and_snapshots(self, service: OfflineSyncService) -> None:
        for index in range(2):
            service.enqueue(
                client_id="phone",
                entity="note",
                operation=MutationOperation.UPDATE,
                payload={"index": index},
                base_version=1,
                mutation_id=f"mut-{index}",
            )
        result = service.process_batch(current_versions={"note": 1})
        assert result.applied == 2
        assert result.conflicts == 0
        assert result.processed == 2
        assert result.success_rate == 1.0
        assert result.snapshot is not None
        assert result.snapshot.version == 2
        assert service.stats().synced == 2
        assert service.stats().pending == 0
        snapshot = service.latest_snapshot()
        assert snapshot is not None
        assert snapshot.version == 2

    def test_process_batch_detects_version_conflict(self, service: OfflineSyncService) -> None:
        service.enqueue(
            client_id="phone",
            entity="note",
            operation=MutationOperation.UPDATE,
            payload={"title": "offline edit"},
            base_version=1,
            mutation_id="mut-conflict",
        )
        result = service.process_batch(current_versions={"note": 4})
        assert result.conflicts == 1
        assert result.applied == 0
        assert result.attention_ids == ("mut-conflict",)
        assert "Version conflict" in result.outcomes[0].detail
        assert service.get_mutation("mut-conflict").is_conflicted
        assert service.stats().has_conflicts

    def test_process_batch_exhausts_retry_budget(self, service: OfflineSyncService) -> None:
        service.enqueue(
            client_id="phone",
            entity="note",
            operation=MutationOperation.UPDATE,
            payload={},
            mutation_id="mut-retry",
        )
        service._store.mutations.save(replace(service.get_mutation("mut-retry"), attempts=5))
        result = service.process_batch()
        assert result.failed == 1
        assert result.outcomes[0].result is SyncOutcome.FAILED
        assert "Retry limit" in result.outcomes[0].detail

    def test_resolve_conflict_local_wins_marks_synced(self, service: OfflineSyncService) -> None:
        service.enqueue(
            client_id="phone",
            entity="note",
            operation=MutationOperation.UPDATE,
            payload={"title": "local"},
            base_version=2,
            mutation_id="mut-1",
        )
        service.process_batch(current_versions={"note": 3})
        resolution = service.resolve_conflict("mut-1", ConflictStrategy.LOCAL_WINS)
        assert resolution.strategy is ConflictStrategy.LOCAL_WINS
        assert resolution.local_version == 2
        assert resolution.remote_version == 3
        assert service.get_mutation("mut-1").is_synced
        assert service.get_mutation("mut-1").payload["title"] == "local"
        assert service.resolution_count() == 1

    def test_resolve_conflict_merge_records_field_changes(
        self, service: OfflineSyncService
    ) -> None:
        service.enqueue(
            client_id="phone",
            entity="note",
            operation=MutationOperation.UPDATE,
            payload={"title": "local", "body": "unchanged"},
            base_version=2,
            mutation_id="mut-2",
        )
        service.process_batch(current_versions={"note": 3})
        resolution = service.resolve_conflict(
            "mut-2",
            ConflictStrategy.MERGE,
            note="Reviewed with the team",
            base_payload={"title": "old", "body": "unchanged"},
            remote_payload={"title": "remote", "body": "remote body"},
        )
        assert resolution.was_merged
        assert resolution.notes == "Reviewed with the team"
        assert [change.field for change in resolution.changes] == ["body", "title"]
        assert resolution.summary.startswith("Merge")
        assert service.get_mutation("mut-2").payload["body"] == "remote body"

    def test_resolve_conflict_rejects_non_conflicted_mutation(
        self, service: OfflineSyncService
    ) -> None:
        service.enqueue(
            client_id="phone",
            entity="note",
            operation=MutationOperation.CREATE,
            payload={},
            mutation_id="mut-3",
        )
        with pytest.raises(ConflictError):
            service.resolve_conflict("mut-3", ConflictStrategy.REMOTE_WINS)
        with pytest.raises(NotFoundError):
            service.resolve_conflict("missing", ConflictStrategy.MERGE)

    def test_retry_conflict_returns_mutation_to_queue(self, service: OfflineSyncService) -> None:
        service.enqueue(
            client_id="phone",
            entity="note",
            operation=MutationOperation.UPDATE,
            payload={},
            base_version=1,
            mutation_id="mut-4",
        )
        service.process_batch(current_versions={"note": 2})
        requeued = service.retry_conflict("mut-4")
        assert requeued.is_pending
        assert requeued.last_error == ""
        assert service.stats().pending == 1
        assert service.stats().conflict == 0

    def test_clear_synced_keeps_pending_and_conflicted(self, service: OfflineSyncService) -> None:
        for index in range(3):
            service.enqueue(
                client_id="phone",
                entity="note",
                operation=MutationOperation.UPDATE,
                payload={"index": index},
                base_version=1,
                mutation_id=f"mut-{index}",
            )
        service.process_batch(current_versions={"note": 1})
        service._store.mutations.save(
            replace(
                service.get_mutation("mut-0"),
                status=MutationStatus.CONFLICT,
            )
        )
        service.enqueue(
            client_id="phone",
            entity="note",
            operation=MutationOperation.UPDATE,
            payload={},
            mutation_id="mut-new",
        )
        deleted = service.clear_synced(client_id="phone")
        assert deleted == 2
        assert service.stats().total == 2
        assert service.get_mutation("mut-0").is_conflicted
        assert service.get_mutation("mut-new").is_pending

    def test_store_direct_reads_and_filters(self, service: OfflineSyncService) -> None:
        store = SyncStore()
        service.enqueue(
            client_id="phone",
            entity="note",
            operation=MutationOperation.CREATE,
            payload={},
            mutation_id="mut-direct",
        )
        assert store.mutations.count_by_status(client_id="phone") == {"pending": 1}
        assert store.mutations.total_attempts() == 0
        assert store.mutations.oldest_pending_at() == START + timedelta(seconds=1)
        assert store.mutations.newest_synced_at() is None
        assert store.snapshots.highest_version() == 0
        assert store.conflicts.count_resolutions() == 0
        assert store.conflicts.for_mutation("mut-direct") is None
        assert service.list_resolutions() == []


class TestApi:
    """HTTP level behaviour of the six sync endpoints."""

    def test_enqueue_and_list_queue(self, client: TestClient) -> None:
        response = client.post(
            "/api/sync/mutations",
            json={
                "client_id": "phone",
                "entity": "note",
                "operation": "update",
                "payload": {"title": "Draft"},
                "base_version": 1,
                "mutation_id": "api-1",
            },
        )
        assert response.status_code == 201
        assert response.json()["id"] == "api-1"
        assert response.json()["status"] == "pending"
        assert response.json()["entity_label"] == "Note"

        queue = client.get("/api/sync/queue", params={"client_id": "phone"})
        assert queue.status_code == 200
        body = queue.json()
        assert body["total"] == 1
        assert body["pending"] == 1
        assert body["items"][0]["payload"] == {"title": "Draft"}

        filtered = client.get("/api/sync/queue", params={"status": "synced"})
        assert filtered.json()["total"] == 0

    def test_process_and_status_endpoints(self, client: TestClient) -> None:
        for index in range(2):
            client.post(
                "/api/sync/mutations",
                json={
                    "client_id": "phone",
                    "entity": "note",
                    "operation": "create",
                    "payload": {"index": index},
                    "mutation_id": f"api-{index}",
                },
            )
        processed = client.post(
            "/api/sync/process",
            json={"current_versions": {"note": 0}, "limit": 10},
        )
        assert processed.status_code == 200
        body = processed.json()
        assert body["applied"] == 2
        assert body["processed"] == 2
        assert body["snapshot"]["version"] == 1

        status = client.get("/api/sync/status")
        assert status.status_code == 200
        payload = status.json()
        assert payload["synced"] == 2
        assert payload["health_label"] == "healthy"
        assert payload["latest_snapshot"]["mutation_count"] == 2
        assert payload["stale"] is False

    def test_full_conflict_resolution_flow(self, client: TestClient) -> None:
        client.post(
            "/api/sync/mutations",
            json={
                "client_id": "phone",
                "entity": "note",
                "operation": "update",
                "payload": {"title": "local", "body": "same"},
                "base_version": 1,
                "mutation_id": "api-conflict",
            },
        )
        processed = client.post(
            "/api/sync/process",
            json={"current_versions": {"note": 3}},
        )
        assert processed.json()["conflicts"] == 1
        assert processed.json()["outcomes"][0]["needs_attention"] is True

        resolved = client.post(
            "/api/sync/conflicts/api-conflict/resolve",
            json={
                "strategy": "merge",
                "note": "kept both edits",
                "base_payload": {"title": "old", "body": "same"},
                "remote_payload": {"title": "remote", "body": "remote body"},
            },
        )
        assert resolved.status_code == 200
        body = resolved.json()
        assert body["strategy"] == "merge"
        assert body["remote_version"] == 3
        assert any(field["contested"] for field in body["field_changes"])

        queue = client.get("/api/sync/queue", params={"status": "synced"})
        assert queue.json()["total"] == 1

    def test_clear_queue_endpoint(self, client: TestClient) -> None:
        client.post(
            "/api/sync/mutations",
            json={
                "client_id": "phone",
                "entity": "note",
                "operation": "create",
                "payload": {},
                "mutation_id": "api-clear",
            },
        )
        client.post("/api/sync/process", json={})
        cleared = client.delete("/api/sync/queue", params={"client_id": "phone"})
        assert cleared.status_code == 200
        assert cleared.json()["deleted"] == 1
        assert cleared.json()["remaining"] == 0

    def test_api_returns_typed_error_envelopes(self, client: TestClient) -> None:
        invalid = client.post(
            "/api/sync/mutations",
            json={
                "client_id": "phone",
                "entity": "note",
                "operation": "update",
                "payload": {},
                "mutation_id": "   ",
            },
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "validation_error"

        duplicate_payload = {
            "client_id": "phone",
            "entity": "note",
            "operation": "update",
            "payload": {},
            "mutation_id": "api-dup",
        }
        assert client.post("/api/sync/mutations", json=duplicate_payload).status_code == 201
        duplicate = client.post("/api/sync/mutations", json=duplicate_payload)
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "conflict"

        missing = client.post(
            "/api/sync/conflicts/missing/resolve",
            json={"strategy": "local_wins"},
        )
        assert missing.status_code == 404

        bad_limit = client.post("/api/sync/process", json={"limit": 999})
        assert bad_limit.status_code == 422

    def test_api_rejects_invalid_enum_values(self, client: TestClient) -> None:
        response = client.post(
            "/api/sync/mutations",
            json={
                "client_id": "phone",
                "entity": "note",
                "operation": "teleport",
                "payload": {},
            },
        )
        assert response.status_code == 422
