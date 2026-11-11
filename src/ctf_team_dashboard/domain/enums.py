"""Canonical enumerations used across the CTF Team Dashboard domain."""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

_StrEnumT = TypeVar("_StrEnumT", bound="StrEnum")


class StrEnum(str, Enum):
    """String-backed enum with helpers for (de)serialisation."""

    def __str__(self) -> str:
        value: str = self.value
        return value

    @classmethod
    def values(cls) -> tuple[str, ...]:
        """Return every legal value of the enum."""
        values: list[str] = []
        for member in cls:
            value: str = member.value
            values.append(value)
        return tuple(values)

    @classmethod
    def parse(cls: type[_StrEnumT], raw: str, default: _StrEnumT | None = None) -> _StrEnumT:
        """Parse a raw string into an enum member, falling back to ``default``.

        Args:
            raw: The raw string to parse.
            default: Value returned when ``raw`` is not a legal member. When
                omitted an ``ValueError`` is raised instead.

        Returns:
            The matching enum member.

        Raises:
            ValueError: If ``raw`` is unknown and no default was supplied.
        """
        normalised = raw.strip().lower()
        for member in cls:
            if member.value == normalised:
                return member
        if default is not None:
            return default
        raise ValueError(f"{raw!r} is not a valid {cls.__name__}")


class Difficulty(StrEnum):
    """Relative difficulty of a challenge."""

    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    INSANE = "insane"

    @property
    def weight(self) -> float:
        """Return a numeric weight used for progress calculations."""
        return {
            Difficulty.TRIVIAL: 0.5,
            Difficulty.EASY: 1.0,
            Difficulty.MEDIUM: 1.75,
            Difficulty.HARD: 3.0,
            Difficulty.INSANE: 5.0,
        }[self]

    @property
    def tier(self) -> int:
        """Return the 1-based tier index, ordered from easiest to hardest."""
        return list(Difficulty).index(self) + 1


class ChallengeCategory(StrEnum):
    """Standard CTF challenge categories."""

    WEB = "web"
    CRYPTO = "crypto"
    PWN = "pwn"
    REVERSE = "reverse"
    FORENSICS = "forensics"
    OSINT = "osint"
    MISC = "misc"

    @property
    def label(self) -> str:
        """Return a human readable display label."""
        return {
            ChallengeCategory.WEB: "Web",
            ChallengeCategory.CRYPTO: "Crypto",
            ChallengeCategory.PWN: "Binary",
            ChallengeCategory.REVERSE: "Reverse",
            ChallengeCategory.FORENSICS: "Forensics",
            ChallengeCategory.OSINT: "OSINT",
            ChallengeCategory.MISC: "Misc",
        }[self]

    @property
    def accent(self) -> str:
        """Return the hex accent colour associated with the category."""
        return {
            ChallengeCategory.WEB: "#38bdf8",
            ChallengeCategory.CRYPTO: "#c084fc",
            ChallengeCategory.PWN: "#fb7185",
            ChallengeCategory.REVERSE: "#fbbf24",
            ChallengeCategory.FORENSICS: "#34d399",
            ChallengeCategory.OSINT: "#a3e635",
            ChallengeCategory.MISC: "#94a3b8",
        }[self]


class ChallengeStatus(StrEnum):
    """Lifecycle status of a challenge."""

    PENDING = "pending"
    ACTIVE = "active"
    SOLVED = "solved"
    LOCKED = "locked"

    @property
    def is_terminal(self) -> bool:
        """Return whether the status can no longer change on its own."""
        return self is ChallengeStatus.SOLVED


class MemberRole(StrEnum):
    """Role of a member inside a team."""

    VIEWER = "viewer"
    ANALYST = "analyst"
    LEAD = "lead"
    ADMIN = "admin"

    @property
    def rank(self) -> int:
        """Return a monotonically increasing rank used for comparisons."""
        return list(MemberRole).index(self)

    def satisfies(self, required: MemberRole) -> bool:
        """Return whether this role grants at least the required clearance."""
        return self.rank >= required.rank


class Presence(StrEnum):
    """Presence indicator for a team member."""

    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


class EventKind(StrEnum):
    """Kinds of realtime events emitted by the dashboard."""

    SOLVE_CREATED = "solve.created"
    SOLVE_REMOVED = "solve.removed"
    CHALLENGE_CREATED = "challenge.created"
    CHALLENGE_UPDATED = "challenge.updated"
    CHALLENGE_DELETED = "challenge.deleted"
    MEMBER_UPDATED = "member.updated"
    TEAM_UPDATED = "team.updated"
    PRESENCE_CHANGED = "presence.changed"
    HEARTBEAT = "heartbeat"
