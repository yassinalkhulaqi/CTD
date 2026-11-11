"""Note management for the challenge board."""

from __future__ import annotations

import uuid

from ctf_team_dashboard.domain.enums import EventKind
from ctf_team_dashboard.domain.models import Note, utcnow
from ctf_team_dashboard.errors import NotFoundError, PermissionDeniedError, ValidationError
from ctf_team_dashboard.repositories import Repositories

MAX_NOTE_LENGTH = 4_000


class NoteService:
    """Business rules for the notes attached to a challenge."""

    def __init__(self, repositories: Repositories | None = None) -> None:
        self.repositories = repositories or Repositories()

    def list_notes(self, challenge_id: str) -> list[Note]:
        """Return the notes attached to a challenge.

        Args:
            challenge_id: The identifier of the challenge.

        Returns:
            The notes, oldest first.
        """
        if self.repositories.challenges.get(challenge_id) is None:
            raise NotFoundError(f"Challenge {challenge_id!r} does not exist")
        return self.repositories.notes.list_for_challenge(challenge_id)

    def list_member_notes(self, member_id: str) -> list[Note]:
        """Return the notes written by a member."""
        return self.repositories.notes.list_for_member(member_id)

    def get_note(self, note_id: str) -> Note:
        """Return a note or raise :class:`NotFoundError`."""
        note = self.repositories.notes.get(note_id)
        if note is None:
            raise NotFoundError(f"Note {note_id!r} does not exist")
        return note

    def add_note(self, *, challenge_id: str, member_id: str, body: str) -> Note:
        """Attach a note to a challenge.

        Args:
            challenge_id: The identifier of the challenge.
            member_id: The identifier of the author.
            body: The content of the note.

        Returns:
            The persisted note.

        Raises:
            NotFoundError: When the challenge or the member is unknown.
            ValidationError: When the body is empty or too long.
        """
        challenge = self.repositories.challenges.get(challenge_id)
        if challenge is None:
            raise NotFoundError(f"Challenge {challenge_id!r} does not exist")
        member = self.repositories.members.get(member_id)
        if member is None:
            raise NotFoundError(f"Member {member_id!r} does not exist")

        cleaned = body.strip()
        if not cleaned:
            raise ValidationError("A note must not be empty")
        if len(cleaned) > MAX_NOTE_LENGTH:
            raise ValidationError(f"A note must not exceed {MAX_NOTE_LENGTH} characters")

        now = utcnow()
        note = Note(
            id=f"note-{uuid.uuid4().hex[:12]}",
            challenge_id=challenge_id,
            member_id=member_id,
            body=cleaned,
            created_at=now,
            updated_at=now,
        )
        self.repositories.notes.create(note)
        self.repositories.events.append(
            EventKind.CHALLENGE_UPDATED,
            team_id=challenge.team_id,
            payload={"id": challenge_id, "action": "note.added", "note_id": note.id},
        )
        return note

    def update_note(self, note_id: str, *, body: str, member_id: str) -> Note:
        """Update the body of a note.

        Args:
            note_id: The identifier of the note.
            body: The new content of the note.
            member_id: The identifier of the author.

        Returns:
            The updated note.

        Raises:
            NotFoundError: When the note is unknown.
            PermissionDeniedError: When the author is not the caller.
            ValidationError: When the body is empty or too long.
        """
        note = self.get_note(note_id)
        if note.member_id != member_id:
            raise PermissionDeniedError("Only the author may edit a note")
        cleaned = body.strip()
        if not cleaned:
            raise ValidationError("A note must not be empty")
        if len(cleaned) > MAX_NOTE_LENGTH:
            raise ValidationError(f"A note must not exceed {MAX_NOTE_LENGTH} characters")
        updated = Note(
            id=note.id,
            challenge_id=note.challenge_id,
            member_id=note.member_id,
            body=cleaned,
            created_at=note.created_at,
            updated_at=utcnow(),
        )
        self.repositories.notes.update(updated)
        return updated

    def delete_note(self, note_id: str, *, member_id: str) -> None:
        """Delete a note written by a member.

        Args:
            note_id: The identifier of the note.
            member_id: The identifier of the author.

        Raises:
            NotFoundError: When the note is unknown.
            PermissionDeniedError: When the author is not the caller.
        """
        note = self.get_note(note_id)
        if note.member_id != member_id:
            raise PermissionDeniedError("Only the author may delete a note")
        self.repositories.notes.delete(note_id)
