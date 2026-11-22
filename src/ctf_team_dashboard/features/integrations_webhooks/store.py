"""SQLite persistence for integrations, deliveries and adapters."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.integrations_webhooks.models import (
    Adapter,
    Delivery,
    DeliveryStatus,
    Integration,
    IntegrationKind,
    decode_events,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)


class IntegrationRepository(BaseRepository):
    """Persistence operations for outbound integrations."""

    table = "v3_integrations"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Integration:
        """Map a database row onto the integration entity."""
        data = row_to_dict(row)
        created = parse_datetime(str(data["created_at"]))
        return Integration(
            id=str(data["id"]),
            name=str(data["name"]),
            kind=IntegrationKind.parse(str(data["kind"])),
            endpoint_url=str(data["endpoint_url"]),
            events_json=str(data["events_json"] or "[]"),
            secret_hash=str(data["secret_hash"] or ""),
            enabled=bool(data["enabled"]),
            created_at=created if created is not None else utcnow(),
        )

    def list_all(self, *, enabled_only: bool = False) -> list[Integration]:
        """Return every integration, optionally filtering out disabled ones."""
        where = "WHERE enabled = 1" if enabled_only else ""
        rows = self.fetch_all(f"SELECT * FROM v3_integrations {where} ORDER BY name ASC")
        return [self.to_model(row) for row in rows]

    def list_supporting(self, event: str) -> list[Integration]:
        """Return enabled integrations subscribed to an event."""
        rows = self.fetch_all("SELECT * FROM v3_integrations WHERE enabled = 1 ORDER BY name ASC")
        return [row for row in map(self.to_model, rows) if event in decode_events(row.events_json)]

    def get(self, integration_id: str) -> Integration | None:
        """Return an integration by identifier, when it exists."""
        row = self.fetch_one("SELECT * FROM v3_integrations WHERE id = ?", (integration_id,))
        return self.to_model(row) if row is not None else None

    def get_by_name(self, name: str) -> Integration | None:
        """Return an integration by case-insensitive name."""
        row = self.fetch_one(
            "SELECT * FROM v3_integrations WHERE lower(name) = lower(?) LIMIT 1",
            (name.strip(),),
        )
        return self.to_model(row) if row is not None else None

    def create(self, integration: Integration) -> Integration:
        """Insert an integration and return the persisted value."""
        self.execute(
            """
            INSERT INTO v3_integrations
                (id, name, kind, endpoint_url, events_json, secret_hash, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                integration.id,
                integration.name,
                integration.kind.value,
                integration.endpoint_url,
                integration.events_json,
                integration.secret_hash,
                int(integration.enabled),
                format_datetime(integration.created_at),
            ),
        )
        return integration

    def update(self, integration: Integration) -> Integration:
        """Persist the mutable fields of an integration."""
        self.execute(
            """
            UPDATE v3_integrations
            SET name = ?, kind = ?, endpoint_url = ?, events_json = ?,
                secret_hash = ?, enabled = ?
            WHERE id = ?
            """,
            (
                integration.name,
                integration.kind.value,
                integration.endpoint_url,
                integration.events_json,
                integration.secret_hash,
                int(integration.enabled),
                integration.id,
            ),
        )
        return integration

    def delete(self, integration_id: str) -> bool:
        """Delete an integration; return whether a row was removed."""
        return self.execute("DELETE FROM v3_integrations WHERE id = ?", (integration_id,)) > 0

    def count_enabled(self) -> int:
        """Return the number of enabled integrations."""
        return int(
            self.fetch_value("SELECT COUNT(*) FROM v3_integrations WHERE enabled = 1", default=0)
            or 0
        )


