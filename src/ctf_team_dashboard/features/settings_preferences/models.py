"""Domain models and pure helpers for settings preferences."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import utcnow

HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
TIMEZONE_RE = re.compile(r"^[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+$|^UTC$")
DATE_FORMATS = frozenset({"YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY", "MMM D, YYYY"})


class Density(StrEnum):
    """Supported workspace density modes."""

    COMPACT = "compact"
    COMFORTABLE = "comfortable"


class SidebarPosition(StrEnum):
    """Supported sidebar placement options."""

    LEFT = "left"
    RIGHT = "right"


class PreferenceValueType(StrEnum):
    """Allowed preference value types for schema validation."""

    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    ENUM = "enum"


@dataclass(frozen=True, slots=True)
class PreferenceField:
    """Schema declaration for a single preference key."""

    key: str
    value_type: PreferenceValueType
    default: Any
    label: str
    description: str
    choices: tuple[str, ...] = ()
    min_value: int | None = None
    max_value: int | None = None

    def coerce(self, value: Any) -> Any:
        """Coerce and validate a value against this field declaration."""
        if str(self.value_type) == PreferenceValueType.BOOLEAN.value:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes", "on"}:
                    return True
                if lowered in {"false", "0", "no", "off"}:
                    return False
            raise ValueError(f"{self.key} expects a boolean")

        if str(self.value_type) == PreferenceValueType.INTEGER.value:
            coerced: int
            if isinstance(value, bool):
                raise ValueError(f"{self.key} expects an integer")
            if isinstance(value, int):
                coerced = value
            elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
                coerced = int(value.strip())
            else:
                raise ValueError(f"{self.key} expects an integer")
            if self.min_value is not None and coerced < self.min_value:
                raise ValueError(f"{self.key} must be >= {self.min_value}")
            if self.max_value is not None and coerced > self.max_value:
                raise ValueError(f"{self.key} must be <= {self.max_value}")
            return coerced

        if str(self.value_type) == PreferenceValueType.STRING.value:
            if not isinstance(value, str):
                raise ValueError(f"{self.key} expects a string")
            cleaned = value.strip()
            if not cleaned:
                raise ValueError(f"{self.key} cannot be empty")
            return cleaned

        if str(self.value_type) == PreferenceValueType.ENUM.value:
            if not isinstance(value, str):
                raise ValueError(f"{self.key} expects one of {', '.join(self.choices)}")
            cleaned = value.strip().lower()
            if cleaned not in self.choices:
                raise ValueError(f"{self.key} expects one of {', '.join(self.choices)}")
            return cleaned

        raise ValueError(f"Unsupported type for {self.key}")


PREFERENCE_SCHEMA: tuple[PreferenceField, ...] = (
    PreferenceField(
        key="notifications.email",
        value_type=PreferenceValueType.BOOLEAN,
        default=True,
        label="Email notifications",
        description="Receive important updates by email.",
    ),
    PreferenceField(
        key="notifications.desktop",
        value_type=PreferenceValueType.BOOLEAN,
        default=False,
        label="Desktop notifications",
        description="Show browser desktop notifications.",
    ),
    PreferenceField(
        key="notifications.digest",
        value_type=PreferenceValueType.ENUM,
        default="daily",
        label="Digest frequency",
        description="How often summary digests are sent.",
        choices=("off", "daily", "weekly"),
    ),
    PreferenceField(
        key="appearance.theme",
        value_type=PreferenceValueType.ENUM,
        default="system",
        label="Theme mode",
        description="Preferred color scheme.",
        choices=("system", "light", "dark"),
    ),
    PreferenceField(
        key="appearance.accent",
        value_type=PreferenceValueType.ENUM,
        default="indigo",
        label="Accent color",
        description="Primary accent token.",
        choices=("indigo", "teal", "amber", "rose"),
    ),
    PreferenceField(
        key="workspace.autoSaveSeconds",
        value_type=PreferenceValueType.INTEGER,
        default=30,
        label="Autosave interval",
        description="Seconds between autosaves.",
        min_value=5,
        max_value=300,
    ),
    PreferenceField(
        key="workspace.showHints",
        value_type=PreferenceValueType.BOOLEAN,
        default=True,
        label="Show hints",
        description="Display contextual hints in workspace views.",
    ),
)

PREFERENCE_SCHEMA_BY_KEY: dict[str, PreferenceField] = {
    field.key: field for field in PREFERENCE_SCHEMA
}


def default_preferences() -> dict[str, Any]:
    """Return a copy of declared default preference values."""
    return {field.key: field.default for field in PREFERENCE_SCHEMA}


def validate_preference_key(key: str) -> PreferenceField:
    """Return schema field for key or raise ValueError."""
    field = PREFERENCE_SCHEMA_BY_KEY.get(key)
    if field is None:
        raise ValueError(f"Unknown preference key: {key}")
    return field


def coerce_preference_value(key: str, value: Any) -> Any:
    """Validate key and coerce value according to schema."""
    return validate_preference_key(key).coerce(value)


def merge_preferences(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge overrides over defaults, coercing values."""
    merged = default_preferences()
    for key, value in (overrides or {}).items():
        merged[key] = coerce_preference_value(key, value)
    return merged


