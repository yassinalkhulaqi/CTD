"""Domain models and pure helpers for the report studio.

The reporting feature has three persisted entities (templates, reports and
export jobs) and a small set of immutable rendering value objects. All of the
logic in this module is side-effect free so it can be exercised directly in
unit tests before any database or HTTP layer is involved.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ctf_team_dashboard.domain.models import utcnow


class ReportFormat(str, Enum):
    """Serialisation formats supported by the export pipeline."""

    MARKDOWN = "markdown"
    CSV = "csv"
    JSON = "json"
    HTML = "html"

    @classmethod
    def parse(cls, value: str | ReportFormat, default: ReportFormat | None = None) -> ReportFormat:
        """Parse a format, falling back to ``default`` for unknown values."""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            if default is not None:
                return default
            raise ReportValueError(f"Unsupported report format: {value}") from None


class ReportStatus(str, Enum):
    """Lifecycle state of a report."""

    DRAFT = "draft"
    FINAL = "final"

    @classmethod
    def parse(cls, value: str | ReportStatus, default: ReportStatus | None = None) -> ReportStatus:
        """Parse a status, falling back to ``default`` for unknown values."""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            if default is not None:
                return default
            raise ReportValueError(f"Unsupported report status: {value}") from None


class TemplateScope(str, Enum):
    """Audience a template was designed for."""

    TEAM = "team"
    EVENT = "event"
    GLOBAL = "global"

    @classmethod
    def parse(
        cls, value: str | TemplateScope, default: TemplateScope | None = None
    ) -> TemplateScope:
        """Parse a scope, falling back to ``default`` for unknown values."""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            if default is not None:
                return default
            raise ReportValueError(f"Unsupported template scope: {value}") from None


class SectionKind(str, Enum):
    """How a template section obtains and displays its content."""

    TEXT = "text"
    TABLE = "table"
    LIST = "list"
    METRICS = "metrics"

    @classmethod
    def parse(cls, value: str | SectionKind, default: SectionKind | None = None) -> SectionKind:
        """Parse a section kind, falling back to ``default`` for unknown values."""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            if default is not None:
                return default
            raise ReportValueError(f"Unsupported section kind: {value}") from None


class ExportStatus(str, Enum):
    """State of an export job."""

    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"

    @classmethod
    def parse(cls, value: str | ExportStatus, default: ExportStatus | None = None) -> ExportStatus:
        """Parse an export status, falling back to ``default`` for unknown values."""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            if default is not None:
                return default
            raise ReportValueError(f"Unsupported export status: {value}") from None


class ReportValueError(ValueError):
    """Local value error converted to a domain error by the service layer."""


PLACEHOLDER_RE = re.compile(
    r"\{\{\s*([A-Za-z0-9_.-]+)(?:\s*\|\|\s*([^{}]*?))?\s*\}\}",
    re.MULTILINE,
)
MISSING = object()


@dataclass(frozen=True, slots=True)
class ReportSection:
    """One configurable block inside a report template."""

    id: str
    title: str = "Section"
    kind: SectionKind = SectionKind.TEXT
    body: str = ""
    source: str = ""
    columns: tuple[str, ...] = ()
    enabled: bool = True
    order: int = 0

    @property
    def label(self) -> str:
        """Return a human readable label for editor lists."""
        return self.title.strip() or "Untitled section"

    @property
    def placeholder_tokens(self) -> tuple[str, ...]:
        """Return the placeholder names referenced by the section."""
        return collect_placeholders((self.title, self.body, self.source))

    def updated(
        self,
        *,
        title: str | None = None,
        kind: SectionKind | None = None,
        body: str | None = None,
        source: str | None = None,
        columns: tuple[str, ...] | None = None,
        enabled: bool | None = None,
        order: int | None = None,
    ) -> ReportSection:
        """Return a copy with the supplied fields replaced."""
        return ReportSection(
            id=self.id,
            title=self.title if title is None else title,
            kind=self.kind if kind is None else kind,
            body=self.body if body is None else body,
            source=self.source if source is None else source,
            columns=self.columns if columns is None else columns,
            enabled=self.enabled if enabled is None else enabled,
            order=self.order if order is None else order,
        )

    def to_mapping(self) -> dict[str, Any]:
        """Return the JSON serialisable representation of the section."""
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind.value,
            "body": self.body,
            "source": self.source,
            "columns": list(self.columns),
            "enabled": self.enabled,
            "order": self.order,
        }


@dataclass(frozen=True, slots=True)
class ReportTemplate:
    """A reusable arrangement of report sections."""

    id: str
    name: str
    sections_json: str
    format: ReportFormat = ReportFormat.MARKDOWN
    scope: TemplateScope = TemplateScope.TEAM
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def sections(self) -> tuple[ReportSection, ...]:
        """Return the parsed sections in display order."""
        return parse_sections(self.sections_json)

    @property
    def enabled_sections(self) -> tuple[ReportSection, ...]:
        """Return only the sections that participate in rendering."""
        return tuple(section for section in self.sections if section.enabled)

    @property
    def section_count(self) -> int:
        """Return the total number of configured sections."""
        return len(self.sections)

    @property
    def is_empty(self) -> bool:
        """Return whether the template has no enabled sections."""
        return not self.enabled_sections

    @property
    def description(self) -> str:
        """Return a short summary used by pickers and lists."""
        kinds = ", ".join(sorted({section.kind.value for section in self.enabled_sections}))
        if not kinds:
            return "No enabled sections"
        return f"{len(self.enabled_sections)} sections · {kinds}"

    def with_sections(self, sections: Sequence[ReportSection]) -> ReportTemplate:
        """Return a copy carrying a new section configuration."""
        return ReportTemplate(
            id=self.id,
            name=self.name,
            sections_json=dump_sections(sections),
            format=self.format,
            scope=self.scope,
            updated_at=utcnow(),
        )


@dataclass(frozen=True, slots=True)
class Report:
    """A report instance created from a template for a concrete scope."""

    id: str
    template_id: str
    title: str
    scope_id: str
    status: ReportStatus = ReportStatus.DRAFT
    created_at: datetime = field(default_factory=utcnow)
    data_json: str = "{}"

    @property
    def is_final(self) -> bool:
        """Return whether the report has been finalised."""
        return self.status is ReportStatus.FINAL

    @property
    def is_draft(self) -> bool:
        """Return whether the report is still editable."""
        return self.status is ReportStatus.DRAFT

    @property
    def data(self) -> dict[str, Any]:
        """Return the captured data snapshot used for rendering."""
        return parse_data(self.data_json)

    def with_status(self, status: ReportStatus) -> Report:
        """Return a copy with a different lifecycle status."""
        return Report(
            id=self.id,
            template_id=self.template_id,
            title=self.title,
            scope_id=self.scope_id,
            status=status,
            created_at=self.created_at,
            data_json=self.data_json,
        )


@dataclass(frozen=True, slots=True)
class ExportJob:
    """A materialised export of one report."""

    id: str
    report_id: str
    format: ReportFormat
    status: ExportStatus
    content: str
    created_at: datetime = field(default_factory=utcnow)

    @property
    def byte_size(self) -> int:
        """Return the UTF-8 size of the rendered content."""
        return len(self.content.encode("utf-8"))

    @property
    def line_count(self) -> int:
        """Return the number of lines in the rendered content."""
        if not self.content:
            return 0
        return len(self.content.splitlines())

    @property
    def extension(self) -> str:
        """Return the conventional file extension of the export."""
        return FORMAT_EXTENSIONS[self.format]

    @property
    def mime_type(self) -> str:
        """Return the MIME type used when downloading the export."""
        return FORMAT_MIME_TYPES[self.format]

    @property
    def is_complete(self) -> bool:
        """Return whether the export produced content."""
        return self.status is ExportStatus.COMPLETE and bool(self.content)


FORMAT_EXTENSIONS: dict[ReportFormat, str] = {
    ReportFormat.MARKDOWN: "md",
    ReportFormat.CSV: "csv",
    ReportFormat.JSON: "json",
    ReportFormat.HTML: "html",
}
FORMAT_MIME_TYPES: dict[ReportFormat, str] = {
    ReportFormat.MARKDOWN: "text/markdown",
    ReportFormat.CSV: "text/csv",
    ReportFormat.JSON: "application/json",
    ReportFormat.HTML: "text/html",
}


@dataclass(frozen=True, slots=True)
class SubstitutionResult:
    """The outcome of substituting placeholders into a string."""

    text: str
    resolved: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        """Return whether every placeholder was resolved."""
        return not self.missing


@dataclass(frozen=True, slots=True)
class RenderedSection:
    """Structured content of one rendered section."""

    id: str
    title: str
    kind: SectionKind
    text: str
    columns: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    items: tuple[str, ...] = ()
    metrics: tuple[tuple[str, str], ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def row_count(self) -> int:
        """Return the number of rendered records in the section."""
        if self.kind is SectionKind.METRICS:
            return len(self.metrics)
        if self.kind is SectionKind.LIST:
            return len(self.items)
        return len(self.rows)

    @property
    def is_empty(self) -> bool:
        """Return whether the section has no content beyond its title."""
        return not self.text and self.row_count == 0


@dataclass(frozen=True, slots=True)
class RenderedReport:
    """A report expanded against a data snapshot, ready for serialisation."""

    title: str
    format: ReportFormat
    generated_at: datetime
    sections: tuple[RenderedSection, ...]
    summary: dict[str, int]
    meta: dict[str, str]
    warnings: tuple[str, ...] = ()

    @property
    def section_count(self) -> int:
        """Return the number of rendered sections."""
        return len(self.sections)

    @property
    def total_rows(self) -> int:
        """Return the total number of records rendered across all sections."""
        return sum(section.row_count for section in self.sections)

    @property
    def has_warnings(self) -> bool:
        """Return whether any placeholder or section could not be resolved."""
        return bool(self.warnings)

    @property
    def is_empty(self) -> bool:
        """Return whether no section produced any data."""
        return all(section.is_empty for section in self.sections)


@dataclass(frozen=True, slots=True)
class ExportPayload:
    """Serialised report content plus its delivery metadata."""

    content: str
    format: ReportFormat
    title: str
    mime_type: str
    extension: str
    byte_size: int
    line_count: int
    filename: str


@dataclass(frozen=True, slots=True)
class ReportStats:
    """Aggregated counters for the report studio overview."""

    templates: int = 0
    reports: int = 0
    draft_reports: int = 0
    final_reports: int = 0
    exports: int = 0
    exports_by_format: dict[str, int] = field(default_factory=dict)

    @property
    def total_artifacts(self) -> int:
        """Return the number of stored templates, reports and exports."""
        return self.templates + self.reports + self.exports

    @property
    def finalisation_rate(self) -> float:
        """Return the fraction of reports that reached the final state."""
        if self.reports == 0:
            return 0.0
        return self.final_reports / self.reports

    def exports_of(self, report_format: ReportFormat) -> int:
        """Return the number of exports produced in one format."""
        return self.exports_by_format.get(report_format.value, 0)


def stringify_value(value: Any) -> str:
    """Convert a data value into a compact, human readable string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(stringify_value(item) for item in value)
    if isinstance(value, Mapping):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def lookup_value(data: Mapping[str, Any], path: str) -> Any:
    """Resolve a dotted path inside nested mappings, returning ``MISSING`` on failure."""
    current: Any = data
    for part in path.split("."):
        key = part.strip()
        if not isinstance(current, Mapping) or key not in current:
            return MISSING
        current = current[key]
    return current


