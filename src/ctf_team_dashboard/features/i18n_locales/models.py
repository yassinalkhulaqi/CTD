"""Domain model of the internationalisation feature.

The objects in this module are immutable and depend on no framework. They
encode the rules that the rest of the feature reuses: locale code parsing,
fallback chains, bidirectional text detection, plural selection, placeholder
interpolation and the two formatting pattern languages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from ctf_team_dashboard.domain.models import utcnow

DEFAULT_LOCALE = "en"

_CODE_PATTERN = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_PLACEHOLDER_PATTERN = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})")
_NUMBER_PATTERN = re.compile(r"^[#,0]+(?:\.0+)?$")
_DATE_TOKEN_PATTERN = re.compile(r"YYYY|YY|MMMM|MMM|MM|DD")

RTL_LANGUAGES: frozenset[str] = frozenset(
    {
        "ar",
        "arc",
        "ckb",
        "dv",
        "fa",
        "he",
        "ku",
        "ps",
        "sd",
        "ug",
        "ur",
        "yi",
    }
)

MONTH_NAMES: dict[str, tuple[str, ...]] = {
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "fr": (
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ),
    "de": (
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ),
}

DEFAULT_NUMBER_PATTERN = "#,##0.00"
DEFAULT_DATE_PATTERN = "YYYY-MM-DD"

_DEFAULT_FORMATS: dict[str, tuple[str, str]] = {
    "en": ("#,##0.00", "MM/DD/YYYY"),
    "fr": ("#,##0.00", "DD/MM/YYYY"),
    "de": ("#,##0.00", "DD.MM.YYYY"),
    "ar": ("#,##0.00", "DD/MM/YYYY"),
    "ja": ("#,##0", "YYYY/MM/DD"),
    "zh": ("#,##0", "YYYY/MM/DD"),
}


class TextDirection(str, Enum):
    """Writing direction of a locale."""

    LTR = "ltr"
    RTL = "rtl"


class PluralRule(str, Enum):
    """Named plural rule families used to choose a message variant."""

    NONE = "none"
    SIMPLE = "simple"
    SLAVIC = "slavic"
    ARABIC = "arabic"


class PluralCategory(str, Enum):
    """CLDR style plural categories."""

    ZERO = "zero"
    ONE = "one"
    TWO = "two"
    FEW = "few"
    MANY = "many"
    OTHER = "other"


class TranslationSource(str, Enum):
    """Where the value of a translation was found."""

    EXACT = "exact"
    PLURAL = "plural"
    BASE = "base"
    DEFAULT = "default"
    MISSING = "missing"


class FormatKind(str, Enum):
    """The two kinds of formatted values."""

    NUMBER = "number"
    DATE = "date"


@dataclass(frozen=True, slots=True)
class LocaleCode:
    """The parsed components of a BCP-47 style locale identifier."""

    raw: str
    language: str
    script: str = ""
    region: str = ""

    @property
    def base(self) -> str:
        """Return the lowercase primary language subtag."""
        return self.language

    @property
    def canonical(self) -> str:
        """Return the normalised code with a title case script and upper region."""
        parts = [self.language]
        if self.script:
            parts.append(self.script.capitalize())
        if self.region:
            parts.append(self.region.upper() if len(self.region) == 2 else self.region)
        return "-".join(parts)

    @property
    def subtags(self) -> tuple[str, ...]:
        """Return every subtag in canonical order."""
        return tuple(part for part in (self.language, self.script, self.region) if part)


def parse_locale_code(code: str) -> LocaleCode:
    """Parse and validate a locale identifier.

    Args:
        code: An identifier such as ``en``, ``fr-CA`` or ``zh-Hant-TW``.

    Returns:
        The parsed components of the identifier.

    Raises:
        ValueError: When the identifier is empty or malformed.
    """
    candidate = code.strip()
    if not candidate or not _CODE_PATTERN.fullmatch(candidate):
        raise ValueError(f"invalid locale code: {code!r}")
    parts = candidate.split("-")
    language = parts[0].lower()
    script = ""
    region = ""
    for part in parts[1:]:
        if len(part) == 4 and part.isalpha():
            script = part.lower()
        elif len(part) == 2 and part.isalpha():
            region = part.lower()
        elif len(part) == 3 and part.isdigit():
            region = part
        else:
            raise ValueError(f"invalid locale subtag: {part!r}")
    return LocaleCode(raw=candidate, language=language, script=script, region=region)


def base_language(code: str) -> str:
    """Return the primary language subtag of ``code``."""
    return parse_locale_code(code).base


def is_rtl_language(code: str) -> bool:
    """Return whether the language of ``code`` is written right to left."""
    return base_language(code) in RTL_LANGUAGES


def direction_for(code: str) -> TextDirection:
    """Return the writing direction implied by a locale code."""
    return TextDirection.RTL if is_rtl_language(code) else TextDirection.LTR


def fallback_chain(code: str, default: str = DEFAULT_LOCALE) -> tuple[str, ...]:
    """Build the locale fallback chain used during message lookup.

    The requested code is tried first, then its base language, then the
    configured default locale. Duplicate entries are removed while preserving
    order.

    Args:
        code: The requested locale identifier.
        default: The final fallback locale.

    Returns:
        An ordered, de-duplicated tuple of locale identifiers.
    """
    parsed = parse_locale_code(code)
    candidates = [code.strip(), parsed.base, default.strip()]
    chain: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.lower()
        if candidate and key not in seen:
            seen.add(key)
            chain.append(candidate)
    return tuple(chain)


def plural_category(rule: PluralRule, count: int) -> PluralCategory:
    """Return the plural category selected by ``rule`` for ``count``."""
    value = abs(int(count))
    if rule is PluralRule.NONE:
        return PluralCategory.OTHER
    if rule is PluralRule.SIMPLE:
        return PluralCategory.ONE if value == 1 else PluralCategory.OTHER
    if rule is PluralRule.ARABIC:
        last_two = value % 100
        if value == 0:
            return PluralCategory.ZERO
        if last_two == 1:
            return PluralCategory.ONE
        if last_two == 2:
            return PluralCategory.TWO
        if 3 <= last_two <= 10:
            return PluralCategory.FEW
        if 11 <= last_two <= 99:
            return PluralCategory.MANY
        return PluralCategory.OTHER
    last_digit = value % 10
    last_two = value % 100
    if last_digit == 1 and last_two != 11:
        return PluralCategory.ONE
    if 2 <= last_digit <= 4 and not 12 <= last_two <= 14:
        return PluralCategory.FEW
    return PluralCategory.MANY


def plural_key(key: str, category: PluralCategory) -> str:
    """Return the message key holding the variant for ``category``."""
    return f"{key}.{category.value}"


def extract_placeholders(template: str) -> tuple[str, ...]:
    """Return the placeholder names referenced by ``template`` in order."""
    found: list[str] = []
    for match in _PLACEHOLDER_PATTERN.finditer(template):
        name = match.group(1)
        if name not in found:
            found.append(name)
    return tuple(found)


@dataclass(frozen=True, slots=True)
class Interpolation:
    """The outcome of rendering a message template."""

    value: str
    applied: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """Return whether every placeholder received a value."""
        return not self.missing


def interpolate(template: str, values: dict[str, object] | None = None) -> Interpolation:
    """Replace ``{name}`` placeholders with the supplied values.

    Doubled braces are unescaped to literal braces and placeholders without a
    supplied value are left intact so translators can spot them easily.

    Args:
        template: The message template.
        values: Mapping of placeholder name to replacement value.

    Returns:
        The rendered text together with the applied and missing names.
    """
    provided = values or {}
    applied: list[str] = []
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in provided:
            if name not in applied:
                applied.append(name)
            return str(provided[name])
        if name not in missing:
            missing.append(name)
        return match.group(0)

    rendered = _PLACEHOLDER_PATTERN.sub(replace, template)
    rendered = rendered.replace("{{", "\x00").replace("}}", "\x01")
    rendered = rendered.replace("\x00", "{").replace("\x01", "}")
    return Interpolation(rendered, tuple(applied), tuple(missing))


def validate_number_pattern(pattern: str) -> str:
    """Validate a number pattern and return its stripped form."""
    candidate = pattern.strip()
    if not candidate or not _NUMBER_PATTERN.fullmatch(candidate) or "0" not in candidate:
        raise ValueError(f"invalid number pattern: {pattern!r}")
    return candidate


def format_number(value: float, pattern: str = DEFAULT_NUMBER_PATTERN) -> str:
    """Format a number using ``#,##0.00`` style patterns."""
    validated = validate_number_pattern(pattern)
    decimals = len(validated.split(".", 1)[1]) if "." in validated else 0
    grouped = "," in validated
    quantum = Decimal(1).scaleb(-decimals)
    rounded = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)
    if grouped:
        return f"{rounded:,.{decimals}f}"
    return f"{rounded:.{decimals}f}"


