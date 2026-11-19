"""HTTP endpoints for the notes workspace feature."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ctf_team_dashboard.features.notes_workspace.models import (
    NoteEntry,
    NotesWorkspaceSummary,
    NoteTemplate,
    RevisionDescriptor,
    TemplateCategory,
)
from ctf_team_dashboard.features.notes_workspace.schemas import (
    ChallengeNotesSummaryRead,
    HeadingRead,
    NoteCreate,
    NoteEntryRead,
    NoteRevisionRead,
    NotesSummaryRead,
    NoteTemplateCreate,
    NoteTemplateRead,
    NoteUpdate,
    PinRequest,
    TemplateRenderRequest,
    TemplateRenderResult,
)
from ctf_team_dashboard.features.notes_workspace.service import NotesWorkspaceService

router = APIRouter(prefix="/api/notes", tags=["notes"])
template_router = APIRouter(prefix="/api/note-templates", tags=["note-templates"])


def get_notes_service() -> NotesWorkspaceService:
    """Dependency returning a service bound to the shared database."""
    return NotesWorkspaceService()


NotesServiceDep = Annotated[NotesWorkspaceService, Depends(get_notes_service)]


def _note_to_read(note: NoteEntry) -> NoteEntryRead:
    """Map a domain note onto its API representation."""
    return NoteEntryRead(
        id=note.id,
        challenge_id=note.challenge_id,
        member_id=note.member_id,
        title=note.title,
        body=note.body,
        format=note.format,
        tags=list(note.tags),
        pinned=note.pinned,
        version=note.version,
        created_at=note.created_at,
        updated_at=note.updated_at,
        word_count=note.word_count,
        reading_time_minutes=note.reading_time_minutes,
        excerpt=note.excerpt,
        headings=[
            HeadingRead(
                level=heading.level,
                text=heading.text,
                line=heading.line,
                anchor=heading.anchor,
                indent=heading.indent,
            )
            for heading in note.headings
        ],
        tag_count=note.tag_count,
        is_pinned=note.is_pinned,
    )


def _revision_to_read(descriptor: RevisionDescriptor) -> NoteRevisionRead:
    """Map a revision descriptor onto its API representation."""
    revision = descriptor.revision
    return NoteRevisionRead(
        id=revision.id,
        note_id=revision.note_id,
        version=revision.version,
        body=revision.body,
        author_id=revision.author_id,
        created_at=revision.created_at,
        added=descriptor.summary.added,
        removed=descriptor.summary.removed,
        net=descriptor.summary.net,
        changed=descriptor.summary.changed,
        magnitude=descriptor.summary.magnitude,
        is_latest=descriptor.is_latest,
        change_summary=descriptor.summary.describe(),
    )


def _template_to_read(template: NoteTemplate) -> NoteTemplateRead:
    """Map a domain template onto its API representation."""
    return NoteTemplateRead(
        id=template.id,
        name=template.name,
        category=template.category,
        body=template.body,
        variables=list(template.variables),
        variable_count=template.variable_count,
        line_count=template.line_count,
    )


def _summary_to_read(summary: NotesWorkspaceSummary) -> NotesSummaryRead:
    """Map a domain summary onto its API representation."""
    return NotesSummaryRead(
        challenges=[
            ChallengeNotesSummaryRead(
                challenge_id=item.challenge_id,
                note_count=item.note_count,
                pinned_count=item.pinned_count,
                revision_count=item.revision_count,
                word_count=item.word_count,
                unique_authors=item.unique_authors,
                top_tags=list(item.top_tags),
                average_words=item.average_words,
                pinned_ratio=item.pinned_ratio,
            )
            for item in summary.challenges
        ],
        total_notes=summary.total_notes,
        total_revisions=summary.total_revisions,
        total_words=summary.total_words,
        pinned_notes=summary.pinned_notes,
        unique_tags=list(summary.unique_tags),
        generated_at=summary.generated_at,
        challenge_count=summary.challenge_count,
        average_words=summary.average_words,
    )


@router.get("", response_model=list[NoteEntryRead])
def list_notes(
    service: NotesServiceDep,
    challenge_id: str | None = None,
    member_id: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    pinned: bool = False,
) -> list[NoteEntryRead]:
    """Return notes filtered by challenge, author, tag and text."""
    notes = service.list_notes(
        challenge_id=challenge_id,
        member_id=member_id,
        tag=tag,
        query=q,
        pinned_only=pinned,
    )
    return [_note_to_read(note) for note in notes]


@router.post(
    "",
    response_model=NoteEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_note(payload: NoteCreate, service: NotesServiceDep) -> NoteEntryRead:
    """Create a new workspace note."""
    note = service.create_note(
        challenge_id=payload.challenge_id,
        member_id=payload.member_id,
        title=payload.title,
        body=payload.body,
        note_format=payload.format,
        tags=payload.tags,
        pinned=payload.pinned,
    )
    return _note_to_read(note)


@router.get("/summary", response_model=NotesSummaryRead)
def get_summary(
    service: NotesServiceDep,
    challenge_id: str | None = None,
) -> NotesSummaryRead:
    """Return per-challenge and workspace wide note statistics."""
    return _summary_to_read(service.summary(challenge_id=challenge_id))


@router.get("/{note_id}", response_model=NoteEntryRead)
def get_note(note_id: str, service: NotesServiceDep) -> NoteEntryRead:
    """Return a single note."""
    return _note_to_read(service.get_note(note_id))


@router.patch("/{note_id}", response_model=NoteEntryRead)
def update_note(
    note_id: str,
    payload: NoteUpdate,
    service: NotesServiceDep,
) -> NoteEntryRead:
    """Update a note, optionally guarding against a stale version."""
    note = service.update_note(
        note_id,
        title=payload.title,
        body=payload.body,
        note_format=payload.format,
        tags=payload.tags,
        expected_version=payload.expected_version,
        author_id=payload.author_id,
    )
    return _note_to_read(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: str, service: NotesServiceDep) -> None:
    """Delete a note and its revision history."""
    service.delete_note(note_id)


@router.post("/{note_id}/pin", response_model=NoteEntryRead)
def pin_note(
    note_id: str,
    payload: PinRequest,
    service: NotesServiceDep,
) -> NoteEntryRead:
    """Pin, unpin or toggle the pinned state of a note."""
    return _note_to_read(service.set_pinned(note_id, payload.pinned))


@router.get("/{note_id}/revisions", response_model=list[NoteRevisionRead])
def list_revisions(
    note_id: str,
    service: NotesServiceDep,
) -> list[NoteRevisionRead]:
    """Return the revision timeline of a note."""
    return [_revision_to_read(item) for item in service.list_revisions(note_id)]


@template_router.get("", response_model=list[NoteTemplateRead])
def list_templates(
    service: NotesServiceDep,
    category: TemplateCategory | None = None,
) -> list[NoteTemplateRead]:
    """Return note templates, optionally filtered by category."""
    return [_template_to_read(item) for item in service.list_templates(category)]


@template_router.post(
    "",
    response_model=NoteTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    payload: NoteTemplateCreate,
    service: NotesServiceDep,
) -> NoteTemplateRead:
    """Create a reusable note template."""
    template = service.create_template(
        name=payload.name,
        category=payload.category,
        body=payload.body,
    )
    return _template_to_read(template)


@template_router.post("/render", response_model=TemplateRenderResult)
def render_template(
    payload: TemplateRenderRequest,
    service: NotesServiceDep,
) -> TemplateRenderResult:
    """Render a template with the supplied variable values."""
    result = service.render_template(
        template_id=payload.template_id,
        body=payload.body,
        variables=payload.variables,
    )
    return TemplateRenderResult(
        body=result.body,
        used_variables=list(result.used_variables),
        unused_variables=list(result.unused_variables),
        variable_count=result.variable_count,
    )
