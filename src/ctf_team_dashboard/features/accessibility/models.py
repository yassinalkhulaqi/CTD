"""Domain models and pure calculations for the accessibility toolkit."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TypeAlias

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import ensure_utc, utcnow

RGB: TypeAlias = tuple[int, int, int]

GLOBAL_SCOPES: frozenset[str] = frozenset({"global", "*", "all"})

_HEX_COLOUR = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_RGB_COLOUR = re.compile(
    r"^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$",
    re.IGNORECASE,
)

_COLOUR_ALIASES: dict[str, str] = {
    "black": "#000000",
    "white": "#ffffff",
    "gray": "#808080",
    "grey": "#808080",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "orange": "#ffa500",
    "navy": "#000080",
}

_KEY_ALIASES: dict[str, str] = {
    "control": "ctrl",
    "option": "alt",
    "cmd": "meta",
    "command": "meta",
    "windows": "meta",
    "esc": "escape",
    "return": "enter",
    "del": "delete",
    "spacebar": "space",
    "plus": "+",
}

_MODIFIER_ORDER: tuple[str, ...] = ("ctrl", "alt", "shift", "meta")

_DISPLAY_NAMES: dict[str, str] = {
    "ctrl": "Ctrl",
    "alt": "Alt",
    "shift": "Shift",
    "meta": "Meta",
    "escape": "Esc",
    "enter": "Enter",
    "delete": "Del",
    "space": "Space",
    "+": "+",
}

_GENERIC_LABELS: frozenset[str] = frozenset(
    {
        "button",
        "click here",
        "here",
        "link",
        "ok",
        "submit",
        "text field",
        "untitled",
    }
)


class Severity(StrEnum):
    """Impact level of an accessibility issue."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def weight(self) -> int:
        """Return a numeric weight used to order issues by impact."""
        return {
            Severity.INFO: 1,
            Severity.WARNING: 2,
            Severity.CRITICAL: 3,
        }[self]

    @property
    def tone(self) -> str:
        """Return the design-system badge tone associated with the level."""
        return {
            Severity.INFO: "info",
            Severity.WARNING: "warning",
            Severity.CRITICAL: "danger",
        }[self]


class ContrastLevel(StrEnum):
    """Highest WCAG conformance level reached by a colour pair."""

    FAIL = "fail"
    AA = "aa"
    AAA = "aaa"

    @property
    def rank(self) -> int:
        """Return a numeric rank where higher means stronger conformance."""
        return {
            ContrastLevel.FAIL: 0,
            ContrastLevel.AA: 1,
            ContrastLevel.AAA: 2,
        }[self]


class FocusDirection(str, Enum):
    """Direction of a single step through a focus trap."""

    NEXT = "next"
    PREVIOUS = "previous"

    @property
    def delta(self) -> int:
        """Return the signed index change for this direction."""
        return 1 if self is FocusDirection.NEXT else -1


def parse_color(raw: str) -> RGB:
    """Parse a CSS-like colour literal into an sRGB triple.

    Args:
        raw: A hex colour, ``rgb(r, g, b)`` expression or supported colour name.

    Returns:
        The red, green and blue channels, each between 0 and 255.

    Raises:
        ValueError: When the literal cannot be parsed.
    """
    value = raw.strip().lower()
    value = _COLOUR_ALIASES.get(value, value)
    hex_match = _HEX_COLOUR.fullmatch(value)
    if hex_match is not None:
        digits = hex_match.group(1)
        if len(digits) == 3:
            digits = "".join(channel * 2 for channel in digits)
        return (
            int(digits[0:2], 16),
            int(digits[2:4], 16),
            int(digits[4:6], 16),
        )
    rgb_match = _RGB_COLOUR.fullmatch(value)
    if rgb_match is not None:
        channels = tuple(int(rgb_match.group(index)) for index in (1, 2, 3))
        if all(0 <= channel <= 255 for channel in channels):
            red, green, blue = channels
            return red, green, blue
    raise ValueError(f"{raw!r} is not a supported colour")


def normalise_color(raw: str) -> str:
    """Return the canonical ``#rrggbb`` representation of a colour."""
    red, green, blue = parse_color(raw)
    return f"#{red:02x}{green:02x}{blue:02x}"


def linearise_channel(channel: int) -> float:
    """Convert an 8-bit sRGB channel into its linear luminance component."""
    value = channel / 255.0
    if value <= 0.04045:
        return value / 12.92
    return float(((value + 0.055) / 1.055) ** 2.4)