def validate_date_pattern(pattern: str) -> str:
    """Validate a date pattern and return its stripped form."""
    candidate = pattern.strip()
    if not candidate:
        raise ValueError("date pattern must not be empty")
    unknown = re.sub(r"YYYY|YY|MMMM|MMM|MM|DD|[^A-Za-z]", "", candidate)
    if unknown:
        raise ValueError(f"unsupported date pattern token: {unknown!r}")
    return candidate


def month_name(locale: str, month: int, *, abbreviated: bool = False) -> str:
    """Return a localised month name with an English fallback."""
    names = MONTH_NAMES.get(base_language(locale), MONTH_NAMES["en"])
    index = min(11, max(0, month - 1))
    name = names[index]
    return name[:3] if abbreviated else name


def format_date(
    value: str | date | datetime,
    pattern: str = DEFAULT_DATE_PATTERN,
    locale: str = DEFAULT_LOCALE,
) -> str:
    """Format an ISO date string or date object using pattern tokens.

    Supported tokens are ``YYYY``, ``YY``, ``MMMM``, ``MMM``, ``MM`` and
    ``DD``. Literal separators are copied through unchanged.
    """
    validated = validate_date_pattern(pattern)
    if isinstance(value, datetime):
        moment = value.date()
    elif isinstance(value, date):
        moment = value
    else:
        try:
            moment = date.fromisoformat(value.strip()[:10])
        except ValueError as error:
            raise ValueError(f"invalid date: {value!r}") from error

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if token == "YYYY":
            return f"{moment.year:04d}"
        if token == "YY":
            return f"{moment.year % 100:02d}"
        if token == "MMMM":
            return month_name(locale, moment.month)
        if token == "MMM":
            return month_name(locale, moment.month, abbreviated=True)
        if token == "MM":
            return f"{moment.month:02d}"
        return f"{moment.day:02d}"

    return _DATE_TOKEN_PATTERN.sub(replace, validated)


