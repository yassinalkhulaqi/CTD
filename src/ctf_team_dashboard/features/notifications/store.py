"""Persistence for the notification centre.

Every query is parameterised and built on :class:`BaseRepository`. The three
repositories own disjoint tables so the service layer can compose them without
any cross-feature imports.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.notifications.models import (
    Channel,
    Digest,
    DigestPeriod,
    Notification,
    NotificationKind,
    NotificationPreference,
    Severity,
    parse_iso,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    format_datetime,
    parse_datetime,
    row_to_dict,
)


class NotificationRepository(BaseRepository):
    """Persistence operations for notification records."""

    table = "v3_notifications"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Notification:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        created = parse_datetime(str(data["created_at"]))
        return Notification(
            id=str(data["id"]),
            recipient_id=str(data["recipient_id"]),
            channel=Channel.parse(str(data["channel"]), Channel.IN_APP),
            kind=NotificationKind.parse(str(data["kind"]), NotificationKind.SYSTEM),
            title=str(data["title"]),
            body=str(data["body"]),
            severity=Severity.parse(str(data["severity"]), Severity.INFO),
            read_at=parse_datetime(str(data["read_at"]) if data["read_at"] else None),
            created_at=created if created is not None else utcnow(),
            action_url=str(data["action_url"] or ""),
        )

    def get(self, notification_id: str) -> Notification | None:
        """Return a notification by identifier."""
        row = self.fetch_one(
            "SELECT * FROM v3_notifications WHERE id = ?",
            (notification_id,),
        )
        return self.to_model(row) if row is not None else None

    def create(self, notification: Notification) -> Notification:
        """Insert a notification and return the stored record."""
        self.execute(
            """
            INSERT INTO v3_notifications
                (id, recipient_id, channel, kind, title, body, severity,
                 read_at, created_at, action_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notification.id,
                notification.recipient_id,
                notification.channel.value,
                notification.kind.value,
                notification.title,
                notification.body,
                notification.severity.value,
                format_datetime(notification.read_at),
                format_datetime(notification.created_at),
                notification.action_url,
            ),
        )
        return notification

    def list_all(self) -> list[Notification]:
        """Return every notification ordered by creation time."""
        rows = self.fetch_all("SELECT * FROM v3_notifications ORDER BY created_at DESC")
        return [self.to_model(row) for row in rows]

    def list_filtered(
        self,
        *,
        recipient_id: str | None = None,
        channel: Channel | None = None,
        kind: NotificationKind | None = None,
        severity: Severity | None = None,
        unread_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Notification]:
        """Return notifications matching the supplied filters.

        Sorting is performed on severity rank before creation time so a
        critical alert always outranks a newer informational message.
        """
        clauses: list[str] = []
        params: list[Any] = []
        if recipient_id is not None:
            clauses.append("recipient_id = ?")
            params.append(recipient_id)
        if channel is not None:
            clauses.append("channel = ?")
            params.append(channel.value)
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind.value)
        if severity is not None:
            clauses.append("severity = ?")
            params.append(severity.value)
        if unread_only:
            clauses.append("read_at IS NULL")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])
        rows = self.fetch_all(
            f"""
            SELECT * FROM v3_notifications{where}
            ORDER BY
                CASE severity WHEN 'critical' THEN 2 WHEN 'warning' THEN 1 ELSE 0 END DESC,
                created_at DESC,
                id ASC
            LIMIT ? OFFSET ?
            """,
            params,
        )
        return [self.to_model(row) for row in rows]

    def count_filtered(
        self,
        *,
        recipient_id: str | None = None,
        channel: Channel | None = None,
        kind: NotificationKind | None = None,
        severity: Severity | None = None,
        unread_only: bool = False,
    ) -> int:
        """Count notifications matching the supplied filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if recipient_id is not None:
            clauses.append("recipient_id = ?")
            params.append(recipient_id)
        if channel is not None:
            clauses.append("channel = ?")
            params.append(channel.value)
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind.value)
        if severity is not None:
            clauses.append("severity = ?")
            params.append(severity.value)
        if unread_only:
            clauses.append("read_at IS NULL")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        value = self.fetch_value(
            f"SELECT COUNT(*) FROM v3_notifications{where}",
            params,
            0,
        )
        return int(value or 0)

    def unread_count(self, recipient_id: str | None = None) -> int:
        """Return the number of unread notifications, optionally per recipient."""
        if recipient_id is None:
            return self.count_filtered(unread_only=True)
        return self.count_filtered(recipient_id=recipient_id, unread_only=True)

    def mark_read(self, notification_id: str, when: Any) -> Notification | None:
        """Set the read timestamp of one notification."""
        self.execute(
            "UPDATE v3_notifications SET read_at = ? WHERE id = ? AND read_at IS NULL",
            (format_datetime(when), notification_id),
        )
        return self.get(notification_id)

    def mark_all_read(self, recipient_id: str, when: Any) -> int:
        """Mark every unread notification of a recipient as read."""
        return self.execute(
            "UPDATE v3_notifications SET read_at = ? WHERE recipient_id = ? AND read_at IS NULL",
            (format_datetime(when), recipient_id),
        )

    def list_older_than(self, cutoff: Any) -> list[Notification]:
        """Return notifications created before ``cutoff``."""
        rows = self.fetch_all(
            "SELECT * FROM v3_notifications WHERE created_at < ?",
            (format_datetime(cutoff),),
        )
        return [self.to_model(row) for row in rows]

    def delete(self, notification_id: str) -> bool:
        """Delete one notification; returns ``True`` when a row was removed."""
        return (
            self.execute(
                "DELETE FROM v3_notifications WHERE id = ?",
                (notification_id,),
            )
            > 0
        )

    def delete_many(self, ids: Sequence[str]) -> int:
        """Delete every notification whose identifier appears in ``ids``."""
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        return self.execute(
            f"DELETE FROM v3_notifications WHERE id IN ({placeholders})",
            tuple(ids),
        )


class PreferenceRepository(BaseRepository):
    """Persistence operations for delivery preferences."""

    table = "v3_notification_preferences"

    @staticmethod
    def to_model(row: sqlite3.Row) -> NotificationPreference:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        return NotificationPreference(
            recipient_id=str(data["recipient_id"]),
            channel=Channel.parse(str(data["channel"]), Channel.IN_APP),
            kind=NotificationKind.parse(str(data["kind"]), NotificationKind.ANY),
            enabled=bool(data["enabled"]),
            quiet_start_hour=int(data["quiet_start_hour"]),
            quiet_end_hour=int(data["quiet_end_hour"]),
        )

    def get(
        self,
        recipient_id: str,
        channel: Channel,
        kind: NotificationKind,
    ) -> NotificationPreference | None:
        """Return one preference by its composite key."""
        row = self.fetch_one(
            "SELECT * FROM v3_notification_preferences "
            "WHERE recipient_id = ? AND channel = ? AND kind = ?",
            (recipient_id, channel.value, kind.value),
        )
        return self.to_model(row) if row is not None else None

    def upsert(self, preference: NotificationPreference) -> NotificationPreference:
        """Insert or replace a preference row."""
        self.execute(
            """
            INSERT INTO v3_notification_preferences
                (recipient_id, channel, kind, enabled, quiet_start_hour, quiet_end_hour)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(recipient_id, channel, kind) DO UPDATE SET
                enabled = excluded.enabled,
                quiet_start_hour = excluded.quiet_start_hour,
                quiet_end_hour = excluded.quiet_end_hour
            """,
            (
                preference.recipient_id,
                preference.channel.value,
                preference.kind.value,
                int(preference.enabled),
                preference.quiet_start_hour,
                preference.quiet_end_hour,
            ),
        )
        return preference

    def list_for_recipient(self, recipient_id: str) -> list[NotificationPreference]:
        """Return every stored preference of a recipient."""
        rows = self.fetch_all(
            "SELECT * FROM v3_notification_preferences "
            "WHERE recipient_id = ? ORDER BY channel, kind",
            (recipient_id,),
        )
        return [self.to_model(row) for row in rows]

    def list_all(self) -> list[NotificationPreference]:
        """Return every stored preference."""
        rows = self.fetch_all(
            "SELECT * FROM v3_notification_preferences ORDER BY recipient_id, channel, kind"
        )
        return [self.to_model(row) for row in rows]

    def delete(
        self,
        recipient_id: str,
        channel: Channel,
        kind: NotificationKind,
    ) -> bool:
        """Delete a preference and report whether a row was removed."""
        return (
            self.execute(
                "DELETE FROM v3_notification_preferences "
                "WHERE recipient_id = ? AND channel = ? AND kind = ?",
                (recipient_id, channel.value, kind.value),
            )
            > 0
        )


class DigestRepository(BaseRepository):
    """Persistence operations for generated digests."""

    table = "v3_digests"

    @staticmethod
    def to_model(row: sqlite3.Row) -> Digest:
        """Map a database row onto the domain model."""
        data = row_to_dict(row)
        sent = parse_iso(str(data["sent_at"])) if data["sent_at"] else None
        return Digest(
            id=str(data["id"]),
            recipient_id=str(data["recipient_id"]),
            period=DigestPeriod.parse(str(data["period"]), DigestPeriod.DAILY),
            entries_json=str(data["entries_json"] or "[]"),
            sent_at=sent,
        )

    def get(self, digest_id: str) -> Digest | None:
        """Return a digest by identifier."""
        row = self.fetch_one("SELECT * FROM v3_digests WHERE id = ?", (digest_id,))
        return self.to_model(row) if row is not None else None

    def create(self, digest: Digest) -> Digest:
        """Insert a digest and return the stored record."""
        self.execute(
            """
            INSERT INTO v3_digests (id, recipient_id, period, entries_json, sent_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                digest.id,
                digest.recipient_id,
                digest.period.value,
                digest.entries_json,
                format_datetime(digest.sent_at),
            ),
        )
        return digest

    def mark_sent(self, digest_id: str, when: Any) -> Digest | None:
        """Record the dispatch time of a digest."""
        self.execute(
            "UPDATE v3_digests SET sent_at = ? WHERE id = ? AND sent_at IS NULL",
            (format_datetime(when), digest_id),
        )
        return self.get(digest_id)

    def list_for_recipient(self, recipient_id: str) -> list[Digest]:
        """Return every digest generated for a recipient."""
        rows = self.fetch_all(
            "SELECT * FROM v3_digests WHERE recipient_id = ? ORDER BY rowid DESC",
            (recipient_id,),
        )
        return [self.to_model(row) for row in rows]

    def list_unsent(self) -> list[Digest]:
        """Return every digest that has not been dispatched yet."""
        rows = self.fetch_all("SELECT * FROM v3_digests WHERE sent_at IS NULL ORDER BY rowid ASC")
        return [self.to_model(row) for row in rows]

    def delete(self, digest_id: str) -> bool:
        """Delete a digest and report whether a row was removed."""
        return (
            self.execute(
                "DELETE FROM v3_digests WHERE id = ?",
                (digest_id,),
            )
            > 0
        )
