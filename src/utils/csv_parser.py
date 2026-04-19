"""Парсинг CSV экспорта паролей из браузеров (Chromium-семейство / Firefox)."""

from __future__ import annotations

import csv
import io
import logging
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class BrowserKind(str, Enum):
    """Поддерживаемые браузеры (по формату CSV)."""

    CHROME = "chrome"
    YANDEX = "yandex"
    EDGE = "edge"
    OPERA = "opera"
    FIREFOX = "firefox"


def _norm_header(h: str) -> str:
    return h.strip().strip('"').strip().lower()


def _host_from_url(url: str) -> str:
    """Извлекает хост из URL для заголовка записи."""
    u = (url or "").strip()
    if not u:
        return "Без названия"
    if "://" not in u and "@" not in u:
        u = "https://" + u
    try:
        p = urlparse(u)
        host = p.netloc or p.path.split("/")[0]
        return host or "Без названия"
    except Exception:  # noqa: BLE001
        return "Без названия"


def parse_browser_csv_text(raw: str, browser_type: BrowserKind) -> list[dict[str, Any]]:
    """
    Парсит текст CSV экспорта паролей и возвращает список словарей:
    ``title``, ``login``, ``password``, ``notes``.

    Raises:
        ValueError: при пустом тексте или неподдерживаемом заголовке.
    """
    if not raw.strip():
        raise ValueError("Файл пустой")

    sample = raw[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = "excel"
    reader = csv.DictReader(io.StringIO(raw), dialect=dialect)
    if reader.fieldnames is None:
        raise ValueError("Нет заголовка CSV")

    headers = {_norm_header(h) for h in reader.fieldnames if h}

    is_firefox = browser_type == BrowserKind.FIREFOX
    if is_firefox:
        if not {"username", "password"}.issubset(headers) or "url" not in headers:
            raise ValueError("Ожидался формат Firefox (колонки url, username, password)")
    else:
        if not {"username", "password"}.issubset(headers):
            raise ValueError("Ожидался формат Chromium (нужны username и password)")
        if "url" not in headers and "name" not in headers:
            raise ValueError("Ожидался формат Chromium (нужны url и/или name)")

    out: list[dict[str, Any]] = []
    for i, row in enumerate(reader):
        norm_row = {_norm_header(k): (v or "").strip() for k, v in row.items() if k}
        url = norm_row.get("url", "")
        name = norm_row.get("name", "")
        login = norm_row.get("username", "")
        password = norm_row.get("password", "")

        title = (name or "").strip() or _host_from_url(url)
        notes_parts = []
        if url:
            notes_parts.append(f"URL: {url}")
        if browser_type != BrowserKind.FIREFOX and name and url:
            notes_parts.append(f"Имя в экспорте: {name}")
        notes = "\n".join(notes_parts)

        out.append(
            {
                "row_index": i,
                "title": title,
                "login": login,
                "password": password,
                "notes": notes,
                "attachment_path": "",
            },
        )

    logger.info("Распарсено строк CSV: %s (%s)", len(out), browser_type.value)
    return out


def parse_browser_csv(file_path: Path, browser_type: BrowserKind) -> list[dict[str, Any]]:
    """
    Читает CSV с диска и делегирует :func:`parse_browser_csv_text`.
    """
    raw = file_path.read_text(encoding="utf-8-sig", errors="replace")
    return parse_browser_csv_text(raw, browser_type)


def parse_browser_zip(zip_path: Path, zip_password: str, browser_type: BrowserKind) -> list[dict[str, Any]]:
    """
    Извлекает первый CSV из ZIP (см. :mod:`src.utils.zip_csv_loader`) и парсит его.
    """
    from src.utils.zip_csv_loader import extract_first_csv_text_from_zip

    raw = extract_first_csv_text_from_zip(zip_path, zip_password)
    return parse_browser_csv_text(raw, browser_type)