@dataclass(frozen=True, slots=True)
class Locale:
    """A registered language variant with its typographic rules."""

    code: str
    name: str
    direction: TextDirection = TextDirection.LTR
    plural_rules: PluralRule = PluralRule.SIMPLE
    created_at: datetime = field(default_factory=utcnow)

    @property
    def base_language(self) -> str:
        """Return the primary language subtag."""
        return base_language(self.code)

    @property
    def canonical_code(self) -> str:
        """Return the normalised locale identifier."""
        return parse_locale_code(self.code).canonical

    @property
    def is_rtl(self) -> bool:
        """Return whether the locale is right to left."""
        return self.direction is TextDirection.RTL

    def fallback_chain(self, default: str = DEFAULT_LOCALE) -> tuple[str, ...]:
        """Return the fallback chain starting at this locale."""
        return fallback_chain(self.code, default)

    def category_for(self, count: int) -> PluralCategory:
        """Return the plural category of ``count`` under this locale."""
        return plural_category(self.plural_rules, count)

    def label(self) -> str:
        """Return a display label combining the name and code."""
        return f"{self.name} ({self.code})"


@dataclass(frozen=True, slots=True)
class Message:
    """A translated string stored for one locale, namespace and key."""

    id: str
    locale: str
    namespace: str
    key: str
    value: str
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def qualified_key(self) -> str:
        """Return the fully qualified ``namespace:key`` identifier."""
        return f"{self.namespace}:{self.key}"

    @property
    def placeholders(self) -> tuple[str, ...]:
        """Return the placeholders referenced by the value."""
        return extract_placeholders(self.value)

    @property
    def is_empty(self) -> bool:
        """Return whether the message has no translation content."""
        return not self.value.strip()

    def matches(self, locale: str, namespace: str, key: str) -> bool:
        """Return whether the message matches a lookup triple."""
        return (
            self.locale.lower() == locale.lower()
            and self.namespace == namespace
            and self.key == key
        )

    def render(self, values: dict[str, object] | None = None) -> Interpolation:
        """Render the message with the supplied placeholder values."""
        return interpolate(self.value, values)

    def with_value(self, value: str) -> Message:
        """Return a copy of the message carrying a new value."""
        return Message(
            id=self.id,
            locale=self.locale,
            namespace=self.namespace,
            key=self.key,
            value=value,
            updated_at=utcnow(),
        )


