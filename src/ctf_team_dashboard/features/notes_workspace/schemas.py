"""Pydantic request and response schemas for the notes workspace API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.features.notes_workspace.models import (
    MAX_BODY_LENGTH,
    MAX_TITLE_LENGTH,
    NoteFormat,
    TemplateCategory,
)


class NotesApiModel(BaseModel):
    """Shared configuration for every schema in this feature."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HeadingRead(NotesApiModel):
    """A Markdown heading extracted from a note body."""

    level: int
    text: str
    line: int
    anchor: str
    indent: int


class NoteEntryRead(NotesApiModel):
    """The API representation of a workspace note."""

    id: str
    challenge_id: str
    member_id: str
    title: str
    body: str
    format: NoteFormat
    tags: list[str]
    pinned: bool
    version: int
    created_at: datetime
    updated_at: datetime
    word_count: int
    reading_time_minutes: float
    excerpt: str
    headings: list[HeadingRead]
    tag_count: int
    is_pinned: bool


class NoteCreate(NotesApiModel):
    """Payload accepted by ``POST /api/notes``."""

    challenge_id: str = Field(min_length=1, max_length=120)
    member_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    body: str = Field(min_length=1, max_length=MAX_BODY_LENGTH)
    format: NoteFormat = NoteFormat.MARKDOWN
    tags: list[str] = Field(default_factory=list, max_length=12)
    pinned: bool = False


class NoteUpdate(NotesApiModel):
    """Payload accepted by ``PATCH /api/notes/{id}``."""

    title: str | None = Field(default=None, min_length=1, max_length=MAX_TITLE_LENGTH)
    body: str | None = Field(default=None, max_length=MAX_BODY_LENGTH)
    format: NoteFormat | None = None
    tags: list[str] | None = Field(default=None, max_length=12)
    expected_version: int | None = Field(default=None, ge=1)
    author_id: str | None = Field(default=None, max_length=120)


class PinRequest(NotesApiModel):
    """Payload accepted by ``POST /api/notes/{id}/pin``."""

    pinned: bool | None = None


class NoteRevisionRead(NotesApiModel):
    """A revision snapshot decorated with its change summary."""

    id: str
    note_id: str
    version: int
    body: str
    author_id: str
    created_at: datetime
    added: int
    removed: int
    net: int
    changed: bool
    magnitude: int
    is_latest: bool
    change_summary: str


class NoteTemplateRead(NotesApiModel):
    """The API representation of a note template."""

    id: str
    name: str
    category: TemplateCategory
    body: str
    variables: list[str]
    variable_count: int
    line_count: int


class NoteTemplateCreate(NotesApiModel):
    """Payload accepted by ``POST /api/note-templates``."""

    name: str = Field(min_length=1, max_length=120)
    category: TemplateCategory = TemplateCategory.GENERAL
    body: str = Field(min_length=1, max_length=MAX_BODY_LENGTH)


class TemplateRenderRequest(NotesApiModel):
    """Payload accepted by ``POST /api/note-templates/render``."""

    template_id: str | None = None
    body: str | None = None
    variables: dict[str, str] = Field(default_factory=dict)


class TemplateRenderResult(NotesApiModel):
    """The rendered template body and variable bookkeeping."""

    body: str
    used_variables: list[str]
    unused_variables: list[str]
    variable_count: int


class ChallengeNotesSummaryRead(NotesApiModel):
    """Aggregated note statistics for one challenge."""

    challenge_id: str
    note_count: int
    pinned_count: int
    revision_count: int
    word_count: int
    unique_authors: int
    top_tags: list[str]
    average_words: float
    pinned_ratio: float


class NotesSummaryRead(NotesApiModel):
    """The workspace wide aggregated payload."""

    challenges: list[ChallengeNotesSummaryRead]
    total_notes: int
    total_revisions: int
    total_words: int
    pinned_notes: int
    unique_tags: list[str]
    generated_at: datetime
    challenge_count: int
    average_words: float
