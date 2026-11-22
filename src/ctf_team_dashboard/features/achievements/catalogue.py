"""Curated badge catalogue for the achievement engine.

The catalogue is data, not logic: each entry describes a badge definition that
is inserted into the ``v3_badges`` table on first start. Operators can still
create custom badges through the API; seeding is idempotent and never overwrites
an edited row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ctf_team_dashboard.features.achievements.models import (
    Badge,
    BadgeTier,
    CriteriaKind,
)


@dataclass(frozen=True, slots=True)
class BadgeBlueprint:
    """Declarative description of a seeded badge."""

    slug: str
    name: str
    description: str
    tier: BadgeTier
    kind: CriteriaKind
    value: int | None = None
    icon: str = "trophy"
    points: int = 100
    secret: bool = False

    def materialise(self) -> Badge:
        """Build the persisted domain badge from this blueprint."""
        target = self.value if self.value is not None else self.kind.target_for(self.tier)
        return Badge(
            id=f"badge-{self.slug}",
            name=self.name,
            description=self.description,
            tier=self.tier,
            criteria_kind=self.kind,
            criteria_value=target,
            icon=self.icon,
            points=self.points,
            secret=self.secret,
        )


BLUEPRINTS: tuple[BadgeBlueprint, ...] = (
    BadgeBlueprint(
        slug="first-blood",
        name="First Blood",
        description="Submit your first successful flag solve.",
        tier=BadgeTier.BRONZE,
        kind=CriteriaKind.SOLVES,
        value=1,
        icon="crosshair",
        points=60,
    ),
    BadgeBlueprint(
        slug="warmup",
        name="Warm Up",
        description="Build momentum with five challenge solves.",
        tier=BadgeTier.BRONZE,
        kind=CriteriaKind.SOLVES,
        value=5,
        icon="flame",
        points=90,
    ),
    BadgeBlueprint(
        slug="veteran-solver",
        name="Veteran Solver",
        description="Fifteen solves is a sign of real staying power.",
        tier=BadgeTier.SILVER,
        kind=CriteriaKind.SOLVES,
        value=15,
        icon="swords",
        points=180,
    ),
    BadgeBlueprint(
        slug="flag-hunter",
        name="Flag Hunter",
        description="Collect thirty-five solves in a single competition.",
        tier=BadgeTier.GOLD,
        kind=CriteriaKind.SOLVES,
        value=35,
        icon="target",
        points=320,
    ),
    BadgeBlueprint(
        slug="polyglot",
        name="Polyglot",
        description="Score solves across two different challenge categories.",
        tier=BadgeTier.BRONZE,
        kind=CriteriaKind.CATEGORIES,
        value=2,
        icon="layers",
        points=100,
    ),
    BadgeBlueprint(
        slug="wide-spectrum",
        name="Wide Spectrum",
        description="Reach four distinct challenge categories.",
        tier=BadgeTier.SILVER,
        kind=CriteriaKind.CATEGORIES,
        value=4,
        icon="grid",
        points=200,
    ),
    BadgeBlueprint(
        slug="renaissance",
        name="Renaissance",
        description="Conquer six categories across the whole event.",
        tier=BadgeTier.GOLD,
        kind=CriteriaKind.CATEGORIES,
        value=6,
        icon="sparkles",
        points=360,
    ),
    BadgeBlueprint(
        slug="on-a-roll",
        name="On A Roll",
        description="Solve something on three consecutive days.",
        tier=BadgeTier.BRONZE,
        kind=CriteriaKind.STREAK,
        value=3,
        icon="calendar",
        points=110,
    ),
    BadgeBlueprint(
        slug="seven-day-run",
        name="Seven Day Run",
        description="Keep the solve streak alive for a full week.",
        tier=BadgeTier.SILVER,
        kind=CriteriaKind.STREAK,
        value=7,
        icon="calendar-days",
        points=220,
    ),
    BadgeBlueprint(
        slug="unbreakable",
        name="Unbreakable",
        description="Maintain a two week solve streak.",
        tier=BadgeTier.GOLD,
        kind=CriteriaKind.STREAK,
        value=14,
        icon="crown",
        points=400,
    ),
    BadgeBlueprint(
        slug="self-reliant",
        name="Self Reliant",
        description="Earn fifteen solves using at most eight hints.",
        tier=BadgeTier.BRONZE,
        kind=CriteriaKind.HINTS,
        value=8,
        icon="lightbulb",
        points=120,
    ),
    BadgeBlueprint(
        slug="sharp-instinct",
        name="Sharp Instinct",
        description="Reach fifteen solves with four hints or fewer.",
        tier=BadgeTier.SILVER,
        kind=CriteriaKind.HINTS,
        value=4,
        icon="brain",
        points=240,
    ),
    BadgeBlueprint(
        slug="no-crutches",
        name="No Crutches",
        description="Win fifteen solves with a single hint or none at all.",
        tier=BadgeTier.GOLD,
        kind=CriteriaKind.HINTS,
        value=1,
        icon="gem",
        points=440,
    ),
    BadgeBlueprint(
        slug="night-owl",
        name="The Night Owl",
        description="A hidden reward for the members who burn the midnight oil.",
        tier=BadgeTier.SILVER,
        kind=CriteriaKind.SOLVES,
        value=12,
        icon="moon",
        points=250,
        secret=True,
    ),
    BadgeBlueprint(
        slug="clean-sweep",
        name="Clean Sweep",
        description="An unknown milestone awaits the thorough solver.",
        tier=BadgeTier.GOLD,
        kind=CriteriaKind.CATEGORIES,
        value=7,
        icon="sun",
        points=500,
        secret=True,
    ),
    BadgeBlueprint(
        slug="iron-will",
        name="Iron Will",
        description="A concealed streak honour for the relentless.",
        tier=BadgeTier.GOLD,
        kind=CriteriaKind.STREAK,
        value=21,
        icon="shield",
        points=520,
        secret=True,
    ),
)


def default_badges() -> tuple[Badge, ...]:
    """Return materialised copies of every seeded badge."""
    return tuple(blueprint.materialise() for blueprint in BLUEPRINTS)


def blueprint_by_slug(slug: str) -> BadgeBlueprint | None:
    """Find a blueprint by its stable slug."""
    for blueprint in BLUEPRINTS:
        if blueprint.slug == slug:
            return blueprint
    return None


def catalogue_summary() -> dict[str, Any]:
    """Return a small summary of the built-in catalogue for documentation."""
    badges = default_badges()
    return {
        "total": len(badges),
        "secret": sum(1 for badge in badges if badge.secret),
        "by_tier": {
            tier.value: sum(1 for badge in badges if badge.tier is tier) for tier in BadgeTier
        },
        "by_kind": {
            kind.value: sum(1 for badge in badges if badge.criteria_kind is kind)
            for kind in CriteriaKind
        },
    }
