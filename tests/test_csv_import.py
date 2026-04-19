"""Тесты парсера CSV и логики импорта из браузера."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.database import PasswordDatabase
from src.core.importer import annotate_import_preview, import_records
from src.utils.csv_parser import BrowserKind, parse_browser_csv

_ROOT = Path(__file__).resolve().parents[1]
_TEST_DATA = _ROOT / "test_data"


def test_parse_chromium_csv() -> None:
    rows = parse_browser_csv(_TEST_DATA / "chrome_passwords.csv", BrowserKind.CHROME)
    assert len(rows) == 2
    assert rows[0]["title"] == "Example"
    assert rows[0]["login"] == "demo_user"
    assert rows[0]["password"] == "demo_secret_1"
    assert "example.com" in rows[0]["notes"]


def test_parse_yandex_csv() -> None:
    rows = parse_browser_csv(_TEST_DATA / "yandex_passwords.csv", BrowserKind.YANDEX)
    assert len(rows) == 1
    assert rows[0]["title"] == "Яндекс ID"
    assert rows[0]["login"] == "yandex_user"


def test_parse_firefox_csv() -> None:
    rows = parse_browser_csv(_TEST_DATA / "firefox_passwords.csv", BrowserKind.FIREFOX)
    assert len(rows) == 1
    assert rows[0]["login"] == "fx_user"
    assert rows[0]["password"] == "fx_pass_sample"


def test_parse_invalid_csv_raises() -> None:
    with pytest.raises(ValueError):
        parse_browser_csv(_TEST_DATA / "invalid_export.csv", BrowserKind.CHROME)


def test_annotate_marks_db_duplicate(tmp_path: Path) -> None:
    dbp = tmp_path / "v.db"
    db, _ = PasswordDatabase.open_or_create(dbp, "masterpassphrase", 50_000)
    try:
        db.add_entry("Example", "old", "old", "", "")
        incoming = [
            {"title": "example", "login": "u", "password": "p", "notes": "", "attachment_path": ""},
            {"title": "New Site", "login": "u2", "password": "p2", "notes": "", "attachment_path": ""},
        ]
        ann = annotate_import_preview(incoming, db)
        assert ann[0].duplicate_in_db is True
        assert ann[1].duplicate_in_db is False
    finally:
        db.close()


def test_import_records_respects_cancel(tmp_path: Path) -> None:
    dbp = tmp_path / "v2.db"
    db, _ = PasswordDatabase.open_or_create(dbp, "masterpassphrase2", 50_000)
    try:
        rows = [
            {"title": "A", "login": "u", "password": "p", "notes": "", "attachment_path": ""},
            {"title": "B", "login": "u", "password": "p", "notes": "", "attachment_path": ""},
        ]
        state = {"n": 0}

        def should_cancel() -> bool:
            return state["n"] >= 1

        def on_prog(n: int, total: int) -> None:
            state["n"] = max(state["n"], n)

        imp, sd, si = import_records(db, rows, should_cancel=should_cancel, on_progress=on_prog)
        assert imp == 1
        assert db.count_entries() == 1
    finally:
        db.close()
