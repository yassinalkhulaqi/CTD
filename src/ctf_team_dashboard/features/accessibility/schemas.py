"""Typed request and response schemas for the accessibility API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ctf_team_dashboard.features.accessibility.models import (
    ContrastLevel,
    Severity,
    normalise_color,
)


class AccessibilityModel(BaseModel):
    """Base model configured for attribute and alias friendly validation."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class IssueCreateRequest(AccessibilityModel):
    """Payload used to record an accessibility issue."""

    path: str = Field(min_length=1, max_length=240)
    rule_id: str = Field(min_length=1, max_length=80)
    severity: Severity
    description: str = Field(min_length=1, max_length=2_000)
    suggestion: str = Field(default="", max_length=500)
    detected_at: datetime | None = None


class IssueRead(AccessibilityModel):
    """An accessibility issue as returned by the API."""

    id: str
    path: str
    rule_id: str
    severity: Severity
    description: str
    suggestion: str
    detected_at: datetime
    resolved_at: datetime | None = None
    is_resolved: bool
    severity_weight: int


class ShortcutCreateRequest(AccessibilityModel):
    """Payload used to register a keyboard shortcut."""

    keys: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=1, max_length=120)
    scope: str = Field(default="global", min_length=1, max_length=60)


class ShortcutRead(AccessibilityModel):
    """A registered keyboard shortcut."""

    id: str
    keys: str
    canonical_keys: str
    display_keys: str
    action: str
    scope: str
    is_global: bool
    is_chord: bool


class ShortcutConflictRead(AccessibilityModel):
    """A pair of shortcuts that collide in keys and scope."""

    description: str
    left_id: str
    right_id: str
    keys: str


class ContrastPairRequest(AccessibilityModel):
    """Payload describing one colour pair to audit."""

    foreground: str = Field(min_length=1, max_length=64)
    background: str = Field(min_length=1, max_length=64)
    path: str = Field(default="", max_length=240)
    label: str = Field(default="", max_length=120)
    large_text: bool = False
    record_issue: bool = False

    @field_validator("foreground", "background")
    @classmethod
    def _normalise_colours(cls, value: str) -> str:
        """Normalise accepted colour literals to ``#rrggbb``."""
        return normalise_color(value)


class ContrastPairRead(AccessibilityModel):
    """The WCAG evaluation of a colour pair."""

    foreground: str
    background: str
    path: str
    label: str
    large_text: bool
    ratio: float
    passes_aa: bool
    passes_aaa: bool
    level: ContrastLevel
    suggestion: str


class ContrastAuditRead(AccessibilityModel):
    """The aggregate result of one or more contrast audits."""

    pairs: list[ContrastPairRead]
    issues: list[IssueRead]
    failures: int
    pass_rate: float
    average_ratio: float


class FocusOrderCreateRequest(AccessibilityModel):
    """Payload used to add a focus stop."""

    label: str = Field(min_length=1, max_length=120)
    order: int | None = Field(default=None, ge=1)


class FocusOrderReorderRequest(AccessibilityModel):
    """Payload describing a complete tab order."""

    ids: list[str] = Field(min_length=1, max_length=100)


class FocusOrderEntryRead(AccessibilityModel):
    """One stop in the configured tab order."""

    id: str
    label: str
    order: int
    aria_label: str


class FocusTrapRead(AccessibilityModel):
    """A snapshot of the focus trap state machine."""

    entries: list[FocusOrderEntryRead]
    index: int
    size: int
    current_id: str | None = None
    next_id: str | None = None
    previous_id: str | None = None


class AriaSuggestionRequest(AccessibilityModel):
    """Payload used to generate an ARIA label suggestion."""

    text: str = Field(min_length=0, max_length=240)
    context: str = Field(default="", max_length=120)
    action: str = Field(default="", max_length=120)


class AriaSuggestionRead(AccessibilityModel):
    """A generated ARIA label suggestion."""

    suggestion: str


class AccessibilityStatsRead(AccessibilityModel):
    """Aggregated counters powering the overview cards."""

    total_issues: int
    open_issues: int
    resolved_issues: int
    critical_open: int
    warning_open: int
    info_open: int
    shortcut_count: int
    focus_entry_count: int
    scopes: list[str]
    severity_counts: dict[str, int]
    resolution_rate: float
    risk_score: int
