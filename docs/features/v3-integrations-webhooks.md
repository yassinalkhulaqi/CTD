# V3 — Webhooks and integrations

The integrations feature turns CTF activity into signed outbound events. It
lets an operator register webhook, Slack or CTF-platform endpoints, subscribe
each one to an allowlisted set of events, inspect every recorded delivery and
retry failures with exponential backoff. An adapter layer rewrites event names
before subscriptions are matched, so a single upstream signal can feed several
downstream systems with their own vocabularies.

Everything runs locally: dispatching an event records a delivery ledger entry
and computes an HMAC signature, but never opens a network connection. The
transport result can be simulated from the UI or the API.

## Domain model

| Entity | Fields | Notes |
| --- | --- | --- |
| `Integration` | `id`, `name`, `kind`, `endpoint_url`, `events_json`, `secret_hash`, `enabled`, `created_at` | Frozen, slotted dataclass. `events`, `host`, `scheme`, `masked_secret`, `is_active` are derived properties. |
| `Delivery` | `id`, `integration_id`, `event`, `payload_json`, `status`, `attempts`, `response_code`, `sent_at` | An append-mostly ledger row; retries update the same record in place. |
| `Adapter` | `id`, `name`, `event_map_json`, `created_at` | A stable, ordered `source → target` event map. |
| `DeliveryStats` | `total`, `pending`, `success`, `failed`, `attempts`, `last_sent_at` | Pure aggregate with `success_rate`, `failure_rate`, `average_attempts`. |

Enums: `IntegrationKind` (`webhook`, `slack`, `ctf_platform`) and
`DeliveryStatus` (`pending`, `success`, `failed`). Both are string enums so the
same values travel through JSON without translation.

### Rules

1. **Endpoint addresses** must use `http` or `https`, contain a host, contain
   no embedded credentials and no fragment. They are normalised to lower-case
   scheme/host and get a `/` path when none is supplied.
2. **Event subscriptions** are drawn from a twelve-item allowlist
   (`challenge.created`, `challenge.solved`, `event.started`, `event.ended`,
   `flag.submitted`, `hint.revealed`, `member.joined`, `score.changed`,
   `solve.created`, `submission.failed`, `team.updated`, `writeup.published`).
   Names are trimmed, lower-cased and de-duplicated; an empty or unknown list
   is rejected.
3. **Secrets** are accepted once on create or update, hashed with SHA-256 and
   only ever persisted as a 64-character hexadecimal digest. The plaintext is
   never stored, returned, logged or included in a payload. Updating an
   integration without a `secret` keeps the previous digest; sending an empty
   string clears it.
4. **Signatures** are HMAC-SHA256 over the canonical JSON of the rendered
   payload (`sort_keys`, compact separators). The stored digest is the HMAC
   key, so a signature can be produced later without recovering the plaintext.
   Signed deliveries carry `signature` and `signature_algorithm` fields.
5. **Templating** resolves `{{dotted.path}}` placeholders against a dispatch
   context. A value that is exactly one placeholder keeps its original type,
   so `"data": "{{payload}}"` stays a JSON object rather than becoming a
   string. Mixed strings substitute the string form of each placeholder.
6. **Adapters** map allowlisted source events to allowlisted target events.
   Dispatch computes all applicable targets and matches each integration
   against them; the delivered `event` is the mapped target while the payload
   keeps both `event` (original) and `mapped_event`.
7. **Retries** use `delay = min(base * multiplier ** (attempt - 1), cap)`
   with `base = 2s`, `multiplier = 2`, `cap = 300s`: 2s, 4s, 8s, 16s … A
   successful delivery cannot be retried; failed and pending ones can.
8. **Statistics** are derived from the ledger: totals per status, attempts,
   last send time, success/failure rates, per-event counts and per-kind counts.

Domain errors use the shared typed exceptions: `ValidationError` (422),
`NotFoundError` (404) and `ConflictError` (409). The application error handler
renders them with the standard `{"error": {...}}` envelope.

## Storage

Three feature-owned tables are created by `SCHEMA_SQL` through the dynamic
feature registry; no shared migration file is touched.

```sql
v3_integrations (id, name UNIQUE, kind, endpoint_url, events_json,
                 secret_hash, enabled, created_at)
v3_deliveries   (id, integration_id FK, event, payload_json, status,
                 attempts, response_code, sent_at)
v3_adapters     (id, name UNIQUE, event_map_json, created_at)
```

Indexes cover `v3_deliveries(integration_id)` and `v3_deliveries(status)`.
All queries are parameterised through `BaseRepository`. Deleting an
integration cascades to its deliveries.

## HTTP API

