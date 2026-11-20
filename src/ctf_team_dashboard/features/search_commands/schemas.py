"""Typed request and response schemas for the search API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.features.search_commands.models import SearchKind


class ApiModel(BaseModel):
    """Base model enabling conversion from slotted domain objects."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SearchDocumentCreate(ApiModel):
    """Payload accepted when indexing a custom document."""

    id: str = Field(min_length=1, max_length=200)
    kind: SearchKind = SearchKind.CUSTOM
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=20_000)
    tags: list[str] = Field(default_factory=list, max_length=32)
    path: str = Field(default="/", max_length=200)
    updated_at: datetime | None = None


class SearchDocumentRead(ApiModel):
    """A document as represented by the search API."""

    id: str
    kind: SearchKind
    title: str
    body: str
    tags: list[str]
    path: str
    updated_at: datetime
    key: str


class HighlightRead(ApiModel):
    """A highlighted span within a result field."""

    start: int
    end: int
    text: str
    field: str


class SearchResultRead(ApiModel):
    """A ranked search hit."""

    document_id: str
    kind: SearchKind
    title: str
    snippet: str
    score: float
    highlights: list[HighlightRead]
    path: str
    relevance: str


class ParsedQueryRead(ApiModel):
    """Echo of the normalised query used to produce a result set."""

    text: str
    kinds: list[SearchKind]
    tags: list[str]
    limit: int
    tokens: list[str]
    has_filters: bool


class SearchResponseRead(ApiModel):
    """The payload returned by the search endpoint."""

    query: ParsedQueryRead
    results: list[SearchResultRead]
    total_indexed: int
    returned: int


class CommandCreate(ApiModel):
    """Payload accepted when registering a command."""

    id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2_000)
    group: str = Field(default="General", max_length=100)
    shortcut: str = Field(default="", max_length=60)
    keywords: list[str] = Field(default_factory=list, max_length=24)


class CommandRead(ApiModel):
    """A command as represented by the search API."""

    id: str
    name: str
    description: str
    group: str
    shortcut: str
    keywords: list[str]
    initials: str
    shortcut_label: str


class CommandMatchRead(ApiModel):
    """A command with its fuzzy match score."""

    command: CommandRead
    score: float
    level: str


class CommandListRead(ApiModel):
    """The payload returned by the command list endpoint."""

    commands: list[CommandRead]
    groups: list[str]
    total: int


class CommandExecuteRequest(ApiModel):
    """Payload accepted when executing a command."""

    arguments: str = Field(default="", max_length=200)


class CommandExecutionRead(ApiModel):
    """Descriptor describing what a client should do after execution."""

    command_id: str
    name: str
    action: str
    target: str
    message: str
    arguments: str
    is_navigation: bool


class IndexRequest(ApiModel):
    """Payload accepted by the bulk indexing endpoint."""

    documents: list[SearchDocumentCreate] = Field(default_factory=list, max_length=500)
    include_repositories: bool = False
    clear: bool = False


class IndexResponseRead(ApiModel):
    """Summary of an indexing operation."""

    indexed: int
    by_kind: dict[str, int]
    skipped: int
    document_count: int


class SearchStatsRead(ApiModel):
    """Aggregate counters describing the index."""

    document_count: int
    command_count: int
    documents_by_kind: dict[str, int]
    top_tags: list[tuple[str, int]]
    average_body_length: float
    has_documents: bool
    distinct_kinds: int
