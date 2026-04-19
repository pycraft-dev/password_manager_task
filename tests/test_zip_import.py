"""Тесты извлечения CSV из ZIP (в т.ч. с паролем)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pyzipper
import pytest

from src.utils.csv_parser import BrowserKind, parse_browser_csv_text, parse_browser_zip
from src.utils.zip_csv_loader import extract_first_csv_text_from_zip

_CHROME_CSV = (
    "name,url,username,password\n"
    "Site,https://example.com/,u1,p1\n"
)


def test_extract_plain_zip_stdlib(tmp_path: Path) -> None:
    zp = tmp_path / "plain.zip"
    with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("export.csv", _CHROME_CSV)
    text = extract_first_csv_text_from_zip(zp, "")
    assert "example.com" in text
    rows = parse_browser_csv_text(text, BrowserKind.CHROME)
    assert len(rows) == 1


def test_extract_password_zip_pyzipper(tmp_path: Path) -> None:
    zp = tmp_path / "enc.zip"
    with pyzipper.AESZipFile(
        zp,
        "w",
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as zf:
        zf.setpassword(b"secret123")
        zf.writestr("passwords.csv", _CHROME_CSV)
    text = extract_first_csv_text_from_zip(zp, "secret123")
    rows = parse_browser_csv_text(text, BrowserKind.CHROME)
    assert len(rows) == 1
    with pytest.raises(ValueError, match="zip_bad_password"):
        extract_first_csv_text_from_zip(zp, "wrong")


def test_parse_browser_zip_integration(tmp_path: Path) -> None:
    zp = tmp_path / "p.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("nested/password_export.csv", _CHROME_CSV)
    rows = parse_browser_zip(zp, "", BrowserKind.CHROME)
    assert len(rows) == 1


def test_zip_no_csv_raises(tmp_path: Path) -> None:
    zp = tmp_path / "empty.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("readme.txt", "no csv")
    with pytest.raises(ValueError, match="zip_no_csv"):
        extract_first_csv_text_from_zip(zp, "")
