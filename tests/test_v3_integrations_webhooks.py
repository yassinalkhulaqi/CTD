"""Tests for the webhook integrations feature."""

from __future__ import annotations

import hashlib
import hmac
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.integrations_webhooks.models import (
    EVENT_ALLOWLIST,
    SIGNATURE_ALGORITHM,
    Adapter,
    Delivery,
    DeliveryStatus,
    Integration,
    IntegrationKind,
    canonical_json,
    decode_events,
    delivery_stats,
    encode_events,
    encode_payload,
    hash_secret,
    hmac_signature,
    mask_secret,
    normalise_event_map,
    normalise_events,
    render_payload_template,
    retry_delay,
    retry_schedule,
    validate_endpoint_url,
    verify_secret,
)
from ctf_team_dashboard.features.integrations_webhooks.service import IntegrationService
from ctf_team_dashboard.features.integrations_webhooks.store import (
    AdapterRepository,
    DeliveryRepository,
    IntegrationRepository,
)

SECRET = "a-very-secret-signing-key"


@pytest.fixture
def service(database: Database) -> IntegrationService:
    """Return a service bound to the isolated test database."""
    return IntegrationService()


def _integration(
    name: str = "Primary hooks",
    *,
    kind: IntegrationKind = IntegrationKind.WEBHOOK,
    url: str = "https://example.com/hook",
    events: tuple[str, ...] = ("challenge.solved",),
    secret: str = "",
    enabled: bool = True,
) -> Integration:
    """Build an integration entity for store level tests."""
    return Integration(
        id=f"int-{name.lower().replace(' ', '-')}",
        name=name,
        kind=kind,
        endpoint_url=url,
        events_json=encode_events(events),
        secret_hash=hash_secret(secret) if secret else "",
        enabled=enabled,
    )


# ----------------------------------------------------------------------
# Pure domain rules
# ----------------------------------------------------------------------
def test_validate_endpoint_url_normalises_http_and_https() -> None:
    assert validate_endpoint_url(" HTTPS://Example.COM/hook?a=1 ") == (
        "https://example.com/hook?a=1"
    )
    assert validate_endpoint_url("http://localhost:9000") == "http://localhost:9000/"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "ftp://example.com/hook",
        "https:///missing-host",
        "https://user:pass@example.com/hook",
        "https://example.com/hook#fragment",
    ],
)
def test_validate_endpoint_url_rejects_unsafe_addresses(value: str) -> None:
    with pytest.raises(ValueError, match="Endpoint URL"):
        validate_endpoint_url(value)


def test_normalise_events_deduplicates_and_enforces_allowlist() -> None:
    assert normalise_events([" Challenge.Solved ", "challenge.solved", "score.changed"]) == (
        "challenge.solved",
        "score.changed",
    )
    with pytest.raises(ValueError, match="Unknown event"):
        normalise_events(["not.an.event"])
    with pytest.raises(ValueError, match="At least one"):
        normalise_events(["  "])
    assert "challenge.solved" in EVENT_ALLOWLIST


def test_secret_hash_mask_and_verification() -> None:
    digest = hash_secret(SECRET)
    assert digest == hashlib.sha256(SECRET.encode("utf-8")).hexdigest()
    assert verify_secret(SECRET, digest)
    assert not verify_secret("incorrect-value", digest)
    masked = mask_secret(digest)
    assert SECRET not in masked
    assert masked.startswith("whsec_")
    assert mask_secret("") == "not configured"
    with pytest.raises(ValueError, match="at least"):
        hash_secret("short")


def test_hmac_signature_matches_standard_library() -> None:
    digest = hash_secret(SECRET)
    body = canonical_json({"event": "challenge.solved", "value": 7})
    expected = hmac.new(bytes.fromhex(digest), body.encode("utf-8"), hashlib.sha256).hexdigest()
    assert hmac_signature(digest, body) == expected
    assert len(hmac_signature(digest, body)) == 64
    assert SIGNATURE_ALGORITHM == "HMAC-SHA256"
    with pytest.raises(ValueError, match="configured secret"):
        hmac_signature("", body)


