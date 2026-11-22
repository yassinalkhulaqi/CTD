"""Pure rendering and serialisation for report exports.

Every function in this module accepts domain objects and returns strings, which
keeps the export pipeline deterministic and independent of the database. The
four writers deliberately share the same structured :class:`RenderedReport` so
that a preview shown in the browser matches the downloaded artefact.
"""

from __future__ import annotations

import html
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from ctf_team_dashboard.domain.models import ensure_utc

from .models import (
    FORMAT_EXTENSIONS,
    FORMAT_MIME_TYPES,
    ExportPayload,
    RenderedReport,
    RenderedSection,
    Report,
    ReportFormat,
    ReportSection,
    ReportTemplate,
    SectionKind,
    export_filename,
    stringify_value,
    substitute_placeholders,
    summary_counts,
)


def csv_cell(value: Any) -> str:
    """Escape one CSV cell, quoting values that contain delimiters or newlines."""
    text = stringify_value(value)
    if any(marker in text for marker in (",", '"', "\n", "\r")):
        return f'"{text.replace(chr(34), chr(34) * 2)}"'
    return text


def html_text(value: Any) -> str:
    """Escape text for safe inclusion in an HTML document."""
    return html.escape(stringify_value(value), quote=True)


def markdown_cell(value: Any) -> str:
    """Escape a value for use inside a Markdown table cell."""
    collapsed = " ".join(stringify_value(value).split())
    return collapsed.replace("\\", "\\\\").replace("|", "\\|")


