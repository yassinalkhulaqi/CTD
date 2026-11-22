"""Typed request and response models for the notification API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.features.notifications.models import (
    Channel,
    DigestPeriod,
    NotificationKind,
    Severity,
)


class ApiModel(BaseModel):
    """Base model using the shared serialisation configuration."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class NotificationRead(ApiModel):
    """A notification as returned by the API."""

    id: str
    recipient_id: str
    channel: Channel
    kind: NotificationKind
    title: str
    body: str
    severity: Severity
    read_at: datetime | None = None
    created_at: datetime
    action_url: str = ""
    is_read: bool
    is_unread: bool
    severity_rank: int
    label: str
    age_seconds: float


class NotificationCreate(ApiModel):
    """Payload used to emit a notification."""

    recipient_id: str = Field(min_length=1, max_length=120)
    channel: Channel
    kind: NotificationKind
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4_000)
    variables: dict[str, Any] = Field(default_factory=dict)
    severity: Severity = Severity.INFO
    action_url: str = Field(default="", max_length=2_000)


class NotificationPage(ApiModel):
    """A filtered, paginated notification listing."""

    items: list[NotificationRead]
    total: int
    unread: int
    limit: int
    offset: int


class DeliveryDecisionRead(ApiModel):
    """Explanation of whether a notification was delivered."""

    channel: Channel
    delivered: bool
    reason: str
    suppressed_until_hour: int | None = None


class CreateResultRead(ApiModel):
    """Result of emitting a notification."""

    notification: NotificationRead
    decision: DeliveryDecisionRead
    delivered: bool


class MarkReadResult(ApiModel):
    """Summary of a mark-read operation."""

    notification_id: str | None = None
    modified: int
    unread: int


class RecipientRequest(ApiModel):
    """Payload carrying only a recipient identifier."""

    recipient_id: str = Field(min_length=1, max_length=120)


class PreferenceRead(ApiModel):
    """Delivery settings for a channel and kind."""

    recipient_id: str
    channel: Channel
    kind: NotificationKind
    enabled: bool
    quiet_start_hour: int
    quiet_end_hour: int
    quiet_hours: str


class PreferenceUpsert(ApiModel):
    """Payload used to change one preference row."""

    recipient_id: str = Field(min_length=1, max_length=120)
    channel: Channel
    kind: NotificationKind
    enabled: bool = True
    quiet_start_hour: int = Field(default=0, ge=0, le=23)
    quiet_end_hour: int = Field(default=0, ge=0, le=23)


class PreferenceList(ApiModel):
    """Every effective preference of a recipient."""

    recipient_id: str
    preferences: list[PreferenceRead]


class DigestEntryRead(ApiModel):
    """A single notification condensed into a digest."""

    notification_id: str
    kind: NotificationKind
    severity: Severity
    title: str
    body: str
    created_at: datetime
    action_url: str = ""


class DigestGroupRead(ApiModel):
    """Digest entries sharing a kind and severity."""

    kind: NotificationKind
    severity: Severity
    count: int
    headline: str
    entries: list[DigestEntryRead]


class DigestRead(ApiModel):
    """A persisted digest."""

    id: str
    recipient_id: str
    period: DigestPeriod
    entries: list[DigestEntryRead]
    groups: list[DigestGroupRead]
    total: int
    sent_at: datetime | None = None
    is_sent: bool
    markdown: str


class DigestPreviewRead(ApiModel):
    """An unsaved digest preview rendered on demand."""

    recipient_id: str
    period: DigestPeriod
    total: int
    groups: list[DigestGroupRead]
    entries: list[DigestEntryRead]
    markdown: str
    generated_at: datetime


class DigestSendRequest(ApiModel):
    """Payload selecting a digest to dispatch."""

    digest_id: str = Field(min_length=1)


class StatsRead(ApiModel):
    """Aggregated notification counters."""

    total: int
    read: int
    unread: int
    critical_unread: int
    read_rate: float
    by_channel: dict[str, int]
    by_kind: dict[str, int]
    by_severity: dict[str, int]


class PruneRequest(ApiModel):
    """Payload controlling retention pruning."""

    max_age_days: int = Field(default=30, ge=1, le=3650)
    keep_unread: bool = True


class PruneResult(ApiModel):
    """Outcome of a retention prune."""

    removed: int
    max_age_days: int
    keep_unread: bool
