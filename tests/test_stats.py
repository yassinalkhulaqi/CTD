"""Tests for the pure statistics helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ctf_team_dashboard.domain.enums import ChallengeCategory, Difficulty
from ctf_team_dashboard.domain.models import Challenge, Member, Solve
from ctf_team_dashboard.services import stats


def test_compute_overview_returns_counts() -> None:
    """The overview helper should aggregate headline counters."""
    overview = stats.compute_overview(
        team_count=2,
        member_count=5,
        challenge_count=10,
        solve_count=7,
    )
    assert overview["teams"] == 2
    assert overview["members"] == 5
    assert overview["challenges"] == 10
    assert overview["solves"] == 7


def test_compute_member_stats_counts_solves() -> None:
    """Member stats should count solves per member."""
    member = Member(id="member-1", team_id="team-1", handle="analyst", display_name="Analyst")
    challenge = Challenge(
        id="challenge-1",
        team_id="team-1",
        title="Web",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
    )
    solve = Solve(id="solve-1", challenge_id="challenge-1", member_id="member-1")
    result = stats.compute_member_stats([member], [solve], [challenge])
    assert result[0].member_id == "member-1"
    assert result[0].solves == 1


def test_compute_category_stats_groups_by_category() -> None:
    """Category stats should group challenges and solves by category."""
    challenges = [
        Challenge(
            id="c1",
            team_id="team-1",
            title="A",
            category=ChallengeCategory.WEB,
            difficulty=Difficulty.EASY,
        ),
        Challenge(
            id="c2",
            team_id="team-1",
            title="B",
            category=ChallengeCategory.CRYPTO,
            difficulty=Difficulty.HARD,
        ),
    ]
    solves = [Solve(id="s1", challenge_id="c1", member_id="member-1")]
    result = stats.compute_category_stats(challenges, solves)
    assert len(result) == 2
    web = next(entry for entry in result if entry.category == "web")
    assert web.solves == 1
    crypto = next(entry for entry in result if entry.category == "crypto")
    assert crypto.solves == 0


def test_time_remaining_is_zero_for_past_deadline() -> None:
    """Seconds remaining should clamp to zero for past deadlines."""
    ends_at = datetime.now(timezone.utc)
    assert stats.time_remaining(ends_at, now=datetime.now(timezone.utc)) == 0.0


def test_time_remaining_counts_down_to_deadline() -> None:
    """Seconds remaining should reflect the delta to the deadline."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert stats.time_remaining(now + timedelta(seconds=90), now=now) == 90.0


def test_compute_category_stats_reports_unsolved_count() -> None:
    """Category stats should expose the outstanding challenge count."""
    challenges = [
        Challenge(
            id="c1",
            team_id="team-1",
            title="A",
            category=ChallengeCategory.WEB,
            difficulty=Difficulty.EASY,
        ),
        Challenge(
            id="c2",
            team_id="team-1",
            title="B",
            category=ChallengeCategory.WEB,
            difficulty=Difficulty.EASY,
        ),
    ]
    solves = [Solve(id="s1", challenge_id="c1", member_id="member-1")]
    result = stats.compute_category_stats(challenges, solves)
    web = next(entry for entry in result if entry.category == "web")
    assert web.challenges == 2
    assert web.solves == 1
    assert web.unsolved == 1
    assert web.solve_rate == 0.5
