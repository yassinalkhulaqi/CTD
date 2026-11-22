"""Feature-specific domain errors for the writeups library."""

from __future__ import annotations

from ctf_team_dashboard.errors import ConflictError, ValidationError
from ctf_team_dashboard.features.writeups_library.models import (
    MAX_RATING,
    MIN_RATING,
    WriteupStatus,
)


class InvalidTransitionError(ValidationError):
    """Raised when a writeup cannot move to the requested status."""

    code = "invalid_status_transition"

    def __init__(self, current: WriteupStatus, target: WriteupStatus) -> None:
        super().__init__(
            f"Cannot move a writeup from {current} to {target}",
            details={"current": current.value, "target": target.value},
        )
        self.current = current
        self.target = target


class DuplicateWriteupError(ConflictError):
    """Raised when an author already wrote up the same challenge."""

    code = "duplicate_writeup"

    def __init__(self, author_id: str, challenge_id: str) -> None:
        super().__init__(
            "A writeup for this challenge already exists",
            details={"author_id": author_id, "challenge_id": challenge_id},
        )
        self.author_id = author_id
        self.challenge_id = challenge_id


class RatingOutOfRangeError(ValidationError):
    """Raised when a rating does not lie between the allowed bounds."""

    code = "invalid_rating"

    def __init__(self, score: int) -> None:
        super().__init__(
            f"Rating must be between {MIN_RATING} and {MAX_RATING}",
            details={"score": score, "min": MIN_RATING, "max": MAX_RATING},
        )
        self.score = score


class ReviewNotAllowedError(ConflictError):
    """Raised when a review is recorded outside the review stage."""

    code = "review_not_allowed"

    def __init__(self, status: WriteupStatus) -> None:
        super().__init__(
            "Reviews can only be submitted while a writeup is in review",
            details={"status": status.value},
        )
        self.status = status


class DuplicateReviewError(ConflictError):
    """Raised when a reviewer tries to review the same writeup twice."""

    code = "duplicate_review"

    def __init__(self, writeup_id: str, reviewer_id: str) -> None:
        super().__init__(
            "This member has already reviewed the writeup",
            details={"writeup_id": writeup_id, "reviewer_id": reviewer_id},
        )


class NotSubmittableError(ValidationError):
    """Raised when an incomplete draft is submitted for review."""

    code = "writeup_incomplete"

    def __init__(self, writeup_id: str) -> None:
        super().__init__(
            "Add a title, summary and a longer body before submitting",
            details={"writeup_id": writeup_id},
        )


class ApprovalRequiredError(ValidationError):
    """Raised when an unreviewed writeup is published."""

    code = "approval_required"

    def __init__(self, writeup_id: str) -> None:
        super().__init__(
            "A writeup needs an approving review before publication",
            details={"writeup_id": writeup_id},
        )