class DeliveryRepository(BaseRepository):
    """Persistence operations for the delivery ledger."""

    table = "v3_deliveries"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Delivery:
        """Map a database row onto the delivery entity."""
        data = row_to_dict(row)
        sent_at = parse_datetime(str(data["sent_at"]) if data["sent_at"] else None)
        return Delivery(
            id=str(data["id"]),
            integration_id=str(data["integration_id"]),
            event=str(data["event"]),
            payload_json=str(data["payload_json"] or "{}"),
            status=DeliveryStatus(str(data["status"])),
            attempts=int(data["attempts"] or 0),
            response_code=int(data["response_code"]) if data["response_code"] is not None else None,
            sent_at=sent_at,
        )

    def list_all(
        self,
        *,
        status: DeliveryStatus | None = None,
        integration_id: str | None = None,
        limit: int = 200,
    ) -> list[Delivery]:
        """Return deliveries, newest first, with optional filters."""
        where: list[str] = []
        params: list[Any] = []
        if status is not None:
            where.append("status = ?")
            params.append(status.value)
        if integration_id is not None:
            where.append("integration_id = ?")
            params.append(integration_id)
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        bounded = max(1, min(limit, 1_000))
        rows = self.fetch_all(
            f"SELECT * FROM v3_deliveries{clause} ORDER BY rowid DESC LIMIT ?",
            (*params, bounded),
        )
        return [self.to_model(row) for row in rows]

    def list_failed(self, limit: int = 100) -> list[Delivery]:
        """Return failed deliveries eligible for a retry."""
        return self.list_all(status=DeliveryStatus.FAILED, limit=limit)

    def get(self, delivery_id: str) -> Delivery | None:
        """Return a delivery by identifier, when it exists."""
        row = self.fetch_one("SELECT * FROM v3_deliveries WHERE id = ?", (delivery_id,))
        return self.to_model(row) if row is not None else None

    def create(self, delivery: Delivery) -> Delivery:
        """Insert a delivery record."""
        self.execute(
            """
            INSERT INTO v3_deliveries
                (id, integration_id, event, payload_json, status, attempts, response_code, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delivery.id,
                delivery.integration_id,
                delivery.event,
                delivery.payload_json,
                delivery.status.value,
                delivery.attempts,
                delivery.response_code,
                format_datetime(delivery.sent_at),
            ),
        )
        return delivery

    def update(self, delivery: Delivery) -> Delivery:
        """Persist the mutable fields of a delivery."""
        self.execute(
            """
            UPDATE v3_deliveries
            SET status = ?, attempts = ?, response_code = ?, sent_at = ?
            WHERE id = ?
            """,
            (
                delivery.status.value,
                delivery.attempts,
                delivery.response_code,
                format_datetime(delivery.sent_at),
                delivery.id,
            ),
        )
        return delivery

    def delete_for_integration(self, integration_id: str) -> int:
        """Remove the delivery ledger of a deleted integration."""
        return self.execute("DELETE FROM v3_deliveries WHERE integration_id = ?", (integration_id,))

    def count_by_status(self) -> dict[DeliveryStatus, int]:
        """Return a counter for each delivery status."""
        rows = self.fetch_all("SELECT status, COUNT(*) AS total FROM v3_deliveries GROUP BY status")
        counts = dict.fromkeys(DeliveryStatus, 0)
        for row in rows:
            status = DeliveryStatus(str(row["status"]))
            counts[status] = int(row["total"])
        return counts

    def total_attempts(self) -> int:
        """Return the sum of attempts across the whole ledger."""
        return int(
            self.fetch_value("SELECT COALESCE(SUM(attempts), 0) FROM v3_deliveries", default=0) or 0
        )

    def list_for_integration(self, integration_id: str, limit: int = 100) -> list[Delivery]:
        """Return the recent deliveries of a single integration."""
        return self.list_all(integration_id=integration_id, limit=limit)


class AdapterRepository(BaseRepository):
    """Persistence operations for event adapters."""

    table = "v3_adapters"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Adapter:
        """Map a database row onto the adapter entity."""
        data = row_to_dict(row)
        created = parse_datetime(str(data["created_at"]))
        return Adapter(
            id=str(data["id"]),
            name=str(data["name"]),
            event_map_json=str(data["event_map_json"] or "{}"),
            created_at=created if created is not None else utcnow(),
        )

    def list_all(self) -> list[Adapter]:
        """Return every adapter in name order."""
        rows = self.fetch_all("SELECT * FROM v3_adapters ORDER BY name ASC")
        return [self.to_model(row) for row in rows]

    def get(self, adapter_id: str) -> Adapter | None:
        """Return an adapter by identifier, when it exists."""
        row = self.fetch_one("SELECT * FROM v3_adapters WHERE id = ?", (adapter_id,))
        return self.to_model(row) if row is not None else None

    def get_by_name(self, name: str) -> Adapter | None:
        """Return an adapter by case-insensitive name."""
        row = self.fetch_one(
            "SELECT * FROM v3_adapters WHERE lower(name) = lower(?) LIMIT 1",
            (name.strip(),),
        )
        return self.to_model(row) if row is not None else None

    def create(self, adapter: Adapter) -> Adapter:
        """Insert an adapter."""
        self.execute(
            "INSERT INTO v3_adapters (id, name, event_map_json, created_at) VALUES (?, ?, ?, ?)",
            (
                adapter.id,
                adapter.name,
                adapter.event_map_json,
                format_datetime(adapter.created_at),
            ),
        )
        return adapter

    def delete(self, adapter_id: str) -> bool:
        """Delete an adapter; return whether a row was removed."""
        return self.execute("DELETE FROM v3_adapters WHERE id = ?", (adapter_id,)) > 0

    def count(self, where: str = "", params: Sequence[Any] = ()) -> int:
        """Return the number of adapters matching an optional filter."""
        clause = f" WHERE {where}" if where else ""
        return int(self.fetch_value(f"SELECT COUNT(*) FROM v3_adapters{clause}", params, 0) or 0)
