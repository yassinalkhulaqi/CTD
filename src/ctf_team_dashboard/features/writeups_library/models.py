"""Domain entities and pure calculations for the writeups library."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime

from ctf_team_dashboard.domain.enums import ChallengeCategory, Difficulty, StrEnum
from ctf_team_dashboard.domain.models import utcnow

MAX_TAGS = 8
DEFAULT_WORDS_PER_MINUTE = 200
DEFAULT_EXCERPT_LENGTH = 160
PRIOR_MEAN = 3.5
PRIOR_WEIGHT = 4.0
MIN_RATING = 1
MAX_RATING = 5
MIN_BODY_WORDS = 40


class WriteupStatus(StrEnum):
    """Publication lifecycle of a writeup."""

    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"

    @property
    def is_public(self) -> bool:
        """Return whether the status makes a writeup visible in the library."""
        return self is WriteupStatus.PUBLISHED

    @property
    def next_options(self) -> tuple[WriteupStatus, ...]:
        """Return the statuses reachable from this one in one transition."""
        transitions: dict[WriteupStatus, tuple[WriteupStatus, ...]] = {
            WriteupStatus.DRAFT: (WriteupStatus.REVIEW,),
            WriteupStatus.REVIEW: (WriteupStatus.DRAFT, WriteupStatus.PUBLISHED),
            WriteupStatus.PUBLISHED: (WriteupStatus.DRAFT,),
        }
        return transitions[self]

    def allows(self, target: WriteupStatus) -> bool:
        """Return whether a transition to ``target`` is legal."""
        return target in self.next_options


class ReviewVerdict(StrEnum):
    """Outcome of a peer review."""

    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"

    @property
    def is_approval(self) -> bool:
        """Return whether the verdict grants publication permission."""
        return self is ReviewVerdict.APPROVE

    @property
    def label(self) -> str:
        """Return a human readable verdict label."""
        return "Approved" if self.is_approval else "Changes requested"


@dataclass(frozen=True, slots=True)
class TocEntry:
    """One heading in a generated table of contents."""

    level: int
    title: str
    anchor: str

    @property
    def indent(self) -> int:
        """Return the zero-based nesting depth of the heading."""
        return max(0, self.level - 2)

    @property
    def is_section(self) -> bool:
        """Return whether the heading is a top level section."""
        return self.level <= 2


@dataclass(frozen=True, slots=True)
class WriteupSection:
    """A slice of a writeup body delimited by markdown headings."""

    level: int
    title: str
    anchor: str
    content: str

    @property
    def word_count(self) -> int:
        """Return the number of words in this section."""
        return count_words(self.content)


@dataclass(frozen=True, slots=True)
class Writeup:
    """A long form solution authored for a solved challenge."""

    id: str
    challenge_id: str
    author_id: str
    title: str
    summary: str
    body: str
    category: ChallengeCategory
    difficulty: Difficulty
    tags: tuple[str, ...] = ()
    status: WriteupStatus = WriteupStatus.DRAFT
    rating_sum: int = 0
    rating_count: int = 0
    views: int = 0
    created_at: datetime = field(default_factory=utcnow)
    published_at: datetime | None = None
    ratings: tuple[tuple[str, int], ...] = ()

    @property
    def slug(self) -> str:
        """Return the URL friendly form of the title."""
        return slugify(self.title)

    @property
    def word_count(self) -> int:
        """Return the number of words in the body."""
        return count_words(self.body)

    @property
    def reading_minutes(self) -> int:
        """Return the estimated reading time in minutes."""
        return reading_time(self.body)

    @property
    def excerpt(self) -> str:
        """Return the concise plain text preview of the body."""
        return excerpt(self.body)

    @property
    def average_rating(self) -> float:
        """Return the arithmetic mean of submitted ratings."""
        if self.rating_count == 0:
            return 0.0
        return round(self.rating_sum / self.rating_count, 2)

    @property
    def bayesian_score(self) -> float:
        """Return the smoothed rating used for ranking."""
        return bayesian_score(self.rating_sum, self.rating_count)

    @property
    def is_published(self) -> bool:
        """Return whether the writeup is live in the library."""
        return self.status is WriteupStatus.PUBLISHED

    @property
    def is_reviewable(self) -> bool:
        """Return whether the writeup currently accepts peer reviews."""
        return self.status is WriteupStatus.REVIEW

    @property
    def has_ratings(self) -> bool:
        """Return whether at least one member rated the writeup."""
        return self.rating_count > 0

    @property
    def toc(self) -> tuple[TocEntry, ...]:
        """Return the table of contents derived from the markdown body."""
        return build_toc(self.body)

    @property
    def sections(self) -> tuple[WriteupSection, ...]:
        """Return the body split into heading delimited sections."""
        return split_sections(self.body)

    @property
    def star_distribution(self) -> tuple[int, ...]:
        """Return the count of ratings received for each star value."""
        distribution = [0] * MAX_RATING
        for _, score in self.ratings:
            if MIN_RATING <= score <= MAX_RATING:
                distribution[score - 1] += 1
        return tuple(distribution)

    def rating_by(self, member_id: str) -> int | None:
        """Return the score a member gave, if they rated the writeup."""
        for rater, score in self.ratings:
            if rater == member_id:
                return score
        return None

    def can_transition_to(self, target: WriteupStatus) -> bool:
        """Return whether the requested status transition is legal."""
        return self.status.allows(target)

    def with_status(self, target: WriteupStatus, *, at: datetime | None = None) -> Writeup:
        """Return a copy moved to ``target`` with publication time updated."""
        published_at = self.published_at
        if target is WriteupStatus.PUBLISHED:
            published_at = at or utcnow()
        elif target is WriteupStatus.DRAFT:
            published_at = None
        return replace(self, status=target, published_at=published_at)

    def with_ratings(self, ratings: Sequence[tuple[str, int]]) -> Writeup:
        """Return a copy with recalculated rating aggregates."""
        merged = dict(ratings)
        return replace(
            self,
            ratings=tuple(merged.items()),
            rating_sum=sum(merged.values()),
            rating_count=len(merged),
        )

    def with_view(self) -> Writeup:
        """Return a copy with the view counter incremented."""
        return replace(self, views=self.views + 1)


@dataclass(frozen=True, slots=True)
class WriteupReview:
    """A peer review recorded against a submitted writeup."""

    id: str
    writeup_id: str
    reviewer_id: str
    verdict: ReviewVerdict
    comment: str = ""
    created_at: datetime = field(default_factory=utcnow)

    @property
    def approved(self) -> bool:
        """Return whether the review approved publication."""
        return self.verdict.is_approval

    @property
    def requests_changes(self) -> bool:
        """Return whether the review asked for revisions."""
        return self.verdict is ReviewVerdict.REQUEST_CHANGES

    @property
    def is_substantive(self) -> bool:
        """Return whether the review includes written feedback."""
        return len(self.comment.strip()) >= 8


@dataclass(frozen=True, slots=True)
class WriteupBookmark:
    """A saved writeup shortcut belonging to a member."""

    id: str
    writeup_id: str
    member_id: str
    created_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True, slots=True)
class CategoryStat:
    """Aggregated writeup counts for a single category."""

    category: ChallengeCategory
    total: int = 0
    published: int = 0
    in_review: int = 0
    score_sum: float = 0.0
    score_count: int = 0

    @property
    def publication_rate(self) -> float:
        """Return the share of writeups that reached publication."""
        if self.total == 0:
            return 0.0
        return round(self.published / self.total, 3)

    @property
    def average_score(self) -> float:
        """Return the mean Bayesian score of rated writeups."""
        if self.score_count == 0:
            return 0.0
        return round(self.score_sum / self.score_count, 2)


@dataclass(frozen=True, slots=True)
class StatusStat:
    """Aggregated writeup counts for a single lifecycle status."""

    status: WriteupStatus
    count: int = 0

    def share(self, total: int) -> float:
        """Return this status's share of ``total`` writeups."""
        if total <= 0:
            return 0.0
        return round(self.count / total, 3)


