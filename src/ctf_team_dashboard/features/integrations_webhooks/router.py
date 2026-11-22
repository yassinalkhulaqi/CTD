"""HTTP API for integrations, deliveries, adapters and statistics."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from ctf_team_dashboard.features.integrations_webhooks.models import DeliveryStatus
from ctf_team_dashboard.features.integrations_webhooks.schemas import (
    AdapterCreate,
    AdapterRead,
    DeliveryRead,
    DispatchRequest,
    IntegrationCreate,
    IntegrationRead,
    IntegrationStatsRead,
    IntegrationUpdate,
    SimulationRequest,
)
from ctf_team_dashboard.features.integrations_webhooks.service import IntegrationService

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


def get_service() -> IntegrationService:
    """Dependency returning a service bound to the current database."""
    return IntegrationService()


ServiceDep = Annotated[IntegrationService, Depends(get_service)]
StatusFilter = Annotated[DeliveryStatus | None, Query(alias="status")]
DeliveryLimit = Annotated[int, Query(ge=1, le=1_000)]


@router.get("/stats", response_model=IntegrationStatsRead)
def get_stats(service: ServiceDep) -> IntegrationStatsRead:
    """Return the aggregated delivery and integration statistics."""
    report = service.stats()
    return IntegrationStatsRead(
        total_integrations=report.total_integrations,
        enabled_integrations=report.enabled_integrations,
        total_adapters=report.total_adapters,
        total_deliveries=report.stats.total,
        pending_deliveries=report.stats.pending,
        successful_deliveries=report.stats.success,
        failed_deliveries=report.stats.failed,
        success_rate=round(report.success_rate, 4),
        failure_rate=round(report.failure_rate, 4),
        average_attempts=round(report.average_attempts, 3),
        last_sent_at=report.last_sent_at,
        by_event=report.by_event,
        by_kind=report.by_kind,
    )


@router.get("/deliveries", response_model=list[DeliveryRead])
def list_deliveries(
    service: ServiceDep,
    status_filter: StatusFilter = None,
    integration_id: str | None = None,
    limit: DeliveryLimit = 200,
) -> list[DeliveryRead]:
    """Return the delivery ledger, newest first, with optional filters."""
    return [
        DeliveryRead.model_validate(delivery)
        for delivery in service.list_deliveries(
            status=status_filter,
            integration_id=integration_id,
            limit=limit,
        )
    ]


@router.post("/deliveries/{delivery_id}/retry", response_model=DeliveryRead)
def retry_delivery(delivery_id: str, service: ServiceDep) -> DeliveryRead:
    """Queue a failed or pending delivery for another attempt."""
    return DeliveryRead.model_validate(service.retry_delivery(delivery_id))


@router.post("/deliveries/{delivery_id}/simulate", response_model=DeliveryRead)
def simulate_delivery(
    delivery_id: str,
    payload: SimulationRequest,
    service: ServiceDep,
) -> DeliveryRead:
    """Record a simulated transport result without making a network call."""
    updated = service.simulate_delivery(
        delivery_id,
        payload.status,
        response_code=payload.response_code,
    )
    return DeliveryRead.model_validate(updated)


@router.get("/adapters", response_model=list[AdapterRead])
def list_adapters(service: ServiceDep) -> list[AdapterRead]:
    """Return every configured event adapter."""
    return [AdapterRead.model_validate(adapter) for adapter in service.list_adapters()]


@router.post("/adapters", response_model=AdapterRead, status_code=status.HTTP_201_CREATED)
def create_adapter(payload: AdapterCreate, service: ServiceDep) -> AdapterRead:
    """Register a new event adapter."""
    adapter = service.create_adapter(name=payload.name, event_map=payload.event_map)
    return AdapterRead.model_validate(adapter)


@router.delete("/adapters/{adapter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_adapter(adapter_id: str, service: ServiceDep) -> Response:
    """Delete an event adapter."""
    service.delete_adapter(adapter_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/dispatch", response_model=list[DeliveryRead])
def dispatch_event(payload: DispatchRequest, service: ServiceDep) -> list[DeliveryRead]:
    """Record deliveries for every enabled integration matching an event."""
    result = service.dispatch(
        payload.event,
        payload.payload,
        simulate_status=payload.simulate_status,
        response_code=payload.response_code,
    )
    return [DeliveryRead.model_validate(delivery) for delivery in result.deliveries]


@router.get("", response_model=list[IntegrationRead])
def list_integrations(service: ServiceDep) -> list[IntegrationRead]:
    """Return every configured integration."""
    return [IntegrationRead.model_validate(item) for item in service.list_integrations()]


@router.get("/{integration_id}", response_model=IntegrationRead)
def get_integration(integration_id: str, service: ServiceDep) -> IntegrationRead:
    """Return a single integration by identifier."""
    return IntegrationRead.model_validate(service.get_integration(integration_id))


@router.post("", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
def create_integration(payload: IntegrationCreate, service: ServiceDep) -> IntegrationRead:
    """Register a new integration with a hashed signing secret."""
    integration = service.create_integration(
        name=payload.name,
        kind=payload.kind,
        endpoint_url=payload.endpoint_url,
        events=payload.events,
        secret=payload.secret,
        enabled=payload.enabled,
    )
    return IntegrationRead.model_validate(integration)


@router.patch("/{integration_id}", response_model=IntegrationRead)
def update_integration(
    integration_id: str,
    payload: IntegrationUpdate,
    service: ServiceDep,
) -> IntegrationRead:
    """Update the mutable fields of an integration."""
    updated = service.update_integration(
        integration_id,
        name=payload.name,
        kind=payload.kind,
        endpoint_url=payload.endpoint_url,
        events=payload.events,
        secret=payload.secret,
        enabled=payload.enabled,
    )
    return IntegrationRead.model_validate(updated)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(integration_id: str, service: ServiceDep) -> Response:
    """Delete an integration and its delivery history."""
    service.delete_integration(integration_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