def relative_luminance(colour: RGB | str) -> float:
    """Compute the WCAG relative luminance of a colour."""
    red, green, blue = parse_color(colour) if isinstance(colour, str) else colour
    return (
        0.2126 * linearise_channel(red)
        + 0.7152 * linearise_channel(green)
        + 0.0722 * linearise_channel(blue)
    )


def contrast_ratio(foreground: RGB | str, background: RGB | str) -> float:
    """Compute the WCAG 2.1 contrast ratio between two colours."""
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter = max(first, second)
    darker = min(first, second)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def contrast_thresholds(*, large_text: bool = False) -> tuple[float, float]:
    """Return the AA and AAA contrast thresholds for the text size."""
    if large_text:
        return 3.0, 4.5
    return 4.5, 7.0


def classify_contrast(ratio: float, *, large_text: bool = False) -> ContrastLevel:
    """Classify a contrast ratio into a WCAG conformance level."""
    aa_threshold, aaa_threshold = contrast_thresholds(large_text=large_text)
    if ratio >= aaa_threshold:
        return ContrastLevel.AAA
    if ratio >= aa_threshold:
        return ContrastLevel.AA
    return ContrastLevel.FAIL


def suggest_contrast_fix(
    foreground: str,
    background: str,
    *,
    large_text: bool = False,
    ratio: float | None = None,
) -> str:
    """Return an actionable suggestion for an audited colour pair."""
    measured = contrast_ratio(foreground, background) if ratio is None else ratio
    aa_threshold, _ = contrast_thresholds(large_text=large_text)
    if measured >= aa_threshold:
        return f"This pair meets WCAG AA at {measured:.2f}:1; preserve it in the theme."
    foreground_luminance = relative_luminance(foreground)
    background_luminance = relative_luminance(background)
    if foreground_luminance >= background_luminance:
        direction = "darken the foreground or lighten the background"
    else:
        direction = "lighten the foreground or darken the background"
    size = "large text" if large_text else "body text"
    return f"Reach at least {aa_threshold:.1f}:1 for {size}: {direction}."


@dataclass(frozen=True, slots=True)
class A11yIssue:
    """A recorded accessibility defect found on a dashboard route."""

    id: str
    path: str
    rule_id: str
    severity: Severity
    description: str
    suggestion: str = ""
    detected_at: datetime = field(default_factory=utcnow)
    resolved_at: datetime | None = None

    @property
    def is_resolved(self) -> bool:
        """Return whether the issue has been resolved."""
        return self.resolved_at is not None

    @property
    def severity_weight(self) -> int:
        """Return the numeric impact weight of the issue."""
        return self.severity.weight

    @property
    def summary(self) -> str:
        """Return a short single-line summary suitable for a list row."""
        return " ".join(self.description.split())[:160]

    @property
    def age_seconds(self) -> float:
        """Return the seconds elapsed since detection, or until resolution."""
        end = ensure_utc(self.resolved_at) if self.resolved_at is not None else utcnow()
        return max(0.0, (end - ensure_utc(self.detected_at)).total_seconds())

    def resolve(self, *, when: datetime | None = None) -> A11yIssue:
        """Return a resolved copy of the issue."""
        if self.resolved_at is not None:
            raise ValueError(f"issue {self.id} is already resolved")
        return A11yIssue(
            id=self.id,
            path=self.path,
            rule_id=self.rule_id,
            severity=self.severity,
            description=self.description,
            suggestion=self.suggestion,
            detected_at=self.detected_at,
            resolved_at=ensure_utc(when if when is not None else utcnow()),
        )

    def with_suggestion(self, suggestion: str) -> A11yIssue:
        """Return a copy carrying a new remediation hint."""
        return A11yIssue(
            id=self.id,
            path=self.path,
            rule_id=self.rule_id,
            severity=self.severity,
            description=self.description,
            suggestion=suggestion,
            detected_at=self.detected_at,
            resolved_at=self.resolved_at,
        )


