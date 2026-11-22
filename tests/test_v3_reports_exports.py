"""Tests for the report studio domain, persistence, service and API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.reports_exports import SCHEMA_SQL
from ctf_team_dashboard.features.reports_exports.models import (
    ExportJob,
    ExportStatus,
    Report,
    ReportFormat,
    ReportSection,
    ReportStats,
    ReportStatus,
    ReportTemplate,
    SectionKind,
    TemplateScope,
    collect_placeholders,
    dump_data,
    dump_sections,
    export_filename,
    parse_data,
    parse_sections,
    section_from_mapping,
    slugify,
    stringify_value,
    substitute_placeholders,
    summary_counts,
    truncate,
)
from ctf_team_dashboard.features.reports_exports.renderers import (
    csv_cell,
    csv_lines,
    excerpt,
    html_table,
    html_text,
    markdown_cell,
    markdown_table,
    render_csv,
    render_export,
    render_html,
    render_json,
    render_markdown,
    render_report,
    resolve_section,
    rows_from_value,
)
from ctf_team_dashboard.features.reports_exports.service import ReportService
from ctf_team_dashboard.features.reports_exports.store import (
    ExportRepository,
    ReportRepository,
    ReportTemplateRepository,
)

DEFAULT_SECTIONS: list[dict[str, Any]] = [
    {
        "id": "overview",
        "title": "Overview for {{ team }}",
        "kind": "text",
        "body": "We solved {{ solved || 0 }} of {{ total }} challenges.",
        "source": "",
        "columns": [],
        "enabled": True,
        "order": 0,
    },
    {
        "id": "challenges",
        "title": "Challenge register",
        "kind": "table",
        "body": "",
        "source": "challenges",
        "columns": ["title", "points"],
        "enabled": True,
        "order": 1,
    },
    {
        "id": "members",
        "title": "Team",
        "kind": "list",
        "body": "",
        "source": "members",
        "columns": [],
        "enabled": True,
        "order": 2,
    },
]

SNAPSHOT: dict[str, Any] = {
    "team": "Null Pointers",
    "solved": 7,
    "total": 12,
    "challenges": [
        {"title": "Blazing, Fast Login", "points": 100},
        {"title": 'Quote "This"', "points": 250},
    ],
    "members": [{"handle": "cortex"}, {"handle": "nxbit"}],
    "score": 350,
}


def template_model(sections: list[dict[str, Any]] | None = None) -> ReportTemplate:
    """Build a template domain object for unit tests."""
    chosen = DEFAULT_SECTIONS if sections is None else sections
    return ReportTemplate(
        id="tpl_test",
        name="Weekly report",
        sections_json=dump_sections(
            [section_from_mapping(item, index) for index, item in enumerate(chosen)]
        ),
        format=ReportFormat.MARKDOWN,
        scope=TemplateScope.TEAM,
        updated_at=datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc),
    )


def create_template(client: TestClient, **overrides: Any) -> dict[str, Any]:
    """Create a template through the API and return its JSON representation."""
    payload: dict[str, Any] = {
        "name": "Incident summary",
        "sections": DEFAULT_SECTIONS,
        "format": "markdown",
        "scope": "team",
    }
    payload.update(overrides)
    response = client.post("/api/reports/templates", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_report(client: TestClient, template_id: str, **overrides: Any) -> dict[str, Any]:
    """Create a report through the API and return its JSON representation."""
    payload: dict[str, Any] = {
        "template_id": template_id,
        "title": "Weekly summary",
        "scope_id": "team-1",
        "data": SNAPSHOT,
    }
    payload.update(overrides)
    response = client.post("/api/reports", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def final_report(client: TestClient, template_id: str) -> dict[str, Any]:
    """Create and finalise a report through the API."""
    report = create_report(client, template_id)
    response = client.post(f"/api/reports/{report['id']}/finalise")
    assert response.status_code == 200, response.text
    return response.json()


class TestDomainModels:
    """Pure domain behaviour of report entities."""

    def test_enum_parsing_is_case_insensitive_with_fallbacks(self) -> None:
        assert ReportFormat.parse("CSV") is ReportFormat.CSV
        assert ReportFormat.parse("yaml", ReportFormat.JSON) is ReportFormat.JSON
        assert ReportStatus.parse("final") is ReportStatus.FINAL
        assert TemplateScope.parse("event") is TemplateScope.EVENT
        assert SectionKind.parse("metrics") is SectionKind.METRICS
        with pytest.raises(ValueError, match="Unsupported report format"):
            ReportFormat.parse("yaml")

    def test_section_defaults_and_placeholders(self) -> None:
        section = ReportSection(
            id="intro",
            title="Hello {{ team }}",
            body="{{ team || team-missing }} / {{ score }}",
            source="{{ scope }}.items",
        )
        assert section.label == "Hello {{ team }}"
        assert section.placeholder_tokens == ("team", "score", "scope")
        updated = section.updated(title="Renamed", order=4)
        assert updated.title == "Renamed"
        assert updated.order == 4
        assert updated.body == section.body
        assert section.to_mapping()["id"] == "intro"

    def test_parse_sections_sorts_and_tolerates_bad_rows(self) -> None:
        payload = json.dumps(
            [
                {"id": "second", "order": 2, "kind": "bogus"},
                None,
                {"id": "first", "order": 1, "title": "First"},
                "not-an-object",
            ]
        )
        sections = parse_sections(payload)
        assert [section.id for section in sections] == ["first", "second"]
        assert sections[1].kind is SectionKind.TEXT
        assert parse_sections("not json") == ()
        assert parse_sections('{"a": 1}') == ()

    def test_dump_parse_round_trip_preserves_columns_and_flags(self) -> None:
        section = ReportSection(
            id="table",
            kind=SectionKind.TABLE,
            columns=("title", "points"),
            enabled=False,
            order=3,
        )
        restored = parse_sections(dump_sections([section]))[0]
        assert restored.columns == ("title", "points")
        assert restored.enabled is False
        assert restored.order == 3

    def test_placeholder_substitution_supports_nesting_and_fallbacks(self) -> None:
        data = {"team": {"name": "Cipher Wardens"}, "count": 0, "empty": ""}
        result = substitute_placeholders(
            "{{ team.name }} solved {{ count }} / {{ missing || none }} / {{ empty || blank }}",
            data,
        )
        assert result.text == "Cipher Wardens solved 0 / none / blank"
        assert result.resolved == ("team.name", "count")
        assert result.missing == ("missing", "empty")
        assert not result.is_complete
        assert collect_placeholders(("{{ a }}", "{{ a }} and {{ b.c }}")) == ("a", "b.c")

    def test_summary_counts_and_data_serialisation(self) -> None:
        counts = summary_counts({"challenges": [1, 2], "points": 250, "active": True, "team": "x"})
        assert counts == {"challenges": 2, "points": 250}
        assert parse_data(dump_data({"b": 1, "a": 2})) == {"a": 2, "b": 1}
        assert parse_data("broken") == {}
        assert parse_data("[1, 2]") == {}
        assert stringify_value({"b": 1, "a": 2}) == '{"a":2,"b":1}'
        assert stringify_value(True) == "yes"
        assert stringify_value(None) == ""

    def test_slug_filename_and_excerpt_helpers(self) -> None:
        assert slugify("Weekly Report / Q1!") == "weekly-report-q1"
        assert export_filename("Weekly Report", ReportFormat.CSV) == "weekly-report.csv"
        assert truncate("  a   b  ", 20) == "a b"
        assert len(truncate("x" * 300, 40)) == 40

    def test_report_and_stats_derived_properties(self, database: Any) -> None:
        template = template_model()
        assert template.section_count == 3
        assert len(template.enabled_sections) == 3
        assert not template.is_empty
        assert "table" in template.description
        assert template.with_sections([]).is_empty
        report = ReportService().reports.get("missing")
        assert report is None

    def test_export_metadata_properties(self) -> None:
        job = ExportJob(
            id="exp_1",
            report_id="rep_1",
            format=ReportFormat.JSON,
            status=ExportStatus.COMPLETE,
            content="line one\nline two",
        )
        assert job.byte_size == 17
        assert job.line_count == 2
        assert job.extension == "json"
        assert job.mime_type == "application/json"
        assert job.is_complete
        stats = ReportStats(templates=2, reports=4, final_reports=2, exports=3)
        assert stats.total_artifacts == 9
        assert stats.finalisation_rate == 0.5
        assert stats.exports_of(ReportFormat.CSV) == 0


class TestRenderers:
    """Formatting rules shared by preview and export."""

    def test_csv_and_markdown_escaping(self) -> None:
        assert csv_cell('a,b "c"\nd') == '"a,b ""c""\nd"'
        assert csv_cell(None) == ""
        assert csv_lines([["a", 1], ["b", None]]) == "a,1\nb,"
        assert markdown_cell("a|b\\c\nd") == "a\\|b\\\\c d"
        assert html_text('<script>alert("x")</script>') == (
            "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"
        )

    def test_table_helpers_render_headers_and_rows(self) -> None:
        table = markdown_table(("Name", "Score"), [("a|b", 10)])
        assert table.startswith("| Name | Score |")
        assert "| --- | --- |" in table
        assert "| a\\|b | 10 |" in table
        html = html_table(("Name",), [("<b>x</b>",)])
        assert '<th scope="col">Name</th>' in html
        assert "&lt;b&gt;x&lt;/b&gt;" in html

    def test_rows_from_value_normalises_mappings_lists_and_scalars(self) -> None:
        assert rows_from_value({"a": 1}) == (("a", "1"),)
        assert rows_from_value([{"title": "x", "points": 10}], ("title", "points")) == (
            ("x", "10"),
        )
        assert rows_from_value([1, 2]) == (("1",), ("2",))
        assert rows_from_value(42) == (("42",),)
        assert rows_from_value([]) == ()

    def test_resolve_section_reports_missing_tokens_and_sources(self) -> None:
        section = ReportSection(
            id="s",
            title="{{ title }}",
            body="{{ absent || fallback }}",
            kind=SectionKind.TABLE,
            source="{{ rows }}",
        )
        rendered = resolve_section(section, {"title": "Hello"})
        assert rendered.title == "Hello"
        assert rendered.text == "fallback"
        assert len(rendered.warnings) == 2
        assert "absent" in rendered.warnings[0]
        assert "rows" in rendered.warnings[1]

    def test_render_report_builds_structured_preview(self) -> None:
        rendered = render_report(
            template_model(),
            Report(
                id="rep_1",
                template_id="tpl_test",
                title="Weekly report",
                scope_id="team-1",
            ),
            SNAPSHOT,
        )
        assert rendered.title == "Weekly report"
        assert rendered.section_count == 3
        assert rendered.summary["challenges"] == 2
        assert rendered.summary["score"] == 350
        assert rendered.total_rows >= 2
        assert rendered.meta["scope_id"] == "team-1"
        assert "Overview for Null Pointers" in rendered.sections[0].title

    def test_markdown_export_contains_tables_and_summary(self) -> None:
        rendered = render_report(
            template_model(),
            Report(id="rep_1", template_id="tpl_test", title="Weekly report", scope_id="team-1"),
            SNAPSHOT,
            ReportFormat.MARKDOWN,
        )
        output = render_markdown(rendered)
        assert output.startswith("# Weekly report")
        assert "## Summary" in output
        assert "| Metric | Value |" in output
        assert "Blazing, Fast Login".replace(",", "\\,") in output or "Blazing" in output
        assert "- handle: cortex" in output

    def test_csv_export_escapes_commas_and_quotes(self) -> None:
        rendered = render_report(
            template_model(),
            Report(id="rep_1", template_id="tpl_test", title="Weekly report", scope_id="team-1"),
            SNAPSHOT,
            ReportFormat.CSV,
        )
        output = render_csv(rendered)
        assert output.startswith("record,section,label,value")
        assert '"Blazing, Fast Login"' in output
        assert '""Quote ""This"""' in output or 'Quote ""This""' in output

    def test_json_export_is_pretty_printed_and_sorted(self) -> None:
        rendered = render_report(
            template_model(),
            Report(id="rep_1", template_id="tpl_test", title="Weekly report", scope_id="team-1"),
            SNAPSHOT,
            ReportFormat.JSON,
        )
        output = render_json(rendered)
        assert '\n  "meta": {' in output
        assert output.index('"format"') < output.index('"sections"')
        assert json.loads(output)["title"] == "Weekly report"

    def test_html_export_escapes_user_content(self) -> None:
        rendered = render_report(
            template_model(),
            Report(id="rep_1", template_id="tpl_test", title="Weekly report", scope_id="team-1"),
            SNAPSHOT,
            ReportFormat.HTML,
        )
        output = render_html(rendered)
        assert output.startswith("<!doctype html>")
        assert "@media print" in output
        assert "Blazing, Fast Login" in output

    def test_render_export_payload_metadata_and_excerpt(self) -> None:
        rendered = render_report(
            template_model(),
            Report(id="rep_1", template_id="tpl_test", title="Weekly Report", scope_id="team-1"),
            SNAPSHOT,
            ReportFormat.CSV,
        )
        payload = render_export(rendered)
        assert payload.extension == "csv"
        assert payload.mime_type == "text/csv"
        assert payload.filename == "weekly-report.csv"
        assert payload.byte_size == len(payload.content.encode("utf-8"))
        assert payload.line_count > 1
        assert "…" in excerpt("x " * 300, 40)


