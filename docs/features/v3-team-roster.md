# Team roster, roles and invitations (V3-06)

## Overview

The team roster feature turns a list of handles into an operating surface for
people management. It models the people who work a CTF, the roles they hold,
their availability and hour budget, the work reserved for them, and the
invitations that bring new teammates in. The backend is a self-contained
feature package (`ctf_team_dashboard.features.team_roster`); the frontend is a
discovered plugin mounted at `/roster` in the `Operations` group. Neither the
shared registries nor any foundation file was edited.

The feature is split into five backend modules:

| Module | Responsibility |
| --- | --- |
| `models.py` | Frozen slotted entities, enums and pure calculation helpers |
| `store.py` | Parameterised SQLite CRUD and filtered listing |
| `service.py` | Validation, orchestration, capacity rules and aggregation |
| `schemas.py` | Typed Pydantic request and response models |
| `router.py` | The `/api/roster` HTTP surface |

Three tables are created by `SCHEMA_SQL` and migrated automatically by
`Database.migrate()`: `v3_roster_members`, `v3_roster_invitations` and
`v3_roster_assignments`. Unique constraints protect team handles, invitation
tokens and the `(member_id, challenge_id)` assignment pair.

## Domain model

### RosterMember

A member carries an id, team id, handle, display name, role, specialty,
timezone, availability, capacity (in hours) and a join timestamp. Entities are
frozen dataclasses, so transitions such as `with_role`, `with_availability` and
`with_details` return a new record rather than mutating state.

Derived values:

- `initials` — up to two uppercase letters from the display name, falling back
  to the handle.
- `rank` — the seniority rank of the role.
- `accepts_work` — true only when availability is `available` and capacity is
  positive.
- `assigned_hours`, `remaining_hours`, `utilisation` — computed from a supplied
  iterable of assignments, keeping the entity independent of the database.

Handles are normalised to lowercase and must be 2–32 characters starting with
a letter or a digit. Timezones must resolve to a real IANA zone. Capacity must
be between 0 and 80 hours. Handles are unique inside a team.

### Roles and permissions

Roles are ordered `observer` (0), `analyst` (1), `member` (2), `lead` (3).
A higher rank inherits the capabilities of lower ranks:

| Permission | observer | analyst | member | lead |
| --- | --- | --- | --- | --- |
| `roster:view` | ✓ | ✓ | ✓ | ✓ |
| `roster:work` | ✓ | ✓ | ✓ | ✓ |
| `roster:contacts` | — | ✓ | ✓ | ✓ |
| `roster:assign` | — | — | ✓ | ✓ |
| `roster:invite` | — | — | ✓ | ✓ |
| `roster:roles` | — | — | — | ✓ |
| `roster:manage` | — | — | — | ✓ |

`RosterRole.satisfies(required)` performs a rank comparison and
`RosterMember.permits(permission)` performs a capability lookup. The same role
and permission tables are mirrored in the frontend `domain.ts` so chips,
menus and disabled states agree with the server. A team must always retain at
least one lead: demoting or removing the last lead is rejected with a conflict.

### Availability

`available`, `busy` and `offline` each expose a display label, a semantic tone
for the UI and an `accepts_work` flag. Availability changes are explicit
operations, not inferred from presence, so an analyst can advertise focus time
without disconnecting.

### Capacity and assignments

`RosterAssignment` reserves a positive number of hours against a challenge for
one member. The service rejects:

- zero, negative or greater-than-24-hour reservations;
- a second reservation of the same challenge for the same member;
- any reservation that would push total assigned hours above the member's
  capacity;
- a capacity reduction below the hours already assigned.

`capacity_utilisation` returns the exact ratio (which may exceed 1), while
`bounded_utilisation` clamps it into `0..1` for progress bars.
`RosterStats` aggregates total capacity, assigned hours, remaining hours,
utilisation, assignment count and pending invitations, grouped by role and by
availability.

### Invitation lifecycle

```
pending ──accept──▶ accepted
   ├──revoke─────▶ revoked
   └──deadline───▶ expired
```

Invitation tokens are generated with `secrets.token_urlsafe(24)` and namespaced
with `inv_`. Invitations last seven days by default; callers may supply an
explicit future deadline. Duplicate pending invitations for the same email and
team are rejected, while accepted, revoked and expired invitations do not
block a fresh invite. `effective_status()` applies deadline expiry to pending
invitations without requiring a write; `expire_pending_invitations()` persists
the transition in bulk. Accepting validates status and deadline, then creates
the roster member with the invited role and `available` availability in the
same service operation. Revoking and accepting terminal invitations raise a
conflict.

## HTTP API

