"""Версия приложения из файла VERSION (рядом с проектом или в bundle EXE)."""

from __future__ import annotations

from pathlib import Path

from src.utils.assets import get_bundle_root, get_project_root


def read_app_version() -> str:
    """Возвращает номер версии из VERSION (первая непустая строка)."""
    for base in (get_bundle_root(), get_project_root()):
        path = base / "VERSION"
        if path.is_file():
            line = path.read_text(encoding="utf-8").strip().splitlines()
            if line:
                return line[0].strip()
    return "0.0.0"
