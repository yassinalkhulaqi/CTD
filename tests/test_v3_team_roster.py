"""Tests for the team roster feature: domain, store, service and API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from ctf_team_dashboard.features.team_roster.models import (
    Availability,
    Invitation,
    InvitationStatus,
    RosterAssignment,
    RosterMember,
    RosterPermission,
    RosterRole,
    bounded_utilisation,
    build_roster_stats,
    capacity_utilisation,
    generate_invite_token,
    initials_of,
    is_expired,
    is_valid_email,
    is_valid_handle,
    is_valid_timezone,
    remaining_capacity,
    total_assigned_hours,
)
from ctf_team_dashboard.features.team_roster.service import RosterService
from ctf_team_dashboard.features.team_roster.store import (
    InvitationRepository,
    RosterAssignmentRepository,
    RosterMemberRepository,
)

TEAM = "team-roster"


def member_record(
    member_id: str = "member-1",
    *,
    team_id: str = TEAM,
    handle: str = "nyx",
    role: RosterRole = RosterRole.MEMBER,
    availability: Availability = Availability.AVAILABLE,
    capacity: float = 8.0,
) -> RosterMember:
    """Build a roster member fixture for store-level tests."""
    return RosterMember(
        id=member_id,
        team_id=team_id,
        handle=handle,
        display_name=f"{handle.title()} Chandler",
        role=role,
        specialty="crypto",
        timezone="Europe/London",
        availability=availability,
        capacity_hours=capacity,
    )


def invitation_record(
    invitation_id: str = "invite-1",
    *,
    email: str = "new@example.com",
    role: RosterRole = RosterRole.ANALYST,
    status: InvitationStatus = InvitationStatus.PENDING,
    expires_at: datetime | None = None,
) -> Invitation:
    """Build an invitation fixture with an explicit deadline."""
    moment = datetime.now(timezone.utc)
    return Invitation(
        id=invitation_id,
        team_id=TEAM,
        email=email,
        role=role,
        token=f"inv_token_{invitation_id}",
        status=status,
        created_at=moment,
        expires_at=expires_at or moment + timedelta(days=3),
    )


def assignment_record(assignment_id: str, member_id: str, hours: float = 2.0) -> RosterAssignment:
    """Build an assignment fixture for store-level tests."""
    return RosterAssignment(
        id=assignment_id,
        member_id=member_id,
        challenge_id=f"challenge-{assignment_id}",
        hours=hours,
    )


# ----------------------------------------------------------------------
# Pure domain helpers
# ----------------------------------------------------------------------
def test_initials_are_derived_from_words_and_handles() -> None:
    """Initials use the first two words or the first two characters."""
    assert initials_of("Nyx Chandler") == "NC"
    assert initials_of("nyx") == "NY"
    assert initials_of("  ") == "??"
    assert member_record().initials == "NC"


def test_role_rank_and_seniority_comparison() -> None:
    """Higher roles satisfy lower roles and inherit their permissions."""
    assert RosterRole.OBSERVER.rank == 0
    assert RosterRole.LEAD.rank == 3
    assert RosterRole.LEAD.satisfies(RosterRole.MEMBER)
    assert not RosterRole.ANALYST.satisfies(RosterRole.MEMBER)
    assert RosterRole.LEAD.permits(RosterPermission.MANAGE_ROSTER)
    assert not RosterRole.MEMBER.permits(RosterPermission.MANAGE_ROSTER)
    assert RosterRole.MEMBER.permits(RosterPermission.INVITE_MEMBERS)
    assert member_record(role=RosterRole.LEAD).satisfies(RosterRole.ANALYST)


def test_availability_labels_and_work_acceptance() -> None:
    """Only available members accept new work."""
    assert Availability.AVAILABLE.label == "Available"
    assert Availability.BUSY.tone == "warning"
    assert Availability.AVAILABLE.accepts_work
    assert not Availability.BUSY.accepts_work
    assert not Availability.OFFLINE.accepts_work
    assert member_record().accepts_work
    assert not member_record(availability=Availability.BUSY).accepts_work


def test_invitation_state_transitions_are_validated() -> None:
    """Accepted and revoked copies keep the original immutable."""
    invitation = invitation_record()
    assert invitation.is_open
    assert invitation.masked_token.startswith("inv_token_")
    accepted = invitation.accepted()
    assert accepted.status is InvitationStatus.ACCEPTED
    assert invitation.status is InvitationStatus.PENDING
    assert not accepted.is_open
    with pytest.raises(ValueError):
        accepted.revoked()
    revoked = invitation.revoked()
    assert revoked.status is InvitationStatus.REVOKED
    assert revoked.status.tone == "danger"


def test_invitation_expiry_detection_and_effective_status() -> None:
    """Pending invitations past their deadline read as expired."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    invitation = invitation_record(expires_at=past)
    assert is_expired(invitation.expires_at)
    assert invitation.is_expired()
    assert invitation.effective_status() is InvitationStatus.EXPIRED
    assert not invitation.can_be_accepted()
    with pytest.raises(ValueError):
        invitation.accepted()
    assert invitation.expired().status is InvitationStatus.EXPIRED
    accepted = invitation_record().accepted()
    assert accepted.effective_status() is InvitationStatus.ACCEPTED