@dataclass(frozen=True, slots=True)
class ContrastPair:
    """A foreground and background colour submitted for WCAG auditing."""

    foreground: str
    background: str
    path: str = ""
    label: str = ""
    large_text: bool = False

    @property
    def foreground_hex(self) -> str:
        """Return the canonical foreground colour."""
        return normalise_color(self.foreground)

    @property
    def background_hex(self) -> str:
        """Return the canonical background colour."""
        return normalise_color(self.background)

    @property
    def ratio(self) -> float:
        """Return the WCAG contrast ratio of the pair."""
        return contrast_ratio(self.foreground_hex, self.background_hex)

    @property
    def passes_aa(self) -> bool:
        """Return whether the pair meets WCAG AA."""
        aa_threshold, _ = contrast_thresholds(large_text=self.large_text)
        return self.ratio >= aa_threshold

    @property
    def passes_aaa(self) -> bool:
        """Return whether the pair meets WCAG AAA."""
        _, aaa_threshold = contrast_thresholds(large_text=self.large_text)
        return self.ratio >= aaa_threshold

    @property
    def level(self) -> ContrastLevel:
        """Return the highest WCAG level reached by the pair."""
        return classify_contrast(self.ratio, large_text=self.large_text)

    @property
    def suggestion(self) -> str:
        """Return a remediation hint for the pair."""
        return suggest_contrast_fix(
            self.foreground_hex,
            self.background_hex,
            large_text=self.large_text,
            ratio=self.ratio,
        )

    @property
    def display_label(self) -> str:
        """Return the human readable label of the audited element."""
        return self.label.strip() or "Unlabelled text"


@dataclass(frozen=True, slots=True)
class ContrastAudit:
    """The outcome of auditing one or more colour pairs."""

    pairs: tuple[ContrastPair, ...]
    issues: tuple[A11yIssue, ...] = ()

    @property
    def failures(self) -> tuple[ContrastPair, ...]:
        """Return the pairs that failed WCAG AA."""
        return tuple(pair for pair in self.pairs if not pair.passes_aa)

    @property
    def passing(self) -> tuple[ContrastPair, ...]:
        """Return the pairs that passed WCAG AA."""
        return tuple(pair for pair in self.pairs if pair.passes_aa)

    @property
    def pass_rate(self) -> float:
        """Return the fraction of pairs that passed WCAG AA."""
        if not self.pairs:
            return 0.0
        return len(self.passing) / len(self.pairs)

    @property
    def average_ratio(self) -> float:
        """Return the mean contrast ratio across all audited pairs."""
        if not self.pairs:
            return 0.0
        return round(sum(pair.ratio for pair in self.pairs) / len(self.pairs), 2)

    @property
    def worst_pair(self) -> ContrastPair | None:
        """Return the pair with the lowest contrast ratio."""
        if not self.pairs:
            return None
        return min(self.pairs, key=lambda pair: pair.ratio)


def parse_shortcut(raw: str) -> tuple[str, ...]:
    """Parse a shortcut expression into canonical key steps.

    Args:
        raw: A shortcut such as ``Ctrl+K`` or a sequence such as ``g g``.

    Returns:
        The canonical steps, each formatted as ``modifier+key``.

    Raises:
        ValueError: When the expression is empty, malformed or too long.
    """
    compact = re.sub(r"\s*\+\s*", "+", raw.strip())
    if not compact:
        raise ValueError("shortcut keys must not be empty")
    steps: list[str] = []
    for token in compact.split():
        parts = [part.strip().lower() for part in token.split("+")]
        parts = [_KEY_ALIASES.get(part, part) for part in parts if part]
        modifiers: list[str] = []
        key = ""
        for part in parts:
            if part in _MODIFIER_ORDER:
                if part in modifiers:
                    raise ValueError(f"duplicate modifier {part!r} in shortcut")
                modifiers.append(part)
            elif key:
                raise ValueError(f"shortcut step {token!r} has multiple keys")
            else:
                key = part
        if not key:
            raise ValueError(f"shortcut step {token!r} has no key")
        ordered = tuple(modifier for modifier in _MODIFIER_ORDER if modifier in modifiers)
        steps.append("+".join((*ordered, key)))
    if len(steps) > 4:
        raise ValueError("a shortcut may contain at most four steps")
    return tuple(steps)


def canonical_shortcut(raw: str) -> str:
    """Return the canonical string representation of a shortcut."""
    return " ".join(parse_shortcut(raw))


def display_shortcut(raw: str) -> str:
    """Return a human friendly rendering of a shortcut."""
    rendered: list[str] = []
    for step in parse_shortcut(raw):
        rendered.append(
            "+".join(_DISPLAY_NAMES.get(part, part.upper()) for part in step.split("+"))
        )
    return " ".join(rendered)


