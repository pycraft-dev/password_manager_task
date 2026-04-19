"""Тесты SQLite-слоя."""

from __future__ import annotations

from pathlib import Path

from src.core.database import PasswordDatabase


def test_create_add_list(tmp_path: Path) -> None:
    dbp = tmp_path / "e.db"
    db, created = PasswordDatabase.open_or_create(dbp, "longpassword1", 50_000)
    assert created is True
    try:
        rid = db.add_entry("GitHub", "u", "p", "notes", "")
        assert rid > 0
        rows = db.list_entries()
        assert len(rows) == 1
        assert rows[0].title == "GitHub"
    finally:
        db.close()


def test_wrong_password(tmp_path: Path) -> None:
    dbp = tmp_path / "e2.db"
    db, _ = PasswordDatabase.open_or_create(dbp, "correcthorse", 50_000)
    db.close()
    try:
        PasswordDatabase.open_or_create(dbp, "wrongpassword", 50_000)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
