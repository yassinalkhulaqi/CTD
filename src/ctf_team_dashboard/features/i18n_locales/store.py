"""Persistence for locales, messages and formatting rules."""

from __future__ import annotations

import sqlite3

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.features.i18n_locales.models import (
    DEFAULT_DATE_PATTERN,
    DEFAULT_NUMBER_PATTERN,
    FormatRule,
    Locale,
    Message,
    PluralRule,
    TextDirection,
)
from ctf_team_dashboard.repositories.base import BaseRepository, format_datetime, parse_datetime


def message_id(locale: str, namespace: str, key: str) -> str:
    """Build the deterministic primary key of a catalogue message."""
    return f"{locale.lower()}:{namespace}:{key}"


class LocaleRepository(BaseRepository):
    """Read and write registered locales."""

    table = "v3_locales"

    def all(self) -> list[Locale]:
        """Return every locale ordered by code."""
        rows = self.fetch_all(
            "SELECT code, name, direction, plural_rules, created_at FROM v3_locales ORDER BY code"
        )
        return [self._map(row) for row in rows]

    def find(self, code: str) -> Locale | None:
        """Return the locale with the given code, if it exists."""
        row = self.fetch_one(
            "SELECT code, name, direction, plural_rules, created_at FROM v3_locales WHERE code = ?",
            (code,),
        )
        return self._map(row) if row is not None else None

    def insert(self, locale: Locale) -> Locale:
        """Insert a locale row and return the stored entity."""
        self.execute(
            "INSERT INTO v3_locales (code, name, direction, plural_rules, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                locale.code,
                locale.name,
                locale.direction.value,
                locale.plural_rules.value,
                format_datetime(locale.created_at),
            ),
        )
        return locale

    def codes(self) -> set[str]:
        """Return all registered locale codes."""
        rows = self.fetch_all("SELECT code FROM v3_locales")
        return {str(row["code"]) for row in rows}

    @staticmethod
    def _map(row: sqlite3.Row) -> Locale:
        """Map a result row onto a locale entity."""
        record = dict(row)
        created = parse_datetime(record.get("created_at")) or utcnow()
        return Locale(
            code=str(record["code"]),
            name=str(record["name"]),
            direction=TextDirection(str(record["direction"])),
            plural_rules=PluralRule(str(record["plural_rules"])),
            created_at=created,
        )


class MessageRepository(BaseRepository):
    """Read and write catalogue messages."""

    table = "v3_messages"

    def all(self, locale: str | None = None, namespace: str | None = None) -> list[Message]:
        """Return messages, optionally filtered by locale and namespace."""
        clauses: list[str] = []
        params: list[object] = []
        if locale is not None:
            clauses.append("locale = ?")
            params.append(locale)
        if namespace is not None:
            clauses.append("namespace = ?")
            params.append(namespace)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.fetch_all(
            "SELECT id, locale, namespace, key, value, updated_at "
            f"FROM v3_messages{where} ORDER BY locale, namespace, key",
            tuple(params),
        )
        return [self._map(row) for row in rows]

    def find(self, locale: str, namespace: str, key: str) -> Message | None:
        """Return one message by its natural key."""
        row = self.fetch_one(
            "SELECT id, locale, namespace, key, value, updated_at "
            "FROM v3_messages WHERE locale = ? AND namespace = ? AND key = ?",
            (locale, namespace, key),
        )
        return self._map(row) if row is not None else None

    def upsert(self, message: Message) -> Message:
        """Insert or update a message value."""
        stored = message.with_value(message.value)
        self.execute(
            "INSERT INTO v3_messages (id, locale, namespace, key, value, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(locale, namespace, key) DO UPDATE SET "
            "value = excluded.value, updated_at = excluded.updated_at",
            (
                message.id,
                message.locale,
                message.namespace,
                message.key,
                message.value,
                format_datetime(stored.updated_at),
            ),
        )
        return stored

    def upsert_many(self, messages: list[Message]) -> list[Message]:
        """Upsert several messages in one transaction."""
        return [self.upsert(message) for message in messages]

    def keys_for(self, locale: str, namespace: str) -> set[str]:
        """Return the stored keys of one locale and namespace."""
        rows = self.fetch_all(
            "SELECT key FROM v3_messages WHERE locale = ? AND namespace = ?",
            (locale, namespace),
        )
        return {str(row["key"]) for row in rows}

    def namespaces_for(self, locale: str) -> set[str]:
        """Return the namespaces used by a locale."""
        rows = self.fetch_all(
            "SELECT DISTINCT namespace FROM v3_messages WHERE locale = ?",
            (locale,),
        )
        return {str(row["namespace"]) for row in rows}

    def delete(self, locale: str, namespace: str, key: str) -> bool:
        """Delete one message and report whether it existed."""
        affected = self.execute(
            "DELETE FROM v3_messages WHERE locale = ? AND namespace = ? AND key = ?",
            (locale, namespace, key),
        )
        return affected > 0

    @staticmethod
    def _map(row: sqlite3.Row) -> Message:
        """Map a result row onto a message entity."""
        record = dict(row)
        updated = parse_datetime(record.get("updated_at")) or utcnow()
        return Message(
            id=str(record["id"]),
            locale=str(record["locale"]),
            namespace=str(record["namespace"]),
            key=str(record["key"]),
            value=str(record["value"]),
            updated_at=updated,
        )


class FormatRuleRepository(BaseRepository):
    """Read and write locale formatting rules."""

    table = "v3_format_rules"

    def all(self) -> list[FormatRule]:
        """Return every stored format rule."""
        rows = self.fetch_all(
            "SELECT locale, number_pattern, date_pattern, updated_at "
            "FROM v3_format_rules ORDER BY locale"
        )
        return [self._map(row) for row in rows]

    def find(self, locale: str) -> FormatRule | None:
        """Return the rule of a locale, if one was stored."""
        row = self.fetch_one(
            "SELECT locale, number_pattern, date_pattern, updated_at "
            "FROM v3_format_rules WHERE locale = ?",
            (locale,),
        )
        return self._map(row) if row is not None else None

    def upsert(self, rule: FormatRule) -> FormatRule:
        """Insert or update a formatting rule."""
        stored = FormatRule(
            locale=rule.locale,
            number_pattern=rule.number_pattern,
            date_pattern=rule.date_pattern,
            updated_at=utcnow(),
        )
        self.execute(
            "INSERT INTO v3_format_rules (locale, number_pattern, date_pattern, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(locale) DO UPDATE SET "
            "number_pattern = excluded.number_pattern, "
            "date_pattern = excluded.date_pattern, "
            "updated_at = excluded.updated_at",
            (
                stored.locale,
                stored.number_pattern,
                stored.date_pattern,
                format_datetime(stored.updated_at),
            ),
        )
        return stored

    @staticmethod
    def _map(row: sqlite3.Row) -> FormatRule:
        """Map a result row onto a formatting rule."""
        record = dict(row)
        updated = parse_datetime(record.get("updated_at")) or utcnow()
        return FormatRule(
            locale=str(record["locale"]),
            number_pattern=str(record["number_pattern"] or DEFAULT_NUMBER_PATTERN),
            date_pattern=str(record["date_pattern"] or DEFAULT_DATE_PATTERN),
            updated_at=updated,
        )


class I18nStore:
    """Facade exposing the three repositories used by the service layer."""

    def __init__(self) -> None:
        self.locales = LocaleRepository()
        self.messages = MessageRepository()
        self.format_rules = FormatRuleRepository()