All paths are prefixed with `/api/roster`. Mutations additionally require the
shared `MEMBER_MANAGE` permission; the test configuration runs in open mode so
fixtures can exercise them without credentials.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/roster` | List members; filters `team_id`, `role`, `availability` |
| `POST` | `/api/roster` | Add a member (201) |
| `GET` | `/api/roster/{id}` | Fetch one member |
| `PATCH` | `/api/roster/{id}` | Update handle, name, specialty, timezone, availability or capacity |
| `DELETE` | `/api/roster/{id}` | Remove a member and their assignments (204) |
| `PATCH` | `/api/roster/{id}/role` | Change role, with last-lead guard |
| `PUT` | `/api/roster/{id}/availability` | Publish availability |
| `GET` | `/api/roster/invitations` | List invitations; filters `team_id`, `status_filter` |
| `POST` | `/api/roster/invitations` | Create an invitation (201) |
| `POST` | `/api/roster/invitations/{id}/accept` | Accept and create the member |
| `POST` | `/api/roster/invitations/{id}/revoke` | Revoke a pending invitation |
| `POST` | `/api/roster/invitations/expire` | Bulk-expire overdue invitations |
| `GET` | `/api/roster/assignments` | List assignments; filters `member_id`, `challenge_id` |
| `POST` | `/api/roster/assignments` | Reserve hours (201) |
| `PATCH` | `/api/roster/assignments/{id}` | Change reserved hours |
| `DELETE` | `/api/roster/assignments/{id}` | Release an assignment (204) |
| `GET` | `/api/roster/stats` | Aggregated statistics; optional `team_id` |

Static paths are registered before `/{member_id}` so filter routes are never
captured as member identifiers. Errors use the shared envelope: validation
failures return 422, unknown identifiers 404, and rule conflicts 409.

## Frontend walkthrough

The plugin declares `id: "roster"`, `path: "/roster"`, label `Roster` and group
`Operations`. The foundation discovers it through `import.meta.glob`, mounts
the route and adds it to the module launcher.

`RosterPage` composes the screen:

1. **Header** — refresh and invite actions.
2. **Statistics** — five stat tiles (members, leads, available, pending
   invites, utilisation) plus role and availability breakdown bars.
3. **Layout switch** — table or cards, implemented with `SegmentedControl`.
4. **Roster table** — sortable columns, team/role/availability filters and a
   search box. Each row shows a `RoleChip`, an availability indicator, a
   `CapacityBar`, specialty/timezone and an inline role `<select>`.
5. **Member cards** — alternative layout with avatar, role menu (`Popover` +
   `Menu`), availability dot and capacity meter.
6. **Invitations panel** — status badges, masked token, team, an inline handle
   field for accepting and a revoke action.
7. **Assignments panel** — form to reserve hours with client-side capacity
   validation, plus a list with release actions.

`InviteDialog` is a modal with email, team and role fields. It validates the
email before submitting, displays API errors inline and resets when reopened.
`rosterApi` wraps the shared client (`get`, `post`, `patch`, `del`) and
`useRoster` loads all four resources in parallel, refreshes after every
successful mutation, exposes a busy flag and surfaces errors through
`ErrorState`.

Components and styling are local to the feature: `RoleChip`, `CapacityBar`,
`MemberCard`, `RosterTable`, `InviteDialog` and `RosterStatsView` each have a
CSS module. No shared stylesheet was modified.

## Tests

`tests/test_v3_team_roster.py` contains 26 tests covering:

- pure helpers: initials, role rank and permissions, availability, capacity
  arithmetic, token uniqueness, validation and expiry;
- Immutability and state-machine transitions of `Invitation`;
- store CRUD, filtered listing, bulk expiry and hour totals;
- service validation, duplicate handles, last-lead guards, capacity checks,
  invitation lifecycle, duplicate pending invites and statistics;
- router success paths, error envelopes, validation failures and dynamic
  registration of tables and routes.

Backend tests require `PYTHONPATH=src` because the editable installation points
at the main checkout rather than the worktree.

Frontend tests are colocated:

- `domain.test.ts` — metadata, formatting, filtering, sorting, deadlines and
  aggregation;
- `api.test.ts` — URLs, query parameter names, verbs and bodies of every
  adapter function;
- `components/RosterTable.test.tsx` — rendering, role change, removal, filters,
  sorting, loading and empty states;
- `components/InviteDialog.test.tsx` — validation, submission, cancellation and
  API errors;
- `components/MemberCard.test.tsx` — identity, role menu and removal;
- `components/RosterStats.test.tsx` — tiles and breakdown bars;
- `plugin.test.ts` — plugin metadata and dynamic discovery.

## Accessibility notes

- Role chips carry an explicit `aria-label` and a title with rank information.
- Availability dots are paired with text labels; colour is never the only
  signal.
- `CapacityBar` is a real `progressbar` with `aria-valuenow`, `aria-valuenow`
  text and a human readable `aria-valuetext`.
- Table headers use `aria-sort`, controls use visible or visually hidden
  labels, and the scroll container is keyboard focusable.
- The invite modal traps focus, closes on Escape and restores focus on close.
- Status colours are semantic tokens from `index.css`, so both light and dark
  themes keep sufficient contrast.
- Hover transitions are short and are removed under
  `prefers-reduced-motion: reduce`.