def substitute_placeholders(text: str, data: Mapping[str, Any]) -> SubstitutionResult:
    """Replace ``{{ key || fallback }}`` tokens using the supplied data mapping.

    A token is resolved when the dotted key exists and is non-empty. Missing
    tokens are reported so previews can warn the author without losing content.
    """
    if not text:
        return SubstitutionResult("", (), ())
    resolved: list[str] = []
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        token = match.group(1)
        fallback = match.group(2)
        value = lookup_value(data, token)
        if value is MISSING or value is None or value == "":
            missing.append(token)
            return "" if fallback is None else fallback.strip()
        resolved.append(token)
        return stringify_value(value)

    return SubstitutionResult(PLACEHOLDER_RE.sub(replace, text), tuple(resolved), tuple(missing))


def collect_placeholders(values: Iterable[str]) -> tuple[str, ...]:
    """Return every unique placeholder token found in the supplied strings."""
    found: list[str] = []
    seen: set[str] = set()
    for value in values:
        for match in PLACEHOLDER_RE.finditer(value or ""):
            token = match.group(1)
            if token not in seen:
                seen.add(token)
                found.append(token)
    return tuple(found)


def summary_counts(data: Mapping[str, Any]) -> dict[str, int]:
    """Derive display counts from the collections and numbers in a data snapshot."""
    counts: dict[str, int] = {}
    for key in sorted(data):
        value = data[key]
        if isinstance(value, bool):
            continue
        if isinstance(value, (list, tuple, set, Mapping)):
            counts[key] = len(value)
        elif isinstance(value, (int, float)):
            counts[key] = int(value)
    return counts