class TestStores:
    """Persistence round trips through the three feature tables."""

    def test_tables_are_migrated(self, database: Any) -> None:
        names = database.table_names()
        assert {"v3_report_templates", "v3_reports", "v3_exports"} <= names
        assert "CREATE TABLE IF NOT EXISTS v3_reports" in SCHEMA_SQL

    def test_template_repository_crud(self, database: Any) -> None:
        repo = ReportTemplateRepository(database)
        template = template_model()
        assert repo.get(template.id) is None
        assert repo.create(template).id == template.id
        assert repo.count() == 1
        assert repo.list_all()[0].name == "Weekly report"
        assert repo.get(template.id).format is ReportFormat.MARKDOWN  # type: ignore[union-attr]
        renamed = ReportTemplate(
            id=template.id,
            name="Renamed",
            sections_json=template.sections_json,
            format=ReportFormat.CSV,
            scope=TemplateScope.GLOBAL,
            updated_at=template.updated_at,
        )
        repo.update(renamed)
        assert repo.get(template.id).name == "Renamed"  # type: ignore[union-attr]
        assert repo.delete(template.id)
        assert repo.count() == 0

    def test_report_repository_crud_and_filters(self, database: Any) -> None:
        templates = ReportTemplateRepository(database)
        templates.create(template_model())
        repo = ReportRepository(database)
        report = Report(
            id="rep_a",
            template_id="tpl_test",
            title="Alpha",
            scope_id="team-1",
            data_json=dump_data({"score": 1}),
        )
        repo.create(report)
        assert repo.get("rep_a").data == {"score": 1}  # type: ignore[union-attr]
        assert len(repo.list_all()) == 1
        assert repo.set_status("rep_a", ReportStatus.FINAL)
        assert repo.count_status(ReportStatus.FINAL) == 1
        assert repo.count_status(ReportStatus.DRAFT) == 0
        assert len(repo.list_all(status=ReportStatus.FINAL)) == 1
        assert len(repo.list_all(template_id="tpl_test")) == 1
        assert repo.set_snapshot("rep_a", dump_data({"score": 9}))
        assert repo.get("rep_a").data == {"score": 9}  # type: ignore[union-attr]
        assert repo.delete("rep_a")

    def test_export_repository_crud_and_counts(self, database: Any) -> None:
        templates = ReportTemplateRepository(database)
        templates.create(template_model())
        reports = ReportRepository(database)
        reports.create(Report(id="rep_a", template_id="tpl_test", title="Alpha", scope_id="team-1"))
        repo = ExportRepository(database)
        job = ExportJob(
            id="exp_a",
            report_id="rep_a",
            format=ReportFormat.HTML,
            status=ExportStatus.COMPLETE,
            content="<html></html>",
        )
        repo.create(job)
        assert repo.get("exp_a").is_complete  # type: ignore[union-attr]
        assert repo.list_for_report("rep_a")[0].id == "exp_a"
        assert repo.list_all()[0].id == "exp_a"
        assert repo.count_by_format() == {"html": 1}
        assert repo.delete("exp_a")