@dataclass(frozen=True, slots=True)
class FormatRule:
    """Number and date patterns attached to a locale."""

    locale: str
    number_pattern: str = DEFAULT_NUMBER_PATTERN
    date_pattern: str = DEFAULT_DATE_PATTERN
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        object.__setattr__(self, "number_pattern", validate_number_pattern(self.number_pattern))
        object.__setattr__(self, "date_pattern", validate_date_pattern(self.date_pattern))

    def number(self, value: float) -> str:
        """Format ``value`` with the number pattern."""
        return format_number(value, self.number_pattern)

    def date(self, value: str | date | datetime) -> str:
        """Format ``value`` with the date pattern."""
        return format_date(value, self.date_pattern, self.locale)

    def number_example(self) -> str:
        """Return a representative formatted number."""
        return self.number(1234567.891)

    def date_example(self) -> str:
        """Return a representative formatted date."""
        return self.date("2026-11-20")


def default_format_rule(locale: str) -> FormatRule:
    """Return a sensible default rule for a locale code."""
    number, date_pattern = _DEFAULT_FORMATS.get(
        base_language(locale), (DEFAULT_NUMBER_PATTERN, DEFAULT_DATE_PATTERN)
    )
    return FormatRule(locale=locale, number_pattern=number, date_pattern=date_pattern)


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """The resolved value of a translation request."""

    key: str
    locale: str
    resolved_locale: str
    value: str
    source: TranslationSource
    variant: str
    applied: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    plural_category: PluralCategory | None = None

    @property
    def found(self) -> bool:
        """Return whether a catalogue entry supplied the value."""
        return self.source is not TranslationSource.MISSING

    @property
    def used_fallback(self) -> bool:
        """Return whether the value came from another locale."""
        return self.source in (TranslationSource.BASE, TranslationSource.DEFAULT)

    @property
    def interpolated(self) -> bool:
        """Return whether at least one placeholder was substituted."""
        return bool(self.applied)

    @property
    def complete(self) -> bool:
        """Return whether every placeholder was substituted."""
        return not self.missing

    @property
    def display_value(self) -> str:
        """Return the value suitable for display, including miss markers."""
        if not self.found:
            return f"[{self.key}]"
        return self.value


@dataclass(frozen=True, slots=True)
class CompletenessStat:
    """Translation completeness of one locale within one namespace."""

    locale: str
    namespace: str
    reference: str
    total: int
    translated: int
    missing_keys: tuple[str, ...] = ()

    @property
    def missing(self) -> int:
        """Return the number of untranslated keys."""
        return max(0, self.total - self.translated)

    @property
    def percent(self) -> float:
        """Return the completeness percentage rounded to one decimal."""
        if self.total <= 0:
            return 0.0
        return round(self.translated / self.total * 100, 1)

    @property
    def is_complete(self) -> bool:
        """Return whether every reference key was translated."""
        return self.total > 0 and self.translated >= self.total

    def describe(self) -> str:
        """Return a short human readable summary."""
        return f"{self.locale}/{self.namespace}: {self.percent:.1f}%"


@dataclass(frozen=True, slots=True)
class MissingKey:
    """A reference key that has no translation in the target locale."""

    locale: str
    namespace: str
    key: str
    reference_value: str
    resolved_locale: str | None = None

    @property
    def qualified_key(self) -> str:
        """Return the fully qualified missing key."""
        return f"{self.namespace}:{self.key}"

    @property
    def has_fallback(self) -> bool:
        """Return whether another locale supplies a fallback value."""
        return self.resolved_locale is not None


@dataclass(frozen=True, slots=True)
class FormatResult:
    """The outcome of a formatting request."""

    locale: str
    kind: FormatKind
    input: str
    output: str
    pattern: str

    @property
    def changed(self) -> bool:
        """Return whether formatting changed the raw input."""
        return self.output != self.input


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    """An aggregate view over the locale catalogue."""

    locales: tuple[Locale, ...] = ()
    messages: tuple[Message, ...] = ()

    @property
    def locale_count(self) -> int:
        """Return the number of registered locales."""
        return len(self.locales)

    @property
    def message_count(self) -> int:
        """Return the number of stored messages."""
        return len(self.messages)

    @property
    def rtl_codes(self) -> tuple[str, ...]:
        """Return the codes of right to left locales."""
        return tuple(item.code for item in self.locales if item.is_rtl)

    def namespaces(self) -> tuple[str, ...]:
        """Return the sorted distinct namespaces in the catalogue."""
        return tuple(sorted({item.namespace for item in self.messages}))
