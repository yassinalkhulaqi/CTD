"""Domain entities and pure rules for the webhook integrations feature.

The module deliberately contains no I/O. Every calculation that can be tested
without a database or a network lives here: address validation, event
allowlisting, secret hashing and masking, HMAC signatures, payload templating,
retry backoff and delivery statistics.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from ctf_team_dashboard.domain.models import utcnow

SIGNATURE_ALGORITHM = "HMAC-SHA256"
SECRET_HASH_LENGTH = 64
MIN_SECRET_LENGTH = 8
MAX_SECRET_LENGTH = 512
MAX_URL_LENGTH = 2048
DEFAULT_BASE_RETRY_SECONDS = 2.0
DEFAULT_RETRY_MULTIPLIER = 2.0
DEFAULT_RETRY_CAP_SECONDS = 300.0

EVENT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "challenge.created",
        "challenge.solved",
        "event.started",
        "event.ended",
        "flag.submitted",
        "hint.revealed",
        "member.joined",
        "score.changed",
        "solve.created",
        "submission.failed",
        "team.updated",
        "writeup.published",
    }
)

_TEMPLATE_PATTERN = re.compile(r"\{\{([^{}]+)\}\}")


class IntegrationKind(str, Enum):
    """The transport family of an integration."""

    WEBHOOK = "webhook"
    SLACK = "slack"
    CTF_PLATFORM = "ctf_platform"

    @property
    def label(self) -> str:
        """Return the display label of the transport."""
        return {
            IntegrationKind.WEBHOOK: "Webhook",
            IntegrationKind.SLACK: "Slack",
            IntegrationKind.CTF_PLATFORM: "CTF platform",
        }[self]

    @property
    def signs_payloads(self) -> bool:
        """Return whether this transport normally carries a signature."""
        return self is not IntegrationKind.SLACK

    @classmethod
    def parse(cls, value: str) -> IntegrationKind:
        """Parse a kind from user input.

        Args:
            value: The raw kind value.

        Returns:
            The parsed integration kind.

        Raises:
            ValueError: When the value is not a supported kind.
        """
        candidate = value.strip().lower()
        try:
            return cls(candidate)
        except ValueError as exc:
            allowed = ", ".join(kind.value for kind in cls)
            raise ValueError(f"Unsupported integration kind {value!r}; expected {allowed}") from exc


class DeliveryStatus(str, Enum):
    """The lifecycle state of a recorded delivery."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

    @property
    def label(self) -> str:
        """Return the display label of the status."""
        return {
            DeliveryStatus.PENDING: "Pending",
            DeliveryStatus.SUCCESS: "Delivered",
            DeliveryStatus.FAILED: "Failed",
        }[self]

    @property
    def is_terminal(self) -> bool:
        """Return whether no further transition is expected."""
        return self is not DeliveryStatus.PENDING


def validate_endpoint_url(value: str) -> str:
    """Validate and normalise an integration endpoint address.

    Args:
        value: The caller supplied URL.

    Returns:
        A normalised http or https URL.

    Raises:
        ValueError: When the scheme, host or shape is not acceptable.
    """
    candidate = value.strip()
    if not candidate:
        raise ValueError("Endpoint URL must not be empty")
    if len(candidate) > MAX_URL_LENGTH:
        raise ValueError("Endpoint URL is too long")
    parts = urlsplit(candidate)
    if parts.scheme.lower() not in {"http", "https"}:
        raise ValueError("Endpoint URL must use http or https")
    if not parts.netloc or not parts.hostname:
        raise ValueError("Endpoint URL must include a host")
    if parts.username is not None or parts.password is not None:
        raise ValueError("Endpoint URL must not embed credentials")
    if parts.fragment:
        raise ValueError("Endpoint URL must not include a fragment")
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def normalise_events(
    events: Iterable[str],
    allowlist: frozenset[str] = EVENT_ALLOWLIST,
) -> tuple[str, ...]:
    """Normalise, validate and de-duplicate a subscription list.

    Args:
        events: Raw event names.
        allowlist: The set of events an integration may subscribe to.

    Returns:
        The ordered, lower-case event tuple.

    Raises:
        ValueError: When the list is empty or contains an unknown event.
    """
    cleaned: list[str] = []
    for raw in events:
        event = raw.strip().lower()
        if not event:
            continue
        if event not in allowlist:
            allowed = ", ".join(sorted(allowlist))
            raise ValueError(f"Unknown event {raw!r}; allowed events: {allowed}")
        if event not in cleaned:
            cleaned.append(event)
    if not cleaned:
        raise ValueError("At least one subscribed event is required")
    return tuple(cleaned)


