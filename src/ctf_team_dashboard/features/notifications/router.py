"""HTTP endpoints for the notification centre."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.notifications.models import (
    Channel,
    Digest,
    DigestEntry,
    DigestGroup,
    DigestPeriod,
    Notification,
    NotificationKind,
    NotificationPreference,
    NotificationQuery,
    NotificationStats,
    RetentionPolicy,
    Severity,
)
from ctf_team_dashboard.features.notifications.schemas import (
    CreateResultRead,
    DeliveryDecisionRead,
    DigestEntryRead,
    DigestGroupRead,
    DigestPreviewRead,
    DigestRead,
    DigestSendRequest,
    MarkReadResult,
    NotificationCreate,
    NotificationPage,
    NotificationRead,
    PreferenceList,
    PreferenceRead,
    PreferenceUpsert,
    PruneRequest,
    PruneResult,
    RecipientRequest,
    StatsRead,
)
from ctf_team_dashboard.features.notifications.service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def get_service() -> NotificationService:
    """Dependency returning a service bound to the current database."""
    return NotificationService()


ServiceDep = Annotated[NotificationService, Depends(get_service)]


def notification_read(notification: Notification) -> NotificationRead:
    """Map a domain notification onto its API representation."""
    return NotificationRead(
        id=notification.id,
        recipient_id=notification.recipient_id,
        channel=notification.channel,
        kind=notification.kind,
        title=notification.title,
        body=notification.body,
        severity=notification.severity,
        read_at=notification.read_at,
        created_at=notification.created_at,
        action_url=notification.action_url,
        is_read=notification.is_read,
        is_unread=notification.is_unread,
        severity_rank=notification.severity.rank,
        label=notification.label,
        age_seconds=notification.age_seconds,
    )


def preference_read(preference: NotificationPreference) -> PreferenceRead:
    """Map a preference onto its API representation."""
    return PreferenceRead(
        recipient_id=preference.recipient_id,
        channel=preference.channel,
        kind=preference.kind,
        enabled=preference.enabled,
        quiet_start_hour=preference.quiet_start_hour,
        quiet_end_hour=preference.quiet_end_hour,
        quiet_hours=preference.quiet_hours.describe(),
    )


def entry_read(entry: DigestEntry) -> DigestEntryRead:
    """Map a digest entry onto its API representation."""
    return DigestEntryRead(
        notification_id=entry.notification_id,
        kind=entry.kind,
        severity=entry.severity,
        title=entry.title,
        body=entry.body,
        created_at=entry.created_at,
        action_url=entry.action_url,
    )


def group_read(group: DigestGroup) -> DigestGroupRead:
    """Map a digest group onto its API representation."""
    return DigestGroupRead(
        kind=group.kind,
        severity=group.severity,
        count=group.count,
        headline=group.headline,
        entries=[entry_read(entry) for entry in group.entries],
    )


def digest_read(digest: Digest) -> DigestRead:
    """Map a stored digest onto its API representation."""
    return DigestRead(
        id=digest.id,
        recipient_id=digest.recipient_id,
        period=digest.period,
        entries=[entry_read(entry) for entry in digest.entries],
        groups=[group_read(group) for group in digest.groups],
        total=digest.total,
        sent_at=digest.sent_at,
        is_sent=digest.is_sent,
        markdown=digest.render_markdown(),
    )


def stats_read(stats: NotificationStats) -> StatsRead:
    """Map notification statistics onto their API representation."""
    return StatsRead(
        total=stats.total,
        read=stats.read,
        unread=stats.unread,
        critical_unread=stats.critical_unread,
        read_rate=stats.read_rate,
        by_channel=stats.by_channel,
        by_kind=stats.by_kind,
        by_severity=stats.by_severity,
    )


@router.get("", response_model=NotificationPage)
def list_notifications(
    service: ServiceDep,
    recipient_id: str | None = None,
    channel: Channel | None = None,
    kind: NotificationKind | None = None,
    severity: Severity | None = None,
    unread_only: bool = False,
    search: str = "",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> NotificationPage:
    """Return a filtered notification listing with unread counters."""
    query = NotificationQuery(
        recipient_id=recipient_id,
        channel=channel,
        kind=kind,
        severity=severity,
        unread_only=unread_only,
        search=search,
        limit=limit,
        offset=offset,
    )
    items = service.list_notifications(query)
    return NotificationPage(
        items=[notification_read(item) for item in items],
        total=service.total_matching(query),
        unread=service.unread_count(recipient_id),
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=CreateResultRead, status_code=status.HTTP_201_CREATED)
def create_notification(payload: NotificationCreate, service: ServiceDep) -> CreateResultRead:
    """Emit a notification, evaluating preferences and quiet hours."""
    result = service.create(
        recipient_id=payload.recipient_id,
        channel=payload.channel,
        kind=payload.kind,
        title=payload.title,
        body=payload.body,
        variables=payload.variables,
        severity=payload.severity,
        action_url=payload.action_url,
    )
    return CreateResultRead(
        notification=notification_read(result.notification),
        decision=DeliveryDecisionRead(**result.decision.to_dict()),
        delivered=result.delivered,
    )


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(notification_id: str, service: ServiceDep) -> NotificationRead:
    """Acknowledge one notification."""
    return notification_read(service.mark_read(notification_id))


@router.post("/read-all", response_model=MarkReadResult)
def mark_all_read(payload: RecipientRequest, service: ServiceDep) -> MarkReadResult:
    """Acknowledge every unread notification of a recipient."""
    modified = service.mark_all_read(payload.recipient_id)
    return MarkReadResult(
        modified=modified,
        unread=service.unread_count(payload.recipient_id),
    )


@router.get("/preferences", response_model=PreferenceList)
def list_preferences(
    service: ServiceDep,
    recipient_id: str = Query(min_length=1),
) -> PreferenceList:
    """Return the complete preference matrix of a recipient."""
    preferences = service.effective_preferences(recipient_id)
    return PreferenceList(
        recipient_id=recipient_id,
        preferences=[preference_read(preference) for preference in preferences],
    )


@router.put("/preferences", response_model=PreferenceRead)
def upsert_preference(payload: PreferenceUpsert, service: ServiceDep) -> PreferenceRead:
    """Create or update one preference row."""
    preference = service.upsert_preference(
        recipient_id=payload.recipient_id,
        channel=payload.channel,
        kind=payload.kind,
        enabled=payload.enabled,
        quiet_start_hour=payload.quiet_start_hour,
        quiet_end_hour=payload.quiet_end_hour,
    )
    return preference_read(preference)


@router.get("/digest", response_model=DigestPreviewRead)
def digest_preview(
    service: ServiceDep,
    recipient_id: str = Query(min_length=1),
    period: DigestPeriod = DigestPeriod.DAILY,
) -> DigestPreviewRead:
    """Preview the digest that would be generated for a period."""
    preview = service.preview_digest(recipient_id, period)
    return DigestPreviewRead(
        recipient_id=recipient_id,
        period=period,
        total=preview.total,
        groups=[group_read(group) for group in preview.groups],
        entries=[entry_read(entry) for entry in preview.entries],
        markdown=preview.render_markdown(),
        generated_at=utcnow(),
    )


@router.post("/digest", response_model=DigestRead, status_code=status.HTTP_201_CREATED)
def build_digest_endpoint(
    service: ServiceDep,
    recipient_id: str = Query(min_length=1),
    period: DigestPeriod = DigestPeriod.DAILY,
) -> DigestRead:
    """Generate and persist a digest for a period."""
    return digest_read(service.build_digest(recipient_id, period))


@router.post("/digest/send", response_model=DigestRead)
def send_digest(payload: DigestSendRequest, service: ServiceDep) -> DigestRead:
    """Mark a stored digest as dispatched."""
    return digest_read(service.send_digest(payload.digest_id))


@router.get("/stats", response_model=StatsRead)
def notification_stats(
    service: ServiceDep,
    recipient_id: str | None = None,
) -> StatsRead:
    """Return aggregated notification counters."""
    return stats_read(service.stats(recipient_id))


@router.post("/prune", response_model=PruneResult)
def prune_notifications(payload: PruneRequest, service: ServiceDep) -> PruneResult:
    """Remove notifications older than the requested retention window."""
    policy = RetentionPolicy(
        max_age_days=payload.max_age_days,
        keep_unread=payload.keep_unread,
    )
    removed = service.prune(policy=policy)
    return PruneResult(
        removed=removed,
        max_age_days=payload.max_age_days,
        keep_unread=payload.keep_unread,
    )