def test_capacity_utilisation_helpers() -> None:
    """Utilisation is clamped for display but exact in arithmetic."""
    assert capacity_utilisation(4, 8) == 0.5
    assert capacity_utilisation(12, 8) == 1.5
    assert capacity_utilisation(3, 0) == 0.0
    assert bounded_utilisation(12, 8) == 1.0
    assert bounded_utilisation(-2, 8) == 0.0
    assert remaining_capacity(8, [assignment_record("a1", "member-1", 3)]) == 5.0
    assert total_assigned_hours([assignment_record("a1", "member-1", 3)]) == 3.0


def test_generated_tokens_are_unique_and_validated_inputs_detected() -> None:
    """Tokens are namespaced and validation helpers reject malformed values."""
    tokens = {generate_invite_token() for _ in range(20)}
    assert len(tokens) == 20
    assert all(token.startswith("inv_") for token in tokens)
    assert is_valid_handle("nyx_1")
    assert not is_valid_handle("x")
    assert not is_valid_handle("bad handle")
    assert is_valid_email("A.User@Example.COM")
    assert not is_valid_email("not-an-email")
    assert is_valid_timezone("Europe/London")
    assert is_valid_timezone("UTC")
    assert not is_valid_timezone("Mars/Olympus!")


def test_build_roster_stats_groups_members_and_invites() -> None:
    """Aggregation counts roles, availability and pending invitations."""
    members = [
        member_record("m1", role=RosterRole.LEAD),
        member_record("m2", handle="ax", role=RosterRole.ANALYST),
        member_record("m3", handle="ob", role=RosterRole.OBSERVER, availability=Availability.BUSY),
    ]
    assignments = [assignment_record("a1", "m1", 4.0)]
    invitations = [
        invitation_record("i1"),
        invitation_record("i2", status=InvitationStatus.REVOKED),
    ]
    stats = build_roster_stats(members, invitations, assignments, team_id=TEAM)
    assert stats.total_members == 3
    assert stats.lead_count == 1
    assert stats.available_count == 2
    assert stats.count_for(RosterRole.ANALYST) == 1
    assert stats.availability_count(Availability.BUSY) == 1
    assert stats.pending_invitations == 1
    assert stats.assigned_hours == 4.0
    assert stats.remaining_hours == 20.0
    assert round(stats.utilisation, 3) == round(4 / 24, 3)
    assert stats.role_share(RosterRole.LEAD) == pytest.approx(1 / 3)


