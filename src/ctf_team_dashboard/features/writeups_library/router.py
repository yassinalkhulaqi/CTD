"""HTTP API for the writeups library."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ctf_team_dashboard.domain.enums import ChallengeCategory
from ctf_team_dashboard.features.writeups_library.models import (
    Writeup,
    WriteupStats,
    WriteupStatus,
)
from ctf_team_dashboard.features.writeups_library.schemas import (
    BookmarkRequest,
    BookmarkResult,
    CategoryStatRead,
    MessageRead,
    RatingRequest,
    ReviewCreate,
    StatusStatRead,
    TocEntryRead,
    WriteupCreate,
    WriteupListRead,
    WriteupRead,
    WriteupReviewRead,
    WriteupStatsRead,
    WriteupUpdate,
)
from ctf_team_dashboard.features.writeups_library.service import WriteupService

router = APIRouter(prefix="/api/writeups", tags=["writeups"])


def get_writeup_service() -> WriteupService:
    """Dependency returning a configured writeup service."""
    return WriteupService()


WriteupServiceDep = Annotated[WriteupService, Depends(get_writeup_service)]


def _to_read(writeup: Writeup) -> WriteupRead:
    """Map a domain writeup onto its API representation."""
    return WriteupRead(
        id=writeup.id,
        challenge_id=writeup.challenge_id,
        author_id=writeup.author_id,
        title=writeup.title,
        slug=writeup.slug,
        summary=writeup.summary,
        body=writeup.body,
        category=writeup.category,
        difficulty=writeup.difficulty,
        tags=list(writeup.tags),
        status=writeup.status,
        excerpt=writeup.excerpt,
        word_count=writeup.word_count,
        reading_minutes=writeup.reading_minutes,
        average_rating=writeup.average_rating,
        bayesian_score=writeup.bayesian_score,
        rating_sum=writeup.rating_sum,
        rating_count=writeup.rating_count,
        views=writeup.views,
        created_at=writeup.created_at,
        published_at=writeup.published_at,
        toc=[
            TocEntryRead(level=entry.level, title=entry.title, anchor=entry.anchor)
            for entry in writeup.toc
        ],
    )


def _stats_to_read(stats: WriteupStats) -> WriteupStatsRead:
    """Map aggregate statistics onto their API representation."""
    return WriteupStatsRead(
        total=stats.total,
        published=stats.published,
        drafts=stats.drafts,
        in_review=stats.in_review,
        total_views=stats.total_views,
        total_ratings=stats.total_ratings,
        bookmarks=stats.bookmarks,
        publication_rate=stats.publication_rate,
        average_views=stats.average_views,
        by_category=[
            CategoryStatRead(
                category=entry.category,
                total=entry.total,
                published=entry.published,
                in_review=entry.in_review,
                publication_rate=entry.publication_rate,
                average_score=entry.average_score,
            )
            for entry in stats.by_category
        ],
        by_status=[
            StatusStatRead(
                status=entry.status,
                count=entry.count,
                share=entry.share(stats.total),
            )
            for entry in stats.by_status
        ],
        top_rated=[_to_read(item) for item in stats.top_rated],
    )


@router.get("", response_model=WriteupListRead)
def list_writeups(
    service: WriteupServiceDep,
    status_filter: Annotated[WriteupStatus | None, Query(alias="status")] = None,
    category: ChallengeCategory | None = None,
    tag: str | None = None,
    author_id: str | None = None,
    search: str = "",
    sort: str = "date",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=24, ge=1, le=100),
) -> WriteupListRead:
    """Return a filtered, paginated view of the library."""
    items = service.list_writeups(
        status=status_filter,
        category=category,
        tag=tag,
        author_id=author_id,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    total = service.writeups.count_matching(
        status=status_filter,
        category=category,
        tag=tag,
        author_id=author_id,
        search=search,
    )
    return WriteupListRead(
        items=[_to_read(item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", response_model=WriteupRead, status_code=status.HTTP_201_CREATED)
def create_writeup(payload: WriteupCreate, service: WriteupServiceDep) -> WriteupRead:
    """Create a draft writeup."""
    return _to_read(
        service.create(
            challenge_id=payload.challenge_id,
            author_id=payload.author_id,
            title=payload.title,
            summary=payload.summary,
            body=payload.body,
            category=payload.category,
            difficulty=payload.difficulty,
            tags=payload.tags,
        )
    )


@router.get("/stats", response_model=WriteupStatsRead)
def get_stats(service: WriteupServiceDep) -> WriteupStatsRead:
    """Return aggregate library statistics."""
    return _stats_to_read(service.stats())


@router.get("/mine", response_model=list[WriteupRead])
def get_mine(author_id: str, service: WriteupServiceDep) -> list[WriteupRead]:
    """Return every writeup authored by a member."""
    return [_to_read(item) for item in service.mine(author_id)]


@router.get("/top", response_model=list[WriteupRead])
def get_top(
    service: WriteupServiceDep, limit: int = Query(default=10, ge=1, le=50)
) -> list[WriteupRead]:
    """Return the highest rated published writeups."""
    return [_to_read(item) for item in service.top_rated(limit)]


@router.get("/bookmarks/{member_id}", response_model=list[WriteupRead])
def get_bookmarks(member_id: str, service: WriteupServiceDep) -> list[WriteupRead]:
    """Return all writeups bookmarked by a member."""
    found = [service.writeups.get(writeup_id) for writeup_id in service.bookmark_ids(member_id)]
    return [_to_read(item) for item in found if item is not None]


@router.get("/{writeup_id}", response_model=WriteupRead)
def get_writeup(
    writeup_id: str,
    service: WriteupServiceDep,
    track_view: bool = True,
) -> WriteupRead:
    """Return one writeup, optionally recording a view."""
    writeup = service.record_view(writeup_id) if track_view else service.get(writeup_id)
    return _to_read(writeup)


@router.get("/{writeup_id}/reviews", response_model=list[WriteupReviewRead])
def get_reviews(writeup_id: str, service: WriteupServiceDep) -> list[WriteupReviewRead]:
    """Return the review timeline of a writeup."""
    return [
        WriteupReviewRead(
            id=review.id,
            writeup_id=review.writeup_id,
            reviewer_id=review.reviewer_id,
            verdict=review.verdict,
            comment=review.comment,
            approved=review.approved,
            created_at=review.created_at,
        )
        for review in service.reviews_for(writeup_id)
    ]


@router.post(
    "/{writeup_id}/reviews",
    response_model=WriteupReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def add_review(
    writeup_id: str, payload: ReviewCreate, service: WriteupServiceDep
) -> WriteupReviewRead:
    """Record a peer review against a submitted writeup."""
    review = service.add_review(writeup_id, payload.reviewer_id, payload.verdict, payload.comment)
    return WriteupReviewRead(
        id=review.id,
        writeup_id=review.writeup_id,
        reviewer_id=review.reviewer_id,
        verdict=review.verdict,
        comment=review.comment,
        approved=review.approved,
        created_at=review.created_at,
    )


@router.patch("/{writeup_id}", response_model=WriteupRead)
def update_writeup(
    writeup_id: str, payload: WriteupUpdate, service: WriteupServiceDep
) -> WriteupRead:
    """Edit the mutable fields of a writeup."""
    return _to_read(
        service.update(
            writeup_id,
            challenge_id=payload.challenge_id,
            title=payload.title,
            summary=payload.summary,
            body=payload.body,
            category=payload.category,
            difficulty=payload.difficulty,
            tags=payload.tags,
        )
    )


@router.delete("/{writeup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_writeup(writeup_id: str, service: WriteupServiceDep) -> None:
    """Delete a writeup and its related records."""
    service.delete(writeup_id)


@router.post("/{writeup_id}/submit", response_model=WriteupRead)
def submit_writeup(writeup_id: str, service: WriteupServiceDep) -> WriteupRead:
    """Submit a draft for peer review."""
    return _to_read(service.submit(writeup_id))


@router.post("/{writeup_id}/publish", response_model=WriteupRead)
def publish_writeup(writeup_id: str, service: WriteupServiceDep) -> WriteupRead:
    """Publish an approved writeup."""
    return _to_read(service.publish(writeup_id))


@router.post("/{writeup_id}/withdraw", response_model=WriteupRead)
def withdraw_writeup(writeup_id: str, service: WriteupServiceDep) -> WriteupRead:
    """Withdraw a published writeup back to drafts."""
    return _to_read(service.withdraw(writeup_id))


@router.post("/{writeup_id}/rate", response_model=WriteupRead)
def rate_writeup(
    writeup_id: str, payload: RatingRequest, service: WriteupServiceDep
) -> WriteupRead:
    """Set a member's rating for a writeup."""
    return _to_read(service.rate(writeup_id, payload.member_id, payload.score))


@router.post("/{writeup_id}/bookmark", response_model=BookmarkResult)
def toggle_bookmark(
    writeup_id: str, payload: BookmarkRequest, service: WriteupServiceDep
) -> BookmarkResult:
    """Toggle a member's bookmark on a writeup."""
    bookmarked = service.toggle_bookmark(writeup_id, payload.member_id)
    return BookmarkResult(
        writeup_id=writeup_id,
        member_id=payload.member_id,
        bookmarked=bookmarked,
        count=service.bookmark_count(writeup_id),
    )


@router.get("/{writeup_id}/bookmark", response_model=MessageRead)
def bookmark_state(writeup_id: str, member_id: str, service: WriteupServiceDep) -> MessageRead:
    """Return the bookmark state of a member as a short message."""
    state = service.is_bookmarked(writeup_id, member_id)
    return MessageRead(message="bookmarked" if state else "not-bookmarked")