def normalise_event_map(value: Mapping[str, str]) -> dict[str, str]:
    """Validate an adapter event map against the allowlist.

    Args:
        value: Source event to target event mapping.

    Returns:
        The normalised mapping.

    Raises:
        ValueError: When a source or target is not an allowed event.
    """
    normalised: dict[str, str] = {}
    for raw_source, raw_target in value.items():
        source = raw_source.strip().lower()
        target = raw_target.strip().lower()
        if source not in EVENT_ALLOWLIST or target not in EVENT_ALLOWLIST:
            raise ValueError("Adapter mappings may only use allowlisted events")
        if not source or not target:
            raise ValueError("Adapter mappings must not be empty")
        normalised[source] = target
    if not normalised:
        raise ValueError("An adapter requires at least one mapping")
    return normalised


def hash_secret(secret: str) -> str:
    """Derive the stored signing key from a plaintext secret.

    The plaintext is never persisted or logged. The resulting digest is used as
    the HMAC key when delivery payloads are signed.

    Args:
        secret: The plaintext secret supplied by the operator.

    Returns:
        The hexadecimal digest of the secret.

    Raises:
        ValueError: When the secret is too short or too long.
    """
    if len(secret) < MIN_SECRET_LENGTH:
        raise ValueError(f"Secret must be at least {MIN_SECRET_LENGTH} characters long")
    if len(secret) > MAX_SECRET_LENGTH:
        raise ValueError(f"Secret must be at most {MAX_SECRET_LENGTH} characters long")
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def verify_secret(secret: str, secret_hash: str) -> bool:
    """Compare a plaintext secret with a stored digest in constant time."""
    return hmac.compare_digest(hash_secret(secret), secret_hash)


def mask_secret(secret_hash: str) -> str:
    """Return a safe display form derived from a stored digest."""
    if not secret_hash:
        return "not configured"
    return f"whsec_{secret_hash[:8]}\u2022\u2022\u2022\u2022{secret_hash[-4:]}"


def hmac_signature(secret_hash: str, body: str) -> str:
    """Sign a canonical payload body with HMAC-SHA256.

    Args:
        secret_hash: The hexadecimal signing key stored on the integration.
        body: The canonical JSON body to sign.

    Returns:
        The hexadecimal signature.

    Raises:
        ValueError: When the integration has no usable signing key.
    """
    if len(secret_hash) != SECRET_HASH_LENGTH:
        raise ValueError("A configured secret is required to sign a payload")
    try:
        key = bytes.fromhex(secret_hash)
    except ValueError as exc:
        raise ValueError("The stored signing key is malformed") from exc
    return hmac.new(key, body.encode("utf-8"), hashlib.sha256).hexdigest()


def encode_events(events: Iterable[str]) -> str:
    """Serialise event subscriptions to their storage representation."""
    return json.dumps(list(events), separators=(",", ":"), ensure_ascii=False)


def decode_events(raw: str | None) -> tuple[str, ...]:
    """Parse an event subscription list from storage."""
    if not raw:
        return ()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    if not isinstance(decoded, list):
        return ()
    return tuple(str(item) for item in decoded if isinstance(item, str))


def encode_payload(payload: Mapping[str, Any]) -> str:
    """Serialise a delivery payload to its storage representation."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


def decode_payload(raw: str | None) -> dict[str, Any]:
    """Parse a delivery payload from storage."""
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def encode_event_map(event_map: Mapping[str, str]) -> str:
    """Serialise an adapter event map to its storage representation."""
    return json.dumps(dict(event_map), separators=(",", ":"), ensure_ascii=False, sort_keys=True)


def decode_event_map(raw: str | None) -> dict[str, str]:
    """Parse an adapter event map from storage."""
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, dict):
        return {}
    return {str(key): str(value) for key, value in decoded.items()}


def canonical_json(value: Any) -> str:
    """Return the deterministic JSON representation used for signing."""
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def _resolve_path(context: Mapping[str, Any], path: str) -> Any:
    """Resolve a dotted template path inside a context mapping."""
    current: Any = context
    for part in path.strip().split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            raise KeyError(path)
    return current


def render_value(value: Any, context: Mapping[str, Any]) -> Any:
    """Render a single template value, preserving typed placeholders.

    A value consisting of exactly one placeholder resolves to the original
    object, which keeps nested payload dictionaries intact. Mixed strings are
    rendered by substituting each placeholder with its string form.
    """
    if isinstance(value, str):
        exact = _TEMPLATE_PATTERN.fullmatch(value)
        if exact is not None:
            return _resolve_path(context, exact.group(1))
        return _TEMPLATE_PATTERN.sub(
            lambda match: str(_resolve_path(context, match.group(1))),
            value,
        )
    if isinstance(value, Mapping):
        return {str(key): render_value(item, context) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [render_value(item, context) for item in value]
    return value


def render_payload_template(
    template: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Render a payload template against a context mapping."""
    rendered = render_value(dict(template), context)
    return rendered if isinstance(rendered, dict) else {}