@dataclass(frozen=True, slots=True)
class WriteupStats:
    """Library wide statistics used by the dashboard summary."""

    total: int = 0
    published: int = 0
    drafts: int = 0
    in_review: int = 0
    total_views: int = 0
    total_ratings: int = 0
    bookmarks: int = 0
    by_category: tuple[CategoryStat, ...] = ()
    by_status: tuple[StatusStat, ...] = ()
    top_rated: tuple[Writeup, ...] = ()

    @property
    def publication_rate(self) -> float:
        """Return the fraction of all writeups that are published."""
        if self.total == 0:
            return 0.0
        return round(self.published / self.total, 3)

    @property
    def average_views(self) -> float:
        """Return the mean view count across writeups."""
        if self.total == 0:
            return 0.0
        return round(self.total_views / self.total, 2)

    def status_count(self, status: WriteupStatus) -> int:
        """Return the count stored for one status."""
        for entry in self.by_status:
            if entry.status is status:
                return entry.count
        return 0


def slugify(value: str) -> str:
    """Convert a human title into a lowercase, hyphenated slug."""
    normalised = value.strip().lower().replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "-", normalised).strip("-")
    return slug or "writeup"


def normalise_tags(tags: Iterable[str]) -> tuple[str, ...]:
    """Clean, lowercase and de-duplicate a collection of tags."""
    result: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        candidate = raw.strip().lstrip("#").lower()
        candidate = re.sub(r"[^a-z0-9+.-]+", "-", candidate).strip("-")
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        result.append(candidate)
        if len(result) >= MAX_TAGS:
            break
    return tuple(result)