def markdown_table(columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """Render a GitHub flavoured Markdown table."""
    if not columns:
        return ""
    header = "| " + " | ".join(markdown_cell(column) for column in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        cells = [
            markdown_cell(row[index]) if index < len(row) else "" for index in range(len(columns))
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def csv_lines(rows: Sequence[Sequence[Any]]) -> str:
    """Render rows as lines of escaped CSV."""
    return "\n".join(",".join(csv_cell(cell) for cell in row) for row in rows)


def html_table(columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """Render an accessible HTML table with a header row."""
    if not columns:
        return ""
    head = "".join(f'<th scope="col">{html_text(column)}</th>' for column in columns)
    body = []
    for row in rows:
        cells = [html_text(row[index]) if index < len(row) else "" for index in range(len(columns))]
        body.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def html_list(items: Sequence[str]) -> str:
    """Render an unordered HTML list."""
    if not items:
        return ""
    entries = "".join(f"<li>{html_text(item)}</li>" for item in items)
    return f"<ul>{entries}</ul>"


def markdown_list(items: Sequence[str]) -> str:
    """Render a Markdown bullet list."""
    return "\n".join(f"- {item.replace(chr(10), ' ')}" for item in items)


def rows_from_value(value: Any, columns: Sequence[str] = ()) -> tuple[tuple[str, ...], ...]:
    """Normalise a data value into tabular rows."""
    if isinstance(value, Mapping):
        return tuple((str(key), stringify_value(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        if not value:
            return ()
        if all(isinstance(item, Mapping) for item in value):
            mappings = [item for item in value if isinstance(item, Mapping)]
            chosen = tuple(columns)
            if not chosen:
                chosen = tuple(dict.fromkeys(key for item in mappings for key in item))
            return tuple(
                tuple(stringify_value(item.get(key, "")) for key in chosen) for item in mappings
            )
        return tuple((stringify_value(item),) for item in value)
    return ((stringify_value(value),),)


def columns_from_value(value: Any, columns: Sequence[str] = ()) -> tuple[str, ...]:
    """Derive table columns from a data value when none were configured."""
    if columns:
        return tuple(columns)
    if isinstance(value, Mapping):
        return ("key", "value")
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, Mapping):
                return tuple(
                    dict.fromkeys(
                        key for entry in value if isinstance(entry, Mapping) for key in entry
                    )
                )
        return ("value",)
    return ("value",)


def items_from_value(value: Any) -> tuple[str, ...]:
    """Normalise a data value into a list of display strings."""
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return tuple(f"{key}: {stringify_value(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return tuple(
            ", ".join(f"{key}: {stringify_value(item)}" for key, item in entry.items())
            if isinstance(entry, Mapping)
            else stringify_value(entry)
            for entry in value
        )
    return (stringify_value(value),)


def metrics_from_value(value: Any) -> tuple[tuple[str, str], ...]:
    """Normalise a data value into labelled metric pairs."""
    if isinstance(value, Mapping):
        return tuple((str(key), stringify_value(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        metrics: list[tuple[str, str]] = []
        for item in value:
            if isinstance(item, Mapping) and "label" in item:
                metrics.append(
                    (stringify_value(item.get("label", "")), stringify_value(item.get("value", "")))
                )
            else:
                metrics.append(("Metric", stringify_value(item)))
        return tuple(metrics)
    if value is None:
        return ()
    return (("Value", stringify_value(value)),)


def resolve_section(section: ReportSection, data: Mapping[str, Any]) -> RenderedSection:
    """Expand one template section against a data snapshot."""
    title_result = substitute_placeholders(section.title, data)
    body_result = substitute_placeholders(section.body, data)
    source_result = substitute_placeholders(section.source, data)
    warnings = [
        f"Unresolved '{token}' in section '{section.label}'"
        for token in dict.fromkeys(
            title_result.missing + body_result.missing + source_result.missing
        )
    ]

    raw_value: Any = data.get(source_result.text, "") if source_result.text else ""
    if source_result.text and source_result.text not in data:
        warnings.append(f"Unknown data source '{source_result.text}' in section '{section.label}'")

    text = body_result.text.strip()
    columns: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    items: tuple[str, ...] = ()
    metrics: tuple[tuple[str, str], ...] = ()

    if section.kind is SectionKind.TEXT:
        if not text and raw_value:
            text = stringify_value(raw_value)
    elif section.kind is SectionKind.TABLE:
        columns = columns_from_value(raw_value, section.columns)
        rows = rows_from_value(raw_value, columns)
    elif section.kind is SectionKind.LIST:
        items = items_from_value(raw_value)
    elif section.kind is SectionKind.METRICS:
        metrics = metrics_from_value(raw_value)

    if section.kind is not SectionKind.TEXT and source_result.text and not raw_value:
        warnings.append(f"Empty data source '{source_result.text}' in section '{section.label}'")

    return RenderedSection(
        id=section.id,
        title=title_result.text.strip() or section.label,
        kind=section.kind,
        text=text,
        columns=columns,
        rows=rows,
        items=items,
        metrics=metrics,
        warnings=tuple(warnings),
    )


def render_report(
    template: ReportTemplate,
    report: Report,
    data: Mapping[str, Any],
    report_format: ReportFormat | None = None,
    generated_at: datetime | None = None,
) -> RenderedReport:
    """Render a report and its template sections against a data snapshot."""
    sections = tuple(resolve_section(section, data) for section in template.enabled_sections)
    warnings = tuple(warning for section in sections for warning in section.warnings)
    timestamp = (
        ensure_utc(generated_at) if generated_at is not None else ensure_utc(report.created_at)
    )
    meta = {
        "report_id": report.id,
        "template_id": template.id,
        "template_name": template.name,
        "scope_id": report.scope_id,
        "status": report.status.value,
        "generated_at": timestamp.isoformat(),
    }
    return RenderedReport(
        title=report.title,
        format=report_format or template.format,
        generated_at=timestamp,
        sections=sections,
        summary=summary_counts(data),
        meta=meta,
        warnings=warnings,
    )


def render_markdown(rendered: RenderedReport) -> str:
    """Serialise a rendered report as Markdown."""
    lines = [f"# {rendered.title}", ""]
    meta = " · ".join(
        f"{label}: {rendered.meta[key]}"
        for label, key in (
            ("Scope", "scope_id"),
            ("Status", "status"),
            ("Generated", "generated_at"),
        )
    )
    lines.extend([f"> {meta}", ""])
    if rendered.summary:
        lines.extend(
            [
                "## Summary",
                "",
                markdown_table(("Metric", "Value"), tuple(rendered.summary.items())),
                "",
            ]
        )
    for section in rendered.sections:
        lines.extend([f"## {section.title}", ""])
        if section.text:
            lines.extend([section.text, ""])
        if section.kind is SectionKind.TABLE and section.columns:
            lines.extend([markdown_table(section.columns, section.rows), ""])
        elif section.kind is SectionKind.LIST and section.items:
            lines.extend([markdown_list(section.items), ""])
        elif section.kind is SectionKind.METRICS and section.metrics:
            lines.extend(f"- **{label}:** {value}" for label, value in section.metrics)
            lines.append("")
        if section.warnings:
            lines.extend(f"> Warning: {warning}" for warning in section.warnings)
            lines.append("")
    if rendered.warnings and not any(section.warnings for section in rendered.sections):
        lines.extend(f"> Warning: {warning}" for warning in rendered.warnings)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_csv(rendered: RenderedReport) -> str:
    """Serialise a rendered report as flattened CSV rows."""
    rows: list[list[Any]] = [["record", "section", "label", "value"]]
    for key, count in rendered.summary.items():
        rows.append(["summary", "", key, count])
    for section in rendered.sections:
        if section.text:
            rows.append(["text", section.id, section.title, section.text])
        if section.kind is SectionKind.TABLE:
            rows.append(["columns", section.id, section.title, ", ".join(section.columns)])
            for row in section.rows:
                rows.append(["row", section.id, "", *row])
        elif section.kind is SectionKind.LIST:
            for item in section.items:
                rows.append(["item", section.id, "", item])
        elif section.kind is SectionKind.METRICS:
            for label, value in section.metrics:
                rows.append(["metric", section.id, label, value])
        for warning in section.warnings:
            rows.append(["warning", section.id, "", warning])
    return csv_lines(rows) + "\n"


def json_payload(rendered: RenderedReport) -> dict[str, Any]:
    """Build the JSON-serialisable payload of a rendered report."""
    return {
        "title": rendered.title,
        "format": rendered.format.value,
        "generated_at": rendered.generated_at.isoformat(),
        "meta": rendered.meta,
        "summary": rendered.summary,
        "warnings": list(rendered.warnings),
        "sections": [
            {
                "id": section.id,
                "title": section.title,
                "kind": section.kind.value,
                "text": section.text,
                "columns": list(section.columns),
                "rows": [list(row) for row in section.rows],
                "items": list(section.items),
                "metrics": [list(metric) for metric in section.metrics],
                "warnings": list(section.warnings),
                "row_count": section.row_count,
            }
            for section in rendered.sections
        ],
    }


def render_json(rendered: RenderedReport) -> str:
    """Serialise a rendered report as indented JSON."""
    return json.dumps(json_payload(rendered), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_html(rendered: RenderedReport) -> str:
    """Serialise a rendered report as a standalone, printable HTML document."""
    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8" />',
        '<meta name="viewport" content="width=device-width, initial-scale=1" />',
        f"<title>{html_text(rendered.title)}</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;line-height:1.55;"
        "max-width:900px;margin:40px auto;padding:0 20px;color:#0f172a}",
        "h1{font-size:2rem;margin-bottom:0.25rem}"
        "h2{margin-top:2rem;border-bottom:1px solid #e2e8f0;padding-bottom:0.4rem}",
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #cbd5e1;padding:6px 10px;text-align:left}",
        "th{background:#f1f5f9}.meta{color:#475569;font-size:0.85rem}.warning{color:#b45309}",
        "@media print{body{margin:0}h2{break-after:avoid}table{break-inside:avoid}}",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{html_text(rendered.title)}</h1>",
        f'<p class="meta">Scope {html_text(rendered.meta.get("scope_id", ""))} · '
        f"Status {html_text(rendered.meta.get('status', ''))} · "
        f"Generated {html_text(rendered.meta.get('generated_at', ''))}</p>",
    ]
    if rendered.summary:
        parts.extend(
            ["<h2>Summary</h2>", html_table(("Metric", "Value"), tuple(rendered.summary.items()))]
        )
    for section in rendered.sections:
        parts.append(f"<h2>{html_text(section.title)}</h2>")
        if section.text:
            parts.append(f"<p>{html_text(section.text)}</p>")
        if section.kind is SectionKind.TABLE and section.columns:
            parts.append(html_table(section.columns, section.rows))
        elif section.kind is SectionKind.LIST and section.items:
            parts.append(html_list(section.items))
        elif section.kind is SectionKind.METRICS and section.metrics:
            pairs = "".join(
                f"<div><strong>{html_text(label)}:</strong> {html_text(value)}</div>"
                for label, value in section.metrics
            )
            parts.append(f'<section class="metrics">{pairs}</section>')
        for warning in section.warnings:
            parts.append(f'<p class="warning">Warning: {html_text(warning)}</p>')
    parts.extend(["</body>", "</html>", ""])
    return "\n".join(parts)


def render_export(rendered: RenderedReport) -> ExportPayload:
    """Serialise a rendered report into the requested export format."""
    writers = {
        ReportFormat.MARKDOWN: render_markdown,
        ReportFormat.CSV: render_csv,
        ReportFormat.JSON: render_json,
        ReportFormat.HTML: render_html,
    }
    content = writers[rendered.format](rendered)
    return ExportPayload(
        content=content,
        format=rendered.format,
        title=rendered.title,
        mime_type=FORMAT_MIME_TYPES[rendered.format],
        extension=FORMAT_EXTENSIONS[rendered.format],
        byte_size=len(content.encode("utf-8")),
        line_count=len(content.splitlines()),
        filename=export_filename(rendered.title, rendered.format),
    )


def excerpt(content: str, limit: int = 240) -> str:
    """Return a compact preview excerpt of a rendered document."""
    collapsed = " ".join(content.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1]}…"
