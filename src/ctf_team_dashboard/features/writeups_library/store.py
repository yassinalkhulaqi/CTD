"""SQLite persistence for the writeups library."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from ctf_team_dashboard.domain.enums import ChallengeCategory, Difficulty
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.writeups_library.models import (
    PRIOR_MEAN,
    PRIOR_WEIGHT,
    ReviewVerdict,
    Writeup,
    WriteupBookmark,
    WriteupReview,
    WriteupStatus,
)
from ctf_team_dashboard.repositories.base import (
    BaseRepository,
    dump_tags,
    format_datetime,
    parse_datetime,
    parse_tags,
)

SORT_CLAUSES: dict[str, str] = {
    "date": "created_at DESC",
    "rating": "(rating_sum + ? * ?) / (rating_count + ?) DESC, created_at DESC",
    "views": "views DESC, created_at DESC",
    "title": "title COLLATE NOCASE ASC",
    "reading": "LENGTH(body) DESC, created_at DESC",
}


def _parse_ratings(raw: str | None) -> tuple[tuple[str, int], ...]:
    """Decode the member-to-score map stored on a writeup row."""
    if not raw:
        return ()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    if not isinstance(decoded, dict):
        return ()
    ratings: list[tuple[str, int]] = []
    for member_id, score in decoded.items():
        if isinstance(score, int):
            ratings.append((str(member_id), score))
    return tuple(ratings)


def _dump_ratings(ratings: Sequence[tuple[str, int]]) -> str:
    """Encode member ratings as a compact JSON object."""
    return json.dumps(dict(ratings), separators=(",", ":"))


class WriteupRepository(BaseRepository):
    """Repository for writeup rows."""

    table = "v3_writeups"

    def _to_entity(self, row: Any) -> Writeup:
        """Map a database row onto a domain writeup."""
        return Writeup(
            id=str(row["id"]),
            challenge_id=str(row["challenge_id"]),
            author_id=str(row["author_id"]),
            title=str(row["title"]),
            summary=str(row["summary"]),
            body=str(row["body"]),
            category=ChallengeCategory.parse(str(row["category"]), ChallengeCategory.MISC),
            difficulty=Difficulty.parse(str(row["difficulty"]), Difficulty.MEDIUM),
            tags=parse_tags(row["tags"]),
            status=WriteupStatus.parse(str(row["status"]), WriteupStatus.DRAFT),
            rating_sum=int(row["rating_sum"]),
            rating_count=int(row["rating_count"]),
            views=int(row["views"]),
            created_at=parse_datetime(row["created_at"]) or utcnow(),
            published_at=parse_datetime(row["published_at"]),
            ratings=_parse_ratings(row["ratings_json"]),
        )

    def create(self, writeup: Writeup) -> Writeup:
        """Insert a new writeup row."""
        self.execute(
            """
            INSERT INTO v3_writeups (
                id, challenge_id, author_id, title, summary, body, category,
                difficulty, tags, status, rating_sum, rating_count, ratings_json,
                views, created_at, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                writeup.id,
                writeup.challenge_id,
                writeup.author_id,
                writeup.title,
                writeup.summary,
                writeup.body,
                writeup.category.value,
                writeup.difficulty.value,
                dump_tags(writeup.tags),
                writeup.status.value,
                writeup.rating_sum,
                writeup.rating_count,
                _dump_ratings(writeup.ratings),
                writeup.views,
                format_datetime(writeup.created_at),
                format_datetime(writeup.published_at),
            ),
        )
        return writeup

    def update(self, writeup: Writeup) -> Writeup:
        """Replace the mutable columns of an existing writeup row."""
        self.execute(
            """
            UPDATE v3_writeups SET
                challenge_id = ?, title = ?, summary = ?, body = ?, category = ?,
                difficulty = ?, tags = ?, status = ?, rating_sum = ?,
                rating_count = ?, ratings_json = ?, views = ?, published_at = ?
            WHERE id = ?
            """,
            (
                writeup.challenge_id,
                writeup.title,
                writeup.summary,
                writeup.body,
                writeup.category.value,
                writeup.difficulty.value,
                dump_tags(writeup.tags),
                writeup.status.value,
                writeup.rating_sum,
                writeup.rating_count,
                _dump_ratings(writeup.ratings),
                writeup.views,
                format_datetime(writeup.published_at),
                writeup.id,
            ),
        )
        return writeup

    def get(self, writeup_id: str) -> Writeup | None:
        """Return one writeup by identifier, if it exists."""
        row = self.fetch_one("SELECT * FROM v3_writeups WHERE id = ?", (writeup_id,))
        return self._to_entity(row) if row is not None else None

    def delete(self, writeup_id: str) -> bool:
        """Delete a writeup and return whether a row was removed."""
        return self.execute("DELETE FROM v3_writeups WHERE id = ?", (writeup_id,)) > 0

    def exists_for_pair(self, author_id: str, challenge_id: str, *, exclude_id: str = "") -> bool:
        """Return whether the author already wrote up this challenge."""
        return self.exists(
            "author_id = ? AND challenge_id = ? AND id != ?",
            (author_id, challenge_id, exclude_id),
        )

    def all(self) -> list[Writeup]:
        """Return every writeup ordered by creation date."""
        rows = self.fetch_all("SELECT * FROM v3_writeups ORDER BY created_at DESC")
        return [self._to_entity(row) for row in rows]

    def _search_terms(self, query: str) -> tuple[str, list[Any]]:
        """Build a parameterised full-text-ish search clause."""
        terms = [term for term in query.strip().lower().split() if term]
        if not terms:
            return "", []
        clauses: list[str] = []
        params: list[Any] = []
        for term in terms:
            like = f"%{term}%"
            clauses.append(
                "(LOWER(title) LIKE ? OR LOWER(summary) LIKE ? "
                "OR LOWER(body) LIKE ? OR LOWER(tags) LIKE ?)"
            )
            params.extend([like, like, like, like])
        return f"({' AND '.join(clauses)})", params

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
        """Return writeups matching the requested filters and ordering."""
        conditions: list[str] = []
        params: list[Any] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status.value)
        elif published_only:
            conditions.append("status = ?")
            params.append(WriteupStatus.PUBLISHED.value)
        if category is not None:
            conditions.append("category = ?")
            params.append(category.value)
        if tag:
            conditions.append("LOWER(tags) LIKE ?")
            params.append(f"%{tag.strip().lower()}%")
        if author_id:
            conditions.append("author_id = ?")
            params.append(author_id)
        if challenge_id:
            conditions.append("challenge_id = ?")
            params.append(challenge_id)
        search_sql, search_params = self._search_terms(search)
        params.extend(search_params)

        parts = [*conditions, search_sql] if search_sql else conditions
        where = f" WHERE {' AND '.join(parts)}" if parts else ""
        order = SORT_CLAUSES.get(sort, SORT_CLAUSES["date"])
        sort_params: list[Any] = []
        if sort == "rating":
            sort_params = [PRIOR_MEAN, PRIOR_WEIGHT, PRIOR_WEIGHT]
        sql = f"SELECT * FROM v3_writeups{where} ORDER BY {order} LIMIT ? OFFSET ?"
        params.extend(sort_params)
        params.extend([max(1, min(limit, 500)), max(0, offset)])
        rows = self.fetch_all(sql, params)
        return [self._to_entity(row) for row in rows]

    def count_matching(
        self,
        *,
        status: WriteupStatus | None = None,
        category: ChallengeCategory | None = None,
        tag: str | None = None,
        author_id: str | None = None,
        search: str = "",
    ) -> int:
        """Count writeups matching the same filter family as ``list_writeups``."""
        conditions: list[str] = []
        params: list[Any] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status.value)
        if category is not None:
            conditions.append("category = ?")
            params.append(category.value)
        if tag:
            conditions.append("LOWER(tags) LIKE ?")
            params.append(f"%{tag.strip().lower()}%")
        if author_id:
            conditions.append("author_id = ?")
            params.append(author_id)
        search_sql, search_params = self._search_terms(search)
        params.extend(search_params)
        parts = [*conditions, search_sql] if search_sql else conditions
        where = f" WHERE {' AND '.join(parts)}" if parts else ""
        return int(self.fetch_value(f"SELECT COUNT(*) FROM v3_writeups{where}", params, 0) or 0)


