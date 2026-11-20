"""Domain model and pure ranking algorithms for the unified search index.

The module deliberately contains no persistence or HTTP concerns. Every scoring
function is deterministic so the same index and query always produce the same
ranking, which makes the behaviour straightforward to unit test.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ctf_team_dashboard.domain.models import utcnow

TITLE_WEIGHT = 5.0
TAG_WEIGHT = 3.0
BODY_WEIGHT = 1.0
PREFIX_BONUS = 0.5
COVERAGE_BONUS = 0.5
PHRASE_TITLE_BONUS = 4.0
PHRASE_BODY_BONUS = 1.5
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MAX_HITS_PER_FIELD = 3
SNIPPET_LENGTH = 180
SNIPPET_CONTEXT = 56

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)


class SearchKind(str, Enum):
    """Kinds of document that can live in the search index."""

    CHALLENGE = "challenge"
    TEAM = "team"
    MEMBER = "member"
    CUSTOM = "custom"

    @classmethod
    def parse(cls, value: str, default: SearchKind | None = None) -> SearchKind:
        """Parse a kind value, falling back to ``default`` when unknown."""
        fallback = default if default is not None else cls.CUSTOM
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            return fallback

    @property
    def label(self) -> str:
        """Return the human readable label used by the interface."""
        return {
            SearchKind.CHALLENGE: "Challenge",
            SearchKind.TEAM: "Team",
            SearchKind.MEMBER: "Member",
            SearchKind.CUSTOM: "Custom",
        }[self]

    @property
    def accent(self) -> str:
        """Return the semantic colour token associated with the kind."""
        return {
            SearchKind.CHALLENGE: "accent",
            SearchKind.TEAM: "info",
            SearchKind.MEMBER: "success",
            SearchKind.CUSTOM: "warning",
        }[self]


def fold_text(raw: str) -> str:
    """Normalise text for comparison: strip accents, case and punctuation."""
    decomposed = unicodedata.normalize("NFKD", raw or "")
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    folded = without_marks.casefold()
    replaced = "".join(char if char.isalnum() else " " for char in folded)
    return " ".join(replaced.split())


def tokenize(raw: str, *, drop_stopwords: bool = True) -> tuple[str, ...]:
    """Split text into normalised tokens, dropping common words by default."""
    words = fold_text(raw).split()
    if not drop_stopwords:
        return tuple(words)
    meaningful = tuple(word for word in words if word not in STOPWORDS)
    return meaningful if meaningful else tuple(words)


def parse_filters(raw: str) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Extract ``kind:`` and ``tag:`` filters from a raw query string."""
    text: list[str] = []
    kinds: list[str] = []
    tags: list[str] = []
    for word in raw.split():
        lowered = word.lower()
        if lowered.startswith("kind:"):
            value = fold_text(lowered[5:])
            if value and value not in kinds:
                kinds.append(value)
        elif lowered.startswith("tag:"):
            value = fold_text(lowered[4:])
            if value and value not in tags:
                tags.append(value)
        else:
            text.append(word)
    return " ".join(text), tuple(kinds), tuple(tags)


def initials_of(text: str) -> str:
    """Return up to four initials for an action name."""
    words = [word for word in fold_text(text).split() if word]
    return "".join(word[0] for word in words[:4])


@dataclass(frozen=True, slots=True)
class Highlight:
    """A highlighted span expressed as offsets into a snippet."""

    start: int
    end: int
    text: str
    field: str = "body"

    @property
    def length(self) -> int:
        """Return the number of highlighted characters."""
        return max(0, self.end - self.start)

    def overlaps(self, other: Highlight) -> bool:
        """Return whether two highlights share any character."""
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True, slots=True)
class Snippet:
    """A shortened body excerpt together with its highlight offsets."""

    text: str
    highlights: tuple[Highlight, ...] = ()

    @property
    def has_highlights(self) -> bool:
        """Return whether the excerpt contains at least one match."""
        return bool(self.highlights)

    @property
    def highlighted_characters(self) -> int:
        """Return the total number of highlighted characters."""
        return sum(item.length for item in self.highlights)


