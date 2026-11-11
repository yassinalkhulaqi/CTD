"""Tests for the persistence layer."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.domain.enums import ChallengeCategory, ChallengeStatus, Difficulty
from ctf_team_dashboard.domain.models import Challenge, Member, Solve, Team
from ctf_team_dashboard.repositories import Repositories


def _team(team_id: str = "team-1") -> Team:
    """Build a team fixture."""
    return Team(
        id=team_id,
        name="Test Team",
        slug=f"slug-{team_id}",
        created_at=datetime.now(timezone.utc),
    )


def test_migrate_creates_tables(tmp_path: object) -> None:
    """Migrating should create every table used by the dashboard."""
    database = Database(str(tmp_path) + "/test.sqlite")  # type: ignore[operator]
    database.migrate()
    tables = database.table_names()
    assert {"teams", "members", "challenges", "solves", "events"} <= tables


def test_repository_round_trip(repositories: Repositories) -> None:
    """A team should survive a write/read round trip."""
    team = _team()
    repositories.teams.create(team)
    loaded = repositories.teams.get(team.id)
    assert loaded is not None
    assert loaded.name == team.name
    assert loaded.slug == team.slug


def test_repository_lookup_by_slug(repositories: Repositories) -> None:
    """Teams should be retrievable by their slug."""
    repositories.teams.create(_team())
    loaded = repositories.teams.get_by_slug("slug-team-1")
    assert loaded is not None
    assert loaded.id == "team-1"


def test_member_requires_unique_handle_per_team(repositories: Repositories) -> None:
    """The unique constraint on (team_id, handle) should be enforced."""
    import sqlite3

    repositories.teams.create(_team())
    member = Member(
        id="member-1",
        team_id="team-1",
        handle="analyst",
        display_name="Analyst",
        joined_at=datetime.now(timezone.utc),
    )
    repositories.members.create(member)
    duplicate = Member(
        id="member-2",
        team_id="team-1",
        handle="analyst",
        display_name="Other",
        joined_at=datetime.now(timezone.utc),
    )
    with pytest.raises(sqlite3.IntegrityError):
        repositories.members.create(duplicate)


def test_challenge_tags_round_trip(repositories: Repositories) -> None:
    """Challenge tags should be serialised as a JSON list."""
    repositories.teams.create(_team())
    challenge = Challenge(
        id="challenge-1",
        team_id="team-1",
        title="Web",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
        tags=("jwt", "auth"),
        created_at=datetime.now(timezone.utc),
    )
    repositories.challenges.create(challenge)
    loaded = repositories.challenges.get("challenge-1")
    assert loaded is not None
    assert loaded.tags == ("jwt", "auth")


def test_solve_list_filters_by_team(repositories: Repositories) -> None:
    """Solves should be filterable by the team owning the challenge."""
    repositories.teams.create(_team("team-1"))
    repositories.teams.create(_team("team-2"))
    for index, team_id in enumerate(("team-1", "team-2"), start=1):
        repositories.members.create(
            Member(
                id=f"member-{index}",
                team_id=team_id,
                handle=f"handle-{index}",
                display_name=f"Member {index}",
                joined_at=datetime.now(timezone.utc),
            )
        )
        repositories.challenges.create(
            Challenge(
                id=f"challenge-{team_id}",
                team_id=team_id,
                title="T",
                category=ChallengeCategory.WEB,
                difficulty=Difficulty.EASY,
                created_at=datetime.now(timezone.utc),
            )
        )
    repositories.solves.create(
        Solve(id="solve-1", challenge_id="challenge-team-1", member_id="member-1")
    )
    repositories.solves.create(
        Solve(id="solve-2", challenge_id="challenge-team-2", member_id="member-2")
    )
    assert len(repositories.solves.list_all(team_id="team-1")) == 1


def test_event_repository_records_events(repositories: Repositories) -> None:
    """Recorded events should be retrievable with their payload."""
    from ctf_team_dashboard.domain.enums import EventKind

    repositories.teams.create(_team())
    event = repositories.events.append(
        EventKind.SOLVE_CREATED, team_id="team-1", payload={"points": 100}
    )
    assert event.id > 0
    recent = repositories.events.recent(limit=10)
    assert recent[0].kind is EventKind.SOLVE_CREATED
    assert recent[0].payload == {"points": 100}


def test_event_repository_since_returns_newer_events(repositories: Repositories) -> None:
    """Resuming a stream should only return events after the given id."""
    from ctf_team_dashboard.domain.enums import EventKind

    repositories.teams.create(_team())
    first = repositories.events.append(EventKind.HEARTBEAT)
    repositories.events.append(EventKind.HEARTBEAT)
    assert len(repositories.events.since(first.id)) == 1


def test_challenge_status_can_be_updated(repositories: Repositories) -> None:
    """The lifecycle status should be updatable in isolation."""
    repositories.teams.create(_team())
    repositories.challenges.create(
        Challenge(
            id="challenge-1",
            team_id="team-1",
            title="Web",
            category=ChallengeCategory.WEB,
            difficulty=Difficulty.EASY,
            created_at=datetime.now(timezone.utc),
        )
    )
    repositories.challenges.set_status("challenge-1", ChallengeStatus.SOLVED)
    loaded = repositories.challenges.get("challenge-1")
    assert loaded is not None
    assert loaded.status is ChallengeStatus.SOLVED
