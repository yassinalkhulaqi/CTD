"""Tests for the V3 notes workspace feature.

The module exercises the pure domain helpers, the three repositories, the
service rules and the mounted HTTP API against isolated databases.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.notes_workspace.models import (
    ChangeSummary,
    NoteEntry,
    NoteFormat,
    NoteRevision,
    NoteTemplate,
    TemplateCategory,
    count_words,
    estimate_reading_time,
    extract_headings,
    extract_variables,
    make_excerpt,
    normalise_tag,
    normalise_tags,
    render_variables,
    slugify,
)
from ctf_team_dashboard.features.notes_workspace.service import NotesWorkspaceService
from ctf_team_dashboard.features.notes_workspace.store import (
    NoteEntryRepository,
    NoteRevisionRepository,
    NotesStore,
    NoteTemplateRepository,
)

CHALLENGE_ID = "challenge-0001"
MEMBER_ID = "member-0001"


def _note(**overrides: object) -> NoteEntry:
    """Build a note entity with sensible defaults for tests."""
    values: dict[str, object] = {
        "id": "note-test-0001",
        "challenge_id": CHALLENGE_ID,
        "member_id": MEMBER_ID,
        "title": "Initial observations",
        "body": "The token is signed with a predictable secret.",
        "format": NoteFormat.MARKDOWN,
        "tags": ("web", "jwt"),
        "pinned": False,
        "version": 1,
    }
    values.update(overrides)
    note = NoteEntry(
        id=str(values["id"]),
        challenge_id=str(values["challenge_id"]),
        member_id=str(values["member_id"]),
        title=str(values["title"]),
        body=str(values["body"]),
        format=(
            values["format"] if isinstance(values["format"], NoteFormat) else NoteFormat.MARKDOWN
        ),
        tags=tuple(values["tags"]) if isinstance(values["tags"], (tuple, list)) else (),
        pinned=bool(values["pinned"]),
        version=int(values["version"]),  # type: ignore[arg-type]
    )
    return note


# ----------------------------------------------------------------------
# Pure domain helpers
# ----------------------------------------------------------------------
def test_count_words_and_reading_time() -> None:
    """Word counting ignores punctuation and reading time scales linearly."""
    assert count_words("one two, three's four!") == 4
    assert count_words("   ") == 0
    assert estimate_reading_time("word " * 400) == 2.0
    assert estimate_reading_time("word", words_per_minute=0) == 0.0


def test_make_excerpt_collapses_markdown_and_truncates() -> None:
    """Excerpts are single line, marker free and bounded."""
    assert make_excerpt("  #  Title  \n  Some **bold** text ") == "Title Some bold text"
    long = make_excerpt("x" * 300, limit=20)
    assert len(long) == 20
    assert long.endswith("…")


def test_tag_normalisation_is_canonical_and_bounded() -> None:
    """Tags are lower-cased, slugified, de-duplicated and capped."""
    assert normalise_tag("  Web Exploit!! ") == "web-exploit"
    assert normalise_tags(["Web", "web", " crypto ", "", "a" * 50]) == (
        "web",
        "crypto",
        "a" * 32,
    )
    assert len(normalise_tags([f"tag-{index}" for index in range(30)])) == 12


def test_heading_extraction_skips_fenced_code() -> None:
    """ATX headings are extracted but code fences are ignored."""
    body = "# Intro\ntext\n```md\n# Not a heading\n```\n## Deep Dive\n### Notes\n"
    headings = extract_headings(body)
    assert [heading.text for heading in headings] == ["Intro", "Deep Dive", "Notes"]
    assert [heading.level for heading in headings] == [1, 2, 3]
    assert [heading.line for heading in headings] == [1, 6, 7]
    assert headings[0].anchor == "intro"
    assert headings[1].indent == 1
    assert slugify("  Hello, World!  ") == "hello-world"
    assert slugify("!!!") == "section"


def test_template_variables_and_rendering() -> None:
    """Placeholders are discovered once and substituted repeatedly."""
    body = "## {{ title }}\nOwner: {{owner}}\nRepeat {{ title }}"
    assert extract_variables(body) == ("title", "owner")
    rendered = render_variables(body, {"title": "RSA", "owner": "nyx"})
    assert "## RSA" in rendered
    assert "Owner: nyx" in rendered
    assert "{{ title }}" not in rendered
    assert render_variables("{{missing}}", {}) == "{{missing}}"
    template = NoteTemplate(id="tpl-1", name="Report", category=TemplateCategory.CRYPTO, body=body)
    assert template.variables == ("title", "owner")
    assert template.variable_count == 2
    assert template.line_count == 3


def test_change_summary_counts_words_and_formats() -> None:
    """A word level diff reports insertions, deletions and a compact label."""
    first = NoteRevision("rev-1", "note-1", 1, "alpha beta gamma", MEMBER_ID)
    second = NoteRevision("rev-2", "note-1", 2, "alpha beta delta epsilon", MEMBER_ID)
    summary = second.summary_against(first)
    assert summary.added == 2
    assert summary.removed == 1
    assert summary.net == 1
    assert summary.magnitude == 3
    assert summary.describe() == "+2 -1"
    assert first.summary_against(None).added == 3
    assert ChangeSummary().describe() == "No content change"


def test_note_derived_properties() -> None:
    """A note exposes computed metadata and text/tag matching."""
    note = _note(body="# Heading\n\nThe **jwt** secret is weak.", tags=("Web", "jwt"))
    assert note.word_count == 6
    assert note.reading_time_minutes == 0.0
    assert "Heading" in note.excerpt
    assert [heading.text for heading in note.headings] == ["Heading"]
    assert note.tag_count == 2
    assert note.matches("SECRET") is True
    assert note.matches("inane") is False
    assert note.has_tag("Web") is True
    assert note.format.label == "Markdown"
    assert NoteFormat.CODE.monospace is True


# ----------------------------------------------------------------------
# Store layer
# ----------------------------------------------------------------------
def test_store_note_crud_search_and_pin(database: Database) -> None:
    """Notes persist, search by text/tags and support pinned state."""
    store = NotesStore(database)
    repo: NoteEntryRepository = store.notes
    first = repo.create(
        _note(id="note-a", title="JWT keys", body="The jwt secret", tags=("web", "jwt"))
    )
    second = repo.create(
        _note(
            id="note-b",
            title="Heap layout",
            body="A uaf in the allocator",
            tags=("pwn", "heap"),
            challenge_id="challenge-0002",
        )
    )
    assert repo.get("note-a") == first
    assert repo.count() == 2
    assert [item.id for item in repo.list_for_challenge(CHALLENGE_ID)] == ["note-a"]
    assert [item.id for item in repo.list_for_member(MEMBER_ID)] == ["note-b", "note-a"]
    assert [item.id for item in repo.search(query="jwt")] == ["note-a"]
    assert [item.id for item in repo.search(tags=["pwn"])] == ["note-b"]
    assert [item.id for item in repo.search(challenge_id=CHALLENGE_ID)] == ["note-a"]
    assert repo.set_pinned("note-a", True) is not None
    pinned_note = repo.get("note-a")
    assert pinned_note is not None
    assert pinned_note.pinned is True
    assert repo.set_pinned("missing", True) is None
    assert repo.distinct_tags() == ("heap", "jwt", "pwn", "web")
    assert repo.delete("note-b") is True
    assert repo.delete("note-b") is False
    assert repo.distinct_tags() == ("jwt", "web")
    assert second.id == "note-b"


def test_store_revisions_and_templates(database: Database) -> None:
    """Revisions append in version order and templates can be listed by category."""
    store = NotesStore(database)
    revisions: NoteRevisionRepository = store.revisions
    for version in (1, 2, 3):
        revisions.create(
            NoteRevision(f"rev-{version}", "note-1", version, f"body {version}", MEMBER_ID)
        )
    found = revisions.list_for_note("note-1")
    assert [item.version for item in found] == [1, 2, 3]
    assert revisions.latest_for_note("note-1") is not None
    assert revisions.count_for_note("note-1") == 3
    assert revisions.delete_for_note("note-1") == 3
    assert revisions.count_for_note("note-1") == 0

    templates: NoteTemplateRepository = store.templates
    templates.create(NoteTemplate("tpl-1", "Web report", TemplateCategory.WEB, "{{target}}"))
    templates.create(NoteTemplate("tpl-2", "Checklist", TemplateCategory.CHECKLIST, "- [ ] task"))
    assert len(templates.list_all()) == 2
    assert [item.name for item in templates.list_all(TemplateCategory.WEB)] == ["Web report"]
    assert templates.find_by_name("web report") is not None
    assert templates.delete("tpl-1") is True


# ----------------------------------------------------------------------
# Service rules
# ----------------------------------------------------------------------
def test_service_creates_note_with_first_revision(database: Database) -> None:
    """Creating a note also stores its first immutable revision."""
    service = NotesWorkspaceService()
    note = service.create_note(
        challenge_id=CHALLENGE_ID,
        member_id=MEMBER_ID,
        title="  Notes  ",
        body="  Some content  ",
        tags=["Web", "web", "JWT"],
    )
    assert note.title == "Notes"
    assert note.body == "Some content"
    assert note.tags == ("web", "jwt")
    assert note.version == 1
    timeline = service.list_revisions(note.id)
    assert len(timeline) == 1
    assert timeline[0].is_latest is True
    assert timeline[0].summary.added == 2


def test_service_validation_rules(database: Database) -> None:
    """Empty titles, empty bodies and blank identifiers are rejected."""
    service = NotesWorkspaceService()
    with pytest.raises(ValidationError):
        service.create_note(challenge_id=CHALLENGE_ID, member_id=MEMBER_ID, title="  ", body="body")
    with pytest.raises(ValidationError):
        service.create_note(challenge_id=CHALLENGE_ID, member_id=MEMBER_ID, title="title", body="")
    with pytest.raises(ValidationError):
        service.create_note(challenge_id="", member_id=MEMBER_ID, title="title", body="body")
    note = service.create_note(
        challenge_id=CHALLENGE_ID, member_id=MEMBER_ID, title="Valid", body="body"
    )
    with pytest.raises(ValidationError):
        service.update_note(note.id, title="  ")
    with pytest.raises(NotFoundError):
        service.update_note("missing", title="Valid")


def test_service_update_creates_revision_only_for_body_change(database: Database) -> None:
    """Metadata edits do not create revisions; body edits do."""
    service = NotesWorkspaceService()
    note = service.create_note(
        challenge_id=CHALLENGE_ID,
        member_id=MEMBER_ID,
        title="Original",
        body="alpha beta",
    )
    renamed = service.update_note(note.id, title="Renamed", tags=["web"])
    assert renamed.version == 1
    assert renamed.title == "Renamed"
    assert len(service.list_revisions(note.id)) == 1
    changed = service.update_note(note.id, body="alpha beta gamma", author_id="member-0002")
    assert changed.version == 2
    timeline = service.list_revisions(note.id)
    assert len(timeline) == 2
    assert timeline[-1].revision.author_id == "member-0002"
    assert timeline[-1].summary.added == 1


def test_service_stale_version_conflict(database: Database) -> None:
    """A write based on an old version is rejected with details."""
    service = NotesWorkspaceService()
    note = service.create_note(
        challenge_id=CHALLENGE_ID, member_id=MEMBER_ID, title="A", body="one"
    )
    service.update_note(note.id, body="one two")
    with pytest.raises(ConflictError) as caught:
        service.update_note(note.id, body="three", expected_version=1)
    assert caught.value.details["current_version"] == 2
    with pytest.raises(ValidationError):
        service.update_note(note.id, body="three", expected_version=0)


def test_service_pin_and_delete_cascade(database: Database) -> None:
    """Pin toggles and deleting a note removes its revisions."""
    service = NotesWorkspaceService()
    note = service.create_note(
        challenge_id=CHALLENGE_ID, member_id=MEMBER_ID, title="A", body="one", tags=["web"]
    )
    assert service.set_pinned(note.id).pinned is True
    assert service.set_pinned(note.id, False).pinned is False
    assert service.set_pinned(note.id, True).pinned is True
    service.delete_note(note.id)
    assert service.store.revisions.count_for_note(note.id) == 0
    with pytest.raises(NotFoundError):
        service.get_note(note.id)
    with pytest.raises(NotFoundError):
        service.delete_note(note.id)


def test_service_template_rendering_rules(database: Database) -> None:
    """Templates render strictly and reject duplicates or missing values."""
    service = NotesWorkspaceService()
    template = service.create_template(
        name="Challenge report",
        category=TemplateCategory.WEB,
        body="## {{ title }}\nTarget: {{ target }}",
    )
    assert template.variables == ("title", "target")
    result = service.render_template(
        template_id=template.id,
        variables={"title": "Login", "target": "example.com", "extra": "ignored"},
    )
    assert "## Login" in result.body
    assert result.used_variables == ("title", "target")
    assert result.unused_variables == ("extra",)
    with pytest.raises(ValidationError) as caught:
        service.render_template(template_id=template.id, variables={"title": "Login"})
    assert caught.value.details["missing"] == ["target"]
    with pytest.raises(ConflictError):
        service.create_template(name="challenge report", category=TemplateCategory.WEB, body="x")
    with pytest.raises(NotFoundError):
        service.render_template(template_id="missing", variables={})
    with pytest.raises(ValidationError):
        service.render_template(variables={})


def test_service_summary_aggregation(database: Database) -> None:
    """Per-challenge buckets and workspace totals are computed correctly."""
    service = NotesWorkspaceService()
    first = service.create_note(
        challenge_id=CHALLENGE_ID,
        member_id=MEMBER_ID,
        title="A",
        body="one two three",
        tags=["web", "jwt"],
        pinned=True,
    )
    service.update_note(first.id, body="one two three four")
    service.create_note(
        challenge_id=CHALLENGE_ID,
        member_id="member-0002",
        title="B",
        body="four five",
        tags=["web"],
    )
    service.create_note(
        challenge_id="challenge-0002",
        member_id=MEMBER_ID,
        title="C",
        body="six",
        tags=["pwn"],
    )
    summary = service.summary()
    assert summary.total_notes == 3
    assert summary.total_revisions == 4
    assert summary.pinned_notes == 1
    assert summary.unique_tags == ("jwt", "pwn", "web")
    assert summary.challenge_count == 2
    bucket = summary.challenge(CHALLENGE_ID)
    assert bucket is not None
    assert bucket.note_count == 2
    assert bucket.pinned_count == 1
    assert bucket.unique_authors == 2
    assert bucket.top_tags[0] == "web"
    assert bucket.average_words == 3.0
    filtered = service.summary(challenge_id=CHALLENGE_ID)
    assert filtered.total_notes == 2
    assert filtered.challenge_count == 1


# ----------------------------------------------------------------------
# HTTP API
# ----------------------------------------------------------------------
def _create(client: TestClient, **overrides: object) -> dict[str, object]:
    """Create a note through the API and return its JSON representation."""
    payload: dict[str, object] = {
        "challenge_id": CHALLENGE_ID,
        "member_id": MEMBER_ID,
        "title": "API note",
        "body": "# Heading\n\nSome **formatted** content.",
        "tags": ["Web", "jwt"],
    }
    payload.update(overrides)
    response = client.post("/api/notes", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_api_create_get_list_and_search(client: TestClient, seeded: object) -> None:
    """The CRUD endpoints expose derived fields and filtering."""
    created = _create(client)
    note_id = str(created["id"])
    assert created["version"] == 1
    assert created["word_count"] == 4
    assert created["headings"][0]["text"] == "Heading"
    assert created["tags"] == ["web", "jwt"]

    fetched = client.get(f"/api/notes/{note_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "API note"

    listed = client.get("/api/notes", params={"q": "formatted"})
    assert [item["id"] for item in listed.json()] == [note_id]
    tagged = client.get("/api/notes", params={"tag": "web"})
    assert [item["id"] for item in tagged.json()] == [note_id]
    missing = client.get("/api/notes", params={"q": "nothingmatches"})
    assert missing.json() == []


def test_api_update_pin_revisions_and_delete(client: TestClient, seeded: object) -> None:
    """Update, pin, revision listing and delete form a complete lifecycle."""
    note_id = str(_create(client)["id"])
    patched = client.patch(
        f"/api/notes/{note_id}",
        json={
            "body": "# Heading\n\nSome formatted content plus more words.",
            "expected_version": 1,
        },
    )
    assert patched.status_code == 200
    assert patched.json()["version"] == 2
    revisions = client.get(f"/api/notes/{note_id}/revisions")
    assert revisions.status_code == 200
    assert len(revisions.json()) == 2
    assert revisions.json()[-1]["change_summary"] != "No content change"

    pinned = client.post(f"/api/notes/{note_id}/pin", json={"pinned": True})
    assert pinned.json()["is_pinned"] is True
    assert client.get("/api/notes", params={"pinned": True}).json()[0]["id"] == note_id

    stale = client.patch(f"/api/notes/{note_id}", json={"body": "stale", "expected_version": 1})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "conflict"

    deleted = client.delete(f"/api/notes/{note_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/notes/{note_id}").status_code == 404
    assert client.get(f"/api/notes/{note_id}/revisions").status_code == 404


def test_api_summary_and_templates(client: TestClient, seeded: object) -> None:
    """Summary aggregation and template endpoints return typed payloads."""
    _create(client, title="First", body="alpha beta", tags=["web"])
    _create(client, title="Second", body="gamma", tags=["crypto"], pinned=True)
    summary = client.get("/api/notes/summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["total_notes"] == 2
    assert payload["pinned_notes"] == 1
    assert payload["challenges"][0]["challenge_id"] == CHALLENGE_ID
    assert payload["challenge_count"] == 1

    filtered = client.get("/api/notes/summary", params={"challenge_id": "missing"})
    assert filtered.json()["total_notes"] == 0

    created = client.post(
        "/api/note-templates",
        json={"name": "Report", "category": "crypto", "body": "## {{ title }}\nBy {{ author }}"},
    )
    assert created.status_code == 201
    template = created.json()
    assert template["variables"] == ["title", "author"]
    assert len(client.get("/api/note-templates").json()) == 1
    assert len(client.get("/api/note-templates", params={"category": "crypto"}).json()) == 1

    rendered = client.post(
        "/api/note-templates/render",
        json={"template_id": template["id"], "variables": {"title": "RSA", "author": "nyx"}},
    )
    assert rendered.status_code == 200
    assert rendered.json()["body"].startswith("## RSA")
    assert rendered.json()["variable_count"] == 2


def test_api_error_envelopes(client: TestClient, seeded: object) -> None:
    """Service errors use the shared envelope with stable status codes."""
    blank = client.post(
        "/api/notes",
        json={
            "challenge_id": CHALLENGE_ID,
            "member_id": MEMBER_ID,
            "title": "   ",
            "body": "body",
        },
    )
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "validation_error"

    not_found = client.get("/api/notes/does-not-exist")
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "not_found"

    duplicate = client.post(
        "/api/note-templates",
        json={"name": "Duplicate", "body": "one"},
    )
    assert duplicate.status_code == 201
    again = client.post(
        "/api/note-templates",
        json={"name": "duplicate", "body": "two"},
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "conflict"

    undecodable = client.get("/api/notes", params={"pinned": "not-a-bool"})
    assert undecodable.status_code == 422
