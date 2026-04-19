"""Импорт записей из распарсенного CSV в хранилище."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.database import PasswordDatabase
from src.utils.csv_parser import BrowserKind
from src.utils.validator import validate_record

logger = logging.getLogger(__name__)


def parse_browser_csv(file_path: Path, browser_type: BrowserKind) -> list[dict[str, Any]]:
    """
    Парсит CSV экспорта паролей браузера (делегирует :func:`src.utils.csv_parser.parse_browser_csv`).
    """
    from src.utils import csv_parser

    return csv_parser.parse_browser_csv(file_path, browser_type)


def parse_browser_zip(zip_path: Path, zip_password: str, browser_type: BrowserKind) -> list[dict[str, Any]]:
    """Парсит первый CSV из ZIP (делегирует :func:`src.utils.csv_parser.parse_browser_zip`)."""
    from src.utils import csv_parser

    return csv_parser.parse_browser_zip(zip_path, zip_password, browser_type)


@dataclass(frozen=True)
class AnnotatedImportRow:
    """Строка предпросмотра с признаками дубликатов и валидности."""

    index: int
    title: str
    login: str
    password: str
    notes: str
    valid: bool
    validation_reason: str | None
    duplicate_in_db: bool
    duplicate_in_file: bool


def find_duplicates(
    import_data: list[dict[str, Any]],
    existing_titles_lower: set[str],
) -> set[int]:
    """
    Индексы записей (по порядку в import_data), которые дублируют уже существующие названия.
    """
    dup: set[int] = set()
    for i, rec in enumerate(import_data):
        t = str(rec.get("title", "")).strip().lower()
        if t and t in existing_titles_lower:
            dup.add(i)
    return dup


def _file_duplicate_indices(import_data: list[dict[str, Any]]) -> set[int]:
    """Индексы строк, чьё название уже встречалось выше в файле (вторые и далее)."""
    seen: set[str] = set()
    dup_idx: set[int] = set()
    for i, rec in enumerate(import_data):
        t = str(rec.get("title", "")).strip().lower()
        if not t:
            continue
        if t in seen:
            dup_idx.add(i)
        else:
            seen.add(t)
    return dup_idx


def annotate_import_preview(
    import_data: list[dict[str, Any]],
    db: PasswordDatabase,
) -> list[AnnotatedImportRow]:
    """
    Строит предпросмотр: валидация, дубликаты в БД и внутри файла.
    """
    existing = db.existing_titles_lower()
    dup_db = find_duplicates(import_data, existing)
    dup_file = _file_duplicate_indices(import_data)

    out: list[AnnotatedImportRow] = []
    for i, rec in enumerate(import_data):
        ok, reason = validate_record(rec)
        out.append(
            AnnotatedImportRow(
                index=i,
                title=str(rec.get("title", "")).strip(),
                login=str(rec.get("login", "")),
                password=str(rec.get("password", "")),
                notes=str(rec.get("notes", "")),
                valid=ok,
                validation_reason=reason,
                duplicate_in_db=i in dup_db,
                duplicate_in_file=i in dup_file,
            ),
        )
    return out


def import_records(
    db: PasswordDatabase,
    records: Iterable[dict[str, Any]],
    *,
    skip_duplicates: bool = True,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[int, int, int]:
    """
    Импортирует записи в БД (каждая через шифрование как в v1).

    Returns:
        (импортировано, пропущено_дубликат, пропущено_невалидно)
    """
    items = list(records)
    total = len(items)
    imported = 0
    skipped_dup = 0
    skipped_inv = 0
    for n, item in enumerate(items, start=1):
        if should_cancel and should_cancel():
            logger.info("Импорт прерван пользователем на шаге %s/%s", n, total)
            break
        ok, _ = validate_record(item)
        if not ok:
            skipped_inv += 1
            if on_progress:
                on_progress(n, total)
            continue
        title = str(item.get("title", "")).strip()
        if skip_duplicates and db.title_exists(title):
            skipped_dup += 1
            if on_progress:
                on_progress(n, total)
            continue
        db.add_entry(
            title=title,
            login=str(item.get("login", "")),
            password=str(item.get("password", "")),
            notes=str(item.get("notes", "")),
            attachment_path=str(item.get("attachment_path", "")),
        )
        imported += 1
        if on_progress:
            on_progress(n, total)
    logger.info(
        "Импорт CSV завершён: добавлено=%s пропуск_дубль=%s пропуск_ошибка=%s",
        imported,
        skipped_dup,
        skipped_inv,
    )
    return imported, skipped_dup, skipped_inv