# ----------------------------------------------------------------------
# Store layer
# ----------------------------------------------------------------------
def test_member_store_crud_and_filtered_listing(database: Database) -> None:
    """The member repository persists and filters roster records."""
    store = RosterMemberRepository(database)
    lead = member_record("m1", role=RosterRole.LEAD)
    busy = member_record("m2", handle="busy", availability=Availability.BUSY)
    other = member_record("m3", handle="other", team_id="team-other")
    for record in (lead, busy, other):
        store.create(record)
    assert store.get("m1") == lead
    assert {item.id for item in store.list_all(team_id=TEAM)} == {"m1", "m2"}
    assert [item.id for item in store.list_all(role=RosterRole.LEAD)] == ["m1"]
    assert [item.id for item in store.list_all(availability=Availability.BUSY)] == ["m2"]
    store.set_availability("m1", Availability.OFFLINE)
    assert store.get("m1") is not None
    assert store.get("m1").availability is Availability.OFFLINE  # type: ignore[union-attr]
    store.set_role("m1", RosterRole.ANALYST)
    assert store.get("m1") is not None
    assert store.get("m1").role is RosterRole.ANALYST  # type: ignore[union-attr]
    assert store.count_for_team(TEAM) == 2
    assert store.delete("m2")
    assert store.get("m2") is None
    assert store.delete_by_team("team-other") == 1


def test_invitation_store_crud_and_expiry_bulk_update(database: Database) -> None:
    """The invitation repository supports lookup, status and expiry filters."""
    store = InvitationRepository(database)
    pending = invitation_record("i1")
    accepted = invitation_record("i2", email="done@example.com", status=InvitationStatus.ACCEPTED)
    for record in (pending, accepted):
        store.create(record)
    assert store.get("i1") == pending
    assert store.get_by_token("inv_token_i1") == pending
    assert [item.id for item in store.pending_for_email(TEAM, pending.email)] == ["i1"]
    assert {item.id for item in store.list_all(status=InvitationStatus.ACCEPTED)} == {"i2"}
    assert store.count_pending(TEAM) == 1
    assert store.expire_before(datetime.now(timezone.utc) + timedelta(days=10)) == 1
    assert store.get("i1") is not None
    assert store.get("i1").status is InvitationStatus.EXPIRED  # type: ignore[union-attr]
    assert store.set_status("i2", InvitationStatus.REVOKED)
    assert store.delete("i1")
    assert store.delete_by_team(TEAM) == 1


def test_assignment_store_crud_and_aggregation(database: Database) -> None:
    """The assignment repository filters and sums reserved hours."""
    store = RosterAssignmentRepository(database)
    first = assignment_record("a1", "m1", 2.5)
    second = assignment_record("a2", "m1", 1.5)
    third = assignment_record("a3", "m2", 4.0)
    for record in (first, second, third):
        store.create(record)
    assert store.get("a1") == first
    assert store.get_for_member_challenge("m1", "challenge-a1") == first
    assert len(store.list_all(member_id="m1")) == 2
    assert len(store.list_all(challenge_id="challenge-a3")) == 1
    assert store.sum_hours("m1") == 4.0
    assert store.count_for_member("m2") == 1
    assert store.update_hours("a1", 3.0)
    assert store.sum_hours("m1") == 4.5
    assert store.delete("a2")
    assert store.delete_by_member("m1") == 1
    assert store.delete_by_challenge("challenge-a3") == 1
    assert store.count() == 0


# ----------------------------------------------------------------------
# Service: members and assignments
# ----------------------------------------------------------------------
def test_service_adds_and_updates_members(database: Database) -> None:
    """Adding and updating members normalises and validates their fields."""
    service = RosterService(database)
    member = service.add_member(
        team_id=TEAM,
        handle="  Nyx_1 ",
        display_name="Nyx Chandler",
        role=RosterRole.LEAD,
        specialty="crypto",
        timezone="Europe/London",
        capacity_hours=6,
    )
    assert member.handle == "nyx_1"
    assert member.initials == "NC"
    assert member.capacity_hours == 6.0
    updated = service.update_member(
        member.id, display_name="Nyx C.", availability=Availability.BUSY
    )
    assert updated.display_name == "Nyx C."
    assert updated.availability is Availability.BUSY
    assert service.get_member(member.id).display_name == "Nyx C."
    with pytest.raises(NotFoundError):
        service.get_member("missing")


def test_service_rejects_invalid_and_duplicate_members(database: Database) -> None:
    """Validation and conflict errors are raised for bad member input."""
    service = RosterService(database)
    service.add_member(team_id=TEAM, handle="nyx")
    with pytest.raises(ConflictError):
        service.add_member(team_id=TEAM, handle="NYX")
    with pytest.raises(ValidationError):
        service.add_member(team_id=TEAM, handle="x")
    with pytest.raises(ValidationError):
        service.add_member(team_id=TEAM, handle="other", timezone="Mars/Base")
    with pytest.raises(ValidationError):
        service.add_member(team_id=TEAM, handle="other", capacity_hours=100)
    with pytest.raises(ValidationError):
        service.add_member(team_id="   ", handle="other")


