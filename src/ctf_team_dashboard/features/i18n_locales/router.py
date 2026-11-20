"""HTTP API of the internationalisation feature."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Query

from ctf_team_dashboard.errors import ValidationError
from ctf_team_dashboard.features.i18n_locales.models import (
    FormatKind,
    TextDirection,
    base_language,
    parse_locale_code,
)
from ctf_team_dashboard.features.i18n_locales.schemas import (
    CatalogResponse,
    CompletenessResponse,
    DirectionResponse,
    FormatResponse,
    FormatRuleResponse,
    FormatRuleUpdate,
    LocaleCreate,
    LocaleResponse,
    MessageResponse,
    MessagesUpsert,
    MissingKeyResponse,
    ParseResponse,
    TranslationResponse,
)
from ctf_team_dashboard.features.i18n_locales.service import I18nService

router = APIRouter(prefix="/api/i18n", tags=["i18n"])


def _service() -> I18nService:
    """Build a service bound to the process database."""
    return I18nService()


def _locale_response(service: I18nService, code: str) -> LocaleResponse:
    """Render a locale entity as an API response."""
    locale = service.get_locale(code)
    return LocaleResponse(
        code=locale.code,
        name=locale.name,
        direction=locale.direction,
        plural_rules=locale.plural_rules,
        base_language=locale.base_language,
        canonical_code=locale.canonical_code,
        is_rtl=locale.is_rtl,
        chain=locale.fallback_chain(service.default_locale),
    )


def _message_response(message: object) -> MessageResponse:
    """Render a message entity as an API response."""
    return MessageResponse.model_validate(message, from_attributes=True)


def _translation_response(result: object) -> TranslationResponse:
    """Render a translation result as an API response."""
    return TranslationResponse.model_validate(result, from_attributes=True)


def _parse_values(raw: str | None) -> dict[str, object]:
    """Decode the JSON encoded placeholder values query parameter."""
    if not raw:
        return {}
    try:
        decoded: Any = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValidationError("values must be a JSON object", details={"values": raw}) from error
    if not isinstance(decoded, dict):
        raise ValidationError("values must be a JSON object")
    return {str(key): value for key, value in decoded.items()}


@router.get("/locales", response_model=list[LocaleResponse])
def list_locales() -> list[LocaleResponse]:
    """Return every registered locale."""
    service = _service()
    return [_locale_response(service, locale.code) for locale in service.list_locales()]


@router.post("/locales", response_model=LocaleResponse, status_code=201)
def create_locale(payload: LocaleCreate) -> LocaleResponse:
    """Register a locale."""
    service = _service()
    locale = service.register_locale(
        payload.code,
        payload.name,
        direction=payload.direction,
        plural_rules=payload.plural_rules,
    )
    return _locale_response(service, locale.code)


@router.get("/messages", response_model=list[MessageResponse])
def list_messages(
    locale: Annotated[str | None, Query()] = None,
    namespace: Annotated[str | None, Query()] = None,
) -> list[MessageResponse]:
    """Return messages with optional filters."""
    return [_message_response(item) for item in _service().list_messages(locale, namespace)]


@router.put("/messages", response_model=list[MessageResponse])
def upsert_messages(payload: MessagesUpsert) -> list[MessageResponse]:
    """Insert or replace a batch of messages."""
    messages = _service().upsert_messages(payload.locale, payload.namespace, payload.messages)
    return [_message_response(item) for item in messages]


@router.get("/translate", response_model=TranslationResponse)
def translate(
    locale: Annotated[str, Query()],
    namespace: Annotated[str, Query()],
    key: Annotated[str, Query()],
    count: Annotated[int | None, Query()] = None,
    values: Annotated[str | None, Query()] = None,
) -> TranslationResponse:
    """Translate a key with fallback, plural rules and interpolation."""
    result = _service().translate(
        locale,
        namespace,
        key,
        count=count,
        values=_parse_values(values),
    )
    return _translation_response(result)


@router.get("/format", response_model=FormatResponse)
def format_value(
    locale: Annotated[str, Query()],
    kind: Annotated[FormatKind, Query()] = FormatKind.NUMBER,
    value: Annotated[str, Query()] = "",
    pattern: Annotated[str | None, Query()] = None,
) -> FormatResponse:
    """Format a number or an ISO date with locale patterns."""
    service = _service()
    if kind is FormatKind.NUMBER:
        try:
            number = float(value)
        except ValueError as error:
            raise ValidationError("value must be a number", details={"value": value}) from error
        result = service.format_number(locale, number, pattern=pattern)
    else:
        result = service.format_date(locale, value, pattern=pattern)
    return FormatResponse(
        locale=result.locale,
        kind=result.kind,
        input=result.input,
        output=result.output,
        pattern=result.pattern,
        changed=result.changed,
    )


@router.get("/completeness", response_model=list[CompletenessResponse])
def completeness(
    reference: Annotated[str, Query()] = "en",
) -> list[CompletenessResponse]:
    """Report translation completeness against a reference locale."""
    stats = _service().completeness(reference)
    return [
        CompletenessResponse(
            locale=stat.locale,
            namespace=stat.namespace,
            reference=stat.reference,
            total=stat.total,
            translated=stat.translated,
            missing=stat.missing,
            missing_keys=stat.missing_keys,
            percent=stat.percent,
            is_complete=stat.is_complete,
        )
        for stat in stats
    ]


@router.get("/missing-keys", response_model=list[MissingKeyResponse])
def missing_keys(
    locale: Annotated[str, Query()],
    namespace: Annotated[str | None, Query()] = None,
) -> list[MissingKeyResponse]:
    """List untranslated reference keys for a locale."""
    items = _service().missing_keys(locale, namespace)
    return [
        MissingKeyResponse(
            locale=item.locale,
            namespace=item.namespace,
            key=item.key,
            qualified_key=item.qualified_key,
            reference_value=item.reference_value,
            resolved_locale=item.resolved_locale,
            has_fallback=item.has_fallback,
        )
        for item in items
    ]


@router.get("/direction", response_model=DirectionResponse)
def direction(locale: Annotated[str, Query()]) -> DirectionResponse:
    """Report the writing direction and fallback chain of a locale."""
    service = _service()
    code = service.require_code(locale)
    return DirectionResponse(
        locale=code,
        base_language=base_language(code),
        direction=service.direction_for(code),
        is_rtl=service.direction_for(code) is TextDirection.RTL,
        chain=service.chain_for(code),
    )


@router.get("/parse", response_model=ParseResponse)
def parse_locale(locale: Annotated[str, Query()]) -> ParseResponse:
    """Parse a locale code into its components."""
    service = _service()
    parsed = parse_locale_code(service.require_code(locale))
    return ParseResponse(
        code=parsed.raw,
        canonical=parsed.canonical,
        base_language=parsed.base,
        script=parsed.script,
        region=parsed.region,
    )


@router.get("/format-rules", response_model=list[FormatRuleResponse])
def list_format_rules() -> list[FormatRuleResponse]:
    """Return the stored formatting rules."""
    return [
        FormatRuleResponse(
            locale=rule.locale,
            number_pattern=rule.number_pattern,
            date_pattern=rule.date_pattern,
            number_example=rule.number_example(),
            date_example=rule.date_example(),
        )
        for rule in _service().store.format_rules.all()
    ]


@router.put("/format-rules", response_model=FormatRuleResponse)
def upsert_format_rule(payload: FormatRuleUpdate) -> FormatRuleResponse:
    """Store the formatting rules of a locale."""
    rule = _service().set_format_rule(payload.locale, payload.number_pattern, payload.date_pattern)
    return FormatRuleResponse(
        locale=rule.locale,
        number_pattern=rule.number_pattern,
        date_pattern=rule.date_pattern,
        number_example=rule.number_example(),
        date_example=rule.date_example(),
    )


@router.get("/catalog", response_model=CatalogResponse)
def catalog() -> CatalogResponse:
    """Return a compact overview of the registered catalogue."""
    service = _service()
    snapshot = service.snapshot()
    return CatalogResponse(
        locale_count=snapshot.locale_count,
        message_count=snapshot.message_count,
        rtl_codes=snapshot.rtl_codes,
        namespaces=snapshot.namespaces(),
        default_locale=service.default_locale,
    )
