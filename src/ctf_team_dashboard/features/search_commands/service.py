"""Business rules for indexing, querying and executing commands."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.search_commands.models import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    Command,
    CommandExecution,
    Highlight,
    IndexReport,
    ParsedQuery,
    SearchDocument,
    SearchKind,
    SearchOutcome,
    SearchResult,
    SearchStats,
    build_snippet,
    find_token_spans,
    fold_text,
    match_commands,
    parse_filters,
    rank_results,
    score_document,
)
from ctf_team_dashboard.features.search_commands.store import SearchStore
from ctf_team_dashboard.repositories.challenges import ChallengeRepository
from ctf_team_dashboard.repositories.members import MemberRepository
from ctf_team_dashboard.repositories.teams import TeamRepository

DEFAULT_COMMANDS: tuple[Command, ...] = (
    Command(
        "nav.search",
        "Focus search",
        "Jump to global search at /search",
        "Workspace",
        "Mod+K",
        ("find", "query", "lookup"),
    ),
    Command(
        "nav.challenges",
        "Open challenges",
        "Open the challenge board at /challenges",
        "Workspace",
        "G C",
        ("board", "puzzles", "tasks"),
    ),
    Command(
        "nav.teams",
        "Open teams",
        "Open the scoreboard at /teams",
        "Workspace",
        "G T",
        ("scoreboard", "ranking"),
    ),
    Command(
        "nav.members",
        "Open members",
        "Open the roster at /members",
        "Workspace",
        "G M",
        ("roster", "people"),
    ),
    Command(
        "nav.overview",
        "Open overview",
        "Open the dashboard overview at /overview",
        "Workspace",
        "G O",
        ("home", "dashboard"),
    ),
    Command(
        "search.kind.challenge",
        "Filter challenges",
        "Search only challenge documents",
        "Search",
        "",
        ("kind challenge", "web pwn crypto"),
    ),
    Command(
        "search.kind.member",
        "Filter members",
        "Search only member documents",
        "Search",
        "",
        ("kind member", "people handles"),
    ),
    Command(
        "search.reindex",
        "Rebuild index",
        "Reindex dashboard entities",
        "Maintenance",
        "",
        ("refresh", "sync", "reload"),
    ),
)

MAX_ARGUMENT_LENGTH = 200
MAX_TITLE_LENGTH = 200
MAX_BODY_LENGTH = 20_000
TOP_TAG_COUNT = 5
PATH_PATTERN = re.compile(r"(/[\w/{}-]+)")


def _require_text(value: str, field: str, maximum: int) -> str:
    """Validate a required text field and return its trimmed value."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must not be empty", details={"field": field})
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise ValidationError(
            f"{field} must be at most {maximum} characters",
            details={"field": field, "maximum": maximum},
        )
    return cleaned


def _optional_text(value: str, field: str, maximum: int) -> str:
    """Validate an optional text field and return its trimmed value."""
    cleaned = (value or "").strip()
    if len(cleaned) > maximum:
        raise ValidationError(
            f"{field} must be at most {maximum} characters",
            details={"field": field, "maximum": maximum},
        )
    return cleaned


