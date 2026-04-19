"""Тесты экспорта и импорта."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.export_import import export_encrypted_file, import_encrypted_file


def test_export_import_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "vault.json"
    entries = [
        {
            "title": "Сайт",
            "login": "user",
            "password": "pw",
            "notes": "n",
            "attachment_path": "",
            "created_at": "",
            "updated_at": "",
        }
    ]
    export_encrypted_file(path, "master-pass", 100_000, entries)
    loaded = import_encrypted_file(path, "master-pass")
    assert len(loaded) == 1
    assert loaded[0]["title"] == "Сайт"
    assert loaded[0]["password"] == "pw"


def test_import_wrong_password(tmp_path: Path) -> None:
    path = tmp_path / "x.json"
    export_encrypted_file(
        path,
        "ok",
        100_000,
        [
            {
                "title": "t",
                "login": "",
                "password": "",
                "notes": "",
                "attachment_path": "",
                "created_at": "",
                "updated_at": "",
            },
        ],
    )
    with pytest.raises(ValueError):
        import_encrypted_file(path, "bad")
