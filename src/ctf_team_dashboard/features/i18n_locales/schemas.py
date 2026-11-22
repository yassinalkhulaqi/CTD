"""Typed request and response models of the i18n API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ctf_team_dashboard.features.i18n_locales.models import (
    FormatKind,
    PluralCategory,
    PluralRule,
    TextDirection,
    TranslationSource,
)


class I18nModel(BaseModel):
    """Base model that tolerates construction from domain attributes."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)


class LocaleCreate(I18nModel):
    """Payload used to register a locale."""

    code: str
    name: str
    direction: TextDirection | None = None
    plural_rules: PluralRule | None = None


class LocaleResponse(I18nModel):
    """A registered locale with its derived properties."""

    code: str
    name: str
    direction: TextDirection
    plural_rules: PluralRule
    base_language: str
    canonical_code: str
    is_rtl: bool
    chain: tuple[str, ...]


class MessagesUpsert(I18nModel):
    """Payload used to insert or replace a batch of messages."""

    locale: str
    namespace: str
    messages: dict[str, str]


class MessageResponse(I18nModel):
    """A stored catalogue message."""

    id: str
    locale: str
    namespace: str
    key: str
    value: str
    qualified_key: str
    placeholders: tuple[str, ...]
    is_empty: bool


class TranslationResponse(I18nModel):
    """The result of a translation request."""

    key: str
    locale: str
    resolved_locale: str
    value: str
    display_value: str
    source: TranslationSource
    variant: str
    found: bool
    used_fallback: bool
    interpolated: bool
    complete: bool
    missing: tuple[str, ...]
    applied: tuple[str, ...]
    plural_category: PluralCategory | None


class FormatResponse(I18nModel):
    """The result of a number or date formatting request."""

    locale: str
    kind: FormatKind
    input: str
    output: str
    pattern: str
    changed: bool


class CompletenessResponse(I18nModel):
    """Completeness of one locale and namespace."""

    locale: str
    namespace: str
    reference: str
    total: int
    translated: int
    missing: int
    missing_keys: tuple[str, ...]
    percent: float
    is_complete: bool


class MissingKeyResponse(I18nModel):
    """A reference key that is absent from a locale."""

    locale: str
    namespace: str
    key: str
    qualified_key: str
    reference_value: str
    resolved_locale: str | None
    has_fallback: bool


class FormatRuleResponse(I18nModel):
    """Formatting patterns of a locale."""

    locale: str
    number_pattern: str
    date_pattern: str
    number_example: str
    date_example: str


class FormatRuleUpdate(I18nModel):
    """Payload used to replace formatting patterns."""

    locale: str
    number_pattern: str
    date_pattern: str


class DirectionResponse(I18nModel):
    """Bidirectional information about a locale."""

    locale: str
    base_language: str
    direction: TextDirection
    is_rtl: bool
    chain: tuple[str, ...]


class ParseResponse(I18nModel):
    """The parsed representation of a locale code."""

    code: str
    canonical: str
    base_language: str
    script: str
    region: str


class CatalogResponse(I18nModel):
    """A compact overview of the catalogue."""

    locale_count: int
    message_count: int
    rtl_codes: tuple[str, ...]
    namespaces: tuple[str, ...]
    default_locale: str