class SearchService:
    """Coordinate indexing, query parsing, ranking and command execution."""

    def __init__(
        self,
        store: SearchStore | None = None,
        *,
        challenges: ChallengeRepository | None = None,
        teams: TeamRepository | None = None,
        members: MemberRepository | None = None,
    ) -> None:
        self._store = store if store is not None else SearchStore()
        self._challenges = challenges if challenges is not None else ChallengeRepository()
        self._teams = teams if teams is not None else TeamRepository()
        self._members = members if members is not None else MemberRepository()

    @property
    def store(self) -> SearchStore:
        """Return the store used by the service."""
        return self._store

    def parse_query(
        self,
        raw: str,
        *,
        limit: int = DEFAULT_LIMIT,
        kinds: Sequence[str] = (),
        tags: Sequence[str] = (),
    ) -> ParsedQuery:
        """Validate and normalise a raw query string and its explicit filters."""
        if not isinstance(raw, str):
            raise ValidationError("q must be a string", details={"field": "q"})
        if limit < 1 or limit > MAX_LIMIT:
            raise ValidationError(
                f"limit must be between 1 and {MAX_LIMIT}",
                details={"field": "limit", "minimum": 1, "maximum": MAX_LIMIT},
            )
        text, inline_kinds, inline_tags = parse_filters(raw)
        resolved_kinds: list[SearchKind] = []
        for value in (*kinds, *inline_kinds):
            kind = SearchKind.parse(value, SearchKind.CUSTOM)
            if kind is SearchKind.CUSTOM and value.strip().lower() != "custom":
                raise ValidationError(
                    f"unknown search kind: {value}",
                    details={"field": "kind", "value": value},
                )
            if kind not in resolved_kinds:
                resolved_kinds.append(kind)

        resolved_tags: list[str] = []
        for value in (*tags, *inline_tags):
            folded = fold_text(value)
            if folded and folded not in resolved_tags:
                resolved_tags.append(folded)
        return ParsedQuery(
            text=text.strip(),
            kinds=tuple(resolved_kinds),
            tags=tuple(resolved_tags),
            limit=limit,
        )

    def search(
        self,
        raw: str,
        *,
        limit: int = DEFAULT_LIMIT,
        kinds: Sequence[str] = (),
        tags: Sequence[str] = (),
    ) -> SearchOutcome:
        """Parse, filter, score and rank documents for a raw query."""
        query = self.parse_query(raw, limit=limit, kinds=kinds, tags=tags)
        documents = self._store.scan_documents(kinds=query.kinds, tags=query.tags)
        tokens = query.tokens
        results: list[SearchResult] = []
        for document in documents:
            score = score_document(document, tokens, query.phrase)
            if tokens and score <= 0:
                continue
            snippet = build_snippet(document.body, tokens)
            highlights = self._title_highlights(document.title, tokens)
            highlights += snippet.highlights
            results.append(
                SearchResult(
                    document_id=document.id,
                    kind=document.kind,
                    title=document.title,
                    snippet=snippet.text,
                    score=score,
                    highlights=highlights,
                    path=document.path,
                )
            )
        ranked = rank_results(results, query.limit)
        return SearchOutcome(query=query, results=ranked, total_indexed=len(documents))

    @staticmethod
    def _title_highlights(title: str, tokens: Sequence[str]) -> tuple[Highlight, ...]:
        """Build title highlight descriptors for the matched tokens."""
        return tuple(
            Highlight(start, end, title[start:end], "title")
            for start, end in find_token_spans(title, tokens)
        )

    def index_document(self, document: SearchDocument) -> SearchDocument:
        """Validate and upsert a single custom document."""
        self._validate_document(document)
        return self._store.upsert_document(document)

    def index_custom(self, documents: Sequence[SearchDocument]) -> int:
        """Validate and bulk upsert custom documents."""
        for document in documents:
            self._validate_document(document)
        return self._store.bulk_index(documents)

    def delete_document(self, document_id: str) -> None:
        """Remove a document, raising a domain error when it is absent."""
        if not self._store.delete_document(document_id):
            raise NotFoundError(
                f"search document not found: {document_id}",
                details={"document_id": document_id},
            )

    def index_from_repositories(self) -> IndexReport:
        """Rebuild index entries from the read-only dashboard repositories."""
        documents: list[SearchDocument] = []
        by_kind: dict[str, int] = {}
        skipped = 0

        for challenge in self._challenges.list_all():
            documents.append(
                SearchDocument(
                    id=f"challenge-{challenge.id}",
                    kind=SearchKind.CHALLENGE,
                    title=challenge.title,
                    body=challenge.description,
                    tags=(
                        *challenge.tags,
                        challenge.category.value,
                        challenge.difficulty.value,
                        challenge.status.value,
                    ),
                    path=f"/challenges/{challenge.id}",
                    updated_at=challenge.created_at,
                )
            )
        for team in self._teams.list_all():
            documents.append(
                SearchDocument(
                    id=f"team-{team.id}",
                    kind=SearchKind.TEAM,
                    title=team.name,
                    body=team.description,
                    tags=(team.slug,),
                    path=f"/teams/{team.id}",
                    updated_at=team.created_at,
                )
            )
        for member in self._members.list_all():
            documents.append(
                SearchDocument(
                    id=f"member-{member.id}",
                    kind=SearchKind.MEMBER,
                    title=member.label,
                    body=f"@{member.handle} — {member.role.value}",
                    tags=(member.handle, member.role.value),
                    path="/members",
                    updated_at=member.joined_at,
                )
            )

        for document in documents:
            try:
                self._validate_document(document)
            except ValidationError:
                skipped += 1
                continue
            by_kind[document.kind.value] = by_kind.get(document.kind.value, 0) + 1

        written = self._store.bulk_index(documents)
        return IndexReport(
            indexed=written,
            by_kind=dict(sorted(by_kind.items())),
            skipped=skipped,
        )

    @staticmethod
    def _validate_document(document: SearchDocument) -> None:
        """Reject documents with invalid identifiers or oversized fields."""
        _require_text(document.id, "id", MAX_TITLE_LENGTH)
        _require_text(document.title, "title", MAX_TITLE_LENGTH)
        if len(document.body) > MAX_BODY_LENGTH:
            raise ValidationError(
                "body is too long",
                details={"field": "body", "maximum": MAX_BODY_LENGTH},
            )
        if document.path and not document.path.startswith("/"):
            raise ValidationError("path must start with a slash", details={"field": "path"})

    def ensure_default_commands(self) -> int:
        """Register the built-in command catalogue when the registry is empty."""
        if self._store.command_count() > 0:
            return 0
        for command in DEFAULT_COMMANDS:
            self._store.upsert_command(command)
        return len(DEFAULT_COMMANDS)

    def register_command(
        self,
        command_id: str,
        name: str,
        description: str = "",
        group: str = "General",
        shortcut: str = "",
        keywords: Sequence[str] = (),
    ) -> Command:
        """Register a new command, rejecting duplicate identifiers."""
        identifier = _require_text(command_id, "id", MAX_TITLE_LENGTH)
        label = _require_text(name, "name", MAX_TITLE_LENGTH)
        if self._store.get_command(identifier) is not None:
            raise ConflictError(
                f"command already registered: {identifier}",
                details={"command_id": identifier},
            )
        command = Command(
            id=identifier,
            name=label,
            description=_optional_text(description, "description", MAX_BODY_LENGTH),
            group=_require_text(group, "group", MAX_TITLE_LENGTH),
            shortcut=_optional_text(shortcut, "shortcut", 60),
            keywords=tuple(
                dict.fromkeys(keyword.strip() for keyword in keywords if keyword.strip())
            ),
        )
        return self._store.upsert_command(command)

    def list_commands(self, query: str = "", *, group: str | None = None) -> tuple[Command, ...]:
        """List commands optionally filtered by group and fuzzy query."""
        self.ensure_default_commands()
        commands = self._store.list_commands(group=group)
        if not query.strip():
            return tuple(commands)
        return tuple(match.command for match in match_commands(commands, query))

    def execute_command(self, command_id: str, arguments: str = "") -> CommandExecution:
        """Resolve a command into an executable descriptor."""
        self.ensure_default_commands()
        command = self._store.get_command(command_id)
        if command is None:
            raise NotFoundError(
                f"command not found: {command_id}", details={"command_id": command_id}
            )
        if len(arguments) > MAX_ARGUMENT_LENGTH:
            raise ValidationError(
                f"arguments must be at most {MAX_ARGUMENT_LENGTH} characters",
                details={"field": "arguments"},
            )
        target = command.target_for(arguments.strip())
        action = "navigate" if PATH_PATTERN.search(target) else "action"
        verb = "Open" if action == "navigate" else "Run"
        return CommandExecution(
            command_id=command.id,
            name=command.name,
            action=action,
            target=target,
            message=f"{verb} {command.name}",
            arguments=arguments.strip(),
        )

    def stats(self) -> SearchStats:
        """Return aggregate statistics for the index and command registry."""
        counts = Counter(tag for tag in self._store.all_tags() if tag.strip())
        top = tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:TOP_TAG_COUNT])
        by_kind = dict(sorted(self._store.documents_by_kind().items()))
        return SearchStats(
            document_count=self._store.document_count(),
            command_count=self._store.command_count(),
            documents_by_kind=by_kind,
            top_tags=top,
            average_body_length=self._store.average_body_length(),
        )

    def rebuild(self) -> SearchStats:
        """Clear custom content, rebuild from repositories and return stats."""
        self._store.clear_documents()
        self.index_from_repositories()
        return self.stats()