class WriteupReviewRepository(BaseRepository):
    """Repository for peer review rows."""

    table = "v3_writeup_reviews"

    def _to_entity(self, row: Any) -> WriteupReview:
        """Map a database row onto a domain review."""
        return WriteupReview(
            id=str(row["id"]),
            writeup_id=str(row["writeup_id"]),
            reviewer_id=str(row["reviewer_id"]),
            verdict=ReviewVerdict.parse(str(row["verdict"]), ReviewVerdict.APPROVE),
            comment=str(row["comment"]),
            created_at=parse_datetime(row["created_at"]) or utcnow(),
        )

    def create(self, review: WriteupReview) -> WriteupReview:
        """Insert a new review row."""
        self.execute(
            """
            INSERT INTO v3_writeup_reviews (
                id, writeup_id, reviewer_id, verdict, comment, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                review.id,
                review.writeup_id,
                review.reviewer_id,
                review.verdict.value,
                review.comment,
                format_datetime(review.created_at),
            ),
        )
        return review

    def for_writeup(self, writeup_id: str) -> list[WriteupReview]:
        """Return all reviews of a writeup in chronological order."""
        rows = self.fetch_all(
            "SELECT * FROM v3_writeup_reviews WHERE writeup_id = ? ORDER BY created_at",
            (writeup_id,),
        )
        return [self._to_entity(row) for row in rows]

    def for_reviewer(self, reviewer_id: str) -> list[WriteupReview]:
        """Return all reviews authored by one member."""
        rows = self.fetch_all(
            "SELECT * FROM v3_writeup_reviews WHERE reviewer_id = ? ORDER BY created_at DESC",
            (reviewer_id,),
        )
        return [self._to_entity(row) for row in rows]

    def get_pair(self, writeup_id: str, reviewer_id: str) -> WriteupReview | None:
        """Return a member's review of a writeup, if present."""
        row = self.fetch_one(
            "SELECT * FROM v3_writeup_reviews WHERE writeup_id = ? AND reviewer_id = ?",
            (writeup_id, reviewer_id),
        )
        return self._to_entity(row) if row is not None else None

    def has_approval(self, writeup_id: str) -> bool:
        """Return whether at least one approving review exists."""
        return self.exists(
            "writeup_id = ? AND verdict = ?", (writeup_id, ReviewVerdict.APPROVE.value)
        )

    def delete_for_writeup(self, writeup_id: str) -> int:
        """Remove every review attached to a writeup."""
        return self.execute("DELETE FROM v3_writeup_reviews WHERE writeup_id = ?", (writeup_id,))

    def count_pending_reviews(self) -> int:
        """Return the number of writeups awaiting review."""
        value = self.fetch_value(
            "SELECT COUNT(DISTINCT writeup_id) FROM v3_writeup_reviews", default=0
        )
        return int(value or 0)


class WriteupBookmarkRepository(BaseRepository):
    """Repository for member bookmarks."""

    table = "v3_writeup_bookmarks"

    def _to_entity(self, row: Any) -> WriteupBookmark:
        """Map a database row onto a domain bookmark."""
        return WriteupBookmark(
            id=str(row["id"]),
            writeup_id=str(row["writeup_id"]),
            member_id=str(row["member_id"]),
            created_at=parse_datetime(row["created_at"]) or utcnow(),
        )

    def create(self, bookmark: WriteupBookmark) -> WriteupBookmark:
        """Insert a new bookmark row."""
        self.execute(
            """
            INSERT INTO v3_writeup_bookmarks (id, writeup_id, member_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                bookmark.id,
                bookmark.writeup_id,
                bookmark.member_id,
                format_datetime(bookmark.created_at),
            ),
        )
        return bookmark

    def remove(self, writeup_id: str, member_id: str) -> bool:
        """Delete a bookmark and return whether a row was removed."""
        return (
            self.execute(
                "DELETE FROM v3_writeup_bookmarks WHERE writeup_id = ? AND member_id = ?",
                (writeup_id, member_id),
            )
            > 0
        )

    def is_bookmarked(self, writeup_id: str, member_id: str) -> bool:
        """Return whether a member bookmarked a writeup."""
        return self.exists("writeup_id = ? AND member_id = ?", (writeup_id, member_id))

    def for_member(self, member_id: str) -> list[WriteupBookmark]:
        """Return all bookmarks of one member."""
        rows = self.fetch_all(
            "SELECT * FROM v3_writeup_bookmarks WHERE member_id = ? ORDER BY created_at DESC",
            (member_id,),
        )
        return [self._to_entity(row) for row in rows]

    def for_writeup(self, writeup_id: str) -> list[WriteupBookmark]:
        """Return all bookmarks pointing at one writeup."""
        rows = self.fetch_all(
            "SELECT * FROM v3_writeup_bookmarks WHERE writeup_id = ?",
            (writeup_id,),
        )
        return [self._to_entity(row) for row in rows]

    def delete_for_writeup(self, writeup_id: str) -> int:
        """Remove every bookmark attached to a writeup."""
        return self.execute("DELETE FROM v3_writeup_bookmarks WHERE writeup_id = ?", (writeup_id,))

    def count_all(self) -> int:
        """Return the total number of bookmarks in the library."""
        return int(self.fetch_value("SELECT COUNT(*) FROM v3_writeup_bookmarks", default=0) or 0)
