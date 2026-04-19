"""Форма создания/редактирования записи и генератор пароля."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from src.config.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_ERROR,
    COLOR_TEXT,
    CORNER_RADIUS,
    GENERATOR_PASSWORD_MAX_LEN,
    GENERATOR_PASSWORD_MIN_LEN,
)
from src.core.database import EntryRecord
from src.core.password_gen import generate_password
from src.ui.components import BrowsePathRow, PasswordField, enable_clipboard
from src.utils.i18n import Translator

logger = logging.getLogger(__name__)


class RecordForm(ctk.CTkFrame):
    """Форма записи с генератором."""

    def __init__(
        self,
        master: ctk.CTkFrame,
        translator: Translator,
        on_save: Callable[[dict[str, str]], None],
        on_cancel: Callable[[], None],
        existing: EntryRecord | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(master, fg_color=COLOR_BG, **kwargs)
        self._tr = translator
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._existing_id = existing.id if existing else None

        pad = {"padx": 0, "pady": 6}

        self._title_e = ctk.CTkEntry(self, fg_color="#2a2a2a", text_color=COLOR_TEXT)
        self._pack_labeled(self._tr.t("field_title"), self._title_e, **pad)
        enable_clipboard(self._title_e)

        self._login_e = ctk.CTkEntry(self, fg_color="#2a2a2a", text_color=COLOR_TEXT)
        self._pack_labeled(self._tr.t("field_login"), self._login_e, **pad)
        enable_clipboard(self._login_e)

        self._pwd = PasswordField(self)
        self._pack_labeled(self._tr.t("field_password"), self._pwd, **pad)

        gen = ctk.CTkFrame(self, fg_color="#252525", corner_radius=CORNER_RADIUS)
        gen.pack(fill="x", pady=8)
        ctk.CTkLabel(gen, text=self._tr.t("generator"), text_color=COLOR_TEXT).pack(
            anchor="w",
            padx=8,
            pady=(8, 4),
        )
        opts = ctk.CTkFrame(gen, fg_color="transparent")
        opts.pack(fill="x", padx=8)
        self._len_var = ctk.IntVar(value=16)
        ctk.CTkLabel(opts, text=self._tr.t("length"), text_color=COLOR_TEXT).grid(
            row=0,
            column=0,
            sticky="w",
        )
        self._len_slider = ctk.CTkSlider(
            opts,
            from_=GENERATOR_PASSWORD_MIN_LEN,
            to=GENERATOR_PASSWORD_MAX_LEN,
            number_of_steps=GENERATOR_PASSWORD_MAX_LEN - GENERATOR_PASSWORD_MIN_LEN,
            variable=self._len_var,
        )
        self._len_slider.grid(row=0, column=1, sticky="ew", padx=8)
        opts.grid_columnconfigure(1, weight=1)
        self._upper = ctk.CTkCheckBox(opts, text=self._tr.t("opt_upper"))
        self._upper.grid(row=1, column=0, columnspan=2, sticky="w", pady=2)
        self._upper.select()
        self._digits = ctk.CTkCheckBox(opts, text=self._tr.t("opt_digits"))
        self._digits.grid(row=2, column=0, columnspan=2, sticky="w", pady=2)
        self._digits.select()
        self._special = ctk.CTkCheckBox(opts, text=self._tr.t("opt_special"))
        self._special.grid(row=3, column=0, columnspan=2, sticky="w", pady=2)
        self._special.select()
        row_btns = ctk.CTkFrame(gen, fg_color="transparent")
        row_btns.pack(fill="x", padx=8, pady=(4, 8))
        ctk.CTkButton(
            row_btns,
            text=self._tr.t("btn_generate"),
            command=self._do_generate,
            fg_color=COLOR_ACCENT,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row_btns,
            text=self._tr.t("btn_copy"),
            command=self._do_copy,
            fg_color=COLOR_ACCENT,
        ).pack(side="left")

        self._notes = ctk.CTkTextbox(self, height=120, fg_color="#2a2a2a", text_color=COLOR_TEXT)
        self._pack_labeled(self._tr.t("field_notes"), self._notes, **pad)
        enable_clipboard(self._notes)

        self._browse = BrowsePathRow(self, browse_label=self._tr.t("browse"))
        self._pack_labeled(self._tr.t("field_attachment"), self._browse, **pad)

        self._err = ctk.CTkLabel(self, text="", text_color=COLOR_ERROR)
        self._err.pack(anchor="w", pady=(4, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", pady=12)
        ctk.CTkButton(
            btns,
            text=self._tr.t("save"),
            command=self._save,
            fg_color=COLOR_ACCENT,
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(
            btns,
            text=self._tr.t("cancel"),
            command=self._on_cancel,
            fg_color="#374151",
        ).pack(side="left", expand=True, fill="x")

        if existing:
            self._title_e.insert(0, existing.title)
            self._login_e.insert(0, existing.login)
            self._pwd.set(existing.password)
            self._notes.insert("1.0", existing.notes)
            if existing.attachment_path:
                self._browse.set_path_str(existing.attachment_path)

    def _pack_labeled(self, title: str, widget: Any, **pack_kw: object) -> None:
        ctk.CTkLabel(self, text=title, text_color=COLOR_TEXT).pack(anchor="w")
        widget.pack(fill="x", **pack_kw)

    def _do_generate(self) -> None:
        try:
            pwd = generate_password(
                int(self._len_var.get()),
                use_uppercase=bool(self._upper.get()),
                use_digits=bool(self._digits.get()),
                use_special=bool(self._special.get()),
            )
            self._pwd.set(pwd)
        except ValueError as exc:
            self._err.configure(text=str(exc))
            logger.info("Генератор: %s", exc)

    def _do_copy(self) -> None:
        text = self._pwd.get()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._err.configure(text=self._tr.t("clipboard_ok"))

    def _save(self) -> None:
        title = self._title_e.get().strip()
        if not title:
            self._err.configure(text=self._tr.t("empty_title"))
            return
        data = {
            "title": title,
            "login": self._login_e.get().strip(),
            "password": self._pwd.get(),
            "notes": self._notes.get("1.0", "end").strip(),
            "attachment_path": self._browse.get_path_str(),
            "id": str(self._existing_id) if self._existing_id is not None else "",
        }
        self._on_save(data)

    def refresh_language(self) -> None:
        """Переводит подписи (без смены введённых данных)."""
        # Заголовки пересобирать дорого; достаточно обновить кнопки генератора
        self._err.configure(text="")
