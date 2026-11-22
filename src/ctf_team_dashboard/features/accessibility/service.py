"""Business rules and orchestration for the accessibility toolkit."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.accessibility.models import (
    A11yIssue,
    AccessibilityStats,
    ContrastAudit,
    ContrastPair,
    FocusDirection,
    FocusOrderEntry,
    FocusTrap,
    KeyboardShortcut,
    Severity,
    ShortcutConflict,
    canonical_shortcut,
    find_shortcut_conflicts,
    normalise_color,
    sort_focus_entries,
    sort_issues,
    suggest_aria_label,
    validate_focus_entries,
)
from ctf_team_dashboard.features.accessibility.store import (
    FocusOrderRepository,
    IssueRepository,
    ShortcutRepository,
)


class AccessibilityService:
    """Coordinate accessibility records, audits and focus helpers."""

    def __init__(
        self,
        issues: IssueRepository | None = None,
        shortcuts: ShortcutRepository | None = None,
        focus: FocusOrderRepository | None = None,
    ) -> None:
        self._issues = issues or IssueRepository()
        self._shortcuts = shortcuts or ShortcutRepository()
        self._focus = focus or FocusOrderRepository()

    @staticmethod
    def _text(value: str, field: str, *, max_length: int) -> str:
        """Validate and trim a required text field."""
        cleaned = value.strip()
        if not cleaned:
            raise ValidationError(f"{field} must not be empty", details={"field": field})
        if len(cleaned) > max_length:
            raise ValidationError(
                f"{field} must be at most {max_length} characters",
                details={"field": field, "max_length": max_length},
            )
        return cleaned

    @staticmethod
    def _severity(value: Severity | str) -> Severity:
        """Normalise a severity value into a domain enum."""
        if isinstance(value, Severity):
            return value
        try:
            return Severity.parse(value)
        except ValueError as exc:
            raise ValidationError(
                f"unknown severity {value!r}", details={"field": "severity"}
            ) from exc

    def record_issue(
        self,
        *,
        path: str,
        rule_id: str,
        severity: Severity | str,
        description: str,
        suggestion: str = "",
        issue_id: str | None = None,
        detected_at: datetime | None = None,
    ) -> A11yIssue:
        """Record a new accessibility issue."""
        clean_path = self._text(path, "path", max_length=240)
        clean_rule = self._text(rule_id, "rule_id", max_length=80)
        clean_description = self._text(description, "description", max_length=2_000)
        hint = suggestion.strip() or suggest_aria_label(clean_description, context=clean_path)
        issue = A11yIssue(
            id=issue_id or f"a11y-{uuid.uuid4().hex[:12]}",
            path=clean_path,
            rule_id=clean_rule,
            severity=self._severity(severity),
            description=clean_description,
            suggestion=hint[:500],
            detected_at=utcnow() if detected_at is None else detected_at,
        )
        return self._issues.create(issue)

    def list_issues(
        self,
        *,
        path: str | None = None,
        severity: Severity | None = None,
        resolved: bool | None = None,
        limit: int = 200,
    ) -> list[A11yIssue]:
        """Return issues ordered by severity and recency."""
        if limit < 1 or limit > 1_000:
            raise ValidationError("limit must be between 1 and 1000", details={"field": "limit"})
        return sort_issues(
            self._issues.list_all(path=path, severity=severity, resolved=resolved, limit=limit)
        )

    def get_issue(self, issue_id: str) -> A11yIssue:
        """Return one issue or raise a not-found error."""
        issue = self._issues.get(issue_id)
        if issue is None:
            raise NotFoundError(f"accessibility issue {issue_id!r} was not found")
        return issue

    def resolve_issue(self, issue_id: str, *, when: datetime | None = None) -> A11yIssue:
        """Resolve an open issue and return its updated state."""
        issue = self.get_issue(issue_id)
        if issue.resolved_at is not None:
            raise ConflictError(
                f"accessibility issue {issue_id!r} is already resolved",
                details={"id": issue_id},
            )
        resolved_at = when if when is not None else utcnow()
        if not self._issues.set_resolved(issue_id, resolved_at):
            raise ConflictError(
                f"accessibility issue {issue_id!r} could not be resolved",
                details={"id": issue_id},
            )
        return issue.resolve(when=resolved_at)

    def audit_contrast_pairs(
        self, pairs: Sequence[ContrastPair], *, record_issues: bool = False
    ) -> ContrastAudit:
        """Audit colour pairs against WCAG AA and optionally record failures."""
        validated: list[ContrastPair] = []
        for pair in pairs:
            try:
                validated.append(
                    ContrastPair(
                        foreground=normalise_color(pair.foreground),
                        background=normalise_color(pair.background),
                        path=pair.path,
                        label=pair.label,
                        large_text=pair.large_text,
                    )
                )
            except ValueError as exc:
                raise ValidationError(
                    "a contrast pair contains an invalid colour",
                    details={"message": str(exc)},
                ) from exc

        issues: list[A11yIssue] = []
        for pair in validated:
            if pair.passes_aa or not record_issues:
                continue
            severity = Severity.CRITICAL if pair.ratio < 3.0 else Severity.WARNING
            issues.append(
                self.record_issue(
                    path=pair.path or "/accessibility",
                    rule_id="wcag-contrast-aa",
                    severity=severity,
                    description=(
                        f"{pair.display_label} has a contrast ratio of {pair.ratio:.2f}:1"
                    ),
                    suggestion=pair.suggestion,
                )
            )
        return ContrastAudit(tuple(validated), tuple(issues))

    def audit_color_pair(
        self,
        *,
        foreground: str,
        background: str,
        path: str = "",
        label: str = "",
        large_text: bool = False,
        record_issue: bool = False,
    ) -> ContrastAudit:
        """Audit a single colour pair supplied as raw strings."""
        return self.audit_contrast_pairs(
            [
                ContrastPair(
                    foreground=foreground,
                    background=background,
                    path=path,
                    label=label,
                    large_text=large_text,
                )
            ],
            record_issues=record_issue,
        )

    def register_shortcut(
        self,
        *,
        keys: str,
        action: str,
        scope: str = "global",
        shortcut_id: str | None = None,
    ) -> KeyboardShortcut:
        """Register a shortcut after checking for scope-aware conflicts."""
        try:
            canonical = canonical_shortcut(keys)
        except ValueError as exc:
            raise ValidationError(
                "shortcut keys are malformed", details={"message": str(exc)}
            ) from exc
        clean_action = self._text(action, "action", max_length=120)
        clean_scope = self._text(scope, "scope", max_length=60).lower()
        candidate = KeyboardShortcut(
            id=shortcut_id or f"shortcut-{uuid.uuid4().hex[:12]}",
            keys=canonical,
            action=clean_action,
            scope=clean_scope,
        )
        for existing in self._shortcuts.find_matching(canonical, scope=clean_scope):
            if not candidate.conflicts_with(existing):
                continue
            raise ConflictError(
                f"shortcut {candidate.display_keys} is already bound",
                details={
                    "keys": canonical,
                    "scope": existing.scope,
                    "action": existing.action,
                    "existing_id": existing.id,
                },
            )
        return self._shortcuts.create(candidate)

    def list_shortcuts(self, *, scope: str | None = None) -> list[KeyboardShortcut]:
        """Return registered shortcuts, optionally scoped to a screen."""
        return self._shortcuts.list_all(scope=scope)

    def get_shortcut(self, shortcut_id: str) -> KeyboardShortcut:
        """Return one shortcut or raise a not-found error."""
        shortcut = self._shortcuts.get(shortcut_id)
        if shortcut is None:
            raise NotFoundError(f"keyboard shortcut {shortcut_id!r} was not found")
        return shortcut

    def delete_shortcut(self, shortcut_id: str) -> None:
        """Remove a registered shortcut."""
        self.get_shortcut(shortcut_id)
        self._shortcuts.delete(shortcut_id)

    def shortcut_conflicts(self) -> list[ShortcutConflict]:
        """Return every conflict among the registered shortcuts."""
        return find_shortcut_conflicts(self._shortcuts.list_all())

    def list_focus_entries(self) -> list[FocusOrderEntry]:
        """Return the configured tab order."""
        return self._focus.list_all()

    def record_focus_entry(
        self,
        label: str,
        *,
        order: int | None = None,
        entry_id: str | None = None,
    ) -> FocusOrderEntry:
        """Add a focus stop, inserting it at the requested position."""
        clean_label = self._text(label, "label", max_length=120)
        existing = self._focus.list_all()
        identifier = entry_id or f"focus-{uuid.uuid4().hex[:10]}"
        if any(entry.id == identifier for entry in existing):
            raise ConflictError(
                f"focus entry {identifier!r} already exists",
                details={"id": identifier},
            )
        requested = order if order is not None else len(existing) + 1
        if requested < 1:
            raise ValidationError("order must be positive", details={"field": "order"})
        candidate = FocusOrderEntry(id=identifier, label=clean_label, order=requested)
        ordered_existing = sort_focus_entries(existing)
        insert_at = min(max(requested - 1, 0), len(ordered_existing))
        inserted = [
            *ordered_existing[:insert_at],
            candidate,
            *ordered_existing[insert_at:],
        ]
        renumbered = [entry.with_order(index + 1) for index, entry in enumerate(inserted)]
        self._focus.replace_all(validate_focus_entries(renumbered))
        return next(entry for entry in renumbered if entry.id == identifier)

    def reorder_focus_entries(self, ids: Sequence[str]) -> list[FocusOrderEntry]:
        """Replace the tab order with the supplied identifier sequence."""
        existing = {entry.id: entry for entry in self._focus.list_all()}
        if len(set(ids)) != len(ids) or set(ids) != set(existing):
            raise ValidationError(
                "focus order must contain every entry exactly once",
                details={"field": "ids"},
            )
        ordered = [existing[entry_id].with_order(index + 1) for index, entry_id in enumerate(ids)]
        return self._focus.replace_all(validate_focus_entries(ordered))

    def delete_focus_entry(self, entry_id: str) -> None:
        """Remove a focus stop and close the resulting order gap."""
        existing = self._focus.list_all()
        if not any(entry.id == entry_id for entry in existing):
            raise NotFoundError(f"focus entry {entry_id!r} was not found")
        remaining = [entry for entry in existing if entry.id != entry_id]
        renumbered = [entry.with_order(index + 1) for index, entry in enumerate(remaining)]
        self._focus.replace_all(validate_focus_entries(renumbered))

    def build_focus_trap(self, *, index: int = 0) -> FocusTrap:
        """Build an in-memory focus trap from the stored tab order."""
        try:
            return FocusTrap.from_entries(self._focus.list_all(), index=index)
        except ValueError as exc:
            raise ValidationError(
                "the stored focus order is invalid", details={"message": str(exc)}
            ) from exc

    def advance_focus(
        self,
        *,
        direction: FocusDirection = FocusDirection.NEXT,
        wrap: bool = True,
        entry_id: str | None = None,
    ) -> FocusTrap:
        """Move through the focus trap from an optional starting stop."""
        trap = self.build_focus_trap()
        if entry_id is not None:
            try:
                trap = trap.move_to(entry_id)
            except ValueError as exc:
                raise NotFoundError(f"focus entry {entry_id!r} was not found") from exc
        return trap.move(direction, wrap=wrap)

    def suggest_aria_label(self, text: str, *, context: str = "", action: str = "") -> str:
        """Return a descriptive ARIA label suggestion."""
        return suggest_aria_label(text, context=context, action=action)

    def stats(self) -> AccessibilityStats:
        """Return aggregated accessibility metrics."""
        total, open_count, resolved = self._issues.count_by_state()
        severity = self._issues.count_by_severity()
        open_severity = self._issues.count_open_by_severity()
        return AccessibilityStats(
            total_issues=total,
            open_issues=open_count,
            resolved_issues=resolved,
            critical_open=open_severity["critical"],
            warning_open=open_severity["warning"],
            info_open=open_severity["info"],
            shortcut_count=self._shortcuts.count(),
            focus_entry_count=self._focus.count(),
            scopes=self._shortcuts.scopes(),
            severity_counts=severity,
        )