def count_words(body: str) -> int:
    """Count words in a markdown body, ignoring punctuation."""
    return len(re.findall(r"\b\w+(?:['’-]\w+)*\b", body))


def reading_time(body: str, words_per_minute: int = DEFAULT_WORDS_PER_MINUTE) -> int:
    """Estimate the reading time in minutes, with a one minute floor."""
    words = count_words(body)
    if words == 0:
        return 0
    if words_per_minute <= 0:
        words_per_minute = DEFAULT_WORDS_PER_MINUTE
    return max(1, math.ceil(words / words_per_minute))


def excerpt(body: str, limit: int = DEFAULT_EXCERPT_LENGTH) -> str:
    """Produce a plain text excerpt truncated on a word boundary."""
    plain = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", body)
    plain = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", plain)
    plain = re.sub(r"^\s{0,3}#{1,6}\s+", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"[*_>~-]+", " ", plain)
    collapsed = " ".join(plain.split())
    if limit <= 0 or len(collapsed) <= limit:
        return collapsed
    cut = collapsed[:limit].rsplit(" ", 1)[0]
    return f"{cut}…"


def bayesian_score(
    rating_sum: int,
    rating_count: int,
    prior_mean: float = PRIOR_MEAN,
    prior_weight: float = PRIOR_WEIGHT,
) -> float:
    """Blend observed ratings with a prior to avoid small-sample spikes."""
    if rating_count <= 0:
        return round(prior_mean, 2)
    total = rating_sum + prior_mean * prior_weight
    weight = rating_count + prior_weight
    return round(min(5.0, max(1.0, total / weight)), 2)


def clean_heading(raw: str) -> str:
    """Strip markdown emphasis and trailing hashes from a heading."""
    title = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", raw)
    title = re.sub(r"[*_`]+", "", title).strip()
    return re.sub(r"\s+#+\s*$", "", title).strip()


def build_toc(body: str, min_level: int = 2, max_level: int = 4) -> tuple[TocEntry, ...]:
    """Extract a table of contents from ATX markdown headings."""
    entries: list[TocEntry] = []
    used: dict[str, int] = {}
    for line in body.splitlines():
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", line)
        if match is None:
            continue
        level = len(match.group(1))
        if level < min_level or level > max_level:
            continue
        title = clean_heading(match.group(2))
        if not title:
            continue
        anchor = slugify(title)
        count = used.get(anchor, 0)
        used[anchor] = count + 1
        if count:
            anchor = f"{anchor}-{count}"
        entries.append(TocEntry(level=level, title=title, anchor=anchor))
    return tuple(entries)


def split_sections(body: str) -> tuple[WriteupSection, ...]:
    """Split a markdown body into sections keyed by their headings."""
    sections: list[WriteupSection] = []
    used: dict[str, int] = {}
    current_title = "Introduction"
    current_level = 2
    current_anchor = "introduction"
    lines: list[str] = []

    def flush() -> None:
        sections.append(
            WriteupSection(
                level=current_level,
                title=current_title,
                anchor=current_anchor,
                content="\n".join(lines).strip(),
            )
        )

    for line in body.splitlines():
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", line)
        if match is None:
            lines.append(line)
            continue
        if lines or sections:
            flush()
        level = len(match.group(1))
        current_title = clean_heading(match.group(2)) or "Untitled"
        current_level = level
        base = slugify(current_title)
        count = used.get(base, 0)
        used[base] = count + 1
        current_anchor = base if count == 0 else f"{base}-{count}"
        lines = []
    flush()
    return tuple(sections)


def is_valid_rating(score: int) -> bool:
    """Return whether a rating lies inside the allowed range."""
    return MIN_RATING <= score <= MAX_RATING


def is_submittable(writeup: Writeup) -> bool:
    """Return whether a draft has enough content to enter review."""
    return (
        bool(writeup.title.strip())
        and bool(writeup.summary.strip())
        and count_words(writeup.body) >= MIN_BODY_WORDS
    )