def test_payload_template_preserves_typed_placeholders() -> None:
    context = {
        "event": "challenge.solved",
        "payload": {"flag": "CTF{ok}", "points": 100},
        "integration": {"id": "int-1", "name": "Alerts"},
    }
    rendered = render_payload_template(
        {
            "event": "{{event}}",
            "label": "event={{event}} on {{integration.name}}",
            "data": "{{payload}}",
            "nested": {"id": "{{integration.id}}"},
        },
        context,
    )
    assert rendered["event"] == "challenge.solved"
    assert rendered["data"] == context["payload"]
    assert rendered["label"] == "event=challenge.solved on Alerts"
    assert rendered["nested"] == {"id": "int-1"}


def test_retry_schedule_uses_exponential_backoff_and_cap() -> None:
    assert retry_schedule(4) == (2.0, 4.0, 8.0, 16.0)
    assert retry_delay(9, cap=10.0) == 10.0
    assert retry_delay(1, base=0.5, multiplier=3.0) == 0.5
    with pytest.raises(ValueError, match="one-based"):
        retry_delay(0)


def test_delivery_stats_aggregates_counts_and_rates() -> None:
    now = utcnow()
    deliveries = [
        Delivery("d1", "i1", "e", "{}", DeliveryStatus.SUCCESS, 1, 200, now - timedelta(minutes=4)),
        Delivery("d2", "i1", "e", "{}", DeliveryStatus.SUCCESS, 2, 201, now - timedelta(minutes=3)),
        Delivery("d3", "i1", "e", "{}", DeliveryStatus.FAILED, 3, 500, now - timedelta(minutes=2)),
        Delivery("d4", "i1", "e", "{}", DeliveryStatus.PENDING, 4, None, None),
    ]
    stats = delivery_stats(deliveries)
    assert (stats.total, stats.pending, stats.success, stats.failed) == (4, 1, 2, 1)
    assert stats.success_rate == 0.5
    assert stats.failure_rate == 0.25
    assert stats.average_attempts == 2.5
    assert stats.last_sent_at == now - timedelta(minutes=2)
    assert stats.has_failures


def test_normalise_event_map_validates_both_sides() -> None:
    assert normalise_event_map({" Challenge.Solved ": "score.changed"}) == {
        "challenge.solved": "score.changed"
    }
    with pytest.raises(ValueError, match="allowlisted"):
        normalise_event_map({"challenge.solved": "not.real"})
    with pytest.raises(ValueError, match="at least one"):
        normalise_event_map({})


# ----------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------
def test_store_round_trip_and_filters(database: Database) -> None:
    integrations = IntegrationRepository()
    deliveries = DeliveryRepository()
    adapters = AdapterRepository()
    integration = _integration("Store hooks")
    deliveries_record = Delivery(
        id="del-store",
        integration_id=integration.id,
        event="challenge.solved",
        payload_json=encode_payload({"hello": "world"}),
        status=DeliveryStatus.PENDING,
    )
    adapter = Adapter("adt-store", "Store adapter", '{"challenge.solved":"score.changed"}')
    integrations.create(integration)
    deliveries.create(deliveries_record)
    adapters.create(adapter)

    assert integrations.get(integration.id) == integration
    assert integrations.get_by_name("store hooks") == integration
    assert integrations.list_supporting("challenge.solved") == [integration]
    assert integrations.list_supporting("score.changed") == []
    assert integrations.count_enabled() == 1
    assert deliveries.get("del-store") == deliveries_record
    assert deliveries.list_for_integration(integration.id) == [deliveries_record]
    assert deliveries.count_by_status()[DeliveryStatus.PENDING] == 1
    assert deliveries.total_attempts() == 0
    assert adapters.get("adt-store") == adapter
    assert adapters.count() == 1


def test_store_delete_removes_integration_history(database: Database) -> None:
    integrations = IntegrationRepository()
    deliveries = DeliveryRepository()
    integration = _integration("Doomed")
    integrations.create(integration)
    deliveries.create(
        Delivery("del-doom", integration.id, "challenge.solved", "{}", DeliveryStatus.FAILED, 2)
    )
    assert deliveries.delete_for_integration(integration.id) == 1
    assert integrations.delete(integration.id)
    assert deliveries.get("del-doom") is None


