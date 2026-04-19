"""Валидация записей перед импортом из браузера."""

from __future__ import annotations

from typing import Any


def validate_record(record: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Проверяет одну запись для импорта.

    Returns:
        (успех, ключ причины отказа для i18n или None).
    """
    title = str(record.get("title", "")).strip()
    if not title:
        return False, "val_empty_title"
    login = str(record.get("login", "")).strip()
    password = str(record.get("password", ""))
    if not login and not password:
        return False, "val_empty_credentials"
    if len(title) > 500:
        return False, "val_title_too_long"
    return True, None