def test_service_role_change_guards_last_lead(database: Database) -> None:
    """Only an authorised actor may change roles and a lead must remain."""
    service = RosterService(database)
    lead = service.add_member(team_id=TEAM, handle="lead", role=RosterRole.LEAD)
    member = service.add_member(team_id=TEAM, handle="member")
    with pytest.raises(ConflictError):
        service.change_role(lead.id, RosterRole.MEMBER)
    service.add_member(team_id=TEAM, handle="lead2", role=RosterRole.LEAD)
    changed = service.change_role(
        lead.id,
        RosterRole.MEMBER,
        actor=member_record("actor", role=RosterRole.LEAD),
    )
    assert changed.role is RosterRole.MEMBER
    assert service.get_member(lead.id).role is RosterRole.MEMBER
    with pytest.raises(PermissionDeniedError):
        service.change_role(
            member.id,
            RosterRole.LEAD,
            actor=member_record("actor", role=RosterRole.OBSERVER),
        )


def test_service_capacity_checks_and_assignment_lifecycle(database: Database) -> None:
    """Assignments respect remaining capacity and uniqueness constraints."""
    service = RosterService(database)
    member = service.add_member(team_id=TEAM, handle="nyx", capacity_hours=6)
    first = service.assign_hours(member_id=member.id, challenge_id="challenge-1", hours=4)
    assert first.hours == 4.0
    assert service.assigned_hours(member.id) == 4.0
    assert service.utilisation_for(member.id) == pytest.approx(4 / 6)
    with pytest.raises(ConflictError):
        service.assign_hours(member_id=member.id, challenge_id="challenge-2", hours=3)
    with pytest.raises(ConflictError):
        service.assign_hours(member_id=member.id, challenge_id="challenge-1", hours=1)
    with pytest.raises(ValidationError):
        service.assign_hours(member_id=member.id, challenge_id="challenge-2", hours=0)
    with pytest.raises(ValidationError):
        service.assign_hours(member_id=member.id, challenge_id="", hours=1)
    updated = service.update_assignment_hours(first.id, 2)
    assert updated.hours == 2.0
    assert service.list_assignments(member_id=member.id)[0].hours == 2.0
    service.remove_assignment(first.id)
    assert service.list_assignments() == []


def test_service_prevents_reducing_capacity_below_assignments(database: Database) -> None:
    """Capacity cannot drop below the hours already reserved."""
    service = RosterService(database)
    member = service.add_member(team_id=TEAM, handle="nyx", capacity_hours=8)
    service.assign_hours(member_id=member.id, challenge_id="challenge-1", hours=5)
    with pytest.raises(ConflictError):
        service.update_member(member.id, capacity_hours=4)
    with pytest.raises(NotFoundError):
        service.get_assignment("missing")


def test_service_remove_member_cleans_assignments(database: Database) -> None:
    """Removing a member releases all of their assignments."""
    service = RosterService(database)
    member = service.add_member(team_id=TEAM, handle="nyx")
    service.assign_hours(member_id=member.id, challenge_id="challenge-1", hours=2)
    service.remove_member(member.id)
    assert service.list_members() == []
    assert service.list_assignments() == []


# ----------------------------------------------------------------------
# Service: invitations and statistics
# ----------------------------------------------------------------------
def test_service_invitation_lifecycle(database: Database) -> None:
    """Creating, accepting and revoking invitations follows the state machine."""
    service = RosterService(database)
    invitation = service.create_invitation(
        team_id=TEAM, email="Alice@Example.com", role=RosterRole.ANALYST
    )
    assert invitation.email == "alice@example.com"
    assert invitation.status is InvitationStatus.PENDING
    assert invitation.role is RosterRole.ANALYST
    with pytest.raises(ConflictError):
        service.create_invitation(team_id=TEAM, email="alice@example.com")
    with pytest.raises(ValidationError):
        service.create_invitation(team_id=TEAM, email="bad-address")
    member, accepted = service.accept_invitation(invitation.id, handle="alice")
    assert accepted.status is InvitationStatus.ACCEPTED
    assert member.handle == "alice"
    assert member.role is RosterRole.ANALYST
    assert member.availability is Availability.AVAILABLE
    with pytest.raises(ConflictError):
        service.accept_invitation(invitation.id, handle="alice2")
    with pytest.raises(ConflictError):
        service.revoke_invitation(invitation.id)


