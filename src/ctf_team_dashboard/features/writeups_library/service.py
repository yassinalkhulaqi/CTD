"""Business rules and orchestration for the writeups library."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from ctf_team_dashboard.domain.enums import ChallengeCategory, Difficulty
from ctf_team_dashboard.errors import NotFoundError, ValidationError
from ctf_team_dashboard.features.writeups_library.errors import (
    ApprovalRequiredError,
    DuplicateReviewError,
    DuplicateWriteupError,
    InvalidTransitionError,
    NotSubmittableError,
    RatingOutOfRangeError,
    ReviewNotAllowedError,
)
from ctf_team_dashboard.features.writeups_library.models import (
    CategoryStat,
    ReviewVerdict,
    StatusStat,
    Writeup,
    WriteupBookmark,
    WriteupReview,
    WriteupStats,
    WriteupStatus,
    bayesian_score,
    is_submittable,
    is_valid_rating,
    normalise_tags,
)
from ctf_team_dashboard.features.writeups_library.store import (
    WriteupBookmarkRepository,
    WriteupRepository,
    WriteupReviewRepository,
)


class WriteupService:
    """Apply writeup domain rules on top of the persistence layer."""

    def __init__(
        self,
        writeups: WriteupRepository | None = None,
        reviews: WriteupReviewRepository | None = None,
        bookmarks: WriteupBookmarkRepository | None = None,
    ) -> None:
        self.writeups = writeups or WriteupRepository()
        self.reviews = reviews or WriteupReviewRepository()
        self.bookmarks = bookmarks or WriteupBookmarkRepository()

    def _require(self, writeup_id: str) -> Writeup:
        """Return a writeup or raise a typed not-found error."""
        writeup = self.writeups.get(writeup_id)
        if writeup is None:
            raise NotFoundError(
                f"Writeup {writeup_id} does not exist", details={"writeup_id": writeup_id}
            )
        return writeup

    def create(
        self,
        *,
        challenge_id: str,
        author_id: str,
        title: str,
        summary: str,
        body: str,
        category: ChallengeCategory,
        difficulty: Difficulty,
        tags: Sequence[str] = (),
    ) -> Writeup:
        """Create a draft writeup, enforcing one writeup per author and challenge."""
        if not title.strip():
            raise ValidationError("A writeup title is required")
        if not summary.strip():
            raise ValidationError("A writeup summary is required")
        if not body.strip():
            raise ValidationError("A writeup body is required")
        if self.writeups.exists_for_pair(author_id, challenge_id):
            raise DuplicateWriteupError(author_id, challenge_id)
        writeup = Writeup(
            id=f"wu_{uuid4().hex[:16]}",
            challenge_id=challenge_id,
            author_id=author_id,
            title=title.strip(),
            summary=summary.strip(),
            body=body.strip(),
            category=category,
            difficulty=difficulty,
            tags=normalise_tags(tags),
        )
        return self.writeups.create(writeup)

    def get(self, writeup_id: str) -> Writeup:
        """Return a writeup by identifier."""
        return self._require(writeup_id)

    def record_view(self, writeup_id: str) -> Writeup:
        """Increment the view counter of a writeup."""
        writeup = self._require(writeup_id)
        viewed = writeup.with_view()
        return self.writeups.update(viewed)

    def list_writeups(
        self,
        *,
        status: WriteupStatus | None = None,
        category: ChallengeCategory | None = None,
        tag: str | None = None,
        author_id: str | None = None,
        challenge_id: str | None = None,
        search: str = "",
        sort: str = "date",
        limit: int = 100,
        offset: int = 0,
        published_only: bool = False,
    ) -> list[Writeup]:
        """Return filtered writeups using the repository query builder."""
        return self.writeups.list_writeups(
            status=status,
            category=category,
            tag=tag,
            author_id=author_id,
            challenge_id=challenge_id,
            search=search,
            sort=sort,
            limit=limit,
            offset=offset,
            published_only=published_only,
        )

    def search(self, query: str, *, limit: int = 50) -> list[Writeup]:
        """Search published writeups by title, summary, body and tags."""
        return self.list_writeups(search=query, published_only=True, sort="rating", limit=limit)

    def mine(self, author_id: str) -> list[Writeup]:
        """Return every writeup authored by one member."""
        return self.list_writeups(author_id=author_id)

    def top_rated(self, limit: int = 10) -> list[Writeup]:
        """Return the highest scoring published writeups."""
        found = self.list_writeups(
            status=WriteupStatus.PUBLISHED, sort="rating", limit=max(1, min(limit, 100))
        )
        return [item for item in found if item.rating_count > 0]

    def update(
        self,
        writeup_id: str,
        *,
        title: str | None = None,
        summary: str | None = None,
        body: str | None = None,
        category: ChallengeCategory | None = None,
        difficulty: Difficulty | None = None,
        tags: Sequence[str] | None = None,
        challenge_id: str | None = None,
    ) -> Writeup:
        """Apply explicit field updates to a writeup."""
        current = self._require(writeup_id)
        changed = False
        final_title = current.title
        final_summary = current.summary
        final_body = current.body
        final_category = current.category
        final_difficulty = current.difficulty
        final_tags = current.tags
        final_challenge = current.challenge_id
        if title is not None:
            if not title.strip():
                raise ValidationError("A writeup title is required")
            final_title = title.strip()
            changed = True
        if summary is not None:
            if not summary.strip():
                raise ValidationError("A writeup summary is required")
            final_summary = summary.strip()
            changed = True
        if body is not None:
            if not body.strip():
                raise ValidationError("A writeup body is required")
            final_body = body.strip()
            changed = True
        if category is not None:
            final_category = category
            changed = True
        if difficulty is not None:
            final_difficulty = difficulty
            changed = True
        if tags is not None:
            final_tags = normalise_tags(tags)
            changed = True
        if challenge_id is not None and challenge_id != current.challenge_id:
            if self.writeups.exists_for_pair(
                current.author_id, challenge_id, exclude_id=current.id
            ):
                raise DuplicateWriteupError(current.author_id, challenge_id)
            final_challenge = challenge_id
            changed = True
        if not changed:
            return current
        updated = Writeup(
            id=current.id,
            challenge_id=final_challenge,
            author_id=current.author_id,
            title=final_title,
            summary=final_summary,
            body=final_body,
            category=final_category,
            difficulty=final_difficulty,
            tags=final_tags,
            status=current.status,
            rating_sum=current.rating_sum,
            rating_count=current.rating_count,
            views=current.views,
            created_at=current.created_at,
            published_at=current.published_at,
            ratings=current.ratings,
        )
        return self.writeups.update(updated)

    def delete(self, writeup_id: str) -> None:
        """Delete a writeup together with its reviews and bookmarks."""
        self._require(writeup_id)
        self.reviews.delete_for_writeup(writeup_id)
        self.bookmarks.delete_for_writeup(writeup_id)
        self.writeups.delete(writeup_id)

    def _transition(self, writeup: Writeup, target: WriteupStatus) -> Writeup:
        """Validate and persist a status transition."""
        if not writeup.can_transition_to(target):
            raise InvalidTransitionError(writeup.status, target)
        return self.writeups.update(writeup.with_status(target))

    def submit(self, writeup_id: str) -> Writeup:
        """Move a complete draft into the review queue."""
        writeup = self._require(writeup_id)
        if writeup.status is not WriteupStatus.DRAFT:
            raise InvalidTransitionError(writeup.status, WriteupStatus.REVIEW)
        if not is_submittable(writeup):
            raise NotSubmittableError(writeup_id)
        return self._transition(writeup, WriteupStatus.REVIEW)

    def publish(self, writeup_id: str) -> Writeup:
        """Publish a reviewed writeup, requiring an approving review."""
        writeup = self._require(writeup_id)
        if writeup.status is not WriteupStatus.REVIEW:
            raise InvalidTransitionError(writeup.status, WriteupStatus.PUBLISHED)
        if not self.reviews.has_approval(writeup_id):
            raise ApprovalRequiredError(writeup_id)
        return self._transition(writeup, WriteupStatus.PUBLISHED)

    def withdraw(self, writeup_id: str) -> Writeup:
        """Return a published writeup to the draft stage."""
        writeup = self._require(writeup_id)
        return self._transition(writeup, WriteupStatus.DRAFT)

    def add_review(
        self,
        writeup_id: str,
        reviewer_id: str,
        verdict: ReviewVerdict,
        comment: str = "",
    ) -> WriteupReview:
        """Record a peer review and apply its workflow side effects."""
        writeup = self._require(writeup_id)
        if writeup.author_id == reviewer_id:
            raise ValidationError("Authors cannot review their own writeups")
        if writeup.status is not WriteupStatus.REVIEW:
            raise ReviewNotAllowedError(writeup.status)
        if self.reviews.get_pair(writeup_id, reviewer_id) is not None:
            raise DuplicateReviewError(writeup_id, reviewer_id)
        review = WriteupReview(
            id=f"rv_{uuid4().hex[:16]}",
            writeup_id=writeup_id,
            reviewer_id=reviewer_id,
            verdict=verdict,
            comment=comment.strip(),
        )
        created = self.reviews.create(review)
        if verdict is ReviewVerdict.REQUEST_CHANGES:
            self.writeups.update(writeup.with_status(WriteupStatus.DRAFT))
        return created

    def reviews_for(self, writeup_id: str) -> list[WriteupReview]:
        """Return the review timeline of a writeup."""
        self._require(writeup_id)
        return self.reviews.for_writeup(writeup_id)

    def rate(self, writeup_id: str, member_id: str, score: int) -> Writeup:
        """Set one member's rating and recompute aggregate scores."""
        writeup = self._require(writeup_id)
        if not is_valid_rating(score):
            raise RatingOutOfRangeError(score)
        ratings = [(member, value) for member, value in writeup.ratings if member != member_id]
        ratings.append((member_id, score))
        return self.writeups.update(writeup.with_ratings(ratings))

    def toggle_bookmark(self, writeup_id: str, member_id: str) -> bool:
        """Toggle a member's bookmark and return the resulting state."""
        self._require(writeup_id)
        if self.bookmarks.is_bookmarked(writeup_id, member_id):
            self.bookmarks.remove(writeup_id, member_id)
            return False
        self.bookmarks.create(
            WriteupBookmark(
                id=f"bm_{uuid4().hex[:16]}",
                writeup_id=writeup_id,
                member_id=member_id,
            )
        )
        return True

    def bookmark_ids(self, member_id: str) -> list[str]:
        """Return the identifiers of writeups bookmarked by a member."""
        return [item.writeup_id for item in self.bookmarks.for_member(member_id)]

    def bookmark_count(self, writeup_id: str) -> int:
        """Return the number of bookmarks pointing at a writeup."""
        return len(self.bookmarks.for_writeup(writeup_id))

    def is_bookmarked(self, writeup_id: str, member_id: str) -> bool:
        """Return whether a member already bookmarked a writeup."""
        return self.bookmarks.is_bookmarked(writeup_id, member_id)

    def stats(self) -> WriteupStats:
        """Aggregate library wide counters and leaderboards."""
        writeups = self.writeups.all()
        total = len(writeups)
        published = [item for item in writeups if item.status is WriteupStatus.PUBLISHED]
        drafts = [item for item in writeups if item.status is WriteupStatus.DRAFT]
        in_review = [item for item in writeups if item.status is WriteupStatus.REVIEW]

        category_stats: list[CategoryStat] = []
        for category in ChallengeCategory:
            matching = [item for item in writeups if item.category is category]
            scores = [item.bayesian_score for item in matching if item.has_ratings]
            category_stats.append(
                CategoryStat(
                    category=category,
                    total=len(matching),
                    published=sum(1 for item in matching if item.is_published),
                    in_review=sum(1 for item in matching if item.status is WriteupStatus.REVIEW),
                    score_sum=round(sum(scores), 2),
                    score_count=len(scores),
                )
            )

        status_stats = tuple(
            StatusStat(
                status=status,
                count=sum(1 for item in writeups if item.status is status),
            )
            for status in WriteupStatus
        )
        top = sorted(
            (item for item in published if item.has_ratings),
            key=lambda item: (item.bayesian_score, item.rating_count, item.views),
            reverse=True,
        )[:10]
        return WriteupStats(
            total=total,
            published=len(published),
            drafts=len(drafts),
            in_review=len(in_review),
            total_views=sum(item.views for item in writeups),
            total_ratings=sum(item.rating_count for item in writeups),
            bookmarks=self.bookmarks.count_all(),
            by_category=tuple(category_stats),
            by_status=status_stats,
            top_rated=tuple(top),
        )

    def score_of(self, writeup: Writeup) -> float:
        """Return the ranking score used by the top-rated board."""
        return bayesian_score(writeup.rating_sum, writeup.rating_count)

    def created_between(
        self, start: datetime, end: datetime, *, status: WriteupStatus | None = None
    ) -> list[Writeup]:
        """Return writeups created inside a closed time window."""
        return [
            item
            for item in self.writeups.all()
            if start <= item.created_at <= end and (status is None or item.status is status)
        ]