@dataclass(frozen=True, slots=True)
class KeyboardShortcut:
    """A keyboard binding registered for a dashboard scope."""

    id: str
    keys: str
    action: str
    scope: str = "global"

    @property
    def steps(self) -> tuple[str, ...]:
        """Return the canonical key steps of the binding."""
        return parse_shortcut(self.keys)

    @property
    def canonical_keys(self) -> str:
        """Return the canonical shortcut expression."""
        return " ".join(self.steps)

    @property
    def display_keys(self) -> str:
        """Return the shortcut formatted for display."""
        return display_shortcut(self.keys)

    @property
    def is_global(self) -> bool:
        """Return whether the binding applies to every scope."""
        return self.scope.strip().lower() in GLOBAL_SCOPES

    @property
    def is_chord(self) -> bool:
        """Return whether the binding is a multi-step chord."""
        return len(self.steps) > 1

    @property
    def modifier_keys(self) -> tuple[str, ...]:
        """Return the modifiers used by the first step of the binding."""
        parts = self.steps[0].split("+")
        return tuple(part for part in parts[:-1] if part in _MODIFIER_ORDER)

    def applies_to(self, scope: str) -> bool:
        """Return whether the binding is active in ``scope``."""
        return self.is_global or self.scope.strip().lower() == scope.strip().lower()

    def matches(self, keys: str, *, scope: str | None = None) -> bool:
        """Return whether a pressed key sequence triggers this binding."""
        if canonical_shortcut(keys) != self.canonical_keys:
            return False
        return scope is None or self.applies_to(scope)

    def conflicts_with(self, other: KeyboardShortcut) -> bool:
        """Return whether two bindings collide in keys and scope."""
        if self.canonical_keys != other.canonical_keys:
            return False
        if self.is_global or other.is_global:
            return True
        return self.scope.strip().lower() == other.scope.strip().lower()


@dataclass(frozen=True, slots=True)
class ShortcutConflict:
    """A pair of keyboard shortcuts that cannot both be active."""

    left: KeyboardShortcut
    right: KeyboardShortcut

    @property
    def description(self) -> str:
        """Return a human readable description of the collision."""
        return (
            f"{self.left.display_keys} is bound to {self.left.action!r} and "
            f"{self.right.action!r} in overlapping scopes"
        )


def find_shortcut_conflicts(shortcuts: Iterable[KeyboardShortcut]) -> list[ShortcutConflict]:
    """Return every conflicting pair in a collection of shortcuts."""
    entries = list(shortcuts)
    conflicts: list[ShortcutConflict] = []
    for index, left in enumerate(entries):
        for right in entries[index + 1 :]:
            if left.conflicts_with(right):
                conflicts.append(ShortcutConflict(left, right))
    return conflicts


def suggest_aria_label(text: str, *, context: str = "", action: str = "") -> str:
    """Suggest a descriptive ARIA label from control text and context."""
    description = " ".join(text.split())
    scope = " ".join(context.split())
    verb = " ".join(action.split())
    lowered = description.lower()

    if not description or lowered in _GENERIC_LABELS:
        if verb and scope:
            suggestion = f"{verb} {scope}"
        elif scope:
            suggestion = f"Open {scope}"
        elif verb:
            suggestion = f"{verb} control"
        else:
            suggestion = "Describe this control"
    else:
        suggestion = description
        if scope and scope.lower() not in suggestion.lower():
            suggestion = f"{suggestion} for {scope}"
        if verb and verb.lower() not in suggestion.lower():
            suggestion = f"{verb} {suggestion}"

    suggestion = " ".join(suggestion.split()).strip(" .")
    if not suggestion:
        return "Describe this control"
    if len(suggestion) > 160:
        suggestion = suggestion[:159].rstrip() + "…"
    return suggestion[0].upper() + suggestion[1:]


@dataclass(frozen=True, slots=True)
class FocusOrderEntry:
    """One stop in the tab sequence of an accessibility demo."""

    id: str
    label: str
    order: int

    @property
    def aria_label(self) -> str:
        """Return the suggested accessible name of the stop."""
        return suggest_aria_label(self.label, context="focus order")

    def with_order(self, order: int) -> FocusOrderEntry:
        """Return a copy with a new position."""
        return FocusOrderEntry(id=self.id, label=self.label, order=order)


def sort_focus_entries(entries: Iterable[FocusOrderEntry]) -> list[FocusOrderEntry]:
    """Sort focus stops by position and identifier."""
    return sorted(entries, key=lambda entry: (entry.order, entry.id))


def validate_focus_entries(entries: Sequence[FocusOrderEntry]) -> tuple[FocusOrderEntry, ...]:
    """Validate and normalise a focus order sequence."""
    identifiers: set[str] = set()
    positions: set[int] = set()
    for entry in entries:
        if not entry.id.strip():
            raise ValueError("focus entry identifiers must not be empty")
        if entry.order < 1:
            raise ValueError("focus order positions must be positive")
        if entry.id in identifiers:
            raise ValueError(f"duplicate focus entry {entry.id!r}")
        if entry.order in positions:
            raise ValueError(f"duplicate focus order position {entry.order}")
        identifiers.add(entry.id)
        positions.add(entry.order)
    return tuple(sort_focus_entries(entries))