# ----------------------------------------------------------------------
# Service
# ----------------------------------------------------------------------
def test_create_integration_hashes_secret_and_normalises_fields(
    service: IntegrationService,
) -> None:
    integration = service.create_integration(
        name="  Alert hub  ",
        kind="WEBHOOK",
        endpoint_url="HTTP://Example.Com/hook",
        events=["challenge.solved", "challenge.solved", "score.changed"],
        secret=SECRET,
    )
    assert integration.name == "Alert hub"
    assert integration.kind is IntegrationKind.WEBHOOK
    assert integration.endpoint_url == "http://example.com/hook"
    assert integration.events == ("challenge.solved", "score.changed")
    assert integration.secret_hash == hash_secret(SECRET)
    assert integration.has_secret
    assert SECRET not in integration.masked_secret
    assert decode_events(integration.events_json) == integration.events


def test_create_integration_validation_and_conflicts(service: IntegrationService) -> None:
    service.create_integration(
        name="Taken",
        kind=IntegrationKind.WEBHOOK,
        endpoint_url="https://example.com/a",
        events=["challenge.solved"],
    )
    with pytest.raises(ConflictError, match="already exists"):
        service.create_integration(
            name="taken",
            kind=IntegrationKind.SLACK,
            endpoint_url="https://example.com/b",
            events=["challenge.solved"],
        )
    with pytest.raises(ValidationError, match="http or https"):
        service.create_integration(
            name="Bad url",
            kind=IntegrationKind.WEBHOOK,
            endpoint_url="ftp://example.com/a",
            events=["challenge.solved"],
        )
    with pytest.raises(ValidationError, match="Unknown event"):
        service.create_integration(
            name="Bad event",
            kind=IntegrationKind.WEBHOOK,
            endpoint_url="https://example.com/a",
            events=["not.real"],
        )


def test_update_integration_preserves_or_clears_secret(service: IntegrationService) -> None:
    integration = service.create_integration(
        name="Mutable",
        kind=IntegrationKind.WEBHOOK,
        endpoint_url="https://example.com/a",
        events=["challenge.solved"],
        secret=SECRET,
    )
    original_hash = integration.secret_hash
    kept = service.update_integration(integration.id, name="Renamed", enabled=False)
    assert kept.name == "Renamed"
    assert not kept.enabled
    assert kept.secret_hash == original_hash
    cleared = service.update_integration(integration.id, secret="", events=["score.changed"])
    assert cleared.secret_hash == ""
    assert cleared.events == ("score.changed",)
    with pytest.raises(NotFoundError, match="does not exist"):
        service.get_integration("int-missing")


def test_dispatch_records_only_matching_enabled_integrations(
    service: IntegrationService,
) -> None:
    service.create_integration(
        name="Solves",
        kind=IntegrationKind.WEBHOOK,
        endpoint_url="https://example.com/solves",
        events=["challenge.solved"],
    )
    service.create_integration(
        name="Scores",
        kind=IntegrationKind.CTF_PLATFORM,
        endpoint_url="https://example.com/scores",
        events=["score.changed"],
    )
    service.create_integration(
        name="Paused",
        kind=IntegrationKind.WEBHOOK,
        endpoint_url="https://example.com/paused",
        events=["challenge.solved"],
        enabled=False,
    )
    result = service.dispatch("challenge.solved", {"flag": "CTF{ok}", "points": 100})
    assert result.delivery_count == 1
    assert result.matched_integrations == 1
    delivery = result.deliveries[0]
    assert delivery.status is DeliveryStatus.PENDING
    assert delivery.payload["data"] == {"flag": "CTF{ok}", "points": 100}
    assert delivery.payload["event"] == "challenge.solved"
    assert delivery.signature == ""
    assert service.list_deliveries() == [delivery]


def test_dispatch_signs_payload_without_persisting_plaintext(
    service: IntegrationService,
) -> None:
    integration = service.create_integration(
        name="Signed",
        kind=IntegrationKind.WEBHOOK,
        endpoint_url="https://example.com/signed",
        events=["challenge.solved"],
        secret=SECRET,
    )
    result = service.dispatch(
        "challenge.solved", {"flag": "CTF{secret}"}, simulate_status="success"
    )
    delivery = result.deliveries[0]
    assert delivery.is_success
    assert delivery.response_code == 200
    assert len(delivery.signature) == 64
    assert SECRET not in delivery.payload_json
    unsigned = {
        k: v for k, v in delivery.payload.items() if k not in {"signature", "signature_algorithm"}
    }
    assert delivery.signature == hmac_signature(integration.secret_hash, canonical_json(unsigned))
    assert delivery.payload["signature_algorithm"] == SIGNATURE_ALGORITHM