def normalize_hex_color(value: str) -> str:
    """Normalize hex color to #RRGGBB uppercase form."""
    candidate = value.strip()
    if not HEX_COLOR_RE.match(candidate):
        raise ValueError(f"Invalid color token: {value}")
    if len(candidate) == 4:
        candidate = "#" + "".join(ch * 2 for ch in candidate[1:])
    return candidate.upper()


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Convert normalized #RRGGBB color to RGB tuple."""
    normalized = normalize_hex_color(color)
    return (
        int(normalized[1:3], 16),
        int(normalized[3:5], 16),
        int(normalized[5:7], 16),
    )


def _linearize(channel: int) -> float:
    scaled = channel / 255.0
    if scaled <= 0.03928:
        return scaled / 12.92
    return float(((scaled + 0.055) / 1.055) ** 2.4)


def relative_luminance(color: str) -> float:
    """Calculate WCAG relative luminance for a hex color."""
    r, g, b = hex_to_rgb(color)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(foreground: str, background: str) -> float:
    """Calculate WCAG contrast ratio between two colors."""
    l1 = relative_luminance(foreground)
    l2 = relative_luminance(background)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    ratio = (lighter + 0.05) / (darker + 0.05)
    return round(ratio, 2)


def passes_wcag(ratio: float, *, large_text: bool = False) -> bool:
    """Return whether contrast ratio meets WCAG AA for text size."""
    threshold = 3.0 if large_text else 4.5
    return ratio >= threshold