def default_payload_template() -> dict[str, Any]:
    """Return the standard envelope template used for dispatched events."""
    return {
        "event": "{{event}}",
        "mapped_event": "{{mapped_event}}",
        "delivery_id": "{{delivery_id}}",
        "integration": {
            "id": "{{integration.id}}",
            "name": "{{integration.name}}",
            "kind": "{{integration.kind}}",
        },
        "occurred_at": "{{timestamp}}",
        "data": "{{payload}}",
    }


def retry_delay(
    attempt: int,
    *,
    base: float = DEFAULT_BASE_RETRY_SECONDS,
    multiplier: float = DEFAULT_RETRY_MULTIPLIER,
    cap: float = DEFAULT_RETRY_CAP_SECONDS,
) -> float:
    """Return the backoff delay before a given retry attempt.

    Args:
        attempt: The one-based number of the retry.
        base: The delay of the first retry in seconds.
        multiplier: The exponential growth factor.
        cap: The maximum delay in seconds.

    Returns:
        The rounded delay in seconds.

    Raises:
        ValueError: When the attempt number is not positive.
    """
    if attempt < 1:
        raise ValueError("Retry attempts are one-based")
    delay = base * multiplier ** (attempt - 1)
    return round(min(delay, cap), 3)


def retry_schedule(
    count: int,
    *,
    base: float = DEFAULT_BASE_RETRY_SECONDS,
    multiplier: float = DEFAULT_RETRY_MULTIPLIER,
    cap: float = DEFAULT_RETRY_CAP_SECONDS,
) -> tuple[float, ...]:
    """Return the delays of the first ``count`` retries."""
    return tuple(
        retry_delay(index, base=base, multiplier=multiplier, cap=cap)
        for index in range(1, count + 1)
    )


@dataclass(frozen=True, slots=True)
class Integration:
    """A configured outbound integration."""

    id: str
    name: str
    kind: IntegrationKind
    endpoint_url: str
    events_json: str
    secret_hash: str = ""
    enabled: bool = True
    created_at: datetime = field(default_factory=utcnow)

    @property
    def events(self) -> tuple[str, ...]:
        """Return the subscribed events."""
        return decode_events(self.events_json)

    @property
    def event_count(self) -> int:
        """Return the number of subscribed events."""
        return len(self.events)

    @property
    def has_secret(self) -> bool:
        """Return whether a signing secret is configured."""
        return bool(self.secret_hash)

    @property
    def masked_secret(self) -> str:
        """Return the safe display form of the signing secret."""
        return mask_secret(self.secret_hash)

    @property
    def host(self) -> str:
        """Return the destination host of the integration."""
        return urlsplit(self.endpoint_url).hostname or ""

    @property
    def scheme(self) -> str:
        """Return the destination scheme of the integration."""
        return urlsplit(self.endpoint_url).scheme

    @property
    def is_active(self) -> bool:
        """Return whether the integration may receive events."""
        return self.enabled and self.event_count > 0

    @property
    def subscribers_label(self) -> str:
        """Return a compact description of the event subscriptions."""
        return ", ".join(self.events) if self.events else "no events"

    def supports(self, event: str) -> bool:
        """Return whether this integration is enabled for an event."""
        return self.enabled and event in self.events

    def with_changes(
        self,
        *,
        name: str | None = None,
        kind: IntegrationKind | None = None,
        endpoint_url: str | None = None,
        events: tuple[str, ...] | None = None,
        secret_hash: str | None = None,
        enabled: bool | None = None,
    ) -> Integration:
        """Return a copy with the supplied fields replaced."""
        return Integration(
            id=self.id,
            name=self.name if name is None else name,
            kind=self.kind if kind is None else kind,
            endpoint_url=self.endpoint_url if endpoint_url is None else endpoint_url,
            events_json=self.events_json if events is None else encode_events(events),
            secret_hash=self.secret_hash if secret_hash is None else secret_hash,
            enabled=self.enabled if enabled is None else enabled,
            created_at=self.created_at,
        )


