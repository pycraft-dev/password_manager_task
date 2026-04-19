"""Генератор паролей с настраиваемым алфавитом."""

from __future__ import annotations

import logging
import secrets
import string

from src.config.constants import (
    GENERATOR_PASSWORD_MAX_LEN,
    GENERATOR_PASSWORD_MIN_LEN,
)

logger = logging.getLogger(__name__)

_LOWERCASE = string.ascii_lowercase
_UPPERCASE = string.ascii_uppercase
_DIGITS = string.digits
_SPECIAL = "!@#$%^&*()-_=+[]{}.,?:;"


def generate_password(
    length: int,
    *,
    use_uppercase: bool = True,
    use_digits: bool = True,
    use_special: bool = True,
) -> str:
    """
    Генерирует криптостойкий пароль заданной длины.

    Raises:
        ValueError: если длина вне допустимого диапазона или алфавит пуст.
    """
    if length < GENERATOR_PASSWORD_MIN_LEN or length > GENERATOR_PASSWORD_MAX_LEN:
        raise ValueError(
            f"Длина должна быть от {GENERATOR_PASSWORD_MIN_LEN} "
            f"до {GENERATOR_PASSWORD_MAX_LEN}",
        )
    alphabet = _LOWERCASE
    if use_uppercase:
        alphabet += _UPPERCASE
    if use_digits:
        alphabet += _DIGITS
    if use_special:
        alphabet += _SPECIAL
    if not alphabet:
        raise ValueError("Нужно включить хотя бы один набор символов")
    for _ in range(500):
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if _is_acceptable(candidate, use_uppercase, use_digits, use_special):
            logger.debug("Сгенерирован пароль длины %s", length)
            return candidate
    raise ValueError("Не удалось подобрать пароль с заданными опциями")


def _is_acceptable(
    pwd: str,
    use_upper: bool,
    use_digits: bool,
    use_special: bool,
) -> bool:
    """Гарантирует наличие выбранных классов символов."""
    if use_upper and not any(c in _UPPERCASE for c in pwd):
        return False
    if use_digits and not any(c in _DIGITS for c in pwd):
        return False
    if use_special and not any(c in _SPECIAL for c in pwd):
        return False
    return True
