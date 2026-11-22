"""Domain entities and pure calculations for the notes workspace feature.

The module deliberately keeps all of the domain maths in small, side-effect
free functions and immutable entities. Persistence and orchestration live in
``store`` and ``service`` so the rules can be tested without a database.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher

from ctf_team_dashboard.domain.enums import StrEnum
from ctf_team_dashboard.domain.models import utcnow

MAX_TITLE_LENGTH = 200
MAX_BODY_LENGTH = 20_000
MAX_TAG_LENGTH = 32
MAX_TAGS = 12
WORDS_PER_MINUTE = 200
EXCERPT_LENGTH = 160
TEMPLATE_MAX_VARIABLES = 24

TEMPLATE_VARIABLE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_PATTERN = re.compile(r"^\s{0,3}(```|~~~)")
WORD_PATTERN = re.compile(r"[\w'-]+", re.UNICODE)
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


class NoteFormat(StrEnum):
    """The rendering mode of a note body."""

    MARKDOWN = "markdown"
    PLAIN = "plain"
    CODE = "code"

    @property
    def label(self) -> str:
        """Return a human readable label for the format."""
        return {
            NoteFormat.MARKDOWN: "Markdown",
            NoteFormat.PLAIN: "Plain text",
            NoteFormat.CODE: "Code",
        }[self]

    @property
    def is_markdown(self) -> bool:
        """Return whether the body should be parsed as Markdown."""
        return self is NoteFormat.MARKDOWN

    @property
    def monospace(self) -> bool:
        """Return whether the editor should use a monospace typeface."""
        return self in (NoteFormat.CODE,)


class TemplateCategory(StrEnum):
    """The catalogue grouping applied to a note template."""

    GENERAL = "general"
    CHECKLIST = "checklist"
    WEB = "web"
    CRYPTO = "crypto"
    PWN = "pwn"
    REVERSE = "reverse"
    FORENSICS = "forensics"
    OSINT = "osint"

    @property
    def label(self) -> str:
        """Return a human readable label for the category."""
        return self.value.replace("-", " ").title()


@dataclass(frozen=True, slots=True)
class Heading:
    """A Markdown ATX heading discovered in a note body."""

    level: int
    text: str
    line: int

    @property
    def anchor(self) -> str:
        """Return the slug used to link to this heading in a preview."""
        return slugify(self.text)

    @property
    def indent(self) -> int:
        """Return the zero based outline depth of the heading."""
        return max(0, self.level - 1)


@dataclass(frozen=True, slots=True)
class ChangeSummary:
    """A word level diff between two versions of a note body."""

    added: int = 0
    removed: int = 0

    @property
    def changed(self) -> bool:
        """Return whether the two versions differed at all."""
        return self.added > 0 or self.removed > 0

    @property
    def net(self) -> int:
        """Return the net change in word count."""
        return self.added - self.removed

    @property
    def magnitude(self) -> int:
        """Return the total number of changed words."""
        return self.added + self.removed

    def describe(self) -> str:
        """Return a compact, human readable description of the diff."""
        if not self.changed:
            return "No content change"
        parts: list[str] = []
        if self.added:
            parts.append(f"+{self.added}")
        if self.removed:
            parts.append(f"-{self.removed}")
        return " ".join(parts)


@dataclass(frozen=True, slots=True)
class NoteRevision:
    """An immutable snapshot of a note body at a given version."""

    id: str
    note_id: str
    version: int
    body: str
    author_id: str
    created_at: datetime = field(default_factory=utcnow)

    @property
    def word_count(self) -> int:
        """Return the number of words in this snapshot."""
        return count_words(self.body)

    def summary_against(self, previous: NoteRevision | None) -> ChangeSummary:
        """Summarise what changed relative to an earlier snapshot.

        Args:
            previous: The immediately preceding revision, or ``None`` for the
                first revision of a note.

        Returns:
            The word level change summary.
        """
        if previous is None:
            return ChangeSummary(added=self.word_count, removed=0)
        return summarise_change(previous.body, self.body)


@dataclass(frozen=True, slots=True)
class RevisionDescriptor:
    """A revision decorated with the diff that introduced it."""

    revision: NoteRevision
    summary: ChangeSummary
    is_latest: bool = False

    @property
    def version(self) -> int:
        """Return the revision version number."""
        return self.revision.version


@dataclass(frozen=True, slots=True)
class NoteEntry:
    """A versioned note attached to a challenge by a team member."""

    id: str
    challenge_id: str
    member_id: str
    title: str
    body: str
    format: NoteFormat = NoteFormat.MARKDOWN
    tags: tuple[str, ...] = ()
    pinned: bool = False
    version: int = 1
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def word_count(self) -> int:
        """Return the number of words in the note body."""
        return count_words(self.body)

    @property
    def reading_time_minutes(self) -> float:
        """Return the estimated reading time, rounded to one decimal."""
        return estimate_reading_time(self.body)

    @property
    def excerpt(self) -> str:
        """Return a compact, single line summary of the note."""
        return make_excerpt(self.body)

    @property
    def headings(self) -> tuple[Heading, ...]:
        """Return the Markdown outline of the note."""
        if not self.format.is_markdown:
            return ()
        return extract_headings(self.body)

    @property
    def tag_count(self) -> int:
        """Return the number of distinct tags on the note."""
        return len(self.tags)

    @property
    def is_pinned(self) -> bool:
        """Return whether the note is pinned to its challenge."""
        return self.pinned

    @property
    def age_days(self) -> int:
        """Return the whole days elapsed since the note was created."""
        return max(0, int((utcnow() - self.created_at).total_seconds() // 86_400))

    def matches(self, query: str) -> bool:
        """Return whether the note matches a case-insensitive text query.

        Args:
            query: The raw search text.

        Returns:
            ``True`` when the title, body or a tag contains the query.
        """
        needle = query.strip().lower()
        if not needle:
            return True
        haystacks = (self.title, self.body, *self.tags)
        return any(needle in value.lower() for value in haystacks)

    def has_tag(self, tag: str) -> bool:
        """Return whether the note carries the given normalised tag."""
        needle = normalise_tag(tag)
        return any(normalise_tag(existing) == needle for existing in self.tags)


@dataclass(frozen=True, slots=True)
class NoteTemplate:
    """A reusable note skeleton with ``{{variable}}`` placeholders."""

    id: str
    name: str
    category: TemplateCategory = TemplateCategory.GENERAL
    body: str = ""

    @property
    def variables(self) -> tuple[str, ...]:
        """Return the placeholder names declared by the template body."""
        return extract_variables(self.body)

    @property
    def variable_count(self) -> int:
        """Return the number of distinct placeholders."""
        return len(self.variables)

    @property
    def line_count(self) -> int:
        """Return the number of lines in the template body."""
        if not self.body:
            return 0
        return len(self.body.splitlines())


@dataclass(frozen=True, slots=True)
class RenderResult:
    """The outcome of rendering a template with a set of variables."""

    body: str
    used_variables: tuple[str, ...]
    unused_variables: tuple[str, ...]

    @property
    def variable_count(self) -> int:
        """Return the number of placeholders that were filled."""
        return len(self.used_variables)


@dataclass(frozen=True, slots=True)
class ChallengeNoteSummary:
    """Aggregated note statistics for a single challenge."""

    challenge_id: str
    note_count: int = 0
    pinned_count: int = 0
    revision_count: int = 0
    word_count: int = 0
    unique_authors: int = 0
    top_tags: tuple[str, ...] = ()

    @property
    def average_words(self) -> float:
        """Return the mean word count per note."""
        if self.note_count == 0:
            return 0.0
        return round(self.word_count / self.note_count, 1)

    @property
    def pinned_ratio(self) -> float:
        """Return the fraction of notes that are pinned."""
        if self.note_count == 0:
            return 0.0
        return round(self.pinned_count / self.note_count, 3)


@dataclass(frozen=True, slots=True)
class NotesWorkspaceSummary:
    """Workspace wide aggregation, including every challenge bucket."""

    challenges: tuple[ChallengeNoteSummary, ...] = ()
    total_notes: int = 0
    total_revisions: int = 0
    total_words: int = 0
    pinned_notes: int = 0
    unique_tags: tuple[str, ...] = ()
    generated_at: datetime = field(default_factory=utcnow)

    @property
    def challenge_count(self) -> int:
        """Return the number of challenges that have at least one note."""
        return len(self.challenges)

    @property
    def average_words(self) -> float:
        """Return the mean word count across all notes."""
        if self.total_notes == 0:
            return 0.0
        return round(self.total_words / self.total_notes, 1)

    def challenge(self, challenge_id: str) -> ChallengeNoteSummary | None:
        """Return the summary bucket for a challenge, when present."""
        for item in self.challenges:
            if item.challenge_id == challenge_id:
                return item
        return None


def count_words(text: str) -> int:
    """Count the words in a body of text.

    Args:
        text: The raw text.

    Returns:
        The number of alphanumeric word tokens.
    """
    return len(WORD_PATTERN.findall(text))


def estimate_reading_time(text: str, words_per_minute: int = WORDS_PER_MINUTE) -> float:
    """Estimate how long a note takes to read.

    Args:
        text: The raw text.
        words_per_minute: Reading speed used for the estimate.

    Returns:
        The duration in minutes, rounded to one decimal place.
    """
    if words_per_minute <= 0:
        return 0.0
    return round(count_words(text) / words_per_minute, 1)


def make_excerpt(text: str, limit: int = EXCERPT_LENGTH) -> str:
    """Build a single line excerpt from a Markdown body.

    Markdown markers and fenced code delimiters are stripped so the excerpt
    reads naturally in lists and tooltips.

    Args:
        text: The raw body.
        limit: Maximum number of characters in the excerpt.

    Returns:
        The excerpt, suffixed with an ellipsis when it was truncated.
    """
    collapsed = " ".join(text.split())
    cleaned = re.sub(r"[#*_`>\[\]]", "", collapsed)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    if limit <= 0:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1].rstrip()}…"


def normalise_tag(tag: str) -> str:
    """Normalise a single tag to its canonical form.

    Args:
        tag: The raw tag supplied by a user.

    Returns:
        A lower-case slug containing only letters, digits and hyphens.
    """
    lowered = tag.strip().lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9_-]+", "", lowered)
    return slug[:MAX_TAG_LENGTH].strip("-_")


def normalise_tags(tags: Iterable[str]) -> tuple[str, ...]:
    """Normalise, de-duplicate and bound a collection of tags.

    Args:
        tags: The raw tags supplied by a user.

    Returns:
        Up to ``MAX_TAGS`` canonical tags in their original order.
    """
    result: list[str] = []
    for tag in tags:
        cleaned = normalise_tag(tag)
        if cleaned and cleaned not in result:
            result.append(cleaned)
        if len(result) == MAX_TAGS:
            break
    return tuple(result)


def slugify(text: str) -> str:
    """Convert a heading into a URL friendly anchor slug.

    Args:
        text: The raw heading text.

    Returns:
        A lower-case slug, or ``section`` for an empty heading.
    """
    slug = SLUG_PATTERN.sub("-", text.strip().lower()).strip("-")
    return slug or "section"


def extract_headings(markdown: str) -> tuple[Heading, ...]:
    """Extract ATX headings from a Markdown body.

    Fenced code blocks are ignored so that ``#`` inside a snippet is not
    mistaken for a heading.

    Args:
        markdown: The Markdown source.

    Returns:
        The headings in document order.
    """
    headings: list[Heading] = []
    in_fence = False
    for number, line in enumerate(markdown.splitlines(), start=1):
        if FENCE_PATTERN.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_PATTERN.match(line)
        if match is None:
            continue
        headings.append(
            Heading(
                level=len(match.group(1)),
                text=match.group(2).strip(),
                line=number,
            )
        )
    return tuple(headings)


def extract_variables(body: str) -> tuple[str, ...]:
    """Return the distinct template variables used in a body.

    Args:
        body: The template source containing ``{{name}}`` placeholders.

    Returns:
        The placeholder names in first appearance order.
    """
    result: list[str] = []
    for match in TEMPLATE_VARIABLE_PATTERN.finditer(body):
        name = match.group(1)
        if name not in result:
            result.append(name)
    return tuple(result)


def render_variables(body: str, variables: Mapping[str, str]) -> str:
    """Substitute template variables with their supplied values.

    Unknown placeholders are left untouched so the caller can decide whether
    to fail or to show them to the user.

    Args:
        body: The template source.
        variables: Mapping of placeholder name to replacement value.

    Returns:
        The rendered body.
    """

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return variables.get(name, match.group(0))

    return TEMPLATE_VARIABLE_PATTERN.sub(replace, body)


def summarise_change(before: str, after: str) -> ChangeSummary:
    """Compute a word level diff between two bodies of text.

    Args:
        before: The earlier text.
        after: The later text.

    Returns:
        The number of inserted and deleted words.
    """
    before_tokens = WORD_PATTERN.findall(before)
    after_tokens = WORD_PATTERN.findall(after)
    matcher = SequenceMatcher(None, before_tokens, after_tokens, autojunk=False)
    added = 0
    removed = 0
    for tag, start_a, end_a, start_b, end_b in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in ("insert", "replace"):
            added += end_b - start_b
        if tag in ("delete", "replace"):
            removed += end_a - start_a
    return ChangeSummary(added=added, removed=removed)
