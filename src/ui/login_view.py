"""Экран ввода мастер-пароля."""

from __future__ import annotations

import logging
from collections.abc import Callable

import customtkinter as ctk

from src.config.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_ERROR,
    COLOR_TEXT,
    CORNER_RADIUS,
    MASTER_PASSWORD_MIN_LEN,
)
from src.ui.components import PasswordField, make_scrollable
from src.utils.i18n import Translator

logger = logging.getLogger(__name__)


class LoginView(ctk.CTkFrame):
    """Форма создания/открытия хранилища."""

    def __init__(
        self,
        master: ctk.CTk,
        translator: Translator,
        is_new_vault: bool,
        on_submit: Callable[[str], None],
        on_language_change: Callable[[], None],
        **kwargs: object,
    ) -> None:
        super().__init__(master, fg_color=COLOR_BG, **kwargs)
        self._tr = translator
        self._is_new = is_new_vault
        self._on_submit = on_submit
        self._on_language_change = on_language_change

        scroll = make_scrollable(self)
        scroll.pack(fill="both", expand=True, padx=12, pady=12)

        lang_row = ctk.CTkFrame(scroll, fg_color="transparent")
        lang_row.pack(fill="x", anchor="e", pady=(0, 8))
        ctk.CTkButton(
            lang_row,
            text=self._tr.t("lang_ru"),
            width=40,
            command=lambda: self._set_lang("ru"),
            fg_color=COLOR_ACCENT,
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            lang_row,
            text=self._tr.t("lang_en"),
            width=40,
            command=lambda: self._set_lang("en"),
            fg_color=COLOR_ACCENT,
        ).pack(side="right")

        self._title_lbl = ctk.CTkLabel(
            scroll,
            text=self._tr.t("login_heading"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXT,
        )
        self._title_lbl.pack(anchor="w", pady=(0, 4))

        self._hint = ctk.CTkLabel(
            scroll,
            text="",
            text_color=COLOR_TEXT,
            wraplength=420,
            justify="left",
        )
        self._hint.pack(anchor="w", pady=(0, 8))
        self._refresh_hint()

        self._pwd = PasswordField(scroll)
        self._pwd.pack(fill="x", pady=(0, 12))

        btn_text = (
            self._tr.t("btn_create") if is_new_vault else self._tr.t("btn_unlock")
        )
        self._submit = ctk.CTkButton(
            scroll,
            text=btn_text,
            command=self._handle_submit,
            fg_color=COLOR_ACCENT,
            corner_radius=CORNER_RADIUS,
        )
        self._submit.pack(fill="x", pady=(0, 8))

        self._error = ctk.CTkLabel(scroll, text="", text_color=COLOR_ERROR)
        self._error.pack(anchor="w")

    def _set_lang(self, lang: str) -> None:
        self._tr.set_lang(lang)
        self._on_language_change()
        self.refresh_language()

    def refresh_language(self) -> None:
        """Обновляет тексты после смены языка."""
        self._title_lbl.configure(text=self._tr.t("login_heading"))
        self._refresh_hint()
        self._submit.configure(
            text=self._tr.t("btn_create") if self._is_new else self._tr.t("btn_unlock"),
        )

    def _refresh_hint(self) -> None:
        self._hint.configure(
            text=self._tr.t("login_hint_new")
            if self._is_new
            else self._tr.t("login_hint_open"),
        )

    def _handle_submit(self) -> None:
        self._error.configure(text="")
        pwd = self._pwd.get().strip()
        if len(pwd) < MASTER_PASSWORD_MIN_LEN:
            self._error.configure(text=self._tr.t("err_short"))
            return
        logger.info("Попытка открытия хранилища (новое=%s)", self._is_new)
        self._on_submit(pwd)

    def show_error(self, message: str) -> None:
        """Показывает сообщение об ошибке."""
        self._error.configure(text=message)
