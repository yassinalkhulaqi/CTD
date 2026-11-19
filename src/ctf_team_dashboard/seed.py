"""Deterministic seed data for the CTF Team Dashboard.

The generator produces a realistic multi-team competition so the dashboard can
be demonstrated, screenshot and tested without an external CTF platform.
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ctf_team_dashboard.domain.enums import (
    ChallengeCategory,
    ChallengeStatus,
    Difficulty,
    MemberRole,
    Presence,
)
from ctf_team_dashboard.domain.models import Challenge, Member, Solve, Team
from ctf_team_dashboard.repositories import Repositories


@dataclass(frozen=True, slots=True)
class TeamBlueprint:
    """Static description of a team used by the seed generator."""

    name: str
    slug: str
    color: str
    description: str
    handles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChallengeBlueprint:
    """Static description of a challenge used by the seed generator."""

    title: str
    category: ChallengeCategory
    difficulty: Difficulty
    points: int
    description: str
    tags: tuple[str, ...] = field(default_factory=tuple)


TEAM_BLUEPRINTS: tuple[TeamBlueprint, ...] = (
    TeamBlueprint(
        name="RedScribe",
        slug="redscribe",
        color="#f43f5e",
        description="Offensive security specialists with a taste for web exploitation.",
        handles=("nyx", "kestrel", "bitrot", "saffron"),
    ),
    TeamBlueprint(
        name="Null Pointers",
        slug="null-pointers",
        color="#22d3ee",
        description="Binary exploitation and kernel internals specialists.",
        handles=("cortex", "nxbit", "mr_sp0t", "quark"),
    ),
    TeamBlueprint(
        name="Cipher Wardens",
        slug="cipher-wardens",
        color="#a855f7",
        description="Cryptanalysis and applied mathematics heavyweights.",
        handles=("entropy", "polybius", "rsa_trouble", "hashbrown"),
    ),
    TeamBlueprint(
        name="Ghost In The Shellcode",
        slug="ghost-in-the-shellcode",
        color="#f59e0b",
        description="Reverse engineering, forensics and hardware hacking.",
        handles=("objdump", "heapster", "tracepoint", "byteme"),
    ),
)

CHALLENGE_BLUEPRINTS: tuple[ChallengeBlueprint, ...] = (
    ChallengeBlueprint(
        title="Blazing Fast Login",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.EASY,
        points=100,
        tags=("jwt", "auth-bypass"),
        description="A login flow that trusts its own input a little too much.",
    ),
    ChallengeBlueprint(
        title="Kubernetes Secrets",
        category=ChallengeCategory.WEB,
        difficulty=Difficulty.MEDIUM,
        points=250,
        tags=("k8s", "cloud"),
        description="Someone pushed a secret to the wrong namespace.",
    ),
    ChallengeBlueprint(
        title="Nonce Reuse",
        category=ChallengeCategory.CRYPTO,
        difficulty=Difficulty.MEDIUM,
        points=250,
        tags=("aes", "stream-cipher"),
        description="The IV looks suspiciously familiar.",
    ),
    ChallengeBlueprint(
        title="RSA In The Shell",
        category=ChallengeCategory.CRYPTO,
        difficulty=Difficulty.HARD,
        points=400,
        tags=("rsa", "padding-oracle"),
        description="Small exponent, careless padding.",
    ),
    ChallengeBlueprint(
        title="Heap House Of Cards",
        category=ChallengeCategory.PWN,
        difficulty=Difficulty.HARD,
        points=400,
        tags=("heap", "uaf"),
        description="Free the wrong chunk twice.",
    ),
    ChallengeBlueprint(
        title="Format String Fan",
        category=ChallengeCategory.PWN,
        difficulty=Difficulty.EASY,
        points=100,
        tags=("fmtstr",),
        description="printf with user supplied input.",
    ),
    ChallengeBlueprint(
        title="Obfuscated Botnet",
        category=ChallengeCategory.REVERSE,
        difficulty=Difficulty.MEDIUM,
        points=250,
        tags=("dotnet", "anti-debug"),
        description="Strip the packer, read the C2 config.",
    ),
    ChallengeBlueprint(
        title="Ghost In The Firmware",
        category=ChallengeCategory.REVERSE,
        difficulty=Difficulty.INSANE,
        points=600,
        tags=("arm", "rootkit"),
        description="A signed implant hiding in a signed update.",
    ),
    ChallengeBlueprint(
        title="Carved From The River",
        category=ChallengeCategory.FORENSICS,
        difficulty=Difficulty.MEDIUM,
        points=250,
        tags=("pcap", "carving"),
        description="Something was extracted from a memory dump.",
    ),
    ChallengeBlueprint(
        title="Timestamp Anomaly",
        category=ChallengeCategory.FORENSICS,
        difficulty=Difficulty.EASY,
        points=100,
        tags=("ntfs", "timeline"),
        description="The timestamps do not agree with each other.",
    ),
    ChallengeBlueprint(
        title="Corporate Ladder",
        category=ChallengeCategory.OSINT,
        difficulty=Difficulty.EASY,
        points=100,
        tags=("dns", "employees"),
        description="Find the person who owns the deploy key.",
    ),
    ChallengeBlueprint(
        title="Quantum Dice",
        category=ChallengeCategory.MISC,
        difficulty=Difficulty.TRIVIAL,
        points=50,
        tags=("steganography", "png"),
        description="The image is hiding more than it shows.",
    ),
)

_ROLE_CYCLE: tuple[MemberRole, ...] = (
    MemberRole.LEAD,
    MemberRole.ANALYST,
    MemberRole.ANALYST,
    MemberRole.VIEWER,
)


def _make_id_factory() -> Callable[[str], str]:
    """Return a factory producing deterministic, unique identifiers.

    The identifiers are stable across runs so the seeded dataset can be
    compared between two instances of the dashboard.
    """
    counter = itertools.count(1)

    def factory(prefix: str) -> str:
        """Return the next identifier for the given prefix."""
        return f"{prefix}-{next(counter):04d}"

    return factory


def build_seed_data(
    *,
    competition_hours: int = 36,
    seed: int = 1337,
    team_count: int | None = None,
) -> tuple[list[Team], list[Member], list[Challenge], list[Solve]]:
    """Build a complete, deterministic dataset.

    Args:
        competition_hours: Length of the competition window in hours.
        seed: Seed for the random number generator.
        team_count: Optional limit on the number of teams generated.

    Returns:
        A tuple of ``(teams, members, challenges, solves)``.
    """
    rng = random.Random(seed)
    uid = _make_id_factory()
    now = datetime.now(timezone.utc)
    starts_at = now - timedelta(hours=competition_hours // 2)
    ends_at = now + timedelta(hours=competition_hours // 2)

    blueprints = TEAM_BLUEPRINTS if team_count is None else TEAM_BLUEPRINTS[:team_count]

    teams: list[Team] = []
    members: list[Member] = []
    challenges: list[Challenge] = []
    solves: list[Solve] = []

    for blueprint in blueprints:
        team_id = uid("team")
        teams.append(
            Team(
                id=team_id,
                name=blueprint.name,
                slug=blueprint.slug,
                color=blueprint.color,
                description=blueprint.description,
                created_at=starts_at,
            )
        )

        for member_index, handle in enumerate(blueprint.handles):
            presence = rng.choice(
                [Presence.ONLINE, Presence.ONLINE, Presence.AWAY, Presence.OFFLINE]
            )
            members.append(
                Member(
                    id=uid("member"),
                    team_id=team_id,
                    handle=handle,
                    display_name=handle.replace("_", " ").title(),
                    role=_ROLE_CYCLE[member_index % len(_ROLE_CYCLE)],
                    presence=presence,
                    joined_at=starts_at,
                )
            )

        for challenge_blueprint in CHALLENGE_BLUEPRINTS:
            offset_hours = rng.randint(-12, 12)
            window_start = starts_at + timedelta(hours=offset_hours)
            challenges.append(
                Challenge(
                    id=uid("challenge"),
                    team_id=team_id,
                    title=challenge_blueprint.title,
                    category=challenge_blueprint.category,
                    difficulty=challenge_blueprint.difficulty,
                    points=challenge_blueprint.points,
                    description=challenge_blueprint.description,
                    status=ChallengeStatus.PENDING,
                    tags=challenge_blueprint.tags,
                    starts_at=window_start,
                    ends_at=ends_at,
                    created_at=window_start,
                )
            )

    solved_counter = 0
    for challenge in challenges:
        if rng.random() > 0.62:
            continue
        team_members = [m for m in members if m.team_id == challenge.team_id]
        if not team_members:
            continue
        solver_count = 1 if rng.random() < 0.75 else min(2, len(team_members))
        for solver in rng.sample(team_members, solver_count):
            solved_counter += 1
            base_time = challenge.starts_at or starts_at
            solved_at = base_time + timedelta(hours=rng.randint(0, max(1, competition_hours // 2)))
            if solved_at > now:
                solved_at = now - timedelta(minutes=rng.randint(1, 90))
            solves.append(
                Solve(
                    id=uid("solve"),
                    challenge_id=challenge.id,
                    member_id=solver.id,
                    flag=f"flag{{{challenge.title.lower().replace(' ', '_')}}}",
                    points_awarded=challenge.difficulty_points,
                    solved_at=solved_at,
                )
            )

    solved_ids = {solve.challenge_id for solve in solves}
    resolved_challenges = [
        Challenge(
            id=challenge.id,
            team_id=challenge.team_id,
            title=challenge.title,
            category=challenge.category,
            difficulty=challenge.difficulty,
            points=challenge.points,
            description=challenge.description,
            status=(
                ChallengeStatus.SOLVED if challenge.id in solved_ids else ChallengeStatus.ACTIVE
            ),
            tags=challenge.tags,
            starts_at=challenge.starts_at,
            ends_at=challenge.ends_at,
            created_at=challenge.created_at,
        )
        for challenge in challenges
    ]

    return teams, members, resolved_challenges, solves


def persist_seed_data(
    repositories: Repositories | None = None, *, force: bool = False
) -> dict[str, int]:
    """Write the seed dataset into the database.

    Args:
        repositories: Optional repository container.
        force: When ``True`` the existing data is replaced.

    Returns:
        A mapping of entity name to the number of persisted rows.
    """
    repos = repositories or Repositories()
    existing = repos.teams.count_matching()
    if existing and not force:
        return {"teams": existing, "members": 0, "challenges": 0, "solves": 0}

    if force:
        for table in ("events", "solves", "challenges", "members", "teams"):
            repos.execute(f"DELETE FROM {table}")

    teams, members, challenges, solves = build_seed_data()
    for team in teams:
        repos.teams.create(team)
    for member in members:
        repos.members.create(member)
    for challenge in challenges:
        repos.challenges.create(challenge)
    for solve in solves:
        repos.solves.create(solve)

    return {
        "teams": len(teams),
        "members": len(members),
        "challenges": len(challenges),
        "solves": len(solves),
    }