All routes are mounted under `/api/integrations` by
`register(app)`; the feature is discovered automatically.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/integrations` | List integrations in name order. |
| `POST` | `/api/integrations` | Create an integration; hashes the supplied secret. `201`. |
| `GET` | `/api/integrations/{id}` | Read one integration. |
| `PATCH` | `/api/integrations/{id}` | Update name, kind, URL, events, secret or enabled flag. |
| `DELETE` | `/api/integrations/{id}` | Delete the integration and its ledger. `204`. |
| `GET` | `/api/integrations/deliveries` | List deliveries; filters `status`, `integration_id`, `limit`. |
| `POST` | `/api/integrations/deliveries/{id}/retry` | Queue another attempt; increments `attempts`. |
| `POST` | `/api/integrations/deliveries/{id}/simulate` | Record a simulated `success`/`failed` result. |
| `GET` | `/api/integrations/adapters` | List event adapters. |
| `POST` | `/api/integrations/adapters` | Create an adapter from an event map. `201`. |
| `DELETE` | `/api/integrations/adapters/{id}` | Delete an adapter. `204`. |
| `GET` | `/api/integrations/stats` | Return the aggregate statistics payload. |
| `POST` | `/api/integrations/dispatch` | Record deliveries for matching integrations. |

Example create request:

```json
{
  "name": "Score alerts",
  "kind": "webhook",
  "endpoint_url": "https://hooks.example.com/ctf",
  "events": ["challenge.solved", "score.changed"],
  "secret": "a-very-secret-signing-key",
  "enabled": true
}
```

The response contains `masked_secret` such as `whsec_9f2c1a7b••••4d0e` and
never the plaintext or the raw digest of a short secret. Simulated results must
be coherent: `success` requires a 2xx code, `failed` requires 4xx/5xx.

## Frontend

The plugin registers at `/integrations` with id `integrations`, label
**Integrations** and group **Operations**. The screen is composed from six
components:

| Component | Responsibility |
| --- | --- |
| `IntegrationCard` | Name, transport badge, endpoint, subscribed events, enable switch, edit/test/delete actions. |
| `SecretField` | Password input with a keyboard operable reveal toggle and a one-way-digest explanation. |
| `EventSelector` | Accessible checkbox grid over the shared event allowlist. |
| `DeliveryInspector` | Status, target, attempts, response code, expandable payload, signature and retry/simulate controls. |
| `AdapterCard` | Readable `source → target` mapping list with a delete action. |
| `IntegrationStats` | Stat tiles, outcome bar and busiest-event badges. |

`hooks.ts` loads integrations, deliveries, adapters and statistics together,
tracks a per-action `busy` key, and refreshes after every mutation. `api.ts` is
the only module that knows the HTTP paths; `logic.ts` holds pure validation and
formatting helpers shared by the components and their tests.

### Walkthrough

1. Open **Integrations** from the Operations group in the module launcher.
   The four headline tiles show integration, delivery, success-rate and adapter
   totals; the outcome bar and busiest events sit underneath.
2. Choose **New integration**, enter a name and an `http(s)` URL, pick a
   transport, tick the events to subscribe to and optionally provide a signing
   secret. Inline field errors appear for invalid names, URLs, empty event
   lists and short secrets. Save to create the integration.
3. Each card has an enable switch. Toggling it patches the integration and
   refreshes the screen. **Send test** dispatches the first subscribed event
   with a sample payload and jumps to the delivery ledger.
4. Edit reuses the same form. The secret field starts empty with a note that
   leaving it blank preserves the stored digest; the masked value from the
   server is displayed read-only on the card.
5. In **Deliveries**, pick an event, edit the JSON payload and dispatch it.
   Expand a ledger row to read the signed payload and the next backoff. Retry
   a failed delivery or simulate a success/failure result.
6. In **Adapters**, create a JSON event map such as
   `{"challenge.solved": "score.changed"}`; cards show each mapping and a
   delete action.

### Accessibility and UX details

* All controls are native buttons, switches, checkboxes, inputs and selects,
  wrapped by the shared design-system primitives. Every icon-only control has
  an `aria-label`; the secret reveal button reports state with `aria-pressed`.
* Event groups use `fieldset`/`legend`; validation messages use `role="alert"`
  and are linked to their controls through `aria-describedby`.
* The delivery list exposes `role="list"`/`role="listitem"`, and each summary
  toggles `aria-expanded`/`aria-controls` for its payload panel.
* Loading, empty, error and success states are all rendered. `Spinner` carries
  an accessible label and `ErrorState` offers a retry action.
* CSS is confined to feature-local modules, uses theme custom properties and
  includes responsive and reduced-motion rules.

## Security notes

* Secrets enter the system only through create/update payloads. They are
  hashed immediately, never echoed in API responses and never written to log
  statements. The UI keeps them in a password input and shows only the digest
  fingerprint returned by the server.
* Endpoint validation rejects non-HTTP schemes and embedded credentials,
  reducing the risk of accidental `file://` or credential-bearing callbacks.
* Payloads are signed with HMAC-SHA256 using the stored digest as the key;
  signatures are deterministic and can be verified by the receiver with the
  same key material provisioned out of band.
* Dispatch is deliberately inert: no outbound request is made from the
  service, so tests and demos cannot leak data to third parties.

## Tests

* `tests/test_v3_integrations_webhooks.py` (29 tests) covers pure domain rules,
  store round-trips and deletes, service validation, hashing/signing, adapter
  mapping, retries, statistics, and the full HTTP API including error
  envelopes and coexistence with seeded data.
* Frontend tests (37 cases across four files) cover pure logic, every typed
  API call, all six components and rendered page interactions with mocked API
  responses: loading, toggle, form validation, dispatch and error retry.

Run them with:

```bash
python3 -m pytest -q
cd frontend && npm test
```

## File layout

```
src/ctf_team_dashboard/features/integrations_webhooks/
  __init__.py     SCHEMA_SQL + register(app)
  models.py       entities, enums, validation, signing, templating, backoff
  store.py        three BaseRepository implementations
  service.py      orchestration and typed domain errors
  schemas.py      Pydantic request/response models
  router.py       /api/integrations routes
  py.typed
frontend/src/features/integrations-webhooks/
  plugin.ts, types.ts, logic.ts, api.ts, hooks.ts
  IntegrationsPage.tsx, IntegrationsPage.module.css
  components/     six components with local CSS modules
tests/test_v3_integrations_webhooks.py
docs/features/v3-integrations-webhooks.md
```