class TestService:
    """Business rules and workflow orchestration."""

    def test_create_template_validation(self, database: Any) -> None:
        service = ReportService()
        with pytest.raises(ValidationError, match="name is required"):
            service.create_template("  ", [])
        with pytest.raises(ValidationError, match="at least one section"):
            service.create_template("Empty", [])
        with pytest.raises(ValidationError, match="Duplicate section"):
            service.create_template(
                "Dupes",
                [section_from_mapping({"id": "same"}), section_from_mapping({"id": "same"})],
            )
        with pytest.raises(ValidationError, match="at most 40"):
            service.create_template(
                "Too many", [section_from_mapping({"id": str(i)}) for i in range(41)]
            )

    def test_create_template_normalises_orders_and_formats(self, database: Any) -> None:
        service = ReportService()
        template = service.create_template(
            " Incidents ",
            [{"id": "b", "order": 9}, {"id": "a", "order": -1}],
            "csv",
            "global",
        )
        assert template.name == "Incidents"
        assert template.format is ReportFormat.CSV
        assert template.scope is TemplateScope.GLOBAL
        assert [section.order for section in template.sections] == [0, 1]

    def test_missing_templates_and_reports_raise_not_found(self, database: Any) -> None:
        service = ReportService()
        with pytest.raises(NotFoundError):
            service.get_template("nope")
        with pytest.raises(NotFoundError):
            service.get_report("nope")
        with pytest.raises(NotFoundError):
            service.get_export("nope")

    def test_create_report_captures_snapshot(self, database: Any, seeded: Any) -> None:
        service = ReportService()
        template = service.create_template("Seeded", DEFAULT_SECTIONS)
        teams = seeded.teams.list_all()
        report = service.create_report(template.id, "Seed report", teams[0].id)
        assert report.is_draft
        assert report.data["team"] == teams[0].name
        assert report.data["total"] > 0
        assert service.preview_report(report.id).section_count > 0

    def test_report_validation_paths(self, database: Any) -> None:
        service = ReportService()
        template = service.create_template("Small", DEFAULT_SECTIONS)
        with pytest.raises(ValidationError, match="title is required"):
            service.create_report(template.id, " ", "scope")
        with pytest.raises(ValidationError, match="scope is required"):
            service.create_report(template.id, "Title", " ")
        with pytest.raises(ValidationError, match="at most 200 keys"):
            service.create_report(template.id, "Title", "scope", {str(i): i for i in range(201)})

    def test_snapshot_update_and_finalise_conflict(self, database: Any) -> None:
        service = ReportService()
        template = service.create_template("Small", DEFAULT_SECTIONS)
        report = service.create_report(template.id, "Title", "scope", SNAPSHOT)
        updated = service.update_report_data(report.id, {"score": 99})
        assert updated.data == {"score": 99}
        finalised = service.finalise_report(report.id)
        assert finalised.is_final
        with pytest.raises(ConflictError, match="already finalised"):
            service.finalise_report(report.id)
        with pytest.raises(ConflictError, match="cannot be edited"):
            service.update_report_data(report.id, {"score": 1})

    def test_export_all_formats_and_draft_guard(self, database: Any) -> None:
        service = ReportService()
        template = service.create_template("Exports", DEFAULT_SECTIONS)
        report = service.create_report(template.id, "Title", "scope", SNAPSHOT)
        with pytest.raises(ConflictError, match="Finalise"):
            service.export_report(report.id, ReportFormat.CSV)
        service.finalise_report(report.id)
        for report_format in ReportFormat:
            job = service.export_report(report.id, report_format)
            assert job.status is ExportStatus.COMPLETE
            assert job.content
        assert service.stats().exports == 4

    def test_stats_and_list_helpers(self, database: Any) -> None:
        service = ReportService()
        template = service.create_template("Stats", DEFAULT_SECTIONS)
        service.create_report(template.id, "Draft", "scope", SNAPSHOT)
        finalised = service.create_report(template.id, "Final", "scope", SNAPSHOT)
        service.finalise_report(finalised.id)
        service.export_report(finalised.id, "json")
        stats = service.stats()
        assert stats.templates == 1
        assert stats.reports == 2
        assert stats.draft_reports == 1
        assert stats.final_reports == 1
        assert stats.exports_of(ReportFormat.JSON) == 1
        assert len(service.list_exports()) == 1
        assert len(service.list_reports(ReportStatus.DRAFT)) == 1
        with pytest.raises(ValidationError):
            service.list_reports(limit=0)

    def test_parse_sections_json_helper(self, database: Any) -> None:
        service = ReportService()
        assert service.parse_sections_json("[]") == ()
        assert len(service.parse_sections_json(json.dumps(DEFAULT_SECTIONS))) == 3


