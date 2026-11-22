"""Typed Pydantic schemas for the writeups library API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ctf_team_dashboard.domain.enums import ChallengeCategory, Difficulty
from ctf_team_dashboard.features.writeups_library.models import ReviewVerdict, WriteupStatus


class WriteupCreate(BaseModel):
    """Payload for creating a draft writeup."""

    model_config = ConfigDict(extra="forbid")

    challenge_id: str = Field(min_length=1, max_length=120)
    author_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=3, max_length=160)
    summary: str = Field(min_length=10, max_length=400)
    body: str = Field(min_length=1)
    category: ChallengeCategory
    difficulty: Difficulty
    tags: list[str] = Field(default_factory=list, max_length=8)


class WriteupUpdate(BaseModel):
    """Partial payload for editing a writeup."""

    model_config = ConfigDict(extra="forbid")

    challenge_id: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=3, max_length=160)
    summary: str | None = Field(default=None, min_length=10, max_length=400)
    body: str | None = Field(default=None, min_length=1)
    category: ChallengeCategory | None = None
    difficulty: Difficulty | None = None
    tags: list[str] | None = Field(default=None, max_length=8)


class ReviewCreate(BaseModel):
    """Payload for recording a peer review."""

    model_config = ConfigDict(extra="forbid")

    reviewer_id: str = Field(min_length=1, max_length=120)
    verdict: ReviewVerdict
    comment: str = Field(default="", max_length=2000)


class RatingRequest(BaseModel):
    """Payload for a single member rating."""

    model_config = ConfigDict(extra="forbid")

    member_id: str = Field(min_length=1, max_length=120)
    score: int = Field(description="An integer score between 1 and 5")


class BookmarkRequest(BaseModel):
    """Payload identifying the member toggling a bookmark."""

    model_config = ConfigDict(extra="forbid")

    member_id: str = Field(min_length=1, max_length=120)


class TocEntryRead(BaseModel):
    """A heading entry in the reader's table of contents."""

    level: int
    title: str
    anchor: str


class SectionRead(BaseModel):
    """A markdown section rendered by the reader."""

    level: int
    title: str
    anchor: str
    content: str


class WriteupRead(BaseModel):
    """Full API representation of a writeup."""

    id: str
    challenge_id: str
    author_id: str
    title: str
    slug: str
    summary: str
    body: str
    category: ChallengeCategory
    difficulty: Difficulty
    tags: list[str]
    status: WriteupStatus
    excerpt: str
    word_count: int
    reading_minutes: int
    average_rating: float
    bayesian_score: float
    rating_sum: int
    rating_count: int
    views: int
    created_at: datetime
    published_at: datetime | None
    toc: list[TocEntryRead]


class WriteupReviewRead(BaseModel):
    """API representation of a peer review."""

    id: str
    writeup_id: str
    reviewer_id: str
    verdict: ReviewVerdict
    comment: str
    approved: bool
    created_at: datetime


class BookmarkResult(BaseModel):
    """Result of a bookmark toggle."""

    writeup_id: str
    member_id: str
    bookmarked: bool
    count: int


class WriteupListRead(BaseModel):
    """A paginated slice of the library."""

    items: list[WriteupRead]
    total: int
    offset: int
    limit: int


class CategoryStatRead(BaseModel):
    """Aggregate row for one category."""

    category: ChallengeCategory
    total: int
    published: int
    in_review: int
    publication_rate: float
    average_score: float


class StatusStatRead(BaseModel):
    """Aggregate row for one lifecycle status."""

    status: WriteupStatus
    count: int
    share: float


class WriteupStatsRead(BaseModel):
    """Library wide statistics payload."""

    total: int
    published: int
    drafts: int
    in_review: int
    total_views: int
    total_ratings: int
    bookmarks: int
    publication_rate: float
    average_views: float
    by_category: list[CategoryStatRead]
    by_status: list[StatusStatRead]
    top_rated: list[WriteupRead]


class MessageRead(BaseModel):
    """A simple acknowledgement payload."""

    message: str