@dataclass(frozen=True, slots=True)
class Preference:
    """A persisted preference override for a user."""

    id: str
    user_id: str
    key: str
    value: Any
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def value_json(self) -> str:
        """Serialize value as JSON for storage."""
        return json.dumps(self.value, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class ThemeToken:
    """A named theme token value."""

    name: str
    value: str

    def normalized_value(self) -> str:
        """Return normalized token value."""
        return normalize_hex_color(self.value)


DEFAULT_THEME_TOKENS: tuple[ThemeToken, ...] = (
    ThemeToken("surface", "#FFFFFF"),
    ThemeToken("surfaceMuted", "#F1F5F9"),
    ThemeToken("textPrimary", "#0F172A"),
    ThemeToken("textMuted", "#475569"),
    ThemeToken("accent", "#4F46E5"),
    ThemeToken("accentText", "#FFFFFF"),
    ThemeToken("danger", "#DC2626"),
)


@dataclass(frozen=True, slots=True)
class ThemeTokenPairEvaluation:
    """Contrast evaluation for a foreground/background token pair."""

    foreground: str
    background: str
    ratio: float
    passes_aa: bool


def evaluate_theme_tokens(tokens: dict[str, str]) -> list[ThemeTokenPairEvaluation]:
    """Evaluate key UI token pairs for WCAG AA contrast."""
    pairs = (
        ("textPrimary", "surface"),
        ("textMuted", "surface"),
        ("accentText", "accent"),
        ("textPrimary", "surfaceMuted"),
    )
    evaluations: list[ThemeTokenPairEvaluation] = []
    for fg_name, bg_name in pairs:
        fg = tokens.get(fg_name)
        bg = tokens.get(bg_name)
        if not fg or not bg:
            continue
        ratio = contrast_ratio(fg, bg)
        evaluations.append(
            ThemeTokenPairEvaluation(
                foreground=fg_name,
                background=bg_name,
                ratio=ratio,
                passes_aa=passes_wcag(ratio),
            )
        )
    return evaluations


def validate_timezone(value: str) -> str:
    """Validate timezone string against supported simple IANA/UTC forms."""
    candidate = value.strip()
    if not candidate or not TIMEZONE_RE.match(candidate):
        raise ValueError("Invalid timezone")
    return candidate


def validate_date_format(value: str) -> str:
    """Validate date format against supported options."""
    candidate = value.strip()
    if candidate not in DATE_FORMATS:
        raise ValueError("Invalid date format")
    return candidate


@dataclass(frozen=True, slots=True)
class WorkspaceLayout:
    """Persisted workspace layout preferences for a user."""

    user_id: str
    density: Density = Density.COMFORTABLE
    sidebar_position: SidebarPosition = SidebarPosition.LEFT
    show_activity: bool = True
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    updated_at: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Serialize layout for API responses/export."""
        density = self.density.value if isinstance(self.density, StrEnum) else str(self.density)
        sidebar = (
            self.sidebar_position.value
            if isinstance(self.sidebar_position, StrEnum)
            else str(self.sidebar_position)
        )
        return {
            "user_id": self.user_id,
            "density": density,
            "sidebar_position": sidebar,
            "show_activity": self.show_activity,
            "timezone": self.timezone,
            "date_format": self.date_format,
            "updated_at": self.updated_at.isoformat(),
        }


def default_layout(user_id: str) -> WorkspaceLayout:
    """Return default layout for user."""
    return WorkspaceLayout(user_id=user_id)


def coerce_layout(
    user_id: str,
    *,
    density: Any = Density.COMFORTABLE,
    sidebar_position: Any = SidebarPosition.LEFT,
    show_activity: Any = True,
    timezone: Any = "UTC",
    date_format: Any = "YYYY-MM-DD",
) -> WorkspaceLayout:
    """Coerce and validate layout values."""
    try:
        density_value = Density.parse(str(density))
    except ValueError as exc:
        raise ValueError("Invalid density") from exc
    try:
        sidebar_value = SidebarPosition.parse(str(sidebar_position))
    except ValueError as exc:
        raise ValueError("Invalid sidebar position") from exc
    if not isinstance(show_activity, bool):
        if isinstance(show_activity, str) and show_activity.lower() in {"true", "false"}:
            show_activity = show_activity.lower() == "true"
        else:
            raise ValueError("show_activity must be boolean")
    tz = validate_timezone(str(timezone))
    fmt = validate_date_format(str(date_format))
    return WorkspaceLayout(
        user_id=user_id,
        density=density_value,
        sidebar_position=sidebar_value,
        show_activity=show_activity,
        timezone=tz,
        date_format=fmt,
    )


def layout_from_mapping(user_id: str, data: dict[str, Any]) -> WorkspaceLayout:
    """Build layout from partial mapping, using defaults."""
    base = default_layout(user_id)
    return coerce_layout(
        user_id,
        density=data.get("density", base.density.value),
        sidebar_position=data.get("sidebar_position", base.sidebar_position.value),
        show_activity=data.get("show_activity", base.show_activity),
        timezone=data.get("timezone", base.timezone),
        date_format=data.get("date_format", base.date_format),
    )


def parse_updated_at(raw: str | None) -> datetime:
    """Parse ISO timestamp from DB, defaulting to now."""
    if not raw:
        return utcnow()
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return utcnow()
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def clamp01(value: float) -> float:
    """Clamp float to [0,1] for score-like metrics."""
    return max(0.0, min(1.0, value))


def contrast_score(ratio: float) -> float:
    """Map contrast ratio to a 0-1 score for UI visualization."""
    # 21:1 max theoretical contrast; 4.5 is AA target.
    normalized = (ratio - 1.0) / 20.0
    return round(clamp01(normalized), 4)


def normalize_theme_tokens(tokens: dict[str, str]) -> dict[str, str]:
    """Normalize and validate theme token map."""
    normalized: dict[str, str] = {}
    for name, value in tokens.items():
        key = str(name).strip()
        if not key:
            raise ValueError("Token name cannot be empty")
        normalized[key] = normalize_hex_color(str(value))
    return normalized


def theme_tokens_to_map(tokens: list[ThemeToken]) -> dict[str, str]:
    """Convert token entities to map."""
    return {token.name: token.normalized_value() for token in tokens}


def ensure_required_theme_tokens(tokens: dict[str, str]) -> dict[str, str]:
    """Ensure all default theme tokens exist, filling missing with defaults."""
    merged = {token.name: token.value for token in DEFAULT_THEME_TOKENS}
    merged.update(normalize_theme_tokens(tokens))
    return merged