@dataclass(frozen=True, slots=True)
class FocusTrap:
    """An immutable focus trap state machine with explicit wrap behaviour."""

    entries: tuple[FocusOrderEntry, ...] = ()
    index: int = 0

    def __post_init__(self) -> None:
        """Reject an index that does not address an entry."""
        if self.entries and not 0 <= self.index < len(self.entries):
            raise ValueError("focus trap index is out of range")
        if not self.entries and self.index != 0:
            raise ValueError("an empty focus trap must stay at index zero")

    @classmethod
    def from_entries(cls, entries: Iterable[FocusOrderEntry], *, index: int = 0) -> FocusTrap:
        """Build a trap from a possibly unsorted collection of entries."""
        ordered = validate_focus_entries(tuple(entries))
        return cls(ordered, index)

    @property
    def size(self) -> int:
        """Return the number of focusable stops."""
        return len(self.entries)

    @property
    def is_empty(self) -> bool:
        """Return whether the trap has no focusable stops."""
        return not self.entries

    @property
    def current(self) -> FocusOrderEntry | None:
        """Return the currently focused stop."""
        if self.is_empty:
            return None
        return self.entries[self.index]

    @property
    def next_entry(self) -> FocusOrderEntry | None:
        """Return the stop reached by moving forward with wrapping."""
        if self.is_empty:
            return None
        return self.entries[(self.index + 1) % self.size]

    @property
    def previous_entry(self) -> FocusOrderEntry | None:
        """Return the stop reached by moving backward with wrapping."""
        if self.is_empty:
            return None
        return self.entries[(self.index - 1) % self.size]

    def move(self, direction: FocusDirection, *, wrap: bool = True) -> FocusTrap:
        """Return the trap after one step in ``direction``."""
        if self.is_empty:
            return self
        target = self.index + direction.delta
        if target < 0 or target >= self.size:
            if not wrap:
                return self
            target %= self.size
        return FocusTrap(self.entries, target)

    def next(self, *, wrap: bool = True) -> FocusTrap:
        """Move the focus to the following stop."""
        return self.move(FocusDirection.NEXT, wrap=wrap)

    def previous(self, *, wrap: bool = True) -> FocusTrap:
        """Move the focus to the preceding stop."""
        return self.move(FocusDirection.PREVIOUS, wrap=wrap)

    def move_to(self, entry_id: str) -> FocusTrap:
        """Focus the stop with the given identifier."""
        for index, entry in enumerate(self.entries):
            if entry.id == entry_id:
                return FocusTrap(self.entries, index)
        raise ValueError(f"unknown focus entry {entry_id!r}")

    def reset(self) -> FocusTrap:
        """Return a trap focused on the first stop."""
        return FocusTrap(self.entries, 0)


def sort_issues(
    issues: Iterable[A11yIssue],
    *,
    resolved_last: bool = True,
    newest_first: bool = True,
) -> list[A11yIssue]:
    """Order issues by severity, resolution state and detection time."""

    def detected(issue: A11yIssue) -> float:
        """Return the UTC timestamp used as the recency tie breaker."""
        return ensure_utc(issue.detected_at).timestamp()

    def key(issue: A11yIssue) -> tuple[int, int, float, str, str]:
        time_part = -detected(issue) if newest_first else detected(issue)
        resolved_part = int(issue.is_resolved) if resolved_last else 0
        return (
            -issue.severity.weight,
            resolved_part,
            time_part,
            issue.path,
            issue.id,
        )

    return sorted(issues, key=key)


@dataclass(frozen=True, slots=True)
class AccessibilityStats:
    """Aggregated counters rendered on the accessibility overview."""

    total_issues: int = 0
    open_issues: int = 0
    resolved_issues: int = 0
    critical_open: int = 0
    warning_open: int = 0
    info_open: int = 0
    shortcut_count: int = 0
    focus_entry_count: int = 0
    scopes: tuple[str, ...] = ()
    severity_counts: dict[str, int] = field(default_factory=dict)

    @property
    def resolution_rate(self) -> float:
        """Return the fraction of issues that have been resolved."""
        if self.total_issues == 0:
            return 0.0
        return round(self.resolved_issues / self.total_issues, 4)

    @property
    def risk_score(self) -> int:
        """Return a weighted open-issue score used by the UI summary."""
        return self.critical_open * 5 + self.warning_open * 2 + self.info_open
