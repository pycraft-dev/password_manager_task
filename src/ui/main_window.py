"""Главный экран: список, поиск, CRUD, экспорт/импорт."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable

import customtkinter as ctk

from src.config.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_TEXT,
    CORNER_RADIUS,
)
from src.config.settings import Settings
from src.core.database import EntryRecord, PasswordDatabase
from src.core.export_import import export_encrypted_file, import_encrypted_file
from src.ui.components import enable_clipboard, make_scrollable
from src.ui.record_form import RecordForm
from src.utils.i18n import Translator

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTkFrame):
    """Основной интерфейс после входа."""

    def __init__(
        self,
        master: Any,
        db: PasswordDatabase,
        settings: Settings,
        translator: Translator,
        master_password: str,
        on_lock: Callable[[], None],
        on_language_change: Callable[[], None],
        **kwargs: object,
    ) -> None:
        super().__init__(master, fg_color=COLOR_BG, **kwargs)
        self._db = db
        self._settings = settings
        self._tr = translator
        self._master_password = master_password
        self._on_lock = on_lock
        self._on_language_change = on_language_change

        self._selected_id: int | None = None
        self._last_sync: datetime | None = None
        self._search_var = ctk.StringVar(value="")
        self._list_buttons: dict[int, ctk.CTkButton] = {}

        self._scroll = make_scrollable(self)

        top = ctk.CTkFrame(self._scroll, fg_color="transparent")
        top.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            top,
            text=self._tr.t("lang_ru"),
            width=40,
            command=lambda: self._set_lang("ru"),
            fg_color=COLOR_ACCENT,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            top,
            text=self._tr.t("lang_en"),
            width=40,
            command=lambda: self._set_lang("en"),
            fg_color=COLOR_ACCENT,
        ).pack(side="left", padx=(0, 12))
        self._btn_lock = ctk.CTkButton(
            top,
            text=self._tr.t("lock"),
            command=self._on_lock,
            fg_color="#374151",
        )
        self._btn_lock.pack(side="right")

        self._heading = ctk.CTkLabel(
            self._scroll,
            text=self._tr.t("main_title"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXT,
        )
        self._heading.pack(anchor="w", pady=(0, 8))

        toolbar = ctk.CTkFrame(self._scroll, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 8))
        self._btn_add = ctk.CTkButton(
            toolbar,
            text=self._tr.t("btn_add"),
            command=self._add,
            fg_color=COLOR_ACCENT,
            width=100,
        )
        self._btn_add.pack(side="left", padx=(0, 6))
        self._btn_edit = ctk.CTkButton(
            toolbar,
            text=self._tr.t("btn_edit"),
            command=self._edit,
            fg_color=COLOR_ACCENT,
            width=100,
        )
        self._btn_edit.pack(side="left", padx=(0, 6))
        self._btn_delete = ctk.CTkButton(
            toolbar,
            text=self._tr.t("btn_delete"),
            command=self._delete_clicked,
            fg_color=COLOR_ACCENT,
            width=100,
        )
        self._btn_delete.pack(side="left", padx=(0, 6))
        self._search_entry = ctk.CTkEntry(
            toolbar,
            textvariable=self._search_var,
            placeholder_text=self._tr.t("search_placeholder"),
            width=160,
            fg_color="#2a2a2a",
            text_color=COLOR_TEXT,
        )
        self._search_entry.pack(side="left", padx=(0, 6))
        enable_clipboard(self._search_entry)
        self._btn_search = ctk.CTkButton(
            toolbar,
            text=self._tr.t("btn_search"),
            command=self._search,
            fg_color=COLOR_ACCENT,
            width=90,
        )
        self._btn_search.pack(side="left", padx=(0, 6))
        self._btn_export = ctk.CTkButton(
            toolbar,
            text=self._tr.t("btn_export"),
            command=self._export,
            fg_color=COLOR_ACCENT,
            width=100,
        )
        self._btn_export.pack(side="left", padx=(0, 6))
        self._btn_import = ctk.CTkButton(
            toolbar,
            text=self._tr.t("btn_import"),
            command=self._import,
            fg_color=COLOR_ACCENT,
            width=100,
        )
        self._btn_import.pack(side="left")

        self._body = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._body.pack(fill="both", expand=True)

        self._confirm_frame = ctk.CTkFrame(
            self._body,
            fg_color="#252525",
            corner_radius=CORNER_RADIUS,
        )
        row_del = ctk.CTkFrame(self._confirm_frame, fg_color="transparent")
        row_del.pack(fill="x", padx=8, pady=8)
        self._confirm_label = ctk.CTkLabel(row_del, text="", text_color=COLOR_TEXT)
        self._confirm_label.pack(side="left", expand=True, fill="x")
        self._confirm_no = ctk.CTkButton(
            row_del,
            text=self._tr.t("no"),
            fg_color="#374151",
            width=80,
            command=self._hide_confirm,
        )
        self._confirm_no.pack(side="right", padx=(4, 0))
        self._confirm_yes = ctk.CTkButton(
            row_del,
            text=self._tr.t("yes"),
            fg_color=COLOR_ERROR,
            width=80,
            command=self._delete_confirmed,
        )
        self._confirm_yes.pack(side="right")

        self._list_frame = ctk.CTkFrame(self._body, fg_color="transparent")
        self._list_frame.pack(fill="both", expand=True)

        self._form_frame = ctk.CTkFrame(self._body, fg_color="transparent")

        bottom = ctk.CTkFrame(self, fg_color="#111111", corner_radius=0)
        row_stat = ctk.CTkFrame(bottom, fg_color="transparent")
        row_stat.pack(fill="x", padx=10, pady=(6, 0))
        self._status_left = ctk.CTkLabel(row_stat, text="", text_color=COLOR_TEXT, anchor="w")
        self._status_left.pack(side="left", fill="x", expand=True)
        self._status_right = ctk.CTkLabel(row_stat, text="", text_color=COLOR_TEXT, anchor="e")
        self._status_right.pack(side="right")
        self._copy_small = ctk.CTkLabel(
            bottom,
            text=self._tr.t("copyright"),
            text_color="#6b7280",
            font=ctk.CTkFont(size=10),
        )
        self._copy_small.pack(fill="x", padx=10, pady=(0, 6))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))
        bottom.grid(row=1, column=0, sticky="ew")

        self._reload_list()
        self._update_status_bar()
        self._confirm_frame.pack_forget()

    def _set_lang(self, lang: str) -> None:
        self._tr.set_lang(lang)
        self._on_language_change()
        self.refresh_language()

    def _reset_scroll_to_top(self) -> None:
        """Возвращает прокрутку основной области к началу (список после длинной формы)."""

        def _do() -> None:
            self.update_idletasks()
            canvas = getattr(self._scroll, "_parent_canvas", None)
            if canvas is not None and hasattr(canvas, "yview_moveto"):
                canvas.yview_moveto(0)

        self.after_idle(_do)

    def refresh_language(self) -> None:
        """Обновляет подписи после смены языка."""
        self._heading.configure(text=self._tr.t("main_title"))
        self._btn_lock.configure(text=self._tr.t("lock"))
        self._btn_add.configure(text=self._tr.t("btn_add"))
        self._btn_edit.configure(text=self._tr.t("btn_edit"))
        self._btn_delete.configure(text=self._tr.t("btn_delete"))
        self._btn_search.configure(text=self._tr.t("btn_search"))
        self._btn_export.configure(text=self._tr.t("btn_export"))
        self._btn_import.configure(text=self._tr.t("btn_import"))
        self._search_entry.configure(placeholder_text=self._tr.t("search_placeholder"))
        self._confirm_label.configure(text=self._tr.t("confirm_delete"))
        self._confirm_yes.configure(text=self._tr.t("yes"))
        self._confirm_no.configure(text=self._tr.t("no"))
        self._copy_small.configure(text=self._tr.t("copyright"))
        self._update_status_bar()

    def _touch_sync(self) -> None:
        self._last_sync = datetime.now()
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        n = self._db.count_entries()
        left = f"{self._tr.t('records')}: {n}"
        if self._last_sync:
            right = f"{self._tr.t('last_sync')}: {self._last_sync.strftime('%Y-%m-%d %H:%M')}"
        else:
            right = f"{self._tr.t('last_sync')}: {self._tr.t('never_sync')}"
        self._status_left.configure(text=left)
        self._status_right.configure(text=right)

    def set_status_message(self, message: str, *, ok: bool = True) -> None:
        """Краткое сообщение в статусной строке."""
        color = COLOR_SUCCESS if ok else COLOR_ERROR
        self._status_left.configure(text_color=color)
        self._status_left.configure(text=message)
        self.after(2500, lambda: self._reset_status_colors())

    def _reset_status_colors(self) -> None:
        self._status_left.configure(text_color=COLOR_TEXT)
        self._update_status_bar()

    def _reload_list(self, query: str | None = None) -> None:
        for w in self._list_frame.winfo_children():
            w.destroy()
        self._list_buttons.clear()
        records = self._db.list_entries(query)
        for rec in records:
            btn = ctk.CTkButton(
                self._list_frame,
                text=rec.title,
                anchor="w",
                fg_color="#2a2a2a",
                hover_color="#333333",
                command=lambda rid=rec.id: self._select(rid),
            )
            btn.pack(fill="x", pady=3)
            if rec.id is not None:
                self._list_buttons[rec.id] = btn
        if self._selected_id is not None and self._selected_id not in self._list_buttons:
            self._selected_id = None
        self._highlight_selection()

    def _highlight_selection(self) -> None:
        for rid, btn in self._list_buttons.items():
            if rid == self._selected_id:
                btn.configure(fg_color=COLOR_ACCENT)
            else:
                btn.configure(fg_color="#2a2a2a")

    def _select(self, entry_id: int) -> None:
        self._selected_id = entry_id
        self._highlight_selection()

    def _search(self) -> None:
        q = self._search_var.get().strip()
        self._reload_list(q if q else None)

    def _add(self) -> None:
        self._hide_confirm()
        self._list_frame.pack_forget()
        self._confirm_frame.pack_forget()
        self._form_frame.pack(fill="both", expand=True)
        for w in self._form_frame.winfo_children():
            w.destroy()
        form = RecordForm(
            self._form_frame,
            self._tr,
            on_save=self._on_save_new,
            on_cancel=self._cancel_form,
        )
        form.pack(fill="both", expand=True)

    def _edit(self) -> None:
        self._hide_confirm()
        if self._selected_id is None:
            self.set_status_message(self._tr.t("select_entry"), ok=False)
            return
        rec = self._db.get_entry(self._selected_id)
        if rec is None:
            self.set_status_message(self._tr.t("select_entry"), ok=False)
            return
        self._list_frame.pack_forget()
        self._confirm_frame.pack_forget()
        self._form_frame.pack(fill="both", expand=True)
        for w in self._form_frame.winfo_children():
            w.destroy()
        form = RecordForm(
            self._form_frame,
            self._tr,
            on_save=self._on_save_edit,
            on_cancel=self._cancel_form,
            existing=rec,
        )
        form.pack(fill="both", expand=True)

    def _delete_clicked(self) -> None:
        if self._selected_id is None:
            self.set_status_message(self._tr.t("select_entry"), ok=False)
            return
        if self._form_frame.winfo_children():
            self._cancel_form()
        self._confirm_label.configure(text=self._tr.t("confirm_delete"))
        self._list_frame.pack_forget()
        self._form_frame.pack_forget()
        self._confirm_frame.pack(fill="x", pady=(0, 8))
        self._list_frame.pack(fill="both", expand=True)

    def _hide_confirm(self) -> None:
        self._confirm_frame.pack_forget()
        self._list_frame.pack(fill="both", expand=True)
        self._reset_scroll_to_top()

    def _delete_confirmed(self) -> None:
        if self._selected_id is not None:
            self._db.delete_entry(self._selected_id)
            logger.info("Удалена запись id=%s", self._selected_id)
            self._selected_id = None
            self._touch_sync()
            self.set_status_message(self._tr.t("deleted"), ok=True)
        self._confirm_frame.pack_forget()
        self._list_frame.pack(fill="both", expand=True)
        self._reload_list(self._search_var.get().strip() or None)
        self._reset_scroll_to_top()

    def _cancel_form(self) -> None:
        for w in self._form_frame.winfo_children():
            w.destroy()
        self._form_frame.pack_forget()
        self._confirm_frame.pack_forget()
        self._list_frame.pack(fill="both", expand=True)
        self._reset_scroll_to_top()

    def _on_save_new(self, data: dict[str, str]) -> None:
        if self._db.title_exists(data["title"]):
            self.set_status_message(self._tr.t("dup_title"), ok=False)
            return
        self._db.add_entry(
            title=data["title"],
            login=data["login"],
            password=data["password"],
            notes=data["notes"],
            attachment_path=data["attachment_path"],
        )
        self._touch_sync()
        self.set_status_message(self._tr.t("saved"), ok=True)
        self._search_var.set("")
        self._cancel_form()
        self._reload_list(None)
        self._reset_scroll_to_top()

    def _on_save_edit(self, data: dict[str, str]) -> None:
        eid = int(data["id"])
        if self._db.title_exists(data["title"], exclude_id=eid):
            self.set_status_message(self._tr.t("dup_title"), ok=False)
            return
        self._db.update_entry(
            entry_id=eid,
            title=data["title"],
            login=data["login"],
            password=data["password"],
            notes=data["notes"],
            attachment_path=data["attachment_path"],
        )
        self._touch_sync()
        self.set_status_message(self._tr.t("saved"), ok=True)
        self._search_var.set("")
        self._cancel_form()
        self._reload_list(None)
        self._reset_scroll_to_top()

    def _export(self) -> None:
        path_str = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            export_encrypted_file(
                path,
                self._master_password,
                self._settings.pbkdf2_iterations,
                self._db.export_plain_records(),
            )
            self._touch_sync()
            self.set_status_message(self._tr.t("export_ok"), ok=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Экспорт: %s", exc)
            self.set_status_message(str(exc), ok=False)

    def _import(self) -> None:
        path_str = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            records = import_encrypted_file(path, self._master_password)
            imp, skip = self._db.import_records_skip_duplicate_titles(records)
            self._touch_sync()
            msg = self._tr.t("import_ok").format(n=imp, s=skip)
            self.set_status_message(msg, ok=True)
            self._reload_list(self._search_var.get().strip() or None)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Импорт: %s", exc)
            self.set_status_message(self._tr.t("import_fail") + f" {exc}", ok=False)
