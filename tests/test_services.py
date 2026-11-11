"""Tests for the service layer."""

from __future__ import annotations

import pytest

from ctf_team_dashboard.domain.enums import ChallengeCategory, ChallengeStatus, Difficulty, Presence
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.repositories import Repositories
from ctf_team_dashboard.services.challenges import ChallengeService
from ctf_team_dashboard.services.members import MemberService
from ctf_team_dashboard.services.solves import SolveService
from ctf_team_dashboard.services.stats import StatsService
from ctf_team_dashboard.services.teams import TeamService, slugify


def test_slugify_normalises_text() -> None:
    """Slugs should be lowercase and hyphen separated."""
    assert slugify("Red Scribe!") == "red-scribe"


def test_slugify_falls_back_to_team() -> None:
    """An empty slug should fall back to a safe default."""
    assert slugify("   ") == "team"


def test_create_team_rejects_duplicate_slug(repositories: Repositories) -> None:
    """Creating two teams with the same slug should be rejected."""
    service = TeamService(repositories)
    service.create_team(name="Red Scribe")
    with pytest.raises(ConflictError, match="already taken"):
        service.create_team(name="Red Scribe")


def test_create_team_rejects_invalid_colour(repositories: Repositories) -> None:
    """An invalid colour should be rejected."""
    service = TeamService(repositories)
    with pytest.raises(ValidationError, match="hex value"):
        service.create_team(name="Bad", color="red")


def test_get_team_raises_not_found(repositories: Repositories) -> None:
    """Unknown teams should raise a not found error."""
    with pytest.raises(NotFoundError, match="missing"):
        TeamService(repositories).get_team("missing")


def test_create_member_requires_existing_team(repositories: Repositories) -> None:
    """Members cannot be created for a team that does not exist."""
    try:
        MemberService(repositories).create_member(team_id="ghost", handle="analyst")
    except NotFoundError:
        pass
    else:
        raise AssertionError("expected a NotFoundError")


def test_create_member_enforces_unique_handle(repositories: Repositories) -> None:
    """Two members of a team cannot share the same handle."""
    team = TeamService(repositories).create_team(name="Red Scribe")
    service = MemberService(repositories)
    service.create_member(team_id=team.id, handle="analyst")
    try:
        service.create_member(team_id=team.id, handle="analyst")
    except ConflictError:
        pass
    else:
        raise AssertionError("expected a ConflictError")


def test_create_member_rejects_invalid_handle(repositories: Repositories) -> None:
    """Handles must match the allowed character set."""
    team = TeamService(repositories).create_team(name="Red Scribe")
    try:
        MemberService(repositories).create_member(team_id=team.id, handle="a b")
    except ValidationError:
        pass
    else:
        raise AssertionError("expected a ValidationError")


def test_set_presence_emits_event(repositories: Repositories) -> None:
    """Changing presence should record an activity event."""
    team = TeamService(repositories).create_team(name="Red Scribe")
    member = MemberService(repositories).create_member(team_id=team.id, handle="analyst")
    MemberService(repositories).set_presence(member.id, Presence.ONLINE)
    events = repositories.events.recent(limit=10)
    assert any(event.kind.value == "presence.changed" for event in events)


def test_record_solve_marks_challenge_solved(repositories: Repositories) -> None:
    """Recording a solve should move the challenge to the solved state."""
    team = TeamService(repositories).create_team(name="Red Scribe")
    member = MemberService(repositories).create_member(team_id=team.id, handle="analyst")
    challenge = ChallengeService(repositories).create_challenge(
        team_id=team.id,
        title="Web Fundamentals",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
        points=100,
    )
    SolveService(repositories).record_solve(
        challenge_id=challenge.id, member_id=member.id, flag="flag{x}"
    )
    refreshed = ChallengeService(repositories).get_challenge(challenge.id)
    assert refreshed.status is ChallengeStatus.SOLVED