def parse_data(raw: str | None) -> dict[str, Any]:
    """Parse a JSON object snapshot, returning an empty dict for invalid input."""
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, dict):
        return {}
    return {str(key): value for key, value in decoded.items()}


def dump_data(data: Mapping[str, Any]) -> str:
    """Serialise a data snapshot with stable key ordering."""
    return json.dumps(dict(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def section_from_mapping(raw: Mapping[str, Any], index: int = 0) -> ReportSection:
    """Build a section from an untrusted mapping, applying sensible defaults."""
    identifier = raw.get("id")
    title = raw.get("title")
    body = raw.get("body")
    source = raw.get("source")
    columns = raw.get("columns")
    order = raw.get("order", index)
    try:
        parsed_order = int(order)
    except (TypeError, ValueError):
        parsed_order = index
    return ReportSection(
        id=str(identifier).strip() or f"section-{index + 1}",
        title=str(title).strip() if title is not None else f"Section {index + 1}",
        kind=SectionKind.parse(raw.get("kind", "text"), SectionKind.TEXT),
        body="" if body is None else str(body),
        source="" if source is None else str(source),
        columns=(
            tuple(str(column) for column in columns if str(column).strip())
            if isinstance(columns, (list, tuple))
            else ()
        ),
        enabled=bool(raw.get("enabled", True)),
        order=parsed_order,
    )


def parse_sections(raw: str | None) -> tuple[ReportSection, ...]:
    """Parse a stored ``sections_json`` value into ordered domain sections."""
    if not raw:
        return ()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    if not isinstance(decoded, list):
        return ()
    sections = [
        section_from_mapping(item, index)
        for index, item in enumerate(decoded)
        if isinstance(item, Mapping)
    ]
    return tuple(sorted(sections, key=lambda section: (section.order, section.id)))


def dump_sections(sections: Sequence[ReportSection]) -> str:
    """Serialise sections to the JSON representation stored in the database."""
    return json.dumps([section.to_mapping() for section in sections], ensure_ascii=False)


def slugify(value: str) -> str:
    """Convert a title into a lowercase, filesystem-safe slug."""
    slug: list[str] = []
    previous_separator = False
    for character in value.lower().strip():
        if character.isalnum():
            slug.append(character)
            previous_separator = False
        elif not previous_separator:
            slug.append("-")
            previous_separator = True
    return "".join(slug).strip("-") or "report"


def export_filename(title: str, report_format: ReportFormat) -> str:
    """Build a deterministic download filename for an export."""
    return f"{slugify(title)}.{FORMAT_EXTENSIONS[report_format]}"


def truncate(text: str, limit: int = 160) -> str:
    """Collapse whitespace and truncate a string for compact previews."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1]}…"
