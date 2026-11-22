"""Business rules for creating, delivering and summarising notifications."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import uuid4

from ctf_team_dashboard.domain.models import ensure_utc, utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.notifications.models import (
    Channel,
    CreateResult,
    DeliveryDecision,
    Digest,
    DigestPeriod,
    Notification,
    NotificationKind,
    NotificationPreference,
    NotificationQuery,
    NotificationStats,
    RetentionPolicy,
    Severity,
    build_digest,
    effective_preferences,
    evaluate_delivery,
    lookup_preference,
    render_template,
)
from ctf_team_dashboard.features.notifications.store import (
    DigestRepository,
    NotificationRepository,
    PreferenceRepository,
)


class NotificationService:
    """Coordinate persistence and domain rules for the notification centre."""

    def __init__(
        self,
        notifications: NotificationRepository | None = None,
        preferences: PreferenceRepository | None = None,
        digests: DigestRepository | None = None,
    ) -> None:
        self.notifications = notifications or NotificationRepository()
        self.preferences = preferences or PreferenceRepository()
        self.digests = digests or DigestRepository()

    # ------------------------------------------------------------------
    # Creation and delivery
    # ------------------------------------------------------------------
    def create(
        self,
        *,
        recipient_id: str,
        channel: Channel,
        kind: NotificationKind,
        title: str,
        body: str,
        variables: Mapping[str, Any] | None = None,
        severity: Severity = Severity.INFO,
        action_url: str = "",
        created_at: datetime | None = None,
        moment: datetime | None = None,
    ) -> CreateResult:
        """Store a notification after validating and templating its content.

        A suppressed notification is still persisted: recipients can see that
        an event happened even when the selected channel was muted. The
        returned decision explains whether it was delivered and why not.
        """
        if not recipient_id.strip():
            raise ValidationError("recipient_id cannot be blank")
        if not title.strip():
            raise ValidationError("title cannot be blank")
        if not body.strip():
            raise ValidationError("body cannot be blank")
        if len(title) > 200:
            raise ValidationError("title cannot exceed 200 characters")
        if len(body) > 4_000:
            raise ValidationError("body cannot exceed 4000 characters")
        if len(action_url) > 2_000:
            raise ValidationError("action_url cannot exceed 2000 characters")

        rendered = render_template(body, variables or {})
        notification = Notification(
            id=f"ntf-{uuid4().hex}",
            recipient_id=recipient_id,
            channel=channel,
            kind=kind,
            title=title.strip(),
            body=rendered,
            severity=severity,
            created_at=ensure_utc(created_at if created_at is not None else utcnow()),
            action_url=action_url,
        )
        preference = lookup_preference(
            self.preferences.list_for_recipient(recipient_id),
            recipient_id,
            channel,
            kind,
        )
        decision = evaluate_delivery(preference, notification, moment)
        self.notifications.create(notification)
        return CreateResult(notification=notification, decision=decision)

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    def get(self, notification_id: str) -> Notification:
        """Return a notification or raise :class:`NotFoundError`."""
        notification = self.notifications.get(notification_id)
        if notification is None:
            raise NotFoundError(f"Notification {notification_id!r} does not exist")
        return notification

    def list_notifications(self, query: NotificationQuery | None = None) -> list[Notification]:
        """Return notifications matching a query, newest urgent items first."""
        resolved = query or NotificationQuery()
        return self.notifications.list_filtered(
            recipient_id=resolved.recipient_id,
            channel=resolved.channel,
            kind=resolved.kind,
            severity=resolved.severity,
            unread_only=resolved.unread_only,
            limit=resolved.limit,
            offset=resolved.offset,
        )

    def total_matching(self, query: NotificationQuery | None = None) -> int:
        """Return the unpaginated size of a filtered listing."""
        resolved = query or NotificationQuery()
        return self.notifications.count_filtered(
            recipient_id=resolved.recipient_id,
            channel=resolved.channel,
            kind=resolved.kind,
            severity=resolved.severity,
            unread_only=resolved.unread_only,
        )

    def unread_count(self, recipient_id: str | None = None) -> int:
        """Return the unread count for a recipient or globally."""
        return self.notifications.unread_count(recipient_id)

    def mark_read(
        self,
        notification_id: str,
        when: datetime | None = None,
    ) -> Notification:
        """Acknowledge one notification; the operation is idempotent."""
        notification = self.get(notification_id)
        if notification.is_read:
            return notification
        when = ensure_utc(when if when is not None else utcnow())
        updated = self.notifications.mark_read(notification_id, when)
        if updated is None:
            raise NotFoundError(f"Notification {notification_id!r} does not exist")
        return updated

    def mark_all_read(self, recipient_id: str, when: datetime | None = None) -> int:
        """Acknowledge every unread notification of a recipient."""
        if not recipient_id.strip():
            raise ValidationError("recipient_id cannot be blank")
        when = ensure_utc(when if when is not None else utcnow())
        return self.notifications.mark_all_read(recipient_id, when)

    def delete(self, notification_id: str) -> None:
        """Permanently remove one notification."""
        if not self.notifications.delete(notification_id):
            raise NotFoundError(f"Notification {notification_id!r} does not exist")

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    def list_preferences(self, recipient_id: str) -> list[NotificationPreference]:
        """Return stored preference rows for a recipient."""
        if not recipient_id.strip():
            raise ValidationError("recipient_id cannot be blank")
        return self.preferences.list_for_recipient(recipient_id)

    def effective_preferences(self, recipient_id: str) -> tuple[NotificationPreference, ...]:
        """Return the complete channel/kind preference matrix."""
        if not recipient_id.strip():
            raise ValidationError("recipient_id cannot be blank")
        return effective_preferences(
            self.preferences.list_for_recipient(recipient_id),
            recipient_id,
        )

    def lookup_preference(
        self,
        recipient_id: str,
        channel: Channel,
        kind: NotificationKind,
    ) -> NotificationPreference:
        """Resolve the most specific preference for a channel and kind."""
        return lookup_preference(
            self.preferences.list_for_recipient(recipient_id),
            recipient_id,
            channel,
            kind,
        )

    def upsert_preference(
        self,
        *,
        recipient_id: str,
        channel: Channel,
        kind: NotificationKind,
        enabled: bool = True,
        quiet_start_hour: int = 0,
        quiet_end_hour: int = 0,
    ) -> NotificationPreference:
        """Create or update a delivery preference."""
        if not recipient_id.strip():
            raise ValidationError("recipient_id cannot be blank")
        preference = NotificationPreference(
            recipient_id=recipient_id,
            channel=channel,
            kind=kind,
            enabled=enabled,
            quiet_start_hour=quiet_start_hour,
            quiet_end_hour=quiet_end_hour,
        )
        return self.preferences.upsert(preference)

    def delete_preference(
        self,
        recipient_id: str,
        channel: Channel,
        kind: NotificationKind,
    ) -> None:
        """Remove an explicit preference, reverting to the implicit default."""
        if not self.preferences.delete(recipient_id, channel, kind):
            raise NotFoundError("No preference matches the supplied key")

    # ------------------------------------------------------------------
    # Digests
    # ------------------------------------------------------------------
    def _window_notifications(
        self,
        recipient_id: str,
        period: DigestPeriod,
        now: datetime | None = None,
    ) -> list[Notification]:
        reference = ensure_utc(now if now is not None else utcnow())
        cutoff = reference - period.window
        return [
            notification
            for notification in self.notifications.list_all()
            if notification.recipient_id == recipient_id
            and ensure_utc(notification.created_at) >= cutoff
        ]

    def preview_digest(
        self,
        recipient_id: str,
        period: DigestPeriod = DigestPeriod.DAILY,
        now: datetime | None = None,
    ) -> Digest:
        """Build a digest structure without persisting it."""
        if not recipient_id.strip():
            raise ValidationError("recipient_id cannot be blank")
        items = self._window_notifications(recipient_id, period, now)
        return build_digest(f"preview-{recipient_id}", recipient_id, period, items)

    def build_digest(
        self,
        recipient_id: str,
        period: DigestPeriod = DigestPeriod.DAILY,
        now: datetime | None = None,
    ) -> Digest:
        """Persist a digest covering the most recent period."""
        digest = self.preview_digest(recipient_id, period, now)
        stored = Digest(
            id=f"dgt-{uuid4().hex}",
            recipient_id=recipient_id,
            period=period,
            entries_json=digest.entries_json,
        )
        return self.digests.create(stored)

    def get_digest(self, digest_id: str) -> Digest:
        """Return a stored digest or raise :class:`NotFoundError`."""
        digest = self.digests.get(digest_id)
        if digest is None:
            raise NotFoundError(f"Digest {digest_id!r} does not exist")
        return digest

    def list_digests(self, recipient_id: str) -> list[Digest]:
        """Return stored digests for a recipient."""
        return self.digests.list_for_recipient(recipient_id)

    def send_digest(self, digest_id: str, when: datetime | None = None) -> Digest:
        """Mark a digest as dispatched; sending twice is a conflict."""
        digest = self.get_digest(digest_id)
        if digest.is_sent:
            raise ConflictError("Digest has already been sent")
        when = ensure_utc(when if when is not None else utcnow())
        updated = self.digests.mark_sent(digest_id, when)
        if updated is None or updated.sent_at is None:
            raise ConflictError("Digest could not be marked as sent")
        return updated

    # ------------------------------------------------------------------
    # Maintenance and reporting
    # ------------------------------------------------------------------
    def prune(
        self,
        *,
        policy: RetentionPolicy | None = None,
        now: datetime | None = None,
    ) -> int:
        """Delete expired notifications and return the number removed."""
        resolved = policy or RetentionPolicy()
        reference = ensure_utc(now if now is not None else utcnow())
        _kept, removed = resolved.prune(self.notifications.list_all(), reference)
        ids = [notification.id for notification in removed]
        return self.notifications.delete_many(ids)

    def stale_count(self, policy: RetentionPolicy | None = None) -> int:
        """Return how many notifications would be removed by a prune."""
        resolved = policy or RetentionPolicy()
        _kept, removed = resolved.prune(self.notifications.list_all())
        return len(removed)

    def stats(self, recipient_id: str | None = None) -> NotificationStats:
        """Aggregate notification counters for a recipient or globally."""
        items = self.notifications.list_all()
        if recipient_id is not None:
            items = [item for item in items if item.recipient_id == recipient_id]
        return NotificationStats.from_notifications(items)


def delivery_reasons(decisions: list[DeliveryDecision]) -> dict[str, int]:
    """Count delivery decisions by reason, useful for audit views."""
    counts: dict[str, int] = {}
    for decision in decisions:
        counts[decision.reason] = counts.get(decision.reason, 0) + 1
    return counts
