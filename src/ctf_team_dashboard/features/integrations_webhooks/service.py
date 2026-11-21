"""Business rules for creating integrations and dispatching their deliveries."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.integrations_webhooks.models import (
    SIGNATURE_ALGORITHM,
    Adapter,
    Delivery,
    DeliveryStats,
    DeliveryStatus,
    Integration,
    IntegrationKind,
    canonical_json,
    default_payload_template,
    delivery_stats,
    encode_event_map,
    encode_events,
    encode_payload,
    hash_secret,
    hmac_signature,
    map_event_through_adapters,
    normalise_event_map,
    normalise_events,
    render_payload_template,
    validate_endpoint_url,
)
from ctf_team_dashboard.features.integrations_webhooks.store import (
    AdapterRepository,
    DeliveryRepository,
    IntegrationRepository,
)

MAX_NAME_LENGTH = 120


@dataclass(frozen=True, slots=True)
class DispatchResult:
    """The outcome of dispatching one event."""

    deliveries: tuple[Delivery, ...]
    matched_integrations: int
    mapped_events: tuple[str, ...]

    @property
    def delivery_count(self) -> int:
        """Return the number of recorded deliveries."""
        return len(self.deliveries)


@dataclass(frozen=True, slots=True)
class IntegrationReport:
    """The aggregated statistics rendered by the UI."""

    total_integrations: int
    enabled_integrations: int
    total_adapters: int
    stats: DeliveryStats
    by_event: dict[str, int]
    by_kind: dict[str, int]

    @property
    def success_rate(self) -> float:
        """Return the successful share of deliveries."""
        return self.stats.success_rate

    @property
    def failure_rate(self) -> float:
        """Return the failed share of deliveries."""
        return self.stats.failure_rate

    @property
    def average_attempts(self) -> float:
        """Return the mean attempts per delivery."""
        return self.stats.average_attempts

    @property
    def last_sent_at(self) -> datetime | None:
        """Return the most recent transport timestamp."""
        return self.stats.last_sent_at


def _parse_status(value: DeliveryStatus | str) -> DeliveryStatus:
    """Parse a delivery status from a string, raising a domain error."""
    if isinstance(value, DeliveryStatus):
        return value
    try:
        return DeliveryStatus(value.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(status.value for status in DeliveryStatus)
        raise ValidationError(f"Unknown delivery status {value!r}; expected {allowed}") from exc


def _validate_response_code(
    status: DeliveryStatus,
    response_code: int | None,
) -> int:
    """Return a validated response code for a simulated transport result."""
    code = (
        response_code
        if response_code is not None
        else (200 if status is DeliveryStatus.SUCCESS else 500)
    )
    if not 100 <= code <= 599:
        raise ValidationError("Response code must be between 100 and 599")
    if status is DeliveryStatus.SUCCESS and not 200 <= code < 300:
        raise ValidationError("A successful delivery needs a 2xx response code")
    if status is DeliveryStatus.FAILED and code < 400:
        raise ValidationError("A failed delivery needs a 4xx or 5xx response code")
    return code


class IntegrationService:
    """Coordinate integrations, adapters and the delivery ledger."""

    def __init__(
        self,
        integrations: IntegrationRepository | None = None,
        deliveries: DeliveryRepository | None = None,
        adapters: AdapterRepository | None = None,
    ) -> None:
        self.integrations = integrations or IntegrationRepository()
        self.deliveries = deliveries or DeliveryRepository()
        self.adapters = adapters or AdapterRepository()

    @staticmethod
    def _new_id(prefix: str) -> str:
        """Return a unique identifier with the given prefix."""
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _clean_name(name: str) -> str:
        """Validate and trim a human readable resource name."""
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError("Name must not be empty")
        if len(cleaned) > MAX_NAME_LENGTH:
            raise ValidationError(f"Name must be at most {MAX_NAME_LENGTH} characters long")
        return cleaned

    # ------------------------------------------------------------------
    # Integrations
    # ------------------------------------------------------------------
    def create_integration(
        self,
        *,
        name: str,
        kind: IntegrationKind | str,
        endpoint_url: str,
        events: tuple[str, ...] | list[str],
        secret: str = "",
        enabled: bool = True,
    ) -> Integration:
        """Create a validated integration with a hashed signing secret.

        Raises:
            ValidationError: When any supplied field is invalid.
            ConflictError: When the name is already registered.
        """
        cleaned_name = self._clean_name(name)
        if self.integrations.get_by_name(cleaned_name) is not None:
            raise ConflictError(f"Integration {cleaned_name!r} already exists")
        try:
            parsed_kind = IntegrationKind.parse(kind) if isinstance(kind, str) else kind
            url = validate_endpoint_url(endpoint_url)
            subscribed = normalise_events(events)
            secret_hash = hash_secret(secret) if secret else ""
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        integration = Integration(
            id=self._new_id("int"),
            name=cleaned_name,
            kind=parsed_kind,
            endpoint_url=url,
            events_json=encode_events(subscribed),
            secret_hash=secret_hash,
            enabled=enabled,
        )
        return self.integrations.create(integration)

    def update_integration(
        self,
        integration_id: str,
        *,
        name: str | None = None,
        kind: IntegrationKind | str | None = None,
        endpoint_url: str | None = None,
        events: tuple[str, ...] | list[str] | None = None,
        secret: str | None = None,
        enabled: bool | None = None,
    ) -> Integration:
        """Update the mutable fields of an integration.

        An empty ``secret`` clears the configured signing key. Omitting it
        leaves the existing digest untouched so the plaintext is never needed.
        """
        existing = self.get_integration(integration_id)
        try:
            parsed_kind = IntegrationKind.parse(kind) if isinstance(kind, str) else kind
            url = validate_endpoint_url(endpoint_url) if endpoint_url is not None else None
            subscribed = normalise_events(events) if events is not None else None
            if secret is None:
                secret_hash: str | None = None
            elif secret:
                secret_hash = hash_secret(secret)
            else:
                secret_hash = ""
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        updated = existing.with_changes(
            name=self._clean_name(name) if name is not None else None,
            kind=parsed_kind,
            endpoint_url=url,
            events=subscribed,
            secret_hash=secret_hash,
            enabled=enabled,
        )
        clash = self.integrations.get_by_name(updated.name)
        if clash is not None and clash.id != updated.id:
            raise ConflictError(f"Integration {updated.name!r} already exists")
        return self.integrations.update(updated)

    def set_enabled(self, integration_id: str, enabled: bool) -> Integration:
        """Enable or disable an integration."""
        return self.update_integration(integration_id, enabled=enabled)

    def get_integration(self, integration_id: str) -> Integration:
        """Return an integration or raise :class:`NotFoundError`."""
        integration = self.integrations.get(integration_id)
        if integration is None:
            raise NotFoundError(f"Integration {integration_id!r} does not exist")
        return integration

    def list_integrations(self) -> list[Integration]:
        """Return every configured integration."""
        return self.integrations.list_all()

    def delete_integration(self, integration_id: str) -> None:
        """Delete an integration together with its delivery history."""
        self.get_integration(integration_id)
        self.deliveries.delete_for_integration(integration_id)
        self.integrations.delete(integration_id)

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------
    def dispatch(
        self,
        event: str,
        payload: Mapping[str, object],
        *,
        now: datetime | None = None,
        simulate_status: DeliveryStatus | str | None = None,
        response_code: int | None = None,
    ) -> DispatchResult:
        """Record one delivery for every enabled matching integration.

        No network call is made. Payloads are templated and signed with the
        integration's stored signing key, then appended to the ledger in the
        pending state unless a simulated transport result is supplied.
        """
        raw_event = event.strip().lower()
        if not raw_event:
            raise ValidationError("Event must not be empty")
        moment = now or utcnow()
        status = _parse_status(simulate_status) if simulate_status is not None else None
        code = _validate_response_code(status, response_code) if status is not None else None
        adapters = self.adapters.list_all()
        targets = map_event_through_adapters(raw_event, adapters)
        deliveries: list[Delivery] = []
        matched = 0
        for target in targets:
            for integration in self.integrations.list_supporting(target):
                matched += 1
                delivery_id = self._new_id("del")
                context: dict[str, object] = {
                    "event": raw_event,
                    "mapped_event": target,
                    "delivery_id": delivery_id,
                    "timestamp": moment.isoformat(),
                    "payload": dict(payload),
                    "integration": {
                        "id": integration.id,
                        "name": integration.name,
                        "kind": integration.kind.value,
                    },
                }
                rendered = render_payload_template(default_payload_template(), context)
                if integration.has_secret:
                    body = canonical_json(rendered)
                    rendered["signature"] = hmac_signature(integration.secret_hash, body)
                    rendered["signature_algorithm"] = SIGNATURE_ALGORITHM
                delivery = Delivery(
                    id=delivery_id,
                    integration_id=integration.id,
                    event=target,
                    payload_json=encode_payload(rendered),
                    status=DeliveryStatus.PENDING,
                )
                if status is not None:
                    delivery = delivery.with_attempt(
                        status=status,
                        response_code=code,
                        sent_at=moment,
                    )
                self.deliveries.create(delivery)
                deliveries.append(delivery)
        return DispatchResult(
            deliveries=tuple(deliveries),
            matched_integrations=matched,
            mapped_events=targets,
        )

    def list_deliveries(
        self,
        *,
        status: DeliveryStatus | None = None,
        integration_id: str | None = None,
        limit: int = 200,
    ) -> list[Delivery]:
        """Return deliveries with optional status and integration filters."""
        return self.deliveries.list_all(status=status, integration_id=integration_id, limit=limit)

    def get_delivery(self, delivery_id: str) -> Delivery:
        """Return a delivery or raise :class:`NotFoundError`."""
        delivery = self.deliveries.get(delivery_id)
        if delivery is None:
            raise NotFoundError(f"Delivery {delivery_id!r} does not exist")
        return delivery

    def simulate_delivery(
        self,
        delivery_id: str,
        status: DeliveryStatus | str,
        response_code: int | None = None,
        *,
        now: datetime | None = None,
    ) -> Delivery:
        """Record a simulated transport result without making a request."""
        delivery = self.get_delivery(delivery_id)
        parsed = _parse_status(status)
        if parsed is DeliveryStatus.PENDING:
            raise ValidationError("A simulation result must be success or failed")
        code = _validate_response_code(parsed, response_code)
        updated = delivery.with_attempt(
            status=parsed,
            response_code=code,
            sent_at=now or utcnow(),
        )
        return self.deliveries.update(updated)

    def retry_delivery(self, delivery_id: str) -> Delivery:
        """Queue a failed or pending delivery for another attempt."""
        delivery = self.get_delivery(delivery_id)
        if not delivery.can_retry:
            raise ConflictError("Successful deliveries cannot be retried")
        retried = delivery.with_attempt(
            status=DeliveryStatus.PENDING,
            response_code=None,
            sent_at=delivery.sent_at or utcnow(),
        )
        return self.deliveries.update(retried)

    # ------------------------------------------------------------------
    # Adapters
    # ------------------------------------------------------------------
    def create_adapter(
        self,
        *,
        name: str,
        event_map: Mapping[str, str],
    ) -> Adapter:
        """Create an adapter that rewrites event names."""
        cleaned_name = self._clean_name(name)
        if self.adapters.get_by_name(cleaned_name) is not None:
            raise ConflictError(f"Adapter {cleaned_name!r} already exists")
        try:
            mappings = normalise_event_map(event_map)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        adapter = Adapter(
            id=self._new_id("adt"),
            name=cleaned_name,
            event_map_json=encode_event_map(mappings),
        )
        return self.adapters.create(adapter)

    def list_adapters(self) -> list[Adapter]:
        """Return every configured adapter."""
        return self.adapters.list_all()

    def get_adapter(self, adapter_id: str) -> Adapter:
        """Return an adapter or raise :class:`NotFoundError`."""
        adapter = self.adapters.get(adapter_id)
        if adapter is None:
            raise NotFoundError(f"Adapter {adapter_id!r} does not exist")
        return adapter

    def delete_adapter(self, adapter_id: str) -> None:
        """Delete an adapter."""
        self.get_adapter(adapter_id)
        self.adapters.delete(adapter_id)

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------
    def stats(self) -> IntegrationReport:
        """Return the headline statistics for the integrations screen."""
        integrations = self.integrations.list_all()
        deliveries = self.deliveries.list_all(limit=1_000)
        by_event = Counter(delivery.event for delivery in deliveries)
        by_kind = Counter(integration.kind.value for integration in integrations)
        return IntegrationReport(
            total_integrations=len(integrations),
            enabled_integrations=sum(1 for integration in integrations if integration.enabled),
            total_adapters=len(self.adapters.list_all()),
            stats=delivery_stats(deliveries),
            by_event=dict(sorted(by_event.items())),
            by_kind=dict(sorted(by_kind.items())),
        )
