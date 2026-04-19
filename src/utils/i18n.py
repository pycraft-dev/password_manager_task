"""Простая локализация RU/EN из translations.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Translator:
    """Доступ к строкам по ключу и текущему языку."""

    def __init__(self, data: dict[str, dict[str, str]], lang: str = "ru") -> None:
        self._data = data
        self.lang = lang

    def t(self, key: str) -> str:
        """Возвращает строку для ключа или ключ при отсутствии перевода."""
        block = self._data.get(key)
        if not isinstance(block, dict):
            return key
        return str(block.get(self.lang) or block.get("ru") or key)

    def set_lang(self, lang: str) -> None:
        """Переключает язык (ru/en)."""
        self.lang = lang if lang in ("ru", "en") else "ru"


def load_translations(path: Path) -> Translator:
    """Загружает файл переводов. При ошибке возвращает пустой набор."""
    try:
        raw = path.read_text(encoding="utf-8")
        data: dict[str, Any] = json.loads(raw)
        flat: dict[str, dict[str, str]] = {}
        for k, v in data.items():
            if isinstance(v, dict):
                flat[k] = {str(a): str(b) for a, b in v.items()}
        return Translator(flat)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Не удалось загрузить переводы %s: %s", path, exc)
        return Translator({})
