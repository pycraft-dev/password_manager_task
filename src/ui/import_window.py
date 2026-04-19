"""Панель импорта паролей из CSV экспорта браузера (внутри главного окна)."""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable

import customtkinter as ctk
from PIL import Image

from src.config.constants import COLOR_ACCENT, COLOR_BG, COLOR_ERROR, COLOR_TEXT, CORNER_RADIUS
from src.core.database import PasswordDatabase
from src.core.importer import AnnotatedImportRow, annotate_import_preview, import_records
from src.ui.components import PasswordField, enable_clipboard
from src.utils.assets import get_browser_icon_path
from src.utils.csv_parser import BrowserKind, parse_browser_csv, parse_browser_zip
from src.utils.i18n import Translator

logger = logging.getLogger(__name__)


class BrowserImportPanel(ctk.CTkFrame):
    """Выбор браузера, CSV, предпросмотр, прогресс и импорт в хранилище."""

    def __init__(
        self,
        master: Any,
        db: PasswordDatabase,
        translator: Translator,
        on_done: Callable[[int, int, int], None],
        on_cancel: Callable[[], None],
        **kwargs: object,
    ) -> None:
        super().__init__(master, fg_color=COLOR_BG, **kwargs)
        self._db = db
        self._tr = translator
        self._on_done = on_done
        self._on_cancel = on_cancel

        self._raw_rows: list[dict[str, Any]] = []
        self._annotated: list[AnnotatedImportRow] = []
        self._check_vars: dict[int, ctk.BooleanVar] = {}
        self._filter_key: str = "all"
        self._filter_key_by_label: dict[str, str] = {}
        self._browser_var = ctk.StringVar(value=BrowserKind.CHROME.value)
        self._show_passwords = ctk.BooleanVar(value=False)
        self._cancel_event = threading.Event()
        self._ui_q: queue.Queue[tuple[Any, ...]] = queue.Queue()
        self._importing = False
        self._icon_refs: list[Any] = []
        self._pending_zip: Path | None = None

        self._build_header()
        self._build_filters_and_table_shell()
        self._build_footer()

    def _build_header(self) -> None:
        self._warn = ctk.CTkTextbox(self, height=72, fg_color="#252525", text_color=COLOR_TEXT, wrap="word")
        self._warn.pack(fill="x", pady=(0, 8))
        self._warn.insert("1.0", self._tr.t("browser_import_warning"))
        self._warn.configure(state="disabled")
        enable_clipboard(self._warn)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(0, 6))
        self._browser_icon_lbl = ctk.CTkLabel(row, text="", width=36)
        self._browser_icon_lbl.pack(side="left", padx=(0, 6))
        opts = [
            BrowserKind.CHROME,
            BrowserKind.YANDEX,
            BrowserKind.EDGE,
            BrowserKind.OPERA,
            BrowserKind.FIREFOX,
        ]
        labels = {b: self._tr.t(f"browser_{b.value}") for b in opts}
        self._browser_labels = labels
        self._browser_menu = ctk.CTkOptionMenu(
            row,
            values=[labels[b] for b in opts],
            command=self._on_browser_label,
            fg_color="#2a2a2a",
            button_color=COLOR_ACCENT,
            button_hover_color="#2563eb",
        )
        self._browser_menu.pack(side="left", fill="x", expand=True)
        self._browser_menu.set(labels[BrowserKind.CHROME])
        self._refresh_browser_icon()

        self._browse_row = ctk.CTkFrame(self, fg_color="transparent")
        self._browse_row.pack(fill="x", pady=(0, 8))
        self._path_e = ctk.CTkEntry(self._browse_row, fg_color="#2a2a2a", text_color=COLOR_TEXT, state="readonly")
        self._path_e.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._browse_row.grid_columnconfigure(0, weight=1)
        self._btn_csv_browse = ctk.CTkButton(
            self._browse_row,
            text=self._tr.t("browse"),
            width=100,
            command=self._pick_csv,
            fg_color=COLOR_ACCENT,
        )
        self._btn_csv_browse.grid(row=0, column=1)
        enable_clipboard(self._path_e)

        self._zip_panel = ctk.CTkFrame(self, fg_color="transparent")
        self._lbl_zip_hint = ctk.CTkLabel(
            self._zip_panel,
            text=self._tr.t("import_zip_hint"),
            text_color="#9ca3af",
            font=ctk.CTkFont(size=11),
            justify="left",
        )
        self._lbl_zip_hint.pack(anchor="w", pady=(0, 4))
        self._lbl_zip_pwd = ctk.CTkLabel(self._zip_panel, text=self._tr.t("import_zip_password"), text_color=COLOR_TEXT)
        self._lbl_zip_pwd.pack(anchor="w")
        zip_pwd_row = ctk.CTkFrame(self._zip_panel, fg_color="transparent")
        zip_pwd_row.pack(fill="x", pady=(2, 4))
        self._zip_pwd = PasswordField(zip_pwd_row)
        self._zip_pwd.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._btn_open_zip = ctk.CTkButton(
            zip_pwd_row,
            text=self._tr.t("import_open_zip"),
            width=130,
            command=self._load_selected_zip,
            fg_color=COLOR_ACCENT,
        )
        self._btn_open_zip.pack(side="right")

        self._err = ctk.CTkLabel(self, text="", text_color=COLOR_ERROR)
        self._err.pack(anchor="w", pady=(0, 4))

    def _build_filters_and_table_shell(self) -> None:
        filt = ctk.CTkFrame(self, fg_color="transparent")
        filt.pack(fill="x", pady=(0, 6))
        self._lbl_filter = ctk.CTkLabel(filt, text=self._tr.t("import_filter"), text_color=COLOR_TEXT)
        self._lbl_filter.pack(side="left", padx=(0, 8))
        self._filter_menu = ctk.CTkOptionMenu(
            filt,
            values=[],
            command=self._on_filter_label,
            fg_color="#2a2a2a",
            button_color=COLOR_ACCENT,
        )
        self._filter_menu.pack(side="left", padx=(0, 8))
        self._setup_filter_menu_labels()

        self._chk_show_pwd = ctk.CTkCheckBox(
            filt,
            text=self._tr.t("import_show_passwords"),
            variable=self._show_passwords,
            command=self._toggle_password_visibility,
        )
        self._chk_show_pwd.pack(side="left", padx=(8, 0))

        bt = ctk.CTkFrame(self, fg_color="transparent")
        bt.pack(fill="x", pady=(0, 6))
        self._btn_sel_all = ctk.CTkButton(
            bt,
            text=self._tr.t("import_select_all"),
            command=self._select_all_visible,
            fg_color=COLOR_ACCENT,
        )
        self._btn_sel_all.pack(side="left", padx=(0, 6))
        self._btn_sel_none = ctk.CTkButton(
            bt,
            text=self._tr.t("import_select_none"),
            command=self._select_none_visible,
            fg_color="#374151",
        )
        self._btn_sel_none.pack(side="left")

        self._table = ctk.CTkScrollableFrame(self, fg_color="#252525", corner_radius=CORNER_RADIUS, height=320)
        self._table.pack(fill="both", expand=True, pady=(0, 8))

    def _build_footer(self) -> None:
        self._progress = ctk.CTkProgressBar(self, height=12)
        self._progress.pack(fill="x", pady=(0, 4))
        self._progress.set(0)
        self._prog_label = ctk.CTkLabel(self, text="", text_color="#9ca3af", font=ctk.CTkFont(size=11))
        self._prog_label.pack(anchor="w", pady=(0, 6))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        self._btn_import_sel = ctk.CTkButton(
            row,
            text=self._tr.t("import_selected"),
            command=self._import_selected,
            fg_color=COLOR_ACCENT,
        )
        self._btn_import_sel.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self._btn_import_all = ctk.CTkButton(
            row,
            text=self._tr.t("import_all"),
            command=self._import_all,
            fg_color=COLOR_ACCENT,
        )
        self._btn_import_all.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self._btn_stop = ctk.CTkButton(
            row,
            text=self._tr.t("import_stop"),
            command=self._stop_import,
            fg_color="#b45309",
            state="disabled",
        )
        self._btn_stop.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self._btn_back = ctk.CTkButton(
            row,
            text=self._tr.t("cancel"),
            command=self._back_if_idle,
            fg_color="#374151",
        )
        self._btn_back.pack(side="left", expand=True, fill="x")

        self._pwd_entries: list[ctk.CTkEntry] = []

    def _setup_filter_menu_labels(self) -> None:
        labels = {
            "all": self._tr.t("filter_all"),
            "new_only": self._tr.t("filter_new_only"),
            "duplicates": self._tr.t("filter_duplicates"),
        }
        self._filter_key_by_label = {v: k for k, v in labels.items()}
        self._filter_menu.configure(values=list(labels.values()))
        self._filter_menu.set(labels[self._filter_key])

    def _on_filter_label(self, label: str) -> None:
        self._filter_key = self._filter_key_by_label.get(label, "all")
        self._rebuild_table()

    def _current_filter_key(self) -> str:
        return self._filter_key

    def _on_browser_label(self, label: str) -> None:
        for kind, text in self._browser_labels.items():
            if text == label:
                self._browser_var.set(kind.value)
                break
        self._refresh_browser_icon()

    def _refresh_browser_icon(self) -> None:
        slug = self._browser_var.get()
        path = get_browser_icon_path(slug)
        if not path.exists():
            self._browser_icon_lbl.configure(image=None, text="🌐")
            return
        try:
            img = Image.open(path).resize((28, 28), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(28, 28))
            self._icon_refs.append(ctk_img)
            self._browser_icon_lbl.configure(image=ctk_img, text="")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Иконка браузера: %s", exc)
            self._browser_icon_lbl.configure(image=None, text="🌐")

    def _pick_csv(self) -> None:
        if self._importing:
            return
        path_str = filedialog.askopenfilename(
            filetypes=[
                ("CSV или ZIP", "*.csv;*.zip"),
                ("CSV", "*.csv"),
                ("ZIP", "*.zip"),
                ("Все файлы", "*.*"),
            ],
        )
        if not path_str:
            return
        path = Path(path_str)
        if not path.is_file():
            self._err.configure(text=self._tr.t("import_file_missing"))
            return
        self._path_e.configure(state="normal")
        self._path_e.delete(0, "end")
        self._path_e.insert(0, str(path))
        self._path_e.configure(state="readonly")
        self._pending_zip = None
        self._zip_panel.pack_forget()
        self._zip_pwd.clear()
        self._err.configure(text="")
        self._raw_rows = []
        self._annotated = []
        self._check_vars.clear()
        self._rebuild_table()

        if path.suffix.lower() == ".zip":
            self._pending_zip = path
            self._zip_panel.pack(fill="x", pady=(0, 6), after=self._browse_row)
            return

        try:
            kind = BrowserKind(self._browser_var.get())
            rows = parse_browser_csv(path, kind)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Парсинг CSV: %s", exc)
            self._err.configure(text=self._tr.t("import_parse_error").format(err=str(exc)))
            return
        self._apply_loaded_rows(rows)

    def _load_selected_zip(self) -> None:
        """Распаковывает CSV из выбранного ZIP и строит предпросмотр."""
        if self._importing or self._pending_zip is None:
            return
        try:
            kind = BrowserKind(self._browser_var.get())
            pwd = self._zip_pwd.get()
            rows = parse_browser_zip(self._pending_zip, pwd, kind)
        except ValueError as exc:
            key = str(exc.args[0]) if exc.args else ""
            if key in ("zip_no_csv", "zip_bad_password", "zip_read_error", "zip_install_pyzipper"):
                self._err.configure(text=self._tr.t(key))
            else:
                self._err.configure(text=self._tr.t("import_parse_error").format(err=str(exc)))
            logger.info("ZIP/CSV: %s", exc)
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Парсинг ZIP: %s", exc)
            self._err.configure(text=self._tr.t("import_parse_error").format(err=str(exc)))
            return
        self._err.configure(text="")
        self._apply_loaded_rows(rows)

    def _apply_loaded_rows(self, rows: list[dict[str, Any]]) -> None:
        """Заполняет предпросмотр по уже распарсенным строкам."""
        self._raw_rows = rows
        self._annotated = annotate_import_preview(rows, self._db)
        self._check_vars.clear()
        for row in self._annotated:
            default_on = row.valid and not row.duplicate_in_db and not row.duplicate_in_file
            self._check_vars[row.index] = ctk.BooleanVar(value=default_on)
        self._rebuild_table()
        logger.info("Загружен предпросмотр импорта: %s строк", len(rows))

    def _row_visible(self, row: AnnotatedImportRow) -> bool:
        key = self._current_filter_key()
        if key == "all":
            return True
        if key == "new_only":
            return row.valid and not row.duplicate_in_db and not row.duplicate_in_file
        return row.duplicate_in_db or row.duplicate_in_file

    def _rebuild_table(self) -> None:
        for w in self._table.winfo_children():
            w.destroy()
        self._pwd_entries.clear()
        for row in self._annotated:
            if not self._row_visible(row):
                continue
            fr = ctk.CTkFrame(self._table, fg_color="transparent")
            fr.pack(fill="x", pady=2)
            var = self._check_vars.setdefault(row.index, ctk.BooleanVar(value=False))
            ctk.CTkCheckBox(fr, text="", variable=var, width=28).grid(row=0, column=0, padx=(0, 4))
            title = row.title[:48] + ("…" if len(row.title) > 48 else "")
            ctk.CTkLabel(fr, text=title, width=160, anchor="w", text_color=COLOR_TEXT).grid(row=0, column=1, sticky="w")
            login_e = ctk.CTkEntry(fr, width=140, fg_color="#2a2a2a", text_color=COLOR_TEXT)
            login_e.grid(row=0, column=2, padx=4)
            login_e.insert(0, row.login)
            login_e.configure(state="readonly")
            enable_clipboard(login_e)
            pwd_e = ctk.CTkEntry(fr, width=140, show="*", fg_color="#2a2a2a", text_color=COLOR_TEXT)
            pwd_e.grid(row=0, column=3, padx=4)
            pwd_e.insert(0, row.password)
            enable_clipboard(pwd_e)
            self._pwd_entries.append(pwd_e)
            pwd_e.configure(show="" if self._show_passwords.get() else "*")
            if not row.valid:
                badge = self._tr.t("import_badge_invalid")
            elif row.duplicate_in_db:
                badge = self._tr.t("import_badge_dup_db")
            elif row.duplicate_in_file:
                badge = self._tr.t("import_badge_dup_file")
            else:
                badge = ""
            ctk.CTkLabel(fr, text=badge, text_color="#fbbf24", width=120, anchor="e").grid(
                row=0,
                column=4,
                sticky="e",
            )
            fr.grid_columnconfigure(1, weight=1)

    def _toggle_password_visibility(self) -> None:
        show = "" if self._show_passwords.get() else "*"
        for e in self._pwd_entries:
            e.configure(show=show)

    def _visible_indices(self) -> list[int]:
        return [r.index for r in self._annotated if self._row_visible(r)]

    def _select_all_visible(self) -> None:
        for i in self._visible_indices():
            self._check_vars.setdefault(i, ctk.BooleanVar(value=False)).set(True)

    def _select_none_visible(self) -> None:
        for i in self._visible_indices():
            self._check_vars.setdefault(i, ctk.BooleanVar(value=False)).set(False)

    def _records_for_indices(self, indices: list[int]) -> list[dict[str, Any]]:
        return [self._raw_rows[i] for i in sorted(set(indices)) if 0 <= i < len(self._raw_rows)]

    def _import_selected(self) -> None:
        if self._importing or not self._raw_rows:
            return
        idx = [i for i in self._visible_indices() if self._check_vars.get(i) and self._check_vars[i].get()]
        if not idx:
            self._err.configure(text=self._tr.t("import_none_selected"))
            return
        self._start_import(self._records_for_indices(idx))

    def _import_all(self) -> None:
        if self._importing or not self._raw_rows:
            return
        self._start_import(list(self._raw_rows))

    def _start_import(self, records: list[dict[str, Any]]) -> None:
        self._importing = True
        self._cancel_event.clear()
        self._err.configure(text="")
        self._progress.set(0)
        self._prog_label.configure(text=self._tr.t("import_progress_start"))
        self._set_import_ui_busy(True)

        def worker() -> None:
            def on_prog(n: int, t: int) -> None:
                self._ui_q.put(("prog", n, t))

            def should_cancel() -> bool:
                return self._cancel_event.is_set()

            try:
                stats = import_records(
                    self._db,
                    records,
                    skip_duplicates=True,
                    should_cancel=should_cancel,
                    on_progress=on_prog,
                )
                self._ui_q.put(("done", stats))
            except Exception as exc:  # noqa: BLE001
                logger.exception("Импорт CSV: %s", exc)
                self._ui_q.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self.after(80, self._poll_import_queue)

    def _poll_import_queue(self) -> None:
        try:
            while True:
                msg = self._ui_q.get_nowait()
                if msg[0] == "prog":
                    _, n, total = msg
                    if total > 0:
                        self._progress.set(n / total)
                    self._prog_label.configure(text=self._tr.t("import_progress_fmt").format(n=n, total=total))
                elif msg[0] == "done":
                    self._import_finished_ok(msg[1])
                    return
                elif msg[0] == "error":
                    self._import_finished_err(msg[1])
                    return
        except queue.Empty:
            pass
        if self._importing:
            self.after(80, self._poll_import_queue)

    def _import_finished_ok(self, stats: tuple[int, int, int]) -> None:
        imp, skip_d, skip_i = stats
        self._importing = False
        self._progress.set(1.0)
        self._prog_label.configure(
            text=self._tr.t("import_result_log").format(i=imp, d=skip_d, e=skip_i),
        )
        self._set_import_ui_busy(False)
        self._on_done(imp, skip_d, skip_i)

    def _import_finished_err(self, err: str) -> None:
        self._importing = False
        self._set_import_ui_busy(False)
        self._err.configure(text=self._tr.t("import_fail") + f" {err}")

    def _stop_import(self) -> None:
        if self._importing:
            self._cancel_event.set()
            self._prog_label.configure(text=self._tr.t("import_cancelling"))

    def _set_import_ui_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self._btn_import_sel.configure(state=state)
        self._btn_import_all.configure(state=state)
        self._btn_back.configure(state=state)
        self._btn_sel_all.configure(state=state)
        self._btn_sel_none.configure(state=state)
        self._btn_csv_browse.configure(state=state)
        self._btn_open_zip.configure(state=state)
        self._zip_pwd.entry.configure(state=state)
        self._zip_pwd.toggle_btn.configure(state=state)
        self._chk_show_pwd.configure(state=state)
        self._btn_stop.configure(state="normal" if busy else "disabled")
        self._filter_menu.configure(state=state)
        self._browser_menu.configure(state=state)

    def _back_if_idle(self) -> None:
        if self._importing:
            return
        self._on_cancel()

    def refresh_language(self) -> None:
        """Обновляет подписи после смены языка."""
        self._warn.configure(state="normal")
        self._warn.delete("1.0", "end")
        self._warn.insert("1.0", self._tr.t("browser_import_warning"))
        self._warn.configure(state="disabled")

        self._browser_labels = {
            BrowserKind.CHROME: self._tr.t("browser_chrome"),
            BrowserKind.YANDEX: self._tr.t("browser_yandex"),
            BrowserKind.EDGE: self._tr.t("browser_edge"),
            BrowserKind.OPERA: self._tr.t("browser_opera"),
            BrowserKind.FIREFOX: self._tr.t("browser_firefox"),
        }
        cur = BrowserKind(self._browser_var.get())
        self._browser_menu.configure(values=[self._browser_labels[k] for k in self._browser_order()])
        self._browser_menu.set(self._browser_labels[cur])

        self._lbl_filter.configure(text=self._tr.t("import_filter"))
        self._setup_filter_menu_labels()
        self._chk_show_pwd.configure(text=self._tr.t("import_show_passwords"))
        self._btn_sel_all.configure(text=self._tr.t("import_select_all"))
        self._btn_sel_none.configure(text=self._tr.t("import_select_none"))
        self._btn_csv_browse.configure(text=self._tr.t("browse"))
        self._lbl_zip_hint.configure(text=self._tr.t("import_zip_hint"))
        self._lbl_zip_pwd.configure(text=self._tr.t("import_zip_password"))
        self._btn_open_zip.configure(text=self._tr.t("import_open_zip"))

        self._btn_import_sel.configure(text=self._tr.t("import_selected"))
        self._btn_import_all.configure(text=self._tr.t("import_all"))
        self._btn_stop.configure(text=self._tr.t("import_stop"))
        self._btn_back.configure(text=self._tr.t("cancel"))
        self._rebuild_table()

    @staticmethod
    def _browser_order() -> list[BrowserKind]:
        return [
            BrowserKind.CHROME,
            BrowserKind.YANDEX,
            BrowserKind.EDGE,
            BrowserKind.OPERA,
            BrowserKind.FIREFOX,
        ]
