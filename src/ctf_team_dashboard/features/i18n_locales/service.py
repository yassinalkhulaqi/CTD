"""Business rules for locale registration, translation and formatting."""

from __future__ import annotations

import re
from typing import Any

from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.i18n_locales.models import (
    DEFAULT_LOCALE,
    CatalogSnapshot,
    CompletenessStat,
    FormatKind,
    FormatResult,
    FormatRule,
    Locale,
    Message,
    MissingKey,
    PluralCategory,
    PluralRule,
    TextDirection,
    TranslationResult,
    TranslationSource,
    base_language,
    default_format_rule,
    direction_for,
    extract_placeholders,
    fallback_chain,
    interpolate,
    parse_locale_code,
    plural_key,
    validate_date_pattern,
    validate_number_pattern,
)
from ctf_team_dashboard.features.i18n_locales.store import I18nStore, message_id

_NAMESPACE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+$")

_PLURAL_DEFAULTS: dict[str, PluralRule] = {
    "ar": PluralRule.ARABIC,
    "ru": PluralRule.SLAVIC,
    "uk": PluralRule.SLAVIC,
    "pl": PluralRule.SLAVIC,
    "cs": PluralRule.SLAVIC,
    "sk": PluralRule.SLAVIC,
}


class I18nService:
    """Coordinate the catalogue, formatting rules and translation fallback."""

    def __init__(self, store: I18nStore | None = None, default: str = DEFAULT_LOCALE) -> None:
        self._store = store or I18nStore()
        self._default = default.strip().lower() or DEFAULT_LOCALE

    @property
    def store(self) -> I18nStore:
        """Return the persistence facade used by the service."""
        return self._store

    @property
    def default_locale(self) -> str:
        """Return the final fallback locale code."""
        return self._default

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def require_code(code: str) -> str:
        """Validate a locale code and return its stripped form."""
        if not isinstance(code, str) or not code.strip():
            raise ValidationError("locale code must not be empty")
        try:
            parse_locale_code(code)
        except ValueError as error:
            raise ValidationError(str(error), details={"code": code}) from error
        return code.strip()

    @staticmethod
    def require_namespace(namespace: str) -> str:
        """Validate a namespace identifier."""
        candidate = namespace.strip()
        if not candidate or not _NAMESPACE_PATTERN.fullmatch(candidate):
            raise ValidationError(
                "namespace must contain only letters, digits, hyphens or underscores",
                details={"namespace": namespace},
            )
        return candidate

    @staticmethod
    def require_key(key: str) -> str:
        """Validate a message key."""
        candidate = key.strip()
        if not candidate or not _KEY_PATTERN.fullmatch(candidate):
            raise ValidationError(
                "key must contain only letters, digits, dots, hyphens or underscores",
                details={"key": key},
            )
        return candidate

    @staticmethod
    def require_name(name: str) -> str:
        """Validate a locale display name."""
        candidate = name.strip()
        if not candidate:
            raise ValidationError("locale name must not be empty")
        return candidate

    # ------------------------------------------------------------------
    # Locale catalogue
    # ------------------------------------------------------------------
    def register_locale(
        self,
        code: str,
        name: str,
        *,
        direction: TextDirection | None = None,
        plural_rules: PluralRule | None = None,
    ) -> Locale:
        """Register a new locale.

        Args:
            code: The BCP-47 style locale identifier.
            name: The English display name of the language.
            direction: An optional direction override; detected when omitted.
            plural_rules: An optional rule family; inferred when omitted.

        Returns:
            The registered locale.

        Raises:
            ValidationError: When the code or name is invalid.
            ConflictError: When the code was already registered.
        """
        valid_code = self.require_code(code)
        valid_name = self.require_name(name)
        if self._store.locales.find(valid_code) is not None:
            raise ConflictError(
                f"locale {valid_code!r} is already registered",
                details={"code": valid_code},
            )
        resolved_direction = direction or direction_for(valid_code)
        resolved_rules = plural_rules or _PLURAL_DEFAULTS.get(
            base_language(valid_code), PluralRule.SIMPLE
        )
        locale = Locale(
            code=valid_code,
            name=valid_name,
            direction=resolved_direction,
            plural_rules=resolved_rules,
        )
        return self._store.locales.insert(locale)

    def list_locales(self) -> list[Locale]:
        """Return registered locales ordered by code."""
        return self._store.locales.all()

    def get_locale(self, code: str) -> Locale:
        """Return a registered locale or raise ``NotFoundError``."""
        valid_code = self.require_code(code)
        locale = self._store.locales.find(valid_code)
        if locale is None:
            raise NotFoundError(
                f"locale {valid_code!r} is not registered", details={"code": valid_code}
            )
        return locale

    def direction_for(self, code: str) -> TextDirection:
        """Return the writing direction of a locale code."""
        return direction_for(self.require_code(code))

    def chain_for(self, code: str) -> tuple[str, ...]:
        """Return the fallback chain of a locale code."""
        return fallback_chain(self.require_code(code), self._default)

    def parse(self, code: str) -> str:
        """Return the canonical form of a locale code."""
        parsed = parse_locale_code(self.require_code(code))
        return parsed.canonical

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------
    def upsert_messages(
        self, locale: str, namespace: str, entries: dict[str, str]
    ) -> list[Message]:
        """Insert or replace a batch of messages for one locale.

        Args:
            locale: The target locale, which must be registered.
            namespace: The catalogue namespace.
            entries: Mapping of message key to translated value.

        Returns:
            The stored messages ordered by key.

        Raises:
            ValidationError: When a key or value is invalid.
            NotFoundError: When the locale is not registered.
        """
        valid_code = self.require_code(locale)
        valid_namespace = self.require_namespace(namespace)
        self.get_locale(valid_code)
        if not entries:
            return []
        prepared: list[Message] = []
        for raw_key, raw_value in entries.items():
            key = self.require_key(raw_key)
            if not isinstance(raw_value, str):
                raise ValidationError("message values must be strings", details={"key": key})
            prepared.append(
                Message(
                    id=message_id(valid_code, valid_namespace, key),
                    locale=valid_code,
                    namespace=valid_namespace,
                    key=key,
                    value=raw_value,
                )
            )
        stored = self._store.messages.upsert_many(prepared)
        return sorted(stored, key=lambda item: item.key)

    def list_messages(
        self, locale: str | None = None, namespace: str | None = None
    ) -> list[Message]:
        """Return messages with optional locale and namespace filters."""
        valid_code = self.require_code(locale) if locale is not None else None
        valid_namespace = self.require_namespace(namespace) if namespace is not None else None
        return self._store.messages.all(valid_code, valid_namespace)

    def get_message(self, locale: str, namespace: str, key: str) -> Message:
        """Return one message or raise ``NotFoundError``."""
        valid_code = self.require_code(locale)
        valid_namespace = self.require_namespace(namespace)
        valid_key = self.require_key(key)
        message = self._store.messages.find(valid_code, valid_namespace, valid_key)
        if message is None:
            raise NotFoundError(
                f"message {valid_namespace}:{valid_key} not found for {valid_code}",
                details={"locale": valid_code, "namespace": valid_namespace, "key": valid_key},
            )
        return message

    def placeholders_for(self, locale: str, namespace: str, key: str) -> tuple[str, ...]:
        """Return the placeholder names referenced by a stored message."""
        return extract_placeholders(self.get_message(locale, namespace, key).value)

    def _lookup(
        self, candidates: list[str], namespace: str, variants: list[str]
    ) -> tuple[Message, str, str] | None:
        """Return the first matching message along with its locale and key."""
        for candidate in candidates:
            for variant in variants:
                message = self._store.messages.find(candidate, namespace, variant)
                if message is not None and not message.is_empty:
                    return message, candidate, variant
        return None

    def _source_for(
        self, requested: str, resolved: str, variant: str, key: str
    ) -> TranslationSource:
        """Classify where a resolved translation came from."""
        if variant != key:
            return TranslationSource.PLURAL
        if resolved.lower() == requested.lower():
            return TranslationSource.EXACT
        if resolved.lower() == base_language(requested):
            return TranslationSource.BASE
        return TranslationSource.DEFAULT

    def translate(
        self,
        locale: str,
        namespace: str,
        key: str,
        *,
        count: int | None = None,
        values: dict[str, object] | None = None,
    ) -> TranslationResult:
        """Translate a key with fallback, plural selection and interpolation.

        Args:
            locale: The requested locale.
            namespace: The catalogue namespace.
            key: The base message key.
            count: When supplied, selects a plural variant of the key.
            values: Placeholder values used for interpolation.

        Returns:
            A result describing the value and how it was resolved.
        """
        requested = self.require_code(locale)
        valid_namespace = self.require_namespace(namespace)
        valid_key = self.require_key(key)
        chain = list(fallback_chain(requested, self._default))
        registered = self._store.locales.codes()
        known = {code.lower() for code in registered}
        candidates = [item for item in chain if item.lower() in known]
        if not candidates:
            candidates = chain

        category: PluralCategory | None = None
        variants = [valid_key]
        if count is not None:
            locale_entity = self._store.locales.find(requested) or Locale(
                code=requested, name=requested
            )
            category = locale_entity.category_for(count)
            variants = [plural_key(valid_key, category), valid_key]

        match = self._lookup(candidates, valid_namespace, variants)
        if match is None:
            return TranslationResult(
                key=valid_key,
                locale=requested,
                resolved_locale="",
                value=valid_key,
                source=TranslationSource.MISSING,
                variant=valid_key,
                plural_category=category,
            )

        message, resolved, variant = match
        rendered = interpolate(message.value, values)
        return TranslationResult(
            key=valid_key,
            locale=requested,
            resolved_locale=resolved,
            value=rendered.value,
            source=self._source_for(requested, resolved, variant, valid_key),
            variant=variant,
            applied=rendered.applied,
            missing=rendered.missing,
            plural_category=category,
        )

    def translate_many(
        self,
        locale: str,
        namespace: str,
        keys: list[str],
        *,
        values: dict[str, object] | None = None,
    ) -> list[TranslationResult]:
        """Translate a batch of keys using one fallback chain."""
        return [self.translate(locale, namespace, key, values=values) for key in keys]

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------
    def get_format_rule(self, locale: str) -> FormatRule:
        """Return the stored rule of a locale or its sensible default."""
        valid_code = self.require_code(locale)
        stored = self._store.format_rules.find(valid_code)
        return stored if stored is not None else default_format_rule(valid_code)

    def set_format_rule(self, locale: str, number_pattern: str, date_pattern: str) -> FormatRule:
        """Validate and store the formatting rules of a locale."""
        valid_code = self.require_code(locale)
        self.get_locale(valid_code)
        try:
            rule = FormatRule(
                locale=valid_code,
                number_pattern=validate_number_pattern(number_pattern),
                date_pattern=validate_date_pattern(date_pattern),
            )
        except ValueError as error:
            raise ValidationError(str(error)) from error
        return self._store.format_rules.upsert(rule)

    def format_number(
        self, locale: str, value: float, *, pattern: str | None = None
    ) -> FormatResult:
        """Format a number with a locale rule or an explicit pattern."""
        valid_code = self.require_code(locale)
        rule = self.get_format_rule(valid_code)
        if pattern is not None:
            try:
                rule = FormatRule(
                    locale=valid_code,
                    number_pattern=validate_number_pattern(pattern),
                    date_pattern=rule.date_pattern,
                )
            except ValueError as error:
                raise ValidationError(str(error)) from error
        output = rule.number(value)
        return FormatResult(
            locale=valid_code,
            kind=FormatKind.NUMBER,
            input=str(value),
            output=output,
            pattern=rule.number_pattern,
        )

    def format_date(self, locale: str, value: str, *, pattern: str | None = None) -> FormatResult:
        """Format an ISO date with a locale rule or an explicit pattern."""
        valid_code = self.require_code(locale)
        rule = self.get_format_rule(valid_code)
        if pattern is not None:
            try:
                rule = FormatRule(
                    locale=valid_code,
                    number_pattern=rule.number_pattern,
                    date_pattern=validate_date_pattern(pattern),
                )
            except ValueError as error:
                raise ValidationError(str(error)) from error
        try:
            output = rule.date(value)
        except ValueError as error:
            raise ValidationError(str(error), details={"value": value}) from error
        return FormatResult(
            locale=valid_code,
            kind=FormatKind.DATE,
            input=value,
            output=output,
            pattern=rule.date_pattern,
        )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def completeness(self, reference: str = DEFAULT_LOCALE) -> list[CompletenessStat]:
        """Compare every locale against the reference catalogue."""
        valid_reference = self.require_code(reference)
        self.get_locale(valid_reference)
        reference_rows = self._store.messages.all(locale=valid_reference)
        groups: dict[str, dict[str, str]] = {}
        for message in reference_rows:
            if message.is_empty:
                continue
            groups.setdefault(message.namespace, {})[message.key] = message.value

        stats: list[CompletenessStat] = []
        for locale in self.list_locales():
            for namespace in sorted(groups):
                keys = tuple(sorted(groups[namespace]))
                stored = {
                    message.key
                    for message in self._store.messages.all(locale=locale.code, namespace=namespace)
                    if not message.is_empty
                }
                translated = tuple(key for key in keys if key in stored)
                stats.append(
                    CompletenessStat(
                        locale=locale.code,
                        namespace=namespace,
                        reference=valid_reference,
                        total=len(keys),
                        translated=len(translated),
                        missing_keys=tuple(key for key in keys if key not in stored),
                    )
                )
        return stats

    def missing_keys(self, locale: str, namespace: str | None = None) -> list[MissingKey]:
        """List reference keys without a translation in the target locale."""
        valid_code = self.require_code(locale)
        valid_namespace = self.require_namespace(namespace) if namespace else None
        self.get_locale(valid_code)

        reference_rows = self._store.messages.all(locale=self._default)
        stored = {
            (message.namespace, message.key)
            for message in self._store.messages.all(locale=valid_code)
            if not message.is_empty
        }
        chain = [
            item
            for item in fallback_chain(valid_code, self._default)
            if item.lower() != valid_code.lower()
        ]
        results: list[MissingKey] = []
        for message in reference_rows:
            if message.is_empty:
                continue
            if valid_namespace is not None and message.namespace != valid_namespace:
                continue
            pair = (message.namespace, message.key)
            if pair in stored:
                continue
            fallback = None
            for candidate in chain:
                other = self._store.messages.find(candidate, message.namespace, message.key)
                if other is not None and not other.is_empty:
                    fallback = candidate
                    break
            results.append(
                MissingKey(
                    locale=valid_code,
                    namespace=message.namespace,
                    key=message.key,
                    reference_value=message.value,
                    resolved_locale=fallback,
                )
            )
        return sorted(results, key=lambda item: (item.namespace, item.key))

    def snapshot(self) -> CatalogSnapshot:
        """Return a combined view of the catalogue."""
        return CatalogSnapshot(
            locales=tuple(self.list_locales()),
            messages=tuple(self.list_messages()),
        )

    def describe(self, locale: str, namespace: str, key: str, count: int | None = None) -> str:
        """Return a compact diagnostic string for one translation."""
        result = self.translate(locale, namespace, key, count=count)
        return (
            f"{result.locale}:{namespace}:{key} -> {result.display_value} [{result.source.value}]"
        )

    def as_mapping(self, locale: str, namespace: str) -> dict[str, Any]:
        """Return the messages of one locale and namespace as a plain mapping."""
        return {message.key: message.value for message in self.list_messages(locale, namespace)}