class TestRouter:
    """HTTP contract, status codes and error envelopes."""

    def test_template_endpoints(self, client: TestClient) -> None:
        assert client.get("/api/reports/templates").json() == []
        template = create_template(client)
        assert template["name"] == "Incident summary"
        assert template["section_count"] == 3
        assert template["sections"][0]["placeholder_tokens"] == ["team", "solved", "total"]
        listed = client.get("/api/reports/templates").json()
        assert [item["id"] for item in listed] == [template["id"]]

    def test_template_validation_error(self, client: TestClient) -> None:
        response = client.post("/api/reports/templates", json={"name": "", "sections": []})
        assert response.status_code == 422

    def test_report_lifecycle_and_preview(self, client: TestClient) -> None:
        template = create_template(client)
        report = create_report(client, template["id"])
        assert report["status"] == "draft"
        assert client.get(f"/api/reports/{report['id']}").json()["title"] == "Weekly summary"
        preview = client.get(f"/api/reports/{report['id']}/preview")
        assert preview.status_code == 200
        assert preview.json()["section_count"] == 3
        assert preview.json()["summary"]["score"] == 350
        csv_preview = client.get(f"/api/reports/{report['id']}/preview?format=csv")
        assert csv_preview.json()["format"] == "csv"
        response = client.post(f"/api/reports/{report['id']}/finalise")
        assert response.status_code == 200
        assert response.json()["is_final"] is True
        filtered = client.get("/api/reports?status=final").json()
        assert [item["id"] for item in filtered] == [report["id"]]

    def test_export_endpoint_and_export_list(self, client: TestClient) -> None:
        template = create_template(client)
        report = final_report(client, template["id"])
        response = client.post(f"/api/reports/{report['id']}/export", json={"format": "markdown"})
        assert response.status_code == 201
        body = response.json()
        assert body["format"] == "markdown"
        assert body["extension"] == "md"
        assert "# Weekly summary" in body["content"]
        exports = client.get("/api/reports/exports").json()
        assert [item["id"] for item in exports] == [body["id"]]

    def test_static_routes_are_not_shadowed_by_report_id(self, client: TestClient) -> None:
        assert client.get("/api/reports/exports").status_code == 200
        assert client.get("/api/reports/stats").status_code == 200
        assert client.get("/api/reports/templates").status_code == 200

    def test_stats_endpoint(self, client: TestClient) -> None:
        template = create_template(client)
        report = final_report(client, template["id"])
        client.post(f"/api/reports/{report['id']}/export", json={"format": "json"})
        stats = client.get("/api/reports/stats").json()
        assert stats["templates"] == 1
        assert stats["reports"] == 1
        assert stats["final_reports"] == 1
        assert stats["exports_by_format"] == {"json": 1}
        assert stats["finalisation_rate"] == 1.0

    def test_snapshot_patch_endpoint(self, client: TestClient) -> None:
        template = create_template(client)
        report = create_report(client, template["id"])
        response = client.patch(f"/api/reports/{report['id']}/data", json={"data": {"score": 42}})
        assert response.status_code == 200
        assert response.json()["data"] == {"score": 42}

    def test_error_paths_return_domain_envelopes(self, client: TestClient) -> None:
        missing = client.get("/api/reports/missing")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "not_found"
        template = create_template(client)
        report = create_report(client, template["id"])
        draft_export = client.post(f"/api/reports/{report['id']}/export", json={"format": "csv"})
        assert draft_export.status_code == 409
        assert draft_export.json()["error"]["code"] == "conflict"
        again = client.post(f"/api/reports/{report['id']}/finalise")
        assert again.status_code == 200
        second = client.post(f"/api/reports/{report['id']}/finalise")
        assert second.status_code == 409
        invalid_format = client.get(f"/api/reports/{report['id']}/preview?format=xml")
        assert invalid_format.status_code == 422

    def test_report_limit_validation(self, client: TestClient) -> None:
        response = client.get("/api/reports?limit=0")
        assert response.status_code == 422