def test_service_revokes_and_expires_invitations(database: Database) -> None:
    """Revocation is final and overdue invitations become expired."""
    service = RosterService(database)
    invitation = service.create_invitation(team_id=TEAM, email="bob@example.com")
    revoked = service.revoke_invitation(invitation.id)
    assert revoked.status is InvitationStatus.REVOKED
    with pytest.raises(ConflictError):
        service.accept_invitation(invitation.id, handle="bob")
    stale = service.create_invitation(team_id=TEAM, email="late@example.com")
    marked = service.expire_pending_invitations(datetime.now(timezone.utc) + timedelta(days=30))
    assert marked >= 1
    assert service.get_invitation(stale.id).status is InvitationStatus.EXPIRED
    with pytest.raises(ConflictError):
        service.accept_invitation(stale.id, handle="late")
    with pytest.raises(ConflictError):
        service.revoke_invitation(stale.id)


def test_service_accepts_invitation_by_token_and_rejects_duplicate_handle(
    database: Database,
) -> None:
    """Token acceptance materialises a member and checks handle uniqueness."""
    service = RosterService(database)
    service.add_member(team_id=TEAM, handle="taken")
    invitation = service.create_invitation(team_id=TEAM, email="carol@example.com")
    with pytest.raises(ConflictError):
        service.accept_invitation_by_token(invitation.token, handle="taken")
    member, _ = service.accept_invitation_by_token(
        invitation.token, handle="carol", display_name="Carol D."
    )
    assert member.display_name == "Carol D."
    with pytest.raises(NotFoundError):
        service.get_invitation_by_token("inv_missing")


def test_service_statistics_group_by_role_and_availability(database: Database) -> None:
    """Service statistics reflect members, assignments and pending invites."""
    service = RosterService(database)
    lead = service.add_member(
        team_id=TEAM, handle="lead", role=RosterRole.LEAD, availability=Availability.AVAILABLE
    )
    service.add_member(
        team_id=TEAM, handle="analyst", role=RosterRole.ANALYST, availability=Availability.AVAILABLE
    )
    service.add_member(
        team_id=TEAM, handle="busy", role=RosterRole.OBSERVER, availability=Availability.BUSY
    )
    service.create_invitation(team_id=TEAM, email="pending@example.com")
    service.assign_hours(member_id=lead.id, challenge_id="challenge-1", hours=3)
    stats = service.stats(TEAM)
    assert stats.total_members == 3
    assert stats.lead_count == 1
    assert stats.available_count == 2
    assert stats.availability_count(Availability.BUSY) == 1
    assert stats.pending_invitations == 1
    assert stats.assigned_hours == 3.0
    assert stats.total_capacity_hours == 24.0
    assert stats.utilisation_percent == 12.5
    assert service.busiest_members()[0][0].id == lead.id


