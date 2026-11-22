"""Tests for the internationalisation and locale framework."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.db.engine import Database
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.i18n_locales.models import (
    CompletenessStat,
    FormatKind,
    FormatRule,
    Locale,
    PluralCategory,
    PluralRule,
    TextDirection,
    TranslationSource,
    base_language,
    direction_for,
    extract_placeholders,
    fallback_chain,
    format_date,
    format_number,
    interpolate,
    parse_locale_code,
    plural_category,
    plural_key,
)
from ctf_team_dashboard.features.i18n_locales.service import I18nService
from ctf_team_dashboard.features.i18n_locales.store import MessageRepository, message_id


@pytest.fixture
def service(database: Database) -> I18nService:
    """Return a service bound to the isolated test database."""
    return I18nService()


@pytest.fixture
def catalog(service: I18nService) -> I18nService:
    """Return a service with a small multi-locale catalogue."""
    service.register_locale("en", "English")
    service.register_locale("fr", "French")
    service.register_locale("fr-CA", "Canadian French")
    service.register_locale("ar", "Arabic", plural_rules=PluralRule.ARABIC)
    service.upsert_messages(
        "en",
        "ui",
        {
            "greeting": "Hello, {name}!",
            "greeting.one": "Hello, {name}!",
            "greeting.other": "Hello, {name}!",
            "items.one": "{count} item",
            "items.other": "{count} items",
            "farewell": "Goodbye",
            "empty": "",
        },
    )
    service.upsert_messages("fr", "ui", {"greeting": "Bonjour, {name} !", "farewell": "Au revoir"})
    service.upsert_messages("ar", "ui", {"greeting": "مرحبا، {name}!"})
    return service


def _seed_api(client: TestClient) -> None:
    """Populate a catalogue through the public API."""
    for code, name in (("en", "English"), ("fr", "French"), ("ar", "Arabic")):
        response = client.post("/api/i18n/locales", json={"code": code, "name": name})
        assert response.status_code == 201
    response = client.put(
        "/api/i18n/messages",
        json={
            "locale": "en",
            "namespace": "ui",
            "messages": {
                "greeting": "Hello, {name}!",
                "items.one": "{count} item",
                "items.other": "{count} items",
                "farewell": "Goodbye",
            },
        },
    )
    assert response.status_code == 200
    response = client.put(
        "/api/i18n/messages",
        json={
            "locale": "fr",
            "namespace": "ui",
            "messages": {"greeting": "Bonjour, {name} !"},
        },
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------
def test_parse_locale_code_components() -> None:
    parsed = parse_locale_code("zh-Hant-TW")
    assert parsed.language == "zh"
    assert parsed.script == "hant"
    assert parsed.region == "tw"
    assert parsed.canonical == "zh-Hant-TW"
    assert parsed.subtags == ("zh", "hant", "tw")
    assert base_language("EN-us") == "en"


def test_parse_locale_code_rejects_invalid_values() -> None:
    for candidate in ("", "e", "english", "en-US-extra-long-subtag"):
        with pytest.raises(ValueError):
            parse_locale_code(candidate)


def test_fallback_chain_dedupes_and_keeps_order() -> None:
    assert fallback_chain("fr-CA") == ("fr-CA", "fr", "en")
    assert fallback_chain("en-US") == ("en-US", "en")
    assert fallback_chain("ar", default="en") == ("ar", "en")
    assert parse_locale_code("en").canonical == "en"


def test_direction_detection() -> None:
    assert direction_for("ar-EG") is TextDirection.RTL
    assert direction_for("he") is TextDirection.RTL
    assert direction_for("fr-CA") is TextDirection.LTR
    urdu = Locale(code="ur", name="Urdu", direction=direction_for("ur"))
    assert urdu.is_rtl


@pytest.mark.parametrize(
    ("rule", "count", "expected"),
    [
        (PluralRule.SIMPLE, 1, PluralCategory.ONE),
        (PluralRule.SIMPLE, 2, PluralCategory.OTHER),
        (PluralRule.ARABIC, 0, PluralCategory.ZERO),
        (PluralRule.ARABIC, 1, PluralCategory.ONE),
        (PluralRule.ARABIC, 2, PluralCategory.TWO),
        (PluralRule.ARABIC, 7, PluralCategory.FEW),
        (PluralRule.ARABIC, 21, PluralCategory.MANY),
        (PluralRule.ARABIC, 101, PluralCategory.ONE),
        (PluralRule.ARABIC, 102, PluralCategory.TWO),
        (PluralRule.ARABIC, 15, PluralCategory.MANY),
        (PluralRule.SLAVIC, 1, PluralCategory.ONE),
        (PluralRule.SLAVIC, 3, PluralCategory.FEW),
        (PluralRule.SLAVIC, 11, PluralCategory.MANY),
        (PluralRule.NONE, 1, PluralCategory.OTHER),
    ],
)
def test_plural_categories(rule: PluralRule, count: int, expected: PluralCategory) -> None:
    assert plural_category(rule, count) is expected
    assert plural_key("items", expected) == f"items.{expected.value}"


def test_placeholder_extraction_and_interpolation() -> None:
    template = "Hello {name}, you have {count} {item}."
    assert extract_placeholders(template) == ("name", "count", "item")
    rendered = interpolate(template, {"name": "Ada", "count": 3})
    assert rendered.value == "Hello Ada, you have 3 {item}."
    assert rendered.applied == ("name", "count")
    assert rendered.missing == ("item",)
    assert not rendered.complete


def test_interpolation_unescapes_braces() -> None:
    rendered = interpolate("Use {{name}} for {name}", {"name": "Ada"})
    assert rendered.value == "Use {name} for Ada"
    assert rendered.complete


def test_number_patterns() -> None:
    assert format_number(1234567.891, "#,##0.00") == "1,234,567.89"
    assert format_number(1234.5, "0") == "1235"
    assert format_number(12.3456, "0.000") == "12.346"
    assert format_number(1234.5, "#,##0") == "1,235"


def test_date_patterns_and_localised_months() -> None:
    assert format_date("2026-11-20", "YYYY-MM-DD") == "2026-11-20"
    assert format_date("2026-11-20", "DD/MM/YYYY") == "20/11/2026"
    assert format_date("2026-11-20", "MMM DD, YYYY", "en") == "Nov 20, 2026"
    assert format_date("2026-11-20", "MMMM YYYY", "fr") == "novembre 2026"
    assert format_date("2026-11-20", "YY.MM.DD") == "26.11.20"


def test_format_rule_validation_and_examples() -> None:
    rule = FormatRule(locale="en", number_pattern="#,##0.0", date_pattern="DD/MM/YYYY")
    assert rule.number_example() == "1,234,567.9"
    assert rule.date_example() == "20/11/2026"
    with pytest.raises(ValueError):
        FormatRule(locale="en", number_pattern="abc")
    with pytest.raises(ValueError):
        FormatRule(locale="en", date_pattern="QQ/YYYY")


def test_completeness_statistics() -> None:
    stat = CompletenessStat(
        locale="fr", namespace="ui", reference="en", total=4, translated=3, missing_keys=("x",)
    )
    assert stat.missing == 1
    assert stat.percent == 75.0
    assert not stat.is_complete
    assert stat.describe() == "fr/ui: 75.0%"
    empty = CompletenessStat(locale="fr", namespace="ui", reference="en", total=0, translated=0)
    assert empty.percent == 0.0


def test_translation_result_flags() -> None:
    from ctf_team_dashboard.features.i18n_locales.models import TranslationResult

    exact = TranslationResult(
        key="k",
        locale="en",
        resolved_locale="en",
        value="Value",
        source=TranslationSource.EXACT,
        variant="k",
        applied=("name",),
    )
    missing = TranslationResult(
        key="k",
        locale="fr",
        resolved_locale="",
        value="k",
        source=TranslationSource.MISSING,
        variant="k",
    )
    assert exact.found
    assert exact.interpolated
    assert exact.complete
    assert not exact.used_fallback
    assert not missing.found
    assert missing.display_value == "[k]"


def test_message_helpers() -> None:
    from ctf_team_dashboard.features.i18n_locales.models import Message

    message = Message(
        id=message_id("en", "ui", "greeting"),
        locale="en",
        namespace="ui",
        key="greeting",
        value="Hi {name}",
    )
    assert message.qualified_key == "ui:greeting"
    assert message.placeholders == ("name",)
    assert message.matches("EN", "ui", "greeting")
    assert message.render({"name": "Ada"}).value == "Hi Ada"
    assert not message.with_value("").value


# ---------------------------------------------------------------------------
# Store and service
# ---------------------------------------------------------------------------
def test_store_upsert_updates_existing_row(service: I18nService) -> None:
    service.register_locale("en", "English")
    first = service.upsert_messages("en", "ui", {"key": "one"})
    second = service.upsert_messages("en", "ui", {"key": "two"})
    assert first[0].id == second[0].id
    assert second[0].value == "two"
    assert service.store.messages.count() == 1
    assert len(MessageRepository().all()) == 1


def test_register_locale_defaults_and_conflict(service: I18nService) -> None:
    arabic = service.register_locale("ar", "Arabic")
    russian = service.register_locale("ru", "Russian")
    assert arabic.direction is TextDirection.RTL
    assert arabic.plural_rules is PluralRule.ARABIC
    assert russian.plural_rules is PluralRule.SLAVIC
    with pytest.raises(ConflictError, match="already registered"):
        service.register_locale("ar", "Arabic again")


def test_register_locale_validation(service: I18nService) -> None:
    with pytest.raises(ValidationError, match="code"):
        service.register_locale("!", "Invalid")
    with pytest.raises(ValidationError, match="name"):
        service.register_locale("en", "   ")


def test_upsert_messages_validation_and_filters(catalog: I18nService) -> None:
    with pytest.raises(ValidationError, match="key"):
        catalog.upsert_messages("en", "ui", {"bad key": "value"})
    with pytest.raises(ValidationError, match="namespace"):
        catalog.upsert_messages("en", "bad ns", {"key": "value"})
    with pytest.raises(NotFoundError, match="not registered"):
        catalog.upsert_messages("xx", "ui", {"key": "value"})
    assert len(catalog.list_messages(namespace="ui")) >= 10
    assert catalog.list_messages(locale="ar")[0].locale == "ar"
    with pytest.raises(NotFoundError, match="not found"):
        catalog.get_message("en", "ui", "missing")


def test_translate_exact_with_interpolation(catalog: I18nService) -> None:
    result = catalog.translate("en", "ui", "greeting", values={"name": "Ada"})
    assert result.value == "Hello, Ada!"
    assert result.source is TranslationSource.EXACT
    assert result.resolved_locale == "en"
    assert result.found
    assert result.interpolated
    assert result.complete


def test_translate_base_and_default_fallback(catalog: I18nService) -> None:
    base = catalog.translate("fr-CA", "ui", "greeting", values={"name": "Ada"})
    assert base.source is TranslationSource.BASE
    assert base.resolved_locale == "fr"
    assert base.value == "Bonjour, Ada !"
    default = catalog.translate("fr-CA", "ui", "items.one")
    assert default.source is TranslationSource.DEFAULT
    assert default.resolved_locale == "en"


def test_translate_plural_selection(catalog: I18nService) -> None:
    singular = catalog.translate("en", "ui", "items", count=1, values={"count": 1})
    plural = catalog.translate("en", "ui", "items", count=5, values={"count": 5})
    arabic = catalog.translate("ar", "ui", "items", count=3, values={"count": 3})
    assert singular.variant == "items.one"
    assert plural.variant == "items.other"
    assert plural.value == "5 items"
    assert arabic.plural_category is PluralCategory.FEW
    assert arabic.source is TranslationSource.MISSING


def test_translate_missing_and_incomplete_placeholders(catalog: I18nService) -> None:
    missing = catalog.translate("en", "ui", "unknown")
    assert missing.source is TranslationSource.MISSING
    assert missing.display_value == "[unknown]"
    incomplete = catalog.translate("en", "ui", "greeting")
    assert incomplete.missing == ("name",)
    assert not incomplete.complete


def test_translate_many_and_mapping(catalog: I18nService) -> None:
    results = catalog.translate_many("fr", "ui", ["farewell", "greeting"])
    assert len(results) == 2
    assert set(catalog.as_mapping("ar", "ui")) == {"greeting"}
    assert "exact" in catalog.describe("en", "ui", "farewell")


def test_formatting_through_service(catalog: I18nService) -> None:
    number = catalog.format_number("en", 1234.567, pattern="#,##0.0")
    date = catalog.format_date("en", "2026-11-20", pattern="MMM DD, YYYY")
    assert number.output == "1,234.6"
    assert date.output == "Nov 20, 2026"
    assert number.changed
    assert date.kind is FormatKind.DATE
    rule = catalog.set_format_rule("fr", "#,##0", "DD/MM/YYYY")
    assert rule.number_example() == "1,234,568"
    assert catalog.format_date("fr", "2026-11-20").output == "20/11/2026"


def test_default_format_rules(catalog: I18nService) -> None:
    assert catalog.get_format_rule("en").date_pattern == "MM/DD/YYYY"
    assert catalog.get_format_rule("fr").date_pattern == "DD/MM/YYYY"
    assert catalog.get_format_rule("ja").number_pattern == "#,##0"


def test_invalid_patterns_are_rejected(catalog: I18nService) -> None:
    with pytest.raises(ValidationError, match="number pattern"):
        catalog.set_format_rule("en", "bad", "YYYY-MM-DD")
    with pytest.raises(ValidationError, match="date pattern"):
        catalog.set_format_rule("en", "#,##0.00", "QQ-MM")
    with pytest.raises(ValidationError, match="date"):
        catalog.format_date("en", "not-a-date")


def test_completeness_report(catalog: I18nService) -> None:
    stats = {stat.locale: stat for stat in catalog.completeness()}
    assert set(stats) == {"en", "fr", "fr-CA", "ar"}
    assert stats["en"].percent == 100.0
    assert stats["fr"].percent < 100.0
    assert "greeting.one" in stats["fr"].missing_keys
    assert stats["ar"].is_complete is False
    with pytest.raises(NotFoundError):
        catalog.completeness("zz")


def test_missing_keys_report(catalog: I18nService) -> None:
    items = catalog.missing_keys("fr", "ui")
    keys = {item.key for item in items}
    assert "items.one" in keys
    assert "greeting" not in keys
    matching = next(item for item in items if item.key == "items.one")
    assert matching.reference_value == "{count} item"
    assert matching.resolved_locale == "en"
    assert matching.has_fallback
    assert all(item.namespace == "ui" for item in catalog.missing_keys("ar", "ui"))


def test_direction_chain_and_parse(catalog: I18nService) -> None:
    assert catalog.direction_for("ar") is TextDirection.RTL
    assert catalog.chain_for("fr-CA") == ("fr-CA", "fr", "en")
    assert catalog.parse("zh-Hant-TW") == "zh-Hant-TW"
    snapshot = catalog.snapshot()
    assert snapshot.locale_count == 4
    assert snapshot.message_count >= 10
    assert snapshot.rtl_codes == ("ar",)
    assert "ui" in snapshot.namespaces()


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------
def test_api_locale_endpoints(client: TestClient) -> None:
    assert client.get("/api/i18n/locales").json() == []
    created = client.post(
        "/api/i18n/locales",
        json={"code": "fr-CA", "name": "Canadian French", "plural_rules": "simple"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["base_language"] == "fr"
    assert body["chain"] == ["fr-CA", "fr", "en"]
    duplicate = client.post("/api/i18n/locales", json={"code": "fr-CA", "name": "Again"})
    assert duplicate.status_code == 409
    assert len(client.get("/api/i18n/locales").json()) == 1


def test_api_message_endpoints(client: TestClient, database: Database) -> None:
    _seed_api(client)
    messages = client.get("/api/i18n/messages", params={"locale": "en", "namespace": "ui"}).json()
    assert len(messages) == 4
    assert messages[0]["qualified_key"] == "ui:farewell"
    updated = client.put(
        "/api/i18n/messages",
        json={"locale": "en", "namespace": "ui", "messages": {"farewell": "Bye"}},
    )
    assert updated.status_code == 200
    assert updated.json()[0]["value"] == "Bye"
    assert client.get("/api/i18n/messages", params={"locale": "zz"}).json() == []


def test_api_translate_endpoint(client: TestClient) -> None:
    _seed_api(client)
    exact = client.get(
        "/api/i18n/translate",
        params={"locale": "en", "namespace": "ui", "key": "greeting", "values": '{"name": "Ada"}'},
    )
    assert exact.status_code == 200
    assert exact.json()["value"] == "Hello, Ada!"
    plural = client.get(
        "/api/i18n/translate",
        params={
            "locale": "en",
            "namespace": "ui",
            "key": "items",
            "count": 2,
            "values": '{"count": 2}',
        },
    ).json()
    assert plural["variant"] == "items.other"
    missing = client.get(
        "/api/i18n/translate", params={"locale": "en", "namespace": "ui", "key": "nope"}
    ).json()
    assert missing["source"] == "missing"
    assert missing["display_value"] == "[nope]"
    base = client.get(
        "/api/i18n/translate",
        params={
            "locale": "fr-CA",
            "namespace": "ui",
            "key": "greeting",
            "values": '{"name": "Ada"}',
        },
    ).json()
    assert base["source"] == "base"
    assert base["resolved_locale"] == "fr"


def test_api_format_endpoint(client: TestClient) -> None:
    _seed_api(client)
    number = client.get(
        "/api/i18n/format",
        params={"locale": "en", "kind": "number", "value": "1234.5", "pattern": "#,##0.00"},
    )
    assert number.status_code == 200
    assert number.json()["output"] == "1,234.50"
    date = client.get(
        "/api/i18n/format",
        params={"locale": "en", "kind": "date", "value": "2026-11-20", "pattern": "DD/MM/YYYY"},
    ).json()
    assert date["output"] == "20/11/2026"
    assert (
        client.get(
            "/api/i18n/format", params={"locale": "en", "kind": "number", "value": "abc"}
        ).status_code
        == 422
    )


def test_api_completeness_and_missing_keys(client: TestClient) -> None:
    _seed_api(client)
    stats = client.get("/api/i18n/completeness").json()
    assert len(stats) == 3
    assert stats[0]["locale"] == "ar"
    assert stats[0]["percent"] == 0.0
    keys = client.get("/api/i18n/missing-keys", params={"locale": "ar"}).json()
    assert {item["key"] for item in keys} == {
        "greeting",
        "items.one",
        "items.other",
        "farewell",
    }
    assert all(item["resolved_locale"] == "en" for item in keys)


def test_api_direction_parse_and_catalog(client: TestClient) -> None:
    _seed_api(client)
    direction = client.get("/api/i18n/direction", params={"locale": "ar-EG"}).json()
    assert direction["is_rtl"] is True
    assert direction["direction"] == "rtl"
    parsed = client.get("/api/i18n/parse", params={"locale": "zh-Hant-TW"}).json()
    assert parsed["canonical"] == "zh-Hant-TW"
    assert parsed["script"] == "hant"
    catalog = client.get("/api/i18n/catalog").json()
    assert catalog["locale_count"] == 3
    assert catalog["namespaces"] == ["ui"]
    assert catalog["rtl_codes"] == ["ar"]


def test_api_format_rules(client: TestClient) -> None:
    assert client.get("/api/i18n/format-rules").json() == []
    _seed_api(client)
    created = client.put(
        "/api/i18n/format-rules",
        json={"locale": "en", "number_pattern": "#,##0", "date_pattern": "DD/MM/YYYY"},
    )
    assert created.status_code == 200
    assert created.json()["number_example"] == "1,234,568"
    assert client.get("/api/i18n/format-rules").json()[0]["date_example"] == "20/11/2026"
    invalid = client.put(
        "/api/i18n/format-rules",
        json={"locale": "en", "number_pattern": "bad", "date_pattern": "YYYY"},
    )
    assert invalid.status_code == 422


def test_api_error_paths(client: TestClient) -> None:
    assert client.get("/api/i18n/translate").status_code == 422
    assert (
        client.get(
            "/api/i18n/translate",
            params={"locale": "en", "namespace": "ui", "key": "k", "values": "not-json"},
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/i18n/messages",
            json={"locale": "xx", "namespace": "ui", "messages": {"k": "v"}},
        ).status_code
        == 404
    )
    assert client.post("/api/i18n/locales", json={"code": "!!", "name": "Bad"}).status_code == 422
    assert client.get("/api/i18n/missing-keys", params={"locale": "xx"}).status_code == 404
