"""Typed request and response models for the integrations API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.features.integrations_webhooks.models import (
    DeliveryStatus,
    IntegrationKind,
)


class IntegrationApiModel(BaseModel):
    """Base model with attribute validation for the integrations feature."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class IntegrationRead(IntegrationApiModel):
    """A configured integration as returned by the API."""

    id: str
    name: str
    kind: IntegrationKind
    endpoint_url: str
    events: list[str]
    masked_secret: str
    has_secret: bool
    enabled: bool
    created_at: datetime
    host: str
    scheme: str
    event_count: int
    is_active: bool
    subscribers_label: str


class IntegrationCreate(IntegrationApiModel):
    """Payload used to register an integration."""

    name: str = Field(min_length=1, max_length=120)
    kind: IntegrationKind
    endpoint_url: str = Field(min_length=1, max_length=2048)
    events: list[str] = Field(min_length=1, max_length=32)
    secret: str = Field(default="", max_length=512)
    enabled: bool = True


class IntegrationUpdate(IntegrationApiModel):
    """Partial update of an integration."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: IntegrationKind | None = None
    endpoint_url: str | None = Field(default=None, max_length=2048)
    events: list[str] | None = Field(default=None, max_length=32)
    secret: str | None = Field(default=None, max_length=512)
    enabled: bool | None = None


class EnabledUpdate(IntegrationApiModel):
    """Payload used to toggle an integration."""

    enabled: bool


class DeliveryRead(IntegrationApiModel):
    """A delivery ledger entry as returned by the API."""

    id: str
    integration_id: str
    event: str
    payload: dict[str, Any]
    status: DeliveryStatus
    attempts: int
    response_code: int | None
    sent_at: datetime | None
    signature: str
    can_retry: bool
    retry_after_seconds: float
    status_label: str


class AdapterRead(IntegrationApiModel):
    """An event adapter as returned by the API."""

    id: str
    name: str
    event_map: dict[str, str]
    mapping_count: int
    created_at: datetime


class AdapterCreate(IntegrationApiModel):
    """Payload used to register an event adapter."""

    name: str = Field(min_length=1, max_length=120)
    event_map: dict[str, str] = Field(min_length=1, max_length=32)


class IntegrationStatsRead(IntegrationApiModel):
    """Aggregated counters for the integrations dashboard."""

    total_integrations: int
    enabled_integrations: int
    total_adapters: int
    total_deliveries: int
    pending_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: float
    failure_rate: float
    average_attempts: float
    last_sent_at: datetime | None
    by_event: dict[str, int]
    by_kind: dict[str, int]


class DispatchRequest(IntegrationApiModel):
    """Payload used to dispatch an event to matching integrations."""

    event: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    simulate_status: DeliveryStatus | None = None
    response_code: int | None = Field(default=None, ge=100, le=599)


class SimulationRequest(IntegrationApiModel):
    """Payload used to simulate a transport result for a delivery."""

    status: DeliveryStatus
    response_code: int | None = Field(default=None, ge=100, le=599)


class OperationResult(IntegrationApiModel):
    """Result of a mutation that does not return an entity."""

    ok: bool
    removed: int = 0
    message: str = ""