def test_record_solve_rejects_duplicate(repositories: Repositories) -> None:
    """A member cannot solve the same challenge twice."""
    team = TeamService(repositories).create_team(name="Red Scribe")
    member = MemberService(repositories).create_member(team_id=team.id, handle="analyst")
    challenge = ChallengeService(repositories).create_challenge(
        team_id=team.id,
        title="Web Fundamentals",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
    )
    service = SolveService(repositories)
    service.record_solve(challenge_id=challenge.id, member_id=member.id)
    try:
        service.record_solve(challenge_id=challenge.id, member_id=member.id)
    except ConflictError:
        pass
    else:
        raise AssertionError("expected a ConflictError")


def test_record_solve_rejects_cross_team_member(repositories: Repositories) -> None:
    """Members cannot solve challenges belonging to another team."""
    first = TeamService(repositories).create_team(name="Red Scribe")
    second = TeamService(repositories).create_team(name="Null Pointers")
    member = MemberService(repositories).create_member(team_id=first.id, handle="analyst")
    challenge = ChallengeService(repositories).create_challenge(
        team_id=second.id,
        title="Web Fundamentals",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
    )
    try:
        SolveService(repositories).record_solve(
            challenge_id=challenge.id, member_id=member.id
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("expected a ValidationError")


def test_delete_solve_reopens_challenge(repositories: Repositories) -> None:
    """Removing the last solve should reopen the challenge."""
    team = TeamService(repositories).create_team(name="Red Scribe")
    member = MemberService(repositories).create_member(team_id=team.id, handle="analyst")
    challenge = ChallengeService(repositories).create_challenge(
        team_id=team.id,
        title="Web Fundamentals",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
    )
    service = SolveService(repositories)
    solve = service.record_solve(challenge_id=challenge.id, member_id=member.id)
    service.delete_solve(solve.id)
    refreshed = ChallengeService(repositories).get_challenge(challenge.id)
    assert refreshed.status is ChallengeStatus.ACTIVE


def test_create_challenge_rejects_invalid_window(repositories: Repositories) -> None:
    """A challenge cannot end before it starts."""
    from datetime import datetime, timedelta, timezone

    team = TeamService(repositories).create_team(name="Red Scribe")
    now = datetime.now(timezone.utc)
    try:
        ChallengeService(repositories).create_challenge(
            team_id=team.id,
            title="Bad",
            category=ChallengeCategory.WEB,
            difficulty=Difficulty.EASY,
            starts_at=now,
            ends_at=now - timedelta(hours=1),
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("expected a ValidationError")


def test_scoreboard_orders_by_points(repositories: Repositories) -> None:
    """The scoreboard should be ordered by descending points."""
    teams = TeamService(repositories)
    first = teams.create_team(name="Red Scribe")
    second = teams.create_team(name="Null Pointers")
    members = MemberService(repositories)
    first_member = members.create_member(team_id=first.id, handle="alpha")
    second_member = members.create_member(team_id=second.id, handle="beta")
    challenges = ChallengeService(repositories)
    first_challenge = challenges.create_challenge(
        team_id=first.id,
        title="A",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
        points=100,
    )
    second_challenge = challenges.create_challenge(
        team_id=second.id,
        title="B",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.INSANE,
        points=500,
    )
    solves = SolveService(repositories)
    solves.record_solve(challenge_id=first_challenge.id, member_id=first_member.id)
    solves.record_solve(challenge_id=second_challenge.id, member_id=second_member.id)
    board = teams.scoreboard()
    assert board[0].team_id == second.id


def test_stats_overview_counts_entities(repositories: Repositories) -> None:
    """The overview should reflect the persisted entities."""
    teams = TeamService(repositories)
    team = teams.create_team(name="Red Scribe")
    MemberService(repositories).create_member(team_id=team.id, handle="analyst")
    overview = StatsService(repositories).overview()
    assert overview["teams"] == 1
    assert overview["members"] == 1
    assert overview["challenges"] == 0