@dataclass(frozen=True, slots=True)
class SearchDocument:
    """An indexable document assembled from any dashboard entity."""

    id: str
    kind: SearchKind
    title: str
    body: str = ""
    tags: tuple[str, ...] = ()
    path: str = "/"
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def key(self) -> str:
        """Return the stable composite identity of the document."""
        return f"{self.kind.value}:{self.id}"

    @property
    def normalized_title(self) -> str:
        """Return the folded title used for scoring."""
        return fold_text(self.title)

    @property
    def normalized_body(self) -> str:
        """Return the folded body used for scoring."""
        return fold_text(self.body)

    @property
    def normalized_tags(self) -> tuple[str, ...]:
        """Return folded, deduplicated tags."""
        seen: set[str] = set()
        result: list[str] = []
        for tag in self.tags:
            value = fold_text(tag)
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return tuple(result)

    @property
    def searchable_text(self) -> str:
        """Return the complete folded text of the document."""
        return " ".join((self.normalized_title, *self.normalized_tags, self.normalized_body))

    def field_tokens(self) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        """Return title, tag and body token sequences for scoring."""
        return (
            tuple(self.normalized_title.split()),
            self.normalized_tags,
            tuple(self.normalized_body.split()),
        )

    def describe(self) -> str:
        """Return a compact one-line description for log free diagnostics."""
        return f"{self.kind.value}/{self.id}: {self.title}"


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A scored document ready to be rendered by the client."""

    document_id: str
    kind: SearchKind
    title: str
    snippet: str
    score: float
    highlights: tuple[Highlight, ...] = ()
    path: str = "/"

    @property
    def rounded_score(self) -> float:
        """Return the score rounded for display."""
        return round(self.score, 2)

    @property
    def relevance(self) -> str:
        """Return a coarse relevance label for the result badge."""
        if self.score >= 12:
            return "exact"
        if self.score >= 5:
            return "strong"
        if self.score > 0:
            return "related"
        return "weak"

    def rank_key(self) -> tuple[float, str]:
        """Return the deterministic ranking key used for sorting."""
        return (-round(self.score, 4), self.document_id)


@dataclass(frozen=True, slots=True)
class ParsedQuery:
    """A validated, normalised representation of a user query."""

    text: str
    kinds: tuple[SearchKind, ...] = ()
    tags: tuple[str, ...] = ()
    limit: int = DEFAULT_LIMIT

    @property
    def tokens(self) -> tuple[str, ...]:
        """Return the search tokens extracted from the query text."""
        return tokenize(self.text)

    @property
    def phrase(self) -> str:
        """Return the folded phrase used for phrase bonuses."""
        return fold_text(self.text)

    @property
    def has_filters(self) -> bool:
        """Return whether the query carries kind or tag restrictions."""
        return bool(self.kinds or self.tags)

    @property
    def summary(self) -> str:
        """Return a readable summary of the parsed query."""
        parts = [f'"{self.text}"'] if self.text else ["all documents"]
        if self.kinds:
            parts.append("kinds=" + ",".join(kind.value for kind in self.kinds))
        if self.tags:
            parts.append("tags=" + ",".join(self.tags))
        parts.append(f"limit={self.limit}")
        return " ".join(parts)

    def accepts(self, document: SearchDocument) -> bool:
        """Return whether a document satisfies the query filters."""
        if self.kinds and document.kind not in self.kinds:
            return False
        return not self.tags or set(self.tags).issubset(set(document.normalized_tags))


@dataclass(frozen=True, slots=True)
class Command:
    """An executable entry contributed by a feature or by the core."""

    id: str
    name: str
    description: str = ""
    group: str = "General"
    shortcut: str = ""
    keywords: tuple[str, ...] = ()

    @property
    def initials(self) -> str:
        """Return the initials used by acronym matching."""
        return initials_of(self.name)

    @property
    def search_text(self) -> str:
        """Return all searchable command text in folded form."""
        return fold_text(" ".join((self.name, self.description, *self.keywords)))

    @property
    def shortcut_label(self) -> str:
        """Return the shortcut in a display friendly form."""
        return self.shortcut.replace("Mod", "⌘/Ctrl").strip()

    def matches(self, query: str) -> bool:
        """Return whether the command fuzzy matches the query."""
        return command_match_score(self, query) > 0

    def target_for(self, arguments: str = "") -> str:
        """Build the navigation target from the route mentioned in the text."""
        target = self.description.strip()
        match = re.search(r"(/[\w/{}-]+)", target)
        if match:
            return match.group(0).replace("{args}", arguments)
        return target.replace("{args}", arguments)


@dataclass(frozen=True, slots=True)
class CommandMatch:
    """A command together with the score that produced its position."""

    command: Command
    score: float

    @property
    def level(self) -> str:
        """Return the qualitative strength of the match."""
        if self.score >= 8:
            return "exact"
        if self.score >= 4:
            return "partial"
        return "fuzzy"


@dataclass(frozen=True, slots=True)
class CommandExecution:
    """Descriptor returned when a command is executed."""

    command_id: str
    name: str
    action: str
    target: str
    message: str
    arguments: str = ""

    @property
    def is_navigation(self) -> bool:
        """Return whether execution should navigate to a route."""
        return self.action == "navigate"


@dataclass(frozen=True, slots=True)
class IndexReport:
    """Summary of an indexing run."""

    indexed: int
    by_kind: dict[str, int]
    skipped: int = 0

    @property
    def total(self) -> int:
        """Return the number of documents written."""
        return sum(self.by_kind.values())


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    """The parsed query together with its ranked results."""

    query: ParsedQuery
    results: tuple[SearchResult, ...]
    total_indexed: int

    @property
    def has_results(self) -> bool:
        """Return whether the query produced any result."""
        return bool(self.results)

    @property
    def returned(self) -> int:
        """Return the number of returned results."""
        return len(self.results)


@dataclass(frozen=True, slots=True)
class SearchStats:
    """Aggregate counters describing the current index."""

    document_count: int
    command_count: int
    documents_by_kind: dict[str, int]
    top_tags: tuple[tuple[str, int], ...]
    average_body_length: float = 0.0

    @property
    def has_documents(self) -> bool:
        """Return whether the index contains any document."""
        return self.document_count > 0

    @property
    def distinct_kinds(self) -> int:
        """Return the number of kinds present in the index."""
        return len(self.documents_by_kind)


def _field_score(tokens: Sequence[str], query: Sequence[str], weight: float) -> float:
    """Score one field against the query tokens, including prefix hits."""
    score = 0.0
    for term in query:
        hits = 0.0
        for token in tokens:
            if token == term:
                hits += 1
            elif token.startswith(term) and len(term) >= 2:
                hits += PREFIX_BONUS
        score += min(hits, MAX_HITS_PER_FIELD) * weight
    return score


def _phrase_bonus(tokens: Sequence[str], phrase_tokens: Sequence[str]) -> float:
    """Return a bonus when the query phrase occurs contiguously in a field."""
    if len(phrase_tokens) < 2 or len(phrase_tokens) > len(tokens):
        return 0.0
    size = len(phrase_tokens)
    for index in range(len(tokens) - size + 1):
        if tuple(tokens[index : index + size]) == tuple(phrase_tokens):
            return 1.0
    return 0.0


def score_document(
    document: SearchDocument,
    query_tokens: Sequence[str],
    phrase: str = "",
) -> float:
    """Compute the weighted relevance score of a document for a query."""
    if not query_tokens:
        return 0.0
    title, tags, body = document.field_tokens()
    phrase_tokens = tuple(tokenize(phrase))
    score = _field_score(title, query_tokens, TITLE_WEIGHT)
    score += _field_score(tags, query_tokens, TAG_WEIGHT)
    score += _field_score(body, query_tokens, BODY_WEIGHT)

    matched = 0
    searchable = (*title, *tags, *body)
    for term in query_tokens:
        if any(token == term or token.startswith(term) for token in searchable):
            matched += 1
    score += (matched / len(query_tokens)) * COVERAGE_BONUS

    if phrase_tokens:
        score += _phrase_bonus(title, phrase_tokens) * PHRASE_TITLE_BONUS
        score += _phrase_bonus(body, phrase_tokens) * PHRASE_BODY_BONUS
    return round(score, 3)


def find_token_spans(text: str, tokens: Sequence[str]) -> list[tuple[int, int]]:
    """Find and merge highlight spans for tokens inside ``text``."""
    spans: list[tuple[int, int]] = []
    for token in tokens:
        if not token:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(token)}", re.IGNORECASE)
        spans.extend((match.start(), match.end()) for match in pattern.finditer(text))
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))
    return merged


def build_snippet(
    text: str,
    tokens: Sequence[str],
    *,
    max_length: int = SNIPPET_LENGTH,
    context: int = SNIPPET_CONTEXT,
) -> Snippet:
    """Build a bounded excerpt with highlight offsets relative to the excerpt."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_length and not collapsed:
        return Snippet("")

    spans = find_token_spans(collapsed, tokens)
    if not spans:
        excerpt = collapsed[:max_length]
        suffix = "…" if len(collapsed) > max_length else ""
        return Snippet(excerpt + suffix)

    first_start = spans[0][0]
    start = max(0, first_start - context)
    if start > 0:
        boundary = collapsed.find(" ", start)
        start = boundary + 1 if 0 <= boundary < first_start else start
    end = min(len(collapsed), start + max_length)
    if end < len(collapsed):
        boundary = collapsed.rfind(" ", start, end)
        if boundary > first_start:
            end = boundary

    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(collapsed) else ""
    excerpt = prefix + collapsed[start:end] + suffix
    highlights = tuple(
        Highlight(
            span_start - start + len(prefix),
            span_end - start + len(prefix),
            collapsed[span_start:span_end],
        )
        for span_start, span_end in spans
        if span_start >= start and span_end <= end
    )
    return Snippet(excerpt, highlights)