# ----------------------------------------------------------------------
# Router layer
# ----------------------------------------------------------------------
def test_router_member_endpoints(client: TestClient, database: Database) -> None:
    """The member CRUD endpoints expose the roster with derived fields."""
    created = client.post(
        "/api/roster",
        json={
            "team_id": TEAM,
            "handle": "nyx",
            "display_name": "Nyx Chandler",
            "role": "lead",
            "availability": "available",
            "capacity_hours": 6,
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["initials"] == "NC"
    assert payload["rank"] == 3
    assert payload["availability_label"] == "Available"
    member_id = payload["id"]
    assert client.get("/api/roster", params={"team_id": TEAM}).json()[0]["id"] == member_id
    assert client.get("/api/roster", params={"role": "observer"}).json() == []
    assert client.get("/api/roster", params={"availability": "busy"}).json() == []
    patched = client.patch(f"/api/roster/{member_id}", json={"display_name": "Nyx C."})
    assert patched.status_code == 200
    assert patched.json()["display_name"] == "Nyx C."
    client.post("/api/roster", json={"team_id": TEAM, "handle": "second-lead", "role": "lead"})
    role = client.patch(f"/api/roster/{member_id}/role", json={"role": "member"})
    assert role.status_code == 200
    assert role.json()["role"] == "member"
    assert client.delete(f"/api/roster/{member_id}").status_code == 204
    assert client.get(f"/api/roster/{member_id}").status_code == 404


def test_router_error_envelopes_and_validation(client: TestClient) -> None:
    """Domain errors map to stable status codes and envelopes."""
    missing = client.get("/api/roster/nope")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    invalid = client.post("/api/roster", json={"team_id": TEAM, "handle": "x"})
    assert invalid.status_code == 422
    duplicate = client.post("/api/roster", json={"team_id": TEAM, "handle": "dup"})
    assert duplicate.status_code == 201
    conflict = client.post("/api/roster", json={"team_id": TEAM, "handle": "DUP"})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


def test_router_invitation_endpoints(client: TestClient) -> None:
    """Invitations can be created, listed, accepted and revoked over HTTP."""
    created = client.post(
        "/api/roster/invitations",
        json={"team_id": TEAM, "email": "dave@example.com", "role": "analyst"},
    )
    assert created.status_code == 201
    invitation = created.json()
    assert invitation["status"] == "pending"
    assert invitation["masked_token"].startswith(invitation["token"][:12])
    listed = client.get("/api/roster/invitations", params={"team_id": TEAM})
    assert len(listed.json()) == 1
    accepted = client.post(
        f"/api/roster/invitations/{invitation['id']}/accept",
        json={"handle": "dave", "display_name": "Dave"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["invitation"]["status"] == "accepted"
    assert accepted.json()["member"]["handle"] == "dave"
    filtered = client.get("/api/roster/invitations", params={"status_filter": "accepted"})
    assert len(filtered.json()) == 1
    revoked = client.post(
        "/api/roster/invitations", json={"team_id": TEAM, "email": "eve@example.com"}
    ).json()
    assert client.post(f"/api/roster/invitations/{revoked['id']}/revoke").status_code == 200
    assert client.post("/api/roster/invitations/expire").status_code == 200


def test_router_assignment_and_stats_endpoints(client: TestClient) -> None:
    """Assignments enforce capacity and statistics aggregate the roster."""
    member = client.post(
        "/api/roster",
        json={"team_id": TEAM, "handle": "nyx", "capacity_hours": 4},
    ).json()
    assigned = client.post(
        "/api/roster/assignments",
        json={"member_id": member["id"], "challenge_id": "challenge-1", "hours": 3},
    )
    assert assigned.status_code == 201
    conflict = client.post(
        "/api/roster/assignments",
        json={"member_id": member["id"], "challenge_id": "challenge-2", "hours": 2},
    )
    assert conflict.status_code == 409
    listed = client.get("/api/roster/assignments", params={"member_id": member["id"]})
    assert len(listed.json()) == 1
    patched = client.patch(f"/api/roster/assignments/{assigned.json()['id']}", json={"hours": 1})
    assert patched.json()["hours"] == 1.0
    stats = client.get("/api/roster/stats", params={"team_id": TEAM})
    assert stats.status_code == 200
    payload = stats.json()
    assert payload["total_members"] == 1
    assert payload["assigned_hours"] == 1.0
    assert payload["by_role"]["member"] == 1
    assert payload["by_availability"]["offline"] == 1
    assert client.delete(f"/api/roster/assignments/{assigned.json()['id']}").status_code == 204


def test_feature_registers_router_and_schema(database: Database) -> None:
    """The dynamic registry installs the feature tables and routes."""
    tables = database.table_names()
    assert "v3_roster_members" in tables
    assert "v3_roster_invitations" in tables
    assert "v3_roster_assignments" in tables
    from ctf_team_dashboard.features import available_feature_names

    assert "team_roster" in available_feature_names()
