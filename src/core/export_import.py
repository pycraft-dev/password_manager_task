"""Экспорт и импорт зашифрованного JSON."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

from src.config.constants import EXPORT_FORMAT_VERSION
from src.core.encryption import derive_key_from_password, open_sealed, seal

logger = logging.getLogger(__name__)


def export_encrypted_file(
    path: Path,
    master_password: str,
    iterations: int,
    entries: list[dict[str, Any]],
) -> None:
    """
    Сохраняет записи в файл, зашифрованный AES-GCM с ключом от мастер-пароля и соли файла.
    """
    import os

    salt = os.urandom(16)
    key = derive_key_from_password(master_password, salt, iterations)
    inner = json.dumps(
        {"version": EXPORT_FORMAT_VERSION, "entries": entries},
        ensure_ascii=False,
    ).encode("utf-8")
    blob = seal(inner, key)
    payload = {
        "format": "password_manager_encrypted_v1",
        "version": EXPORT_FORMAT_VERSION,
        "salt_b64": base64.b64encode(salt).decode("ascii"),
        "iterations": iterations,
        "ciphertext_b64": base64.b64encode(blob).decode("ascii"),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Экспорт выполнен: %s", path)


def import_encrypted_file(path: Path, master_password: str) -> list[dict[str, Any]]:
    """
    Читает и расшифровывает экспорт. Возвращает список записей.

    Raises:
        ValueError: при неверном пароле или неверной структуре файла.
    """
    raw_text = path.read_text(encoding="utf-8")
    try:
        outer = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Файл не является корректным JSON") from exc
    _validate_outer(outer)
    salt = base64.b64decode(outer["salt_b64"])
    iterations = int(outer["iterations"])
    blob = base64.b64decode(outer["ciphertext_b64"])
    key = derive_key_from_password(master_password, salt, iterations)
    try:
        inner_bytes = open_sealed(blob, key)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Не удалось расшифровать (неверный пароль или файл повреждён)") from exc
    try:
        inner = json.loads(inner_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Внутреннее содержимое повреждено") from exc
    return _validate_entries(inner)


def _validate_outer(data: dict[str, Any]) -> None:
    if data.get("format") != "password_manager_encrypted_v1":
        raise ValueError("Неизвестный формат экспорта")
    if "salt_b64" not in data or "ciphertext_b64" not in data or "iterations" not in data:
        raise ValueError("Неполный заголовок экспорта")


def _validate_entries(inner: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(inner, dict):
        raise ValueError("Ожидался объект с полем entries")
    if int(inner.get("version", 0)) != EXPORT_FORMAT_VERSION:
        raise ValueError("Неподдерживаемая версия содержимого")
    entries = inner.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Поле entries должно быть массивом")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(entries):
        if not isinstance(item, dict):
            raise ValueError(f"Запись #{i} не является объектом")
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"Запись #{i}: некорректное поле title")
        out.append(
            {
                "title": str(item.get("title", "")),
                "login": str(item.get("login", "")),
                "password": str(item.get("password", "")),
                "notes": str(item.get("notes", "")),
                "attachment_path": str(item.get("attachment_path", "")),
                "created_at": str(item.get("created_at", "")),
                "updated_at": str(item.get("updated_at", "")),
            }
        )
    return out