@dataclass(frozen=True, slots=True)
class Delivery:
    """A recorded attempt to deliver one event to one integration."""

    id: str
    integration_id: str
    event: str
    payload_json: str
    status: DeliveryStatus
    attempts: int = 0
    response_code: int | None = None
    sent_at: datetime | None = None

    @property
    def payload(self) -> dict[str, Any]:
        """Return the decoded delivery payload."""
        return decode_payload(self.payload_json)

    @property
    def signature(self) -> str:
        """Return the signature attached to the payload, if any."""
        return str(self.payload.get("signature", ""))

    @property
    def is_pending(self) -> bool:
        """Return whether the delivery is waiting for transport."""
        return self.status is DeliveryStatus.PENDING

    @property
    def is_success(self) -> bool:
        """Return whether the delivery completed successfully."""
        return self.status is DeliveryStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        """Return whether the delivery failed."""
        return self.status is DeliveryStatus.FAILED

    @property
    def can_retry(self) -> bool:
        """Return whether a retry is permitted."""
        return not self.is_success

    @property
    def retry_after_seconds(self) -> float:
        """Return the backoff before the next retry."""
        return retry_delay(self.attempts + 1)

    @property
    def status_label(self) -> str:
        """Return the display label of the status."""
        return self.status.label

    def with_attempt(
        self,
        *,
        status: DeliveryStatus,
        response_code: int | None,
        sent_at: datetime,
        increment: bool = True,
    ) -> Delivery:
        """Return a copy reflecting a transport attempt."""
        return Delivery(
            id=self.id,
            integration_id=self.integration_id,
            event=self.event,
            payload_json=self.payload_json,
            status=status,
            attempts=self.attempts + 1 if increment else self.attempts,
            response_code=response_code,
            sent_at=sent_at,
        )


@dataclass(frozen=True, slots=True)
class Adapter:
    """A mapping that rewrites incoming events for integrations."""

    id: str
    name: str
    event_map_json: str
    created_at: datetime = field(default_factory=utcnow)

    @property
    def event_map(self) -> dict[str, str]:
        """Return the decoded event mapping."""
        return decode_event_map(self.event_map_json)

    @property
    def mapping_count(self) -> int:
        """Return the number of mappings in the adapter."""
        return len(self.event_map)

    @property
    def source_events(self) -> tuple[str, ...]:
        """Return the source events understood by the adapter."""
        return tuple(sorted(self.event_map))

    def maps(self, event: str) -> bool:
        """Return whether the adapter has a mapping for an event."""
        return event in self.event_map

    def map_event(self, event: str) -> str:
        """Map an event to its target, returning the original when absent."""
        return self.event_map.get(event, event)


def map_event_through_adapters(event: str, adapters: Iterable[Adapter]) -> tuple[str, ...]:
    """Return all adapter targets for an event in stable order.

    When no adapter applies, the original event is returned so dispatchers can
    always work with a non-empty tuple.
    """
    targets: list[str] = []
    for adapter in adapters:
        if adapter.maps(event):
            target = adapter.map_event(event)
            if target not in targets:
                targets.append(target)
    return tuple(targets) if targets else (event,)


@dataclass(frozen=True, slots=True)
class DeliveryStats:
    """Aggregated delivery counters used by the statistics panel."""

    total: int = 0
    pending: int = 0
    success: int = 0
    failed: int = 0
    attempts: int = 0
    last_sent_at: datetime | None = None

    @property
    def success_rate(self) -> float:
        """Return the fraction of deliveries that succeeded."""
        if self.total <= 0:
            return 0.0
        return self.success / self.total

    @property
    def failure_rate(self) -> float:
        """Return the fraction of deliveries that failed."""
        if self.total <= 0:
            return 0.0
        return self.failed / self.total

    @property
    def average_attempts(self) -> float:
        """Return the mean number of attempts per delivery."""
        if self.total <= 0:
            return 0.0
        return self.attempts / self.total

    @property
    def has_failures(self) -> bool:
        """Return whether at least one delivery failed."""
        return self.failed > 0


def delivery_stats(deliveries: Iterable[Delivery]) -> DeliveryStats:
    """Fold a collection of deliveries into aggregate counters."""
    total = 0
    pending = 0
    success = 0
    failed = 0
    attempts = 0
    last_sent_at: datetime | None = None
    for delivery in deliveries:
        total += 1
        attempts += delivery.attempts
        if delivery.is_pending:
            pending += 1
        elif delivery.is_success:
            success += 1
        else:
            failed += 1
        if delivery.sent_at is not None and (
            last_sent_at is None or delivery.sent_at > last_sent_at
        ):
            last_sent_at = delivery.sent_at
    return DeliveryStats(
        total=total,
        pending=pending,
        success=success,
        failed=failed,
        attempts=attempts,
        last_sent_at=last_sent_at,
    )
