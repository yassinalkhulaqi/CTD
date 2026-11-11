"""Challenge detail endpoints: notes, timeline and flag submission."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ctf_team_dashboard.dependencies import require_permission
from ctf_team_dashboard.errors import NotFoundError, ValidationError
from ctf_team_dashboard.repositories import Repositories
from ctf_team_dashboard.schemas import (
    FlagResult,
    FlagSubmission,
    NoteCreate,
    NoteRead,
    NoteUpdate,
    TimelineEntry,
)
from ctf_team_dashboard.security.flags import FlagFormatError, mask_flag, normalise_flag
from ctf_team_dashboard.security.permissions import Permission
from ctf_team_dashboard.services.challenges import ChallengeService
from ctf_team_dashboard.services.notes import NoteService
from ctf_team_dashboard.services.solves import SolveService

router = APIRouter(prefix="/api/challenges", tags=["challenge-detail"])


def get_challenge_services() -> tuple[ChallengeService, NoteService, SolveService]:
    """Dependency returning the services backing the challenge details."""
    return ChallengeService(), NoteService(), SolveService()


ServicesDep = Annotated[
    tuple[ChallengeService, NoteService, SolveService], Depends(get_challenge_services)
]


@router.get("/{challenge_id}/notes", response_model=list[NoteRead])
def list_notes(challenge_id: str, services: ServicesDep) -> list[NoteRead]:
    """Return the notes attached to a challenge."""
    _challenges, notes, _solves = services
    return [
        NoteRead(
            id=note.id,
            challenge_id=note.challenge_id,
            member_id=note.member_id,
            body=note.body,
            preview=note.preview,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
        for note in notes.list_notes(challenge_id)
    ]


@router.post(
    "/{challenge_id}/notes",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    challenge_id: str,
    payload: NoteCreate,
    services: ServicesDep,
    _principal: object = Depends(require_permission(Permission.CHALLENGE_UPDATE)),
) -> NoteRead:
    """Attach a note to a challenge."""
    _challenges, notes, _solves = services
    note = notes.add_note(
        challenge_id=challenge_id,
        member_id=payload.member_id,
        body=payload.body,
    )
    return NoteRead(
        id=note.id,
        challenge_id=note.challenge_id,
        member_id=note.member_id,
        body=note.body,
        preview=note.preview,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.patch("/notes/{note_id}", response_model=NoteRead)
def update_note(
    note_id: str,
    payload: NoteUpdate,
    services: ServicesDep,
    _principal: object = Depends(require_permission(Permission.CHALLENGE_UPDATE)),
) -> NoteRead:
    """Edit a note written by the caller."""
    _challenges, notes, _solves = services
    note = notes.update_note(note_id, body=payload.body, member_id=payload.member_id)
    return NoteRead(
        id=note.id,
        challenge_id=note.challenge_id,
        member_id=note.member_id,
        body=note.body,
        preview=note.preview,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str,
    member_id: str,
    services: ServicesDep,
    _principal: object = Depends(require_permission(Permission.CHALLENGE_UPDATE)),
) -> None:
    """Delete a note written by the caller."""
    _challenges, notes, _solves = services
    notes.delete_note(note_id, member_id=member_id)


@router.get("/{challenge_id}/timeline", response_model=list[TimelineEntry])
def get_timeline(challenge_id: str, services: ServicesDep) -> list[TimelineEntry]:
    """Return the solves recorded for a challenge, newest first."""
    _challenges, _notes, solves = services
    repositories = Repositories()
    members = {member.id: member for member in repositories.members.list_all()}

    entries = [
        TimelineEntry(
            solve_id=solve.id,
            member_id=solve.member_id,
            member_handle=members[solve.member_id].handle
            if solve.member_id in members
            else "unknown",
            points_awarded=solve.points_awarded,
            solved_at=solve.solved_at,
            masked_flag=mask_flag(solve.flag) if solve.flag else "",
        )
        for solve in solves.list_solves(challenge_id=challenge_id)
    ]
    return sorted(entries, key=lambda entry: entry.solved_at, reverse=True)


@router.post("/{challenge_id}/flags", response_model=FlagResult)
def submit_flag(
    challenge_id: str,
    payload: FlagSubmission,
    services: ServicesDep,
    _principal: object = Depends(require_permission(Permission.SOLVE_CREATE)),
) -> FlagResult:
    """Submit a flag for a challenge.

    The flag format is validated before the solve is recorded so a typo is
    reported immediately instead of scoring an empty solve.
    """
    _challenges, _notes, solves = services

    if payload.challenge_id != challenge_id:
        raise ValidationError("The challenge identifier does not match the payload")

    try:
        normalised = normalise_flag(payload.flag)
    except FlagFormatError as exc:
        return FlagResult(accepted=False, message=str(exc))

    try:
        solve = solves.record_solve(
            challenge_id=challenge_id,
            member_id=payload.member_id,
            flag=normalised,
        )
    except NotFoundError as exc:
        return FlagResult(accepted=False, message=str(exc))
    except ValidationError as exc:
        return FlagResult(accepted=False, message=str(exc))

    return FlagResult(
        accepted=True,
        message=f"Solve recorded for {solve.points_awarded} points",
        points_awarded=solve.points_awarded,
        solve_id=solve.id,
    )
