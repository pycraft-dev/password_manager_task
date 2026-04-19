"""Переиспользуемые виджеты: скролл, буфер обмена, поле пароля, обзор файла."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import customtkinter as ctk
from tkinter import filedialog

from src.config.constants import COLOR_ACCENT, COLOR_BG, COLOR_TEXT, CORNER_RADIUS
from src.ui.clipboard_bindings import enable_clipboard_bindings as _enable_clipboard_raw

logger = logging.getLogger(__name__)


def enable_clipboard(widget: Any) -> None:
    """Включает горячие клавиши буфера для CTkEntry / CTkTextbox (см. clipboard_bindings)."""
    _enable_clipboard_raw(widget)


def make_scrollable(parent: Any) -> ctk.CTkScrollableFrame:
    """Создаёт основной скролл-контейнер в стиле приложения."""
    return ctk.CTkScrollableFrame(
        master=parent,
        fg_color=COLOR_BG,
        corner_radius=CORNER_RADIUS,
    )


class PasswordField(ctk.CTkFrame):
    """Поле пароля с переключателем видимости."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._show = False
        self.entry = ctk.CTkEntry(self, show="*", fg_color="#2a2a2a", text_color=COLOR_TEXT)
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.toggle_btn = ctk.CTkButton(
            self,
            text="👁",
            width=36,
            command=self._toggle,
            fg_color=COLOR_ACCENT,
        )
        self.toggle_btn.grid(row=0, column=1)
        self.grid_columnconfigure(0, weight=1)
        enable_clipboard(self.entry)

    def _toggle(self) -> None:
        self._show = not self._show
        self.entry.configure(show="" if self._show else "*")
        self.toggle_btn.configure(text="🙈" if self._show else "👁")

    def get(self) -> str:
        """Текущее значение пароля."""
        return self.entry.get()

    def set(self, value: str) -> None:
        """Устанавливает значение."""
        self.entry.delete(0, "end")
        self.entry.insert(0, value)

    def clear(self) -> None:
        """Очищает поле."""
        self.entry.delete(0, "end")


class BrowsePathRow(ctk.CTkFrame):
    """Readonly путь + кнопка Обзор."""

    def __init__(
        self,
        master: Any,
        browse_label: str,
        on_selected: Callable[[Path], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_selected = on_selected
        self.entry = ctk.CTkEntry(self, state="readonly", fg_color="#2a2a2a", text_color=COLOR_TEXT)
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.btn = ctk.CTkButton(
            self,
            text=browse_label,
            width=100,
            command=self._browse,
            fg_color=COLOR_ACCENT,
        )
        self.btn.grid(row=0, column=1)
        self.grid_columnconfigure(0, weight=1)
        enable_clipboard(self.entry)

    def _browse(self) -> None:
        path_str = filedialog.askopenfilename()
        if not path_str:
            return
        path = Path(path_str)
        if not path.is_file():
            logger.warning("Выбран не файл: %s", path)
            return
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.entry.insert(0, str(path))
        self.entry.configure(state="readonly")
        if self._on_selected:
            self._on_selected(path)

    def get_path_str(self) -> str:
        """Возвращает строку пути (может быть пусто)."""
        self.entry.configure(state="normal")
        v = self.entry.get().strip()
        self.entry.configure(state="readonly")
        return v

    def set_path_str(self, value: str) -> None:
        """Устанавливает путь; пусто, если файл не существует."""
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        v = value.strip()
        if v:
            p = Path(v)
            if not p.is_file():
                logger.warning("Путь вложения не найден или не файл: %s", p)
                v = ""
        self.entry.insert(0, v)
        self.entry.configure(state="readonly")