def rank_results(
    results: Iterable[SearchResult], limit: int | None = None
) -> tuple[SearchResult, ...]:
    """Sort results by descending score with a stable identifier tie-break."""
    ordered = sorted(results, key=SearchResult.rank_key)
    if limit is not None:
        ordered = ordered[:limit]
    return tuple(ordered)


def command_match_score(command: Command, query: str) -> float:
    """Fuzzy match a command by substring, initials, keywords and description."""
    phrase = fold_text(query)
    if not phrase:
        return 0.0
    name = fold_text(command.name)
    initials = command.initials
    keywords = tuple(fold_text(word) for word in command.keywords)

    if name == phrase:
        return 12.0
    score = 0.0
    if phrase in name:
        score = 8.0 + (1.0 if name.startswith(phrase) else 0.0)
    if phrase in initials or initials.startswith(phrase):
        score = max(score, 6.0)
    for keyword in keywords:
        if keyword == phrase:
            score = max(score, 5.0)
        elif phrase in keyword:
            score = max(score, 3.0)
    if phrase in fold_text(command.description):
        score = max(score, 1.5)
    return round(score, 3)


def match_commands(
    commands: Iterable[Command], query: str, limit: int | None = None
) -> tuple[CommandMatch, ...]:
    """Return commands that fuzzy match a query in deterministic order."""
    matches = [
        CommandMatch(command, score)
        for command in commands
        if (score := command_match_score(command, query)) > 0
    ]
    matches.sort(key=lambda item: (-item.score, item.command.id))
    if limit is not None:
        matches = matches[:limit]
    return tuple(matches)