def test_adapter_rewrites_events_for_subscribers(service: IntegrationService) -> None:
    service.create_adapter(
        name="Score bridge",
        event_map={"challenge.solved": "score.changed"},
    )
    service.create_integration(
        name="Score sink",
        kind=IntegrationKind.SLACK,
        endpoint_url="https://hooks.example.com/score",
        events=["score.changed"],
    )
    result = service.dispatch("challenge.solved", {"points": 100})
    assert result.mapped_events == ("score.changed",)
    assert result.delivery_count == 1
    assert result.deliveries[0].event == "score.changed"
    assert result.deliveries[0].payload["event"] == "challenge.solved"
    assert result.deliveries[0].payload["mapped_event"] == "score.changed"


def test_retry_and_simulation_lifecycle(service: IntegrationService) -> None:
    service.create_integration(
        name="Retries",
        kind=IntegrationKind.WEBHOOK,
        endpoint_url="https://example.com/retries",
        events=["challenge.solved"],
    )
    delivery = service.dispatch("challenge.solved", {}).deliveries[0]
    failed = service.simulate_delivery(delivery.id, DeliveryStatus.FAILED, response_code=503)
    assert failed.is_failed
    assert failed.attempts == 1
    assert failed.retry_after_seconds == 4.0
    retried = service.retry_delivery(delivery.id)
    assert retried.is_pending
    assert retried.attempts == 2
    succeeded = service.simulate_delivery(delivery.id, "success", response_code=204)
    assert succeeded.is_success
    assert succeeded.can_retry is False
    with pytest.raises(ConflictError, match="cannot be retried"):
        service.retry_delivery(delivery.id)
    with pytest.raises(ValidationError, match="Unknown delivery status"):
        service.simulate_delivery(delivery.id, "bogus")
    with pytest.raises(ValidationError, match="2xx"):
        service.simulate_delivery(delivery.id, "success", response_code=500)
    with pytest.raises(NotFoundError, match="Delivery"):
        service.get_delivery("del-unknown")


def test_service_stats_aggregate_all_ledger_outcomes(service: IntegrationService) -> None:
    service.create_integration(
        name="Stats",
        kind=IntegrationKind.WEBHOOK,
        endpoint_url="https://example.com/stats",
        events=["challenge.solved", "score.changed"],
    )
    service.create_adapter(name="Adapter", event_map={"challenge.solved": "score.changed"})
    first = service.dispatch("challenge.solved", {}, simulate_status="success").deliveries[0]
    service.dispatch("challenge.solved", {}, simulate_status="failed").deliveries[0]
    third = service.dispatch("score.changed", {}).deliveries[0]
    report = service.stats()
    assert report.total_integrations == 1
    assert report.enabled_integrations == 1
    assert report.total_adapters == 1
    assert (
        report.stats.total,
        report.stats.success,
        report.stats.failed,
        report.stats.pending,
    ) == (
        3,
        1,
        1,
        1,
    )
    assert report.stats.attempts == first.attempts + 1 + third.attempts
    assert report.by_event["score.changed"] == 3
    assert report.by_kind["webhook"] == 1
    assert report.success_rate == round(1 / 3, 16)


def test_delete_integration_removes_deliveries(service: IntegrationService) -> None:
    integration = service.create_integration(
        name="Temporary",
        kind=IntegrationKind.WEBHOOK,
        endpoint_url="https://example.com/temp",
        events=["challenge.solved"],
    )
    service.dispatch("challenge.solved", {})
    assert service.list_deliveries() != []
    service.delete_integration(integration.id)
    assert service.list_integrations() == []
    assert service.list_deliveries() == []
    with pytest.raises(NotFoundError, match="Adapter"):
        service.delete_adapter("adt-unknown")


