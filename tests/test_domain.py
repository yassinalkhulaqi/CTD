"""Tests for the domain layer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ctf_team_dashboard.domain.enums import (
    ChallengeCategory,
    ChallengeStatus,
    Difficulty,
    EventKind,
    MemberRole,
    Presence,
)
from ctf_team_dashboard.domain.models import (
    Challenge,
    CompetitionWindow,
    Member,
    Solve,
    Team,
    ensure_utc,
)


def test_str_enum_parse_is_case_insensitive() -> None:
    """Enum parsing should tolerate casing and surrounding whitespace."""
    assert Difficulty.parse("  HARD ") is Difficulty.HARD


def test_str_enum_parse_raises_for_unknown_values() -> None:
    """Unknown enum values should raise a descriptive error."""
    with pytest.raises(ValueError, match="not a valid Difficulty"):
        Difficulty.parse("impossible")


def test_str_enum_parse_uses_default() -> None:
    """A default should be returned for unknown enum values."""
    assert ChallengeCategory.parse("unknown", ChallengeCategory.MISC) is ChallengeCategory.MISC


def test_difficulty_weight_increases_with_tier() -> None:
    """Harder difficulties should carry a larger weight."""
    weights = [difficulty.weight for difficulty in Difficulty]
    assert weights == sorted(weights)


def test_difficulty_tier_is_one_based() -> None:
    """The tier index should start at one for the easiest difficulty."""
    assert Difficulty.TRIVIAL.tier == 1
    assert Difficulty.INSANE.tier == 5


def test_member_role_satisfies_requirement() -> None:
    """Higher roles should satisfy lower clearance requirements."""
    assert MemberRole.ADMIN.satisfies(MemberRole.VIEWER)
    assert not MemberRole.VIEWER.satisfies(MemberRole.LEAD)


def test_team_initials_uses_two_words() -> None:
    """Team initials should be derived from the first two words."""
    assert Team(id="t", name="Red Scribe", slug="red-scribe").initials == "RS"


def test_team_initials_falls_back_to_single_word() -> None:
    """A single word team should use its first two characters."""
    assert Team(id="t", name="Null", slug="null").initials == "NU"


def test_member_is_online_reflects_presence() -> None:
    """The online helper should follow the presence flag."""
    member = Member(
        id="m",
        team_id="t",
        handle="a",
        display_name="A",
        presence=Presence.ONLINE,
    )
    assert member.is_online


def test_challenge_seconds_remaining_clamps_at_zero() -> None:
    """Expired challenges should report zero remaining seconds."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    challenge = Challenge(
        id="c",
        team_id="t",
        title="T",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
        ends_at=now - timedelta(hours=1),
    )
    assert challenge.seconds_remaining(now) == 0.0


def test_challenge_seconds_until_start() -> None:
    """Challenges should report the delay until their start time."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    challenge = Challenge(
        id="c",
        team_id="t",
        title="T",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
        starts_at=now + timedelta(minutes=30),
    )
    assert challenge.seconds_until_start(now) == 1800.0


def test_challenge_difficulty_points_scales_with_weight() -> None:
    """Awarded points should scale with the difficulty weight."""
    easy = Challenge(
        id="c",
        team_id="t",
        title="T",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
        points=100,
    )
    hard = Challenge(
        id="c",
        team_id="t",
        title="T",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.HARD,
        points=100,
    )
    assert hard.difficulty_points > easy.difficulty_points


def test_competition_window_progress() -> None:
    """The competition progress should reflect the elapsed fraction."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    window = CompetitionWindow(starts_at=now, ends_at=now + timedelta(hours=10))
    assert window.progress(now) == 0.0
    assert window.progress(now + timedelta(hours=5)) == 0.5


def test_competition_window_without_bounds_is_empty() -> None:
    """An unbounded competition window should report zeroes."""
    window = CompetitionWindow()
    assert window.total_seconds() == 0.0
    assert window.progress() == 0.0


def test_ensure_utc_marks_naive_datetimes() -> None:
    """Naive datetimes should be interpreted as UTC."""
    naive = datetime(2026, 1, 1, 12, 0, 0)
    assert ensure_utc(naive).tzinfo is timezone.utc


def test_solve_is_scored_only_with_points() -> None:
    """A solve only counts as scored when points were awarded."""
    assert Solve(id="s", challenge_id="c", member_id="m", points_awarded=10).is_scored
    assert not Solve(id="s", challenge_id="c", member_id="m").is_scored


def test_event_kind_values_are_unique() -> None:
    """Every event kind should map to a distinct wire value."""
    values = [kind.value for kind in EventKind]
    assert len(values) == len(set(values))


def test_challenge_status_terminal_flag() -> None:
    """Only the solved status should be considered terminal."""
    assert ChallengeStatus.SOLVED.is_terminal
    assert not ChallengeStatus.ACTIVE.is_terminal
