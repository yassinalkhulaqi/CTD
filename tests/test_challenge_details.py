"""Tests for the challenge notes, timeline and flag submission."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.errors import NotFoundError, PermissionDeniedError, ValidationError
from ctf_team_dashboard.repositories import Repositories
from ctf_team_dashboard.security.flags import (
    FlagFormatError,
    is_valid_flag,
    mask_flag,
    normalise_flag,
)
from ctf_team_dashboard.services.notes import NoteService


# ----------------------------------------------------------------------
# Flag helpers
# ----------------------------------------------------------------------
def test_normalise_flag_trims_the_value() -> None:
    """A valid flag should be trimmed."""
    assert normalise_flag("  flag{value}  ") == "flag{value}"


def test_normalise_flag_rejects_an_empty_value() -> None:
    """An empty flag should be rejected."""
    with pytest.raises(FlagFormatError, match="empty"):
        normalise_flag("   ")


def test_normalise_flag_rejects_a_malformed_value() -> None:
    """A flag without braces should be rejected."""
    assert not is_valid_flag("flagvalue")
    assert not is_valid_flag("flag{}")


def test_mask_flag_hides_the_content() -> None:
    """The masked flag should not expose the whole content."""
    masked = mask_flag("flag{super-secret-value}")
    assert "super-secret" not in masked
    assert masked == "flag{****}"


def test_mask_flag_handles_a_short_value() -> None:
    """A short flag should be fully masked."""
    assert mask_flag("abc") == "***"


# ----------------------------------------------------------------------
# Notes service
# ----------------------------------------------------------------------
def test_add_note_requires_a_known_challenge(repositories: Repositories) -> None:
    """A note cannot be attached to an unknown challenge."""
    try:
        NoteService(repositories).add_note(challenge_id="ghost", member_id="member-1", body="hello")
    except NotFoundError:
        pass
    else:
        raise AssertionError("expected a NotFoundError")


def test_add_note_rejects_an_empty_body(repositories: Repositories) -> None:
    """An empty note should be rejected."""
    team = _team(repositories)
    challenge = _challenge(repositories, team)
    try:
        NoteService(repositories).add_note(challenge_id=challenge, member_id="member-1", body="   ")
    except ValidationError:
        pass
    else:
        raise AssertionError("expected a ValidationError")


def test_update_note_requires_the_author(repositories: Repositories) -> None:
    """Only the author may edit a note."""
    team = _team(repositories)
    challenge = _challenge(repositories, team)
    service = NoteService(repositories)
    note = service.add_note(challenge_id=challenge, member_id="member-1", body="hello")
    try:
        service.update_note(note.id, body="changed", member_id="member-2")
    except PermissionDeniedError:
        pass
    else:
        raise AssertionError("expected a PermissionDeniedError")


def test_note_preview_is_truncated(repositories: Repositories) -> None:
    """A long note should expose a truncated preview."""
    team = _team(repositories)
    challenge = _challenge(repositories, team)
    note = NoteService(repositories).add_note(
        challenge_id=challenge, member_id="member-1", body="word " * 100
    )
    assert len(note.preview) <= 140


def _team(repositories: Repositories) -> str:
    """Persist a team and return its identifier."""
    from datetime import datetime, timezone

    from ctf_team_dashboard.domain.models import Team

    team = Team(
        id="team-notes",
        name="Note Crew",
        slug="note-crew",
        created_at=datetime.now(timezone.utc),
    )
    repositories.teams.create(team)
    return team.id


def _challenge(repositories: Repositories, team_id: str) -> str:
    """Persist a challenge with its author and return its identifier."""
    from datetime import datetime, timezone

    from ctf_team_dashboard.domain.enums import ChallengeCategory, Difficulty
    from ctf_team_dashboard.domain.models import Challenge, Member

    repositories.members.create(
        Member(
            id="member-1",
            team_id=team_id,
            handle="nyx",
            display_name="Nyx",
            joined_at=datetime.now(timezone.utc),
        )
    )
    repositories.members.create(
        Member(
            id="member-2",
            team_id=team_id,
            handle="kestrel",
            display_name="Kestrel",
            joined_at=datetime.now(timezone.utc),
        )
    )
    repositories.challenges.create(
        Challenge(
            id="challenge-notes",
            team_id=team_id,
            title="Notes",
            category=ChallengeCategory.MISC,
            difficulty=Difficulty.EASY,
            created_at=datetime.now(timezone.utc),
        )
    )
    return "challenge-notes"


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------
def test_notes_endpoints_round_trip(client: TestClient) -> None:
    """A note should be created, listed and deleted through the API."""
    teams = client.get("/api/teams").json()
    team_id = teams[0]["id"]
    member = client.post("/api/members", json={"team_id": team_id, "handle": "notewriter"}).json()
    challenge = client.post(
        "/api/challenges",
        json={
            "team_id": team_id,
            "title": "Noted Challenge",
            "category": "misc",
            "difficulty": "easy",
        },
    ).json()

    created = client.post(
        f"/api/challenges/{challenge['id']}/notes",
        json={"member_id": member["id"], "body": "The key is in the README."},
    )
    assert created.status_code == 201
    note = created.json()
    assert note["body"] == "The key is in the README."

    listed = client.get(f"/api/challenges/{challenge['id']}/notes")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = client.delete(
        f"/api/challenges/notes/{note['id']}", params={"member_id": member["id"]}
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/challenges/{challenge['id']}/notes").json() == []


def test_update_note_endpoint(client: TestClient) -> None:
    """The note body should be editable through the API."""
    teams = client.get("/api/teams").json()
    team_id = teams[0]["id"]
    member = client.post("/api/members", json={"team_id": team_id, "handle": "editor"}).json()
    challenge = client.post(
        "/api/challenges",
        json={
            "team_id": team_id,
            "title": "Editable Challenge",
            "category": "misc",
            "difficulty": "easy",
        },
    ).json()

    note = client.post(
        f"/api/challenges/{challenge['id']}/notes",
        json={"member_id": member["id"], "body": "first"},
    ).json()

    updated = client.patch(
        f"/api/challenges/notes/{note['id']}",
        json={"member_id": member["id"], "body": "second"},
    )
    assert updated.status_code == 200
    assert updated.json()["body"] == "second"


def test_timeline_endpoint(client: TestClient) -> None:
    """The timeline should list the solves of a challenge."""
    teams = client.get("/api/teams").json()
    team_id = teams[0]["id"]
    member = client.post("/api/members", json={"team_id": team_id, "handle": "solver"}).json()
    challenge = client.post(
        "/api/challenges",
        json={
            "team_id": team_id,
            "title": "Timeline Challenge",
            "category": "misc",
            "difficulty": "easy",
        },
    ).json()
    client.post(
        "/api/solves",
        json={
            "challenge_id": challenge["id"],
            "member_id": member["id"],
            "flag": "flag{timeline}",
        },
    )

    response = client.get(f"/api/challenges/{challenge['id']}/timeline")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 1
    assert entries[0]["member_handle"] == "solver"
    assert "timeline" not in entries[0]["masked_flag"]
    assert entries[0]["masked_flag"].startswith("flag{")


def test_flag_submission_records_a_solve(client: TestClient) -> None:
    """A valid flag should be accepted and award the points."""
    teams = client.get("/api/teams").json()
    team_id = teams[0]["id"]
    member = client.post("/api/members", json={"team_id": team_id, "handle": "flagger"}).json()
    challenge = client.post(
        "/api/challenges",
        json={
            "team_id": team_id,
            "title": "Flag Challenge",
            "category": "misc",
            "difficulty": "medium",
            "points": 200,
        },
    ).json()

    response = client.post(
        f"/api/challenges/{challenge['id']}/flags",
        json={
            "challenge_id": challenge["id"],
            "member_id": member["id"],
            "flag": "flag{accepted}",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["points_awarded"] > 0
    assert payload["solve_id"]


def test_flag_submission_rejects_a_malformed_flag(client: TestClient) -> None:
    """A malformed flag should be reported without recording a solve."""
    teams = client.get("/api/teams").json()
    team_id = teams[0]["id"]
    member = client.post("/api/members", json={"team_id": team_id, "handle": "typo"}).json()
    challenge = client.post(
        "/api/challenges",
        json={
            "team_id": team_id,
            "title": "Typo Challenge",
            "category": "misc",
            "difficulty": "easy",
        },
    ).json()

    response = client.post(
        f"/api/challenges/{challenge['id']}/flags",
        json={
            "challenge_id": challenge["id"],
            "member_id": member["id"],
            "flag": "not-a-flag",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is False
    assert payload["solve_id"] is None


def test_flag_submission_rejects_a_mismatched_challenge(client: TestClient) -> None:
    """The challenge identifier of the payload must match the path."""
    teams = client.get("/api/teams").json()
    team_id = teams[0]["id"]
    member = client.post("/api/members", json={"team_id": team_id, "handle": "mismatch"}).json()
    challenge = client.post(
        "/api/challenges",
        json={
            "team_id": team_id,
            "title": "Mismatch Challenge",
            "category": "misc",
            "difficulty": "easy",
        },
    ).json()

    response = client.post(
        f"/api/challenges/{challenge['id']}/flags",
        json={
            "challenge_id": "another-challenge",
            "member_id": member["id"],
            "flag": "flag{mismatch}",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
