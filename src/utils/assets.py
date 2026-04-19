"""Пути к ресурсам и корню приложения."""

from __future__ import annotations

import sys
from pathlib import Path


def get_project_root() -> Path:
    """
    Каталог для записи данных: рядом с EXE при сборке или корень репозитория при разработке.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def get_bundle_root() -> Path:
    """
    Каталог встроенных ресурсов (PyInstaller _MEIPASS) или корень проекта.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def get_icon_path() -> Path:
    """Путь к файлу иконки окна (из datas или из папки проекта)."""
    bundled = get_bundle_root() / "assets" / "icon.ico"
    if bundled.exists():
        return bundled
    return get_project_root() / "assets" / "icon.ico"


def get_browser_icon_path(slug: str) -> Path:
    """
    Путь к PNG-иконке браузера (``chrome``, ``yandex``, ``firefox``, ``edge``, ``opera``).
    """
    name = f"{slug}.png"
    bundled = get_bundle_root() / "assets" / "browser_icons" / name
    if bundled.exists():
        return bundled
    return get_project_root() / "assets" / "browser_icons" / name
