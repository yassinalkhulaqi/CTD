"""HTTP endpoints for unified search and the command registry."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.search_commands.models import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    IndexReport,
    SearchDocument,
)
from ctf_team_dashboard.features.search_commands.schemas import (
    CommandCreate,
    CommandExecuteRequest,
    CommandExecutionRead,
    CommandListRead,
    CommandRead,
    IndexRequest,
    IndexResponseRead,
    SearchDocumentCreate,
    SearchResponseRead,
    SearchStatsRead,
)
from ctf_team_dashboard.features.search_commands.service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


def get_search_service() -> SearchService:
    """Dependency returning a service bound to the current database."""
    return SearchService()


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]


def _split_values(values: list[str] | None) -> list[str]:
    """Expand repeated and comma-separated query parameters."""
    result: list[str] = []
    for value in values or ():
        for part in value.split(","):
            cleaned = part.strip()
            if cleaned and cleaned not in result:
                result.append(cleaned)
    return result


def _to_document(payload: SearchDocumentCreate) -> SearchDocument:
    """Map a request schema onto a domain search document."""
    return SearchDocument(
        id=payload.id,
        kind=payload.kind,
        title=payload.title,
        body=payload.body,
        tags=tuple(payload.tags),
        path=payload.path,
        updated_at=payload.updated_at if payload.updated_at is not None else utcnow(),
    )


@router.get("", response_model=SearchResponseRead)
def search(
    service: SearchServiceDep,
    q: str = "",
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    kind: Annotated[list[str] | None, Query()] = None,
    tag: Annotated[list[str] | None, Query()] = None,
) -> SearchResponseRead:
    """Search the index with weighted scoring and optional filters."""
    outcome = service.search(
        q,
        limit=limit,
        kinds=_split_values(kind),
        tags=_split_values(tag),
    )
    return SearchResponseRead.model_validate(outcome)


@router.post("/index", response_model=IndexResponseRead)
def index_documents(
    payload: IndexRequest,
    service: SearchServiceDep,
) -> IndexResponseRead:
    """Upsert custom documents and optionally rebuild from repositories."""
    if payload.clear:
        service.store.clear_documents()
    report = (
        service.index_from_repositories()
        if payload.include_repositories
        else IndexReport(indexed=0, by_kind={}, skipped=0)
    )
    documents = [_to_document(item) for item in payload.documents]
    written = service.index_custom(documents)
    by_kind = dict(report.by_kind)
    for document in documents:
        by_kind[document.kind.value] = by_kind.get(document.kind.value, 0) + 1
    return IndexResponseRead(
        indexed=report.indexed + written,
        by_kind=dict(sorted(by_kind.items())),
        skipped=report.skipped,
        document_count=service.store.document_count(),
    )


@router.get("/commands", response_model=CommandListRead)
def list_commands(
    service: SearchServiceDep,
    q: str = "",
    group: str | None = None,
) -> CommandListRead:
    """List registered commands, optionally filtered by query and group."""
    commands = service.list_commands(q, group=group)
    groups = sorted({command.group for command in commands})
    return CommandListRead(
        commands=[CommandRead.model_validate(command) for command in commands],
        groups=groups,
        total=len(commands),
    )


@router.post(
    "/commands",
    response_model=CommandRead,
    status_code=status.HTTP_201_CREATED,
)
def register_command(
    payload: CommandCreate,
    service: SearchServiceDep,
) -> CommandRead:
    """Register a new command in the palette registry."""
    command = service.register_command(
        payload.id,
        payload.name,
        payload.description,
        payload.group,
        payload.shortcut,
        payload.keywords,
    )
    return CommandRead.model_validate(command)


@router.post("/commands/{command_id}/execute", response_model=CommandExecutionRead)
def execute_command(
    command_id: str,
    payload: CommandExecuteRequest,
    service: SearchServiceDep,
) -> CommandExecutionRead:
    """Resolve a command into a descriptor the client can act on."""
    execution = service.execute_command(command_id, payload.arguments)
    return CommandExecutionRead.model_validate(execution)


@router.get("/stats", response_model=SearchStatsRead)
def search_stats(service: SearchServiceDep) -> SearchStatsRead:
    """Return aggregate index and command statistics."""
    return SearchStatsRead.model_validate(service.stats())


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, service: SearchServiceDep) -> None:
    """Remove one document from the index."""
    service.delete_document(document_id)


@router.post("/commands/bootstrap", response_model=CommandListRead)
def bootstrap_commands(service: SearchServiceDep) -> CommandListRead:
    """Ensure the built-in command catalogue is present and return it."""
    service.ensure_default_commands()
    commands = service.list_commands()
    groups = sorted({command.group for command in commands})
    return CommandListRead(
        commands=[CommandRead.model_validate(command) for command in commands],
        groups=groups,
        total=len(commands),
    )