# ----------------------------------------------------------------------
# HTTP API
# ----------------------------------------------------------------------
def test_api_integration_crud_lifecycle(client: TestClient) -> None:
    created = client.post(
        "/api/integrations",
        json={
            "name": "HTTP hooks",
            "kind": "webhook",
            "endpoint_url": "https://example.com/incoming",
            "events": ["challenge.solved"],
            "secret": SECRET,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "HTTP hooks"
    assert body["masked_secret"].startswith("whsec_")
    assert "secret_hash" not in body
    assert SECRET not in created.text
    integration_id = body["id"]

    assert client.get("/api/integrations").json()[0]["id"] == integration_id
    assert client.get(f"/api/integrations/{integration_id}").status_code == 200
    patched = client.patch(
        f"/api/integrations/{integration_id}",
        json={"enabled": False, "events": ["score.changed"]},
    )
    assert patched.status_code == 200
    assert patched.json()["enabled"] is False
    assert patched.json()["events"] == ["score.changed"]
    assert client.delete(f"/api/integrations/{integration_id}").status_code == 204
    assert client.patch(f"/api/integrations/{integration_id}", json={}).status_code == 404


def test_api_dispatch_deliveries_retry_and_stats(client: TestClient) -> None:
    integration = client.post(
        "/api/integrations",
        json={
            "name": "API hooks",
            "kind": "webhook",
            "endpoint_url": "https://example.com/api",
            "events": ["challenge.solved"],
            "secret": SECRET,
        },
    ).json()
    dispatched = client.post(
        "/api/integrations/dispatch",
        json={"event": "challenge.solved", "payload": {"challenge": "web-100"}},
    )
    assert dispatched.status_code == 200
    delivery = dispatched.json()[0]
    assert delivery["status"] == "pending"
    assert delivery["payload"]["data"] == {"challenge": "web-100"}
    assert len(delivery["signature"]) == 64

    deliveries = client.get("/api/integrations/deliveries").json()
    assert len(deliveries) == 1
    filtered = client.get(
        "/api/integrations/deliveries",
        params={"status": "failed", "integration_id": integration["id"]},
    ).json()
    assert filtered == []

    simulated = client.post(
        f"/api/integrations/deliveries/{delivery['id']}/simulate",
        json={"status": "failed", "response_code": 502},
    )
    assert simulated.status_code == 200
    assert simulated.json()["status"] == "failed"
    retried = client.post(f"/api/integrations/deliveries/{delivery['id']}/retry")
    assert retried.status_code == 200
    assert retried.json()["attempts"] == 2

    stats = client.get("/api/integrations/stats").json()
    assert stats["total_integrations"] == 1
    assert stats["total_deliveries"] == 1
    assert stats["pending_deliveries"] == 1
    assert stats["by_event"] == {"challenge.solved": 1}
    assert stats["by_kind"] == {"webhook": 1}


def test_api_adapters_and_mapping(client: TestClient) -> None:
    created = client.post(
        "/api/integrations/adapters",
        json={"name": "Bridge", "event_map": {"challenge.solved": "score.changed"}},
    )
    assert created.status_code == 201
    assert created.json()["mapping_count"] == 1
    assert client.get("/api/integrations/adapters").json()[0]["name"] == "Bridge"
    assert client.delete(f"/api/integrations/adapters/{created.json()['id']}").status_code == 204
    assert client.get("/api/integrations/adapters").json() == []


def test_api_domain_errors_have_stable_envelopes(client: TestClient) -> None:
    payload = {
        "name": "Validation",
        "kind": "webhook",
        "endpoint_url": "file:///etc/passwd",
        "events": ["challenge.solved"],
    }
    invalid = client.post("/api/integrations", json=payload)
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    valid = {**payload, "endpoint_url": "https://example.com/hook"}
    assert client.post("/api/integrations", json=valid).status_code == 201
    duplicate = client.post("/api/integrations", json={**valid, "name": "validation"})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"

    missing = client.patch("/api/integrations/int-unknown", json={"enabled": True})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_api_feature_coexists_with_seeded_data(client: TestClient, seeded: object) -> None:
    assert seeded is not None
    assert client.get("/api/integrations/stats").status_code == 200
    assert client.get("/api/teams").status_code == 200
