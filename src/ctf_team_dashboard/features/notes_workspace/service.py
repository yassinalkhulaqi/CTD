"""Business rules and orchestration for the notes workspace.

The service is the only component allowed to reject invalid input or to decide
when a new revision must be created. It raises the shared typed errors so the
HTTP layer can map them without understanding the domain.
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable, Mapping

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.notes_workspace.models import (
    MAX_BODY_LENGTH,
    MAX_TITLE_LENGTH,
    TEMPLATE_MAX_VARIABLES,
    ChallengeNoteSummary,
    NoteEntry,
    NoteFormat,
    NoteRevision,
    NotesWorkspaceSummary,
    NoteTemplate,
    RenderResult,
    RevisionDescriptor,
    TemplateCategory,
    extract_variables,
    normalise_tags,
    render_variables,
    summarise_change,
)
from ctf_team_dashboard.features.notes_workspace.store import NotesStore


def _identifier(prefix: str) -> str:
    """Generate a short, readable identifier.

    Args:
        prefix: The prefix used for the identifier.

    Returns:
        A unique identifier such as ``note-3f1c2a9b7d4e``.
    """
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _clean_text(value: str, label: str, maximum: int) -> str:
    """Trim, validate and bound a required text value.

    Args:
        value: The raw value.
        label: The field name used in error messages.
        maximum: The maximum accepted length.

    Returns:
        The trimmed value.

    Raises:
        ValidationError: When the value is empty or too long.
    """
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{label} must not be empty", details={"field": label})
    if len(cleaned) > maximum:
        raise ValidationError(
            f"{label} must not exceed {maximum} characters",
            details={"field": label, "maximum": maximum},
        )
    return cleaned


def _clean_identifier(value: str, label: str) -> str:
    """Validate an identifier supplied by a caller.

    Args:
        value: The raw identifier.
        label: The field name used in error messages.

    Returns:
        The trimmed identifier.
    """
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{label} must not be empty", details={"field": label})
    if len(cleaned) > 120:
        raise ValidationError(f"{label} is too long", details={"field": label})
    return cleaned


class NotesWorkspaceService:
    """Application rules for authoring and organising challenge notes."""

    def __init__(self, store: NotesStore | None = None) -> None:
        self.store = store or NotesStore()

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------
    def list_notes(
        self,
        *,
        challenge_id: str | None = None,
        member_id: str | None = None,
        tag: str | None = None,
        query: str | None = None,
        pinned_only: bool = False,
    ) -> list[NoteEntry]:
        """Return notes matching the supplied filters.

        Args:
            challenge_id: Restrict results to one challenge.
            member_id: Restrict results to one author.
            tag: Restrict results to one normalised tag.
            query: Free text matched against the title, body and tags.
            pinned_only: Restrict results to pinned notes.

        Returns:
            The matching notes in display order.
        """
        tags = normalise_tags([tag]) if tag else ()
        return self.store.notes.search(
            query=query,
            tags=tags,
            challenge_id=challenge_id,
            member_id=member_id,
            pinned_only=pinned_only,
        )

    def get_note(self, note_id: str) -> NoteEntry:
        """Return a note or raise :class:`NotFoundError`."""
        note = self.store.notes.get(note_id)
        if note is None:
            raise NotFoundError(f"Note {note_id!r} does not exist")
        return note

    def create_note(
        self,
        *,
        challenge_id: str,
        member_id: str,
        title: str,
        body: str,
        note_format: NoteFormat = NoteFormat.MARKDOWN,
        tags: Iterable[str] = (),
        pinned: bool = False,
    ) -> NoteEntry:
        """Create a note together with its first revision.

        Args:
            challenge_id: The challenge the note belongs to.
            member_id: The author of the note.
            title: The note title.
            body: The note body.
            note_format: The rendering mode of the body.
            tags: Raw tags, normalised before persistence.
            pinned: Whether the note starts pinned.

        Returns:
            The persisted note.
        """
        clean_challenge = _clean_identifier(challenge_id, "challenge_id")
        clean_member = _clean_identifier(member_id, "member_id")
        clean_title = _clean_text(title, "title", MAX_TITLE_LENGTH)
        clean_body = _clean_text(body, "body", MAX_BODY_LENGTH)
        now = utcnow()
        note = NoteEntry(
            id=_identifier("note"),
            challenge_id=clean_challenge,
            member_id=clean_member,
            title=clean_title,
            body=clean_body,
            format=note_format,
            tags=normalise_tags(tags),
            pinned=pinned,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.store.notes.create(note)
        self.store.revisions.create(
            NoteRevision(
                id=_identifier("rev"),
                note_id=note.id,
                version=note.version,
                body=note.body,
                author_id=note.member_id,
                created_at=now,
            )
        )
        return note

    def update_note(
        self,
        note_id: str,
        *,
        title: str | None = None,
        body: str | None = None,
        note_format: NoteFormat | None = None,
        tags: Iterable[str] | None = None,
        expected_version: int | None = None,
        author_id: str | None = None,
    ) -> NoteEntry:
        """Update a note, creating a revision when its body changed.

        Args:
            note_id: The identifier of the note.
            title: Replacement title, or ``None`` to keep the current value.
            body: Replacement body, or ``None`` to keep the current value.
            note_format: Replacement rendering mode.
            tags: Replacement raw tags.
            expected_version: Version the caller believes it is editing.
            author_id: The member saving the change, used for revision metadata.

        Returns:
            The updated note.

        Raises:
            ConflictError: When ``expected_version`` is stale.
            ValidationError: When the merged title or body is invalid.
        """
        current = self.get_note(note_id)
        self._assert_version(current, expected_version)
        next_title = (
            _clean_text(title, "title", MAX_TITLE_LENGTH) if title is not None else current.title
        )
        next_body = _clean_text(body, "body", MAX_BODY_LENGTH) if body is not None else current.body
        next_format = note_format if note_format is not None else current.format
        next_tags = normalise_tags(tags) if tags is not None else current.tags
        body_changed = next_body != current.body
        next_version = current.version + 1 if body_changed else current.version
        updated = NoteEntry(
            id=current.id,
            challenge_id=current.challenge_id,
            member_id=current.member_id,
            title=next_title,
            body=next_body,
            format=next_format,
            tags=next_tags,
            pinned=current.pinned,
            version=next_version,
            created_at=current.created_at,
            updated_at=utcnow(),
        )
        self.store.notes.update(updated)
        if body_changed:
            self.store.revisions.create(
                NoteRevision(
                    id=_identifier("rev"),
                    note_id=updated.id,
                    version=next_version,
                    body=updated.body,
                    author_id=author_id or current.member_id,
                    created_at=updated.updated_at,
                )
            )
        return updated

    def _assert_version(self, note: NoteEntry, expected_version: int | None) -> None:
        """Reject a write based on an out of date version number.

        Args:
            note: The persisted note.
            expected_version: The version the caller edited, if supplied.

        Raises:
            ConflictError: When the supplied version does not match.
        """
        if expected_version is None:
            return
        if expected_version < 1:
            raise ValidationError("expected_version must be at least 1")
        if expected_version != note.version:
            raise ConflictError(
                "The note was updated by someone else",
                details={"expected_version": expected_version, "current_version": note.version},
            )

    def delete_note(self, note_id: str) -> None:
        """Delete a note and all of its revisions."""
        self.get_note(note_id)
        self.store.revisions.delete_for_note(note_id)
        self.store.notes.delete(note_id)

    def set_pinned(self, note_id: str, pinned: bool | None = None) -> NoteEntry:
        """Pin, unpin or toggle a note.

        Args:
            note_id: The identifier of the note.
            pinned: Explicit state, or ``None`` to toggle the current state.

        Returns:
            The note with its new pinned state.
        """
        current = self.get_note(note_id)
        target = not current.pinned if pinned is None else pinned
        updated = self.store.notes.set_pinned(note_id, target)
        if updated is None:
            raise NotFoundError(f"Note {note_id!r} does not exist")
        return updated

    def list_revisions(self, note_id: str) -> list[RevisionDescriptor]:
        """Return the revision timeline of a note with per-step diffs."""
        self.get_note(note_id)
        revisions = self.store.revisions.list_for_note(note_id)
        descriptors: list[RevisionDescriptor] = []
        previous: NoteRevision | None = None
        for index, revision in enumerate(revisions):
            if previous is None:
                summary = summarise_change("", revision.body)
            else:
                summary = summarise_change(previous.body, revision.body)
            descriptors.append(
                RevisionDescriptor(
                    revision=revision,
                    summary=summary,
                    is_latest=index == len(revisions) - 1,
                )
            )
            previous = revision
        return descriptors

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------
    def list_templates(self, category: TemplateCategory | None = None) -> list[NoteTemplate]:
        """Return templates, optionally restricted to one category."""
        return self.store.templates.list_all(category)

    def create_template(self, *, name: str, category: TemplateCategory, body: str) -> NoteTemplate:
        """Create a reusable template with a unique name.

        Raises:
            ValidationError: When the name or body is empty or too long.
            ConflictError: When a template with the same name already exists.
        """
        clean_name = _clean_text(name, "name", 120)
        clean_body = _clean_text(body, "body", MAX_BODY_LENGTH)
        if self.store.templates.find_by_name(clean_name) is not None:
            raise ConflictError(
                f"A template named {clean_name!r} already exists",
                details={"name": clean_name},
            )
        template = NoteTemplate(
            id=_identifier("tpl"),
            name=clean_name,
            category=category,
            body=clean_body,
        )
        return self.store.templates.create(template)

    def get_template(self, template_id: str) -> NoteTemplate:
        """Return a template or raise :class:`NotFoundError`."""
        template = self.store.templates.get(template_id)
        if template is None:
            raise NotFoundError(f"Template {template_id!r} does not exist")
        return template

    def render_template(
        self,
        *,
        template_id: str | None = None,
        body: str | None = None,
        variables: Mapping[str, str] | None = None,
    ) -> RenderResult:
        """Render a template with ``{{variable}}`` substitution.

        Args:
            template_id: Id of a stored template to render.
            body: Inline template body, used when no id is supplied.
            variables: Values keyed by placeholder name.

        Returns:
            The rendered body and the variable bookkeeping.

        Raises:
            ValidationError: When a required variable is missing.
            NotFoundError: When an unknown template id is supplied.
        """
        supplied = dict(variables or {})
        if len(supplied) > TEMPLATE_MAX_VARIABLES:
            raise ValidationError(
                f"At most {TEMPLATE_MAX_VARIABLES} template variables are allowed"
            )
        if template_id is not None:
            source = self.get_template(template_id).body
        elif body is not None:
            source = body
        else:
            raise ValidationError("Either template_id or body is required")
        required = extract_variables(source)
        missing = tuple(name for name in required if name not in supplied)
        if missing:
            raise ValidationError(
                "Missing template variables: " + ", ".join(missing),
                details={"missing": list(missing)},
            )
        unused = tuple(sorted(name for name in supplied if name not in required))
        used = tuple(name for name in required if name in supplied)
        return RenderResult(
            body=render_variables(source, supplied),
            used_variables=used,
            unused_variables=unused,
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------
    def summary(self, *, challenge_id: str | None = None) -> NotesWorkspaceSummary:
        """Aggregate notes into per-challenge and workspace wide statistics.

        Args:
            challenge_id: Optional restriction to one challenge.

        Returns:
            The aggregated summary.
        """
        notes = (
            self.store.notes.list_for_challenge(challenge_id)
            if challenge_id
            else self.store.notes.list_all()
        )
        buckets: dict[str, list[NoteEntry]] = {}
        for note in notes:
            buckets.setdefault(note.challenge_id, []).append(note)

        summaries: list[ChallengeNoteSummary] = []
        all_tags: set[str] = set()
        all_revisions = 0
        for bucket_id, items in buckets.items():
            tag_counter: Counter[str] = Counter()
            authors: set[str] = set()
            bucket_revisions = 0
            for item in items:
                tag_counter.update(item.tags)
                authors.add(item.member_id)
                all_tags.update(item.tags)
                bucket_revisions += self.store.revisions.count_for_note(item.id)
            all_revisions += bucket_revisions
            top_tags = tuple(
                tag
                for tag, _count in sorted(
                    tag_counter.items(), key=lambda entry: (-entry[1], entry[0])
                )[:5]
            )
            summaries.append(
                ChallengeNoteSummary(
                    challenge_id=bucket_id,
                    note_count=len(items),
                    pinned_count=sum(1 for item in items if item.pinned),
                    revision_count=bucket_revisions,
                    word_count=sum(item.word_count for item in items),
                    unique_authors=len(authors),
                    top_tags=top_tags,
                )
            )
        summaries.sort(key=lambda item: (-item.note_count, item.challenge_id))
        return NotesWorkspaceSummary(
            challenges=tuple(summaries),
            total_notes=len(notes),
            total_revisions=all_revisions,
            total_words=sum(item.word_count for item in notes),
            pinned_notes=sum(1 for item in notes if item.pinned),
            unique_tags=tuple(sorted(all_tags)),
            generated_at=utcnow(),
        )
