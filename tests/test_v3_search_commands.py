"""Tests for the unified search index and command palette backend."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from tests.factories import Factory

from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.search_commands.models import (
    Command,
    ParsedQuery,
    SearchDocument,
    SearchKind,
    SearchResult,
    build_snippet,
    command_match_score,
    fold_text,
    match_commands,
    parse_filters,
    rank_results,
    score_document,
    tokenize,
)
from ctf_team_dashboard.features.search_commands.service import SearchService
from ctf_team_dashboard.features.search_commands.store import SearchStore
from ctf_team_dashboard.repositories.challenges import ChallengeRepository
from ctf_team_dashboard.repositories.members import MemberRepository
from ctf_team_dashboard.repositories.teams import TeamRepository


def document(
    identifier: str,
    title: str,
    body: str = "",
    tags: tuple[str, ...] = (),
    kind: SearchKind = SearchKind.CUSTOM,
) -> SearchDocument:
    """Build a deterministic search document for unit tests."""
    return SearchDocument(
        id=identifier,
        kind=kind,
        title=title,
        body=body,
        tags=tags,
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_tokenize_normalises_case_accents_and_stopwords() -> None:
    assert tokenize("The  CAFÉ Web-Shell") == ("cafe", "web", "shell")
    assert tokenize("the and") == ("the", "and")
    assert tokenize("the and", drop_stopwords=False) == ("the", "and")
    assert fold_text("Crème brûlée!") == "creme brulee"


def test_parse_filters_extracts_kinds_and_tags_in_order() -> None:
    text, kinds, tags = parse_filters("web kind:challenge tag:easy kind:team tag:web")
    assert text == "web"
    assert kinds == ("challenge", "team")
    assert tags == ("easy", "web")
    assert parse_filters("kind: tag:") == ("", (), ())


def test_scoring_uses_field_weights_and_prefix_bonus() -> None:
    web = document("a", "Web Challenge", "unrelated prose", ("web", "intro"))
    prose = document("b", "Nothing", "the web appears", ())
    assert score_document(web, ("web",)) == pytest.approx(8.5)
    assert score_document(web, ("web",)) > score_document(prose, ("web",))
    prefix = score_document(web, ("cha",))
    assert 0 < prefix < score_document(web, ("web",))


def test_phrase_bonus_rewards_contiguous_query() -> None:
    ordered = document("a", "Login Bypass", "login bypass guide")
    shuffled = document("b", "Bypass Login", "guide")
    assert score_document(ordered, ("login", "bypass"), "login bypass") > score_document(
        shuffled, ("login", "bypass"), "login bypass"
    )


def test_rank_results_breaks_ties_by_identifier() -> None:
    results = (
        SearchResult("b", SearchKind.CUSTOM, "B", "", 4.0),
        SearchResult("a", SearchKind.CUSTOM, "A", "", 4.0),
        SearchResult("c", SearchKind.CUSTOM, "C", "", 9.0),
    )
    ranked = rank_results(results, limit=2)
    assert [item.document_id for item in ranked] == ["c", "a"]


def test_snippet_builds_highlight_offsets_relative_to_excerpt() -> None:
    text = " ".join(f"word{index}" for index in range(30))
    snippet = build_snippet(text, ("word12",), max_length=60, context=6)
    assert snippet.has_highlights
    assert snippet.highlighted_characters == len("word12")
    for highlight in snippet.highlights:
        assert highlight.field == "body"
        assert snippet.text[highlight.start : highlight.end] == highlight.text
    assert build_snippet("hello world", ("missing",)).text == "hello world"


def test_command_matching_covers_substring_initials_and_keywords() -> None:
    command = Command(
        "nav.challenges",
        "Open challenges",
        "Open the board at /challenges",
        "Workspace",
        "G C",
        ("board", "puzzles"),
    )
    assert command_match_score(command, "challen") >= 8
    assert command_match_score(command, "oc") >= 6
    assert command_match_score(command, "board") >= 5
    assert command_match_score(command, "zzz") == 0
    assert command.initials == "oc"
    assert command.target_for() == "/challenges"


def test_match_commands_orders_by_score_then_identifier() -> None:
    first = Command("b", "Open challenges", keywords=("challenge",))
    second = Command("a", "Open challenges", keywords=("challenge",))
    matches = match_commands([first, second], "challenge")
    assert [match.command.id for match in matches] == ["a", "b"]
    assert matches[0].level == "exact"


def test_parsed_query_validation_and_derived_values() -> None:
    query = ParsedQuery("web shell", (SearchKind.CHALLENGE,), ("easy",), 5)
    assert query.tokens == ("web", "shell")
    assert query.has_filters
    assert query.accepts(document("a", "Shell", tags=("easy",), kind=SearchKind.CHALLENGE))
    assert not query.accepts(document("b", "Shell", kind=SearchKind.TEAM))
    assert "kinds=challenge" in query.summary
    service = SearchService()
    with pytest.raises(ValidationError):
        service.parse_query("web", limit=0)
    with pytest.raises(ValidationError):
        service.parse_query("web", kinds=("unknown",))


def test_store_upsert_scan_and_delete(database: object) -> None:
    store = SearchStore()
    store.upsert_document(document("a", "Alpha", tags=("web",)))
    store.bulk_index(
        [
            document("b", "Beta", tags=("pwn",), kind=SearchKind.CHALLENGE),
            document("c", "Gamma", tags=("web",)),
        ]
    )
    assert store.document_count() == 3
    assert store.get_document("a") is not None
    assert len(store.scan_documents(kinds=(SearchKind.CHALLENGE,))) == 1
    assert len(store.scan_documents(tags=("web",))) == 2
    assert store.documents_by_kind()["custom"] == 2
    assert store.all_tags().count("web") == 2
    assert store.delete_document("a")
    assert not store.delete_document("missing")


def test_service_indexes_read_only_repositories(database: object) -> None:
    factory = Factory(prefix="idx")
    team = TeamRepository().create(factory.team(name="Atom", slug="atom"))
    member = MemberRepository().create(
        factory.member(team_id=team.id, handle="shellfox", display_name="Shell Fox")
    )
    challenge = ChallengeRepository().create(
        factory.challenge(
            team_id=team.id,
            title="Web Shell",
            description="Bypass the login form",
            tags=("web",),
        )
    )
    report = SearchService().index_from_repositories()
    assert report.indexed == 3
    assert report.by_kind == {"challenge": 1, "member": 1, "team": 1}
    assert member.id
    assert challenge.id
    outcome = SearchService().search("shell", kinds=("challenge",))
    assert outcome.results[0].document_id == f"challenge-{challenge.id}"
    assert outcome.results[0].path == f"/challenges/{challenge.id}"


def test_service_custom_index_search_and_stats(database: object) -> None:
    service = SearchService()
    service.index_custom(
        [
            document("a", "Login Bypass", "login bypass notes", ("web",)),
            document("b", "Roster", "member list", ("team",), SearchKind.TEAM),
        ]
    )
    outcome = service.search("login", kinds=("custom",))
    assert outcome.has_results
    assert outcome.results[0].document_id == "a"
    assert outcome.results[0].highlights
    assert service.search("login", kinds=("team",)).returned == 0
    filtered = service.parse_query("tag:web kind:custom", limit=3)
    assert filtered.tags == ("web",)
    assert filtered.limit == 3
    stats = service.stats()
    assert stats.document_count == 2
    assert "web" in {tag for tag, _ in stats.top_tags}
    service.delete_document("a")
    with pytest.raises(NotFoundError):
        service.delete_document("a")


def test_service_command_registration_and_execution(database: object) -> None:
    service = SearchService()
    assert service.ensure_default_commands() == 8
    assert service.ensure_default_commands() == 0
    assert len(service.list_commands()) == 8
    assert len(service.list_commands("oc")) >= 1
    assert len(service.list_commands(group="Workspace")) == 5
    with pytest.raises(ConflictError):
        service.register_command("nav.search", "Duplicate", "")
    created = service.register_command("custom.run", "Run drill", "Run at /drills")
    assert created.initials == "rd"
    execution = service.execute_command(created.id, "alpha")
    assert execution.is_navigation
    assert execution.target == "/drills"
    assert execution.message == "Open Run drill"
    with pytest.raises(NotFoundError):
        service.execute_command("missing")
    with pytest.raises(ValidationError):
        service.execute_command("custom.run", "x" * 201)


def test_api_search_and_index(client: TestClient) -> None:
    response = client.post(
        "/api/search/index",
        json={
            "clear": True,
            "documents": [
                {
                    "id": "api-a",
                    "kind": "custom",
                    "title": "SQL Injection",
                    "body": "sql injection payload list",
                    "tags": ["web"],
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["document_count"] == 1

    found = client.get("/api/search", params={"q": "sql", "kind": "custom"})
    assert found.status_code == 200
    payload = found.json()
    assert payload["query"]["tokens"] == ["sql"]
    assert payload["results"][0]["document_id"] == "api-a"
    assert payload["results"][0]["score"] > 0
    assert payload["returned"] == 1

    empty = client.get("/api/search", params={"q": "sql", "kind": "team"})
    assert empty.json()["returned"] == 0


def test_api_commands_and_stats(client: TestClient) -> None:
    listing = client.get("/api/search/commands")
    assert listing.status_code == 200
    assert listing.json()["total"] == 8
    assert "Workspace" in listing.json()["groups"]
    filtered = client.get("/api/search/commands", params={"q": "oc"})
    assert filtered.json()["total"] >= 1

    created = client.post(
        "/api/search/commands",
        json={
            "id": "api.command",
            "name": "Open reports",
            "description": "Open reports at /reports",
            "group": "Workspace",
            "keywords": ["analytics"],
        },
    )
    assert created.status_code == 201
    executed = client.post(
        "/api/search/commands/api.command/execute",
        json={"arguments": ""},
    )
    assert executed.status_code == 200
    assert executed.json()["target"] == "/reports"
    assert executed.json()["action"] == "navigate"

    stats = client.get("/api/search/stats")
    assert stats.status_code == 200
    assert stats.json()["command_count"] == 9


def test_api_error_envelopes(client: TestClient) -> None:
    invalid_kind = client.get("/api/search", params={"q": "web", "kind": "nope"})
    assert invalid_kind.status_code == 422
    assert invalid_kind.json()["error"]["code"] == "validation_error"

    missing = client.post(
        "/api/search/commands/missing/execute",
        json={"arguments": ""},
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"

    duplicate = client.post(
        "/api/search/commands",
        json={"id": "nav.search", "name": "Duplicate"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"


def test_api_reindex_and_delete_document(client: TestClient, seeded: object) -> None:
    rebuilt = client.post("/api/search/index", json={"include_repositories": True})
    assert rebuilt.status_code == 200
    assert rebuilt.json()["indexed"] > 0
    stats = client.get("/api/search/stats").json()
    assert stats["document_count"] == rebuilt.json()["document_count"]
    first = client.get("/api/search").json()["results"][0]
    deleted = client.delete(f"/api/search/documents/{first['document_id']}")
    assert deleted.status_code == 204
    assert client.delete(f"/api/search/documents/{first['document_id']}").status_code == 404


def test_document_and_result_derived_properties() -> None:
    item = document("a", "Team Alpha", tags=("RED", "red", " blue "))
    assert item.key == "custom:a"
    assert item.normalized_tags == ("red", "blue")
    assert "team alpha red blue" in item.searchable_text
    assert item.describe() == "custom/a: Team Alpha"
    result = SearchResult("a", SearchKind.CUSTOM, "A", "snippet", 13.126)
    assert result.rounded_score == 13.13
    assert result.relevance == "exact"
    assert result.rank_key() == (-13.126, "a")
